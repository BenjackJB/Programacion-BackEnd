"""
Configuración de paginación de la API REST.
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Paginación estándar: permite al cliente especificar page_size
    (por defecto usa PAGE_SIZE del settings).
    """
    page_size_query_param = 'page_size'
    max_page_size = 100