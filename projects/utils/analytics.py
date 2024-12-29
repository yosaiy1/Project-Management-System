from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import logging
from ..models import Task, Team
from .constants import TASK_STATUS_TODO, TASK_STATUS_IN_PROGRESS, TASK_STATUS_DONE

# Initialize logger
logger = logging.getLogger(__name__)

def get_timeline_labels(time_range=7):
    """Get timeline labels for last N days"""
    try:
        today = timezone.now()
        return [(today - timedelta(days=x)).strftime('%b %d') 
                for x in range(time_range-1, -1, -1)]
    except Exception as e:
        logger.error(f"Error getting timeline labels: {e}")
        return []

def get_completed_tasks_data(user, time_range=7):
    """Get completed tasks data with time range parameter"""
    try:
        tasks = Task.objects.filter(
            assigned_to=user,
            status=TASK_STATUS_DONE
        ).select_related('project')
        
        data = []
        for x in range(time_range-1, -1, -1):
            date = timezone.now() - timedelta(days=x)
            count = tasks.filter(completed_at__date=date.date()).count()
            data.append(count)
            
        return data
    except Exception as e:
        logger.error(f"Error getting completed tasks data: {e}")
        return [0] * time_range

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

def get_completion_trend(user, time_range=7):
    """Get task completion trend for the specified time range"""
    try:
        tasks = Task.objects.filter(assigned_to=user)
        trend_data = []
        
        for x in range(time_range-1, -1, -1):
            date = timezone.now() - timedelta(days=x)
            total = tasks.filter(created_at__date=date.date()).count()
            completed = tasks.filter(
                status=TASK_STATUS_DONE,
                completed_at__date=date.date()
            ).count()
            
            percentage = (completed / total * 100) if total > 0 else 0
            trend_data.append(round(percentage, 1))
            
        return trend_data
    except Exception as e:
        logger.error(f"Error getting completion trend: {e}")
        return [0] * time_range