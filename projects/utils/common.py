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

def get_common_context(request):
    """Get common context data for all views"""
    if request.user.is_authenticated:
        projects = Project.objects.filter(
            Q(team__members__user=request.user) |  # Projects where user is team member
            Q(team__owner=request.user) |          # Projects owned by user 
            Q(manager=request.user) |              # Projects managed by user
            Q(tasks__assigned_to=request.user)     # Projects with tasks assigned
        ).distinct().select_related(
            'team',
            'manager'
        ).prefetch_related(
            'team__members',
            'tasks'
        )

        return {
            'user_projects': projects,
            'projects_count': projects.count(),
            'active_projects': projects.filter(status='active'),
            'active_projects_count': projects.filter(status='active').count(),
            'notifications': Notification.objects.filter(user=request.user)[:5],
            'unread_notifications_count': Notification.objects.filter(
                user=request.user, 
                read=False
            ).count()
        }
    return {}