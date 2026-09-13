"""
Permisos personalizados para la app academic.

Controlan acceso a vistas y endpoints API según rol de usuario.
El superusuario 'profe' tiene acceso total.
"""

from rest_framework import permissions


class IsSuperUserOrReadOnly(permissions.BasePermission):
    """
    Permiso: lectura libre para cualquiera, escritura solo para superusuarios.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
