# Django imports
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.db import transaction
from django.contrib.auth import update_session_auth_hash, login, authenticate, logout
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from datetime import datetime
# Python imports
import json
import logging

# Local imports
from .models import Team, Project, Task, Profile, Notification, TeamMember
from .forms import (
    ProfileForm, TeamMemberForm, ReportForm,
    ProjectSearchForm, TeamSearchForm, ProjectForm, 
    TaskForm, CustomUserCreationForm
)

# Utils imports
from .utils.analytics import (
    calculate_completion_rate,
    get_task_distribution,
    get_team_performance,
    get_completion_trend,
    get_timeline_labels
)
from .utils.team import get_user_team_members
from .utils.tasks import get_user_tasks, get_recent_activity
from .utils.projects import get_user_projects
from .utils.reports import generate_report
from .utils.notifications import send_notification
from .utils.common import get_common_context  # Add this import
from .utils.permissions import (
    can_manage_project,
    has_team_permission,
    has_project_permission,
    has_task_permission,
    can_manage_team
)
from .utils.decorators import (
    handle_view_errors,
    transaction_handler,
    team_permission_required
)
from .utils.constants import (
    MSG_PERMISSION_DENIED,
    MSG_SUCCESS,
    MSG_ERROR,
    TASK_STATUS_DONE,
    TASK_STATUS_IN_PROGRESS,
    NOTIFICATION_SUCCESS,
    MSG_LOGIN_SUCCESS,
    MSG_LOGOUT_SUCCESS,
    MSG_INVALID_REQUEST
)

# Initialize logger
logger = logging.getLogger(__name__)

# Core Views
@login_required
@handle_view_errors
def homepage(request):
    try:
        projects = get_user_projects(request.user)
        tasks = get_user_tasks(request.user)
        context = get_common_context(request.user)
        context.update({
            'projects': projects,
            'tasks': tasks,
            'recent_activity': get_recent_activity(request.user)
        })
        return render(request, 'projects/homepage.html', context)
    except Exception as e:
        logger.error(f"Homepage error: {str(e)}")
        messages.error(request, MSG_ERROR)
        return redirect('login')

# Authentication Views
@handle_view_errors
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('homepage')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@handle_view_errors
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:  # Add active check
                    login(request, user)
                    messages.success(request, MSG_LOGIN_SUCCESS)
                    return redirect('homepage')
            else:
                messages.error(request, "Invalid username or password")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, MSG_LOGOUT_SUCCESS)
    return redirect('login')

# Project Views
@login_required
@handle_view_errors
def project_list(request):
    projects = get_user_projects(request.user)
    paginator = Paginator(projects, 10)  # Show 10 projects per page
    page = request.GET.get('page')
    projects = paginator.get_page(page)
    return render(request, 'projects/project_list.html', {'projects': projects})

@login_required
@handle_view_errors
@transaction_handler
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            try:
                project = form.save(commit=False)
                project.created_by = request.user
                project.manager = request.user
                project.created_at = timezone.now()  # Ensure timezone-aware datetime
                project.save()
                messages.success(request, 'Project created successfully!')
                return redirect('project_detail', project_id=project.id)
            except Exception as e:
                logger.error(f"Project creation error: {str(e)}")
                messages.error(request, MSG_ERROR)
                return redirect('project_list')  # Add error redirect
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ProjectForm()
    return render(request, 'projects/project_form.html', {'form': form})

@login_required
@handle_view_errors
def project_detail(request, project_id):
    project = get_object_or_404(Project.objects.select_related('team', 'manager'), id=project_id)
    if not has_project_permission(request.user, project):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('project_list')
    
    tasks = Task.objects.filter(project=project).select_related('assigned_to', 'project')
    context = {
        'project': project,
        'tasks': tasks,
        'can_manage': can_manage_project(request.user, project)
    }
    return render(request, 'projects/project_detail.html', context)

# Task Views
@login_required
@handle_view_errors
@transaction_handler
def task_create(request, project_id=None):
    project = None
    try:
        if project_id:
            project = get_object_or_404(Project, id=project_id)
            if not has_project_permission(request.user, project):
                messages.error(request, MSG_PERMISSION_DENIED)
                return redirect('project_list')

        if request.method == 'POST':
            form = TaskForm(request.POST)
            if form.is_valid():
                task = form.save(commit=False)
                task.created_by = request.user
                if project:
                    task.project = project
                task.save()
                messages.success(request, 'Task created successfully!')
                return redirect('task_detail', project_id=task.project.id, task_id=task.id)
        else:
            form = TaskForm(initial={'project': project} if project else None)
        
        return render(request, 'projects/task_form.html', {
            'form': form,
            'project': project
        })
    except Exception as e:
        logger.error(f"Task creation error: {str(e)}")
        messages.error(request, MSG_ERROR)
        return redirect('project_list')

@login_required
@handle_view_errors
def task_detail(request, project_id, task_id):
    task = get_object_or_404(Task.objects.select_related('project', 'assigned_to'), 
                            id=task_id, project_id=project_id)
    if not has_task_permission(request.user, task):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('project_detail', project_id=project_id)
    
    return render(request, 'projects/task_detail.html', {'task': task})

@login_required
@handle_view_errors
@transaction_handler
def task_update(request, project_id, task_id):
    task = get_object_or_404(Task, id=task_id, project_id=project_id)
    if not has_task_permission(request.user, task):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('task_detail', project_id=project_id, task_id=task_id)

    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully!')
            return redirect('task_detail', project_id=project_id, task_id=task_id)
    else:
        form = TaskForm(instance=task)
    
    return render(request, 'projects/task_form.html', {
        'form': form,
        'task': task,
        'project': task.project
    })

# Team Views
@login_required
@handle_view_errors
def team_list(request):
    teams = Team.objects.filter(members__user=request.user).distinct()
    return render(request, 'projects/team_list.html', {'teams': teams})

@login_required
@handle_view_errors
@transaction_handler
def team_create(request):
    try:
        if request.method == 'POST':
            team = Team.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                owner=request.user
            )
            TeamMember.objects.create(team=team, user=request.user)
            messages.success(request, 'Team created successfully!')
            return redirect('team_detail', team_id=team.id)
    except Exception as e:
        logger.error(f"Team creation error: {str(e)}")
        messages.error(request, MSG_ERROR)
        return redirect('team_list')
    return render(request, 'projects/team_form.html')

@login_required
@handle_view_errors
@team_permission_required
def team_detail(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    context = {
        'team': team,
        'members': team.members.all(),
        'projects': team.projects.all(),
        'can_manage': can_manage_team(request.user, team)
    }
    return render(request, 'projects/team_detail.html', context)

@login_required
@handle_view_errors
def analytics_view(request):
    if not request.user.is_staff:
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('homepage')
        
    context = {
        'task_distribution': get_task_distribution(request.user),
        'team_performance': get_team_performance(request.user),
        'completion_trend': get_completion_trend(request.user),
        'timeline_labels': get_timeline_labels(),
        'total_projects': Project.objects.count(),
        'total_tasks': Task.objects.count(),
        'active_tasks': Task.objects.filter(status='inprogress').count(),
        'team_members': TeamMember.objects.count(),  # Add this
        'completion_rate': calculate_completion_rate(request.user)  # Add this
    }
    return render(request, 'projects/analytics.html', context)

# API Views
@login_required
@handle_view_errors
@transaction_handler
def update_task_status(request, task_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': MSG_INVALID_REQUEST})
    
    try:
        task = get_object_or_404(Task, id=task_id)
        if not has_task_permission(request.user, task):
            return JsonResponse({'status': 'error', 'message': MSG_PERMISSION_DENIED})
        
        data = json.loads(request.body)
        new_status = data.get('status')
        if new_status:
            task.status = new_status
            if new_status == TASK_STATUS_DONE:
                task.completed_at = timezone.now()
            task.save()
            return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Task status update error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': MSG_ERROR})

# Profile Views
@login_required
@handle_view_errors
def view_profile(request):
    try:
        # Get or create profile for user
        profile, created = Profile.objects.get_or_create(user=request.user)
        if created:
            # Set default values if needed
            profile.save()
            messages.info(request, "Profile created successfully!")
            
        return render(request, 'profile/view_profile.html', {'profile': profile})  # Update path
    except Exception as e:
        logger.error(f"Profile view error: {str(e)}")
        messages.error(request, "Error accessing profile")
        return redirect('homepage')
        
@login_required
@handle_view_errors
@transaction_handler
def update_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('view_profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    return render(request, 'profile/update_profile.html', {'form': form})  # Update path

@login_required
@handle_view_errors
@transaction_handler
def delete_account(request):
    if request.method == 'POST':
        request.user.delete()
        messages.success(request, 'Your account has been deleted.')
        return redirect('login')
    return render(request, 'projects/delete_account.html')

# Settings Views
@login_required
@handle_view_errors
def settings_view(request):
    return render(request, 'projects/settings.html')

@login_required
@handle_view_errors
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('settings')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'projects/change_password.html', {'form': form})

# Progress & Reports Views
@login_required
@handle_view_errors
def progress(request):
    context = {
        'completion_rate': calculate_completion_rate(request.user),
        'recent_tasks': get_user_tasks(request.user)[:5],
        'timeline_data': get_completion_trend(request.user)
    }
    return render(request, 'projects/progress.html', context)

@login_required
@handle_view_errors
def member_progress(request):
    if not request.user.is_staff:
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('homepage')
    
    team_members = get_user_team_members(request.user)
    context = {
        'members': team_members,
        'performance_data': get_team_performance(request.user)
    }
    return render(request, 'projects/member_progress.html', context)

@login_required
@handle_view_errors
def reports_view(request):
    try:
        if request.method == 'POST':
            form = ReportForm(request.POST)
            if form.is_valid():
                start_date = timezone.make_aware(
                    datetime.combine(form.cleaned_data['start_date'], datetime.min.time())
                )
                end_date = timezone.make_aware(
                    datetime.combine(form.cleaned_data['end_date'], datetime.max.time())
                )
                report_type = form.cleaned_data['report_type']
                
                report_data = generate_report(request.user, start_date, end_date, report_type)
                if not report_data:
                    messages.error(request, MSG_ERROR)
                    return redirect('reports')
                    
                return render(request, 'projects/report_result.html', {
                    'report_data': report_data,
                    'form': form
                })
        else:
            form = ReportForm()
        return render(request, 'projects/reports.html', {'form': form})
    except Exception as e:
        logger.error(f"Report generation error: {str(e)}")
        messages.error(request, MSG_ERROR)
        return redirect('homepage')

# Team Member Management Views
@login_required
@handle_view_errors
@team_permission_required
def manage_team_members(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    if not can_manage_team(request.user, team):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('team_detail', team_id=team_id)

    try:
        if request.method == 'POST':
            form = TeamMemberForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data['user']
                if not TeamMember.objects.filter(team=team, user=user).exists():
                    TeamMember.objects.create(team=team, user=user)
                    messages.success(request, f'{user.username} added to team.')
                else:
                    messages.warning(request, f'{user.username} is already in the team.')
                return redirect('manage_team_members', team_id=team_id)
        else:
            form = TeamMemberForm()

        members = team.members.select_related('user').all()
        return render(request, 'projects/manage_team_members.html', {
            'team': team,
            'members': members,
            'form': form
        })
    except Exception as e:
        logger.error(f"Team member management error: {str(e)}")
        messages.error(request, MSG_ERROR)
        return redirect('team_detail', team_id=team_id)

@login_required
@handle_view_errors
@team_permission_required
def remove_team_member(request, team_id, member_id):
    team = get_object_or_404(Team, id=team_id)
    if not can_manage_team(request.user, team):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('team_detail', team_id=team_id)
    
    member = get_object_or_404(TeamMember, id=member_id, team=team)
    if member.user == team.owner:
        messages.error(request, "Cannot remove team owner.")
    else:
        member.delete()
        messages.success(request, "Member removed successfully.")
    return redirect('manage_team_members', team_id=team_id)

# Search Views
@login_required
@handle_view_errors
def search_view(request):
    query = request.GET.get('q', '')
    if query:
        projects = Project.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query),
            team__members__user=request.user
        ).distinct()
        
        tasks = Task.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query),
            project__team__members__user=request.user
        ).distinct()
    else:
        projects = Project.objects.none()
        tasks = Task.objects.none()
        
    context = {
        'query': query,
        'projects': projects,
        'tasks': tasks
    }
    return render(request, 'projects/search_results.html', context)

@login_required
@handle_view_errors
def api_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({
            'status': 'error',
            'message': 'Query too short'
        })
    
    try:
        projects = Project.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query),
            team__members__user=request.user
        ).distinct()[:5]
        
        tasks = Task.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query),
            project__team__members__user=request.user
        ).distinct()[:5]
        
        results = []
        for project in projects:
            results.append({
                'type': 'project',
                'id': project.id,
                'title': project.name,
                'url': reverse('project_detail', args=[project.id])
            })
            
        for task in tasks:
            results.append({
                'type': 'task',
                'id': task.id,
                'title': task.title,
                'url': reverse('task_detail', args=[task.project.id, task.id])
            })
            
        return JsonResponse({
            'status': 'success',
            'results': results
        })
    except Exception as e:
        logger.error(f"API search error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': MSG_ERROR
        })

# Notification Views
@login_required
@transaction_handler
def clear_all_notifications(request):
    try:
        Notification.objects.filter(user=request.user).delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Clear notifications error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': MSG_ERROR})

@login_required
def mark_notification_as_read(request, notification_id):
    try:
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Mark notification error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': MSG_ERROR})

@login_required
@handle_view_errors
def all_team_members(request):
    """View to display all team members across teams"""
    teams = Team.objects.filter(members__user=request.user).distinct()
    context = {
        'teams': teams,
        'user_is_staff': request.user.is_staff
    }
    return render(request, 'projects/all_team_members.html', context)

@login_required
@handle_view_errors
@transaction_handler
def quick_create_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            messages.success(request, 'Task created successfully!')
            return redirect('task_detail', project_id=task.project.id, task_id=task.id)
    return redirect('homepage')

@login_required
@handle_view_errors
@transaction_handler
def project_update(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not has_project_permission(request.user, project):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('project_list')

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project updated successfully!')
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/project_form.html', {'form': form, 'project': project})

@login_required
@handle_view_errors
@transaction_handler
def project_delete(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not has_project_permission(request.user, project):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('project_list')
        
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project deleted successfully!')
        return redirect('project_list')
    return render(request, 'projects/project_confirm_delete.html', {'project': project})

@login_required
@handle_view_errors
def team_projects(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    if not has_team_permission(request.user, team):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('team_list')
        
    projects = Project.objects.filter(team=team)
    return render(request, 'projects/team_projects.html', {
        'team': team,
        'projects': projects
    })

@login_required
@handle_view_errors
@transaction_handler
def task_delete(request, project_id, task_id):
    task = get_object_or_404(Task, id=task_id, project_id=project_id)
    if not has_task_permission(request.user, task):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('project_detail', project_id=project_id)
        
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted successfully!')
        return redirect('project_detail', project_id=project_id)
    return render(request, 'projects/task_confirm_delete.html', {'task': task})

@login_required
@handle_view_errors
def team_members(request, team_id):
    """View to display members of a specific team"""
    team = get_object_or_404(Team, id=team_id)
    if not has_team_permission(request.user, team):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('homepage')
        
    members = TeamMember.objects.filter(team=team).select_related('user')
    return render(request, 'projects/team_members.html', {
        'team': team,
        'members': members,
        'is_owner': team.owner == request.user
    })

@login_required
@handle_view_errors
def task_list(request):
    """View to display all tasks for the current user"""
    tasks = get_user_tasks(request.user)
    paginator = Paginator(tasks, 10)
    page = request.GET.get('page')
    tasks = paginator.get_page(page)
    return render(request, 'projects/task_list.html', {'tasks': tasks})

def base_context(request):
    """Context processor to add common data to all templates"""
    if request.user.is_authenticated:
        return {
            'unread_notifications': Notification.objects.filter(
                user=request.user, 
                read=False
            ).count(),
            'user_teams': Team.objects.filter(
                members__user=request.user
            ).distinct(),
            'team_members_count': TeamMember.objects.filter(
                team__members__user=request.user
            ).distinct().count(),
            'completed_tasks_count': Task.objects.filter(
                assigned_to=request.user,
                status=TASK_STATUS_DONE
            ).count(),
            'tasks_count': Task.objects.filter(
                assigned_to=request.user
            ).count()
        }
    return {}    

@login_required
@handle_view_errors
def notification_list(request):
    """View to display all notifications for the current user"""
    notifications = (Notification.objects.filter(user=request.user)
                    .select_related('user')
                    .order_by('-created_at'))
    
    paginator = Paginator(notifications, 10)  # Show 10 notifications per page
    page = request.GET.get('page')
    notifications = paginator.get_page(page)
    
    return render(request, 'projects/notifications.html', {
        'notifications': notifications,
        'unread_count': notifications.filter(read=False).count()
    })

# In views.py, add these new views

@login_required
@handle_view_errors
def project_stats(request, project_id):
    """Display project statistics"""
    project = get_object_or_404(Project.objects.select_related('team', 'manager'), id=project_id)
    if not has_project_permission(request.user, project):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('project_list')
    
    context = {
        'project': project,
        'completion_rate': calculate_completion_rate(project.tasks.all()),
        'task_distribution': get_task_distribution(request.user, project),
        'timeline_data': get_completion_trend(request.user, project)
    }
    return render(request, 'projects/project_stats.html', context)

@login_required
@handle_view_errors
def project_timeline(request, project_id):
    """Display project timeline"""
    project = get_object_or_404(Project.objects.select_related('team', 'manager'), id=project_id)
    if not has_project_permission(request.user, project):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('project_list')
    
    tasks = Task.objects.filter(project=project).order_by('start_date')
    context = {
        'project': project,
        'tasks': tasks,
        'timeline_labels': get_timeline_labels()
    }
    return render(request, 'projects/project_timeline.html', context)

@login_required
@handle_view_errors
def member_detail(request, team_id, member_id):
    """Display team member details"""
    team = get_object_or_404(Team, id=team_id)
    member = get_object_or_404(TeamMember, id=member_id, team=team)
    if not has_team_permission(request.user, team):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('team_list')
    
    context = {
        'team': team,
        'member': member,
        'tasks': Task.objects.filter(assigned_to=member.user, project__team=team)
    }
    return render(request, 'projects/member_detail.html', context)

@login_required
@handle_view_errors
def member_tasks(request, team_id, member_id):
    """Display tasks assigned to team member"""
    team = get_object_or_404(Team, id=team_id)
    member = get_object_or_404(TeamMember, id=member_id, team=team)
    if not has_team_permission(request.user, team):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('team_list')
    
    tasks = Task.objects.filter(assigned_to=member.user, project__team=team)
    return render(request, 'projects/member_tasks.html', {
        'team': team,
        'member': member,
        'tasks': tasks
    })

@login_required
@handle_view_errors
def dashboard(request):
    """Main dashboard view"""
    context = get_common_context(request.user)
    return render(request, 'projects/dashboard.html', context)

@login_required
@handle_view_errors
def dashboard_overview(request):
    """Dashboard overview with analytics"""
    context = {
        'projects': get_user_projects(request.user),
        'tasks': get_user_tasks(request.user),
        'completion_rate': calculate_completion_rate(request.user),
        'task_distribution': get_task_distribution(request.user)
    }
    return render(request, 'projects/dashboard_overview.html', context)

@login_required
@handle_view_errors
@transaction_handler
def project_files(request, project_id):
    """Display project files"""
    project = get_object_or_404(Project, id=project_id)
    if not has_project_permission(request.user, project):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('project_list')
    
    files = File.objects.filter(task__project=project)
    return render(request, 'projects/project_files.html', {
        'project': project,
        'files': files
    })

@login_required
@handle_view_errors
@transaction_handler
def upload_file(request, project_id):
    """Upload file to project"""
    project = get_object_or_404(Project, id=project_id)
    if not has_project_permission(request.user, project):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('project_list')
    
    if request.method == 'POST':
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.save(commit=False)
            file.uploaded_by = request.user
            file.save()
            messages.success(request, 'File uploaded successfully!')
            return redirect('project_files', project_id=project_id)
    else:
        form = FileForm()
    
    return render(request, 'projects/upload_file.html', {
        'form': form,
        'project': project
    })

@login_required
@handle_view_errors
@transaction_handler
def delete_file(request, file_id):
    """Delete project file"""
    file = get_object_or_404(File, id=file_id)
    if not has_project_permission(request.user, file.task.project):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('project_list')
    
    project_id = file.task.project.id
    file.delete()
    messages.success(request, 'File deleted successfully!')
    return redirect('project_files', project_id=project_id)    