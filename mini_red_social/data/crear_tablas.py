from data.conexion import crear_conexion
from auxiliares.mensajes import mostrar_error, mostrar_info

def crear_tablas_iniciales():
    """
    Crea las tablas necesarias para la red social si no existen.
    Esto refleja la estructura de clases (Criterio 2.1.1.1).
    """
    sql_tabla_usuarios = """
    CREATE TABLE IF NOT EXISTS Usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE
    );
    """

    sql_tabla_publicaciones = """
    CREATE TABLE IF NOT EXISTS Publicaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contenido TEXT NOT NULL,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        usuario_id INTEGER NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES Usuarios (id)
    );
    """

    sql_tabla_amistades = """
    CREATE TABLE IF NOT EXISTS amistades (
        id INT PRIMARY KEY AUTO_INCREMENT,
        usuario_id1 INT NOT NULL,
        usuario_id2 INT NOT NULL,
        estado VARCHAR(20) DEFAULT 'pendiente',
        fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fecha_aceptacion TIMESTAMP NULL,
        FOREIGN KEY (usuario_id1) REFERENCES usuarios (id) ON DELETE CASCADE,
        FOREIGN KEY (usuario_id2) REFERENCES usuarios (id) ON DELETE CASCADE,
        UNIQUE KEY unique_amistad (usuario_id1, usuario_id2)
    );
    """

    sql_tabla_likes = """
    CREATE TABLE IF NOT EXISTS Likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        publicacion_id INTEGER NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES Usuarios (id),
        FOREIGN KEY (publicacion_id) REFERENCES Publicaciones (id),
        UNIQUE(usuario_id, publicacion_id)
    );
    """

    conn = crear_conexion()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute(sql_tabla_usuarios)
            c.execute(sql_tabla_publicaciones)
            c.execute(sql_tabla_amistades)
            c.execute(sql_tabla_likes)
            conn.commit()
            mostrar_info("Tablas verificadas/creadas correctamente.")
        except Exception as e:
            mostrar_error(f"Error al crear las tablas: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
    else:
        mostrar_error("No se pudo establecer conexión para crear las tablas.")