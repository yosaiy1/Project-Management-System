from django.utils import timezone
from django.db.models import Q, Count, F
from django.core.exceptions import ValidationError
from datetime import timedelta
import logging
from ..models import Task, Project, TeamMember

logger = logging.getLogger(__name__)

def get_user_tasks(user):
    """Get all tasks for a user with optimized queries"""
    try:
        if user.is_project_manager:
            # Project managers see tasks they created or are assigned to
            return Task.objects.filter(
                Q(created_by=user) |
                Q(assigned_to=user) |
                Q(project__team__members__user=user, project__team__members__role__in=['owner', 'manager'])
            ).select_related(
                'project',
                'project__team',
                'assigned_to',
                'created_by'
            ).distinct().order_by('-created_at')
        else:
            # Regular users only see assigned tasks
            return Task.objects.filter(
                assigned_to=user
            ).select_related(
                'project',
                'project__team',
                'assigned_to',
                'created_by'
            ).order_by('-created_at')
    except Exception as e:
        logger.error(f"Error getting user tasks: {str(e)}")
        return Task.objects.none()

def get_project_tasks(project, user):
    """Get tasks for a specific project based on user role"""
    try:
        member = TeamMember.objects.get(team=project.team, user=user)
        
        if member.role in ['owner', 'manager'] or user == project.manager:
            # Full access to project managers and team owners/managers
            return Task.objects.filter(
                project=project
            ).select_related(
                'assigned_to',
                'created_by'
            ).order_by('-created_at')
        else:
            # Regular members only see their assigned tasks
            return Task.objects.filter(
                project=project,
                assigned_to=user
            ).select_related(
                'assigned_to',
                'created_by'
            ).order_by('-created_at')
    except TeamMember.DoesNotExist:
        # No team membership
        return Task.objects.none()
    except Exception as e:
        logger.error(f"Error getting project tasks: {str(e)}")
        return Task.objects.none()

def calculate_completion_rate(user):
    """Calculate task completion rate for user"""
    try:
        tasks = Task.objects.filter(assigned_to=user)
        total = tasks.count()
        if not total:
            return 0
        completed = tasks.filter(status='done').count()
        return round((completed / total) * 100, 1)
    except Exception as e:
        logger.error(f"Error calculating completion rate: {str(e)}")
        return 0

def get_recent_activity(user, days=7):
    """Get recent task activity for user"""
    try:
        start_date = timezone.now() - timedelta(days=days)
        
        if user.is_project_manager:
            return Task.objects.filter(
                Q(created_by=user) |
                Q(assigned_to=user) |
                Q(project__team__members__user=user, project__team__members__role__in=['owner', 'manager']),
                created_at__gte=start_date
            ).select_related(
                'project',
                'assigned_to'
            ).distinct().order_by('-created_at')
        else:
            return Task.objects.filter(
                assigned_to=user,
                created_at__gte=start_date
            ).select_related(
                'project',
                'assigned_to'
            ).order_by('-created_at')
    except Exception as e:
        logger.error(f"Error getting recent activity: {str(e)}")
        return Task.objects.none()

def create_task(data, created_by):
    """Create a new task with validation"""
    try:
        if not data.get('project'):
            raise ValidationError("Project is required")
            
        project = Project.objects.get(id=data['project'])
        
        # Check if user can create tasks in this project
        member = TeamMember.objects.get(team=project.team, user=created_by)
        if member.role not in ['owner', 'manager'] and created_by != project.manager:
            raise ValidationError("You don't have permission to create tasks in this project")

        task = Task.objects.create(
            title=data['title'],
            description=data.get('description', ''),
            project=project,
            assigned_to_id=data['assigned_to'],
            status=data.get('status', 'todo'),
            priority=data.get('priority', 'medium'),
            start_date=data['start_date'],
            due_date=data['due_date'],
            created_by=created_by
        )
        return task
        
    except (Project.DoesNotExist, TeamMember.DoesNotExist):
        raise ValidationError("Invalid project or insufficient permissions")
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        raise ValidationError("Failed to create task")

def update_task_status(task, new_status, user):
    """Update task status with validation"""
    try:
        if not task.can_be_modified_by(user):
            raise ValidationError("You don't have permission to modify this task")
            
        old_status = task.status
        task.status = new_status
        task.save()
        
        return {
            'success': True,
            'message': f"Task status updated from {old_status} to {new_status}"
        }
    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        raise ValidationError("Failed to update task status")