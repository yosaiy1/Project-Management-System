from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import logging
from ..models import Project, Task, Notification, TeamMember  # Add TeamMember here
from .projects import get_user_projects
from .tasks import get_user_tasks
from .constants import TASK_STATUS_TODO, TASK_STATUS_IN_PROGRESS

# Initialize logger
logger = logging.getLogger(__name__)

def get_common_context(user):
    try:
        notifications = Notification.objects.filter(user=user).select_related('user')
        return {
            'projects_count': Project.objects.filter(team__members__user=user).distinct().count(),
            'tasks_count': Task.objects.filter(assigned_to=user).count(),
            'notifications': notifications[:5],
            'unread_notifications_count': notifications.filter(read=False).count(),
            'team_members_count': TeamMember.objects.filter(team__members__user=user).distinct().count(),
            'active_projects_count': Project.objects.filter(team__members__user=user, status='active').distinct().count(),
            'completed_tasks_count': Task.objects.filter(assigned_to=user, status='done').count()
        }
    except Exception as e:
        logger.error(f"Context error: {str(e)}")
        return {}