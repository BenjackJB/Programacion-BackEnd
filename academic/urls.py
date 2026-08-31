"""
Configuración de URLs de la app academic.

Incluye:
- Rutas para vistas HTML (templates)
- Rutas para API REST (DRF ViewSets)
- Login/Logout personalizados
- Rutas especiales para PK compuesta en StudentCourse
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# =============================================================================
# ROUTER DRF PARA API REST
# =============================================================================

router = DefaultRouter()
router.register(r'teachers', views.TeacherViewSet, basename='teacher')
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'students', views.StudentViewSet, basename='student')
router.register(r'enrollments', views.StudentCourseViewSet, basename='enrollment')

# =============================================================================
# URLPATTERNS - VISTAS HTML (TEMPLATES)
# =============================================================================

urlpatterns = [
    # Autenticación
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # Vistas principales (templates HTML)
    path('', views.HomeView.as_view(), name='home'),
    path('courses/', views.CoursesView.as_view(), name='courses'),
    path('students/', views.StudentsView.as_view(), name='students'),

    # API REST (DRF) - prefijo /api/
    path('api/', include(router.urls)),

    # Rutas explícitas para StudentCourse con PK compuesta
    # GET/PUT/DELETE /api/enrollments/<student_id>/<course_id>/
    path(
        'api/enrollments/<int:student_id>/<int:course_id>/',
        views.StudentCourseViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='enrollment-detail-composite'
    ),
]