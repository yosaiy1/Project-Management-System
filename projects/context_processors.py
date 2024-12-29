from .models import Notification

def notification_context(request):
    """Add notifications to template context"""
    if request.user.is_authenticated:
        notifications = (request.user.notifications
                       .select_related('content_type')
                       .order_by('-created_at')[:5])
        return {
            'notifications': notifications,
            'unread_notifications_count': request.user.notifications.filter(read=False).count()
        }
    return {
        'notifications': [],
        'unread_notifications_count': 0
    }