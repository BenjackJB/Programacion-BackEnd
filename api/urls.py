from django.urls import path

from api import views

urlpatterns = [
    path('programmer/', views.programmers_table, name='programmers_table'),
    path('project/', views.projects_table, name='projects_table'),
    path('skill/', views.skills_table, name='skills_table'),
    path('programmer/create/', views.programmer_create, name='programmer_create'),
    path('programmer/<int:pk>/edit/', views.programmer_edit, name='programmer_edit'),
    path('programmer/<int:pk>/delete/', views.programmer_delete, name='programmer_delete'),
    path('project/create/', views.project_create, name='project_create'),
    path('project/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('project/<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('skill/create/', views.skill_create, name='skill_create'),
    path('skill/<int:pk>/edit/', views.skill_edit, name='skill_edit'),
    path('skill/<int:pk>/delete/', views.skill_delete, name='skill_delete'),
    path('programmer/<int:pk>/', views.programmer_detail, name='programmer_detail'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    path('skill/<int:pk>/', views.skill_detail, name='skill_detail'),
]
