"""
Permisos personalizados para la app academic.

Controlan acceso a vistas y endpoints API según rol de usuario.
El superusuario 'profe' tiene acceso total.
"""

from rest_framework import permissions
from django.contrib.auth.models import User


class IsSuperUserOrReadOnly(permissions.BasePermission):
    """
    Permiso: lectura libre para cualquiera, escritura solo para superusuarios.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsOwnerOrSuperUser(permissions.BasePermission):
    """
    Permiso: Dueño del objeto o superusuario pueden modificar.
    Para modelos con campo 'user' o similar.
    """
    def has_object_permission(self, request, view, obj):
        # Superusuario tiene acceso total
        if request.user.is_superuser:
            return True
        # Verificar si el objeto tiene campo user y coincide
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class AcademicPermission(permissions.BasePermission):
    """
    Permiso académico: lectura libre y escritura solo para superusuarios.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class CanManageTeachers(permissions.BasePermission):
    """Permiso para gestionar docentes (solo superusuario)."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class CanManageCourses(permissions.BasePermission):
    """Permiso para gestionar cursos (solo superusuario)."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class CanManageStudents(permissions.BasePermission):
    """Permiso para gestionar estudiantes (solo superusuario)."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class CanManageEnrollments(permissions.BasePermission):
    """Permiso para gestionar inscripciones (solo superusuario)."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser