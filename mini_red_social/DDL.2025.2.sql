CREATE DATABASE IF NOT EXISTS mini_red_social;
USE mini_red_social;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    contrasena VARCHAR(255) NOT NULL,
    estado VARCHAR(20) DEFAULT 'activo',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS amistades (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id1 INT NOT NULL,
    usuario_id2 INT NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente',
    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_aceptacion TIMESTAMP NULL,
    FOREIGN KEY (usuario_id1) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id2) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY unique_amistad (usuario_id1, usuario_id2)
);

CREATE TABLE IF NOT EXISTS publicaciones (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT NOT NULL,
    contenido TEXT NOT NULL,
    estado VARCHAR(20) DEFAULT 'activo',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS me_gusta (
    id INT PRIMARY KEY AUTO_INCREMENT,
    publicacion_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (publicacion_id) REFERENCES publicaciones(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY unique_me_gusta (publicacion_id, usuario_id)
);

CREATE TABLE IF NOT EXISTS comentarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    publicacion_id INT NOT NULL,
    usuario_id INT NOT NULL,
    contenido TEXT NOT NULL,
    estado VARCHAR(20) DEFAULT 'activo',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (publicacion_id) REFERENCES publicaciones(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mensajes_privados (
    id INT PRIMARY KEY AUTO_INCREMENT,
    emisor_id INT NOT NULL,
    receptor_id INT NOT NULL,
    contenido TEXT NOT NULL,
    estado VARCHAR(20) DEFAULT 'activo',
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (emisor_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (receptor_id) REFERENCES usuarios(id) ON DELETE CASCADE
);