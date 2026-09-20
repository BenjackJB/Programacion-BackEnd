"""
Configuración del panel de administración Django para la app academic.

Registra los modelos con opciones personalizadas:
- Filtros, búsquedas, campos de solo lectura
- Acciones de borrado lógico y restauración
- Visualización de campos relacionados
"""

from django.contrib import admin
from .models import Teacher, Course, Student, StudentCourse, Asignatura


# =============================================================================
# ADMIN BASE CON BORRADO LÓGICO
# =============================================================================

class SoftDeleteAdmin(admin.ModelAdmin):
    """
    Admin base que maneja borrado lógico.
    - Muestra solo registros ACTIVOS en el listado
    - Acciones para activar/desactivar en masa
    - Filtro por estado activo/inactivo
    - Delete físico (no soft delete) para limpiar BD
    """
    list_filter = ('activo', 'fecha_creacion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    actions = ['soft_delete_selected', 'restore_selected', 'hard_delete_selected']

    def get_queryset(self, request):
        """Superusuario ve también registros inactivos; el resto solo activos."""
        if request.user.is_authenticated and request.user.is_superuser:
            return self.model.all_objects.all()
        return self.model.objects.all()

    @admin.action(description='Desactivar seleccionados (borrado lógico)')
    def soft_delete_selected(self, request, queryset):
        updated = 0
        for obj in queryset:
            if obj.activo:
                obj.soft_delete()
                updated += 1
        self.message_user(request, f'{updated} registro(s) desactivado(s).')

    @admin.action(description='Restaurar seleccionados')
    def restore_selected(self, request, queryset):
        updated = 0
        for obj in queryset:
            if not obj.activo:
                obj.restore()
                updated += 1
        self.message_user(request, f'{updated} registro(s) restaurado(s).')

    @admin.action(description='Eliminar permanentemente seleccionados')
    def hard_delete_selected(self, request, queryset):
        """Borrado físico de la base de datos."""
        count = queryset.delete()[0]
        self.message_user(request, f'{count} registro(s) eliminado(s) permanentemente.')


# =============================================================================
# TEACHER ADMIN
# =============================================================================

@admin.register(Teacher)
class TeacherAdmin(SoftDeleteAdmin):
    list_display = ('id', 'full_name', 'first_name', 'last_name', 'sexo', 'courses_count', 'activo', 'fecha_creacion')
    list_display_links = ('id', 'full_name')
    list_filter = ('activo', 'sexo', 'fecha_creacion')
    search_fields = ('first_name', 'last_name')
    ordering = ('last_name', 'first_name')
    list_per_page = 25

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Nombre Completo'

    def courses_count(self, obj):
        return obj.courses.filter(activo=True).count()
    courses_count.short_description = 'Cursos'


# =============================================================================
# COURSE ADMIN
# =============================================================================

@admin.register(Course)
class CourseAdmin(SoftDeleteAdmin):
    list_display = ('id', 'codigo', 'name', 'teacher', 'jornada', 'students_count', 'activo', 'fecha_creacion')
    list_display_links = ('id', 'codigo')
    list_filter = ('activo', 'jornada', 'teacher', 'fecha_creacion')
    search_fields = ('codigo', 'name', 'teacher__first_name', 'teacher__last_name')
    raw_id_fields = ('teacher',)
    ordering = ('codigo',)
    list_per_page = 25

    def students_count(self, obj):
        return obj.student_courses.filter(activo=True, student__activo=True).count()
    students_count.short_description = 'Estudiantes'


# =============================================================================
# STUDENT ADMIN
# =============================================================================

@admin.register(Student)
class StudentAdmin(SoftDeleteAdmin):
    list_display = ('id', 'full_name', 'first_name', 'last_name', 'sexo', 'jornada', 'courses_count', 'activo', 'fecha_creacion')
    list_display_links = ('id', 'full_name')
    list_filter = ('activo', 'sexo', 'jornada', 'fecha_creacion')
    search_fields = ('first_name', 'last_name')
    ordering = ('last_name', 'first_name')
    list_per_page = 25

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Nombre Completo'

    def courses_count(self, obj):
        return obj.student_courses.filter(activo=True, course__activo=True).count()
    courses_count.short_description = 'Cursos'


# =============================================================================
# ASIGNATURA ADMIN
# =============================================================================

@admin.register(Asignatura)
class AsignaturaAdmin(SoftDeleteAdmin):
    list_display = ('id', 'codigo', 'nombre', 'tipo', 'nivel', 'creditos', 'activo', 'fecha_creacion')
    list_display_links = ('id', 'nombre')
    list_filter = ('activo', 'tipo', 'nivel', 'fecha_creacion')
    search_fields = ('nombre', 'codigo')
    ordering = ('nombre',)
    list_per_page = 25


# =============================================================================
# STUDENTCOURSE ADMIN (INSCRIPCIONES)
# =============================================================================

@admin.register(StudentCourse)
class StudentCourseAdmin(SoftDeleteAdmin):
    list_display = ('student', 'course', 'activo', 'fecha_creacion')
    list_display_links = ('student', 'course')
    list_filter = ('activo', 'course', 'student', 'fecha_creacion')
    search_fields = ('student__first_name', 'student__last_name', 'course__name')
    raw_id_fields = ('student', 'course')
    ordering = ('-fecha_creacion',)
    list_per_page = 30

    # Campos de solo lectura para PK compuesta (solo al editar, no al crear)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

    def get_readonly_fields(self, request, obj=None):
        """Al editar una inscripción, student/course (PK) no se pueden cambiar."""
        if obj:
            return ('student', 'course', 'fecha_creacion', 'fecha_actualizacion')
        return self.readonly_fields

    def has_add_permission(self, request):
        """Permitir agregar nuevas inscripciones."""
        return True

    def has_change_permission(self, request, obj=None):
        """Permitir cambiar solo el estado activo."""
        return True