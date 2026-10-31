"""
Precios de referencia en CLP para los insumos de Dulce Arte.

Los precios están expresados en pesos chilenos **por unidad de medida del
insumo** (por kilo, por litro, por unidad o por mililitro), que es exactamente
lo que espera ``Insumo.precio_unitario`` y lo que multiplica el BOM.

Antes estos valores estaban en una escala tipo dólar (harina 1.2, huevos 0.2),
por eso la ficha del producto mostraba "$1" y "$0" y el margen quedaba inflado
en un factor ~1.000.

Fuentes (consultadas 2026-10): Jumbo.cl y La Casa Chocolate / Repostería
Llopis (mayoristas de repostería). Se usa el precio de lista, no el de oferta.

Para aplicar estos precios a una base ya poblada (local o AWS)::

    python manage.py precios_clp
"""
from __future__ import annotations

from decimal import Decimal

FUENTE = "Jumbo.cl + La Casa Chocolate / Repostería Llopis (precio de lista, 2026-10)"

# nombre del insumo -> (precio CLP por unidad del insumo, nota del formato real)
PRECIOS_CLP: dict[str, tuple[Decimal, str]] = {
    "Harina": (Decimal("1390"), "harina sin polvos 1 kg"),
    "Azúcar": (Decimal("1290"), "azúcar granulada 1 kg"),
    "Mantequilla": (Decimal("13200"), "mantequilla 250 g ≈ $3.300 → $13.200/kg"),
    "Huevos": (Decimal("340"), "huevo blanco por unidad (maple 30 ≈ $10.200)"),
    "Chocolate amargo": (Decimal("7900"), "cobertura amarga profesional 1 kg"),
    "Crema para batir": (Decimal("4900"), "crema de leche 1 L"),
    "Fondant": (Decimal("6290"), "fondant blanco 1 kg"),
    "Colorante alimentario": (Decimal("95"), "gel 20 g ≈ $1.990 → ≈$95/ml"),
    "Frutas frescas": (Decimal("8990"), "frambuesas IQF 1 kg"),
    "Levadura": (Decimal("18900"), "levadura seca 125 g ≈ $2.450 → $19.600/kg"),
    "Cacao en polvo": (Decimal("7500"), "cacao amargo 500 g ≈ $3.750 → $7.500/kg"),
    "Vainilla": (Decimal("10.5"), "esencia 165 ml ≈ $1.730 → ≈$10,5/ml"),
    "Cajas de presentación": (Decimal("1190"), "caja de repostería por unidad"),
    "Faja para torta": (Decimal("190"), "faja de cartulina por unidad (estimado)"),
}


def precio_clp(nombre: str) -> Decimal | None:
    """Devuelve el precio CLP de referencia para un insumo, si existe."""
    dato = PRECIOS_CLP.get(nombre)
    return dato[0] if dato else None
