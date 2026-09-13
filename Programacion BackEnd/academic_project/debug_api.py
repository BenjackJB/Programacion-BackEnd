#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
import json

# Verificar que el usuario admin existe
users = User.objects.all()
print(f"Usuarios disponibles: {list(users.values_list('username', 'is_superuser'))}")

client = Client()

# Obtener lista de estudiantes
print("\n=== Obteniendo estudiantes ===")
response = client.get('/api/students/')
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    students = data if isinstance(data, list) else data.get('results', [])
    if students:
        print(f"Encontrados {len(students)} estudiantes")
        student = students[0]
        print(f"Primer estudiante: ID={student.get('id')}, activo={student.get('activo')}")
    else:
        print("No hay estudiantes")
else:
    print(f"Error: {response.content}")

# Obtener lista de cursos
print("\n=== Obteniendo cursos ===")
response = client.get('/api/courses/')
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    courses = data if isinstance(data, list) else data.get('results', [])
    if courses:
        print(f"Encontrados {len(courses)} cursos")
        course = courses[0]
        print(f"Primer curso: ID={course.get('id')}, activo={course.get('activo')}")
    else:
        print("No hay cursos")
else:
    print(f"Error: {response.content}")

# Obtener lista de docentes
print("\n=== Obteniendo docentes ===")
response = client.get('/api/teachers/')
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    teachers = data if isinstance(data, list) else data.get('results', [])
    if teachers:
        print(f"Encontrados {len(teachers)} docentes")
        teacher = teachers[0]
        print(f"Primer docente: ID={teacher.get('id')}, activo={teacher.get('activo')}")
    else:
        print("No hay docentes")
else:
    print(f"Error: {response.content}")
