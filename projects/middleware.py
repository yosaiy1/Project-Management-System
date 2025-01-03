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

class PermissionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            logger.debug(f"User {request.user.username} accessing {request.path}")
            if 'team_id' in request.resolver_match.kwargs:
                team_id = request.resolver_match.kwargs['team_id']
                team = Team.objects.get(id=team_id)
                logger.debug(f"Team access check: {has_team_permission(request.user, team)}")
        
        response = self.get_response(request)
        return response