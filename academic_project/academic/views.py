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

from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django_filters.rest_framework import DjangoFilterBackend

from .models import Teacher, Course, Student, StudentCourse, Asignatura
from django.db.models import Prefetch, Count, Q
from .serializers import (
    TeacherSerializer, CourseSerializer, StudentSerializer, StudentCourseSerializer,
    AsignaturaSerializer,
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
    def get(self, request, *args, **kwargs):
        return redirect('courses')


# =============================================================================
# VIEWSETS API REST (DRF)
# =============================================================================

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.all_objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo', 'sexo']
    search_fields = ['first_name', 'last_name']
    ordering_fields = ['last_name', 'first_name', 'fecha_creacion', 'courses_count']
    ordering = ['last_name', 'first_name']

    def get_queryset(self):
        """Superusuarios ven todos (activos e inactivos). Solo activos para el resto."""
        annotate = dict(courses_count=Count('courses', filter=Q(courses__activo=True)))
        base = Teacher.all_objects if self.request.user.is_superuser else Teacher.objects
        return base.annotate(**annotate)

    def get_object(self):
        """Usa el queryset anotado (con cursos_count) y filtra por rol.
        Superusuarios acceden a inactivos (para restaurar); el resto solo a activos."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        try:
            obj = queryset.get(**filter_kwargs)
        except Teacher.DoesNotExist:
            raise NotFound('Docente no encontrado.')
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        """Borrado lógico en lugar de eliminación física."""
        instance.soft_delete()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def restore(self, request, pk=None):
        """Restaura un docente desactivado."""
        teacher = self.get_object()
        teacher.restore()
        serializer = self.get_serializer(teacher)
        return Response(serializer.data)


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.all_objects.select_related('teacher').all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo', 'jornada', 'teacher']
    search_fields = ['name', 'teacher__first_name', 'teacher__last_name']
    ordering_fields = ['name', 'fecha_creacion', 'students_count', 'teacher__last_name', 'teacher__first_name']
    ordering = ['name']

    def get_queryset(self):
        """Superusuarios ven todos (activos e inactivos). Solo activos para el resto."""
        student_courses = Prefetch(
            'student_courses',
            queryset=StudentCourse.all_objects.select_related('student').filter(
                activo=True, student__activo=True
            )
        )
        students_count_annotation = Count(
            'student_courses',
            filter=Q(student_courses__activo=True, student_courses__student__activo=True)
        )
        base = Course.all_objects if self.request.user.is_superuser else Course.objects
        return base.select_related('teacher').prefetch_related(student_courses).annotate(
            students_count=students_count_annotation
        )

    def get_object(self):
        """Usa el queryset anotado (con students_count) y filtra por rol.
        Superusuarios acceden a inactivos (para restaurar); el resto solo a activos."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        try:
            obj = queryset.get(**filter_kwargs)
        except Course.DoesNotExist:
            raise NotFound('Curso no encontrado.')
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        """Borrado lógico en lugar de eliminación física."""
        instance.soft_delete()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def restore(self, request, pk=None):
        """Restaura un curso desactivado."""
        course = self.get_object()
        course.restore()
        serializer = self.get_serializer(course)
        return Response(serializer.data)


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.all_objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo', 'sexo', 'jornada']
    search_fields = ['first_name', 'last_name']
    ordering_fields = ['last_name', 'first_name', 'fecha_creacion', 'courses_count']
    ordering = ['last_name', 'first_name']

    def get_queryset(self):
        """Superusuarios ven todos (activos e inactivos). Solo activos para el resto."""
        courses_count_annotation = Count(
            'student_courses',
            filter=Q(student_courses__activo=True, student_courses__course__activo=True)
        )
        base = Student.all_objects if self.request.user.is_superuser else Student.objects
        return base.annotate(courses_count=courses_count_annotation)

    def get_object(self):
        """Usa el queryset anotado (con courses_count) y filtra por rol.
        Superusuarios acceden a inactivos (para restaurar); el resto solo a activos."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        try:
            obj = queryset.get(**filter_kwargs)
        except Student.DoesNotExist:
            raise NotFound('Estudiante no encontrado.')
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        """Borrado lógico en lugar de eliminación física."""
        instance.soft_delete()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def restore(self, request, pk=None):
        """Restaura un estudiante desactivado."""
        student = self.get_object()
        student.restore()
        serializer = self.get_serializer(student)
        return Response(serializer.data)


class StudentCourseViewSet(viewsets.ModelViewSet):
    queryset = StudentCourse.all_objects.select_related('student', 'course').all()
    serializer_class = StudentCourseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo', 'student', 'course']
    search_fields = ['student__first_name', 'student__last_name', 'course__name']
    ordering_fields = ['fecha_creacion']
    ordering = ['-fecha_creacion']

    def get_object(self):
        """
        Obtiene objeto por PK compuesta (student_id, course_id).
        Superusuarios acceden a inactivas (para restaurar); el resto solo a activas.
        """
        base = StudentCourse.all_objects if self.request.user.is_superuser else StudentCourse.objects
        queryset = base.select_related('student', 'course')
        student_id = self.kwargs.get('student_id')
        course_id = self.kwargs.get('course_id')
        if not student_id or not course_id:
            pk = self.kwargs.get('pk')
            if pk and '_' in str(pk):
                student_id, course_id = pk.split('_', 1)
        try:
            obj = queryset.get(student_id=student_id, course_id=course_id)
        except StudentCourse.DoesNotExist:
            raise NotFound('Inscripción no encontrada.')
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        """Superusuarios ven todas (activas e inactivas); el resto solo activas."""
        if self.request.user.is_superuser:
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

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def restore(self, request, student_id=None, course_id=None):
        """Restaura una inscripción desactivada."""
        enrollment = self.get_object()
        enrollment.restore()
        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)


# =============================================================================
# VIEWSET ASIGNATURA (LIBRE ACCESO: LECTURA PÚBLICA, ESCRITURA CON JWT)
# =============================================================================

class AsignaturaViewSet(viewsets.ModelViewSet):
    queryset = Asignatura.all_objects.all()
    serializer_class = AsignaturaSerializer
    # Lectura pública para cualquiera; crear/editar/eliminar requiere autenticación (JWT o sesión).
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo', 'tipo', 'nivel']
    search_fields = ['nombre', 'codigo']
    ordering_fields = ['nombre', 'codigo', 'creditos', 'fecha_creacion']
    ordering = ['nombre']

    def get_queryset(self):
        """Superusuarios ven todas (activas e inactivas); el resto solo activas."""
        if self.request.user.is_superuser:
            return Asignatura.all_objects.all()
        return Asignatura.objects.all()

    def get_object(self):
        """Usa el queryset filtrado por rol (inactivas solo para superusuarios)."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        try:
            obj = queryset.get(**filter_kwargs)
        except Asignatura.DoesNotExist:
            raise NotFound('Asignatura no encontrada.')
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        """Borrado lógico en lugar de eliminación física."""
        instance.soft_delete()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def restore(self, request, pk=None):
        """Restaura una asignatura desactivada."""
        asignatura = self.get_object()
        asignatura.restore()
        serializer = self.get_serializer(asignatura)
        return Response(serializer.data)