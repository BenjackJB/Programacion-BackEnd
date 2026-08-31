#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_project.settings')
django.setup()

from academic.models import StudentCourse, Student, Teacher, Course
from django.contrib.admin.models import LogEntry

print("\n📊 ESTADO ACTUAL DE LA BASE DE DATOS")
print("="*50)

# Docentes
teachers = Teacher.objects.all()
print(f"\n👨‍🏫 DOCENTES ({teachers.count()}):")
for t in teachers:
    print(f"   • {t.full_name}")

# Cursos
courses = Course.objects.all()
print(f"\n📚 CURSOS ({courses.count()}):")
for c in courses:
    print(f"   • {c.name} (Docente: {c.teacher.full_name})")

# Estudiantes
students = Student.objects.all()
print(f"\n👥 ESTUDIANTES ({students.count()}):")
for s in students:
    print(f"   • {s.full_name}")

# Inscripciones
enrollments = StudentCourse.objects.all()
print(f"\n📝 INSCRIPCIONES ({enrollments.count()}):")
for e in enrollments:
    print(f"   • {e.student.full_name} → {e.course.name}")

# Historial
logs = LogEntry.objects.all()
print(f"\n📋 HISTORIAL DE ACCIONES: {logs.count()} entradas")

print("\n" + "="*50)
print("✓ Base de datos limpia y lista para usar")
