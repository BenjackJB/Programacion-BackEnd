"""
Vistas de la aplicación academic.

Incluye:
- Vistas basadas en clases (CBV) para renderizar templates HTML
- ViewSets de DRF para endpoints API REST
- Todas las vistas HTML usan render() y consumen la API vía fetch() en JavaScript

NOTA: StudentCourse usa PK compuesta (student, course) - se maneja con lookup_url_kwarg
"""

# =============================================================================
# IMPORTS
# =============================================================================
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.urls import reverse_lazy

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Teacher, Course, Student, StudentCourse
from .serializers import (
    TeacherSerializer, CourseSerializer, StudentSerializer, StudentCourseSerializer,
    CourseListSerializer, StudentListSerializer
)
from .permissions import (
    IsSuperUserOrReadOnly, AcademicPermission,
    CanManageTeachers, CanManageCourses, CanManageStudents, CanManageEnrollments
)


# =============================================================================
# VISTAS DE AUTENTICACIÓN (HTML)
# =============================================================================

class CustomLoginView(LoginView):
    """
    Vista de login personalizada usando template login.html.
    Redirige a courses después de login exitoso.
    """
    template_name = 'academic/login.html'
    redirect_authenticated_user = True
    next_page = reverse_lazy('courses')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Iniciar Sesión - Gestión Académica'
        return context


class CustomLogoutView(LogoutView):
    """Vista de logout que redirige a login."""
    next_page = reverse_lazy('login')


# =============================================================================
# VISTAS PRINCIPALES (HTML - TEMPLATES)
# =============================================================================

@method_decorator(login_required, name='dispatch')
class BaseTemplateView(LoginRequiredMixin, TemplateView):
    """
    Vista base para templates que requieren autenticación.
    Proporciona contexto común: usuario, menú de navegación.
    """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'user': self.request.user,
            'is_superuser': self.request.user.is_superuser,
        })
        return context


class CoursesView(BaseTemplateView):
    """
    Vista para listado de cursos (courses.html).
    Renderiza template y pasa contexto inicial.
    Los datos se cargan vía JavaScript fetch() desde /api/courses/
    """
    template_name = 'academic/courses.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Cursos',
            'page_header': 'Cursos y Docentes Asignados',
            'api_endpoint': '/api/courses/',
        })
        return context


class StudentsView(BaseTemplateView):
    """
    Vista para listado de estudiantes (students.html).
    Renderiza template y pasa contexto inicial.
    Los datos se cargan vía JavaScript fetch() desde /api/students/
    """
    template_name = 'academic/students.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Estudiantes',
            'page_header': 'Estudiantes Inscritos',
            'api_endpoint': '/api/students/',
        })
        return context


class HomeView(BaseTemplateView):
    """
    Vista de inicio (dashboard) - redirige a courses.
    Evita error 404 en ruta raíz "/".
    """
    template_name = 'academic/courses.html'

    def get(self, request, *args, **kwargs):
        return redirect('courses')


# =============================================================================
# VIEWSETS API REST (DRF)
# =============================================================================

class TeacherViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Docentes - API REST completa.
    Endpoints:
    - GET    /api/teachers/          - Listar (paginado)
    - POST   /api/teachers/          - Crear (solo superuser)
    - GET    /api/teachers/{id}/     - Detalle
    - PUT    /api/teachers/{id}/     - Actualizar (solo superuser)
    - PATCH  /api/teachers/{id}/     - Actualizar parcial (solo superuser)
    - DELETE /api/teachers/{id}/     - Borrado lógico (solo superuser)
    """
    queryset = Teacher.all_objects.all()  # Incluye inactivos para admin
    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated, CanManageTeachers]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name']
    ordering_fields = ['last_name', 'first_name', 'fecha_creacion']
    ordering = ['last_name', 'first_name']

    def perform_destroy(self, instance):
        """Borrado lógico en lugar de eliminación física."""
        instance.soft_delete()

    @action(detail=True, methods=['post'], permission_classes=[CanManageTeachers])
    def restore(self, request, pk=None):
        """Restaura un docente desactivado."""
        teacher = self.get_object()
        teacher.restore()
        serializer = self.get_serializer(teacher)
        return Response(serializer.data)


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Cursos - API REST completa.
    Endpoints:
    - GET    /api/courses/           - Listar (paginado)
    - POST   /api/courses/           - Crear (solo superuser)
    - GET    /api/courses/{id}/      - Detalle
    - PUT    /api/courses/{id}/      - Actualizar (solo superuser)
    - PATCH  /api/courses/{id}/      - Actualizar parcial (solo superuser)
    - DELETE /api/courses/{id}/      - Borrado lógico (solo superuser)
    """
    queryset = Course.all_objects.select_related('teacher').all()
    permission_classes = [IsAuthenticated, CanManageCourses]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'teacher__first_name', 'teacher__last_name']
    ordering_fields = ['name', 'fecha_creacion']
    ordering = ['name']

    def get_serializer_class(self):
        """Usa serializer optimizado para listado."""
        if self.action == 'list':
            return CourseListSerializer
        return CourseSerializer

    def get_queryset(self):
        """Filtra según parámetros de query."""
        queryset = super().get_queryset()
        # Filtrar por teacher si se proporciona
        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        return queryset

    def perform_destroy(self, instance):
        """Borrado lógico en lugar de eliminación física."""
        instance.soft_delete()

    @action(detail=True, methods=['post'], permission_classes=[CanManageCourses])
    def restore(self, request, pk=None):
        """Restaura un curso desactivado."""
        course = self.get_object()
        course.restore()
        serializer = self.get_serializer(course)
        return Response(serializer.data)


class StudentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Estudiantes - API REST completa.
    Endpoints:
    - GET    /api/students/          - Listar (paginado)
    - POST   /api/students/          - Crear (solo superuser)
    - GET    /api/students/{id}/     - Detalle
    - PUT    /api/students/{id}/     - Actualizar (solo superuser)
    - PATCH  /api/students/{id}/     - Actualizar parcial (solo superuser)
    - DELETE /api/students/{id}/     - Borrado lógico (solo superuser)
    """
    queryset = Student.all_objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated, CanManageStudents]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name']
    ordering_fields = ['last_name', 'first_name', 'fecha_creacion']
    ordering = ['last_name', 'first_name']

    def get_serializer_class(self):
        """Usa serializer optimizado para listado."""
        if self.action == 'list':
            return StudentListSerializer
        return StudentSerializer

    def perform_destroy(self, instance):
        """Borrado lógico en lugar de eliminación física."""
        instance.soft_delete()

    @action(detail=True, methods=['post'], permission_classes=[CanManageStudents])
    def restore(self, request, pk=None):
        """Restaura un estudiante desactivado."""
        student = self.get_object()
        student.restore()
        serializer = self.get_serializer(student)
        return Response(serializer.data)


class StudentCourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Inscripciones - API REST completa.
    PK COMPUESTA: (student_id, course_id) - NO usa 'pk' simple.
    
    Endpoints:
    - GET    /api/enrollments/                    - Listar (paginado)
    - POST   /api/enrollments/                    - Crear inscripción (solo superuser)
    - GET    /api/enrollments/{student_id}/{course_id}/  - Detalle
    - PUT    /api/enrollments/{student_id}/{course_id}/  - Actualizar (solo superuser)
    - DELETE /api/enrollments/{student_id}/{course_id}/  - Borrado lógico (solo superuser)
    """
    queryset = StudentCourse.all_objects.select_related('student', 'course').all()
    serializer_class = StudentCourseSerializer
    permission_classes = [IsAuthenticated, CanManageEnrollments]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['student__first_name', 'student__last_name', 'course__name']
    ordering_fields = ['fecha_creacion']
    ordering = ['-fecha_creacion']

    # Configuración para PK compuesta
    lookup_fields = ['student_id', 'course_id']
    lookup_url_kwargs = ['student_id', 'course_id']

    def get_object(self):
        """
        Obtiene objeto por PK compuesta (student_id, course_id).
        DRF espera 'pk' por defecto, pero usamos dos parámetros.
        """
        queryset = self.filter_queryset(self.get_queryset())
        student_id = self.kwargs.get('student_id')
        course_id = self.kwargs.get('course_id')
        
        if not student_id or not course_id:
            # Fallback para compatibilidad (si se usa pk simple)
            pk = self.kwargs.get('pk')
            if pk and '_' in str(pk):
                student_id, course_id = pk.split('_', 1)
        
        obj = queryset.filter(student_id=student_id, course_id=course_id).first()
        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound('Inscripción no encontrada.')
        
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        """Filtros adicionales por estudiante o curso."""
        queryset = super().get_queryset()
        student_id = self.request.query_params.get('student_id')
        course_id = self.request.query_params.get('course_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset

    def perform_destroy(self, instance):
        """Borrado lógico en lugar de eliminación física."""
        instance.soft_delete()

    @action(detail=True, methods=['post'], permission_classes=[CanManageEnrollments])
    def restore(self, request, student_id=None, course_id=None):
        """Restaura una inscripción desactivada."""
        enrollment = self.get_object()
        enrollment.restore()
        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)