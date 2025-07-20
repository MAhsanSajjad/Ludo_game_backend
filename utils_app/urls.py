from django.urls import path
from employee_management_app.views import *
from .views import *


urlpatterns = [
    path('skills-list', SkillAPIView.as_view(), name='create-employee'),
]
