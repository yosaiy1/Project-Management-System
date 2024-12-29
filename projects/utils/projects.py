from django.utils import timezone
from ..models import Project

def get_user_projects(user):
    """Get all projects for a user with optimized queries"""
    return (Project.objects.filter(team__members__user=user)
            .select_related('team')
            .distinct()
            .order_by('-created_at'))