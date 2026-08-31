#!/usr/bin/env python
import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from academic.models import Student, Course, Teacher

# Crear un cliente autenticado
client = Client()

# Obtener el usuario admin
user = User.objects.filter(username='profe').first()
if not user:
    print("Usuario 'profe' no encontrado")
    sys.exit(1)

# Autenticar el cliente
client.force_login(user)

# Obtener un estudiante inactivo o crear uno
students = Student.objects.all()
print(f"Total de estudiantes: {len(students)}")

student = students.first()
if student:
    print(f"\nProbando con estudiante ID={student.id}, activo={student.activo}")
    
    # Test 1: Desactivar un estudiante activo
    if student.activo:
        print("\n=== Test 1: Desactivar estudiante ===")
        response = client.patch(
            f'/api/students/{student.id}/',
            data=json.dumps({'activo': False}),
            content_type='application/json'
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Respuesta: activo={data.get('activo')}")
        else:
            print(f"Error: {response.content}")
    
    # Test 2: Reactivar el estudiante usando restore
    print("\n=== Test 2: Activar estudiante (restore) ===")
    response = client.post(f'/api/students/{student.id}/restore/')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Respuesta: activo={data.get('activo')}")
    else:
        print(f"Error: {response.content}")

# Probar con cursos
print("\n" + "="*50)
courses = Course.objects.all()
print(f"Total de cursos: {len(courses)}")

course = courses.first()
if course:
    print(f"\nProbando con curso ID={course.id}, activo={course.activo}")
    
    # Test 1: Desactivar un curso activo
    if course.activo:
        print("\n=== Test 1: Desactivar curso ===")
        response = client.patch(
            f'/api/courses/{course.id}/',
            data=json.dumps({'activo': False}),
            content_type='application/json'
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Respuesta: activo={data.get('activo')}")
        else:
            print(f"Error: {response.content}")
    
    # Test 2: Reactivar el curso usando restore
    print("\n=== Test 2: Activar curso (restore) ===")
    response = client.post(f'/api/courses/{course.id}/restore/')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Respuesta: activo={data.get('activo')}")
    else:
        print(f"Error: {response.content}")

# Probar con docentes
print("\n" + "="*50)
teachers = Teacher.objects.all()
print(f"Total de docentes: {len(teachers)}")

teacher = teachers.first()
if teacher:
    print(f"\nProbando con docente ID={teacher.id}, activo={teacher.activo}")
    
    # Test 1: Desactivar un docente activo
    if teacher.activo:
        print("\n=== Test 1: Desactivar docente ===")
        response = client.patch(
            f'/api/teachers/{teacher.id}/',
            data=json.dumps({'activo': False}),
            content_type='application/json'
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Respuesta: activo={data.get('activo')}")
        else:
            print(f"Error: {response.content}")
    
    # Test 2: Reactivar el docente usando restore
    print("\n=== Test 2: Activar docente (restore) ===")
    response = client.post(f'/api/teachers/{teacher.id}/restore/')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Respuesta: activo={data.get('activo')}")
    else:
        print(f"Error: {response.content}")
