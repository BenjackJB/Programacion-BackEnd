"""
Comando para poblar la base de datos con datos de prueba.
Uso: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from academic.models import Teacher, Course, Student, StudentCourse


class Command(BaseCommand):
    help = 'Pobla la base de datos con datos de prueba (docentes, cursos, estudiantes, inscripciones)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpia todos los datos antes de crear nuevos',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Limpiando datos existentes...')
            StudentCourse.objects.all().delete()
            Student.all_objects.all().delete()
            Course.all_objects.all().delete()
            Teacher.all_objects.all().delete()

        # Crear superusuario si no existe
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Superusuario creado: admin / admin123'))
        else:
            self.stdout.write('Superusuario "admin" ya existe.')

        # Crear docentes
        docentes_data = [
            {'first_name': 'Carlos', 'last_name': 'Mendoza'},
            {'first_name': 'Ana', 'last_name': 'Garcia'},
            {'first_name': 'Luis', 'last_name': 'Rodriguez'},
            {'first_name': 'Maria', 'last_name': 'Lopez'},
            {'first_name': 'Pedro', 'last_name': 'Martinez'},
            {'first_name': 'Laura', 'last_name': 'Hernandez'},
            {'first_name': 'Jorge', 'last_name': 'Diaz'},
            {'first_name': 'Sofia', 'last_name': 'Torres'},
        ]

        docentes = []
        for data in docentes_data:
            teacher, created = Teacher.objects.get_or_create(
                first_name=data['first_name'],
                last_name=data['last_name']
            )
            docentes.append(teacher)
            if created:
                self.stdout.write(f'  Docente creado: {teacher.first_name} {teacher.last_name}')

        # Crear cursos
        cursos_data = [
            {'name': 'Matematicas I', 'teacher': docentes[0]},
            {'name': 'Fisica I', 'teacher': docentes[1]},
            {'name': 'Programacion I', 'teacher': docentes[2]},
            {'name': 'Base de Datos', 'teacher': docentes[3]},
            {'name': 'Redes de Computadoras', 'teacher': docentes[4]},
            {'name': 'Ingenieria de Software', 'teacher': docentes[5]},
            {'name': 'Inteligencia Artificial', 'teacher': docentes[6]},
            {'name': 'Sistemas Operativos', 'teacher': docentes[7]},
            {'name': 'Estructuras de Datos', 'teacher': docentes[2]},
            {'name': 'Calculo II', 'teacher': docentes[0]},
        ]

        cursos = []
        for data in cursos_data:
            course, created = Course.objects.get_or_create(
                name=data['name'],
                defaults={'teacher': data['teacher']}
            )
            cursos.append(course)
            if created:
                self.stdout.write(f'  Curso creado: {course.name}')

        # Crear estudiantes
        estudiantes_data = [
            {'first_name': 'Juan', 'last_name': 'Perez'},
            {'first_name': 'Diego', 'last_name': 'Sanchez'},
            {'first_name': 'Camila', 'last_name': 'Ramirez'},
            {'first_name': 'Valentina', 'last_name': 'Torres'},
            {'first_name': 'Mateo', 'last_name': 'Flores'},
            {'first_name': 'Isabella', 'last_name': 'Gomez'},
            {'first_name': 'Sebastian', 'last_name': 'Diaz'},
            {'first_name': 'Daniela', 'last_name': 'Vargas'},
            {'first_name': 'Nicolas', 'last_name': 'Morales'},
            {'first_name': 'Luciana', 'last_name': 'Cruz'},
            {'first_name': 'Andres', 'last_name': 'Reyes'},
            {'first_name': 'Paula', 'last_name': 'Ortiz'},
            {'first_name': 'Felipe', 'last_name': 'Gutierrez'},
            {'first_name': 'Mariana', 'last_name': 'Castillo'},
            {'first_name': 'Alejandro', 'last_name': 'Jimenez'},
            {'first_name': 'Carolina', 'last_name': 'Ruiz'},
            {'first_name': 'Daniel', 'last_name': 'Alvarez'},
            {'first_name': 'Gabriela', 'last_name': 'Mendoza'},
            {'first_name': 'Mateo', 'last_name': 'Herrera'},
            {'first_name': 'Lucia', 'last_name': 'Aguilar'},
        ]

        estudiantes = []
        for data in estudiantes_data:
            student, created = Student.objects.get_or_create(
                first_name=data['first_name'],
                last_name=data['last_name']
            )
            estudiantes.append(student)
            if created:
                self.stdout.write(f'  Estudiante creado: {student.first_name} {student.last_name}')

        # Crear inscripciones (cada estudiante en 2-4 cursos)
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
        self.stdout.write(f'  - {StudentCourse.objects.count()} inscripciones')
        self.stdout.write('\nCredenciales de acceso: admin / admin123')
