# Django imports
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.db import transaction
from django.contrib.auth import update_session_auth_hash, login, authenticate, logout
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import PermissionDenied
from django.db.models import (
    Count, F, Q, Subquery, OuterRef, FloatField, ExpressionWrapper,
    functions
)
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
from .models import Team, Project, Task, Profile, Notification, TeamMember, File, User
from .forms import (
    ProfileForm, TeamMemberForm, ReportForm,
    ProjectSearchForm, TeamSearchForm, ProjectForm, 
    TaskForm, CustomUserCreationForm, FileForm
)

# Utils imports
from .utils.analytics import (
    calculate_completion_rate,
    get_task_distribution,
    get_team_performance,
    get_completion_trend,
    get_timeline_labels,
    get_completed_tasks_data
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
    MSG_FILE_UPLOAD_ERROR,
    TASK_STATUS_DONE,
    TASK_STATUS_IN_PROGRESS,
    NOTIFICATION_SUCCESS,
    MSG_LOGIN_SUCCESS,
    MSG_LOGOUT_SUCCESS,
    MSG_INVALID_REQUEST
)

Cast = functions.Cast

# Initialize logger
logger = logging.getLogger(__name__)

# Core Views
def get_tasks_by_status(user):
    """Helper to get tasks organized by status"""
    tasks = Task.objects.filter(assigned_to=user).select_related('project')
    return {
        'todo_tasks': tasks.filter(status='todo'),
        'inprogress_tasks': tasks.filter(status='inprogress'),
        'done_tasks': tasks.filter(status='done')
    }

@login_required
@handle_view_errors
def homepage(request):
    try:
        # Get base context
        context = get_common_context(request.user)
        
        # Get tasks organized by status
        tasks_by_status = get_tasks_by_status(request.user)
        
        # Add page-specific data
        context.update({
            'projects': get_user_projects(request.user)[:5],
            'tasks': get_user_tasks(request.user),
            'recent_activity': get_recent_activity(request.user),
            'completion_rate': calculate_completion_rate(request.user),
            # Add Kanban board data
            'todo_tasks': tasks_by_status['todo_tasks'],
            'inprogress_tasks': tasks_by_status['inprogress_tasks'],
            'done_tasks': tasks_by_status['done_tasks'],
            'pending_tasks_count': Task.objects.filter(
                assigned_to=request.user
            ).exclude(status='done').count()
        })
        
        return render(request, 'projects/homepage.html', context)
    except Exception as e:
        logger.error(f"Homepage error: {str(e)}", exc_info=True)
        messages.error(request, MSG_ERROR)
        return redirect('login')

# Authentication Views
@handle_view_errors
def register(request):
    if request.user.is_authenticated:
        return redirect('homepage')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        try:
            if form.is_valid():
                user = form.save()
                # Create associated profile
                Profile.objects.create(user=user)
                login(request, user)
                messages.success(request, 'Registration successful!')
                return redirect('homepage')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            messages.error(request, "Registration failed. Please try again.")
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
def analytics_data(request):
    """API endpoint for analytics data"""
    try:
        time_range = int(request.GET.get('range', 7))
        user = request.user
        
        try:
            data = {
                'timelineLabels': get_timeline_labels(),
                'completedTasksData': get_completed_tasks_data(user, time_range),
                'taskDistribution': get_task_distribution(user),
                'teamLabels': [team.name for team in Team.objects.filter(members__user=user)],
                'teamPerformance': get_team_performance(user),
                'trendLabels': get_timeline_labels(),
                'completionTrend': get_completion_trend(user, time_range)  # Add time_range parameter
            }
            
            return JsonResponse(data)
        except Exception as e:
            raise ValueError(f"Error processing analytics data: {str(e)}")
            
    except Exception as e:
        logger.error(f"Analytics data error: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to fetch analytics data',
            'message': str(e)
        }, status=500)

@login_required
@handle_view_errors
def analytics_view(request):
    """View for analytics dashboard"""
    try:
        # Get timeline data
        timeline_data = get_timeline_labels()
        completed_tasks = get_completed_tasks_data(request.user)
        task_dist = get_task_distribution(request.user)
        teams = Team.objects.filter(members__user=request.user)
        team_labels = [team.name for team in teams]
        team_perf = get_team_performance(request.user)
        completion_trend = get_completion_trend(request.user)
        
        context = {
            'timeline_labels': json.dumps(timeline_data, cls=DjangoJSONEncoder),
            'completed_tasks_data': json.dumps(completed_tasks, cls=DjangoJSONEncoder),
            'task_distribution': json.dumps(task_dist, cls=DjangoJSONEncoder),
            'team_labels': json.dumps(team_labels, cls=DjangoJSONEncoder),
            'team_performance': json.dumps(team_perf, cls=DjangoJSONEncoder),
            'trend_labels': json.dumps(timeline_data, cls=DjangoJSONEncoder),
            'completion_trend': json.dumps(completion_trend, cls=DjangoJSONEncoder),
            'total_projects': Project.objects.count(),
            'active_tasks': Task.objects.exclude(status='done').count(),
            'team_members': User.objects.filter(is_active=True).count(),
            'completion_rate': calculate_completion_rate(request.user)
        }
        return render(request, 'projects/analytics.html', context)
        
    except Exception as e:
        logger.error(f"Analytics view error: {str(e)}", exc_info=True)
        messages.error(request, "Failed to load analytics")
        return redirect('homepage')

# API Views
@login_required
@handle_view_errors
@transaction_handler
def update_task_status(request, task_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        task = get_object_or_404(Task, id=task_id)
        if not has_task_permission(request.user, task):
            return JsonResponse({
                'success': False, 
                'message': MSG_PERMISSION_DENIED
            }, status=403)
        
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in dict(Task.STATUS_CHOICES).keys():
            return JsonResponse({
                'success': False,
                'message': 'Invalid status value'
            }, status=400)
            
        task.status = new_status
        task.last_active = timezone.now()
        if new_status == 'done':
            task.completed_at = timezone.now()
        task.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Task status updated successfully',
            'task': {
                'id': task.id,
                'status': task.status,
                'completion_rate': calculate_completion_rate(request.user)
            }
        })
            
    except Exception as e:
        logger.error(f"Task status update error: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': MSG_ERROR
        }, status=500)

# Profile Views
@login_required
@handle_view_errors
def view_profile(request):
    try:
        profile, created = Profile.objects.get_or_create(user=request.user)
        if created:
            profile.save()
            messages.info(request, "Profile created successfully!")
            
        context = {
            'profile': profile,
            'user': request.user,
            'projects_count': Project.objects.filter(team__members__user=request.user).count(),
            'tasks_count': Task.objects.filter(assigned_to=request.user).count(),
            'completion_rate': calculate_completion_rate(request.user)
        }
        return render(request, 'profile/view_profile.html', context)
    except Exception as e:
        logger.error(f"Profile view error: {str(e)}")
        messages.error(request, "Error accessing profile")
        return redirect('homepage')
        
@login_required
@handle_view_errors
@transaction_handler
def update_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('view_profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    return render(request, 'profile/update_profile.html', {'form': form})

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
    """User settings view"""
    context = {
        'user': request.user,
        'profile': request.user.profile,
        'notifications_enabled': True,
        'form': PasswordChangeForm(request.user),
        'teams': Team.objects.filter(members__user=request.user).distinct()
    }
    return render(request, 'settings/settings.html', context)

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
    try:
        query = request.GET.get('q', '').strip()
        if len(query) < 2:
            return JsonResponse({
                'status': 'error',
                'message': 'Query too short'
            })

        # Search projects and tasks
        projects = Project.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        )[:5]

        tasks = Task.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        )[:5]

        results = []
        
        for project in projects:
            results.append({
                'type': 'project',
                'title': project.title,
                'url': f'/projects/{project.id}/'
            })
            
        for task in tasks:
            results.append({
                'type': 'task',
                'title': task.title,
                'url': f'/tasks/{task.id}/'
            })

        return JsonResponse({
            'status': 'success',
            'results': results
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@csrf_exempt
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
    """Clear all notifications for current user"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
        
    try:
        count = Notification.objects.filter(user=request.user).delete()[0]
        return JsonResponse({
            'status': 'success',
            'message': f'Cleared {count} notifications',
            'unread_count': 0
        })
    except Exception as e:
        logger.error(f"Clear notifications error: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': 'Failed to clear notifications'
        }, status=500)

@login_required
def mark_notification_as_read(request, notification_id):
    """Mark specific notification as read"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
        
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id, 
            user=request.user
        )
        notification.read = True
        notification.save()
        
        unread_count = Notification.objects.filter(
            user=request.user, 
            read=False
        ).count()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Notification marked as read',
            'unread_count': unread_count
        })
    except Notification.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Notification not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Mark notification error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to mark notification as read'
        }, status=500)

login_required
@handle_view_errors
def all_team_members(request):
    """View to display all team members across teams"""
    teams = Team.objects.filter(
        members__user=request.user
    ).prefetch_related(
        'members',
        'members__user',
        'members__user__profile',
        'projects',
        'members__user__assigned_tasks'
    ).annotate(
        completion_rate=Subquery(
            Task.objects.filter(
                project__team=OuterRef('pk'),
                status='done'
            ).values('project__team')
            .annotate(rate=ExpressionWrapper(
                Cast(Count('id'), output_field=FloatField()) * 100.0 / 
                Cast(Count('project'), output_field=FloatField()),
                output_field=FloatField()
            ))
            .values('rate')[:1]
        )
    ).distinct()
    
    context = {
        'teams': teams,
        'user_is_staff': request.user.is_staff
    }
    return render(request, 'projects/all_team_members.html', context)

@login_required
@handle_view_errors
@transaction_handler
def invite_team_member(request, team_id):
    """Handle team member invitation"""
    team = get_object_or_404(Team, id=team_id)
    if not can_manage_team(request.user, team):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('team_detail', team_id=team_id)

    try:
        if request.method == 'POST':
            email = request.POST.get('email')
            role = request.POST.get('role', 'member')
            
            try:
                user = User.objects.get(email=email)
                if not TeamMember.objects.filter(team=team, user=user).exists():
                    TeamMember.objects.create(
                        team=team,
                        user=user,
                        role=role
                    )
                    messages.success(request, f'Successfully added {user.username} to the team.')
                else:
                    messages.warning(request, 'User is already a member of this team.')
            except User.DoesNotExist:
                messages.error(request, 'No user found with that email address.')
            
        return redirect('all_team_members')
            
    except Exception as e:
        logger.error(f"Team member invitation error: {str(e)}")
        messages.error(request, MSG_ERROR)
        return redirect('all_team_members')

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
        return JsonResponse({
            'success': False,
            'message': MSG_PERMISSION_DENIED
        }, status=403)
        
    if request.method == 'POST':
        try:
            project.delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Project deleted successfully!'
                })
            messages.success(request, 'Project deleted successfully!')
            return redirect('project_list')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=500)
            messages.error(request, f'Error deleting project: {str(e)}')
            return redirect('project_detail', project_id=project_id)
            
    return render(request, 'projects/project_detail.html', {'project': project})

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
    # Get tasks by status using the helper function
    tasks_by_status = get_tasks_by_status(request.user)
    
    context = {
        'todo_tasks': tasks_by_status['todo_tasks'],
        'inprogress_tasks': tasks_by_status['inprogress_tasks'],
        'done_tasks': tasks_by_status['done_tasks'],
        'completion_rate': calculate_completion_rate(request.user)
    }
    
    return render(request, 'projects/task_list.html', context)

def base_context(request):
    """Context processor to add common data to all templates"""
    if request.user.is_authenticated:
        user_teams = Team.objects.filter(members__user=request.user).distinct()
        user_tasks = Task.objects.filter(assigned_to=request.user)
        
        return {
            'unread_notifications': Notification.objects.filter(
                user=request.user, 
                read=False
            ).count(),
            'user_teams': user_teams,
            'team_members_count': TeamMember.objects.filter(
                team__in=user_teams
            ).distinct().count(),
            'completed_tasks_count': user_tasks.filter(
                status=TASK_STATUS_DONE
            ).count(),
            'tasks_count': user_tasks.count(),
            'projects_count': Project.objects.filter(
                team__in=user_teams
            ).distinct().count(),
            'active_projects_count': Project.objects.filter(
                team__in=user_teams,
                status='active'
            ).distinct().count(),
            'pending_tasks_count': user_tasks.filter(
                status__in=['todo', 'inprogress']
            ).count(),
            'completion_rate': calculate_completion_rate(request.user)
        }
    return {}   


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
    
    try:
        if request.method == 'POST':
            form = FileForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.save(commit=False)
                file.uploaded_by = request.user
                file.save()
                messages.success(request, 'File uploaded successfully!')
                return redirect('project_files', project_id=project_id)
            else:
                for error in form.errors.values():
                    messages.error(request, error)
        else:
            form = FileForm()
        
        return render(request, 'projects/upload_file.html', {
            'form': form,
            'project': project
        })
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        messages.error(request, MSG_FILE_UPLOAD_ERROR)
        return redirect('project_files', project_id=project_id)

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

@login_required
@handle_view_errors
@transaction_handler
def update_avatar(request):
    """Update user profile avatar"""
    if request.method == 'POST':
        try:
            profile = request.user.profile
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            return JsonResponse({
                'status': 'success',
                'avatar_url': profile.profile_picture.url
            })
        except Exception as e:
            logger.error(f"Avatar update error: {str(e)}")
            return JsonResponse({
                'status': 'error', 
                'message': MSG_AVATAR_UPDATE_ERROR
            })
    return JsonResponse({'status': 'error', 'message': MSG_INVALID_REQUEST})

@login_required
def notification_list(request):
    """Display all notifications or return JSON for AJAX requests"""
    notifications_queryset = (
        Notification.objects.filter(user=request.user)
        .select_related('user')
        .order_by('-created_at')
    )
    
    unread_count = notifications_queryset.filter(read=False).count()
    
    # Handle AJAX requests for JSON data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'notifications': [
                {
                    'id': n.id,
                    'message': n.message,
                    'created_at': n.created_at.isoformat(),
                    'read': n.read
                } for n in notifications_queryset[:5]  # Return latest 5
            ],
            'unread_count': unread_count
        })

    # Handle regular page request
    paginator = Paginator(notifications_queryset, 10)
    page = request.GET.get('page')
    notifications = paginator.get_page(page)
    
    return render(request, 'projects/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count
    })

def handler404(request, exception):
    """Custom 404 error handler"""
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """Custom 500 error handler"""
    return render(request, 'errors/500.html', status=500)

def handler403(request, exception):
    """Custom 403 error handler"""
    return render(request, 'errors/403.html', status=403)   