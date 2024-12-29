from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import logging
from ..models import Task, Team
from .constants import TASK_STATUS_TODO, TASK_STATUS_IN_PROGRESS, TASK_STATUS_DONE

# Initialize logger
logger = logging.getLogger(__name__)

def get_timeline_labels():
    """Return last 7 days formatted labels"""
    try:
        return [
            (timezone.now() - timedelta(days=x)).strftime('%b %d') 
            for x in range(6, -1, -1)
        ]
    except Exception as e:
        logger.error(f"Error generating timeline labels: {e}")
        return []

def get_completed_tasks_data(user):
    """Return completed tasks count for last 7 days"""
    try:
        tasks = Task.objects.filter(
            assigned_to=user,
            status=TASK_STATUS_DONE
        ).select_related('project')

        return [
            tasks.filter(
                completed_at__date=timezone.now().date() - timedelta(days=x)
            ).count() 
            for x in range(6, -1, -1)
        ]
    except Exception as e:
        logger.error(f"Error getting completed tasks data: {e}")
        return [0] * 7

def get_task_distribution(user):
    """Get task counts by status"""
    try:
        tasks = Task.objects.filter(assigned_to=user)
        distribution = tasks.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        status_counts = {
            TASK_STATUS_TODO: 0,
            TASK_STATUS_IN_PROGRESS: 0,
            TASK_STATUS_DONE: 0
        }
        
        for item in distribution:
            status_counts[item['status']] = item['count']
        
        return [
            status_counts[TASK_STATUS_TODO],
            status_counts[TASK_STATUS_IN_PROGRESS],
            status_counts[TASK_STATUS_DONE]
        ]
    except Exception as e:
        logger.error(f"Error getting task distribution: {e}")
        return [0, 0, 0]

def get_team_labels(user):
    """Get list of team names"""
    try:
        return list(Team.objects.filter(
            members__user=user
        ).values_list('name', flat=True))
    except Exception as e:
        logger.error(f"Error getting team labels: {e}")
        return []

def get_team_performance(user):
    """Get completed tasks count per team"""
    try:
        teams = Team.objects.filter(
            members__user=user
        ).prefetch_related('projects__tasks')
        
        return [
            Task.objects.filter(
                project__team=team,
                status=TASK_STATUS_DONE
            ).count()
            for team in teams
        ]
    except Exception as e:
        logger.error(f"Error getting team performance: {e}")
        return []

def calculate_completion_rate(user):
    """Calculate task completion rate for user"""
    try:
        total_tasks = Task.objects.filter(assigned_to=user).count()
        if not total_tasks:
            return 0
            
        completed_tasks = Task.objects.filter(
            assigned_to=user,
            status=TASK_STATUS_DONE
        ).count()
        
        return round((completed_tasks / total_tasks) * 100)
    except Exception as e:
        logger.error(f"Error calculating completion rate: {e}")
        return 0

def get_completion_trend(user):
    """Get task completion trend over 4 weeks"""
    try:
        trend_data = []
        now = timezone.now()
        
        for week in range(4):
            start_date = now - timedelta(weeks=week+1)
            end_date = now - timedelta(weeks=week)
            
            completed = Task.objects.filter(
                assigned_to=user,
                status=TASK_STATUS_DONE,
                completed_at__range=[start_date, end_date]
            ).count()
            trend_data.append(completed)
        
        return trend_data[::-1]  # Reverse to show oldest to newest
    except Exception as e:
        logger.error(f"Error getting completion trend: {e}")
        return [0] * 4

def get_trend_labels():
    """Get week labels for trends"""
    return ['Week 1', 'Week 2', 'Week 3', 'Week 4']