#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_project.settings')
django.setup()

from academic.models import StudentCourse, Student, Teacher, Course
from django.contrib.admin.models import LogEntry

print("="*60)
print("LIMPIEZA DE REGISTROS INACTIVOS")
print("="*60)

# 1. Borrar inscripciones inactivas (StudentCourse)
print("\n1. Borrando inscripciones inactivas...")
inactive_enrollments = StudentCourse.all_objects.filter(activo=False)
count_enrollments = inactive_enrollments.count()
if count_enrollments > 0:
    # Usar delete directamente (sin borrado lógico) para inscripciones inactivas
    for enrollment in inactive_enrollments:
        enrollment.delete(keep_parents=True)  # Fuerza borrado físico
    print(f"   ✓ Eliminadas {count_enrollments} inscripciones inactivas")
else:
    print("   ℹ No hay inscripciones inactivas")

# 2. Borrar docentes inactivos (Teacher)
print("\n2. Borrando docentes inactivos...")
# Primero, borrar sus cursos asociados si están inactivos
inactive_teachers = Teacher.all_objects.filter(activo=False)
count_teachers = 0
for teacher in inactive_teachers:
    # Borrar cursos inactivos de este docente
    inactive_courses = Course.all_objects.filter(teacher=teacher, activo=False)
    for course in inactive_courses:
        course.delete(keep_parents=True)
    # Ahora borrar el docente
    teacher.delete(keep_parents=True)
    count_teachers += 1

if count_teachers > 0:
    print(f"   ✓ Eliminados {count_teachers} docentes inactivos")
else:
    print("   ℹ No hay docentes inactivos")

# 3. Borrar cursos inactivos (Course)
print("\n3. Borrando cursos inactivos...")
inactive_courses = Course.all_objects.filter(activo=False)
count_courses = 0
for course in inactive_courses:
    # Primero borrar las inscripciones de este curso
    enrollments = StudentCourse.all_objects.filter(course=course)
    for enrollment in enrollments:
        enrollment.delete(keep_parents=True)
    # Ahora borrar el curso
    course.delete(keep_parents=True)
    count_courses += 1

if count_courses > 0:
    print(f"   ✓ Eliminados {count_courses} cursos inactivos")
else:
    print("   ℹ No hay cursos inactivos")

# 4. Borrar estudiantes inactivos (Student)
print("\n4. Borrando estudiantes inactivos...")
inactive_students = Student.all_objects.filter(activo=False)
count_students = 0
for student in inactive_students:
    # Primero borrar sus inscripciones
    enrollments = StudentCourse.all_objects.filter(student=student)
    for enrollment in enrollments:
        enrollment.delete(keep_parents=True)
    # Ahora borrar el estudiante
    student.delete(keep_parents=True)
    count_students += 1

if count_students > 0:
    print(f"   ✓ Eliminados {count_students} estudiantes inactivos")
else:
    print("   ℹ No hay estudiantes inactivos")

# 5. Limpiar historial de acciones (LogEntry)
print("\n5. Borrando historial de acciones...")
log_entries = LogEntry.objects.all()
count_logs = log_entries.count()
if count_logs > 0:
    log_entries.delete()
    print(f"   ✓ Eliminadas {count_logs} entradas del historial")
else:
    print("   ℹ No hay historial para limpiar")

print("\n" + "="*60)
print("✓ LIMPIEZA COMPLETADA")
print("="*60)

# Resumen final
print("\nRESUMEN DE REGISTROS ACTIVOS RESTANTES:")
print(f"  - Docentes activos: {Teacher.objects.filter(activo=True).count()}")
print(f"  - Cursos activos: {Course.objects.filter(activo=True).count()}")
print(f"  - Estudiantes activos: {Student.objects.filter(activo=True).count()}")
print(f"  - Inscripciones activas: {StudentCourse.objects.filter(activo=True).count()}")
