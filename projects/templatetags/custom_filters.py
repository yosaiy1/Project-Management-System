from django import template
from django.utils import timezone
from django.db.models import QuerySet
from datetime import datetime

register = template.Library()

@register.filter
def task_status_color(status):
    """Maps task status to a corresponding Bootstrap color class."""
    status_colors = {
        'todo': 'warning',
        'inprogress': 'info',
        'done': 'success',
        'blocked': 'danger',
        'unassigned': 'secondary'
    }
    return status_colors.get(str(status).lower(), 'secondary')

@register.filter
def role_color(role):
    """Maps user roles to corresponding Bootstrap color classes."""
    colors = {
        'owner': 'danger',
        'manager': 'primary',
        'member': 'success',
        'admin': 'dark'
    }
    return colors.get(str(role).lower(), 'secondary')

@register.filter
def priority_color(priority):
    """Maps priority levels to Bootstrap color classes."""
    colors = {
        'high': 'danger',
        'medium': 'warning',
        'low': 'info',
        'normal': 'secondary'
    }
    return colors.get(str(priority).lower(), 'secondary')

@register.filter
def time_since(value):
    """Returns a human-friendly time difference."""
    if not value:
        return 'Never'
        
    try:
        now = timezone.now()
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        diff = now - value

        if diff.days > 365:
            years = diff.days // 365
            return f'{years}y ago'
        elif diff.days > 30:
            months = diff.days // 30
            return f'{months}mo ago'
        elif diff.days > 0:
            return f'{diff.days}d ago'
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f'{hours}h ago'
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f'{minutes}m ago'
        else:
            return 'Just now'
    except Exception:
        return str(value)

@register.filter
def completed_tasks_count(queryset):
    """Returns count of completed tasks from queryset."""
    try:
        if not queryset:
            return 0
        return queryset.filter(status='done').count()
    except Exception:
        return 0

@register.filter
def progress_color(value):
    """Returns appropriate Bootstrap color class based on progress percentage."""
    try:
        value = float(value)
        if value >= 75:
            return 'success'
        elif value >= 50:
            return 'info'
        elif value >= 25:
            return 'warning'
        return 'danger'
    except (ValueError, TypeError):
        return 'secondary'

@register.filter
def filter_done_tasks(tasks):
    """Returns count of completed tasks from a task collection."""
    try:
        if not tasks:
            return 0
        if isinstance(tasks, QuerySet):
            return tasks.filter(status='done').count()
        if isinstance(tasks, list):
            return len([t for t in tasks if getattr(t, 'status', '') == 'done'])
        return 0
    except Exception:
        return 0

@register.filter
def completion_percentage(tasks):
    """Calculates completion percentage for a collection of tasks."""
    try:
        if not tasks:
            return 0
        total = len(tasks)
        completed = len([t for t in tasks if getattr(t, 'status', '') == 'done'])
        return round((completed / total) * 100) if total > 0 else 0
    except Exception:
        return 0

@register.filter
def format_deadline(value):
    """Formats deadline with appropriate styling class."""
    if not value:
        return ''
    
    try:
        now = timezone.now()
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            
        diff = value - now
        
        if diff.days < 0:
            return 'overdue'
        elif diff.days == 0:
            return 'due-today'
        elif diff.days <= 3:
            return 'due-soon'
        return 'upcoming'
    except Exception:
        return ''

@register.filter
def status_icon(status):
    """Returns appropriate Bootstrap icon class for task status."""
    icons = {
        'todo': 'bi-circle',
        'inprogress': 'bi-play-circle',
        'done': 'bi-check-circle-fill',
        'blocked': 'bi-x-circle',
        'unassigned': 'bi-dash-circle'
    }
    return icons.get(str(status).lower(), 'bi-circle')

@register.filter
def truncate_string(value, length=50):
    """Truncates string to specified length with ellipsis."""
    try:
        value = str(value)
        if len(value) <= length:
            return value
        return value[:length-3] + '...'
    except Exception:
        return value