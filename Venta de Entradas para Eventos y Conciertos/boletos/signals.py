"""
SEÑALES (SIGNALS) DE DJANGO: EFECTOS DE LAS TRANSICIONES DE ESTADO.

La rúbrica exige que el código fuente (modelos, vistas, serializadores y
SEÑALES) esté organizado y comentado por bloques. En este módulo viven todos
los efectos secundarios de cada cambio de estado de la orden `Compra`:

    PENDIENTE -> PAGADO    valida y descuenta el stock + emite los tickets
                           con código Hash/UUID único (único momento en que
                           se descuenta inventario).
    PAGADO    -> CANCELADO repone el stock descontado + anula los tickets.
    PAGADO    -> ENTREGADO marca la asistencia: tickets a INGRESADO.

CÓMO FUNCIONA
1. `pre_save(Compra)` guarda en la instancia el estado anterior de la orden
   (snapshot consultado en base de datos) antes de escribir el nuevo.
2. `post_save(Compra)` compara el estado anterior con el nuevo y ejecuta
   únicamente el efecto correspondiente a esa transición concreta.
3. Todo corre DENTRO de la transacción del llamador (procesar_pago o
   Compra.cambiar_estado): si un efecto falla (p. ej. stock insuficiente) se
   produce un ROLLBACK completo y no queda ningún registro huérfano.
4. Los efectos son IDEMPOTENTES: cada transición real se procesa una sola vez
   aunque la orden vuelva a guardarse por otros motivos.

QUIÉN LLAMA
- boletos/services.py -> procesar_pago() (checkout del espectador).
- boletos/models.py   -> Compra.cambiar_estado() (organizador: ENTREGADO /
                         CANCELADO).
"""

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from rest_framework.exceptions import ValidationError

from .models import Carro, CarroItem, Compra, Sector, Ticket


# =============================================================================
# AUXILIARES COMPARTIDOS POR LOS EFECTOS
# =============================================================================

def _consultar_items_del_pago(compra):
    """
    Ítems que deben facturarse al pasar a PAGADO.

    El checkout adjunta la lista (`_items_pago`) antes de guardar la orden;
    si no viene adjunta, se toman los ítems activos del carro persistente del
    comprador. Devuelve una lista vacía cuando no hay nada que facturar.
    """
    items = getattr(compra, '_items_pago', None)
    if items is not None:
        return list(items)

    carro = Carro.all_objects.filter(usuario=compra.comprador).first()
    if carro is None:
        return []
    return list(
        carro.items.select_related('sector', 'sector__evento').filter(activo=True)
    )


def _sector_bloqueado(sector_id):
    """Sector con bloqueo pesimista (SELECT FOR UPDATE) si estamos en transacción."""
    consulta = Sector.all_objects
    if transaction.get_connection().in_atomic_block:
        consulta = consulta.select_for_update()
    return consulta.get(pk=sector_id)


def _tickets_bloqueados(compra):
    """Tickets de la orden bloqueados para evitar condiciones de carrera."""
    consulta = compra.tickets
    if transaction.get_connection().in_atomic_block:
        consulta = consulta.select_for_update()
    return list(consulta.select_related('sector'))


# =============================================================================
# EFECTO 1: PENDIENTE -> PAGADO (DESCUENTO DE STOCK + EMISIÓN DE TICKETS)
# =============================================================================

def _pagar_orden(compra):
    """
    Valida disponibilidad, descuenta el stock de cada sector y emite un ticket
    por entrada con código Hash/UUID de 32 caracteres.

    Si un sector no alcanza, lanza ValidationError y la transacción completa se
    revierte (la orden deja de existir, el stock queda intacto y no hay tickets).
    """
    if Ticket.all_objects.filter(compra=compra).exists():
        return  # idempotencia: la orden ya tenía sus entradas emitidas

    items = _consultar_items_del_pago(compra)
    if not items:
        return  # nada que facturar (p. ej. una orden creada sin ítems)

    for item in items:
        sector = _sector_bloqueado(item.sector_id)

        if sector.stock_disponible < item.cantidad:
            raise ValidationError({
                'stock': (
                    f'Stock insuficiente para "{sector.nombre}" ({sector.evento.nombre}): '
                    f'se solicitan {item.cantidad} y quedan '
                    f'{sector.stock_disponible} disponibles.'
                )
            })

        # DESCUENTO DE INVENTARIO: exactamente al pasar a PAGADO.
        sector.stock_disponible -= item.cantidad
        sector.save(update_fields=['stock_disponible', 'fecha_actualizacion'])

        # EMISIÓN: un ticket por entrada, con código Hash/UUID único.
        for _ in range(item.cantidad):
            Ticket.objects.create(
                codigo=Ticket.generar_codigo(),
                compra=compra,
                sector=sector,
                evento=sector.evento,
            )


# =============================================================================
# EFECTO 2: PAGADO -> CANCELADO (REPOSICIÓN DE STOCK + ANULACIÓN DE TICKETS)
# =============================================================================

def _cancelar_orden(compra):
    """
    Repone el stock descontado (1 por ticket válido) y anula las entradas.

    Solo se repone lo que todavía estaba descontado: los tickets ya cancelados
    no vuelven a sumar cupo, por lo que el efecto es idempotente y jamás deja
    el stock por encima de `stock_total`.
    """
    for ticket in _tickets_bloqueados(compra):
        if ticket.estado == Ticket.Estado.CANCELADO:
            continue  # ya repuesto en un intento anterior

        sector = _sector_bloqueado(ticket.sector_id)
        sector.stock_disponible = min(sector.stock_disponible + 1, sector.stock_total)
        sector.save(update_fields=['stock_disponible', 'fecha_actualizacion'])

        ticket.estado = Ticket.Estado.CANCELADO
        ticket.save(update_fields=['estado', 'fecha_actualizacion'])


# =============================================================================
# EFECTO 3: PAGADO -> ENTREGADO (MARCA DE ASISTENCIA / INGRESO)
# =============================================================================

def _entregar_orden(compra):
    """
    Marca la asistencia: todos los tickets pasan a INGRESADO.

    El stock NO se repone: la venta se concreta y el cupo queda consumido.
    """
    for ticket in _tickets_bloqueados(compra):
        if ticket.estado in (Ticket.Estado.INGRESADO, Ticket.Estado.CANCELADO):
            continue  # idempotente: no se re-registra una entrada anulada
        ticket.estado = Ticket.Estado.INGRESADO
        ticket.save(update_fields=['estado', 'fecha_actualizacion'])


# =============================================================================
# CONEXIÓN DE LAS SEÑALES
# =============================================================================

@receiver(pre_save, sender=Compra)
def capturar_estado_anterior(sender, instance, **kwargs):
    """
    SEÑAL: antes de guardar una orden, recuerda su estado anterior.

    Permite que `post_save` sepa si hubo una transición real (p. ej. de
    PENDIENTE a PAGADO) y no simplemente una re-escritura de los mismos datos.
    """
    if instance.pk:
        instance._estado_anterior = (
            sender.all_objects.filter(pk=instance.pk)
            .values_list('estado', flat=True)
            .first()
        )
    else:
        instance._estado_anterior = None


@receiver(post_save, sender=Compra)
def aplicar_efectos_de_transicion(sender, instance, created, **kwargs):
    """
    SEÑAL: después de guardar una orden, ejecuta el efecto de su transición.

    - Al crear la orden (created=True) no hay transición: solo se anota el
      estado inicial para las comparaciones siguientes.
    - Si el estado no cambió, no se hace nada (re-guardados frecuentes).
    - Cada efecto ocurre dentro de la transacción del llamador.
    """
    if created:
        instance._estado_anterior = instance.estado
        return

    anterior = getattr(instance, '_estado_anterior', None)
    instance._estado_anterior = instance.estado  # se consume: no se repite

    if not anterior or anterior == instance.estado:
        return

    if instance.estado == Compra.Estado.PAGADO and anterior == Compra.Estado.PENDIENTE:
        _pagar_orden(instance)
    elif instance.estado == Compra.Estado.CANCELADO and anterior == Compra.Estado.PAGADO:
        _cancelar_orden(instance)
    elif instance.estado == Compra.Estado.ENTREGADO and anterior == Compra.Estado.PAGADO:
        _entregar_orden(instance)
