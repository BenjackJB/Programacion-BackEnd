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
from django.contrib.auth import logout
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
    """Vista de logout compatible con GET y renderiza una página custom."""
    http_method_names = ['get', 'post', 'options']
    template_name = 'academic/logout.html'

    def get(self, request, *args, **kwargs):
        logout(request)
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        logout(request)
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Sesión cerrada',
            'message': 'Has cerrado sesión correctamente.',
            'login_url': reverse_lazy('login'),
        })
        return context


# =============================================================================
# VISTAS PRINCIPALES (HTML - TEMPLATES)
# =============================================================================

class BaseTemplateView(TemplateView):
    """
    Vista base pública para lectura. Requiere autenticación solo para acciones de escritura.
    """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'user': self.request.user,
            'is_superuser': getattr(self.request.user, 'is_superuser', False),
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


class TeachersView(BaseTemplateView):
    """Vista para listado y gestión de docentes."""
    template_name = 'academic/teachers.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Docentes',
            'page_header': 'Docentes',
            'api_endpoint': '/api/teachers/',
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
    ViewSet para Docentes.
    - Usuarios sin autenticar: lectura permitida.
    - Superusuario: puede escribir y gestionar.
    """
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [IsSuperUserOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name']
    ordering_fields = ['last_name', 'first_name', 'fecha_creacion']
    ordering = ['last_name', 'first_name']

    def get_queryset(self):
        """Superusuario ve todos los registros, incluido inactivos; resto solo activos."""
        if getattr(self, 'action', None) == 'restore':
            return Teacher.all_objects.all()
        if self.request.user.is_authenticated and self.request.user.is_superuser:
            return Teacher.all_objects.all()
        return Teacher.objects.all()

    def get_object(self):
        """Permite recuperar un docente inactivo para PATCH/PUT/DELETE y restauración."""
        queryset = Teacher.all_objects.all()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = queryset.filter(**filter_kwargs).first()
        if obj is None:
            from rest_framework.exceptions import NotFound
            raise NotFound('Docente no encontrado.')
        self.check_object_permissions(self.request, obj)
        return obj

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
    ViewSet para Cursos.
    Lectura pública; escritura solo para superusuarios.
    """
    queryset = Course.objects.select_related('teacher').all()
    permission_classes = [IsSuperUserOrReadOnly]
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
        """Superusuario ve todos los registros; el resto solo activos."""
        if getattr(self, 'action', None) == 'restore':
            queryset = Course.all_objects.select_related('teacher').all()
        elif self.request.user.is_authenticated and self.request.user.is_superuser:
            queryset = Course.all_objects.select_related('teacher').all()
        else:
            queryset = Course.objects.select_related('teacher').all()

        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        return queryset

    def get_object(self):
        """Permite recuperar un curso inactivo para PATCH/PUT/DELETE y restauración."""
        queryset = Course.all_objects.select_related('teacher').all()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = queryset.filter(**filter_kwargs).first()
        if obj is None:
            from rest_framework.exceptions import NotFound
            raise NotFound('Curso no encontrado.')
        self.check_object_permissions(self.request, obj)
        return obj

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
    ViewSet para Estudiantes.
    - Usuarios sin autenticar: lectura permitida.
    - Superusuario: puede escribir y gestionar.
    """
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsSuperUserOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name']
    ordering_fields = ['last_name', 'first_name', 'fecha_creacion']
    ordering = ['last_name', 'first_name']

    def get_queryset(self):
        """Superusuario ve todos los registros, incluso inactivos; resto solo activos."""
        if getattr(self, 'action', None) == 'restore':
            return Student.all_objects.all()
        if self.request.user.is_authenticated and self.request.user.is_superuser:
            return Student.all_objects.all()
        return Student.objects.all()

    def get_object(self):
        """Permite recuperar un estudiante inactivo para PATCH/PUT/DELETE y restauración."""
        queryset = Student.all_objects.all()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = queryset.filter(**filter_kwargs).first()
        if obj is None:
            from rest_framework.exceptions import NotFound
            raise NotFound('Estudiante no encontrado.')
        self.check_object_permissions(self.request, obj)
        return obj

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
    ViewSet para Inscripciones.
    - Usuarios sin autenticar: lectura permitida.
    - Superusuario: puede escribir y gestionar.
    """
    queryset = StudentCourse.objects.select_related('student', 'course').all()
    serializer_class = StudentCourseSerializer
    permission_classes = [IsSuperUserOrReadOnly]
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
        """Superusuario ve todas las inscripciones, incluso inactivas; resto solo activas."""
        if getattr(self, 'action', None) == 'restore':
            queryset = StudentCourse.all_objects.select_related('student', 'course').all()
        elif self.request.user.is_authenticated and self.request.user.is_superuser:
            queryset = StudentCourse.all_objects.select_related('student', 'course').all()
        else:
            queryset = StudentCourse.objects.select_related('student', 'course').all()

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