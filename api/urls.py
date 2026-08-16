from django.urls import path, include
from rest_framework import routers
from api import views
router = routers.DefaultRouter() # este elemento enrutador permite manejar múltiples rutas.
# esta es la base del conjunto de rutas o la raíz de las rutas
# acá se manejan las rutas o ENDsPOINTS que pueda tener tu API
router.register(r'programmers', views.ProgrammerViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'skills', views.SkillViewSet)
# la r permite que no se interprete como un salto de línea o como un escape de carácter
# usamos la r para indicar que no tome los caracteres como \n o \t que es un salto de línea o una tabulación, es un formato tipo RAW de python.
# 'programmers' es un ENDPOINT
urlpatterns = [
 path('programmers/', views.programmers_table, name='programmers_table'),
 path('projects/', views.projects_table, name='projects_table'),
 path('skills/', views.skills_table, name='skills_table'),
 path('html/programmers/', views.programmer_list, name='programmer_list'),
 path('html/programmers/<int:pk>/', views.programmer_detail, name='programmer_detail'),
 path('html/projects/', views.project_list, name='project_list'),
 path('html/projects/<int:pk>/', views.project_detail, name='project_detail'),
 path('html/skills/', views.skill_list, name='skill_list'),
 path('html/skills/<int:pk>/', views.skill_detail, name='skill_detail'),
 # ===== PROGRAMMER CRUD URLS =====
 path('programmer/create/', views.programmer_create, name='programmer_create'),
 path('programmer/<int:pk>/edit/', views.programmer_edit, name='programmer_edit'),
 path('programmer/<int:pk>/delete/', views.programmer_delete, name='programmer_delete'),
 # ===== PROJECT CRUD URLS =====
 path('project/create/', views.project_create, name='project_create'),
 path('project/<int:pk>/edit/', views.project_edit, name='project_edit'),
 path('project/<int:pk>/delete/', views.project_delete, name='project_delete'),
 # ===== SKILL CRUD URLS =====
 path('skill/create/', views.skill_create, name='skill_create'),
 path('skill/<int:pk>/edit/', views.skill_edit, name='skill_edit'),
 path('skill/<int:pk>/delete/', views.skill_delete, name='skill_delete'),
 path('', include(router.urls)),
# la ruta base va a incluir todos los elementos que tenga el router que hemos creado en URLS
# esta es la lista de URLS que maneja ROUTER en sus elementos URLS
]
