import sys
import getpass
from data.conexion import crear_conexion
import auxiliares.mensajes as msj
from negocio.usuario import Usuario
from negocio.publicacion import Publicacion


usuario_actual = None

def manejar_registro(conn):
    """Maneja el registro AHORA CON CONTRASEÑA."""
    msj.mostrar_info("--- Registro de Nuevo Usuario ---")
    try:
        nombre = input("Nombre de usuario: ")
        email = input("Email: ")
        contrasena = getpass.getpass("Contraseña: ")
        contrasena_conf = getpass.getpass("Confirme la contraseña: ")

        if not nombre or not email or not contrasena:
            msj.mostrar_error("Nombre, email y contraseña no pueden estar vacíos.")
            return
        
        if contrasena != contrasena_conf:
            msj.mostrar_error("Las contraseñas no coinciden.")
            return

        nuevo_usuario = Usuario(nombre=nombre, email=email, contrasena=contrasena)
        if nuevo_usuario.guardar(conn):
            msj.mostrar_exito("Usuario registrado correctamente.")
        else:
            msj.mostrar_error("No se pudo registrar al usuario.")
    
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error inesperado: {e}")

def manejar_login(conn):
    """Maneja el inicio de sesión AHORA CON CONTRASEÑA."""
    global usuario_actual
    msj.mostrar_info("--- Iniciar Sesión ---")
    try:
        nombre = input("Nombre de usuario: ")
        contrasena = getpass.getpass("Contraseña: ")
        
        usuario = Usuario.buscar_para_login(conn, nombre, contrasena)
        
        if usuario:
            usuario_actual = usuario
            msj.mostrar_exito(f"Inicio de sesión exitoso como {usuario.nombre}.")
        else:
            msj.mostrar_error("Nombre de usuario o contraseña incorrectos.")
    
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error: {e}")

def manejar_crear_publicacion(conn):
    msj.mostrar_info("--- Nueva Publicación ---")
    try:
        contenido = input("Escribe tu publicación:\n")
        if not contenido:
            msj.mostrar_error("La publicación no puede estar vacía.")
            return
        if usuario_actual.crear_publicacion(conn, contenido):
            msj.mostrar_exito("Publicación creada exitosamente.")
        else:
            msj.mostrar_error("No se pudo crear la publicación.")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error: {e}")

def mostrar_publicaciones(publicaciones):
    """Función auxiliar para imprimir publicaciones."""
    if not publicaciones:
        msj.mostrar_info("No hay publicaciones para mostrar.")
        return
    for pub in publicaciones:
        print("-" * 30)
        if pub.info_autor:
            print(f"De: {pub.info_autor}")
        print(f"ID: {pub.id} | Fecha: {pub.fecha}")
        print(f"Likes: {pub.conteo_likes}")
        print(f"\n{pub.contenido}\n")
    print("-" * 30)

def manejar_ver_mis_publicaciones(conn):
    msj.mostrar_info("--- Mis Publicaciones ---")
    try:
        publicaciones = Publicacion.listar_por_usuario(conn, usuario_actual.id)
        mostrar_publicaciones(publicaciones)
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error: {e}")

def manejar_ver_todas_publicaciones(conn):
    msj.mostrar_info("--- Todas las Publicaciones ---")
    try:
        publicaciones = Publicacion.listar_todos(conn)
        mostrar_publicaciones(publicaciones)
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error: {e}")

def manejar_agregar_amigo(conn):
    """Maneja la SOLICITUD de amistad."""
    msj.mostrar_info("--- Enviar solicitud de amistad ---")
    try:
        nombre_amigo = input("Nombre de usuario del amigo: ")
        if nombre_amigo == usuario_actual.nombre:
            msj.mostrar_error("No puedes agregarte a ti mismo.")
            return

        amigo = Usuario.buscar_por_nombre(conn, nombre_amigo)
        if not amigo:
            msj.mostrar_error("No se encontró ningún usuario con ese nombre.")
            return

        if usuario_actual.agregar_amigo(conn, amigo.id):
            msj.mostrar_exito(f"¡Solicitud de amistad enviada a {amigo.nombre}!")
        else:
            msj.mostrar_error("No se pudo enviar la solicitud.")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error: {e}")

def manejar_ver_amigos(conn):
    """Muestra la lista de amigos (y solicitudes)."""
    msj.mostrar_info("--- Mis Amigos (y Solicitudes) ---")
    try:
        amigos = usuario_actual.ver_amigos(conn)
        if not amigos:
            msj.mostrar_info("Aún no tienes amigos.")
            return
        for amigo in amigos:
            print(f"- {amigo.nombre} ({amigo.email})")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error: {e}")

def manejar_dar_like(conn):
    msj.mostrar_info("--- Dar 'Me Gusta' ---")
    msj.mostrar_info("Puedes ver los IDs en 'Ver todas las publicaciones'.")
    try:
        id_publicacion = int(input("ID de la publicación: "))
        if usuario_actual.dar_like(conn, id_publicacion):
            msj.mostrar_exito("¡'Me Gusta' registrado!")
        else:
            msj.mostrar_error("No se pudo registrar el 'Me Gusta'.")
    except ValueError:
        msj.mostrar_error("Entrada inválida. Debe ser un número (ID).")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error: {e}")


def manejar_borrar_mi_publicacion(conn):
    """Permite al usuario logueado borrar una de sus publicaciones."""
    msj.mostrar_info("--- Borrar mi publicación ---")
    try:
        publicaciones = Publicacion.listar_por_usuario(conn, usuario_actual.id)
        if not publicaciones:
            msj.mostrar_info("No tienes publicaciones para borrar.")
            return
        mostrar_publicaciones(publicaciones)
        try:
            id_pub = int(input("ID de la publicación a borrar: "))
        except ValueError:
            msj.mostrar_error("ID inválido.")
            return

        pub = Publicacion.buscar_por_id(conn, id_pub)
        if not pub:
            msj.mostrar_error("No se encontró la publicación.")
            return
        if pub.usuario_id != usuario_actual.id:
            msj.mostrar_error("No puedes borrar una publicación que no es tuya.")
            return

        confirm = input(f"Confirma eliminar la publicación ID {pub.id}? (s/n): ")
        if confirm.lower() == 's':
            if pub.eliminar(conn):
                msj.mostrar_exito("Publicación eliminada.")
            else:
                msj.mostrar_error("No se pudo eliminar la publicación.")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error al borrar la publicación: {e}")

def manejar_eliminar_amigo(conn):
    """Permite al usuario logueado eliminar (deshacer) una amistad."""
    msj.mostrar_info("--- Eliminar amigo ---")
    try:
        clave = input("Ingrese nombre o email del amigo a eliminar: ")
        amigo = Usuario.buscar_por_email(conn, clave) or Usuario.buscar_por_nombre(conn, clave)
        if not amigo:
            msj.mostrar_error("No se encontró el usuario especificado.")
            return
        if amigo.id == usuario_actual.id:
            msj.mostrar_error("No puedes eliminarte a ti mismo.")
            return

        confirm = input(f"Confirma eliminar la amistad con '{amigo.nombre}'? (s/n): ")
        if confirm.lower() == 's':
            if usuario_actual.eliminar_amigo(conn, amigo.id):
                msj.mostrar_exito("Amigo eliminado correctamente.")
            else:
                msj.mostrar_error("No se pudo eliminar la amistad (tal vez no existía).")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error al eliminar el amigo: {e}")

def manejar_modificar_mi_publicacion(conn):
    """Permite al usuario modificar el contenido de una de sus publicaciones."""
    msj.mostrar_info("--- Modificar mi publicación ---")
    try:
        publicaciones = Publicacion.listar_por_usuario(conn, usuario_actual.id)
        if not publicaciones:
            msj.mostrar_info("No tienes publicaciones para modificar.")
            return
        mostrar_publicaciones(publicaciones)
        try:
            id_pub = int(input("ID de la publicación a modificar: "))
        except ValueError:
            msj.mostrar_error("ID inválido.")
            return
        pub = Publicacion.buscar_por_id(conn, id_pub)
        if not pub:
            msj.mostrar_error("No se encontró la publicación.")
            return
        if pub.usuario_id != usuario_actual.id:
            msj.mostrar_error("No puedes modificar una publicación que no es tuya.")
            return
        nuevo_contenido = input("Nuevo contenido: ")
        if not nuevo_contenido:
            msj.mostrar_error("Contenido vacío.")
            return
        pub = Publicacion(contenido=nuevo_contenido, usuario_id=pub.usuario_id, id_publicacion=pub.id)
        if pub.actualizar(conn):
            msj.mostrar_exito("Publicación actualizada correctamente.")
        else:
            msj.mostrar_error("No se pudo actualizar la publicación.")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error al modificar la publicación: {e}")

def manejar_obtener_publicacion(conn):
    """Muestra los datos completos de una publicación por ID."""
    msj.mostrar_info("--- Obtener publicación por ID ---")
    try:
        try:
            id_pub = int(input("ID de la publicación: "))
        except ValueError:
            msj.mostrar_error("ID inválido.")
            return
        pub = Publicacion.buscar_por_id(conn, id_pub)
        if not pub:
            msj.mostrar_info("Publicación no encontrada.")
            return
        print("-" * 30)
        if pub.info_autor:
            print(f"De: {pub.info_autor}")
        print(f"ID: {pub.id} | Fecha: {pub.fecha}")
        print(f"Likes: {pub.conteo_likes}")
        print(f"\n{pub.contenido}\n")
        print("-" * 30)
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error al obtener la publicación: {e}")

def manejar_quitar_like(conn):
    """Permite al usuario quitar su 'me gusta' de una publicación."""
    msj.mostrar_info("--- Quitar 'Me Gusta' ---")
    try:
        try:
            id_pub = int(input("ID de la publicación: "))
        except ValueError:
            msj.mostrar_error("ID inválido.")
            return
        if usuario_actual.eliminar_like(conn, id_pub):
            msj.mostrar_exito("Se quitó tu 'Me Gusta' de la publicación.")
        else:
            msj.mostrar_error("No se pudo quitar el 'Me Gusta' (quizá no existía).")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error al quitar el 'Me Gusta': {e}")

def manejar_agregar_comentario(conn):
    msj.mostrar_info("--- Agregar comentario ---")
    try:
        try:
            id_pub = int(input("ID de la publicación: "))
        except ValueError:
            msj.mostrar_error("ID inválido.")
            return
        contenido = input("Contenido del comentario: ")
        if not contenido:
            msj.mostrar_error("Comentario vacío.")
            return
        if Publicacion.agregar_comentario(conn, id_pub, usuario_actual.id, contenido):
            msj.mostrar_exito("Comentario agregado.")
        else:
            msj.mostrar_error("No se pudo agregar el comentario.")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error al agregar el comentario: {e}")

def manejar_ver_comentarios(conn):
    msj.mostrar_info("--- Ver comentarios de una publicación ---")
    try:
        try:
            id_pub = int(input("ID de la publicación: "))
        except ValueError:
            msj.mostrar_error("ID inválido.")
            return
        comentarios = Publicacion.listar_comentarios(conn, id_pub)
        if not comentarios:
            msj.mostrar_info("No hay comentarios para esa publicación.")
            return
        for c in comentarios:
            print("-" * 30)
            print(f"ID: {c['id']} | Autor: {c['usuario_nombre']} (ID {c['usuario_id']}) | Fecha: {c['fecha']}")
            print(c['contenido'])
        print("-" * 30)
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error al listar comentarios: {e}")

def manejar_eliminar_comentario(conn):
    msj.mostrar_info("--- Eliminar comentario ---")
    try:
        try:
            id_com = int(input("ID del comentario a eliminar: "))
        except ValueError:
            msj.mostrar_error("ID inválido.")
            return
        if Publicacion.eliminar_comentario(conn, id_com, usuario_actual.id):
            msj.mostrar_exito("Comentario eliminado.")
        else:
            msj.mostrar_error("No se pudo eliminar el comentario (quizá no eres el autor).")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error al eliminar el comentario: {e}")

def manejar_enviar_mensaje_privado(conn):
    msj.mostrar_info("--- Enviar mensaje privado ---")
    try:
        clave = input("Nombre o ID del receptor: ")
        receptor = None
        try:
            id_rec = int(clave)
        except ValueError:
            id_rec = None
        if id_rec:
            usuarios = Usuario.listar_todos(conn)
            for u in usuarios:
                if u.id == id_rec:
                    receptor = u
                    break
        else:
            receptor = Usuario.buscar_por_nombre(conn, clave) or Usuario.buscar_por_email(conn, clave)
        if not receptor:
            msj.mostrar_error("No se encontró el receptor especificado.")
            return
        contenido = input("Contenido del mensaje: ")
        if not contenido:
            msj.mostrar_error("Mensaje vacío.")
            return
        if usuario_actual.enviar_mensaje_privado(conn, receptor.id, contenido):
            msj.mostrar_exito("Mensaje enviado.")
        else:
            msj.mostrar_error("No se pudo enviar el mensaje.")
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error al enviar el mensaje: {e}")

def manejar_ver_mensajes_privados(conn):
    msj.mostrar_info("--- Mensajes privados recibidos ---")
    try:
        mensajes = Usuario.listar_mensajes_recibidos(conn, usuario_actual.id)
        if not mensajes:
            msj.mostrar_info("No tienes mensajes privados.")
            return
        for m in mensajes:
            print("-" * 30)
            print(f"ID: {m['id']} | De: {m['emisor_nombre']} (ID {m['emisor_id']}) | Fecha: {m['fecha']}")
            print(m['contenido'])
        print("-" * 30)
    except Exception as e:
        msj.mostrar_error(f"Ocurrió un error al listar mensajes privados: {e}")

def menu_usuario_logueado(conn):
    global usuario_actual
    while True:
        opcion = msj.mostrar_menu_usuario(usuario_actual.nombre)
        if opcion == '1':
            manejar_crear_publicacion(conn)
        elif opcion == '2':
            manejar_ver_mis_publicaciones(conn)
        elif opcion == '3':
            manejar_ver_todas_publicaciones(conn)
        elif opcion == '4':
            manejar_agregar_amigo(conn)
        elif opcion == '5':
            manejar_ver_amigos(conn)
        elif opcion == '6':
            manejar_dar_like(conn)
        elif opcion == '7':
            manejar_agregar_comentario(conn)
        elif opcion == '8':
            manejar_ver_comentarios(conn)
        elif opcion == '9':
            manejar_eliminar_comentario(conn)
        elif opcion == '10':
            manejar_borrar_mi_publicacion(conn)
        elif opcion == '11':
            manejar_eliminar_amigo(conn)
        elif opcion == '12':
            manejar_quitar_like(conn)
        elif opcion == '13':
            manejar_enviar_mensaje_privado(conn)
        elif opcion == '14':
            manejar_ver_mensajes_privados(conn)
        elif opcion == '15':
            msj.mostrar_info(f"Sesión cerrada. ¡Hasta pronto, {usuario_actual.nombre}!")
            usuario_actual = None
            break
        else:
            msj.mostrar_error("Opción no válida.")

def menu_principal():
    conn = crear_conexion()
    if conn is None:
        msj.mostrar_error("FALLO CRÍTICO: No se puede conectar a la base de datos.")
        sys.exit(1)

    
    

    while True:
        if usuario_actual:
            menu_usuario_logueado(conn)
        else:
            opcion = msj.mostrar_menu_principal()
            if opcion == '1':
                manejar_registro(conn)
            elif opcion == '2':
                manejar_login(conn)
            elif opcion == '3':
                msj.mostrar_info("Saliendo de la Mini Red Social.")
                break
            else:
                msj.mostrar_error("Opción no válida.")
    
    if conn:
        conn.close()

if __name__ == "__main__":
    menu_principal()