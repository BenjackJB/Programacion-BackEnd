"""Tags y filtros de plantilla propios de Dulce Arte."""
from django import template
from django.utils.html import format_html

register = template.Library()


# Paleta del design system por estado (una sola coral por viewport)
_ESTADO_LABELS = {
    "recibido": "Recibido",
    "preparacion": "En Preparación",
    "horneado": "Horneado / Decorado",
    "control": "Control de Calidad",
    "listo": "Listo",
}

_ESTADO_COLORS = {
    "recibido": "#707070",
    "preparacion": "#dc8264",
    "horneado": "#fa7864",
    "control": "#282828",
    "listo": "#2e7d32",
}

_PRIORIDAD_COLORS = {
    "normal": ("#e8e8e1", "#282828"),
    "alta": ("#dc8264", "#ffffff"),
    "urgente": ("#fa7864", "#ffffff"),
}


@register.filter
def estado_badge(valor):
    """Convierte el valor de un estado en una etiqueta pill coloreada."""
    color = _ESTADO_COLORS.get(str(valor), "#707070")
    etiqueta = _ESTADO_LABELS.get(str(valor), str(valor).title())
    return format_html(
        '<span class="badge" style="background:{};color:#fff">{}</span>',
        color,
        etiqueta,
    )


@register.filter
def prioridad_badge(valor):
    bg, fg = _PRIORIDAD_COLORS.get(str(valor), ("#e8e8e1", "#282828"))
    etiqueta = str(valor).title()
    return format_html(
        '<span class="badge" style="background:{};color:{}">{}</span>',
        bg,
        fg,
        etiqueta,
    )


@register.filter
def estado_despacho_badge(valor):
    colores = {
        "pendiente": "#707070",
        "en_ruta": "#dc8264",
        "entregado": "#2e7d32",
        "rechazado": "#c62828",
    }
    color = colores.get(str(valor), "#707070")
    etiqueta = str(valor).replace("_", " ").title()
    return format_html(
        '<span class="badge" style="background:{};color:#fff">{}</span>',
        color,
        etiqueta,
    )
