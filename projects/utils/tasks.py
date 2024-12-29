from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import logging
from ..models import Task
from .constants import TASK_STATUS_DONE

# Initialize logger
logger = logging.getLogger(__name__)

def get_user_tasks(user):
    """Get all tasks for a user with optimized queries"""
    try:
        return (Task.objects.filter(assigned_to=user)
                .select_related('project')
                .order_by('-created_at'))
    except Exception as e:
        logger.error(f"Error getting user tasks: {str(e)}")
        return Task.objects.none()

def calculate_completion_rate(user):
    """Calculate task completion rate for user"""
    try:
        total_tasks = Task.objects.filter(assigned_to=user).count()
        completed_tasks = Task.objects.filter(
            assigned_to=user, 
            status=TASK_STATUS_DONE
        ).count()
        return round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0)
    except Exception as e:
        logger.error(f"Error calculating completion rate: {str(e)}")
        return 0

def get_recent_activity(user, days=7):
    """Get recent task activity for user"""
    try:
        start_date = timezone.now() - timedelta(days=days)
        return Task.objects.filter(
            assigned_to=user,
            created_at__gte=start_date
        ).select_related('project').order_by('-created_at')
    except Exception as e:
        logger.error(f"Error getting recent activity: {str(e)}")
        return Task.objects.none()