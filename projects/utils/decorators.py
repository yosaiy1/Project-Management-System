from functools import wraps
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction 
import logging 

# Import models and utils
from ..models import Team, Project, TeamMember
from .permissions import (
    has_team_permission, 
    can_manage_team,
    can_manage_project,
    can_create_team_member
)
from .constants import MSG_PERMISSION_DENIED

# Initialize logger
logger = logging.getLogger(__name__)

def handle_view_errors(view_func):
    """Decorator to handle view exceptions"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"View error in {view_func.__name__}: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred. Please try again.")
            return redirect('homepage')
    return wrapper

def transaction_handler(view_func):
    """Decorator to handle database transactions"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            with transaction.atomic():
                return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Transaction error in {view_func.__name__}: {str(e)}", exc_info=True)
            messages.error(request, "Database error occurred. Please try again.")
            return redirect('homepage')
    return wrapper

def team_permission_required(view_func):
    """Decorator to check team access permissions"""
    @wraps(view_func)
    def wrapper(request, team_id, *args, **kwargs):
        try:
            team = get_object_or_404(Team.objects.select_related('owner'), id=team_id)
            
            # Check team membership
            if not has_team_permission(request.user, team):
                messages.error(request, MSG_PERMISSION_DENIED)
                return redirect('team_list')
            
            # Add team to view kwargs
            kwargs['team'] = team
            return view_func(request, team_id, *args, **kwargs)
        except Exception as e:
            logger.error(f"Team permission error: {str(e)}", exc_info=True)
            messages.error(request, MSG_PERMISSION_DENIED)
            return redirect('homepage')
    return wrapper

def team_manager_required(view_func):
    """Decorator to check team management permissions"""
    @wraps(view_func)
    def wrapper(request, team_id=None, *args, **kwargs):
        try:
            # Check if team_id is provided
            if not team_id:
                messages.error(request, "Team ID is required")
                return redirect('team_list')
                
            # Get team with optimized query
            team = get_object_or_404(
                Team.objects.select_related(
                    'owner',
                    'owner__profile'
                ).prefetch_related(
                    'members'
                ), 
                id=team_id
            )
            
            # Check if user can manage team
            if not can_manage_team(request.user, team):
                messages.error(request, "Only team managers can perform this action")
                return redirect('team_detail', team_id=team_id)
            
            kwargs['team'] = team
            return view_func(request, team_id, *args, **kwargs)
            
        except Http404:
            messages.error(request, "Team not found")
            return redirect('team_list')
        except Exception as e:
            logger.error(f"Team manager permission error: {str(e)}", exc_info=True)
            messages.error(request, MSG_PERMISSION_DENIED)
            return redirect('team_list')
    return wrapper

def member_access_required(view_func):
    """Decorator to check team member access permissions"""
    @wraps(view_func)
    def wrapper(request, team_id, member_id, *args, **kwargs):
        try:
            team = get_object_or_404(Team, id=team_id)
            member = get_object_or_404(TeamMember, id=member_id, team=team)
            
            # Check if user has permission to access member
            if not (has_team_permission(request.user, team) and 
                   (request.user == team.owner or 
                    request.user == member.user or 
                    can_manage_team(request.user, team))):
                messages.error(request, MSG_PERMISSION_DENIED)
                return redirect('team_detail', team_id=team_id)
            
            kwargs['team'] = team
            kwargs['member'] = member
            return view_func(request, team_id, member_id, *args, **kwargs)
        except Exception as e:
            logger.error(f"Member access error: {str(e)}", exc_info=True)
            messages.error(request, MSG_PERMISSION_DENIED)
            return redirect('team_list')
    return wrapper