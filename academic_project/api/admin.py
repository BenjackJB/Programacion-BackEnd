from django.contrib import admin
from .models import programmer, Project, Skill

# Register your models here.
admin.site.register(programmer)
admin.site.register(Project)
admin.site.register(Skill)