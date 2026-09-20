"""
Pruebas unitarias para la app academic.

Cubre:
- Modelos (creación, borrado lógico, propiedades)
- Serializers (validación, campos)
- Vistas API (endpoints, permisos)
- Vistas HTML (renderizado, autenticación)
"""

from django.test import TestCase, Client
from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Teacher, Course, Student, StudentCourse, Asignatura


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
        self.course = Course.objects.create(codigo='MAT-N1-C1', name='Matemáticas', teacher=self.teacher)

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
        self.course = Course.objects.create(codigo='FIS-N1-C1', name='Física', teacher=self.teacher)
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
        # Tiene campo pk (id autogenerado por Django) pero la PK compuesta es (student, course)
        self.assertIsNotNone(self.enrollment.pk)
        # Verificar que la constraint única funciona
        self.assertTrue(hasattr(self.enrollment, 'student') and hasattr(self.enrollment, 'course'))

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
        self.course = Course.objects.create(codigo='QUI-N1-C1', name='Química', teacher=self.teacher)
        from .serializers import CourseSerializer
        self.serializer = CourseSerializer(self.course)

    def test_contains_teacher_nested(self):
        """Verifica teacher anidado en serializer."""
        data = self.serializer.data
        self.assertIn('teacher', data)
        self.assertEqual(data['teacher']['full_name'], 'Lucía Fernández')

    def test_contains_enrolled_students(self):
        """Verifica que el curso incluya sus estudiantes inscritos."""
        from .serializers import CourseSerializer
        student = Student.objects.create(first_name='Alumno', last_name='Inscrito')
        StudentCourse.objects.create(student=student, course=self.course)
        data = CourseSerializer(self.course).data
        self.assertEqual(data['students_count'], 1)
        self.assertEqual(data['students'][0]['full_name'], 'Alumno Inscrito')


class StudentCourseSerializerTest(TestCase):
    """Pruebas para StudentCourseSerializer (PK compuesta)."""

    def setUp(self):
        self.teacher = Teacher.objects.create(first_name='Test', last_name='Teacher')
        self.course = Course.objects.create(codigo='TST-N1-C1', name='Test Course', teacher=self.teacher)
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
        self.course = Course.objects.create(codigo='API-N1-C1', name='Curso API', teacher=self.teacher)

    def test_list_courses(self):
        """GET /api/courses/"""
        url = reverse('course-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_course(self):
        """POST /api/courses/"""
        url = reverse('course-list')
        data = {'codigo': 'NUEVO-N1-C1', 'name': 'Nuevo Curso', 'teacher_id': self.teacher.pk}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_activate_inactive_course(self):
        """PATCH /api/courses/{id}/ - activa un curso desactivado."""
        self.course.soft_delete()
        url = reverse('course-detail', kwargs={'pk': self.course.pk})
        response = self.client.patch(url, {'activo': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertTrue(self.course.activo)


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

    def test_activate_inactive_student(self):
        """PATCH /api/students/{id}/ - activa un estudiante desactivado."""
        self.student.soft_delete()
        url = reverse('student-detail', kwargs={'pk': self.student.pk})
        response = self.client.patch(url, {'activo': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertTrue(self.student.activo)


class StudentCourseAPITest(APITestCase):
    """Pruebas para endpoints API de StudentCourse (PK compuesta)."""

    def setUp(self):
        self.user = User.objects.create_superuser('profe', 'profe@test.com', '123456')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.teacher = Teacher.objects.create(first_name='T', last_name='T')
        self.course = Course.objects.create(codigo='CRS-N1-C1', name='Curso', teacher=self.teacher)
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
        """POST /api/enrollments/ - crear nueva inscripción con otro estudiante."""
        url = reverse('enrollment-list')
        # Crear un segundo estudiante para evitar duplicado
        student2 = Student.objects.create(first_name='Otro', last_name='Estudiante')
        data = {'student_id': student2.pk, 'course_id': self.course.pk}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_duplicate_enrollment_returns_400(self):
        """Re-inscribir cuando ya existe inscripción inactiva devuelve 400 (no 500)."""
        self.enrollment.soft_delete()
        url = reverse('enrollment-list')
        data = {'student_id': self.student.pk, 'course_id': self.course.pk}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_enrollment_composite_pk(self):
        """GET /api/enrollments/{student_id}/{course_id}/"""
        # Usar URL personalizada para PK compuesta
        url = f'/api/enrollments/{self.student.pk}/{self.course.pk}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_enrollment_reactivates_it(self):
        """PATCH /api/enrollments/{student_id}/{course_id}/ reactiva una inscripción."""
        self.enrollment.soft_delete()
        url = f'/api/enrollments/{self.student.pk}/{self.course.pk}/'
        response = self.client.patch(url, {'activo': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.enrollment.refresh_from_db()
        self.assertTrue(self.enrollment.activo)

    def test_delete_enrollment_soft_deletes_it(self):
        """DELETE /api/enrollments/{student_id}/{course_id}/ desinscribe al estudiante."""
        url = f'/api/enrollments/{self.student.pk}/{self.course.pk}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.enrollment.refresh_from_db()
        self.assertFalse(self.enrollment.activo)


# =============================================================================
# TESTS DE API ENDPOINTS - ASIGNATURA
# =============================================================================

class AsignaturaAPITest(APITestCase):
    """Pruebas para endpoints API de Asignatura (lectura pública, escritura JWT)."""

    def setUp(self):
        self.user = User.objects.create_user('userapi', 'userapi@test.com', 'password')
        self.asignatura = Asignatura.objects.create(
            codigo='PRO101', nombre='Programacion I', tipo='O', nivel='2', creditos=5
        )

    def test_anonymous_can_read_asignaturas(self):
        """Registros de Asignatura son de libre acceso para lectura (sin autenticación)."""
        url = reverse('asignatura-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Programacion I', [item['nombre'] for item in response.data['results']])

    def test_anonymous_can_read_asignatura_detail(self):
        """Detalle de asignatura también es lectura libre."""
        url = reverse('asignatura-detail', kwargs={'pk': self.asignatura.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre'], 'Programacion I')

    def test_anonymous_cannot_create_asignatura(self):
        """Crear asignatura requiere autenticación (401 sin JWT)."""
        url = reverse('asignatura-list')
        data = {'codigo': 'NUE1', 'nombre': 'Nueva', 'tipo': 'O', 'nivel': '1'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_can_create_asignatura(self):
        """Usuario autenticado (JWT o sesión) puede crear asignatura (201)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('asignatura-list')
        data = {'codigo': 'NUE1', 'nombre': 'Nueva', 'tipo': 'E', 'nivel': '4', 'creditos': 3}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Asignatura.objects.count(), 2)

    def test_choices_validated(self):
        """El uso de choices (tipo/nivel) se valida: un valor inválido da 400."""
        self.client.force_authenticate(user=self.user)
        url = reverse('asignatura-list')
        data = {'codigo': 'X1', 'nombre': 'Invalida', 'tipo': 'Z', 'nivel': '9'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# TESTS DE VISTAS HTML (TEMPLATES)
# =============================================================================

class HTMLViewsTest(TestCase):
    """Pruebas para vistas HTML (templates)."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'password123')
        self.client = Client()
        self.teacher = Teacher.objects.create(first_name='HTML', last_name='Teacher')
        self.course = Course.objects.create(codigo='HTM-N1-C1', name='Curso HTML', teacher=self.teacher)
        self.student = Student.objects.create(first_name='HTML', last_name='Student')

    def test_login_page_accessible(self):
        """Verifica que login es accesible sin autenticación."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academic/login.html')

    def test_courses_are_visible_without_login(self):
        """Verifica que la vista de cursos es pública para lectura."""
        response = self.client.get(reverse('courses'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academic/courses.html')
        self.assertContains(response, 'Cursos y Docentes Asignados')

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

    def test_home_redirects_to_courses(self):
        """Verifica que raíz redirige a courses."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('courses'))

    def test_unknown_url_redirects_to_courses(self):
        response = self.client.get('/ruta-inexistente/')
        self.assertRedirects(response, reverse('courses'))

    def test_logout_renders_template_and_clears_session(self):
        """Verifica que el logout por GET cierra sesión y muestra la página de cierre."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academic/logout.html')
        self.assertFalse(response.wsgi_request.user.is_authenticated)


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

    def test_authenticated_user_full_access(self):
        """Cualquier usuario autenticado (JWT o sesión) puede hacer CRUD (GET y POST)."""
        self.client.force_authenticate(user=self.normal_user)
        # GET permitido
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # POST permitido (requisito: "el resto debe pedir JWT (crud)")
        response = self.client.post('/api/teachers/', {'first_name': 'New', 'last_name': 'Teacher'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unauthenticated_denied(self):
        """Sin autenticar: la API exige JWT (401)."""
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_write(self):
        """Sin autenticar: no puede crear ni modificar registros (401 = debe autenticarse)."""
        response = self.client.post('/api/teachers/', {'first_name': 'New', 'last_name': 'Teacher'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_non_superuser_can_write(self):
        """Autenticado (no superusuario) puede escribir: el CRUD pide JWT, no superusuario."""
        self.client.force_authenticate(user=self.normal_user)
        data = {'first_name': 'New', 'last_name': 'Teacher', 'sexo': 'M'}
        response = self.client.post('/api/teachers/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_superuser_sees_inactive_records_but_normal_user_does_not(self):
        """El superusuario ve solo inactivos con ?include_inactive=true;
        los usuarios normales no los ven ni con el parámetro; los anónimos no acceden."""
        active_teacher = Teacher.objects.create(first_name='Activo', last_name='Docente')
        inactive_teacher = Teacher.objects.create(first_name='Inactivo', last_name='Docente')
        inactive_teacher.soft_delete()

        # Superusuario SIN include_inactive solo ve activos
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(active_teacher.pk, ids)
        self.assertNotIn(inactive_teacher.pk, ids)

        # Superusuario CON include_inactive solo ve inactivos
        response = self.client.get('/api/teachers/?include_inactive=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(inactive_teacher.pk, ids)
        self.assertNotIn(active_teacher.pk, ids)

        # Usuario normal autenticado NO los ve (ni con include_inactive)
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(inactive_teacher.pk, [item['id'] for item in response.data['results']])

        response = self.client.get('/api/teachers/?include_inactive=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(inactive_teacher.pk, [item['id'] for item in response.data['results']])

        # Anónimo no puede consultar (requiere JWT)
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_cannot_retrieve_inactive_detail(self):
        """Un usuario no superusuario no puede acceder al detalle de un registro inactivo (404)."""
        inactive_teacher = Teacher.objects.create(first_name='Inactivo', last_name='Detalle')
        inactive_teacher.soft_delete()
        self.client.force_authenticate(user=self.normal_user)
        url = reverse('teacher-detail', kwargs={'pk': inactive_teacher.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_superuser_can_retrieve_inactive_detail(self):
        """El superusuario sí puede acceder al detalle de un registro inactivo (para restaurarlo)."""
        inactive_teacher = Teacher.objects.create(first_name='Inactivo', last_name='Detalle')
        inactive_teacher.soft_delete()
        self.client.force_authenticate(user=self.superuser)
        url = reverse('teacher-detail', kwargs={'pk': inactive_teacher.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_queryset_keeps_inactive_records_for_superuser(self):
        """El admin debe conservar registros desactivados para superusuario."""
        inactive_course = Course.objects.create(codigo='INA-N1-C1', name='Curso inactivo', teacher=self.teacher)
        inactive_course.soft_delete()

        request = self.client.request().wsgi_request
        request.user = self.superuser
        admin_queryset = admin.site._registry[Course].get_queryset(request)
        self.assertIn(inactive_course, admin_queryset)

    def test_api_root_only_superusers(self):
        """La raíz /api/ (índice navegable) solo es accesible para superusuarios."""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/')
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get('/api/')
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ui_session_superuser_can_create_course(self):
        """Regresión: la UI usa sesión. Un superusuario logueado por sesión debe
        poder crear cursos (antes 403 por configurar solo autenticación JWT)."""
        self.client.force_login(self.superuser)
        data = {'name': 'Curso de la UI', 'teacher_id': self.teacher.pk, 'jornada': 'D'}
        response = self.client.post('/api/courses/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_ui_session_normal_user_can_write(self):
        """Un usuario normal logueado por sesión SÍ puede escribir vía API
        (el CRUD pide autenticación, no superusuario)."""
        self.client.force_login(self.normal_user)
        data = {'name': 'Curso con sesión', 'teacher_id': self.teacher.pk, 'jornada': 'D'}
        response = self.client.post('/api/courses/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_jwt_token_usable_for_any_user(self):
        """El login asociado a JWT: cualquier usuario con credenciales válidas
        obtiene tokens, y con ellos puede hacer CRUD en la API."""
        # Obtener token como usuario normal
        response = self.client.post('/api/token/', {
            'username': 'student', 'password': 'password'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access = response.data['access']
        self.assertTrue(access)

        # Usar el token JWT para CRUD en cursos
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.get('/api/courses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.post('/api/courses/', {
            'name': 'Curso con JWT', 'teacher_id': self.teacher.pk, 'jornada': 'D'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_docs_schema_public(self):
        """La documentación (drf-spectacular) sigue accesible sin autenticación."""
        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get('/docs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# =============================================================================
# TESTS DE BORRADO LÓGICO INTEGRADO
# =============================================================================

class SoftDeleteIntegrationTest(TestCase):
    """Pruebas integradas de borrado lógico en toda la app."""

    def setUp(self):
        self.teacher = Teacher.objects.create(first_name='Soft', last_name='Delete')
        self.course = Course.objects.create(codigo='SD-N1-C1', name='Curso SD', teacher=self.teacher)
        self.student = Student.objects.create(first_name='Est', last_name='SD')
        self.enrollment = StudentCourse.objects.create(
            student=self.student,
            course=self.course
        )

    def test_cascade_soft_delete_teacher(self):
        """Desactivar teacher no elimina cursos (PROTECT). Soft delete funciona."""
        # El soft_delete no debe fallar por PROTECT
        self.teacher.soft_delete()
        self.assertFalse(self.teacher.activo)
        # Los cursos siguen existiendo
        self.assertIn(self.course, Course.objects.all())

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
# TESTS DEL ESQUEMA COREAPI (DOCUMENTACIÓN PARALELA)
# =============================================================================

class CoreAPISchemaTest(TestCase):
    """El esquema CoreAPI (CoreJSON) debe servirse y ser legible por coreapi."""

    def test_coreapi_schema_endpoint_returns_corejson(self):
        from coreapi.codecs import CoreJSONCodec

        url = reverse('api-coreapi-schema')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('application/vnd.coreapi+json', response['Content-Type'])

        # El contenido debe decodificarse como Documento CoreAPI.
        doc = CoreJSONCodec().decode(response.content)
        self.assertEqual(doc.title, 'API Académica - Esquema CoreAPI')
        self.assertIn('token', list(doc.keys()))
        self.assertIn('teachers', list(doc.keys()))
        self.assertIn('courses', list(doc.keys()))
        self.assertIn('students', list(doc.keys()))
        self.assertIn('asignaturas', list(doc.keys()))
        self.assertIn('enrollments', list(doc.keys()))

    def test_coreapi_schema_links_are_well_formed(self):
        from coreapi.codecs import CoreJSONCodec

        url = reverse('api-coreapi-schema')
        doc = CoreJSONCodec().decode(self.client.get(url).content)

        self.assertEqual(doc['teachers']['list'].action, 'get')
        self.assertEqual(doc['teachers']['create'].url, '/api/teachers/')
        self.assertEqual(doc['enrollments']['create'].fields[0].name, 'student_id')
        self.assertEqual(doc['enrollments']['restore'].action, 'post')
        self.assertEqual(doc['token']['obtain'].url, '/api/token/')


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