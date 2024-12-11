from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Project, Task, User 

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'start_date', 'end_date', 'team']

class TaskForm(forms.ModelForm):  
    class Meta:
        model = Task
        fields = ['title', 'description', 'start_date', 'due_date', 'assigned_to']


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User  
        fields = ('username', 'email', 'role', 'password1', 'password2')  
