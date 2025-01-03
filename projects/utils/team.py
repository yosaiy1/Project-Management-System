from django.db.models import Count, Q, F, FloatField, Case, When, Value, ExpressionWrapper
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import Team, TeamMember, Task, Project
import logging

logger = logging.getLogger(__name__)

def get_user_team_members(user):
    """Get team members based on user's role"""
    try:
        if user.is_project_manager:
            # Project managers see members of teams they manage
            teams = Team.objects.filter(
                Q(owner=user) |
                Q(projects__manager=user) |
                Q(members__user=user, members__role__in=['owner', 'manager'])
            )
        else:
            # Regular users only see members of their teams
            teams = Team.objects.filter(members__user=user)
            
        return TeamMember.objects.filter(
            team__in=teams
        ).select_related(
            'user', 
            'team'
        ).distinct()
    except Exception as e:
        logger.error(f"Error getting team members: {str(e)}")
        return TeamMember.objects.none()

def get_team_stats(team):
    """Calculate team statistics"""
    try:
        tasks = Task.objects.filter(project__team=team)
        stats = {
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(status='done').count(),
            'active_projects': team.projects.exclude(status='completed').count(),
            'completed_projects': team.projects.filter(status='completed').count()
        }
        
        stats['progress'] = (
            (stats['completed_tasks'] / stats['total_tasks'] * 100)
            if stats['total_tasks'] > 0 else 0
        )
        return stats
    except Exception as e:
        logger.error(f"Error calculating team stats: {str(e)}")
        return {
            'total_tasks': 0,
            'completed_tasks': 0,
            'active_projects': 0,
            'completed_projects': 0,
            'progress': 0
        }

def get_member_stats(member):
    """Calculate member statistics"""
    try:
        tasks = Task.objects.filter(
            assigned_to=member.user,
            project__team=member.team
        )
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='done').count()
        
        return {
            'task_count': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error calculating member stats: {str(e)}")
        return {
            'task_count': 0,
            'completed_tasks': 0,
            'completion_rate': 0
        }

def can_manage_team(user, team):
    """Check if user can manage team"""
    try:
        if user == team.owner or user.is_project_manager:
            return True
            
        return TeamMember.objects.filter(
            user=user,
            team=team,
            role__in=['owner', 'manager']
        ).exists()
    except Exception as e:
        logger.error(f"Error checking team permissions: {str(e)}")
        return False

def get_team_members_with_stats(team):
    """Get team members with their statistics"""
    try:
        return TeamMember.objects.filter(
            team=team
        ).select_related(
            'user',
            'user__profile'
        ).annotate(
            task_count=Count('user__assigned_tasks', filter=Q(user__assigned_tasks__project__team=team)),
            completed_tasks=Count(
                'user__assigned_tasks',
                filter=Q(
                    user__assigned_tasks__project__team=team,
                    user__assigned_tasks__status='done'
                )
            ),
            completion_rate=Case(
                When(task_count=0, then=Value(0.0)),
                default=ExpressionWrapper(
                    F('completed_tasks') * 100.0 / F('task_count'),
                    output_field=FloatField()
                ),
                output_field=FloatField()
            )
        ).order_by('-role', 'user__username')
    except Exception as e:
        logger.error(f"Error getting team members with stats: {str(e)}")
        return TeamMember.objects.none()

def get_team_progress(team):
    """Calculate overall team progress"""
    try:
        tasks = Task.objects.filter(project__team=team)
        total = tasks.count()
        completed = tasks.filter(status='done').count()
        
        return (completed / total * 100) if total > 0 else 0
    except Exception as e:
        logger.error(f"Error calculating team progress: {str(e)}")
        return 0

def get_active_teams(user):
    """Get active teams based on user role"""
    try:
        if user.is_project_manager:
            # Project managers see teams they manage
            query = Q(owner=user) | Q(projects__manager=user)
        else:
            # Regular users see teams they're members of
            query = Q(members__user=user)
            
        return Team.objects.filter(query).annotate(
            member_count=Count('members', distinct=True),
            project_count=Count('projects', distinct=True),
            completed_tasks=Count(
                'projects__tasks',
                filter=Q(projects__tasks__status='done'),
                distinct=True
            ),
            total_tasks=Count('projects__tasks', distinct=True)
        ).annotate(
            progress=Case(
                When(total_tasks=0, then=Value(0.0)),
                default=ExpressionWrapper(
                    F('completed_tasks') * 100.0 / F('total_tasks'),
                    output_field=FloatField()
                ),
                output_field=FloatField()
            )
        ).distinct()
    except Exception as e:
        logger.error(f"Error getting active teams: {str(e)}")
        return Team.objects.none()

def create_team_member(team, user, role='member', created_by=None):
    """Create a new team member"""
    try:
        if TeamMember.objects.filter(team=team, user=user).exists():
            raise ValidationError("User is already a member of this team")

        # If no created_by specified, use the team owner
        if not created_by:
            created_by = team.owner

        member = TeamMember.objects.create(
            team=team,
            user=user,
            role=role,
            created_by=created_by
        )
        
        notify_member_added(team, user, created_by)
        logger.info(f"Created team member: {user.username} in team {team.name}")
        return member
    except Exception as e:
        logger.error(f"Error creating team member: {str(e)}")
        raise

def notify_team_created(team, user):
    """Send notifications when a new team is created"""
    try:
        team.owner.notify(
            f"Team '{team.name}' created successfully",
            notification_type='success',
            action_type='team_created',
            related_object=team
        )

        for member in team.members.exclude(user=team.owner):
            member.user.notify(
                f"You have been added to team '{team.name}' by {user.username}",
                notification_type='info',
                action_type='team_joined',
                related_object=team
            )

        return True
    except Exception as e:
        logger.error(f"Error sending team creation notifications: {str(e)}")
        return False

def notify_team_update(team, user):
    """Send notifications when a team is updated"""
    try:
        if user != team.owner:
            team.owner.notify(
                f"Team '{team.name}' was updated by {user.username}",
                notification_type='info',
                action_type='team_updated',
                related_object=team
            )

        for member in team.members.exclude(user=user):
            member.user.notify(
                f"Team '{team.name}' has been updated",
                notification_type='info',
                action_type='team_updated',
                related_object=team
            )

        return True
    except Exception as e:
        logger.error(f"Error sending team update notifications: {str(e)}")
        return False

def notify_member_added(team, user, added_by):
    """Send notifications when a new member is added"""
    try:
        user.notify(
            f"You have been added to team '{team.name}' by {added_by.username}",
            notification_type='success',
            action_type='team_joined',
            related_object=team
        )

        if added_by != team.owner:
            team.owner.notify(
                f"{user.username} has been added to {team.name} by {added_by.username}",
                notification_type='info',
                action_type='member_added',
                related_object=team
            )

        return True
    except Exception as e:
        logger.error(f"Error sending member added notifications: {str(e)}")
        return False