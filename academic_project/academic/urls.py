"""
Configuración de URLs de la app academic.

Incluye:
- Rutas para vistas HTML (templates)
- Rutas para API REST (DRF ViewSets)
- Login/Logout personalizados
- Rutas especiales para PK compuesta en StudentCourse
"""

from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter, APIRootView
from . import views
from .permissions import IsSuperUser
from .coreapi_schema import coreapi_schema_view

# =============================================================================
# ROUTER DRF PARA API REST
# La raíz /api/ (índice navegable que lista todos los endpoints) solo es
# visible para superusuarios; el resto de endpoints siguen su propio permiso.
# =============================================================================

class SuperUserOnlyAPIRootView(APIRootView):
    """Índice de la API: solo superusuarios pueden ver la raíz de /api/."""
    permission_classes = [IsSuperUser]


class AcademicRouter(DefaultRouter):
    APIRootView = SuperUserOnlyAPIRootView


router = AcademicRouter()
router.register(r'teachers', views.TeacherViewSet, basename='teacher')
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'students', views.StudentViewSet, basename='student')
router.register(r'asignaturas', views.AsignaturaViewSet, basename='asignatura')
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
    path('teachers/', views.TeachersView.as_view(), name='teachers'),
    path('students/', views.StudentsView.as_view(), name='students'),
    path('asignaturas/', views.AsignaturasView.as_view(), name='asignaturas'),

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
    # POST /api/enrollments/<student_id>/<course_id>/restore/
    path(
        'api/enrollments/<int:student_id>/<int:course_id>/restore/',
        views.StudentCourseViewSet.as_view({'post': 'restore'}),
        name='enrollment-restore-composite'
    ),

    # Esquema CoreAPI (formato CoreJSON) - documentación paralela a /docs/ y /api/schema/
    path('api/coreapi/', coreapi_schema_view, name='api-coreapi-schema'),

    # Catch-all: cualquier ruta desconocida se redirige a courses (evita 404).
    path('<path:unknown_path>', RedirectView.as_view(url='/courses/', permanent=False)),
]
