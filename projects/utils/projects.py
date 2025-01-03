from django.utils import timezone
from django.db.models import Q, Prefetch, Count
from django.template.defaulttags import register
from ..models import Project, TeamMember, Task

def get_user_projects(user):
    """Get all projects accessible to user"""
    if user.is_superuser:
        # Superusers see all projects
        return Project.objects.all()
    
    query = Q(team__members__user=user)  # Projects where user is team member
    
    if user.is_project_manager:
        query |= Q(manager=user)  # Add projects managed by user
        
    # Add projects where user is assigned tasks
    query |= Q(tasks__assigned_to=user)
        
    return Project.objects.filter(query).distinct().select_related(
        'team',
        'manager'
    ).prefetch_related(
        Prefetch('tasks', queryset=Task.objects.select_related('assigned_to')),
        'team__members__user',
    ).order_by('-created_at')

def get_managed_projects(user):
    """Get projects where user is manager"""
    return Project.objects.filter(
        Q(manager=user) |  # Projects directly managed
        Q(team__members__user=user, team__members__role__in=['owner', 'manager'])  # Projects in teams where user is owner/manager
    ).distinct().select_related(
        'team',
        'manager'
    ).prefetch_related(
        Prefetch('tasks', queryset=Task.objects.select_related('assigned_to')),
        'team__members__user'
    ).order_by('-created_at')

def get_team_projects(user):
    """Get projects where user is team member but not manager"""
    return Project.objects.filter(
        team__members__user=user
    ).exclude(
        Q(manager=user) |
        Q(team__members__user=user, team__members__role__in=['owner', 'manager'])
    ).distinct().select_related(
        'team',
        'manager'
    ).prefetch_related(
        Prefetch('tasks', queryset=Task.objects.select_related('assigned_to')),
        'team__members__user'
    ).order_by('-created_at')

def get_assigned_projects(user):
    """Get projects where user has assigned tasks"""
    return Project.objects.filter(
        tasks__assigned_to=user
    ).exclude(
        Q(manager=user) |
        Q(team__members__user=user)
    ).distinct().select_related(
        'team',
        'manager'
    ).prefetch_related(
        Prefetch('tasks', queryset=Task.objects.select_related('assigned_to')),
        'team__members__user'
    ).order_by('-created_at')

@register.filter
def completed_projects_count(projects):
    """Count completed projects"""
    if not projects:
        return 0
    # Handle both QuerySet and related manager
    if hasattr(projects, 'all'):
        projects = projects.all()
    return projects.filter(status='completed').count()

@register.filter 
def active_projects_count(projects):
    """Count active projects"""
    if not projects:
        return 0
    # Handle both QuerySet and related manager
    if hasattr(projects, 'all'):
        projects = projects.all()
    return projects.filter(
        Q(status='active') | Q(status='planned')
    ).count()

@register.filter
def calculate_completion_rate(projects):
    """Calculate completion rate for projects"""
    if not projects:
        return 0
    
    # Handle both QuerySet and related manager
    if hasattr(projects, 'all'):
        projects = projects.all()
        
    total = projects.count()
    if total == 0:
        return 0
        
    completed = projects.filter(status='completed').count()
    return round((completed / total) * 100)

@register.filter
def get_project_progress(project):
    """Calculate progress for a single project"""
    if not project or not project.tasks.exists():
        return 0
        
    total_tasks = project.tasks.count()
    completed_tasks = project.tasks.filter(status='done').count()
    
    return round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0