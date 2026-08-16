-- Insertar usuarios de ejemplo
INSERT INTO usuarios (nombre, correo, contrasena) VALUES 
('ana_garcia', 'ana.garcia@email.com', 'contrasena123'),
('carlos_lopez', 'carlos.lopez@email.com', 'contrasena123'),
('maria_rodriguez', 'maria.rodriguez@email.com', 'contrasena123'),
('pedro_martinez', 'pedro.martinez@email.com', 'contrasena123'),
('lucia_fernandez', 'lucia.fernandez@email.com', 'contrasena123');

-- Insertar amistades de ejemplo
INSERT INTO amistades (usuario_id1, usuario_id2, estado, fecha_aceptacion) VALUES 
(1, 2, 'aceptada', NOW()),
(1, 3, 'aceptada', NOW()),
(2, 4, 'aceptada', NOW()),
(3, 5, 'aceptada', NOW());

-- Insertar publicaciones de ejemplo
INSERT INTO publicaciones (usuario_id, contenido) VALUES 
(1, '¡Hola a todos! Esta es mi primera publicación en la red social. ¡Qué emocionante!'),
(2, 'Hoy es un gran día para programar y aprender cosas nuevas. #Desarrollo #Python'),
(3, 'Acabo de terminar de leer un libro increíble. ¿Alguien tiene recomendaciones?'),
(1, 'Compartiendo algunas fotos de mi último viaje. ¡Fue una experiencia maravillosa!'),
(4, 'Reflexión del día: La perseverancia es la clave del éxito. Nunca se rindan.'),
(5, '¡Feliz viernes a todos! ¿Qué planes tienen para el fin de semana?');

-- Insertar me gusta de ejemplo
INSERT INTO me_gusta (publicacion_id, usuario_id) VALUES 
(1, 2), (1, 3), (1, 4),
(2, 1), (2, 3),
(3, 1), (3, 2),
(4, 2), (4, 3), (4, 5),
(5, 1), (5, 3),
(6, 2), (6, 4);

-- Insertar comentarios de ejemplo
INSERT INTO comentarios (publicacion_id, usuario_id, contenido) VALUES 
(1, 2, '¡Bienvenida Ana! Esperamos verte mucho por aquí.'),
(1, 3, 'Me alegra verte en la plataforma. ¡Bienvenida!'),
(2, 1, 'Totalmente de acuerdo, Carlos. ¿En qué estás trabajando?'),
(2, 3, 'Python es genial para el desarrollo. ¡Sigue así!'),
(3, 1, '¿De qué trataba el libro? Me gustaría leerlo.'),
(4, 2, '¡Las fotos se ven increíbles! ¿A dónde fuiste?'),
(5, 3, 'Muy cierta tu reflexión, Pedro. La perseverancia lo es todo.'),
(6, 1, '¡Feliz viernes! Voy a descansar y ver algunas series.');

-- Insertar mensajes privados de ejemplo
INSERT INTO mensajes_privados (emisor_id, receptor_id, contenido) VALUES 
(1, 2, 'Hola Carlos, ¿cómo estás?'),
(2, 1, '¡Hola Ana! Estoy bien, gracias. ¿Y tú?'),
(1, 2, 'Todo excelente. ¿Viste mi última publicación?'),
(3, 1, 'Ana, me encantó tu publicación sobre el viaje.'),
(1, 3, '¡Gracias María! Fue un viaje increíble.');