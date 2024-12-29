from django import template
from django.utils import timezone
from datetime import datetime

register = template.Library()

@register.filter
def add_class(field, class_name):
    """Adds a class to a form field's widget."""
    if not field:
        return ''
    return field.as_widget(attrs={'class': f"{field.field.widget.attrs.get('class', '')} {class_name}".strip()})

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
def completed_projects_count(projects):
    """Returns count of completed projects."""
    try:
        return projects.filter(status='completed').count() if projects else 0
    except Exception:
        return 0

@register.filter
def active_projects_count(projects):
    """Returns count of active projects."""
    try:
        return projects.filter(status='active').count() if projects else 0
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

@register.filter
def time_since(value):
    """Returns human readable time since given datetime."""
    if not value:
        return ''

    try:
        now = timezone.now() if timezone.is_aware(value) else datetime.now()
        diff = now - value

        intervals = [
            (diff.days // 365, "year"),
            (diff.days // 30, "month"),
            (diff.days, "day"),
            (diff.seconds // 3600, "hour"),
            (diff.seconds // 60, "minute"),
        ]

        for count, name in intervals:
            if count > 0:
                return f"{count} {name}{'s' if count != 1 else ''} ago"
                
        return "Just now"
    except Exception:
        return str(value)

@register.filter
def completed_tasks_count(tasks):
    """Returns count of completed tasks."""
    try:
        return tasks.filter(status='done').count() if tasks else 0
    except Exception:
        return 0

@register.filter
def format_status(status):
    """Formats status string to be more readable."""
    try:
        return status.replace('_', ' ').title()
    except Exception:
        return status

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