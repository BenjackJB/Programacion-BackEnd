import mysql.connector
from mysql.connector import Error
from auxiliares.data_conexion import CONFIG_MYSQL
from auxiliares.mensajes import mostrar_error

def crear_conexion():
    """Crea una conexión a la base de datos MySQL."""
    conn = None
    try:
        conn = mysql.connector.connect(**CONFIG_MYSQL)
    except Error as e:
        mostrar_error(f"No se pudo conectar a la base de datos MySQL: {e}")
    return conn

def ejecutar_sql(conn, sql, params=()):
    """Ejecuta una consulta SQL (INSERT, UPDATE, DELETE)."""
    try:
        c = conn.cursor()
        c.execute(sql, params)
        conn.commit()
        return c.lastrowid
    except Error as e:
        mostrar_error(f"SQL: {sql} | params: {params}")
        if e.errno == 1062: 
            if "correo" in e.msg:
                mostrar_error("Error: El correo electrónico ya está registrado.")
            elif "nombre" in e.msg:
                mostrar_error("Error: El nombre de usuario ya existe.")
            elif "unique_amistad" in e.msg:
                mostrar_error("Error: La solicitud de amistad ya existe.")
            elif "unique_me_gusta" in e.msg:
                mostrar_error("Error: Ya le diste 'Me Gusta' a esta publicación.")
            else:
                mostrar_error("Error: Se violó una restricción única.")
        else:
            mostrar_error(f"Error al ejecutar SQL en MySQL: {e}")
        return None

def consultar_sql(conn, sql, params=()):
    """Ejecuta una consulta SQL (SELECT)."""
    try:
        c = conn.cursor(buffered=True)
        c.execute(sql, params)
        return c.fetchall()
    except Error as e:
        mostrar_error(f"Error al consultar SQL en MySQL: {e}")
        return []