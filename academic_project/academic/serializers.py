"""
Serializers para Django REST Framework.

Mapean los modelos (Teacher, Course, Student, StudentCourse) a representaciones JSON
para los endpoints de la API. Incluyen campos relacionados y validaciones.

NOTA: StudentCourse usa PK compuesta (student, course) sin campo 'id' propio.
"""

from rest_framework import serializers
from .models import Teacher, Course, Student, StudentCourse, Asignatura


# =============================================================================
# SERIALIZER TEACHER
# =============================================================================

class TeacherSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    courses_count = serializers.SerializerMethodField()
    activo = serializers.BooleanField(required=False, default=True)
    sexo = serializers.ChoiceField(required=False, default='M', choices=['M', 'F', 'O'], help_text='Sexo: M=Masculino, F=Femenino, O=Otro')

    def get_courses_count(self, obj):
        if hasattr(obj, 'courses_count') and obj.courses_count is not None:
            return obj.courses_count
        return obj.courses.filter(activo=True).count() if hasattr(obj, 'courses') else 0

    class Meta:
        model = Teacher
        fields = ['id', 'first_name', 'last_name', 'full_name', 'sexo', 'courses_count', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion', 'courses_count', 'full_name']


class TeacherBriefSerializer(serializers.ModelSerializer):
    """Versión ligera de Teacher para anidar en otros serializers (sin N+1)."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Teacher
        fields = ['id', 'first_name', 'last_name', 'full_name', 'sexo', 'activo']


# =============================================================================
# SERIALIZER COURSE
# =============================================================================

class CourseSerializer(serializers.ModelSerializer):
    teacher = TeacherSerializer(read_only=True)
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='teacher',
        write_only=True,
        help_text='ID del docente asignado'
    )
    students_count = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    activo = serializers.BooleanField(required=False, default=True)
    jornada = serializers.ChoiceField(required=False, default='D', choices=['D', 'V'], help_text='Jornada: D=Diurna, V=Vespertina')

    def get_students_count(self, obj):
        if hasattr(obj, 'students_count') and obj.students_count is not None:
            return obj.students_count
        return obj.student_courses.filter(activo=True, student__activo=True).count() if hasattr(obj, 'student_courses') else 0

    def get_students(self, obj):
        # Usa el cache de prefetch_related si existe; si no, ejecuta una sola query.
        students = [
            enrollment.student
            for enrollment in obj.student_courses.all()
            if enrollment.activo is not False and enrollment.student.activo
        ]
        return StudentBriefSerializer(students, many=True).data

    class Meta:
        model = Course
        fields = ['id', 'name', 'teacher', 'teacher_id', 'jornada', 'students_count', 'students', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion', 'students_count']


class CourseBriefSerializer(serializers.ModelSerializer):
    """Versión ligera de Course para anidar en otros serializers (sin N+1)."""
    teacher = TeacherBriefSerializer(read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'name', 'teacher', 'jornada', 'activo']


# =============================================================================
# SERIALIZER STUDENT
# =============================================================================

class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    courses_count = serializers.SerializerMethodField()
    activo = serializers.BooleanField(required=False, default=True)
    sexo = serializers.ChoiceField(required=False, default='M', choices=['M', 'F', 'O'], help_text='Sexo: M=Masculino, F=Femenino, O=Otro')
    jornada = serializers.ChoiceField(required=False, default='D', choices=['D', 'V'], help_text='Jornada: D=Diurna, V=Vespertina')

    def get_courses_count(self, obj):
        if hasattr(obj, 'courses_count') and obj.courses_count is not None:
            return obj.courses_count
        return obj.student_courses.filter(activo=True, course__activo=True).count() if hasattr(obj, 'student_courses') else 0

    class Meta:
        model = Student
        fields = ['id', 'first_name', 'last_name', 'full_name', 'sexo', 'jornada', 'courses_count', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion', 'courses_count', 'full_name']


class StudentBriefSerializer(serializers.ModelSerializer):
    """Versión ligera de Student para anidar en otros serializers (sin N+1)."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Student
        fields = ['id', 'first_name', 'last_name', 'full_name', 'sexo', 'jornada', 'activo']


# =============================================================================
# SERIALIZER ASIGNATURA
# =============================================================================

class AsignaturaSerializer(serializers.ModelSerializer):
    tipo = serializers.ChoiceField(
        required=False,
        default='O',
        choices=Asignatura.TIPO_CHOICES,
        help_text='Tipo: O=Obligatoria, E=Electiva'
    )
    nivel = serializers.ChoiceField(
        required=False,
        default='1',
        choices=Asignatura.NIVEL_CHOICES,
        help_text='Nivel: 1=Primer año ... 5=Quinto año'
    )
    activo = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Asignatura
        fields = ['id', 'codigo', 'nombre', 'descripcion', 'creditos', 'tipo', 'nivel', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion']


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
    student = StudentBriefSerializer(read_only=True)
    course = CourseBriefSerializer(read_only=True)
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
    activo = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = StudentCourse
        # Sin 'id' - PK compuesta es (student, course)
        fields = ['student', 'course', 'student_id', 'course_id', 'activo', 'fecha_creacion']
        read_only_fields = ['fecha_creacion']

    def validate(self, attrs):
        """Validación personalizada: evitar inscripciones duplicadas y estado inválido."""
        if self.instance is None:
            # Creación: no permitir duplicados (ni siquiera si la inscripción existente está inactiva,
            # porque la UniqueConstraint (student, course) impediría el INSERT y causaría un 500).
            student = attrs.get('student')
            course = attrs.get('course')
            if student and course:
                if not student.activo:
                    raise serializers.ValidationError(
                        {'student': 'No se puede inscribir un estudiante inactivo.'}
                    )
                if not course.activo:
                    raise serializers.ValidationError(
                        {'course': 'No se puede inscribir en un curso inactivo.'}
                    )
                if StudentCourse.all_objects.filter(student=student, course=course).exists():
                    raise serializers.ValidationError(
                        'El estudiante ya tiene una inscripción en este curso. '
                        'Restáurela si estaba desactivada.'
                    )
        else:
            # Actualización: no permitir activar una inscripción de estudiante/curso inactivo.
            activo = attrs.get('activo', self.instance.activo)
            if activo and (not self.instance.student.activo or not self.instance.course.activo):
                raise serializers.ValidationError(
                    'No se puede activar una inscripción de un estudiante o curso inactivo.'
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