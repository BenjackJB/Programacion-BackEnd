"""
Servicios de negocio del sistema de boletería.

El checkout prepara la orden y delega los efectos de la transición en la
señal `aplicar_efectos_de_transicion` (ver boletos/signals.py): validación y
descuento de stock, emisión de tickets con código Hash/UUID único y
reposición/anulación cuando la orden se cancela.
"""

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
