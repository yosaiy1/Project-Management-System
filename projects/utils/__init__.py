from django.utils import timezone
from django.db.models import Q
from datetime import timedelta, date
import logging
from ..models import Project, Task, Team, TeamMember, Notification  # Changed from .models to ..models

# Initialize logger
logger = logging.getLogger(__name__)

def get_user_projects(user):
    """Get all projects accessible to user"""
    return Project.objects.filter(
        Q(team__members__user=user) |  # Projects where user is team member
        Q(team__owner=user) |          # Projects owned by user
        Q(manager=user) |              # Projects managed by user
        Q(tasks__assigned_to=user)     # Projects with tasks assigned to user
    ).distinct().select_related(
        'team',
        'manager'
    ).prefetch_related(
        'team__members',
        'tasks'
    )

def get_user_tasks(user):
    """Get all tasks for a user with optimized queries"""
    return (Task.objects.filter(assigned_to=user)
            .select_related('project')
            .order_by('-created_at'))

def get_common_context(user):
    """Get common context data for templates"""
    if not user.is_authenticated:
        return {}
        
    try:
        notifications = (Notification.objects.filter(user=user)
                      .select_related('user')
                      .order_by('-created_at'))
        
        return {
            'projects_count': Project.objects.filter(
                team__members__user=user
            ).distinct().count(),
            'tasks_count': Task.objects.filter(
                assigned_to=user,
                status__in=['todo', 'inprogress']
            ).count(),
            'notifications': notifications[:5],
            'unread_notifications_count': notifications.filter(read=False).count(),
        }
    except Exception as e:
        logger.error(f"Context error: {str(e)}")
        return {}