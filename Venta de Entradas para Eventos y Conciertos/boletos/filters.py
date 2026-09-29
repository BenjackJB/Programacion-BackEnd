"""
Sistema de filtros con django-filter.

- EventoFilter : categoría, estado, recinto, rango de precios y rango de fechas.
- CompraFilter : estado de la orden, comprador, evento y rango de fechas.
"""

from django.db.models import OuterRef, Subquery
from django_filters import rest_framework as filters

from .models import Compra, Evento, Recinto, Sector, User


class EventoFilter(filters.FilterSet):
    """Filtros del catálogo de eventos sobre campos clave del modelo."""

    categoria = filters.ChoiceFilter(choices=Evento.Categoria.choices, label='Categoría')
    estado = filters.ChoiceFilter(choices=Evento.Estado.choices, label='Estado')
    recinto = filters.ModelChoiceFilter(queryset=Recinto.objects.all(), label='Recinto')
    organizador = filters.ModelChoiceFilter(queryset=User.objects.all(), label='Organizador')

    fecha_desde = filters.DateTimeFilter(field_name='fecha', lookup_expr='gte', label='Fecha desde')
    fecha_hasta = filters.DateTimeFilter(field_name='fecha', lookup_expr='lte', label='Fecha hasta')

    precio_min = filters.NumberFilter(method='filter_precio_min', label='Precio mínimo')
    precio_max = filters.NumberFilter(method='filter_precio_max', label='Precio máximo')
    disponibles = filters.BooleanFilter(method='filter_disponibles', label='Solo con entradas')

    class Meta:
        model = Evento
        fields = ['categoria', 'estado', 'recinto', 'organizador']

    @staticmethod
    def _subquery_precio_minimo():
        """Subconsulta con el precio del sector más barato de cada evento."""
        return Subquery(
            Sector.objects.filter(
                evento=OuterRef('pk'),
                activo=True,
            ).order_by('precio').values('precio')[:1]
        )

    def filter_precio_min(self, queryset, name, value):
        """Eventos cuyo sector más barato cuesta igual o más que el valor indicado."""
        return queryset.annotate(_precio_min=self._subquery_precio_minimo()).filter(
            _precio_min__gte=value
        )

    def filter_precio_max(self, queryset, name, value):
        """Eventos cuyo sector más barato cuesta igual o menos que el valor indicado."""
        return queryset.annotate(_precio_max=self._subquery_precio_minimo()).filter(
            _precio_max__lte=value
        )

    def filter_disponibles(self, queryset, name, value):
        """Filtra eventos con stock disponible (o agotados cuando value=False)."""
        con_stock = Sector.objects.filter(activo=True).exclude(
            stock_disponible__lte=0
        ).values('evento_id')
        if value:
            return queryset.filter(pk__in=con_stock)
        return queryset.exclude(pk__in=con_stock)


class CompraFilter(filters.FilterSet):
    """Filtros de consulta de ventas/órdenes para el organizador."""

    estado = filters.ChoiceFilter(choices=Compra.Estado.choices, label='Estado')
    comprador = filters.ModelChoiceFilter(queryset=User.objects.all(), label='Comprador')
    evento = filters.ModelChoiceFilter(
        queryset=Evento.objects.all(), method='filter_evento', label='Evento'
    )
    fecha_desde = filters.DateFilter(
        field_name='fecha_creacion', lookup_expr='date__gte', label='Desde'
    )
    fecha_hasta = filters.DateFilter(
        field_name='fecha_creacion', lookup_expr='date__lte', label='Hasta'
    )
    total_min = filters.NumberFilter(field_name='total', lookup_expr='gte', label='Total mínimo')
    total_max = filters.NumberFilter(field_name='total', lookup_expr='lte', label='Total máximo')

    class Meta:
        model = Compra
        fields = ['estado', 'comprador']

    def filter_evento(self, queryset, name, value: Evento):
        """Órdenes que contienen al menos un ticket del evento indicado."""
        return queryset.filter(tickets__evento=value).distinct()
