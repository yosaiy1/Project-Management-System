from django.utils import timezone
from django.db import transaction
from ..models import Notification
import logging
from .constants import (
    NOTIFICATION_INFO,
    NOTIFICATION_SUCCESS,
    NOTIFICATION_WARNING,
    NOTIFICATION_ERROR
)

# Initialize logger
logger = logging.getLogger(__name__)

def send_notification(user, message, notification_type=NOTIFICATION_INFO):
    """
    Create a new notification for a user
    Args:
        user: User object
        message: Notification message
        notification_type: Type of notification (info/success/warning/error)
    Returns:
        Notification object or None if failed
    """
    try:
        return Notification.objects.create(
            user=user,
            message=message,
            notification_type=notification_type,
            read=False,
            created_at=timezone.now()
        )
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return None

def get_user_notifications(user, limit=None):
    """
    Get notifications for a user with optimized query
    Args:
        user: User object
        limit: Optional limit for number of notifications
    Returns:
        QuerySet of notifications
    """
    try:
        notifications = (Notification.objects
            .filter(user=user)
            .select_related('user')
            .order_by('-created_at'))
        
        return notifications[:limit] if limit else notifications
    except Exception as e:
        logger.error(f"Error getting user notifications: {str(e)}")
        return Notification.objects.none()

def send_bulk_notifications(users, message, notification_type=NOTIFICATION_INFO):
    """
    Send notification to multiple users
    Args:
        users: Queryset or list of User objects
        message: Notification message
        notification_type: Type of notification
    Returns:
        Number of notifications created
    """
    try:
        with transaction.atomic():
            notifications = [
                Notification(
                    user=user,
                    message=message,
                    notification_type=notification_type,
                    created_at=timezone.now()
                ) for user in users
            ]
            return Notification.objects.bulk_create(notifications)
    except Exception as e:
        logger.error(f"Error sending bulk notifications: {str(e)}")
        return []

def cleanup_old_notifications(days=30):
    """
    Remove notifications older than specified days
    Args:
        days: Number of days to keep notifications
    Returns:
        Number of notifications deleted
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return Notification.objects.filter(created_at__lt=cutoff_date).delete()[0]
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {str(e)}")
        return 0

def mark_notifications_as_read(user, notification_ids=None):
    """
    Mark notifications as read for a user
    Args:
        user: User object
        notification_ids: Optional list of notification IDs to mark as read
    Returns:
        Number of notifications updated
    """
    try:
        notifications = Notification.objects.filter(user=user)
        if notification_ids:
            notifications = notifications.filter(id__in=notification_ids)
        return notifications.update(read=True)
    except Exception as e:
        logger.error(f"Error marking notifications as read: {str(e)}")
        return 0

def notify_team_changes(user, team, action_type, message):
    """Send notifications for team-related actions"""
    notification = Notification.objects.create(
        user=user,
        message=message,
        action_type=action_type,
        related_object=team
    )
    
    if action_type == 'team_member_removed':
        # Send email notification
        send_team_removal_email(user, team)
        
    return notification