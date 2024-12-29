from django.utils import timezone
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
    """
    try:
        return Notification.objects.create(
            user=user,
            message=message,
            read=False
        )
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return None

def get_user_notifications(user):
    """Get notifications for a user with optimized query"""
    try:
        return (Notification.objects.filter(user=user)
                .select_related('user')
                .order_by('-created_at'))
    except Exception as e:
        logger.error(f"Error getting user notifications: {str(e)}")
        return Notification.objects.none()