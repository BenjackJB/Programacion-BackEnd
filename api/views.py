from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .serializer import ProgrammerSerializer
from .models import programmer, Project, Skill
from .forms import ProgrammerForm, ProjectForm, SkillForm

# Create your views here.
class ProgrammerViewSet(viewsets.ModelViewSet):
 # acá creamos una consulta o QUERY a nuestra tabla, trayendo todos los campos como un objeto.
 queryset = programmer.objects.all()
 # Agregamos la clase ProgrammerSerializer que ya tiene el modelo serializado para mostrar
 serializer_class = ProgrammerSerializer
 permission_classes = [IsAuthenticated]

from .serializer import ProjectSerializer, SkillSerializer


class ProjectViewSet(viewsets.ModelViewSet):
	queryset = Project.objects.all()
	serializer_class = ProjectSerializer
	permission_classes = [IsAuthenticated]


class SkillViewSet(viewsets.ModelViewSet):
	queryset = Skill.objects.all()
	serializer_class = SkillSerializer
	permission_classes = [IsAuthenticated]


# --- HTML template views ---
@login_required(login_url='/accounts/login/')
def admin_home(request):
    return render(request, 'admin_home.html')


@login_required(login_url='/accounts/login/')
def programmer_list(request):
	objs = programmer.objects.all()
	return render(request, 'api/programmers_list.html', {'programmers': objs})


@login_required(login_url='/accounts/login/')
def programmers_table(request):
    objs = programmer.objects.prefetch_related('skills', 'projects').all()
    return render(request, 'programmers_table.html', {'programmers': objs})


@login_required(login_url='/accounts/login/')
def programmer_detail(request, pk):
	obj = get_object_or_404(programmer, pk=pk)
	return render(request, 'api/programmer_detail.html', {'programmer': obj})


@login_required(login_url='/accounts/login/')
def project_list(request):
	objs = Project.objects.all()
	return render(request, 'api/projects_list.html', {'projects': objs})


@login_required(login_url='/accounts/login/')
def projects_table(request):
    objs = Project.objects.select_related('owner').all()
    return render(request, 'projects_table.html', {'projects': objs})


@login_required(login_url='/accounts/login/')
def project_detail(request, pk):
	obj = get_object_or_404(Project, pk=pk)
	return render(request, 'api/project_detail.html', {'project': obj})


@login_required(login_url='/accounts/login/')
def skill_list(request):
	objs = Skill.objects.all()
	return render(request, 'api/skills_list.html', {'skills': objs})


@login_required(login_url='/accounts/login/')
def skills_table(request):
    objs = Skill.objects.prefetch_related('programmers').all()
    return render(request, 'skills_table.html', {'skills': objs})


@login_required(login_url='/accounts/login/')
def skill_detail(request, pk):
	obj = get_object_or_404(Skill, pk=pk)
	return render(request, 'api/skill_detail.html', {'skill': obj})


# ===== PROGRAMMER CRUD VIEWS =====
@login_required(login_url='/accounts/login/')
def programmer_create(request):
	if request.method == 'POST':
		form = ProgrammerForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Programador creado exitosamente.')
			return redirect('programmers_table')
	else:
		form = ProgrammerForm()
	return render(request, 'api/programmer_form.html', {'form': form, 'title': 'Crear Programador'})


@login_required(login_url='/accounts/login/')
def programmer_edit(request, pk):
	obj = get_object_or_404(programmer, pk=pk)
	if request.method == 'POST':
		form = ProgrammerForm(request.POST, instance=obj)
		if form.is_valid():
			form.save()
			messages.success(request, 'Programador actualizado exitosamente.')
			return redirect('programmers_table')
	else:
		form = ProgrammerForm(instance=obj)
	return render(request, 'api/programmer_form.html', {'form': form, 'title': 'Editar Programador', 'programmer': obj})


@login_required(login_url='/accounts/login/')
def programmer_delete(request, pk):
	obj = get_object_or_404(programmer, pk=pk)
	if request.method == 'POST':
		obj.delete()
		messages.success(request, 'Programador eliminado exitosamente.')
		return redirect('programmers_table')
	return render(request, 'api/programmer_confirm_delete.html', {'programmer': obj})


# ===== PROJECT CRUD VIEWS =====
@login_required(login_url='/accounts/login/')
def project_create(request):
	if request.method == 'POST':
		form = ProjectForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Proyecto creado exitosamente.')
			return redirect('projects_table')
	else:
		form = ProjectForm()
	return render(request, 'api/project_form.html', {'form': form, 'title': 'Crear Proyecto'})


@login_required(login_url='/accounts/login/')
def project_edit(request, pk):
	obj = get_object_or_404(Project, pk=pk)
	if request.method == 'POST':
		form = ProjectForm(request.POST, instance=obj)
		if form.is_valid():
			form.save()
			messages.success(request, 'Proyecto actualizado exitosamente.')
			return redirect('projects_table')
	else:
		form = ProjectForm(instance=obj)
	return render(request, 'api/project_form.html', {'form': form, 'title': 'Editar Proyecto', 'project': obj})


@login_required(login_url='/accounts/login/')
def project_delete(request, pk):
	obj = get_object_or_404(Project, pk=pk)
	if request.method == 'POST':
		obj.delete()
		messages.success(request, 'Proyecto eliminado exitosamente.')
		return redirect('projects_table')
	return render(request, 'api/project_confirm_delete.html', {'project': obj})


# ===== SKILL CRUD VIEWS =====
@login_required(login_url='/accounts/login/')
def skill_create(request):
	if request.method == 'POST':
		form = SkillForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Habilidad creada exitosamente.')
			return redirect('skills_table')
	else:
		form = SkillForm()
	return render(request, 'api/skill_form.html', {'form': form, 'title': 'Crear Habilidad'})


@login_required(login_url='/accounts/login/')
def skill_edit(request, pk):
	obj = get_object_or_404(Skill, pk=pk)
	if request.method == 'POST':
		form = SkillForm(request.POST, instance=obj)
		if form.is_valid():
			form.save()
			messages.success(request, 'Habilidad actualizada exitosamente.')
			return redirect('skills_table')
	else:
		form = SkillForm(instance=obj)
	return render(request, 'api/skill_form.html', {'form': form, 'title': 'Editar Habilidad', 'skill': obj})


@login_required(login_url='/accounts/login/')
def skill_delete(request, pk):
	obj = get_object_or_404(Skill, pk=pk)
	if request.method == 'POST':
		obj.delete()
		messages.success(request, 'Habilidad eliminada exitosamente.')
		return redirect('skills_table')
	return render(request, 'api/skill_confirm_delete.html', {'skill': obj})

