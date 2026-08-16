from negocio.base_modelo import BaseModelo
from data.conexion import ejecutar_sql, consultar_sql

class Publicacion(BaseModelo):
    """
    Representa una Publicación (Actualizada para tu DDL).
    """

    def __init__(self, contenido, usuario_id, id_publicacion=None, fecha=None):
        self.__id = id_publicacion
        self.__contenido = contenido
        self.__fecha = fecha
        self.__usuario_id = usuario_id
        self.__info_autor = None
        self.__conteo_likes = 0

    @property
    def id(self): return self.__id
    @property
    def contenido(self): return self.__contenido
    @property
    def fecha(self): return self.__fecha
    @property
    def usuario_id(self): return self.__usuario_id
    @property
    def info_autor(self): return self.__info_autor
    @property
    def conteo_likes(self): return self.__conteo_likes

    def guardar(self, conn):
        """Guarda una nueva publicación."""
        sql = "INSERT INTO publicaciones (contenido, usuario_id) VALUES (%s, %s)"
        params = (self.__contenido, self.__usuario_id)
        nuevo_id = ejecutar_sql(conn, sql, params)
        if nuevo_id:
            self.__id = nuevo_id
            return True
        return False

    def actualizar(self, conn):
        sql = "UPDATE publicaciones SET contenido = %s WHERE id = %s"
        return ejecutar_sql(conn, sql, (self.__contenido, self.__id)) is not None
    def eliminar(self, conn):
        sql = "DELETE FROM publicaciones WHERE id = %s"
        return ejecutar_sql(conn, sql, (self.__id,)) is not None

    @staticmethod
    def listar_todos(conn):
        sql = """
        SELECT 
            P.id, P.contenido, P.fecha_creacion, P.usuario_id,
            U.nombre, U.correo,
            (SELECT COUNT(*) FROM me_gusta MG WHERE MG.publicacion_id = P.id) AS conteo_likes
        FROM publicaciones P
        JOIN usuarios U ON P.usuario_id = U.id
        WHERE P.estado = 'activo'
        ORDER BY P.fecha_creacion DESC
        """
        filas = consultar_sql(conn, sql)
        publicaciones = []
        for fila in filas:
            pub = Publicacion(
                id_publicacion=fila[0],
                contenido=fila[1],
                fecha=fila[2],
                usuario_id=fila[3]
            )
            pub.__info_autor = f"{fila[4]} ({fila[5]})"
            pub.__conteo_likes = fila[6]
            publicaciones.append(pub)
        return publicaciones

    @staticmethod
    def listar_por_usuario(conn, usuario_id):
        sql = """
        SELECT 
            P.id, P.contenido, P.fecha_creacion, P.usuario_id,
            (SELECT COUNT(*) FROM me_gusta MG WHERE MG.publicacion_id = P.id) AS conteo_likes
        FROM publicaciones P
        WHERE P.usuario_id = %s AND P.estado = 'activo'
        ORDER BY P.fecha_creacion DESC
        """
        params = (usuario_id,)
        filas = consultar_sql(conn, sql, params)
        publicaciones = []
        for fila in filas:
            pub = Publicacion(
                id_publicacion=fila[0],
                contenido=fila[1],
                fecha=fila[2],
                usuario_id=fila[3]
            )
            pub.__conteo_likes = fila[4]
            publicaciones.append(pub)
        return publicaciones

    @staticmethod
    def agregar_comentario(conn, publicacion_id, usuario_id, contenido):
        sql = "INSERT INTO comentarios (publicacion_id, usuario_id, contenido) VALUES (%s, %s, %s)"
        params = (publicacion_id, usuario_id, contenido)
        nuevo_id = ejecutar_sql(conn, sql, params)
        return nuevo_id is not None

    @staticmethod
    def listar_comentarios(conn, publicacion_id):
        sql = """
        SELECT C.id, C.contenido, C.fecha_creacion, U.id AS usuario_id, U.nombre
        FROM comentarios C
        JOIN usuarios U ON C.usuario_id = U.id
        WHERE C.publicacion_id = %s AND C.estado = 'activo'
        ORDER BY C.fecha_creacion ASC
        """
        params = (publicacion_id,)
        filas = consultar_sql(conn, sql, params)
        comentarios = []
        for fila in filas:
            comentarios.append({
                'id': fila[0],
                'contenido': fila[1],
                'fecha': fila[2],
                'usuario_id': fila[3],
                'usuario_nombre': fila[4]
            })
        return comentarios

    @staticmethod
    def eliminar_comentario(conn, comentario_id, usuario_id):
        # Solo el autor del comentario puede eliminarlo
        sql = "DELETE FROM comentarios WHERE id = %s AND usuario_id = %s"
        params = (comentario_id, usuario_id)
        return ejecutar_sql(conn, sql, params) is not None

    @staticmethod
    def buscar_por_id(conn, id_publicacion):
        sql = """
        SELECT 
            P.id, P.contenido, P.fecha_creacion, P.usuario_id,
            U.nombre, U.correo,
            (SELECT COUNT(*) FROM me_gusta MG WHERE MG.publicacion_id = P.id) AS conteo_likes
        FROM publicaciones P
        JOIN usuarios U ON P.usuario_id = U.id
        WHERE P.id = %s AND P.estado = 'activo'
        """
        params = (id_publicacion,)
        filas = consultar_sql(conn, sql, params)
        if not filas:
            return None
        fila = filas[0]
        pub = Publicacion(
            id_publicacion=fila[0],
            contenido=fila[1],
            fecha=fila[2],
            usuario_id=fila[3]
        )
        pub._Publicacion__info_autor = f"{fila[4]} ({fila[5]})"
        pub._Publicacion__conteo_likes = fila[6]
        return pub