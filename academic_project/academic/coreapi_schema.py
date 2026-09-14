"""
Esquema CoreAPI de la API Académica.

Documentación PARALELA a drf-spectacular (/api/schema/ y /docs/). Se sirve un
documento en formato CoreAPI / CoreJSON en /api/coreapi/, legible por
coreapi.Client (coreapi 2.3.3) y herramientas compatibles.

Este módulo NO modifica ningún endpoint existente: solo añade una ruta de
documentación. El esquema se construye manualmente con coreapi.Document porque
DRF 3.15 dejó de incluir soporte CoreAPI y el generador deprecado de CoreAPI
exige get_schema_fields() en los filter backends (que django-filter 26.1 ya no
implementa, causa de los errores 500 anteriores).

Consumo:
    import coreapi
    client = coreapi.Client()
    schema = client.get('http://127.0.0.1:8000/api/coreapi/')
"""

from django.http import HttpResponse

from coreapi import Document, Field, Link
from coreapi.codecs import CoreJSONCodec


def _field(name, required=True, location='form', description=''):
    """Helper para crear un Field de CoreAPI."""
    return Field(name, required=required, location=location, description=description)


def _resource(prefix, write_fields, read_fields=None, filters=None):
    """
    Genera los endpoints CRUD + restore de un recurso del router.

    - prefix: nombre del recurso (p.ej. 'teachers') para la documentación.
    - write_fields: campos a enviar para crear/actualizar.
    - read_fields: campos mostrados en la respuesta (opcional, informativo).
    - filters: parámetros query de filtrado/búsqueda/listado.
    """
    base = f'/api/{prefix}/'
    detail = f'/api/{prefix}/{{id}}/'
    list_query_fields = [
        _field(name, required=False, location='query', description=f'Filtro {name}')
        for name in (filters or [])
    ]
    return {
        'list': Link(
            url=base,
            action='get',
            fields=list_query_fields,
            description=(
                f'Lista de {prefix}. '
                f'Campos por entidad: {", ".join(read_fields) if read_fields else "-"}'
            ),
        ),
        'create': Link(
            url=base,
            action='post',
            fields=write_fields,
            description=f'Crea un {prefix}.',
        ),
        'read': Link(
            url=detail,
            action='get',
            fields=[_field('id', description='ID del registro', location='path')],
            description=f'Detalle (GET) de un {prefix}.',
        ),
        'update': Link(
            url=detail,
            action='put',
            fields=[_field('id', description='ID del registro', location='path')] + write_fields,
            description=f'Actualiza completamente un {prefix}.',
        ),
        'partial_update': Link(
            url=detail,
            action='patch',
            fields=[_field('id', description='ID del registro', location='path')],
            description=f'Actualiza parcialmente un {prefix}.',
        ),
        'delete': Link(
            url=detail,
            action='delete',
            fields=[_field('id', description='ID del registro', location='path')],
            description=f'Elimina (borrado lógico) un {prefix}.',
        ),
        'restore': Link(
            url=detail + 'restore/',
            action='post',
            fields=[_field('id', description='ID del registro', location='path')],
            description=f'Restaura un {prefix} inactivo (solo superusuario).',
        ),
    }


def _build_schema():
    """Construye el Documento CoreAPI con todas las rutas de la API."""
    teacher_fields = [
        _field('first_name', description='Nombre'),
        _field('last_name', description='Apellido'),
        _field('sexo', required=False, description='M=Masculino, F=Femenino, O=Otro'),
        _field('activo', required=False, description='Activo (borrado lógico)'),
    ]
    course_fields = [
        _field('name', description='Nombre del curso'),
        _field('teacher_id', description='ID del docente asignado'),
        _field('jornada', required=False, description='D=Diurna, V=Vespertina'),
        _field('activo', required=False, description='Activo (borrado lógico)'),
    ]
    student_fields = [
        _field('first_name', description='Nombre'),
        _field('last_name', description='Apellido'),
        _field('sexo', required=False, description='M=Masculino, F=Femenino, O=Otro'),
        _field('jornada', required=False, description='D=Diurna, V=Vespertina'),
        _field('activo', required=False, description='Activo (borrado lógico)'),
    ]
    enrollment_fields = [
        _field('student_id', description='ID del estudiante'),
        _field('course_id', description='ID del curso'),
        _field('activo', required=False, description='Activo (borrado lógico)'),
    ]
    asignatura_fields = [
        _field('codigo', required=False, description='Código de la asignatura'),
        _field('nombre', description='Nombre de la asignatura'),
        _field('descripcion', required=False, description='Descripción'),
        _field('creditos', required=False, description='Créditos'),
        _field('tipo', required=False, description='O=Obligatoria, E=Electiva'),
        _field('nivel', required=False, description='1..5 (año)'),
        _field('activo', required=False, description='Activo (borrado lógico)'),
    ]
    enrollment_detail = '/api/enrollments/{student_id}/{course_id}/'

    return Document(
        url='/api/coreapi/',
        title='API Académica - Esquema CoreAPI',
        description=(
            'Documentación paralela de la API REST (drf-spectacular sigue en /api/schema/ y /docs/). '
            'Asignatura: lectura pública y escritura con JWT. Cursos, Docentes, Estudiantes e '
            'Inscripciones: CRUD completo requiere JWT. La raiz /api/ requiere superusuario.'
        ),
        content={
            'token': {
                'obtain': Link(
                    url='/api/token/', action='post',
                    description='Obtiene un par de tokens JWT (cualquier usuario con credenciales válidas).',
                    fields=[_field('username'), _field('password')],
                ),
                'refresh': Link(
                    url='/api/token/refresh/', action='post',
                    description='Renueva el access token a partir del refresh token.',
                    fields=[_field('refresh')],
                ),
                'verify': Link(
                    url='/api/token/verify/', action='post',
                    description='Verifica que un access token sea válido.',
                    fields=[_field('token')],
                ),
                'blacklist': Link(
                    url='/api/token/blacklist/', action='post',
                    description='Invalida (bloquea) un refresh token.',
                    fields=[_field('refresh')],
                ),
            },
            'teachers': _resource(
                'teachers', teacher_fields,
                read_fields=['id', 'first_name', 'last_name', 'full_name', 'sexo', 'courses_count', 'activo', 'fecha_creacion'],
                filters=['activo', 'sexo', 'search', 'ordering', 'page'],
            ),
            'courses': _resource(
                'courses', course_fields,
                read_fields=['id', 'name', 'teacher', 'jornada', 'students_count', 'students', 'activo', 'fecha_creacion'],
                filters=['activo', 'jornada', 'teacher', 'search', 'ordering', 'page'],
            ),
            'students': _resource(
                'students', student_fields,
                read_fields=['id', 'first_name', 'last_name', 'full_name', 'sexo', 'jornada', 'courses_count', 'activo', 'fecha_creacion'],
                filters=['activo', 'sexo', 'jornada', 'search', 'ordering', 'page'],
            ),
            'asignaturas': _resource(
                'asignaturas', asignatura_fields,
                read_fields=['id', 'codigo', 'nombre', 'descripcion', 'creditos', 'tipo', 'nivel', 'activo', 'fecha_creacion'],
                filters=['activo', 'tipo', 'nivel', 'search', 'ordering', 'page'],
            ),
            'enrollments': {
                'list': Link(
                    url='/api/enrollments/',
                    action='get',
                    fields=[
                        _field('student', required=False, location='query', description='Filtro por estudiante'),
                        _field('course', required=False, location='query', description='Filtro por curso'),
                        _field('activo', required=False, location='query', description='Filtro por estado'),
                        _field('search', required=False, location='query', description='Búsqueda'),
                        _field('ordering', required=False, location='query', description='Orden'),
                        _field('page', required=False, location='query', description='Página'),
                    ],
                    description='Lista de inscripciones.',
                ),
                'create': Link(
                    url='/api/enrollments/',
                    action='post',
                    fields=enrollment_fields,
                    description='Inscribe a un estudiante en un curso.',
                ),
                'read': Link(
                    url=enrollment_detail,
                    action='get',
                    fields=[
                        _field('student_id', location='path', description='ID del estudiante'),
                        _field('course_id', location='path', description='ID del curso'),
                    ],
                    description='Detalle de inscripción (PK compuesta estudiante+curso).',
                ),
                'update': Link(
                    url=enrollment_detail,
                    action='put',
                    fields=[
                        _field('student_id', location='path', description='ID del estudiante'),
                        _field('course_id', location='path', description='ID del curso'),
                    ] + enrollment_fields,
                    description='Actualiza una inscripción.',
                ),
                'partial_update': Link(
                    url=enrollment_detail,
                    action='patch',
                    fields=[
                        _field('student_id', location='path', description='ID del estudiante'),
                        _field('course_id', location='path', description='ID del curso'),
                    ],
                    description='Actualiza parcialmente una inscripción.',
                ),
                'delete': Link(
                    url=enrollment_detail,
                    action='delete',
                    fields=[
                        _field('student_id', location='path', description='ID del estudiante'),
                        _field('course_id', location='path', description='ID del curso'),
                    ],
                    description='Retira (borrado lógico) una inscripción.',
                ),
                'restore': Link(
                    url=enrollment_detail + 'restore/',
                    action='post',
                    fields=[
                        _field('student_id', location='path', description='ID del estudiante'),
                        _field('course_id', location='path', description='ID del curso'),
                    ],
                    description='Restaura una inscripción inactiva (solo superusuario).',
                ),
            },
        },
    )


_SCHEMA_TEXT = None


def coreapi_schema_view(request):
    """Vista: sirve el esquema CoreAPI en formato CoreJSON."""
    global _SCHEMA_TEXT
    if _SCHEMA_TEXT is None:
        _SCHEMA_TEXT = CoreJSONCodec().encode(_build_schema())
    return HttpResponse(_SCHEMA_TEXT, content_type='application/vnd.coreapi+json')