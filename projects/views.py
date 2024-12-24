from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from .models import Team, Project, Task, Profile, Notification, ProjectReport, TeamMember, User
from .forms import ProjectForm, TaskForm, CustomUserCreationForm, CustomLoginForm, ProfileForm, TeamMemberForm
import json
import logging

logger = logging.getLogger(__name__)

# Helper function to send notifications
def send_notification(user, message):
    Notification.objects.create(user=user, message=message, read=False)

# Homepage View
@login_required
def homepage(request):
    try:
        team_member = TeamMember.objects.get(user=request.user)
        teams = Team.objects.filter(members=team_member)
    except TeamMember.DoesNotExist:
        teams = Team.objects.none()

    team = teams.first() if teams.exists() else None  # Use the first team or None
    projects = Project.objects.all()
    todo_tasks = Task.objects.filter(status='todo')
    inprogress_tasks = Task.objects.filter(status='inprogress')
    done_tasks = Task.objects.filter(status='done')

    unread_notifications = Notification.objects.filter(user=request.user, read=False)
    unread_notifications_count = unread_notifications.count()

    return render(request, 'projects/homepage.html', {
        'projects': projects,
        'todo_tasks': todo_tasks,
        'inprogress_tasks': inprogress_tasks,
        'done_tasks': done_tasks,
        'unread_notifications': unread_notifications,
        'unread_notifications_count': unread_notifications_count,
        'team': team,
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
            send_notification(request.user, "Your password was changed successfully.")
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
                project = form.save()
                send_notification(request.user, f"Project '{project.name}' created successfully.")
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
        # Ensure the user is a member of the team
        if not TeamMember.objects.filter(user=request.user, team=team).exists():
            messages.error(request, "You are not a member of this team.")
            return redirect('homepage')
        projects = Project.objects.filter(team=team)
    else:
        # Default behavior: show all projects if no specific team is selected
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
            updated_task = form.save()
            if updated_task.status == 'done':
                send_notification(updated_task.assigned_to, f"Task '{updated_task.title}' is marked as done.")
            messages.success(request, 'Task updated successfully!')
            return redirect('task_detail', project_id=project_id, task_id=task_id)
        else:
            messages.error(request, 'There was an error with your task update.')
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
        send_notification(request.user, f"Task '{task.title}' was deleted.")
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
            send_notification(request.user, "Your profile has been updated.")
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
        send_notification(request.user, "Your account was deleted.")
        return redirect('register')
    return render(request, 'profile/delete_account.html')

# Profile View
@login_required
def view_profile(request):
    profile = get_object_or_404(Profile, user=request.user)
    return render(request, 'profile/view_profile.html', {'profile': profile})

@login_required
def manage_team_members(request, team_id):
    team = get_object_or_404(Team, id=team_id)

    # Check if the user is the owner or has permission to manage the team members
    if request.user != team.owner:
        messages.error(request, "You don't have permission to manage this team's members.")
        return redirect('team_detail', team_id=team.id)

    if request.method == 'POST':
        form = TeamMemberForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            
            # Check if the user is already a member of the team
            if TeamMember.objects.filter(team=team, user=user).exists():
                messages.error(request, f"{user.username} is already a member of this team.")
            else:
                # Add the new member
                team_member = form.save(commit=False)
                team_member.team = team
                team_member.save()
                messages.success(request, 'Team member added successfully!')
                send_notification(request.user, f"New team member added to team '{team.name}'")
                return redirect('manage_team_members', team_id=team.id)
        else:
            messages.error(request, 'There was an error with your submission.')
    else:
        form = TeamMemberForm(initial={'team': team})

    members = TeamMember.objects.filter(team=team)  # List the current team members
    return render(request, 'projects/manage_team_members.html', {
        'form': form,
        'team': team,
        'members': members
    })

# Remove Team Member View
@login_required
def remove_team_member(request, team_id, member_id):
    team = get_object_or_404(Team, id=team_id)
    member = get_object_or_404(TeamMember, id=member_id, team=team)

    # Ensure the logged-in user has permission to remove team members (e.g., only team owner can remove members)
    if request.user != team.owner:
        messages.error(request, "You don't have permission to remove this member.")
        return redirect('team_members', team_id=team.id)

    # Remove the team member
    member.delete()
    messages.success(request, f"Member {member.user.username} has been removed from the team.")
    send_notification(request.user, f"Member {member.user.username} was removed from team '{team.name}'")
    return redirect('team_members', team_id=team.id)


# Project Report Generation
@login_required
def generate_report(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    tasks = Task.objects.filter(project=project)
    report_content = generate_report_content(project, tasks)
    ProjectReport.objects.create(project=project, content=report_content)
    messages.success(request, 'Report generated successfully!')
    send_notification(request.user, f"Report for project '{project.name}' has been generated.")
    return redirect('project_detail', project_id=project.id)

def generate_report_content(project, tasks):
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
    Notification.objects.create(user=user, message=message, read=False)

# Clear all notifications - expects a POST request
@csrf_protect  # Ensure CSRF protection in production
def clear_all_notifications(request):
    if request.method == 'POST':
        try:
            # Fetch notifications for the logged-in user and delete them
            notifications = Notification.objects.filter(user=request.user)
            notifications.delete()
            
            # Add a success message to be displayed to the user
            messages.success(request, 'All notifications cleared.')
            
            # Redirect the user back to the homepage (or another relevant page)
            return redirect('homepage')  # Adjust this to where you'd like to redirect
        except Exception as e:
            # Add an error message if something goes wrong
            messages.error(request, f"Error clearing notifications: {str(e)}")
            
            # Redirect back to the homepage or relevant page
            return redirect('homepage')  # Adjust as needed
    else:
        # Return an error response if the request method is not POST
        return JsonResponse({'error': 'Invalid request method'}, status=400)

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
            send_notification(task.assigned_to, f"Task '{task.title}' status updated to {new_status}")
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
        'members': members,
        'no_members': not members.exists()  # Flag to show message if no members exist
    })


@login_required
def progress(request):
    projects = Project.objects.all()
    tasks = Task.objects.all()
    return render(request, 'projects/progress.html', {
        'projects': projects,
        'tasks': tasks
    })