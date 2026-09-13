# Prompts utilizados con Inteligencia Artificial

**Proyecto:** academic_project - Sistema de Gestión Académica
**Herramientas IA:** GitHub Copilot, Claude 3.5 Sonnet
**Fecha:** 2024

---

## 1. Diseño de Modelos (models.py)

### Prompt:
```
Diseña modelos Django para un sistema académico con las siguientes entidades:
- Teacher (id, first_name, last_name)
- Course (id, name, teacher_id FK)
- Student (id, first_name, last_name)
- StudentCourse (student_id FK, course_id FK) - tabla intermedia Many-to-Many con PK compuesta

REQUISITOS ESTRICTOS:
1. Borrado lógico (soft delete) - NO eliminar registros físicamente, usar campo 'activo' Boolean
2. Modelo base abstracto con campos: id, activo, fecha_creacion, fecha_actualizacion
3. Managers personalizados: objects (solo activos), all_objects (todos), inactive_objects
4. StudentCourse SIN campo id propio - PK compuesta (student_id, course_id)
5. Código comentado por bloques explicando cada sección
6. Sobrescribir delete() para forzar soft delete siempre
```

### Respuesta IA (resumen):
- Creó clase `BaseModel` abstracta con managers personalizados
- Implementó `ActiveManager`, `InactiveManager`
- Modelos Teacher, Course, Student heredando de BaseModel
- StudentCourse sin heredar de BaseModel, con `primary_key=True` en ambos FK
- Métodos `soft_delete()`, `restore()`, `delete()` sobrescrito
- Validaciones en `clean()` y `save()`

---

## 2. Migración Inicial (0001_initial.py)

### Prompt:
```
Genera la migración Django inicial para los modelos anteriores.
IMPORTANTE: StudentCourse debe tener PK compuesta (student_id, course_id) sin columna id.
Usa primary_key=True en ambos ForeignKey y serialize=False.
Incluye UniqueConstraint explícito para claridad.
```

### Respuesta IA:
- Migración con CreateModel para Teacher, Student, Course
- StudentCourse con dos ForeignKey con `primary_key=True, serialize=False`
- AddConstraint con UniqueConstraint en (student, course)

---

## 3. Serializers DRF (serializers.py)

### Prompt:
```
Crea serializers DRF para los modelos:
- TeacherSerializer: con full_name (computed) y courses_count
- CourseSerializer: teacher anidado (lectura), teacher_id (escritura), students_count
- StudentSerializer: full_name (computed), courses_count
- StudentCourseSerializer: PK compuesta - sin campo 'id', student/course anidados (lectura), student_id/course_id (escritura)
- Validación: evitar inscripciones duplicadas activas
- Serializers optimizados para listados: CourseListSerializer, StudentListSerializer
```

### Respuesta IA:
- ModelSerializer para cada entidad
- Campos `source` para propiedades computadas
- `PrimaryKeyRelatedField` con `source` para escritura
- Validación personalizada en `validate()`
- `create()` y `update()` manejando PK compuesta

---

## 4. Views y ViewSets (views.py)

### Prompt:
```
Implementa vistas Django:
1. CBV para HTML templates: LoginView, LogoutView, TemplateView para courses.html y students.html
2. ViewSets DRF para API REST completa (CRUD) en Teacher, Course, Student, StudentCourse
3. Permisos: Solo superusuario puede escribir (POST/PUT/PATCH/DELETE), usuarios autenticados solo lectura
4. Borrado lógico en perform_destroy() llamando soft_delete()
5. Acción custom 'restore' para reactivar
6. StudentCourseViewSet con lookup por PK compuesta (student_id, course_id)
7. Renderizado de templates con contexto para fetch() en JavaScript
```

### Respuesta IA:
- CustomLoginView, CustomLogoutView extendiendo auth views
- BaseTemplateView con LoginRequiredMixin
- CoursesView, StudentsView pasando api_endpoint al contexto
- ViewSets con permission_classes personalizadas
- get_object() sobrescrito para PK compuesta en StudentCourse
- Filtros SearchFilter, OrderingFilter

---

## 5. URLs (urls.py)

### Prompt:
```
Configura URLs:
- Router DRF para ViewSets (teachers, courses, students, enrollments)
- Rutas HTML: login, logout, courses, students, home (redirect a courses)
- Ruta explícita para StudentCourse detail con PK compuesta: /api/enrollments/<student_id>/<course_id>/
- Evitar error 404 en ruta raíz "/"
```

### Respuesta IA:
- DefaultRouter para ViewSets estándar
- path() explícito para composite PK en enrollments
- RedirectView para raíz
- Include de router.urls bajo /api/

---

## 6. Templates Bootstrap (base.html, login.html, courses.html, students.html)

### Prompt para base.html:
```
Crea template base.html con Bootstrap 5 CDN:
- Navbar superior con brand, user dropdown, logout
- Sidebar lateral con navegación: Cursos, Estudiantes, Admin (solo superuser)
- Main content area con messages framework
- CSS custom: variables de color, cards, tablas, loading overlay, empty state
- Responsive: sidebar colapsable en móvil
- Bloques: title, extra_css, content, extra_js
```

### Respuesta IA:
- HTML5 semántico con Bootstrap 5.3.2 + Bootstrap Icons
- Navbar gradient oscuro, sidebar gradient
- Cards sin bordes con shadow hover
- Tablas con hover, badges de estado
- Loading spinner overlay absoluto
- Empty state con iconos Bootstrap

### Prompt para login.html:
```
Template login.html extendiendo base.html:
- Card centrada con formulario login
- Campos username/password con iconos Bootstrap
- Manejo de errores de formulario
- Botón submit con icono
- Nota con credenciales superusuario: profe / 123456
```

### Respuesta IA:
- Formulario POST con CSRF
- Renderizado manual de campos para agregar iconos
- Alert para non_field_errors
- Credenciales en text-muted

### Prompt para courses.html:
```
Template courses.html extendiendo base.html:
- Header con título y botón "Nuevo Curso" (solo superuser, link a admin)
- Tabla Bootstrap: ID, Curso, Docente, Estado (badge)
- JavaScript fetch() asíncrono a /api/courses/ al cargar
- Renderizado dinámico de filas en tbody
- Loading spinner, empty state, manejo de errores 401 (redirect login)
- Formateo de fechas locale es-CL
```

### Respuesta IA:
- fetch() con credentials: 'same-origin'
- Manejo respuesta paginada DRF (data.results)
- renderCourseRow() crea tr con innerHTML
- Badges dinámicos para estado activo/inactivo
- Contador actualizado en badge header

### Prompt para students.html:
```
Template students.html similar a courses.html:
- Tabla: ID, Estudiante, Cursos Inscritos (badge con count), Estado
- JavaScript fetch() a /api/students/
- Mismo patrón: loading, empty, error handling
```

### Respuesta IA:
- Estructura idéntica a courses.html
- courses_count desde serializer
- Badge verde para cursos inscritos

---

## 7. Seed Data (seed_data.py)

### Prompt:
```
Script seed_data.py standalone para poblar BD:
- Datos JSON hardcodeados: 8 teachers, 10 courses, 15 students, 45 enrollments
- Funciones modulares: load_teachers, load_courses, load_students, load_enrollments
- get_or_create para idempotencia
- Exportar datos cargados a seed_data.json con timestamp
- Configuración Django standalone (setup settings)
- Imprimir resumen final con conteos
```

### Respuesta IA:
- Arrays JSON para cada entidad
- ENROLLMENTS_JSON como tuplas (student_idx, course_idx)
- Funciones con print status (✓, ⏭)
- Exportación JSON con estructura completa
- Bloque try/except con traceback

---

## 8. Admin (admin.py)

### Prompt:
```
Admin Django para todos los modelos:
- Base SoftDeleteAdmin con actions: desactivar/restaurar seleccionados
- get_queryset usando all_objects (ver inactivos)
- TeacherAdmin: full_name, courses_count en list_display
- CourseAdmin: teacher raw_id, students_count
- StudentAdmin: full_name, courses_count
- StudentCourseAdmin: raw_id student/course, readonly PK compuesta
- Filtros por activo, búsqueda por nombres
```

### Respuesta IA:
- SoftDeleteAdmin con actions personalizadas
- readonly_fields para timestamps y PK compuesta
- list_display con propiedades computadas
- raw_id_fields para FK grandes
- search_fields en nombres

---

## 9. Tests (tests.py)

### Prompt:
```
Tests unitarios completos:
- Model tests: creation, str, properties, soft_delete, restore, PK compuesta
- Serializer tests: fields, nested, computed, no_id_field
- API tests: CRUD endpoints, auth, permissions, composite PK retrieve
- HTML views tests: login accessible, protected views, templates, redirect root
- Permissions tests: superuser write, normal read-only, unauth denied
- SoftDeleteIntegrationTest: cascade, visibility filters
- APITestCase para DRF, TestCase para Django
```

### Respuesta IA:
- 6 clases de test cubriendo todo
- setUp con datos de prueba
- Assertions de status codes, templates, conteos
- Tests de permisos diferenciados
- Integración de borrado lógico

---

## 10. Configuración Settings (settings.py)

### Prompt:
```
settings.py para academic_project:
- INSTALLED_APPS: django.contrib.*, rest_framework, academic
- TEMPLATES DIRS: BASE_DIR / 'templates'
- DATABASES: SQLite db.sqlite3
- REST_FRAMEWORK: IsAuthenticated default, pagination 20
- LANGUAGE_CODE: es-cl, TIME_ZONE: America/Santiago
- LOGIN_URL, LOGIN_REDIRECT_URL, LOGOUT_REDIRECT_URL
- STATICFILES_DIRS
```

### Respuesta IA:
- Configuración completa lista para producción
- REST_FRAMEWORK con permisos y paginación
- Timezone Chile, idioma español
- Redirects de auth

---

## 11. Permissions (permissions.py)

### Prompt:
```
Permisos DRF personalizados:
- IsSuperUserOrReadOnly: superuser write, authenticated read
- AcademicPermission: authenticated required, superuser full, normal read-only
- CanManageTeachers/Courses/Students/Enrollments: solo superuser
- BasePermission subclasses con has_permission/has_object_permission
```

### Respuesta IA:
- 5 clases de permisos granulares
- Usadas en ViewSets via permission_classes
- SAFE_METHODS para lectura

---

## Resumen de Archivos Generados con IA

| Archivo | Prompts Principales |
|---------|---------------------|
| models.py | 1 (diseño completo) |
| migrations/0001_initial.py | 1 (migración PK compuesta) |
| serializers.py | 1 (serializers + validación) |
| views.py | 1 (CBV + ViewSets + PK compuesta) |
| urls.py | 1 (router + composite PK route) |
| templates/base.html | 1 (layout Bootstrap) |
| templates/login.html | 1 (form login) |
| templates/courses.html | 1 (tabla + fetch JS) |
| templates/students.html | 1 (tabla + fetch JS) |
| seed_data.py | 1 (datos + export JSON) |
| admin.py | 1 (admin + actions) |
| tests.py | 1 (suite completa) |
| settings.py | 1 (configuración) |
| permissions.py | 1 (permisos DRF) |

**Total: ~14 prompts principales** para generar todo el proyecto.