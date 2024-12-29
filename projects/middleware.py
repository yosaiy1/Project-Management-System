from .models import Notification

class NotificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.notifications = request.user.notifications.select_related(
                'content_type'
            ).order_by('-created_at')[:5]
            request.unread_notifications_count = request.user.notifications.filter(
                read=False
            ).count()
        return self.get_response(request)