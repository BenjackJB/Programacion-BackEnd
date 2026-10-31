"""
Control de acceso por rol de usuario.

El rol vive en el modelo Perfil (OneToOne con User). Estas utilidades se usan
tanto en las vistas web (decorador ``roles_required`` que dispara el manejador
403 de Django) como en la API DRF (``user_tiene_rol`` + Response 403).

Regla de negocio Dulce Arte:
  * Kanban (ver tablero y mover pedidos)  → cocina o administración
  * Confirmar entrega de despachos        → despacho o administración
  * El resto de los módulos               → cualquier usuario autenticado
"""
from functools import wraps

from django.core.exceptions import PermissionDenied

from core.models import Perfil

ADMIN = Perfil.Rol.ADMIN
COCINA = Perfil.Rol.COCINA
DESPACHO = Perfil.Rol.DESPACHO
VENTA = Perfil.Rol.VENTA


def rol_de(user) -> str:
    """Rol del usuario; si no tiene perfil se asume VENTA (el más restrictivo)."""
    perfil = getattr(user, "perfil", None) if user is not None else None
    return perfil.rol if perfil else Perfil.Rol.VENTA


def user_tiene_rol(user, *roles: str) -> bool:
    """True si el usuario está autenticado y su rol está en la lista indicada."""
    if user is None or not user.is_authenticated:
        return False
    return rol_de(user) in roles


def roles_required(*roles: str):
    """
    Restringe una vista a los roles indicados.

    Usar SIEMPRE debajo de @login_required (así los usuarios sin sesión
    son redirigidos al login y los autenticados sin rol reciben 403).
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not user_tiene_rol(request.user, *roles):
                raise PermissionDenied(
                    "Esta sección requiere un rol autorizado."
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
