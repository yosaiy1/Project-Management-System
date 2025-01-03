from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction, connection
from django.db.models import (
    Count, 
    Q, 
    F, 
    FloatField, 
    Case, 
    When, 
    Value, 
    ExpressionWrapper,
    Max,
    functions,
    Subquery,  # Add this
    OuterRef,  # Add this
)
from django.db.models.functions import Cast  # Change this line
from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt, csrf_protect

# Python standard library imports
from datetime import datetime
import json
import logging

# Local model imports
from .models import (
    Team, 
    Project, 
    Task, 
    Profile, 
    Notification, 
    TeamMember, 
    File, 
    User
)

# Local form imports
from .forms import (
    ProfileForm,
    TeamMemberForm,
    ReportForm,
    ProjectSearchForm,
    TeamSearchForm,
    ProjectForm,
    TaskForm,
    TeamForm,
    CustomUserCreationForm,
    FileForm,
    CustomTeamMemberCreationForm,
    CustomLoginForm
)

# Local utility imports
from .utils.analytics import (
    calculate_completion_rate,
    get_task_distribution,
    get_team_performance,
    get_completion_trend,
    get_timeline_labels,
    get_completed_tasks_data
)
from .utils.team import (
    get_team_stats,
    can_manage_team,
    get_team_members_with_stats,
    get_user_team_members,
    notify_team_created,
    notify_team_update
)
from .utils.tasks import (
    get_user_tasks,
    get_recent_activity
)
from .utils.projects import get_user_projects
from .utils.reports import generate_report
from .utils.email import send_team_removal_email 
from .utils.notifications import send_notification
from .utils.common import get_common_context
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
    team_permission_required,
    team_manager_required
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
    """Homepage view showing dashboard with projects, tasks and activity"""
    try:
        # Get projects with all necessary relationships
        projects = Project.objects.filter(
            Q(team__members__user=request.user) |      # Team member projects
            Q(team__owner=request.user) |              # Owned projects
            Q(manager=request.user) |                  # Managed projects
            Q(tasks__assigned_to=request.user)         # Projects with assigned tasks
        ).distinct().select_related(
            'team',
            'manager'
        ).prefetch_related(
            'team__members',
            'team__members__user',
            'tasks'
        ).order_by('-created_at')

        # Get tasks organized by status
        tasks = Task.objects.filter(
            Q(assigned_to=request.user) |              # Tasks assigned to user
            Q(project__manager=request.user)           # Tasks in managed projects
        ).select_related(
            'project',
            'assigned_to'
        )

        todo_tasks = tasks.filter(status='todo')
        inprogress_tasks = tasks.filter(status='inprogress')
        done_tasks = tasks.filter(status='done')

        # Calculate stats
        total_tasks = tasks.count()
        completed_tasks = done_tasks.count()
        pending_tasks = total_tasks - completed_tasks
        completion_rate = int((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0)

        # Prepare context
        context = {
            'projects': projects[:5],                  # 5 most recent projects
            'total_projects': projects.count(),
            'active_projects': projects.filter(status='active'),
            'tasks': tasks,
            'tasks_count': total_tasks,
            'completed_tasks_count': completed_tasks,
            'pending_tasks_count': pending_tasks,
            'completion_rate': completion_rate,
            
            # Kanban board data
            'todo_tasks': todo_tasks,
            'inprogress_tasks': inprogress_tasks,
            'done_tasks': done_tasks,

            # Project counts
            'total_projects_count': projects.count(),
            'active_projects_count': projects.filter(status='active').count()
        }

        return render(request, 'projects/homepage.html', context)

    except Exception as e:
        logger.error(f"Homepage error: {str(e)}", exc_info=True)
        messages.error(request, "An error occurred loading the dashboard. Please try again.")
        return redirect('login')

# Authentication Views
@handle_view_errors
def register(request):
    """Handle regular user/project manager registration"""
    if request.user.is_authenticated:
        return redirect('homepage')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        try:
            if form.is_valid():
                with transaction.atomic():
                    user = form.save()
                    
                    # Log the user in after registration
                    login(request, user)
                    
                    if user.is_project_manager:
                        messages.success(request, 'Account created successfully as Project Manager!')
                    else:
                        messages.success(request, 'Account created successfully!')
                    
                    return redirect('homepage')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            messages.error(request, "Registration failed. Please try again.")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

@handle_view_errors 
def login_view(request):
    """Handle user authentication and login"""
    if request.user.is_authenticated:
        return redirect('homepage')
        
    if request.method == 'POST':
        form = CustomLoginForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember = form.cleaned_data.get('remember')
            
            try:
                # Check if input is email
                if '@' in username:
                    try:
                        user = User.objects.get(email__iexact=username)
                        username = user.username
                    except User.DoesNotExist:
                        messages.error(request, "No account found with this email address.")
                        return render(request, 'registration/login.html', {'form': form})

                # Authenticate with username
                user = authenticate(request, username=username, password=password)
                
                if user is not None and user.is_active:
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.username}!")
                    
                    # Handle remember me
                    if remember:
                        request.session.set_expiry(1209600)  # 2 weeks
                    else:
                        request.session.set_expiry(0)

                    # Redirect to next URL or homepage
                    next_url = request.GET.get('next', 'homepage')
                    return redirect(next_url)
                else:
                    if user is None:
                        messages.error(request, "Invalid username/email or password.")
                    else:
                        messages.error(request, "This account is inactive.")
            except Exception as e:
                messages.error(request, f"Login failed. {str(e)}")
    else:
        form = CustomLoginForm()
    
    return render(request, 'registration/login.html', {'form': form})

@handle_view_errors
def logout_view(request):
    """Handle user logout"""
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been successfully logged out.")
        return redirect('login')
    return redirect('homepage')

# Project Views
@login_required
@handle_view_errors
def project_list(request):
    """View for displaying all accessible projects"""
    try:
        # Get base context first
        context = get_common_context(request)
        
        # Get all accessible projects
        projects = Project.objects.filter(
            Q(team__members__user=request.user) |
            Q(team__owner=request.user) |
            Q(manager=request.user) |
            Q(tasks__assigned_to=request.user)
        ).distinct().select_related(
            'team',
            'manager'
        ).prefetch_related(
            'team__members',
            'tasks',
            'tasks__assigned_to'
        ).order_by('-created_at')

        # Split projects by role
        context.update({
            'managed_projects': projects.filter(
                Q(manager=request.user) | Q(team__owner=request.user)
            ),
            'team_projects': projects.filter(
                team__members__user=request.user
            ).exclude(
                Q(manager=request.user) | Q(team__owner=request.user)
            ),
            'assigned_projects': projects.filter(
                tasks__assigned_to=request.user
            ).exclude(
                Q(team__members__user=request.user) | 
                Q(manager=request.user) | 
                Q(team__owner=request.user)
            ),
            'projects_count': projects.count(),
            'active_projects_count': projects.filter(status='active').count()
        })
        
        return render(request, 'projects/project_list.html', context)

    except Exception as e:
        logger.error(f"Project list error: {str(e)}")
        messages.error(request, "Error loading projects. Please try again.")
        return redirect('homepage')

@login_required
@handle_view_errors
@transaction_handler
def project_create(request):
    """Create a new project"""
    try:
        if request.method == 'POST':
            form = ProjectForm(request.POST)
            if form.is_valid():
                project = form.save(commit=False)
                project.created_by = request.user
                
                # Set the manager to the current user if they're the team owner or project manager
                team = form.cleaned_data['team']
                if request.user == team.owner or request.user.is_project_manager:
                    project.manager = request.user
                else:
                    # For team managers, set them as project manager
                    member = TeamMember.objects.get(team=team, user=request.user)
                    if member.role == 'manager':
                        project.manager = request.user
                    else:
                        project.manager = team.owner  # Default to team owner
                
                project.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Project created successfully',
                        'redirect_url': reverse('project_detail', kwargs={'project_id': project.id})
                    })
                return redirect('project_detail', project_id=project.id)
                
        else:
            form = ProjectForm()
            
        return render(request, 'projects/project_form.html', {
            'form': form,
            'teams': request.user.get_accessible_teams()
        })
        
    except Exception as e:
        logger.error(f"Project creation error: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
        messages.error(request, MSG_ERROR)
        return redirect('project_list')

@login_required
@handle_view_errors
def project_detail(request, project_id):
    """Display project details"""
    try:
        # Get project with related data
        project = get_object_or_404(
            Project.objects.select_related(
                'team', 
                'manager'
            ).prefetch_related(
                'team__members',
                'team__members__user',
                'tasks',
                'tasks__assigned_to'
            ),
            id=project_id
        )

        # Check permissions
        if not has_project_permission(request.user, project):
            messages.error(request, MSG_PERMISSION_DENIED)
            return redirect('project_list')
        
        # Get tasks
        tasks = Task.objects.filter(project=project).select_related(
            'assigned_to', 
            'project'
        )

        context = {
            'project': project,
            'tasks': tasks,
            'can_view_members': True,
            'can_manage': can_manage_project(request.user, project)
        }
        
        return render(request, 'projects/project_detail.html', context)

    except Project.DoesNotExist:
        messages.error(request, "Project not found")
        return redirect('project_list')
        
    except Exception as e:
        logger.error(f"Project detail error: {str(e)}")
        messages.error(request, MSG_ERROR)
        return redirect('project_list')

# Task Views
@login_required
@handle_view_errors
@transaction_handler
def task_create(request, project_id=None):
    """Create a new task, optionally associated with a project"""
    project = None
    try:
        # Get project if project_id is provided
        if project_id:
            project = get_object_or_404(
                Project.objects.select_related('team'), 
                id=project_id
            )
            
            # Check project permissions
            if not has_project_permission(request.user, project):
                messages.error(request, MSG_PERMISSION_DENIED)
                return redirect('project_list')

        if request.method == 'POST':
            # Pass project to form for proper initialization
            form = TaskForm(request.POST, project=project)
            if form.is_valid():
                with transaction.atomic():
                    task = form.save(commit=False)
                    task.created_by = request.user
                    
                    # Set project if provided
                    if project:
                        task.project = project
                    
                    # Set initial status if not provided
                    if not task.status:
                        task.status = 'todo'
                    
                    task.save()
                    
                    # Send notifications
                    assigned_to = form.cleaned_data.get('assigned_to')
                    if assigned_to:
                        assigned_to.notify(
                            f"You have been assigned to task: {task.title}",
                            notification_type='info',
                            action_type='task_assigned',
                            related_object=task
                        )

                    if task.project:
                        task.project.team.owner.notify(
                            f"New task created in {task.project.name} by {request.user.username}",
                            notification_type='info',
                            action_type='task_created',
                            related_object=task
                        )

                    # Success response
                    success_message = 'Task created successfully!'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': success_message,
                            'redirect_url': reverse('task_detail', kwargs={
                                'project_id': task.project.id,
                                'task_id': task.id
                            })
                        })
                        
                    messages.success(request, success_message)
                    return redirect('task_detail', project_id=task.project.id, task_id=task.id)
                    
            elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid form data',
                    'errors': form.errors
                }, status=400)
        else:
            # Initialize form with default values
            initial_data = {
                'project': project,
                'start_date': timezone.now().date(),
                'due_date': (timezone.now() + timezone.timedelta(days=7)).date(),
                'priority': 'medium',
                'status': 'todo'
            }
            form = TaskForm(initial=initial_data, project=project)
        
        context = {
            'form': form,
            'project': project,
            'page_title': 'Create Task',
            'submit_text': 'Create Task'
        }
        
        return render(request, 'projects/task_form.html', context)
        
    except ValidationError as e:
        logger.warning(f"Task creation validation error: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': str(e),
                'errors': form.errors if 'form' in locals() else None
            }, status=400)
        messages.error(request, str(e))
        return redirect('project_list')
        
    except Exception as e:
        logger.error(f"Task creation error: {str(e)}", exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': MSG_ERROR
            }, status=500)
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
    """Display all teams the user is a member of"""
    # Get teams where user is either owner or member
    teams = Team.objects.filter(
        Q(owner=request.user) | Q(members__user=request.user)
    ).prefetch_related(
        'members',
        'projects',
        'projects__tasks'
    ).annotate(
        member_count=Count('members', distinct=True),
        project_count=Count('projects', distinct=True),
        completed_tasks=Count(
            'projects__tasks',
            filter=Q(projects__tasks__status='done'),
            distinct=True,
            output_field=FloatField()
        ),
        total_tasks=Count(
            'projects__tasks', 
            distinct=True,
            output_field=FloatField()
        )
    ).annotate(
        team_progress=Case(
            When(total_tasks=0, then=Value(0.0, output_field=FloatField())),
            default=ExpressionWrapper(
                (F('completed_tasks') / F('total_tasks')) * 100.0,
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    ).distinct()

    return render(request, 'projects/team_list.html', {
        'teams': teams,
        'user_is_owner': Team.objects.filter(owner=request.user).exists(),
        'user_is_manager': request.user.is_project_manager
    })

@login_required
@handle_view_errors
@transaction_handler
def team_form(request, team_id=None):
    """
    Create or update a team.
    
    Args:
        request: HttpRequest object
        team_id: Optional team ID for editing existing team
        
    Returns:
        HttpResponse: Rendered team form or redirect
    """
    try:
        # Get existing team if editing
        team = None if team_id is None else get_object_or_404(
            Team.objects.select_related('owner'), 
            id=team_id
        )
        
        # Check permissions for editing existing team
        if team and not team.can_manage_team(request.user):
            messages.error(request, MSG_PERMISSION_DENIED)
            return redirect('team_list')

        if request.method == 'POST':
            form = TeamForm(
                request.POST,
                request.FILES,
                instance=team
            )
            
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # Save team
                        team = form.save(commit=False)
                        if not team_id:
                            team.owner = request.user
                        team.save()
                        
                        # Create owner membership for new team
                        if not team_id:
                            TeamMember.objects.create(
                                team=team,
                                user=request.user,
                                role='owner',
                                created_by=request.user
                            )
                        
                        # Send notifications
                        if team_id:
                            notify_team_update(team, request.user)
                        else:
                            notify_team_created(team, request.user)

                        # Handle AJAX request
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': True,
                                'message': 'Team saved successfully',
                                'redirect_url': reverse('team_detail', kwargs={'team_id': team.id})
                            })
                            
                        messages.success(request, 'Team saved successfully')
                        return redirect('team_detail', team_id=team.id)
                        
                except ValidationError as e:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'message': str(e)
                        }, status=400)
                    messages.error(request, str(e))
                    
                except Exception as e:
                    logger.error(f"Team save error: {str(e)}", exc_info=True)
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'message': MSG_ERROR
                        }, status=500)
                    messages.error(request, MSG_ERROR)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid form data',
                        'errors': form.errors
                    }, status=400)

        else:
            form = TeamForm(instance=team)

        context = {
            'form': form,
            'team': team,
            'is_edit': team_id is not None,
            'can_manage': request.user.is_project_manager or (team and team.owner == request.user)
        }
        
        return render(request, 'projects/team_form.html', context)

    except Exception as e:
        logger.error(f"Team form error: {str(e)}", exc_info=True)
        messages.error(request, MSG_ERROR)
        return redirect('team_list')

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
def team_detail(request, team_id):
    """Display team details with member management and statistics"""
    try:
        # Get team with optimized related data loading
        team = get_object_or_404(
            Team.objects.select_related(
                'owner',
                'owner__profile'
            ).prefetch_related(
                'members__user__profile',
                'members__user__assigned_tasks',
                'projects',
                'projects__tasks',
                'projects__manager'
            ),
            id=team_id
        )
        
        # Check permissions using utility function
        if not has_team_permission(request.user, team):
            messages.error(request, MSG_PERMISSION_DENIED)
            return redirect('team_list')

        # Get role-based permissions
        is_member = TeamMember.objects.filter(team=team, user=request.user).exists()
        is_manager = request.user.is_project_manager
        is_owner = request.user == team.owner
        
        # Get team statistics using utility function
        team_stats = get_team_stats(team)
        
        # Get members with detailed statistics
        members = TeamMember.objects.filter(
            team=team
        ).select_related(
            'user',
            'user__profile'
        ).prefetch_related(
            'user__assigned_tasks'
        ).annotate(
            task_count=Count('user__assigned_tasks', distinct=True),
            completed_tasks=Count(
                'user__assigned_tasks',
                filter=Q(user__assigned_tasks__status='done'),
                distinct=True
            ),
            completion_rate=Case(
                When(task_count=0, then=Value(0.0, output_field=FloatField())),
                default=ExpressionWrapper(
                    F('completed_tasks') * 100.0 / F('task_count'),
                    output_field=FloatField()
                )
            ),
            last_active=Max('user__assigned_tasks__updated_at')
        ).order_by('-role', 'user__username')

        context = {
            'team': team,
            'members': members,
            'total_tasks': team_stats['total_tasks'],
            'completed_tasks': team_stats['completed_tasks'],
            'active_projects': team_stats['active_projects'],
            'completed_projects': team_stats['completed_projects'],
            'team_progress': team_stats['progress'],
            'can_manage': can_manage_team(request.user, team),
            'available_roles': TeamMember.ROLE_CHOICES,
            'is_member': is_member,
            'is_manager': is_manager,
            'is_owner': is_owner
        }
        
        return render(request, 'projects/team_detail.html', context)

    except Team.DoesNotExist:
        messages.error(request, "Team not found")
        return redirect('team_list')
    except PermissionDenied:
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('team_list')
    except Exception as e:
        logger.error(f"Team detail error: {str(e)}", exc_info=True)
        messages.error(request, MSG_ERROR)
        return redirect('team_list')

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
@cache_page(60 * 15)  # Cache for 15 minutes
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
            'stats': [
                {
                    'title': 'Total Projects',
                    'value': Project.objects.count(),
                    'icon': 'folder-fill',
                    'color': 'primary'
                },
                {
                    'title': 'Active Tasks',
                    'value': Task.objects.exclude(status='done').count(),
                    'icon': 'list-check',
                    'color': 'success'
                },
                {
                    'title': 'Team Members',
                    'value': User.objects.filter(is_active=True).count(),
                    'icon': 'people-fill',
                    'color': 'info'
                },
                {
                    'title': 'Completion Rate',
                    'value': f"{calculate_completion_rate(request.user)}%",
                    'icon': 'graph-up',
                    'color': 'warning'
                }
            ]
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
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    try:
        with transaction.atomic():
            task = Task.objects.select_related(
                'project', 'assigned_to'
            ).select_for_update().get(id=task_id)
            
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
            
            old_status = task.status
            task.status = new_status
            task.last_active = timezone.now()
            
            if new_status == TASK_STATUS_DONE:
                task.completed_at = timezone.now()
            elif old_status == TASK_STATUS_DONE:
                task.completed_at = None
                
            task.save()
            
            # Send notification using notify() method
            task.assigned_to.notify(
                f"Task '{task.title}' status changed to {task.get_status_display()}",
                notification_type='info',
                action_type='task_status_changed',
                related_object=task
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Task status updated successfully',
                'task': {
                    'id': task.id,
                    'status': task.status,
                    'completion_rate': calculate_completion_rate(request.user)
                }
            })

    except Task.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Task not found'
        }, status=404)
        
    except Exception as e:
        logger.error(f"Task status update error: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': str(e)
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
def update_profile(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get form data
                first_name = request.POST.get('first_name', '')
                last_name = request.POST.get('last_name', '')
                email = request.POST.get('email', '')
                bio = request.POST.get('bio', '')

                # Update user
                user = request.user
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()

                # Update profile
                profile = user.profile
                profile.bio = bio
                
                # Handle profile picture upload
                if 'profile_picture' in request.FILES:
                    # Delete old profile picture if it exists
                    if profile.profile_picture:
                        profile.profile_picture.delete(save=False)
                    profile.profile_picture = request.FILES['profile_picture']
                
                profile.save()

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Profile updated successfully',
                        'profile_picture_url': profile.profile_picture.url if profile.profile_picture else None
                    })

                messages.success(request, 'Profile updated successfully')
                return redirect('settings')

        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=500)
            messages.error(request, 'Failed to update profile')
            return redirect('settings')

    return render(request, 'settings/settings.html')

@login_required
@handle_view_errors
@transaction_handler
def remove_avatar(request):
    """Remove user profile picture"""
    if request.method == 'POST':
        try:
            profile = request.user.profile
            if profile.profile_picture:
                profile.profile_picture.delete()  # This will delete the file
                profile.profile_picture = None    # Set the field to None
                profile.save()

            return JsonResponse({
                'success': True,
                'message': 'Profile picture removed successfully',
                'initial': request.user.username[0].upper()
            })
        except Exception as e:
            logger.error(f"Avatar removal error: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Failed to remove profile picture'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=400)

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
def change_password(request):
    if request.method == 'POST':
        try:
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if not request.user.check_password(old_password):
                return JsonResponse({
                    'success': False,
                    'message': 'Current password is incorrect'
                }, status=400)

            if new_password1 != new_password2:
                return JsonResponse({
                    'success': False,
                    'message': 'New passwords do not match'
                }, status=400)

            # Set the new password
            request.user.set_password(new_password1)
            request.user.save()

            # Update session to prevent logout
            update_session_auth_hash(request, request.user)

            return JsonResponse({
                'success': True,
                'message': 'Password updated successfully'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=400)

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
def manage_team_members(request, team_id, team=None):
    """
    View for managing team members - adding, removing, and updating roles.
    Only project managers or team owners can manage team members.
    """
    if not team:
        team = get_object_or_404(
            Team.objects.select_related(
                'owner',
                'owner__profile'
            ), 
            id=team_id
        )
    
    if not team.can_manage_team(request.user):
        messages.error(request, "You don't have permission to manage team members")
        return redirect('team_detail', team_id=team_id)

    try:
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'remove':
                member_id = request.POST.get('member_id')
                try:
                    member = TeamMember.objects.get(id=member_id, team=team)
                    if member.user == team.owner:
                        raise ValidationError("Cannot remove team owner")
                    
                    username = member.user.username
                    team.remove_member(member.user)
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': f"Removed {username} from team"
                        })
                    messages.success(request, f"Removed {username} from team")
                except (TeamMember.DoesNotExist, ValidationError) as e:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'message': str(e)
                        }, status=400)
                    messages.error(request, str(e))
                    
            elif action == 'update_role':
                member_id = request.POST.get('member_id')
                new_role = request.POST.get('role')
                
                try:
                    member = TeamMember.objects.get(id=member_id, team=team)
                    if member.user == team.owner:
                        raise ValidationError("Cannot change team owner's role")
                        
                    old_role = member.get_role_display()
                    member.role = new_role
                    member.save()
                    
                    # Notify member of role change
                    member.user.notify(
                        f"Your role in {team.name} has been changed to {member.get_role_display()}",
                        notification_type='info',
                        action_type='role_changed'
                    )
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': f"Updated role to {member.get_role_display()}"
                        })
                    messages.success(request, f"Updated {member.user.username}'s role to {member.get_role_display()}")
                except (TeamMember.DoesNotExist, ValidationError) as e:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'message': str(e)
                        }, status=400)
                    messages.error(request, str(e))

            return redirect('manage_team_members', team_id=team_id)

        # Get team members with statistics
        members = TeamMember.objects.filter(team=team).select_related(
            'user',
            'user__profile'
        ).annotate(
            task_count=Count('user__assigned_tasks', distinct=True),
            completed_tasks=Count(
                'user__assigned_tasks',
                filter=Q(user__assigned_tasks__status='done'),
                distinct=True
            ),
            completion_rate=Case(
                When(task_count=0, then=Value(0.0)),
                default=ExpressionWrapper(
                    F('completed_tasks') * 100.0 / F('task_count'),
                    output_field=FloatField()
                )
            ),
            last_active=Max('user__assigned_tasks__updated_at')
        ).order_by('-role', 'user__username')

        context = {
            'team': team,
            'members': members,
            'can_manage': team.can_manage_team(request.user),
            'available_roles': TeamMember.ROLE_CHOICES,
            'user_is_owner': request.user == team.owner,
            'user_is_manager': request.user.is_project_manager
        }
        
        return render(request, 'projects/manage_team_members.html', context)

    except Exception as e:
        logger.error(f"Team member management error: {str(e)}", exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': MSG_ERROR
            }, status=500)
        messages.error(request, MSG_ERROR)
        return redirect('team_detail', team_id=team_id)

@login_required
@handle_view_errors
@transaction_handler
def remove_team_member(request, team_id, member_id):
    """Remove a member from the team"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': MSG_INVALID_REQUEST
        }, status=400)

    try:
        with transaction.atomic():
            team = Team.objects.select_related('owner').get(id=team_id)
            
            if not team.can_manage_team(request.user):
                return JsonResponse({
                    'success': False,
                    'message': MSG_PERMISSION_DENIED
                }, status=403)

            member = TeamMember.objects.select_related('user').get(id=member_id, team=team)
            if member.user == team.owner:
                raise ValidationError("Cannot remove team owner")

            user = member.user
            reason = request.POST.get('reason')
            notify = request.POST.get('notify_member') == 'on'

            # Handle all database operations in a single transaction
            Task.objects.filter(
                assigned_to=user,
                project__team=team
            ).update(
                assigned_to=None,
                status='unassigned',
                updated_at=timezone.now()
            )

            # Remove member
            member.delete()

            # Send notifications outside of transaction
            transaction.on_commit(lambda: send_notifications(user, team, notify, reason))

            return JsonResponse({
                'success': True,
                'message': f"Removed {user.username} from team"
            })

    except TeamMember.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': "Member not found"
        }, status=404)
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error removing team member: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': "An error occurred while removing the member"
        }, status=500)

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

@login_required 
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
                Cast('id', output_field=FloatField()) * 100.0 / 
                Cast('project', output_field=FloatField()),
                output_field=FloatField()
            ))
            .values('rate')[:1]
        )
    ).distinct()
    
    context = {
        'teams': teams,
        'user_is_staff': request.user.is_staff,
        'available_roles': TeamMember.ROLE_CHOICES
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
            try:
                project = form.save()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Project updated successfully',
                        'redirect_url': reverse('project_detail', kwargs={'project_id': project.id})
                    })
                messages.success(request, 'Project updated successfully!')
                return redirect('project_detail', project_id=project.id)
            except Exception as e:
                logger.error(f"Project update error: {str(e)}", exc_info=True)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Error updating project',
                        'errors': form.errors
                    }, status=400)
                messages.error(request, 'Error updating project')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the errors below',
                    'errors': form.errors
                }, status=400)
    else:
        form = ProjectForm(instance=project)
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'project': project
    })

@login_required
@handle_view_errors
@transaction_handler
def project_delete(request, project_id):
    """Delete project view with proper error handling"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

    try:
        with transaction.atomic():
            # Get project with all related data
            project = Project.objects.select_related(
                'team', 'manager'
            ).prefetch_related(
                'tasks',
                'tasks__files'
            ).filter(id=project_id).first()
            
            if not project:
                return JsonResponse({
                    'success': False,
                    'message': 'Project not found',
                    'redirect_url': reverse('project_list')
                }, status=404)
            
            if not has_project_permission(request.user, project):
                return JsonResponse({
                    'success': False, 
                    'message': MSG_PERMISSION_DENIED
                }, status=403)

            project_name = project.name

            # Delete files first to prevent integrity errors
            for task in project.tasks.all():
                for file in task.files.all():
                    try:
                        file.file.delete()  # Delete physical file
                        file.delete()       # Delete file record
                    except Exception as e:
                        logger.warning(f"Error deleting file {file.id}: {str(e)}")
                        continue

            # Delete tasks
            project.tasks.all().delete()
            
            # Finally delete the project
            project.delete()

            return JsonResponse({
                'success': True,
                'message': f'Project "{project_name}" deleted successfully',
                'redirect_url': reverse('project_list')
            })

    except (OperationalError, ProgrammingError) as e:
        logger.error(f"Database error during project deletion: {str(e)}")
        connection.close()
        return JsonResponse({
            'success': False,
            'message': 'Database error occurred. Please try again.'
        }, status=500)
        
    except Exception as e:
        logger.error(f"Project deletion error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while deleting the project.'
        }, status=500)

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
            with transaction.atomic():
                form = FileForm(request.POST, request.FILES)
                if form.is_valid():
                    file = form.save(commit=False)
                    file.uploaded_by = request.user
                    file.save()
                    
                    # Create notification
                    send_notification(
                        user=project.manager,
                        message=f'New file uploaded to project {project.name}',
                        related_object=file
                    )
                    
                    messages.success(request, 'File uploaded successfully!')
                    return redirect('project_files', project_id=project_id)
                else:
                    for error in form.errors.values():
                        messages.error(request, error)
                        
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
            if 'profile_picture' not in request.FILES:
                raise ValueError("No image file provided")

            image = request.FILES['profile_picture']
            
            # Validate file size (2MB limit)
            if image.size > 2 * 1024 * 1024:
                raise ValueError("Image file too large (max 2MB)")

            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if image.content_type not in allowed_types:
                raise ValueError("Invalid image format")

            profile = request.user.profile
            
            # Delete old avatar if exists
            if profile.profile_picture:
                profile.profile_picture.delete(save=False)
                
            profile.profile_picture = image
            profile.save()

            return JsonResponse({
                'success': True,
                'message': 'Profile picture updated successfully',
                'avatar_url': profile.profile_picture.url
            })
            
        except Exception as e:
            logger.error(f"Avatar update error: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
            
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=405)

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

@login_required
@handle_view_errors
@team_manager_required
def create_team_member(request, team_id, team=None):
    """Create a new team member"""
    if not team:
        team = get_object_or_404(
            Team.objects.select_related('owner'), 
            id=team_id
        )
    
    if not team.can_create_team_members(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': "Only team managers or owners can create team members"
            }, status=403)
        messages.error(request, "Only team managers or owners can create team members")
        return redirect('team_detail', team_id=team_id)

    try:
        if request.method == 'POST':
            form = CustomTeamMemberCreationForm(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    member = form.save(commit=True, team=team, created_by=request.user)
                    
                    success_message = f'Successfully created account for {member.user.username}'
                    messages.success(request, success_message)
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': success_message,
                            'redirect_url': reverse('manage_team_members', args=[team_id])
                        })
                    return redirect('manage_team_members', team_id=team_id)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the form errors',
                    'errors': form.errors
                }, status=400)
        else:
            form = CustomTeamMemberCreationForm()
        
        return render(request, 'projects/create_team_member.html', {
            'form': form,
            'team': team
        })
            
    except ValidationError as e:
        error_message = str(e)
        logger.error(f"Team member creation validation error: {error_message}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_message
            }, status=400)
        messages.error(request, error_message)
        return redirect('manage_team_members', team_id=team_id)
        
    except IntegrityError as e:
        error_message = "A user with this username or email already exists"
        logger.error(f"Team member creation integrity error: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_message
            }, status=400)
        messages.error(request, error_message)
        return redirect('manage_team_members', team_id=team_id)
        
    except Exception as e:
        logger.error(f"Team member creation error: {str(e)}", exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': "An error occurred while creating the team member"
            }, status=500)
        messages.error(request, MSG_ERROR)
        return redirect('manage_team_members', team_id=team_id)

@login_required
@handle_view_errors
@transaction_handler
def add_team_member(request, team_id):
    """Add a new member to the team"""
    team = get_object_or_404(Team, id=team_id)
    
    if not team.can_manage_team(request.user):
        messages.error(request, MSG_PERMISSION_DENIED)
        return redirect('team_detail', team_id=team_id)

    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            role = request.POST.get('role', 'member')
            user = User.objects.get(email=email)

            member = team.add_member(
                user=user,
                role=role,
                created_by=request.user
            )

            messages.success(request, f"{user.username} added to team successfully")
            return JsonResponse({'success': True, 'message': 'Member added successfully'})

        except User.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': "User with this email does not exist"
            }, status=400)
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

    return redirect('manage_team_members', team_id=team_id)

@login_required
@handle_view_errors
@team_manager_required
def update_member_role(request, team_id, member_id, team=None):
    """Update a team member's role"""
    if not team:
        team = get_object_or_404(Team, id=team_id)
    
    if not team.can_manage_team(request.user):
        return JsonResponse({
            'success': False,
            'message': MSG_PERMISSION_DENIED
        }, status=403)

    if request.method == 'POST':
        try:
            new_role = request.POST.get('role')
            member = TeamMember.objects.get(id=member_id, team=team)
            
            if member.user == team.owner:
                raise ValidationError("Cannot change team owner's role")
                
            member.role = new_role
            member.save()  # This will trigger the notification in the model's save method
            
            return JsonResponse({
                'success': True,
                'message': f"Updated role to {member.get_role_display()}"
            })
        except (TeamMember.DoesNotExist, ValidationError) as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'success': False,
        'message': MSG_INVALID_REQUEST
    }, status=400)

@login_required
@handle_view_errors
@transaction_handler
def remove_team_member(request, team_id, member_id):
    """Remove a member from the team"""
    team = get_object_or_404(Team, id=team_id)
    
    if not team.can_manage_team(request.user):
        return JsonResponse({
            'success': False,
            'message': MSG_PERMISSION_DENIED
        }, status=403)

    if request.method == 'POST':
        try:
            member = TeamMember.objects.get(id=member_id, team=team)
            if member.user == team.owner:
                raise ValidationError("Cannot remove team owner")

            user = member.user
            team.remove_member(user)
            
            if request.POST.get('notify_member') == 'on':
                send_team_removal_email(user, team, request.POST.get('reason'))
            
            return JsonResponse({
                'success': True,
                'message': f"Removed {user.username} from team"
            })

        except (TeamMember.DoesNotExist, ValidationError) as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'success': False,
        'message': MSG_INVALID_REQUEST
    }, status=400)

@login_required
@handle_view_errors
def get_project_team_members(request, project_id):
    try:
        # Get project with optimized query
        project = get_object_or_404(
            Project.objects.select_related('team', 'team__owner'),
            id=project_id
        )
        
        # Permission check hierarchy:
        if not (
            # 1. Has general project permission through TeamMember role
            has_project_permission(request.user, project) or 
            # 2. Is the team owner explicitly 
            request.user == project.team.owner or
            # 3. Is a project manager (global permission)
            request.user.is_project_manager
        ):
            return JsonResponse({
                'error': 'Permission denied'
            }, status=403)
            
        # If permission check passes, get all active team members
        members = TeamMember.objects.filter(
            team=project.team,
            user__is_active=True
        ).select_related('user')
        
        return JsonResponse({
            'members': [{
                'id': member.user.id,
                'name': member.user.get_full_name() or member.username
            } for member in members]
        })
        
    except Exception as e:
        logger.error(f"Error fetching team members: {str(e)}")
        return JsonResponse({
            'error': str(e)
        }, status=500)