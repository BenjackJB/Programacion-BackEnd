#!/usr/bin/env python
"""
Script de precarga de datos de prueba (seed) para el proyecto academic_project.

Genera datos ficticios en formato JSON y los carga en la base de datos.
Incluye: Teachers, Courses, Students, y StudentCourses (inscripciones).

Uso:
    python seed_data.py

O desde Django shell:
    exec(open('seed_data.py').read())
"""

import os
import sys
import json
import django
from datetime import datetime

# Configurar Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_project.settings')
django.setup()

from academic.models import Teacher, Course, Student, StudentCourse


# =============================================================================
# DATOS DE PRUEBA EN FORMATO JSON (generados con asistencia de IA)
# =============================================================================

TEACHERS_JSON = [
    {"first_name": "María", "last_name": "González"},
    {"first_name": "Carlos", "last_name": "Rodríguez"},
    {"first_name": "Ana", "last_name": "Martínez"},
    {"first_name": "Luis", "last_name": "Fernández"},
    {"first_name": "Patricia", "last_name": "López"},
    {"first_name": "Jorge", "last_name": "Sánchez"},
    {"first_name": "Laura", "last_name": "Pérez"},
    {"first_name": "Roberto", "last_name": "Gómez"},
]

COURSES_JSON = [
    {"name": "Matemáticas I", "teacher_idx": 0},
    {"name": "Física General", "teacher_idx": 1},
    {"name": "Química Orgánica", "teacher_idx": 2},
    {"name": "Programación Python", "teacher_idx": 3},
    {"name": "Base de Datos", "teacher_idx": 4},
    {"name": "Álgebra Lineal", "teacher_idx": 0},
    {"name": "Cálculo Diferencial", "teacher_idx": 1},
    {"name": "Estadística Aplicada", "teacher_idx": 5},
    {"name": "Redes Computacionales", "teacher_idx": 6},
    {"name": "Inteligencia Artificial", "teacher_idx": 7},
]

STUDENTS_JSON = [
    {"first_name": "Andrés", "last_name": "Silva"},
    {"first_name": "Camila", "last_name": "Torres"},
    {"first_name": "Diego", "last_name": "Rojas"},
    {"first_name": "Valentina", "last_name": "Flores"},
    {"first_name": "Sebastián", "last_name": "Vargas"},
    {"first_name": "Isidora", "last_name": "Morales"},
    {"first_name": "Matías", "last_name": "Herrera"},
    {"first_name": "Javiera", "last_name": "Medina"},
    {"first_name": "Tomás", "last_name": "Cortés"},
    {"first_name": "Antonia", "last_name": "Reyes"},
    {"first_name": "Benjamín", "last_name": "Gutiérrez"},
    {"first_name": "Emilia", "last_name": "Ruiz"},
    {"first_name": "Vicente", "last_name": "Ortiz"},
    {"first_name": "Constanza", "last_name": "Castillo"},
    {"first_name": "Maximiliano", "last_name": "Ramos"},
]

# Inscripciones: (student_idx, course_idx)
ENROLLMENTS_JSON = [
    (0, 0), (0, 3), (0, 5),   # Andrés: Matemáticas I, Python, Álgebra
    (1, 1), (1, 4), (1, 7),   # Camila: Física, BD, Estadística
    (2, 2), (2, 3), (2, 8),   # Diego: Química, Python, Redes
    (3, 0), (3, 4), (3, 9),   # Valentina: Matemáticas I, BD, IA
    (4, 1), (4, 5), (4, 6),   # Sebastián: Física, Álgebra, Cálculo
    (5, 2), (5, 7), (5, 9),   # Isidora: Química, Estadística, IA
    (6, 0), (6, 3), (6, 8),   # Matías: Matemáticas I, Python, Redes
    (7, 1), (7, 4), (7, 6),   # Javiera: Física, BD, Cálculo
    (8, 2), (8, 5), (8, 9),   # Tomás: Química, Álgebra, IA
    (9, 0), (9, 3), (9, 7),   # Antonia: Matemáticas I, Python, Estadística
    (10, 1), (10, 4), (10, 8), # Benjamín: Física, BD, Redes
    (11, 2), (11, 6), (11, 9), # Emilia: Química, Cálculo, IA
    (12, 0), (12, 5), (12, 7), # Vicente: Matemáticas I, Álgebra, Estadística
    (13, 1), (13, 3), (13, 8), # Constanza: Física, Python, Redes
    (14, 2), (14, 4), (14, 9), # Maximiliano: Química, BD, IA
]


# =============================================================================
# FUNCIONES DE CARGA
# =============================================================================

def clear_existing_data():
    """Limpia datos existentes (solo para desarrollo)."""
    print("🧹 Limpiando datos existentes...")
    StudentCourse.all_objects.all().delete()
    Course.all_objects.all().delete()
    Student.all_objects.all().delete()
    Teacher.all_objects.all().delete()
    print("   ✓ Datos limpiados")


def load_teachers():
    """Carga docentes desde JSON."""
    print("👨‍🏫 Cargando docentes...")
    teachers = []
    for data in TEACHERS_JSON:
        teacher, created = Teacher.objects.get_or_create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            defaults={'activo': True}
        )
        teachers.append(teacher)
        status = "creado" if created else "existente"
        print(f"   ✓ {teacher.full_name} ({status})")
    return teachers


def load_courses(teachers):
    """Carga cursos desde JSON."""
    print("📚 Cargando cursos...")
    courses = []
    for data in COURSES_JSON:
        teacher = teachers[data['teacher_idx']]
        course, created = Course.objects.get_or_create(
            name=data['name'],
            teacher=teacher,
            defaults={'activo': True}
        )
        courses.append(course)
        status = "creado" if created else "existente"
        print(f"   ✓ {course.name} - {teacher.full_name} ({status})")
    return courses


def load_students():
    """Carga estudiantes desde JSON."""
    print("👨‍🎓 Cargando estudiantes...")
    students = []
    for data in STUDENTS_JSON:
        student, created = Student.objects.get_or_create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            defaults={'activo': True}
        )
        students.append(student)
        status = "creado" if created else "existente"
        print(f"   ✓ {student.full_name} ({status})")
    return students


def load_enrollments(students, courses):
    """Carga inscripciones desde JSON."""
    print("📝 Cargando inscripciones...")
    count = 0
    for student_idx, course_idx in ENROLLMENTS_JSON:
        student = students[student_idx]
        course = courses[course_idx]

        enrollment, created = StudentCourse.objects.get_or_create(
            student=student,
            course=course,
            defaults={'activo': True}
        )
        if created:
            count += 1
            print(f"   ✓ {student.full_name} → {course.name}")
        else:
            print(f"   ⏭ {student.full_name} → {course.name} (ya existe)")

    print(f"   Total inscripciones nuevas: {count}")


def export_to_json(teachers, courses, students):
    """Exporta los datos cargados a archivo JSON para respaldo."""
    print("💾 Exportando a JSON...")

    data = {
        "generated_at": datetime.now().isoformat(),
        "teachers": [
            {
                "id": t.id,
                "first_name": t.first_name,
                "last_name": t.last_name,
                "full_name": t.full_name,
                "activo": t.activo,
            }
            for t in teachers
        ],
        "courses": [
            {
                "id": c.id,
                "name": c.name,
                "teacher_id": c.teacher_id,
                "teacher_name": c.teacher.full_name,
                "activo": c.activo,
            }
            for c in courses
        ],
        "students": [
            {
                "id": s.id,
                "first_name": s.first_name,
                "last_name": s.last_name,
                "full_name": s.full_name,
                "activo": s.activo,
            }
            for s in students
        ],
        "enrollments": [
            {
                "student_id": e.student_id,
                "student_name": e.student.full_name,
                "course_id": e.course_id,
                "course_name": e.course.name,
                "activo": e.activo,
            }
            for e in StudentCourse.objects.filter(activo=True).select_related('student', 'course')
        ],
    }

    output_path = os.path.join(BASE_DIR, 'seed_data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"   ✓ Datos exportados a: {output_path}")


def print_summary(teachers, courses, students):
    """Imprime resumen final."""
    enrollments_count = StudentCourse.objects.filter(activo=True).count()
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE CARGA")
    print("=" * 50)
    print(f"   Docentes:     {len(teachers)}")
    print(f"   Cursos:       {len(courses)}")
    print(f"   Estudiantes:  {len(students)}")
    print(f"   Inscripciones: {enrollments_count}")
    print("=" * 50)
    print("✅ Seed completado exitosamente")


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    """Ejecuta la carga completa de datos de prueba."""
    print("\n" + "🌱" + " INICIANDO SEED DATA - academic_project " + "🌱\n")

    try:
        # Opcional: limpiar datos previos
        # clear_existing_data()

        # Cargar en orden de dependencias
        teachers = load_teachers()
        courses = load_courses(teachers)
        students = load_students()
        load_enrollments(students, courses)

        # Exportar a JSON
        export_to_json(teachers, courses, students)

        # Resumen
        print_summary(teachers, courses, students)

    except Exception as e:
        print(f"\n❌ Error durante seed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()