"""Context processors globales."""


def rol_usuario(request):
    """Expone el rol del usuario autenticado a todas las plantillas.

    Permite mostrar u ocultar elementos de navegación según el rol
    (p. ej. el tablero Kanban solo se muestra a cocina/administración).
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from core.decorators import rol_de

        return {"user_rol": rol_de(user)}
    return {"user_rol": ""}
