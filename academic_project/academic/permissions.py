"""
Permisos personalizados para la app academic.

Controlan acceso a vistas y endpoints API según rol de usuario.
En la API: lectura pública para Asignatura, y CRUD protegido por JWT en el resto
(se usa IsAuthenticated / IsAuthenticatedOrReadOnly de DRF directamente en las vistas).
"""

from rest_framework import permissions


class IsSuperUser(permissions.BasePermission):
    """
    Permiso: solo superusuarios (acceso al índice/root de la API).
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
