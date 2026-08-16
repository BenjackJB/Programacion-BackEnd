from django import forms
from .models import programmer, Project, Skill


class ProgrammerForm(forms.ModelForm):
    class Meta:
        model = programmer
        fields = ['fullname', 'nickname', 'language', 'age', 'is_active']
        widgets = {
            'fullname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'}),
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apodo'}),
            'language': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lenguaje de programación'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Edad'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'start_date', 'end_date', 'owner']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del proyecto'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descripción', 'rows': 4}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'owner': forms.Select(attrs={'class': 'form-control'}),
        }


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'level', 'programmers']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la habilidad'}),
            'level': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nivel (ej: Básico, Intermedio, Avanzado)'}),
            'programmers': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }
