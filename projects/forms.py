from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Project, Task, User  # Import User model to work with custom user form

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'start_date', 'end_date', 'team']

class TaskForm(forms.ModelForm):  # Removed unnecessary comment
    class Meta:
        model = Task
        fields = ['title', 'description', 'start_date', 'due_date', 'assigned_to']

# Custom user creation form
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User  # Using your custom User model
        fields = ('username', 'email', 'role', 'password1', 'password2')  # Fields to include in the form
