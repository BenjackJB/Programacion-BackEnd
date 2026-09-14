"""
Comando para poblar la base de datos con datos de prueba.
Uso: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from academic.models import Teacher, Course, Student, StudentCourse, Asignatura


class Command(BaseCommand):
    help = 'Pobla la base de datos con datos de prueba (docentes, cursos, estudiantes, asignaturas, inscripciones)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpia todos los datos antes de crear nuevos',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Limpiando datos existentes...')
            # Se usa all_objects + QuerySet.delete() (borrado físico real, en orden
            # para respetar las FK PROTECT: inscripciones -> estudiantes -> cursos -> docentes)
            StudentCourse.all_objects.all().delete()
            Student.all_objects.all().delete()
            Course.all_objects.all().delete()
            Teacher.all_objects.all().delete()
            Asignatura.all_objects.all().delete()

        # Crear superusuario si no existe
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Superusuario creado: admin / admin123'))
        else:
            self.stdout.write('Superusuario "admin" ya existe.')

        # Crear usuario profesor si no existe
        if not User.objects.filter(username='profe').exists():
            profe = User.objects.create_user('profe', 'profe@example.com', '123456', is_staff=True, is_superuser=True)
            self.stdout.write(self.style.SUCCESS('Usuario creado: profe / 123456'))
        else:
            self.stdout.write('Usuario "profe" ya existe.')

        # Crear usuario normal (con JWT puede hacer CRUD; no ve inactivos)
        if not User.objects.filter(username='alumno').exists():
            User.objects.create_user('alumno', 'alumno@example.com', 'secret')
            self.stdout.write(self.style.SUCCESS('Usuario creado: alumno / secret'))
        else:
            self.stdout.write('Usuario "alumno" ya existe.')

        # Crear docentes
        docentes_data = [
            {'first_name': 'Carlos', 'last_name': 'Mendoza', 'sexo': 'M'},
            {'first_name': 'Ana', 'last_name': 'Garcia', 'sexo': 'F'},
            {'first_name': 'Luis', 'last_name': 'Rodriguez', 'sexo': 'M'},
            {'first_name': 'Maria', 'last_name': 'Lopez', 'sexo': 'F'},
            {'first_name': 'Pedro', 'last_name': 'Martinez', 'sexo': 'M'},
            {'first_name': 'Laura', 'last_name': 'Hernandez', 'sexo': 'F'},
            {'first_name': 'Jorge', 'last_name': 'Diaz', 'sexo': 'M'},
            {'first_name': 'Sofia', 'last_name': 'Torres', 'sexo': 'F'},
        ]

        docentes = []
        for data in docentes_data:
            teacher, created = Teacher.objects.get_or_create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                defaults={'sexo': data['sexo']}
            )
            docentes.append(teacher)
            if created:
                self.stdout.write(f'  Docente creado: {teacher.first_name} {teacher.last_name} ({teacher.get_sexo_display()})')

        # Crear cursos con jornada
        cursos_data = [
            {'name': 'Matematicas I', 'teacher': docentes[0], 'jornada': 'D'},
            {'name': 'Fisica I', 'teacher': docentes[1], 'jornada': 'D'},
            {'name': 'Programacion I', 'teacher': docentes[2], 'jornada': 'V'},
            {'name': 'Base de Datos', 'teacher': docentes[3], 'jornada': 'V'},
            {'name': 'Redes de Computadoras', 'teacher': docentes[4], 'jornada': 'D'},
            {'name': 'Ingenieria de Software', 'teacher': docentes[5], 'jornada': 'V'},
            {'name': 'Inteligencia Artificial', 'teacher': docentes[6], 'jornada': 'D'},
            {'name': 'Sistemas Operativos', 'teacher': docentes[7], 'jornada': 'V'},
            {'name': 'Estructuras de Datos', 'teacher': docentes[2], 'jornada': 'D'},
            {'name': 'Calculo II', 'teacher': docentes[0], 'jornada': 'V'},
        ]

        cursos = []
        for data in cursos_data:
            course, created = Course.objects.get_or_create(
                name=data['name'],
                defaults={'teacher': data['teacher'], 'jornada': data['jornada']}
            )
            cursos.append(course)
            if created:
                self.stdout.write(f'  Curso creado: {course.name} ({course.get_jornada_display()})')

        # Crear estudiantes con sexo y jornada
        estudiantes_data = [
            {'first_name': 'Juan', 'last_name': 'Perez', 'sexo': 'M', 'jornada': 'D'},
            {'first_name': 'Diego', 'last_name': 'Sanchez', 'sexo': 'M', 'jornada': 'D'},
            {'first_name': 'Camila', 'last_name': 'Ramirez', 'sexo': 'F', 'jornada': 'V'},
            {'first_name': 'Valentina', 'last_name': 'Torres', 'sexo': 'F', 'jornada': 'V'},
            {'first_name': 'Mateo', 'last_name': 'Flores', 'sexo': 'M', 'jornada': 'D'},
            {'first_name': 'Isabella', 'last_name': 'Gomez', 'sexo': 'F', 'jornada': 'V'},
            {'first_name': 'Sebastian', 'last_name': 'Diaz', 'sexo': 'M', 'jornada': 'D'},
            {'first_name': 'Daniela', 'last_name': 'Vargas', 'sexo': 'F', 'jornada': 'V'},
            {'first_name': 'Nicolas', 'last_name': 'Morales', 'sexo': 'M', 'jornada': 'D'},
            {'first_name': 'Luciana', 'last_name': 'Cruz', 'sexo': 'F', 'jornada': 'V'},
            {'first_name': 'Andres', 'last_name': 'Reyes', 'sexo': 'M', 'jornada': 'D'},
            {'first_name': 'Paula', 'last_name': 'Ortiz', 'sexo': 'F', 'jornada': 'V'},
            {'first_name': 'Felipe', 'last_name': 'Gutierrez', 'sexo': 'M', 'jornada': 'D'},
            {'first_name': 'Mariana', 'last_name': 'Castillo', 'sexo': 'F', 'jornada': 'V'},
            {'first_name': 'Alejandro', 'last_name': 'Jimenez', 'sexo': 'M', 'jornada': 'D'},
            {'first_name': 'Carolina', 'last_name': 'Ruiz', 'sexo': 'F', 'jornada': 'V'},
            {'first_name': 'Daniel', 'last_name': 'Alvarez', 'sexo': 'M', 'jornada': 'D'},
            {'first_name': 'Gabriela', 'last_name': 'Mendoza', 'sexo': 'F', 'jornada': 'V'},
            {'first_name': 'Mateo', 'last_name': 'Herrera', 'sexo': 'M', 'jornada': 'D'},
            {'first_name': 'Lucia', 'last_name': 'Aguilar', 'sexo': 'F', 'jornada': 'V'},
        ]

        estudiantes = []
        for data in estudiantes_data:
            student, created = Student.objects.get_or_create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                defaults={'sexo': data['sexo'], 'jornada': data['jornada']}
            )
            estudiantes.append(student)
            if created:
                self.stdout.write(f'  Estudiante creado: {student.first_name} {student.last_name} ({student.get_sexo_display()})')

        # Crear asignaturas (lectura pública; CRUD con JWT)
        asignaturas_data = [
            {'codigo': 'MAT101', 'nombre': 'Algebra', 'tipo': 'O', 'nivel': '1', 'creditos': 4},
            {'codigo': 'MAT102', 'nombre': 'Calculo I', 'tipo': 'O', 'nivel': '1', 'creditos': 4},
            {'codigo': 'FIS101', 'nombre': 'Fisica General', 'tipo': 'O', 'nivel': '1', 'creditos': 4},
            {'codigo': 'PRO101', 'nombre': 'Programacion I', 'tipo': 'O', 'nivel': '2', 'creditos': 5},
            {'codigo': 'PRO102', 'nombre': 'Programacion II', 'tipo': 'O', 'nivel': '2', 'creditos': 5},
            {'codigo': 'BASE02', 'nombre': 'Base de Datos', 'tipo': 'O', 'nivel': '2', 'creditos': 4},
            {'codigo': 'RED101', 'nombre': 'Redes de Computadoras', 'tipo': 'O', 'nivel': '3', 'creditos': 4},
            {'codigo': 'ING301', 'nombre': 'Ingenieria de Software', 'tipo': 'O', 'nivel': '3', 'creditos': 4},
            {'codigo': 'IA401', 'nombre': 'Inteligencia Artificial', 'tipo': 'E', 'nivel': '4', 'creditos': 3},
            {'codigo': 'SOP301', 'nombre': 'Sistemas Operativos', 'tipo': 'O', 'nivel': '3', 'creditos': 4},
        ]
        for data in asignaturas_data:
            asignatura, created = Asignatura.objects.get_or_create(
                codigo=data['codigo'],
                defaults={
                    'nombre': data['nombre'],
                    'tipo': data['tipo'],
                    'nivel': data['nivel'],
                    'creditos': data['creditos'],
                }
            )
            if created:
                self.stdout.write(f'  Asignatura creada: {asignatura.nombre} ({asignatura.get_tipo_display()})')

        # Crear inscripciones
        inscripciones_data = [
            (0, [0, 2, 4]),
            (1, [0, 3, 5]),
            (2, [1, 2, 6]),
            (3, [1, 4, 7]),
            (4, [2, 3, 8]),
            (5, [0, 5, 9]),
            (6, [3, 6, 8]),
            (7, [1, 7, 9]),
            (8, [2, 4, 6]),
            (9, [0, 3, 7]),
            (10, [1, 5, 8]),
            (11, [4, 6, 9]),
            (12, [2, 3, 5]),
            (13, [0, 7, 8]),
            (14, [1, 4, 6]),
            (15, [3, 5, 9]),
            (16, [2, 7, 8]),
            (17, [0, 4, 6]),
            (18, [1, 3, 9]),
            (19, [2, 5, 7]),
        ]

        for est_idx, curso_indices in inscripciones_data:
            for curso_idx in curso_indices:
                enrollment, created = StudentCourse.objects.get_or_create(
                    student=estudiantes[est_idx],
                    course=cursos[curso_idx]
                )
                if created:
                    self.stdout.write(
                        f'  Inscripcion: {estudiantes[est_idx].first_name} -> {cursos[curso_idx].name}'
                    )

        self.stdout.write(self.style.SUCCESS('\nDatos de prueba creados exitosamente!'))
        self.stdout.write(f'  - {Teacher.objects.count()} docentes')
        self.stdout.write(f'  - {Course.objects.count()} cursos')
        self.stdout.write(f'  - {Student.objects.count()} estudiantes')
        self.stdout.write(f'  - {Asignatura.objects.count()} asignaturas')
        self.stdout.write(f'  - {StudentCourse.objects.count()} inscripciones')
        self.stdout.write('\nCredenciales de acceso: admin / admin123 (superusuario)')
        self.stdout.write('JWT: POST /api/token/ con {"username": "admin", "password": "admin123"} (cualquier usuario con credenciales válidas)')
        self.stdout.write('Docs: /docs/')
