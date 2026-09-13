from django.urls import include, path
from rest_framework import routers

from api import views

router = routers.DefaultRouter()
router.register(r'programmer', views.ProgrammerViewSet, basename='programmer')
router.register(r'project', views.ProjectViewSet, basename='project')
router.register(r'skill', views.SkillViewSet, basename='skill')

urlpatterns = [
    path('', include(router.urls)),
]
