"""
Serializers para Django REST Framework.

Mapean los modelos (Teacher, Course, Student, StudentCourse) a representaciones JSON
para los endpoints de la API. Incluyen campos relacionados y validaciones.

NOTA: StudentCourse usa PK compuesta (student, course) sin campo 'id' propio.
"""

from rest_framework import serializers
from .models import Teacher, Course, Student, StudentCourse


# =============================================================================
# SERIALIZER TEACHER
# =============================================================================

class TeacherSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Teacher.
    Incluye campo computado 'full_name' y conteo de cursos.
    """
    full_name = serializers.ReadOnlyField()
    courses_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Teacher
        fields = ['id', 'first_name', 'last_name', 'full_name', 'courses_count', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion', 'courses_count', 'full_name']


# =============================================================================
# SERIALIZER COURSE
# =============================================================================

class CourseSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Course.
    Incluye datos del teacher relacionado y conteo de estudiantes.
    """
    teacher = TeacherSerializer(read_only=True)
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='teacher',
        write_only=True,
        help_text='ID del docente asignado'
    )
    students_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'name', 'teacher', 'teacher_id', 'students_count', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion', 'students_count']


# =============================================================================
# SERIALIZER STUDENT
# =============================================================================

class StudentSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Student.
    Incluye campo computado 'full_name' y conteo de cursos.
    """
    full_name = serializers.ReadOnlyField()
    courses_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'first_name', 'last_name', 'full_name', 'courses_count', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion', 'courses_count', 'full_name']


# =============================================================================
# SERIALIZER STUDENTCOURSE (INSCRIPCIONES - PK COMPUESTA)
# =============================================================================

class StudentCourseSerializer(serializers.ModelSerializer):
    """
    Serializer para inscripciones (StudentCourse) con PK COMPUESTA.
    No tiene campo 'id' - la PK es (student, course).
    Para lectura: incluye objetos anidados student y course.
    Para escritura: usa student_id y course_id.
    """
    student = StudentSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.filter(activo=True),
        source='student',
        write_only=True,
        help_text='ID del estudiante'
    )
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.filter(activo=True),
        source='course',
        write_only=True,
        help_text='ID del curso'
    )

    class Meta:
        model = StudentCourse
        # Sin 'id' - PK compuesta es (student, course)
        fields = ['student', 'course', 'student_id', 'course_id', 'activo', 'fecha_creacion']
        read_only_fields = ['fecha_creacion']

    def validate(self, attrs):
        """Validación personalizada: evitar inscripciones duplicadas."""
        student = attrs.get('student')
        course = attrs.get('course')
        if student and course:
            # Verificar si ya existe inscripción activa
            exists = StudentCourse.objects.filter(
                student=student,
                course=course,
                activo=True
            ).exists()
            if exists and not self.instance:
                raise serializers.ValidationError(
                    'El estudiante ya está inscrito en este curso.'
                )
        return attrs

    def create(self, validated_data):
        """Crea inscripción usando PK compuesta."""
        return StudentCourse.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Actualiza inscripción - PK compuesta no se modifica."""
        # No permitir cambiar student/course (son la PK)
        validated_data.pop('student', None)
        validated_data.pop('course', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# =============================================================================
# SERIALIZERS ESPECIALES PARA VISTAS ESPECÍFICAS (LISTADOS)
# =============================================================================

class CourseListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listado de cursos (vista courses.html).
<<<<<<< HEAD
    Incluye solo campos necesarios: id, name, teacher, activo, estudiantes, fechas.
    """
    teacher = TeacherSerializer(read_only=True)
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='teacher',
        write_only=True,
        help_text='ID del docente asignado'
    )
    students_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'name', 'teacher', 'teacher_id', 'students_count', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion', 'students_count']
=======
    Incluye solo campos necesarios: id, name, teacher (nombre).
    """
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'name', 'teacher_name']
        read_only_fields = fields
>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0


class StudentListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listado de estudiantes (vista students.html).
<<<<<<< HEAD
    Incluye solo campos necesarios: id, full_name, cursos, activo, fechas.
    """
    full_name = serializers.ReadOnlyField()
    courses_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'first_name', 'last_name', 'full_name', 'courses_count', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion', 'courses_count', 'full_name']
=======
    Incluye solo campos necesarios: id, full_name.
    """
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Student
        fields = ['id', 'full_name']
        read_only_fields = fields
>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0
