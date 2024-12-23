from django import template

register = template.Library()

@register.filter
def add_class(field, class_name):
    """
    Adds a class to a form field's widget.
    """
    return field.as_widget(attrs={'class': class_name})

@register.filter
def task_status_color(status):
    """
    Maps task status to a corresponding CSS class.
    """
    if status == 'todo':
        return 'todo'
    elif status == 'inprogress':
        return 'inprogress'
    elif status == 'done':
        return 'done'
    return ''