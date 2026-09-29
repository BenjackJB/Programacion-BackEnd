"""Paginación estándar del API (respuestas de lista)."""

from rest_framework.pagination import PageNumberPagination


class ResultadosPaginados(PageNumberPagination):
    """Paginación por número de página: ?page=N&page_size=M (máx. 100)."""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
