"""Devuelve rutas con IDs reales para el smoke test."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dulce_arte.settings")
django.setup()

from core.models import Cliente, Despacho, Insumo, Pedido, Producto  # noqa


def ids():
    rutas = []
    for p in Producto.objects.all()[:2]:
        rutas.append(f"/productos/{p.pk}/")
    for i in Insumo.objects.all()[:2]:
        rutas.append(f"/insumos/{i.pk}/")
    for p in Pedido.objects.all()[:3]:
        rutas.append(f"/pedidos/{p.pk}/")
    for c in Cliente.objects.all()[:2]:
        rutas.append(f"/clientes/{c.pk}/")
    for d in Despacho.objects.all()[:2]:
        rutas.append(f"/despachos/{d.pk}/")
    return rutas
