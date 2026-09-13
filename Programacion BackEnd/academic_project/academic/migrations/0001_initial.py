# Generated migration for initial models with composite PK on StudentCourse
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Teacher',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha creación')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True, verbose_name='Fecha actualización')),
                ('first_name', models.CharField(max_length=100, verbose_name='Nombre')),
                ('last_name', models.CharField(max_length=100, verbose_name='Apellido')),
            ],
            options={
                'verbose_name': 'Docente',
                'verbose_name_plural': 'Docentes',
                'db_table': 'teacher',
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha creación')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True, verbose_name='Fecha actualización')),
                ('first_name', models.CharField(max_length=100, verbose_name='Nombre')),
                ('last_name', models.CharField(max_length=100, verbose_name='Apellido')),
            ],
            options={
                'verbose_name': 'Estudiante',
                'verbose_name_plural': 'Estudiantes',
                'db_table': 'student',
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha creación')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True, verbose_name='Fecha actualización')),
                ('name', models.CharField(max_length=100, verbose_name='Nombre del curso')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='courses', to='academic.teacher', verbose_name='Docente')),
            ],
            options={
                'verbose_name': 'Curso',
                'verbose_name_plural': 'Cursos',
                'db_table': 'course',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='StudentCourse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha creación')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True, verbose_name='Fecha actualización')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='student_courses', to='academic.student', verbose_name='Estudiante')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='student_courses', to='academic.course', verbose_name='Curso')),
            ],
            options={
                'verbose_name': 'Inscripción',
                'verbose_name_plural': 'Inscripciones',
                'db_table': 'student_course',
                'ordering': ['-fecha_creacion'],
            },
        ),
        migrations.AddConstraint(
            model_name='studentcourse',
            constraint=models.UniqueConstraint(fields=('student', 'course'), name='unique_student_course_pk'),
        ),
    ]