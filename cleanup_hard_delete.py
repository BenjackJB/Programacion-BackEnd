#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_project.settings')
django.setup()

from academic.models import StudentCourse, Student, Teacher, Course

print("="*60)
print("ELIMINACION FISICA DE TODOS LOS REGISTROS INACTIVOS")
print("="*60)

# 1. Inscripciones inactivas
print("\n1. Eliminando inscripciones inactivas de la BD...")
inactive_enrollments = StudentCourse.all_objects.filter(activo=False)
count = inactive_enrollments.count()
if count > 0:
    # Borrado físico directo (no soft delete)
    StudentCourse.all_objects.filter(activo=False).delete()
    print(f"   ✓ Eliminadas {count} inscripciones inactivas")
else:
    print("   ℹ No hay inscripciones inactivas")

# 2. Estudiantes inactivos
print("\n2. Eliminando estudiantes inactivos de la BD...")
inactive_students = Student.all_objects.filter(activo=False)
count = inactive_students.count()
if count > 0:
    Student.all_objects.filter(activo=False).delete()
    print(f"   ✓ Eliminados {count} estudiantes inactivos")
else:
    print("   ℹ No hay estudiantes inactivos")

# 3. Cursos inactivos
print("\n3. Eliminando cursos inactivos de la BD...")
inactive_courses = Course.all_objects.filter(activo=False)
count = inactive_courses.count()
if count > 0:
    Course.all_objects.filter(activo=False).delete()
    print(f"   ✓ Eliminados {count} cursos inactivos")
else:
    print("   ℹ No hay cursos inactivos")

# 4. Docentes inactivos
print("\n4. Eliminando docentes inactivos de la BD...")
inactive_teachers = Teacher.all_objects.filter(activo=False)
count = inactive_teachers.count()
if count > 0:
    Teacher.all_objects.filter(activo=False).delete()
    print(f"   ✓ Eliminados {count} docentes inactivos")
else:
    print("   ℹ No hay docentes inactivos")

print("\n" + "="*60)
print("✓ LIMPIEZA FISICA COMPLETADA")
print("="*60)

# Verificación final
print("\nVERIFICACION FINAL:")
print(f"  - Docentes en BD: {Teacher.all_objects.count()} (todos activos)")
print(f"  - Cursos en BD: {Course.all_objects.count()} (todos activos)")
print(f"  - Estudiantes en BD: {Student.all_objects.count()} (todos activos)")
print(f"  - Inscripciones en BD: {StudentCourse.all_objects.count()} (todos activos)")

print("\n✓ Base de datos completamente limpia - Solo quedan registros activos")
