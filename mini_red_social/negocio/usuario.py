from negocio.base_modelo import BaseModelo
from data.conexion import ejecutar_sql, consultar_sql
import getpass

class Usuario(BaseModelo):
    """
    Representa a un Usuario (Actualizado para tu DDL con contraseña).
    """
    
    def __init__(self, nombre, email, contrasena, id_usuario=None):
        self.__id = id_usuario
        self.__nombre = nombre
        self.__email = email
        self.__contrasena = contrasena

    @property
    def id(self):
        return self.__id

    @property
    def nombre(self):
        return self.__nombre

    @property
    def email(self):
        return self.__email

    def guardar(self, conn):
        sql = "INSERT INTO usuarios (nombre, correo, contrasena) VALUES (%s, %s, %s)"
        params = (self.__nombre, self.__email, self.__contrasena)
        nuevo_id = ejecutar_sql(conn, sql, params)
        if nuevo_id:
            self.__id = nuevo_id
            return True
        return False

    def actualizar(self, conn):
        sql = "UPDATE usuarios SET nombre = %s, correo = %s, contrasena = %s WHERE id = %s"
        params = (self.__nombre, self.__email, self.__contrasena, self.__id)
        return ejecutar_sql(conn, sql, params) is not None

    def eliminar(self, conn):
        sql = "DELETE FROM usuarios WHERE id = %s"
        return ejecutar_sql(conn, sql, (self.__id,)) is not None

    @staticmethod
    def listar_todos(conn):
        sql = "SELECT id, nombre, correo, contrasena FROM usuarios WHERE estado = 'activo'"
        filas = consultar_sql(conn, sql)
        usuarios = []
        for fila in filas:
            usuarios.append(Usuario(id_usuario=fila[0], nombre=fila[1], email=fila[2], contrasena=fila[3]))
        return usuarios

    @staticmethod
    def buscar_para_login(conn, nombre, contrasena):
        sql = "SELECT id, nombre, correo, contrasena FROM usuarios WHERE nombre = %s AND contrasena = %s AND estado = 'activo'"
        params = (nombre, contrasena)
        filas = consultar_sql(conn, sql, params)
        if filas:
            fila = filas[0]
            return Usuario(id_usuario=fila[0], nombre=fila[1], email=fila[2], contrasena=fila[3])
        return None

    @staticmethod
    def buscar_por_nombre(conn, nombre):
        sql = "SELECT id, nombre, correo, contrasena FROM usuarios WHERE nombre = %s AND estado = 'activo'"
        params = (nombre,)
        filas = consultar_sql(conn, sql, params)
        if filas:
            fila = filas[0]
            return Usuario(id_usuario=fila[0], nombre=fila[1], email=fila[2], contrasena=fila[3])
        return None

    def crear_publicacion(self, conn, contenido):
        pub = Publicacion(contenido=contenido, usuario_id=self.__id)
        return pub.guardar(conn)

    def agregar_amigo(self, conn, id_amigo):
        id_1 = min(self.__id, id_amigo)
        id_2 = max(self.__id, id_amigo)
        sql = "INSERT INTO amistades (usuario_id1, usuario_id2) VALUES (%s, %s)"
        params = (id_1, id_2)
        return ejecutar_sql(conn, sql, params) is not None

    def dar_like(self, conn, id_publicacion):
        sql = "INSERT INTO me_gusta (usuario_id, publicacion_id) VALUES (%s, %s)"
        params = (self.__id, id_publicacion)
        return ejecutar_sql(conn, sql, params) is not None

    def ver_amigos(self, conn):
        sql = """
        SELECT U.id, U.nombre, U.correo, U.contrasena
    FROM usuarios U
    JOIN amistades A ON U.id = A.usuario_id2
    WHERE A.usuario_id1 = %s
        UNION
        SELECT U.id, U.nombre, U.correo, U.contrasena
    FROM usuarios U
    JOIN amistades A ON U.id = A.usuario_id1
    WHERE A.usuario_id2 = %s
        """
        params = (self.__id, self.__id)
        filas = consultar_sql(conn, sql, params)
        amigos = []
        for fila in filas:
            amigos.append(Usuario(id_usuario=fila[0], nombre=fila[1], email=fila[2], contrasena=fila[3]))
        return amigos

    @staticmethod
    def buscar_por_email(conn, email):
        sql = "SELECT id, nombre, correo, contrasena FROM usuarios WHERE correo = %s AND estado = 'activo'"
        params = (email,)
        filas = consultar_sql(conn, sql, params)
        if filas:
            fila = filas[0]
            return Usuario(id_usuario=fila[0], nombre=fila[1], email=fila[2], contrasena=fila[3])
        return None

    def actualizar_nombre(self, conn, nuevo_nombre):
        sql = "UPDATE usuarios SET nombre = %s WHERE id = %s"
        params = (nuevo_nombre, self.__id)
        actualizado = ejecutar_sql(conn, sql, params) is not None
        if actualizado:
            self.__nombre = nuevo_nombre
        return actualizado

    def eliminar_amigo(self, conn, id_amigo):
        """Elimina una amistad entre este usuario y otro (si existe)."""
        id_1 = min(self.__id, id_amigo)
        id_2 = max(self.__id, id_amigo)
        sql = "DELETE FROM amistades WHERE usuario_id1 = %s AND usuario_id2 = %s"
        params = (id_1, id_2)
        return ejecutar_sql(conn, sql, params) is not None

    def eliminar_like(self, conn, id_publicacion):
        """Elimina el 'me gusta' del usuario sobre una publicación (si existe)."""
        sql = "DELETE FROM me_gusta WHERE usuario_id = %s AND publicacion_id = %s"
        params = (self.__id, id_publicacion)
        return ejecutar_sql(conn, sql, params) is not None

    def enviar_mensaje_privado(self, conn, receptor_id, contenido):
        sql = "INSERT INTO mensajes_privados (emisor_id, receptor_id, contenido) VALUES (%s, %s, %s)"
        params = (self.__id, receptor_id, contenido)
        nuevo_id = ejecutar_sql(conn, sql, params)
        return nuevo_id is not None

    @staticmethod
    def listar_mensajes_recibidos(conn, usuario_id):
        sql = """
        SELECT M.id, M.contenido, M.fecha_envio, E.id AS emisor_id, E.nombre AS emisor_nombre
        FROM mensajes_privados M
        JOIN usuarios E ON M.emisor_id = E.id
        WHERE M.receptor_id = %s AND M.estado = 'activo'
        ORDER BY M.fecha_envio DESC
        """
        params = (usuario_id,)
        filas = consultar_sql(conn, sql, params)
        mensajes = []
        for fila in filas:
            mensajes.append({
                'id': fila[0],
                'contenido': fila[1],
                'fecha': fila[2],
                'emisor_id': fila[3],
                'emisor_nombre': fila[4]
            })
        return mensajes

from negocio.publicacion import Publicacion