"""
Servicios de negocio del sistema de boletería.

El checkout prepara la orden y delega los efectos de la transición en la
señal `aplicar_efectos_de_transicion` (ver boletos/signals.py): validación y
descuento de stock, emisión de tickets con código Hash/UUID único y
reposición/anulación cuando la orden se cancela.

Además prepara el pago en línea con TRANSBANK WEBPAY PLUS:
- preparar_orden_webpay()  crea/reutiliza la orden PENDIENTE con un snapshot
  de los ítems del carro antes de redirigir al ambiente de pago.
- confirmar_pago_webpay()  confirma la orden (PENDIENTE -> PAGADO) cuando
  Webpay aprueba la transacción, reutilizando la misma señal de efectos.
"""

from types import SimpleNamespace

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Carro, Compra, CompraHistorial


@transaction.atomic
def procesar_pago(usuario, observacion=''):
    """
    CONFIRMACIÓN DEL PEDIDO Y PROCESAMIENTO DEL PAGO.

    Pasos (todos dentro de una misma transacción):
    1. Bloquea el carro del usuario y lee sus ítems.
    2. Crea la orden en estado PENDIENTE (auditoría inicial).
    3. Adjunta los ítems a facturar y guarda la orden como PAGADO: en ese
       momento la SEÑAL de transiciones valida y descuenta el stock de cada
       sector (bloqueo pesimista) y emite un ticket por entrada con código
       Hash/UUID único. Si algún sector no alcanza, la transacción se RECHAZA
       completa (rollback) y no queda registro de la orden.
    4. Registra la transición en el historial de auditoría.
    5. Vacía el carro persistente.

    El stock solo se descuenta aquí: nunca al agregar al carro.
    Devuelve la orden pagada con sus tickets emitidos.
    """
    carro = Carro.objects.select_for_update().filter(usuario=usuario).first()
    if carro is None:
        raise ValidationError({'carro': 'No tienes un carro de compras activo.'})

    items = list(carro.items.select_related('sector', 'sector__evento').filter(activo=True))
    if not items:
        raise ValidationError({'carro': 'El carro está vacío: agrega entradas antes de pagar.'})

    total = sum((item.subtotal for item in items), 0)

    # 1) Orden creada como PENDIENTE (transición inicial del ciclo de vida).
    compra = Compra.objects.create(
        comprador=usuario,
        estado=Compra.Estado.PENDIENTE,
        total=total,
    )
    CompraHistorial.objects.create(
        compra=compra,
        estado=Compra.Estado.PENDIENTE,
        usuario=usuario,
        detalle='Orden generada en el checkout (pendiente de pago).',
    )

    # 2) Transición PENDIENTE -> PAGADO: la señal descuenta stock y emite tickets.
    compra._items_pago = items
    compra.estado = Compra.Estado.PAGADO
    compra.fecha_pago = timezone.now()
    if observacion:
        compra.observacion = observacion
    compra.save(update_fields=['estado', 'fecha_pago', 'observacion', 'fecha_actualizacion'])

    CompraHistorial.objects.create(
        compra=compra,
        estado=Compra.Estado.PAGADO,
        usuario=usuario,
        detalle='Pago aprobado: stock descontado y tickets emitidos.',
    )

    # 3) El carro se liquida al confirmar el pedido.
    carro.vaciar()

    return compra


# =============================================================================
# PAGO EN LÍNEA CON TRANSBANK WEBPAY PLUS
# =============================================================================

def _items_del_carro(usuario):
    """Ítems activos del carro del usuario (bloqueo pesimista si hay carro)."""
    carro = Carro.objects.select_for_update().filter(usuario=usuario).first()
    if carro is None:
        return [], None
    items = list(carro.items.select_related('sector', 'sector__evento').filter(activo=True))
    return items, carro


@transaction.atomic
def preparar_orden_webpay(usuario):
    """
    Prepara la orden PENDIENTE antes de redirigir al ambiente de Webpay.

    1. Bloquea el carro y lee sus ítems (misma validación del checkout).
    2. Crea la orden PENDIENTE (o reutiliza la existente de un intento previo)
       con el total recalculado.
    3. Guarda un SNAPSHOT de los ítems ({sector_id, cantidad}) en
       `items_pago`: si el usuario modifica el carro mientras paga en Webpay,
       la señal de PAGADO facturará exactamente lo que se ofreció aquí.

    El stock sigue intacto hasta que Webpay apruebe el pago (señal PAGADO).
    Devuelve la orden lista para asociarle la transacción Webpay.
    """
    items, carro = _items_del_carro(usuario)
    if carro is None:
        raise ValidationError({'carro': 'No tienes un carro de compras activo.'})
    if not items:
        raise ValidationError({'carro': 'El carro está vacío: agrega entradas antes de pagar.'})

    total = sum((item.subtotal for item in items), 0)

    compra = Compra.objects.filter(comprador=usuario, estado=Compra.Estado.PENDIENTE).first()
    if compra is None:
        compra = Compra.objects.create(
            comprador=usuario,
            estado=Compra.Estado.PENDIENTE,
            total=total,
        )
        CompraHistorial.objects.create(
            compra=compra,
            estado=Compra.Estado.PENDIENTE,
            usuario=usuario,
            detalle='Orden generada en el checkout Webpay (pendiente de pago).',
        )
    else:
        compra.total = total

    compra.items_pago = [
        {'sector_id': item.sector_id, 'cantidad': item.cantidad} for item in items
    ]
    compra.save(update_fields=['total', 'items_pago', 'fecha_actualizacion'])
    return compra


def _items_desde_snapshot(compra):
    """Reconstruye los ítems del snapshot `items_pago` (sector_id + cantidad)."""
    if not compra.items_pago:
        return None
    return [
        SimpleNamespace(sector_id=item['sector_id'], cantidad=item['cantidad'])
        for item in compra.items_pago
    ]


@transaction.atomic
def confirmar_pago_webpay(compra):
    """
    Confirma la orden cuando Webpay aprueba el pago: PENDIENTE -> PAGADO.

    - Usa el snapshot `items_pago` (o, en su defecto, los ítems del carro como
      respaldo) para que la señal `aplicar_efectos_de_transicion` valide y
      descuente el stock y emita los tickets con código Hash/UUID único.
    - Registra la transición en el historial de auditoría.
    - Vacía el carro persistente.

    Idempotente: si la orden ya estaba PAGADA (doble retorno de Webpay) no
    vuelve a descontar stock ni emitir tickets.
    """
    if compra.estado == Compra.Estado.PAGADO:
        return compra
    if compra.estado != Compra.Estado.PENDIENTE:
        raise ValidationError({
            'estado': f'La orden está en {compra.get_estado_display()} y no puede confirmarse como pagada.',
        })

    items = _items_desde_snapshot(compra)
    if items is None:
        items, _carro = _items_del_carro(compra.comprador)
    if not items:
        raise ValidationError({'webpay': 'La orden no tiene ítems para facturar.'})

    # Transición PENDIENTE -> PAGADO: la señal descuenta stock y emite tickets.
    compra._items_pago = items
    compra.estado = Compra.Estado.PAGADO
    compra.fecha_pago = timezone.now()
    compra.save(update_fields=['estado', 'fecha_pago', 'fecha_actualizacion'])

    CompraHistorial.objects.create(
        compra=compra,
        estado=Compra.Estado.PAGADO,
        usuario=compra.comprador,
        detalle='Pago Webpay aprobado: stock descontado y tickets emitidos.',
    )

    # El carro se liquida al confirmar el pedido.
    carro = Carro.all_objects.filter(usuario=compra.comprador).first()
    if carro is not None:
        carro.vaciar()

    return compra
