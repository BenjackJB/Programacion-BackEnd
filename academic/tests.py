"""
Pruebas unitarias para la app academic.

Cubre:
- Modelos (creación, borrado lógico, propiedades)
- Serializers (validación, campos)
- Vistas API (endpoints, permisos)
- Vistas HTML (renderizado, autenticación)
"""

from django.test import TestCase, Client
<<<<<<< HEAD
from django.contrib import admin
=======
>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Teacher, Course, Student, StudentCourse


# =============================================================================
# TESTS DE MODELOS
# =============================================================================

class TeacherModelTest(TestCase):
    """Pruebas para el modelo Teacher."""

    def setUp(self):
        self.teacher = Teacher.objects.create(
            first_name='Juan',
            last_name='Pérez'
        )

    def test_teacher_creation(self):
        """Verifica creación correcta de docente."""
        self.assertEqual(self.teacher.first_name, 'Juan')
        self.assertEqual(self.teacher.last_name, 'Pérez')
        self.assertTrue(self.teacher.activo)
        self.assertIsNotNone(self.teacher.fecha_creacion)

    def test_teacher_str(self):
        """Verifica representación string."""
        self.assertEqual(str(self.teacher), 'Juan Pérez')

    def test_teacher_full_name_property(self):
        """Verifica propiedad full_name."""
        self.assertEqual(self.teacher.full_name, 'Juan Pérez')

    def test_teacher_soft_delete(self):
        """Verifica borrado lógico."""
        self.teacher.soft_delete()
        self.assertFalse(self.teacher.activo)
        # No debe aparecer en queryset por defecto
        self.assertNotIn(self.teacher, Teacher.objects.all())
        # Pero sí en all_objects
        self.assertIn(self.teacher, Teacher.all_objects.all())

    def test_teacher_restore(self):
        """Verifica restauración."""
        self.teacher.soft_delete()
        self.teacher.restore()
        self.assertTrue(self.teacher.activo)
        self.assertIn(self.teacher, Teacher.objects.all())


class CourseModelTest(TestCase):
    """Pruebas para el modelo Course."""

    def setUp(self):
        self.teacher = Teacher.objects.create(first_name='María', last_name='González')
        self.course = Course.objects.create(name='Matemáticas', teacher=self.teacher)

    def test_course_creation(self):
        """Verifica creación correcta de curso."""
        self.assertEqual(self.course.name, 'Matemáticas')
        self.assertEqual(self.course.teacher, self.teacher)
        self.assertTrue(self.course.activo)

    def test_course_teacher_relationship(self):
        """Verifica relación con docente."""
        self.assertEqual(self.course.teacher.full_name, 'María González')
        self.assertIn(self.course, self.teacher.courses.all())


class StudentModelTest(TestCase):
    """Pruebas para el modelo Student."""

    def setUp(self):
        self.student = Student.objects.create(first_name='Carlos', last_name='López')

    def test_student_creation(self):
        """Verifica creación correcta de estudiante."""
        self.assertEqual(self.student.first_name, 'Carlos')
        self.assertEqual(self.student.last_name, 'López')
        self.assertTrue(self.student.activo)

    def test_student_full_name_property(self):
        """Verifica propiedad full_name."""
        self.assertEqual(self.student.full_name, 'Carlos López')


class StudentCourseModelTest(TestCase):
    """Pruebas para el modelo StudentCourse (PK compuesta)."""

    def setUp(self):
        self.teacher = Teacher.objects.create(first_name='Ana', last_name='Martínez')
        self.course = Course.objects.create(name='Física', teacher=self.teacher)
        self.student = Student.objects.create(first_name='Laura', last_name='Sánchez')
        self.enrollment = StudentCourse.objects.create(
            student=self.student,
            course=self.course
        )

    def test_enrollment_creation(self):
        """Verifica creación de inscripción con PK compuesta."""
        self.assertEqual(self.enrollment.student, self.student)
        self.assertEqual(self.enrollment.course, self.course)
        self.assertTrue(self.enrollment.activo)
        # No tiene campo id propio
        self.assertFalse(hasattr(self.enrollment, 'id') or self.enrollment.pk is not None)

    def test_composite_pk_unique_constraint(self):
        """Verifica que no se puede duplicar inscripción."""
        with self.assertRaises(Exception):
            StudentCourse.objects.create(
                student=self.student,
                course=self.course
            )

    def test_enrollment_soft_delete(self):
        """Verifica borrado lógico de inscripción."""
        self.enrollment.soft_delete()
        self.assertFalse(self.enrollment.activo)
        self.assertNotIn(self.enrollment, StudentCourse.objects.all())


# =============================================================================
# TESTS DE SERIALIZERS
# =============================================================================

class TeacherSerializerTest(TestCase):
    """Pruebas para TeacherSerializer."""

    def setUp(self):
        self.teacher = Teacher.objects.create(first_name='Pedro', last_name='Gómez')
        from .serializers import TeacherSerializer
        self.serializer = TeacherSerializer(self.teacher)

    def test_contains_expected_fields(self):
        """Verifica campos esperados en serializer."""
        data = self.serializer.data
        expected = ['id', 'first_name', 'last_name', 'full_name', 'courses_count', 'activo', 'fecha_creacion']
        for field in expected:
            self.assertIn(field, data)

    def test_full_name_field(self):
        """Verifica campo computado full_name."""
        self.assertEqual(self.serializer.data['full_name'], 'Pedro Gómez')


class CourseSerializerTest(TestCase):
    """Pruebas para CourseSerializer."""

    def setUp(self):
        self.teacher = Teacher.objects.create(first_name='Lucía', last_name='Fernández')
        self.course = Course.objects.create(name='Química', teacher=self.teacher)
        from .serializers import CourseSerializer
        self.serializer = CourseSerializer(self.course)

    def test_contains_teacher_nested(self):
        """Verifica teacher anidado en serializer."""
        data = self.serializer.data
        self.assertIn('teacher', data)
        self.assertEqual(data['teacher']['full_name'], 'Lucía Fernández')


class StudentCourseSerializerTest(TestCase):
    """Pruebas para StudentCourseSerializer (PK compuesta)."""

    def setUp(self):
        self.teacher = Teacher.objects.create(first_name='Test', last_name='Teacher')
        self.course = Course.objects.create(name='Test Course', teacher=self.teacher)
        self.student = Student.objects.create(first_name='Test', last_name='Student')
        self.enrollment = StudentCourse.objects.create(
            student=self.student,
            course=self.course
        )
        from .serializers import StudentCourseSerializer
        self.serializer = StudentCourseSerializer(self.enrollment)

    def test_no_id_field(self):
        """Verifica que NO hay campo 'id' (PK compuesta)."""
        data = self.serializer.data
        self.assertNotIn('id', data)

    def test_contains_student_and_course(self):
        """Verifica campos student y course anidados."""
        data = self.serializer.data
        self.assertIn('student', data)
        self.assertIn('course', data)
        self.assertEqual(data['student']['full_name'], 'Test Student')
        self.assertEqual(data['course']['name'], 'Test Course')


# =============================================================================
# TESTS DE API ENDPOINTS
# =============================================================================

class TeacherAPITest(APITestCase):
    """Pruebas para endpoints API de Teacher."""

    def setUp(self):
        self.user = User.objects.create_superuser('profe', 'profe@test.com', '123456')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.teacher = Teacher.objects.create(first_name='API', last_name='Teacher')

    def test_list_teachers(self):
        """GET /api/teachers/"""
        url = reverse('teacher-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_teacher(self):
        """POST /api/teachers/"""
        url = reverse('teacher-list')
        data = {'first_name': 'Nuevo', 'last_name': 'Docente'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Teacher.objects.count(), 2)

    def test_retrieve_teacher(self):
        """GET /api/teachers/{id}/"""
        url = reverse('teacher-detail', kwargs={'pk': self.teacher.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'API Teacher')

    def test_soft_delete_teacher(self):
        """DELETE /api/teachers/{id}/ - borrado lógico"""
        url = reverse('teacher-detail', kwargs={'pk': self.teacher.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.teacher.refresh_from_db()
        self.assertFalse(self.teacher.activo)


class CourseAPITest(APITestCase):
    """Pruebas para endpoints API de Course."""

    def setUp(self):
        self.user = User.objects.create_superuser('profe', 'profe@test.com', '123456')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.teacher = Teacher.objects.create(first_name='Prof', last_name='Test')
        self.course = Course.objects.create(name='Curso API', teacher=self.teacher)

    def test_list_courses(self):
        """GET /api/courses/"""
        url = reverse('course-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_course(self):
        """POST /api/courses/"""
        url = reverse('course-list')
        data = {'name': 'Nuevo Curso', 'teacher_id': self.teacher.pk}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

<<<<<<< HEAD
    def test_activate_inactive_course(self):
        """PATCH /api/courses/{id}/ - activa un curso desactivado."""
        self.course.soft_delete()
        url = reverse('course-detail', kwargs={'pk': self.course.pk})
        response = self.client.patch(url, {'activo': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertTrue(self.course.activo)

=======
>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0

class StudentAPITest(APITestCase):
    """Pruebas para endpoints API de Student."""

    def setUp(self):
        self.user = User.objects.create_superuser('profe', 'profe@test.com', '123456')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.student = Student.objects.create(first_name='Est', last_name='UDIANTE')

    def test_list_students(self):
        """GET /api/students/"""
        url = reverse('student-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

<<<<<<< HEAD
    def test_activate_inactive_student(self):
        """PATCH /api/students/{id}/ - activa un estudiante desactivado."""
        self.student.soft_delete()
        url = reverse('student-detail', kwargs={'pk': self.student.pk})
        response = self.client.patch(url, {'activo': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertTrue(self.student.activo)

=======
>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0

class StudentCourseAPITest(APITestCase):
    """Pruebas para endpoints API de StudentCourse (PK compuesta)."""

    def setUp(self):
        self.user = User.objects.create_superuser('profe', 'profe@test.com', '123456')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.teacher = Teacher.objects.create(first_name='T', last_name='T')
        self.course = Course.objects.create(name='Curso', teacher=self.teacher)
        self.student = Student.objects.create(first_name='Est', last_name='Udiante')
        self.enrollment = StudentCourse.objects.create(
            student=self.student,
            course=self.course
        )

    def test_list_enrollments(self):
        """GET /api/enrollments/"""
        url = reverse('enrollment-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_enrollment(self):
        """POST /api/enrollments/"""
        url = reverse('enrollment-list')
        data = {'student_id': self.student.pk, 'course_id': self.course.pk}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_enrollment_composite_pk(self):
        """GET /api/enrollments/{student_id}/{course_id}/"""
        # Usar URL personalizada para PK compuesta
        url = f'/api/enrollments/{self.student.pk}/{self.course.pk}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# =============================================================================
# TESTS DE VISTAS HTML (TEMPLATES)
# =============================================================================

class HTMLViewsTest(TestCase):
    """Pruebas para vistas HTML (templates)."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'password123')
        self.client = Client()
        self.teacher = Teacher.objects.create(first_name='HTML', last_name='Teacher')
        self.course = Course.objects.create(name='Curso HTML', teacher=self.teacher)
        self.student = Student.objects.create(first_name='HTML', last_name='Student')

    def test_login_page_accessible(self):
        """Verifica que login es accesible sin autenticación."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academic/login.html')

<<<<<<< HEAD
    def test_courses_are_visible_without_login(self):
        """Verifica que la vista de cursos es pública para lectura."""
        response = self.client.get(reverse('courses'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academic/courses.html')
        self.assertContains(response, 'Cursos y Docentes Asignados')
=======
    def test_courses_requires_login(self):
        """Verifica que courses requiere autenticación."""
        response = self.client.get(reverse('courses'))
        self.assertEqual(response.status_code, 302)  # Redirect a login
>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0

    def test_courses_with_login(self):
        """Verifica courses con usuario autenticado."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('courses'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academic/courses.html')
        self.assertContains(response, 'Cursos y Docentes Asignados')

    def test_students_with_login(self):
        """Verifica students con usuario autenticado."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('students'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academic/students.html')
        self.assertContains(response, 'Estudiantes Inscritos')

<<<<<<< HEAD
    def test_teachers_are_visible_without_login(self):
        """Verifica que la vista de docentes es pública para lectura."""
        response = self.client.get(reverse('teachers'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academic/teachers.html')
        self.assertContains(response, 'Docentes')

    def test_teachers_with_login(self):
        """Verifica docentes con usuario autenticado."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('teachers'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academic/teachers.html')
        self.assertContains(response, 'Docentes')

=======
>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0
    def test_home_redirects_to_courses(self):
        """Verifica que raíz redirige a courses."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('courses'))

<<<<<<< HEAD
    def test_logout_renders_template_and_clears_session(self):
        """Verifica que el logout por GET cierra sesión y muestra la página de cierre."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academic/logout.html')
        self.assertFalse(response.wsgi_request.user.is_authenticated)

=======
>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0

# =============================================================================
# TESTS DE PERMISOS
# =============================================================================

class PermissionsTest(APITestCase):
    """Pruebas de permisos y autenticación."""

    def setUp(self):
        self.superuser = User.objects.create_superuser('profe', 'profe@test.com', '123456')
        self.normal_user = User.objects.create_user('student', 'student@test.com', 'password')
        self.teacher = Teacher.objects.create(first_name='Perm', last_name='Test')
        self.client = APIClient()

    def test_superuser_full_access(self):
        """Superusuario tiene acceso total."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post('/api/teachers/', {'first_name': 'New', 'last_name': 'Teacher'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_normal_user_read_only(self):
        """Usuario normal solo lectura."""
        self.client.force_authenticate(user=self.normal_user)
        # GET permitido
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # POST denegado
        response = self.client.post('/api/teachers/', {'first_name': 'New', 'last_name': 'Teacher'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

<<<<<<< HEAD
    def test_unauthenticated_read_only_access(self):
        """Sin autenticar: solo lectura permitida en la API."""
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_cannot_write(self):
        """Sin autenticar: no puede crear ni modificar registros."""
        response = self.client.post('/api/teachers/', {'first_name': 'New', 'last_name': 'Teacher'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_sees_inactive_records_but_anonymous_does_not(self):
        """Superusuario ve registros inactivos; usuario anónimo solo activos."""
        inactive_teacher = Teacher.objects.create(first_name='Inactivo', last_name='Docente')
        inactive_teacher.soft_delete()

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item['id'] == inactive_teacher.pk for item in response.data['results']))

        self.client.force_authenticate(user=None)
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(any(item['id'] == inactive_teacher.pk for item in response.data['results']))

    def test_admin_queryset_keeps_inactive_records_for_superuser(self):
        """El admin debe conservar registros desactivados para superusuario."""
        inactive_course = Course.objects.create(name='Curso inactivo', teacher=self.teacher)
        inactive_course.soft_delete()

        request = self.client.request().wsgi_request
        request.user = self.superuser
        admin_queryset = admin.site._registry[Course].get_queryset(request)
        self.assertIn(inactive_course, admin_queryset)

=======
    def test_unauthenticated_denied(self):
        """Sin autenticar: acceso denegado."""
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

>>>>>>> 3fdb7aba9b1c11e353b7619528ed4d660791b4a0

# =============================================================================
# TESTS DE BORRADO LÓGICO INTEGRADO
# =============================================================================

class SoftDeleteIntegrationTest(TestCase):
    """Pruebas integradas de borrado lógico en toda la app."""

    def setUp(self):
        self.teacher = Teacher.objects.create(first_name='Soft', last_name='Delete')
        self.course = Course.objects.create(name='Curso SD', teacher=self.teacher)
        self.student = Student.objects.create(first_name='Est', last_name='SD')
        self.enrollment = StudentCourse.objects.create(
            student=self.student,
            course=self.course
        )

    def test_cascade_soft_delete_teacher(self):
        """Desactivar teacher no elimina cursos (PROTECT)."""
        # PROTECT impide borrar teacher si tiene cursos
        with self.assertRaises(Exception):
            self.teacher.delete()  # Hard delete falla por PROTECT

    def test_soft_delete_teacher_hides_courses(self):
        """Desactivar teacher oculta cursos en API (según filtro)."""
        self.teacher.soft_delete()
        # Teacher no aparece en listado normal
        self.assertNotIn(self.teacher, Teacher.objects.all())
        # Pero curso sí aparece (course.activo sigue True)
        self.assertIn(self.course, Course.objects.all())

    def test_soft_delete_student_hides_enrollments(self):
        """Desactivar estudiante oculta sus inscripciones."""
        self.student.soft_delete()
        self.assertNotIn(self.student, Student.objects.all())
        # Inscripción no aparece en listado normal (filtra student__activo=True)
        self.assertNotIn(self.enrollment, StudentCourse.objects.all())


# =============================================================================
# HELPER PARA EJECUTAR TESTS
# =============================================================================

if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner

    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['academic.tests'])
    exit(failures)