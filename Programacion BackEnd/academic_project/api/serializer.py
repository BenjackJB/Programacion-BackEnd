from rest_framework import serializers
from .models import programmer, Project, Skill


class ProgrammerSerializer(serializers.ModelSerializer):
	class Meta:
		model = programmer
		fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
	class Meta:
		model = Project
		fields = '__all__'


class SkillSerializer(serializers.ModelSerializer):
	class Meta:
		model = Skill
		fields = '__all__'