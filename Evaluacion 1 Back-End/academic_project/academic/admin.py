"""
Configuración del panel de administración Django para la app academic.

Registra los modelos con opciones personalizadas:
- Filtros, búsquedas, campos de solo lectura
- Acciones de borrado lógico y restauración
- Visualización de campos relacionados
"""

from django.contrib import admin
from .models import Teacher, Course, Student, StudentCourse


# =============================================================================
# ADMIN BASE CON BORRADO LÓGICO
# =============================================================================

class SoftDeleteAdmin(admin.ModelAdmin):
    """
    Admin base que maneja borrado lógico.
    - Muestra campo 'activo' en listado
    - Acciones para activar/desactivar en masa
    - Filtro por estado activo/inactivo
    """
    list_filter = ('activo', 'fecha_creacion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    actions = ['soft_delete_selected', 'restore_selected']

    def get_queryset(self, request):
        """Muestra TODOS los registros (incluye inactivos) en admin."""
        return self.model.all_objects.all()

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


# =============================================================================
# TEACHER ADMIN
# =============================================================================

@admin.register(Teacher)
class TeacherAdmin(SoftDeleteAdmin):
    list_display = ('id', 'full_name', 'first_name', 'last_name', 'courses_count', 'activo', 'fecha_creacion')
    list_display_links = ('id', 'full_name')
    search_fields = ('first_name', 'last_name')
    ordering = ('last_name', 'first_name')
    list_per_page = 25

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Nombre Completo'

    def courses_count(self, obj):
        return obj.courses_count
    courses_count.short_description = 'Cursos'


# =============================================================================
# COURSE ADMIN
# =============================================================================

@admin.register(Course)
class CourseAdmin(SoftDeleteAdmin):
    list_display = ('id', 'name', 'teacher', 'students_count', 'activo', 'fecha_creacion')
    list_display_links = ('id', 'name')
    list_filter = ('activo', 'teacher', 'fecha_creacion')
    search_fields = ('name', 'teacher__first_name', 'teacher__last_name')
    raw_id_fields = ('teacher',)
    ordering = ('name',)
    list_per_page = 25

    def students_count(self, obj):
        return obj.students_count
    students_count.short_description = 'Estudiantes'


# =============================================================================
# STUDENT ADMIN
# =============================================================================

@admin.register(Student)
class StudentAdmin(SoftDeleteAdmin):
    list_display = ('id', 'full_name', 'first_name', 'last_name', 'courses_count', 'activo', 'fecha_creacion')
    list_display_links = ('id', 'full_name')
    search_fields = ('first_name', 'last_name')
    ordering = ('last_name', 'first_name')
    list_per_page = 25

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Nombre Completo'

    def courses_count(self, obj):
        return obj.courses_count
    courses_count.short_description = 'Cursos'


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

    # Campos de solo lectura para PK compuesta
    readonly_fields = ('student', 'course', 'fecha_creacion', 'fecha_actualizacion')

    def has_add_permission(self, request):
        """Permitir agregar nuevas inscripciones."""
        return True

    def has_change_permission(self, request, obj=None):
        """Permitir cambiar solo el estado activo."""
        return True