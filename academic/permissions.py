"""
Permisos personalizados para la app academic.

Controlan acceso a vistas y endpoints API según rol de usuario.
El superusuario 'profe' tiene acceso total.
"""

from rest_framework import permissions
from django.contrib.auth.models import User


class IsSuperUserOrReadOnly(permissions.BasePermission):
    """
<<<<<<< HEAD
    Permiso: lectura libre para cualquiera, escritura solo para superusuarios.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
=======
    Permiso: Solo superusuarios pueden modificar (POST, PUT, PATCH, DELETE).
    Otros usuarios autenticados solo lectura (GET, HEAD, OPTIONS).
    """
    def has_permission(self, request, view):
        # Lectura permitida para cualquier usuario autenticado
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Escritura solo para superusuarios
        return request.user and request.user.is_superuser
>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0


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
<<<<<<< HEAD
    Permiso académico: lectura libre y escritura solo para superusuarios.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
=======
    Permiso personalizado para la app academic.
    - Superusuario (profe): acceso total a todo
    - Usuario autenticado: lectura de cursos y estudiantes
    - Sin autenticar: solo login
    """
    def has_permission(self, request, view):
        # Requiere autenticación para todo
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusuario tiene acceso total
        if request.user.is_superuser:
            return True

        # Usuarios normales: solo lectura en endpoints académicos
        if request.method in permissions.SAFE_METHODS:
            return True

        # No permitir escritura a usuarios no superuser
        return False
>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0


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