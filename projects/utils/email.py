from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_team_removal_email(user, team, reason=None):
    """Send email notification when user is removed from team"""
    try:
        subject = f"You have been removed from {team.name}"
        context = {
            'user': user,
            'team': team,
            'reason': reason
        }
        
        html_message = render_to_string('emails/team_removal.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send team removal email: {str(e)}")
        return False