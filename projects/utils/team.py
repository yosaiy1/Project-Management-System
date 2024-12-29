from django.db.models import Q
from ..models import Team, TeamMember
import logging

# Initialize logger
logger = logging.getLogger(__name__)

def get_user_team_members(user):
    """Get all team members for user's teams"""
    try:
        return TeamMember.objects.filter(
            team__in=Team.objects.filter(members__user=user)
        ).select_related('user', 'team').distinct()
    except Exception as e:
        logger.error(f"Error getting team members: {str(e)}")
        return TeamMember.objects.none()