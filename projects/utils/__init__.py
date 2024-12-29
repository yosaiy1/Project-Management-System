from django.utils import timezone
from django.db.models import Q
from datetime import timedelta, date
import logging
from ..models import Project, Task, Team, TeamMember, Notification  # Changed from .models to ..models

# Initialize logger
logger = logging.getLogger(__name__)

def get_user_projects(user):
    """Get all projects for a user with optimized queries"""
    return (Project.objects.filter(team__members__user=user)
            .select_related('team')
            .distinct()
            .order_by('-date_created'))

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