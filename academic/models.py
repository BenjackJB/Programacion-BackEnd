"""
Modelos de datos para el sistema de gestión académica.

Entidades según modelo ER:
- Teacher (Docentes)
- Course (Asignaturas)
- Student (Estudiantes)
- StudentCourse (Inscripciones - tabla intermedia Many-to-Many con PK compuesta)

IMPORTANTE: Borrado lógico (soft delete) - NO se eliminan registros físicamente.
Se usa campo 'activo' (Boolean) para marcar como desactivado.

NOTA: student_course usa PK compuesta (student_id, course_id) sin columna id propia,
conforme al modelo SQL especificado.
"""

from django.db import models
from django.db.models import Manager, UniqueConstraint


# =============================================================================
# MANAGER PERSONALIZADO PARA BORRADO LÓGICO
# =============================================================================

class ActiveManager(Manager):
    """
    Manager que filtra solo registros activos (activo=True).
    Oculta automáticamente los registros desactivados (borrado lógico).
    """
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)

    def all_with_inactive(self):
        """Retorna todos los registros incluyendo inactivos (para admin)."""
        return super().get_queryset()


class InactiveManager(Manager):
    """Manager para consultar solo registros inactivos."""
    def get_queryset(self):
        return super().get_queryset().filter(activo=False)


# =============================================================================
# MODELO BASE ABSTRACTO CON BORRADO LÓGICO
# =============================================================================

class BaseModel(models.Model):
    """
    Modelo base abstracto que implementa borrado lógico.
    Todos los modelos heredarán: id, activo, fecha_creacion, fecha_actualizacion.
    """
    id = models.BigAutoField(primary_key=True, verbose_name='ID')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Fecha actualización')

    # Managers: objects = solo activos, all_objects = todos (incluye inactivos)
    objects = ActiveManager()
    all_objects = Manager()  # Manager por defecto de Django (sin filtros)
    inactive_objects = InactiveManager()

    class Meta:
        abstract = True
        ordering = ['-fecha_creacion']

    def soft_delete(self):
        """
        Borrado lógico: marca el registro como inactivo en lugar de eliminarlo.
        No ejecuta DELETE en la base de datos.
        """
        self.activo = False
        self.save(update_fields=['activo', 'fecha_actualizacion'])

    def restore(self):
        """Restaura un registro desactivado (activo=True)."""
        self.activo = True
        self.save(update_fields=['activo', 'fecha_actualizacion'])

    def delete(self, using=None, keep_parents=False):
        """
        Sobrescribe delete() para forzar borrado lógico siempre.
        NOTA: Esto evita el borrado físico accidental.
        """
        self.soft_delete()


# =============================================================================
# MODELO TEACHER (DOCENTES)
# =============================================================================

class Teacher(BaseModel):
    """
    Docente de la institución.
    Campos: id, first_name, last_name, activo, fechas (heredados de BaseModel).
    Tabla: teacher
    """
    first_name = models.CharField(max_length=100, verbose_name='Nombre')
    last_name = models.CharField(max_length=100, verbose_name='Apellido')

    class Meta:
        db_table = 'teacher'
        verbose_name = 'Docente'
        verbose_name_plural = 'Docentes'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        """Retorna nombre completo del docente."""
        return f"{self.first_name} {self.last_name}"

    @property
    def courses_count(self):
        """Cantidad de cursos asignados (solo activos)."""
        return self.courses.filter(activo=True).count()


# =============================================================================
# MODELO COURSE (ASIGNATURAS)
# =============================================================================

class Course(BaseModel):
    """
    Asignatura/Curso impartido por un docente.
    Campos: id, name, teacher (FK), activo, fechas.
    Tabla: course
    Relación: Un docente dicta muchos cursos (1:N)
    """
    name = models.CharField(max_length=100, verbose_name='Nombre del curso')
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,  # PROTECT evita borrar teacher si tiene cursos
        related_name='courses',
        verbose_name='Docente'
    )

    class Meta:
        db_table = 'course'
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def students_count(self):
        """Cantidad de estudiantes inscritos (solo activos)."""
        return self.student_courses.filter(activo=True, student__activo=True).count()


# =============================================================================
# MODELO STUDENT (ESTUDIANTES)
# =============================================================================

class Student(BaseModel):
    """
    Estudiante de la institución.
    Campos: id, first_name, last_name, activo, fechas.
    Tabla: student
    """
    first_name = models.CharField(max_length=100, verbose_name='Nombre')
    last_name = models.CharField(max_length=100, verbose_name='Apellido')

    class Meta:
        db_table = 'student'
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        """Retorna nombre completo del estudiante."""
        return f"{self.first_name} {self.last_name}"

    @property
    def courses_count(self):
        """Cantidad de cursos inscritos (solo activos)."""
        return self.student_courses.filter(activo=True, course__activo=True).count()


# =============================================================================
# MODELO STUDENTCOURSE (INSCRIPCIONES - TABLA INTERMEDIA CON PK COMPUESTA)
# =============================================================================

class StudentCourse(models.Model):
    """
    Inscripción de un estudiante en un curso.
    Se usa una restricción única sobre (student, course) para evitar duplicados,
    sin crear una clave primaria compuesta no soportada por Django.
    """
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name='student_courses',
        verbose_name='Estudiante',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='student_courses',
        verbose_name='Curso',
    )

    # Campos de borrado lógico y auditoría
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Fecha actualización')

    # Managers personalizados para borrado lógico
    objects = ActiveManager()
    all_objects = Manager()
    inactive_objects = InactiveManager()

    class Meta:
        db_table = 'student_course'
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        ordering = ['-fecha_creacion']
        constraints = [
            UniqueConstraint(fields=['student', 'course'], name='unique_student_course_pk'),
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.course.name}"

    def clean(self):
        """Validación adicional antes de guardar."""
        from django.core.exceptions import ValidationError
        # Solo validar si se intenta crear una inscripción activa con estudiante/curso inactivos
        # No validar durante soft delete (cuando activo=False)
        if self.activo:
            if not self.student.activo:
                raise ValidationError('No se puede inscribir un estudiante inactivo.')
            if not self.course.activo:
                raise ValidationError('No se puede inscribir en un curso inactivo.')

    def save(self, *args, **kwargs):
        """Sobrescribe save para ejecutar validaciones."""
        # No validar si solo se actualiza el campo activo (soft delete)
        if not kwargs.get('update_fields'):
            self.full_clean()
        super().save(*args, **kwargs)

    def soft_delete(self):
        """Borrado lógico: marca como inactivo."""
        self.activo = False
        self.save(update_fields=['activo', 'fecha_actualizacion'])

    def restore(self):
        """Restaura inscripción desactivada."""
        self.activo = True
        self.save(update_fields=['activo', 'fecha_actualizacion'])

    def delete(self, using=None, keep_parents=False):
        """Forza borrado lógico siempre."""
        self.soft_delete()