def mostrar_menu_principal():
    """Muestra el menú principal de la red social."""
    print("\n--- MINI RED SOCIAL ---")
    print("1. Registrar nuevo usuario")
    print("2. Iniciar sesión")
    print("3. Salir")
    return input("Seleccione una opción: ")

def mostrar_menu_usuario(nombre_usuario):
    """Muestra el menú de acciones para un usuario que ha iniciado sesión."""
    print(f"\n--- Bienvenido, {nombre_usuario} ---")
    print("1. Crear una nueva publicación")
    print("2. Ver mis publicaciones")
    print("3. Ver todas las publicaciones")
    print("4. Agregar un amigo")
    print("5. Ver mis amigos")
    print("6. Dar 'Me Gusta' a una publicación")
    print("7. Agregar comentario a una publicación")
    print("8. Ver comentarios de una publicación")
    print("9. Eliminar comentario")
    print("10. Borrar una de mis publicaciones")
    print("11. Eliminar un amigo")
    print("12. Quitar mi 'Me Gusta' de una publicación")
    print("13. Enviar mensaje privado")
    print("14. Ver mensajes privados")
    print("15. Cerrar sesión")
    return input("Seleccione una opción: ")

def mostrar_error(mensaje):
    """Muestra un mensaje de error."""
    print(f"[ERROR] {mensaje}")

def mostrar_exito(mensaje):
    """Muestra un mensaje de éxito."""
    print(f"[ÉXITO] {mensaje}")

def mostrar_info(mensaje):
    """Muestra un mensaje informativo."""
    print(f"[INFO] {mensaje}")