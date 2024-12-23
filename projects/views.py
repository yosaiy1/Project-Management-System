from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Team, Project, Task, Profile, Notification, ProjectReport, TeamMember, User
from .forms import ProjectForm, TaskForm, CustomUserCreationForm, CustomLoginForm, ProfileForm, TeamMemberForm
import json
import logging

logger = logging.getLogger(__name__)

# Homepage View
@login_required
def homepage(request):
    # Get the TeamMember instance for the logged-in user
    try:
        team_member = TeamMember.objects.get(user=request.user)
        teams = Team.objects.filter(members=team_member)
    except TeamMember.DoesNotExist:
        # Handle cases where the user is not part of any team
        teams = Team.objects.none()

    team = teams.first() if teams.exists() else None  # Use the first team or None
    projects = Project.objects.all()
    todo_tasks = Task.objects.filter(status='todo')
    inprogress_tasks = Task.objects.filter(status='inprogress')
    done_tasks = Task.objects.filter(status='done')
    unread_notifications_count = request.user.notifications.filter(read=False).count()

    return render(request, 'projects/homepage.html', {
        'projects': projects,
        'todo_tasks': todo_tasks,
        'inprogress_tasks': inprogress_tasks,
        'done_tasks': done_tasks,
        'unread_notifications_count': unread_notifications_count,
        'team': team,  # Pass the first team (or None) for the sidebar
    })


@login_required
def settings_view(request):
    return render(request, 'settings/settings.html')

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('settings')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'settings/change_password.html', {
        'form': form
    })

# Project Create View
@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project_name = form.cleaned_data.get('name')
            if Project.objects.filter(name=project_name).exists():
                messages.error(request, 'A project with this name already exists.')
            else:
                form.save()
                messages.success(request, 'Project created successfully!')
                return redirect('homepage')
        else:
            messages.error(request, 'There was an error with your submission.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form})

# View Projects of a Team
@login_required
def team_projects(request, team_id=None):
    if team_id:
        team = get_object_or_404(Team, id=team_id)
        projects = Project.objects.filter(team=team)
    else:
        team = None
        projects = Project.objects.all()
    
    return render(request, 'projects/team_projects.html', {
        'team': team,
        'projects': projects
    })

# Project Detail View
@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    tasks = Task.objects.filter(project=project)
    return render(request, 'projects/project_detail.html', {'project': project, 'tasks': tasks})

# Task Detail View
@login_required
def task_detail(request, project_id, task_id):
    project = get_object_or_404(Project, id=project_id)
    task = get_object_or_404(Task, id=task_id, project=project)
    return render(request, 'projects/task_detail.html', {'task': task, 'project': project})

# Task Create View
@login_required
def task_create(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task_title = form.cleaned_data.get('title')
            if Task.objects.filter(project=project, title=task_title).exists():
                messages.error(request, 'A task with this title already exists in this project.')
            else:
                task = form.save(commit=False)
                task.project = project
                task.save()
                send_notification(task.assigned_to, f"You have been assigned a new task: {task.title}")
                messages.success(request, 'Task created successfully!')
                return redirect('project_detail', project_id=project.id)
        else:
            messages.error(request, 'There was an error with your task submission.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = TaskForm()

    return render(request, 'projects/task_form.html', {'form': form, 'project': project})

# Task Update View
@login_required
def task_update(request, project_id, task_id):
    task = get_object_or_404(Task, id=task_id, project_id=project_id)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully!')
            return redirect('task_detail', project_id=project_id, task_id=task_id)
        else:
            messages.error(request, 'There was an error with your task update.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = TaskForm(instance=task)

    return render(request, 'projects/task_form.html', {'form': form, 'task': task})

# Task Delete View
@login_required
def task_delete(request, project_id, task_id):
    task = get_object_or_404(Task, id=task_id, project_id=project_id)
    if request.method == "POST":
        task.delete()
        messages.success(request, 'Task deleted successfully!')
        return redirect('project_detail', project_id=project_id)
    return render(request, 'projects/task_delete_confirm.html', {'task': task, 'project_id': project_id})

# User Registration View
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            if User.objects.filter(username=username).exists():
                messages.error(request, 'A user with this username already exists.')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'A user with this email already exists.')
            else:
                user = form.save()
                login(request, user)
                messages.success(request, 'Registration successful! You are now logged in.')
                return redirect('homepage')
        else:
            messages.error(request, 'There was an error with your registration.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})

# User Login View
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username_or_email, password=password)
            if user is None:
                user = authenticate(request, email=username_or_email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful!')
                return redirect('homepage')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid login details')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})

# User Logout View
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return render(request, 'registration/logout_confirmation.html')

# Profile Update View
@login_required
def update_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            updated_profile = form.save(commit=False)
            updated_profile.save()
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('view_profile')
        else:
            messages.error(request, 'There was an error with your profile update.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'profile/update_profile.html', {'form': form})

# Profile Delete View
@login_required
def delete_account(request):
    if request.method == 'POST':
        request.user.delete()
        messages.success(request, 'Account deleted successfully!')
        return redirect('register')
    return render(request, 'profile/delete_account.html')

# Profile View
@login_required
def view_profile(request):
    profile = get_object_or_404(Profile, user=request.user)
    return render(request, 'profile/view_profile.html', {'profile': profile})

# Manage Team Members View
@login_required
def manage_team_members(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    if request.method == 'POST':
        form = TeamMemberForm(request.POST)
        if form.is_valid():
            team_member = form.save(commit=False)
            team_member.team = team
            team_member.save()
            messages.success(request, 'Team member added successfully!')
            return redirect('manage_team_members', team_id=team.id)
    else:
        form = TeamMemberForm(initial={'team': team})
    return render(request, 'projects/manage_team_members.html', {'form': form, 'team': team})

# Generate Report View
@login_required
def generate_report(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    tasks = Task.objects.filter(project=project)
    report_content = generate_report_content(project, tasks)
    ProjectReport.objects.create(project=project, content=report_content)
    messages.success(request, 'Report generated successfully!')
    return redirect('project_detail', project_id=project.id)

def generate_report_content(project, tasks):
    # Generate report content (e.g., in HTML or plain text format)
    content = f"Report for project: {project.name}\n\n"
    for task in tasks:
        content += f"Task: {task.title}, Assigned to: {task.assigned_to.username}, Due date: {task.due_date}\n"
    return content

# Member Progress View
@login_required
def member_progress(request):
    tasks = Task.objects.filter(assigned_to=request.user)
    return render(request, 'projects/member_progress.html', {'tasks': tasks})

# Send Notification Function
def send_notification(user, message):
    Notification.objects.create(user=user, message=message)

# Update Task Status View
@csrf_exempt
def update_task_status(request, task_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')
            task = Task.objects.get(id=task_id)
            task.status = new_status
            task.save()
            logger.info(f"Task {task_id} status updated to {new_status}")
            return JsonResponse({'status': 'success'})
        except Task.DoesNotExist:
            logger.error(f"Task with id {task_id} does not exist.")
            return JsonResponse({'status': 'error', 'message': 'Task not found'}, status=404)
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload.")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload'}, status=400)
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred'}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
def team_list(request):
    teams = Team.objects.all()
    return render(request, 'projects/team_list.html', {'teams': teams})

@login_required
def team_detail(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    return render(request, 'projects/team_detail.html', {'team': team})

@login_required
def team_members(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    members = TeamMember.objects.filter(team=team)
    return render(request, 'projects/team_members.html', {
        'team': team,
        'members': members
    })

@login_required
def progress(request):
    projects = Project.objects.all()
    tasks = Task.objects.all()
    return render(request, 'projects/progress.html', {
        'projects': projects,
        'tasks': tasks
    })