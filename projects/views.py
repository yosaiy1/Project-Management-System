from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from .models import Team, Project, Task, Profile, Notification, ProjectReport, TeamMember, User
from .forms import ProjectForm, TaskForm, CustomUserCreationForm, CustomLoginForm, ProfileForm, TeamMemberForm
from django.utils import timezone
from django.urls import reverse
from django.db import transaction
from datetime import timedelta, date
import json
import logging

logger = logging.getLogger(__name__)

# Helper function to send notifications
def send_notification(user, message):
    Notification.objects.create(
        user=user,
        message=message,
        read=False
    )

# Homepage View
@login_required
def homepage(request):
    try:
        team_member = TeamMember.objects.get(user=request.user)
        teams = Team.objects.filter(members=team_member)
    except TeamMember.DoesNotExist:
        teams = Team.objects.none()

    context = {
        'projects': Project.objects.filter(team__members__user=request.user).distinct(),
        'todo_tasks': Task.objects.filter(assigned_to=request.user, status='todo'),
        'inprogress_tasks': Task.objects.filter(assigned_to=request.user, status='inprogress'),
        'done_tasks': Task.objects.filter(assigned_to=request.user, status='done'),
        'team': teams.first() if teams.exists() else None,
        'notifications': Notification.objects.filter(user=request.user).order_by('-created_at')[:5],
        'unread_notifications_count': Notification.objects.filter(user=request.user, read=False).count(),
        'teams': teams,
    }
    return render(request, 'projects/homepage.html', context)

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
            project = form.save(commit=False)
            team = form.cleaned_data.get('team')
            
            if not (TeamMember.objects.filter(user=request.user, team=team).exists() or request.user == team.owner):
                messages.error(request, "You don't have permission to create projects in this team.")
                return redirect('homepage')
            
            project.save()
            messages.success(request, 'Project created successfully!')
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm()
    return render(request, 'projects/project_form.html', {'form': form})

# View Projects of a Team
@login_required
def team_projects(request, team_id=None):
    if team_id:
        team = get_object_or_404(Team, id=team_id)
        if not (TeamMember.objects.filter(user=request.user, team=team).exists() or request.user == team.owner):
            messages.error(request, "You don't have permission to view this team's projects.")
            return redirect('homepage')
        projects = Project.objects.filter(team=team)
    else:
        projects = Project.objects.filter(team__members__user=request.user).distinct()
    
    return render(request, 'projects/team_projects.html', {'projects': projects})

# Project Detail View
@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not (TeamMember.objects.filter(user=request.user, team=project.team).exists() or request.user == project.team.owner):
        messages.error(request, "You don't have permission to view this project.")
        return redirect('homepage')
    tasks = Task.objects.filter(project=project)
    return render(request, 'projects/project_detail.html', {'project': project, 'tasks': tasks})

# Task List View
@login_required
def task_list(request):
    tasks = Task.objects.filter(
        assigned_to=request.user
    ).select_related('project').order_by('-created_at')
    
    return render(request, 'projects/task_list.html', {
        'tasks': tasks,
        'todo_tasks': tasks.filter(status='todo'),
        'inprogress_tasks': tasks.filter(status='inprogress'),
        'done_tasks': tasks.filter(status='done')
    })

# Task Detail View
@login_required
def task_detail(request, project_id, task_id):
    project = get_object_or_404(Project, id=project_id)
    task = get_object_or_404(Task, id=task_id, project=project)
    if not (TeamMember.objects.filter(user=request.user, team=project.team).exists() or 
            request.user == project.team.owner or 
            request.user == task.assigned_to):
        messages.error(request, "You don't have permission to view this task.")
        return redirect('homepage')
    return render(request, 'projects/task_detail.html', {'task': task, 'project': project})

# Task Create View
@login_required
def task_create(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not TeamMember.objects.filter(user=request.user, team=project.team).exists():
        messages.error(request, "You don't have permission to create tasks in this project.")
        return redirect('homepage')
        
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.save()
            send_notification(task.assigned_to, f"You have been assigned a new task: {task.title}")
            messages.success(request, 'Task created successfully!')
            return redirect('project_detail', project_id=project.id)
    else:
        form = TaskForm(initial={'project': project})

    return render(request, 'projects/task_form.html', {'form': form, 'project': project})

# Task Update View
@login_required
def task_update(request, project_id, task_id):
    task = get_object_or_404(Task, id=task_id, project_id=project_id)
    if not (request.user == task.assigned_to or 
            TeamMember.objects.filter(user=request.user, team=task.project.team).exists()):
        messages.error(request, "You don't have permission to update this task.")
        return redirect('homepage')
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
    if not (request.user == task.assigned_to or request.user == task.project.team.owner):
        messages.error(request, "You don't have permission to delete this task.")
        return redirect('homepage')
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
    if not (TeamMember.objects.filter(user=request.user, team=project.team).exists() or request.user == project.team.owner):
        messages.error(request, "You don't have permission to generate reports for this project.")
        return redirect('homepage')
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
@login_required
def update_task_status(request, task_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
    try:
        with transaction.atomic():
            data = json.loads(request.body)
            new_status = data.get('status')
            task = Task.objects.select_for_update().get(id=task_id)
            
            if not (request.user == task.assigned_to or 
                   TeamMember.objects.filter(user=request.user, team=task.project.team).exists()):
                return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
            
            old_status = task.status
            task.status = new_status
            
            if new_status == 'done' and old_status != 'done':
                task.completed_at = timezone.now()
            
            task.save()
            send_notification(task.assigned_to, f"Task '{task.title}' status updated to {new_status}")
            return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def team_list(request):
    teams = Team.objects.filter(members__user=request.user).distinct()
    return render(request, 'projects/team_list.html', {'teams': teams})

def has_team_permission(user, team):
    return TeamMember.objects.filter(user=user, team=team).exists() or user == team.owner

@login_required 
def team_detail(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    if not has_team_permission(request.user, team):
        messages.error(request, "You don't have permission to view this team.")
        return redirect('homepage')
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
    user_projects = Project.objects.filter(
        team__members__user=request.user
    ).select_related('team').distinct()
    
    user_tasks = Task.objects.filter(
        assigned_to=request.user
    ).select_related('project')
    
    context = {
        'projects': user_projects,
        'tasks': user_tasks,
        'completion_rate': calculate_completion_rate(request.user),
        'recent_activity': Task.objects.filter(
            assigned_to=request.user,
            updated_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('project').order_by('-updated_at')
    }
    return render(request, 'projects/progress.html', context)

@login_required 
def project_list(request):
    projects = Project.objects.filter(
        team__members__user=request.user
    ).select_related('team').distinct().order_by('-date_created')

@login_required
def analytics_view(request):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view analytics.")
        return redirect('homepage')
        
    projects = Project.objects.filter(
        team__members__user=request.user
    ).select_related('team').distinct()
    
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    context = {
        'total_projects': projects.count(),
        'active_tasks': Task.objects.filter(
            assigned_to=request.user,
            status__in=['todo', 'inprogress']
        ).count(),
        'team_members': TeamMember.objects.filter(
            team__projects__in=projects
        ).distinct().count(),
        'completion_rate': calculate_completion_rate(request.user),
        'timeline_labels': get_timeline_labels(),
        'completed_tasks_data': get_completed_tasks_data(request.user),
        'task_distribution': get_task_distribution(request.user),
        'team_labels': get_team_labels(request.user),
        'team_performance': get_team_performance(request.user),
        'trend_labels': get_trend_labels(),
        'completion_trend': get_completion_trend(request.user),
        'recent_activities': Task.objects.filter(
            assigned_to=request.user,
            updated_at__date__gte=thirty_days_ago
        ).order_by('-updated_at')[:10]
    }
    return render(request, 'projects/analytics.html', context)

def calculate_completion_rate(user):
    total_tasks = Task.objects.filter(assigned_to=user).count()
    completed_tasks = Task.objects.filter(assigned_to=user, status='done').count()
    return round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0)

def get_timeline_labels():
    # Returns last 7 days
    return [date.strftime('%b %d') for date in 
            [(timezone.now() - timedelta(days=x)) for x in range(6, -1, -1)]]

def get_completed_tasks_data(user):
    # Returns completed tasks count for last 7 days
    return [Task.objects.filter(
        assigned_to=user,
        status='done',
        completed_at__date=timezone.now().date() - timedelta(days=x)
    ).count() for x in range(6, -1, -1)]

def get_task_distribution(user):
    todo = Task.objects.filter(assigned_to=user, status='todo').count()
    inprogress = Task.objects.filter(assigned_to=user, status='inprogress').count()
    done = Task.objects.filter(assigned_to=user, status='done').count()
    return [todo, inprogress, done]

def get_team_labels(user):
    teams = Team.objects.filter(members__user=user)
    return [team.name for team in teams]

def get_team_performance(user):
    teams = Team.objects.filter(members__user=user)
    return [Task.objects.filter(project__team=team, status='done').count() 
            for team in teams]

def get_trend_labels():
    return ['Week 1', 'Week 2', 'Week 3', 'Week 4']

def get_completion_trend(user):
    weeks = []
    for week in range(4):
        start_date = timezone.now() - timedelta(weeks=week+1)
        end_date = timezone.now() - timedelta(weeks=week)
        completed = Task.objects.filter(
            assigned_to=user,
            status='done',
            completed_at__range=[start_date, end_date]
        ).count()
        weeks.append(completed)
    return weeks[::-1]

@login_required
@csrf_protect
def mark_notification_as_read(request, notification_id):
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.read = True
            notification.save()
            return JsonResponse({'status': 'success'})
        except Notification.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def quick_create_task(request):
    if request.method == 'POST':
        with transaction.atomic():
            form = TaskForm(request.POST)
            if form.is_valid():
                task = form.save(commit=False)
                if not TeamMember.objects.filter(
                    user=request.user, 
                    team=task.project.team
                ).exists():
                    messages.error(request, "You don't have permission to create tasks in this project.")
                    return redirect('homepage')
                task.save()
                send_notification(task.assigned_to, f"You have been assigned a new task: {task.title}")
                messages.success(request, 'Task created successfully!')
                return redirect('task_detail', project_id=task.project.id, task_id=task.id)
    else:
        form = TaskForm()
    return render(request, 'projects/task_form.html', {
        'form': form, 
        'is_quick_create': True
    })

@login_required
def search_view(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': [], 'message': 'Query too short'})
    
    try:
        projects = Project.objects.filter(
            team__members__user=request.user,
            name__icontains=query
        ).distinct()
        tasks = Task.objects.filter(
            assigned_to=request.user,
            title__icontains=query
        )
        
        results = []
        for project in projects:
            results.append({
                'type': 'project',
                'title': project.name,
                'description': project.description[:100] if project.description else '',
                'url': reverse('project_detail', args=[project.id])
            })
        for task in tasks:
            results.append({
                'type': 'task',
                'title': task.title,
                'description': f'Task in {task.project.name}',
                'status': task.status,
                'url': reverse('task_detail', args=[task.project.id, task.id])
            })
        return JsonResponse({
            'status': 'success',
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while searching'
        }, status=500)


def base_context(request):
    if request.user.is_authenticated:
        try:
            notifications = (Notification.objects.filter(user=request.user)
                          .select_related('user')
                          .order_by('-created_at'))
            
            return {
                'projects_count': Project.objects.filter(
                    team__members__user=request.user
                ).distinct().count(),
                'tasks_count': Task.objects.filter(
                    assigned_to=request.user,
                    status__in=['todo', 'inprogress']
                ).count(),
                'notifications': notifications[:5],
                'unread_notifications_count': notifications.filter(read=False).count(),
            }
        except Exception as e:
            logger.error(f"Base context error: {str(e)}", exc_info=True)
            return {}
    return {}

@login_required
def project_update(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not has_team_permission(request.user, project.team):
        messages.error(request, "You don't have permission to update this project.")
        return redirect('homepage')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                form = ProjectForm(request.POST, instance=project)
                if form.is_valid():
                    updated_project = form.save()
                    messages.success(request, 'Project updated successfully!')
                    
                    # Send notification to team members
                    for member in project.team.members.all():
                        send_notification(
                            member.user,
                            f"Project '{updated_project.name}' was updated."
                        )
                    
                    return redirect('project_detail', project_id=project.id)
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
        except Exception as e:
            logger.error(f"Project update error: {str(e)}")
            messages.error(request, "An error occurred while updating the project.")
    else:
        form = ProjectForm(instance=project)
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'project': project,
        'is_update': True,
        'title': 'Update Project'
    })



