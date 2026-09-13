from django.db import models


# Create your models here.
class programmer(models.Model):
	fullname = models.CharField(max_length=100)
	nickname = models.CharField(max_length=100)
	language = models.CharField(max_length=100)
	age = models.PositiveSmallIntegerField()
	is_active = models.BooleanField(default=True)


class Project(models.Model):
	name = models.CharField(max_length=150)
	description = models.TextField(blank=True)
	start_date = models.DateField(null=True, blank=True)
	end_date = models.DateField(null=True, blank=True)
	owner = models.ForeignKey(programmer, on_delete=models.CASCADE, related_name='projects')

	def __str__(self):
		return self.name


class Skill(models.Model):
	name = models.CharField(max_length=100)
	level = models.CharField(max_length=50, blank=True)
	programmers = models.ManyToManyField(programmer, related_name='skills', blank=True)

	def __str__(self):
		return self.name
