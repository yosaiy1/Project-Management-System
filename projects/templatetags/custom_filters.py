from django import template
from django.utils import timezone
from django.db.models import QuerySet
from datetime import datetime

register = template.Library()

@register.filter
def task_status_color(status):
    """Maps task status to a corresponding CSS class."""
    status_colors = {
        'todo': 'warning',
        'inprogress': 'info',
        'done': 'success',
        'blocked': 'danger'
    }
    return status_colors.get(status.lower(), 'secondary')

@register.filter
def role_color(role):
    """Maps team member role to Bootstrap color class."""
    try:
        role_colors = {
            'owner': 'danger',
            'admin': 'warning',
            'member': 'info',
            'viewer': 'secondary'
        }
        return role_colors.get(str(role).lower(), 'secondary')
    except Exception:
        return 'secondary'

@register.filter
def time_since(value):
    """Returns a human-friendly time difference"""
    if not value:
        return 'Never'
        
    now = timezone.now()
    diff = now - value

    if diff.days > 365:
        return f'{diff.days // 365}y ago'
    elif diff.days > 30:
        return f'{diff.days // 30}mo ago'
    elif diff.days > 0:
        return f'{diff.days}d ago'
    elif diff.seconds > 3600:
        return f'{diff.seconds // 3600}h ago'
    elif diff.seconds > 60:
        return f'{diff.seconds // 60}m ago'
    else:
        return 'Just now'

@register.filter
def completed_tasks_count(queryset):
    """Returns count of completed tasks from queryset"""
    try:
        if not queryset:
            return 0
        return queryset.filter(status='done').count()
    except Exception:
        return 0

@register.filter
def progress_color(value):
    """Returns appropriate Bootstrap color class based on progress value."""
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