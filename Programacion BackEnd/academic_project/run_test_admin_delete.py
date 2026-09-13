#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from academic.models import StudentCourse

# Crear un cliente autenticado
client = Client()

# Obtener el usuario admin
user = User.objects.filter(username='profe').first()
if not user:
    print("Usuario 'profe' no encontrado")
    sys.exit(1)

# Autenticar el cliente
client.force_login(user)

# Obtener una inscripción activa
enrollment = StudentCourse.objects.filter(activo=True).first()
if not enrollment:
    print("No hay inscripciones activas")
    sys.exit(1)

print(f"Probando delete en admin para inscripción ID={enrollment.id}")
print(f"Student: {enrollment.student.full_name} (activo={enrollment.student.activo})")
print(f"Course: {enrollment.course.name} (activo={enrollment.course.activo})")

# Simular el POST de delete desde admin
response = client.post(
    f'/admin/academic/studentcourse/{enrollment.id}/delete/',
    {'post': 'yes'},  # Confirmar el borrado
    follow=True
)

print(f"\nStatus: {response.status_code}")
if response.status_code == 200:
    # Verificar si fue eliminado
    still_exists = StudentCourse.objects.filter(id=enrollment.id, activo=True).exists()
    if not still_exists:
        print("✓ Inscripción eliminada correctamente (soft delete)")
        # Verificar si está marcada como inactiva
        soft_deleted = StudentCourse.all_objects.filter(id=enrollment.id, activo=False).exists()
        if soft_deleted:
            print("✓ Confirmado: registro marcado como inactivo en BD")
    else:
        print("✗ Error: inscripción no fue eliminada")
else:
    print(f"✗ Error HTTP {response.status_code}")
    # Buscar mensajes de error en la respuesta
    if b"ValidationError" in response.content:
        print("✗ Error de validación detectado")
