"""
Permisos personalizados por rol para el API (DRF).

Roles del sistema (claim `rol` del JWT):
- Espectador  : carro de compras, pago y consulta de sus entradas.
- Organizador : alta/edición/baja de eventos y sectores, consulta de ventas
                y cambio de estado de las órdenes (ENTREGADO / CANCELADO).
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class EsOrganizador(BasePermission):
    """Acceso solo para usuarios autenticados con rol Organizador."""

    message = 'Se requiere rol Organizador para realizar esta operación.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'es_organizador', False))


class EsEspectador(BasePermission):
    """Acceso solo para usuarios autenticados con rol Espectador."""

    message = 'Se requiere rol Espectador para realizar esta operación.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and not getattr(user, 'es_organizador', False))


class LecturaPublicaEscrituraOrganizador(BasePermission):
    """
    Lectura pública para el catálogo; escritura solo con rol Organizador.
    Se combina con get_permissions() en los viewsets del catálogo.
    """

    message = 'Se requiere rol Organizador para modificar el catálogo.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'es_organizador', False))


class EsDuenioOVorganizador(BasePermission):
    """
    Permiso de objeto: el organizador solo puede modificar recursos propios
    (sus eventos y los sectores de sus eventos). El superusuario puede todo.
    """

    message = 'Solo puede modificar recursos de sus propios eventos.'

    def has_object_permission(self, request, view, view_obj):
        # La lectura siempre está permitida (catálogo público).
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        obj = view_obj
        organizador = getattr(obj, 'organizador', None)
        if organizador is None and hasattr(obj, 'evento'):
            organizador = getattr(obj.evento, 'organizador', None)
        if organizador is not None:
            return organizador.pk == user.pk

        comprador = getattr(obj, 'comprador', None)
        if comprador is not None:
            return comprador.pk == user.pk
        return False
