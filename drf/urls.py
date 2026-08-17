from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

from api import views

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', views.admin_home, name='admin_home'),
    path('admin/programmer/', views.programmers_table, name='programmers_table'),
    path('admin/project/', views.projects_table, name='projects_table'),
    path('admin/skill/', views.skills_table, name='skills_table'),
    path('admin/programmer/create/', views.programmer_create, name='programmer_create'),
    path('admin/programmer/<int:pk>/edit/', views.programmer_edit, name='programmer_edit'),
    path('admin/programmer/<int:pk>/delete/', views.programmer_delete, name='programmer_delete'),
    path('admin/project/create/', views.project_create, name='project_create'),
    path('admin/project/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('admin/project/<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('admin/skill/create/', views.skill_create, name='skill_create'),
    path('admin/skill/<int:pk>/edit/', views.skill_edit, name='skill_edit'),
    path('admin/skill/<int:pk>/delete/', views.skill_delete, name='skill_delete'),
    path('admin/programmer/<int:pk>/', views.programmer_detail, name='programmer_detail'),
    path('admin/project/<int:pk>/', views.project_detail, name='project_detail'),
    path('admin/skill/<int:pk>/', views.skill_detail, name='skill_detail'),
    path('api/', include('api.api_urls')),
    path('django-admin/', admin.site.urls),
]
