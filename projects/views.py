from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .models import Team, Project, Task
from .forms import ProjectForm, TaskForm, CustomUserCreationForm, CustomLoginForm


# Homepage View
def homepage(request):
    projects = Project.objects.all()  
    return render(request, 'projects/homepage.html', {'projects': projects})


# Project Create View
@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project created successfully!')
            return redirect('homepage')  
        else:
            messages.error(request, 'There was an error with your submission.')
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form})


# View Projects of a Team
def team_projects(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    projects = Project.objects.filter(team=team)
    return render(request, 'projects/team_projects.html', {'team': team, 'projects': projects})


# Project Detail View
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    tasks = Task.objects.filter(project=project)
    return render(request, 'projects/project_detail.html', {'project': project, 'tasks': tasks})


# Task Detail View
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    return render(request, 'projects/task_detail.html', {'task': task})


# Task Create View
@login_required
def task_create(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project  
            task.save()
            messages.success(request, 'Task created successfully!')
            return redirect('project_detail', project_id=project.id)  
        else:
            messages.error(request, 'There was an error with your task submission.')
    else:
        form = TaskForm()

    return render(request, 'projects/task_form.html', {'form': form, 'project': project})


# Task Delete View
@login_required
def task_delete(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    project_id = task.project.id
    task.delete()  
    messages.success(request, 'Task deleted successfully!')
    return redirect('project_detail', project_id=project_id)  


# User Registration View
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)  
        if form.is_valid():
            user = form.save()  
            login(request, user)  
            messages.success(request, 'Registration successful! You are now logged in.')
            return redirect('homepage')  
        else:
            messages.error(request, 'There was an error with your registration.')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


# User Login View
def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful!')
                return redirect('homepage')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid login details')
    else:
        form = CustomLoginForm()

    return render(request, 'registration/login.html', {'form': form})
