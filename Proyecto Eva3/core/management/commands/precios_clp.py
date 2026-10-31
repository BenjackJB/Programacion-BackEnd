"""
Comando idempotente para corregir los precios de insumos a CLP.

Uso::

    python manage.py precios_clp --dry-run   # muestra qué cambiaría
    python manage.py precios_clp             # aplica los precios de referencia

Sirve tanto en la base local (SQLite) como en la de AWS (PostgreSQL): se puede
ejecutar tras un ``git pull`` sin volver a sembrar datos ni perder pedidos.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand

from core.models import Insumo
from core.precios_referencia import FUENTE, PRECIOS_CLP


class Command(BaseCommand):
    help = "Actualiza Insumo.precio_unitario a precios de referencia realistas en CLP."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra los cambios sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        self.stdout.write(f"Precios de referencia CLP - {FUENTE}")

        actualizados = 0
        sin_cambio = 0
        desconocidos = []

        for insumo in Insumo.objects.order_by("nombre"):
            referencia = PRECIOS_CLP.get(insumo.nombre)
            if referencia is None:
                desconocidos.append(insumo.nombre)
                continue
            precio, _nota = referencia
            if insumo.precio_unitario == precio:
                sin_cambio += 1
                continue
            self.stdout.write(
                f"  {insumo.nombre}: ${insumo.precio_unitario:,.0f} -> ${precio:,.0f} "
                f"/ {insumo.get_unidad_display().lower()}"
            )
            if not dry_run:
                insumo.precio_unitario = precio
                insumo.save(update_fields=["precio_unitario", "actualizado"])
            actualizados += 1

        verbo = "se actualizarían" if dry_run else "actualizados"
        self.stdout.write(
            self.style.SUCCESS(
                f"{actualizados} insumos {verbo}, {sin_cambio} ya estaban correctos."
            )
        )
        if desconocidos:
            self.stdout.write(
                self.style.WARNING(
                    "Sin precio de referencia (se dejan intactos): "
                    + ", ".join(desconocidos)
                )
            )

        if not dry_run:
            self._resumen_margenes()

    def _resumen_margenes(self) -> None:
        """Muestra el margen resultante por producto para detectar outliers."""
        from core.models import Producto

        self.stdout.write("\nMárgenes resultantes:")
        for producto in Producto.objects.all():
            costo = producto.costo_insumos
            margen = producto.margen
            pct = (margen / producto.precio_base * 100) if producto.precio_base else Decimal("0")
            self.stdout.write(
                f"  {producto.nombre}: costo ${costo:,.0f} | "
                f"precio ${producto.precio_base:,.0f} | "
                f"margen ${margen:,.0f} ({pct:.1f}%)"
            )
