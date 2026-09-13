#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from academic.models import StudentCourse, Student, Course
import json

# Crear un cliente autenticado
client = Client()

# Obtener el usuario admin
user = User.objects.filter(username='profe').first()
if not user:
    print("Usuario 'profe' no encontrado")
    sys.exit(1)

# Autenticar el cliente
client.force_login(user)

# Obtener una inscripción
enrollments = StudentCourse.objects.all()
print(f"Total de inscripciones: {len(enrollments)}")

if enrollments:
    enrollment = enrollments.first()
    print(f"\nProbando con inscripción ID={enrollment.id} (Student={enrollment.student.id}, Course={enrollment.course.id})")
    
    # Test 1: Soft delete (desactivar inscripción)
    print("\n=== Test 1: Soft delete de inscripción ===")
    try:
        # Usar el método soft_delete directamente
        enrollment.soft_delete()
        print(f"✓ Soft delete exitoso. Ahora activo={enrollment.activo}")
    except Exception as e:
        print(f"✗ Error en soft delete: {e}")
    
    # Test 2: Restaurar la inscripción
    print("\n=== Test 2: Restaurar inscripción ===")
    try:
        enrollment.restore()
        print(f"✓ Restauración exitosa. Ahora activo={enrollment.activo}")
    except Exception as e:
        print(f"✗ Error en restauración: {e}")
    
    # Test 3: Intentar crear inscripción con estudiante inactivo
    print("\n=== Test 3: Validar que no se puede crear inscripción con estudiante inactivo ===")
    try:
        # Desactivar el estudiante
        student = enrollment.student
        student.activo = False
        student.save()
        
        # Intentar crear una nueva inscripción con este estudiante
        other_course = Course.objects.exclude(id=enrollment.course.id).first()
        if other_course:
            try:
                new_enrollment = StudentCourse(student=student, course=other_course)
                new_enrollment.full_clean()  # Esto debería fallar
                print(f"✗ No se validó correctamente - debería haber fallado")
            except Exception as e:
                print(f"✓ Validación correcta: {e}")
        
        # Reactivar el estudiante
        student.activo = True
        student.save()
    except Exception as e:
        print(f"Error en test: {e}")

print("\n✓ Pruebas completadas")
