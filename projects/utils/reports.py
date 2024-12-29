from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import logging
from ..models import Project, Task, Team
from .constants import TASK_STATUS_DONE

# Initialize logger
logger = logging.getLogger(__name__)

def generate_report(user, start_date, end_date, report_type):
    """Generate report based on type and date range"""
    try:
        if report_type == 'tasks':
            return generate_tasks_report(user, start_date, end_date)
        elif report_type == 'projects':
            return generate_projects_report(user, start_date, end_date)
        elif report_type == 'team':
            return generate_team_report(user, start_date, end_date)
        return None
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return None

def generate_tasks_report(user, start_date, end_date):
    """Generate tasks report"""
    try:
        tasks = Task.objects.filter(
            assigned_to=user,
            created_at__range=[start_date, end_date]
        ).select_related('project')
        
        return {
            'report_type': 'tasks',
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(status=TASK_STATUS_DONE).count(),
            'pending_tasks': tasks.exclude(status=TASK_STATUS_DONE).count(),
            'tasks': tasks
        }
    except Exception as e:
        logger.error(f"Error generating tasks report: {e}")
        return None

def generate_projects_report(user, start_date, end_date):
    """Generate projects report"""
    try:
        projects = Project.objects.filter(
            Q(manager=user) | Q(team__members__user=user),
            created_at__range=[start_date, end_date]
        ).distinct().select_related('team')
        
        return {
            'report_type': 'projects',
            'total_projects': projects.count(),
            'active_projects': projects.filter(status='active').count(),
            'completed_projects': projects.filter(status='completed').count(),
            'projects': projects
        }
    except Exception as e:
        logger.error(f"Error generating projects report: {e}")
        return None

def generate_team_report(user, start_date, end_date):
    """Generate team performance report"""
    try:
        teams = Team.objects.filter(
            members__user=user
        ).distinct().prefetch_related('projects__tasks')
        
        team_data = []
        for team in teams:
            tasks = Task.objects.filter(
                project__team=team,
                created_at__range=[start_date, end_date]
            )
            team_data.append({
                'team': team,
                'total_tasks': tasks.count(),
                'completed_tasks': tasks.filter(status=TASK_STATUS_DONE).count(),
                'completion_rate': calculate_completion_rate(tasks)
            })
        
        return {
            'report_type': 'team',
            'teams': team_data
        }
    except Exception as e:
        logger.error(f"Error generating team report: {e}")
        return None

def calculate_completion_rate(tasks):
    """Calculate completion rate for tasks"""
    try:
        total = tasks.count()
        if total == 0:
            return 0
        completed = tasks.filter(status=TASK_STATUS_DONE).count()
        return round((completed / total) * 100, 1)
    except Exception as e:
        logger.error(f"Error calculating completion rate: {e}")
        return 0