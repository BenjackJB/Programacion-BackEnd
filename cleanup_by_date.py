#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_project.settings')
django.setup()

from academic.models import StudentCourse, Student, Teacher, Course
from django.utils import timezone as django_timezone

print("="*60)
print("ELIMINANDO REGISTROS POSTERIORES A 31-08-2026 23:00")
print("="*60)

# Fecha límite: 31-08-2026 a las 23:00
cutoff_date = django_timezone.make_aware(
    datetime(2026, 8, 31, 23, 0, 0)
)
print(f"\nFecha límite: {cutoff_date}")
print(f"Se eliminarán registros con fecha_creacion > {cutoff_date}\n")

# 1. Inscripciones
print("1. Eliminando inscripciones posteriores a la fecha...")
enrollments_to_delete = StudentCourse.all_objects.filter(fecha_creacion__gt=cutoff_date)
count_enrollments = enrollments_to_delete.count()
for enrollment in enrollments_to_delete:
    enrollment.delete(keep_parents=True)
print(f"   ✓ Eliminadas {count_enrollments} inscripciones")

# 2. Docentes
print("\n2. Eliminando docentes posteriores a la fecha...")
teachers_to_delete = Teacher.all_objects.filter(fecha_creacion__gt=cutoff_date)
count_teachers = teachers_to_delete.count()
for teacher in teachers_to_delete:
    # Primero eliminar sus cursos
    courses = Course.all_objects.filter(teacher=teacher)
    for course in courses:
        # Eliminar inscripciones del curso
        enrollments = StudentCourse.all_objects.filter(course=course)
        for enrollment in enrollments:
            enrollment.delete(keep_parents=True)
        course.delete(keep_parents=True)
    teacher.delete(keep_parents=True)
print(f"   ✓ Eliminados {count_teachers} docentes")

# 3. Cursos
print("\n3. Eliminando cursos posteriores a la fecha...")
courses_to_delete = Course.all_objects.filter(fecha_creacion__gt=cutoff_date)
count_courses = courses_to_delete.count()
for course in courses_to_delete:
    # Eliminar inscripciones del curso
    enrollments = StudentCourse.all_objects.filter(course=course)
    for enrollment in enrollments:
        enrollment.delete(keep_parents=True)
    course.delete(keep_parents=True)
print(f"   ✓ Eliminados {count_courses} cursos")

# 4. Estudiantes
print("\n4. Eliminando estudiantes posteriores a la fecha...")
students_to_delete = Student.all_objects.filter(fecha_creacion__gt=cutoff_date)
count_students = students_to_delete.count()
for student in students_to_delete:
    # Eliminar inscripciones del estudiante
    enrollments = StudentCourse.all_objects.filter(student=student)
    for enrollment in enrollments:
        enrollment.delete(keep_parents=True)
    student.delete(keep_parents=True)
print(f"   ✓ Eliminados {count_students} estudiantes")

print("\n" + "="*60)
print("✓ ELIMINACIÓN COMPLETADA")
print("="*60)

# Resumen final
print("\nRESUMEN DE REGISTROS RESTANTES:")
active_teachers = Teacher.objects.filter(activo=True).count()
all_teachers = Teacher.all_objects.count()
print(f"  - Docentes: {active_teachers} activos ({all_teachers} total)")

active_courses = Course.objects.filter(activo=True).count()
all_courses = Course.all_objects.count()
print(f"  - Cursos: {active_courses} activos ({all_courses} total)")

active_students = Student.objects.filter(activo=True).count()
all_students = Student.all_objects.count()
print(f"  - Estudiantes: {active_students} activos ({all_students} total)")

active_enrollments = StudentCourse.objects.filter(activo=True).count()
all_enrollments = StudentCourse.all_objects.count()
print(f"  - Inscripciones: {active_enrollments} activas ({all_enrollments} total)")
