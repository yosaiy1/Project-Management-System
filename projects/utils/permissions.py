from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from ..models import TeamMember, Team, Project, Task

def has_team_permission(user, team):
    """Check if user has permission to access team"""
    return (
        user == team.owner or 
        TeamMember.objects.filter(user=user, team=team).exists() or
        user.is_project_manager
    )

def has_project_permission(user, project):
    """Check if user has permission to access project"""
    # Project manager, team owner, or project manager always has access
    if user == project.manager or user == project.team.owner or user.is_project_manager:
        return True
        
    # Check team membership
    try:
        member = TeamMember.objects.get(team=project.team, user=user)
        # Team owners and managers have full access
        if member.role in ['owner', 'manager']:
            return True
        # Regular members can access projects in their team
        return member.team == project.team
    except TeamMember.DoesNotExist:
        # Check if user has assigned tasks even without membership
        return project.tasks.filter(assigned_to=user).exists()

def has_task_permission(user, task):
    """Check if user has permission to access/modify task"""
    # Project manager, team owner, task assignee have access
    if (user == task.project.manager or 
        user == task.project.team.owner or
        user == task.assigned_to or
        user.is_project_manager):
        return True
        
    try:
        member = TeamMember.objects.get(team=task.project.team, user=user)
        # Owners and managers have full access
        if member.role in ['owner', 'manager']:
            return True
        # Regular members can access tasks in their team
        return member.team == task.project.team
    except TeamMember.DoesNotExist:
        return False

def can_manage_team(user, team):
    """Check if user can manage team settings"""
    try:
        if user == team.owner or user.is_project_manager:
            return True
            
        member = TeamMember.objects.get(team=team, user=user)
        return member.role in ['owner', 'manager']
    except TeamMember.DoesNotExist:
        return False

def can_manage_project(user, project):
    """Check if user can manage project settings"""
    try:
        member = TeamMember.objects.get(team=project.team, user=user)
        return (
            user == project.manager or 
            member.role in ['owner', 'manager']
        )
    except TeamMember.DoesNotExist:
        return False

def can_manage_task(user, task):
    """Check if user can manage task"""
    try:
        member = TeamMember.objects.get(team=task.project.team, user=user)
        return (
            user == task.created_by or
            user == task.assigned_to or
            user == task.project.manager or
            member.role in ['owner', 'manager']
        )
    except TeamMember.DoesNotExist:
        return False

def can_create_team_member(user, team):
    """Check if user can create team members"""
    try:
        if user == team.owner or user.is_project_manager:
            return True
            
        member = TeamMember.objects.get(team=team, user=user)
        return member.role in ['owner', 'manager']
    except TeamMember.DoesNotExist:
        return False

def can_assign_tasks(user, project):
    """Check if user can assign tasks in project"""
    try:
        if user == project.manager:
            return True
            
        member = TeamMember.objects.get(team=project.team, user=user)
        return member.role in ['owner', 'manager']
    except TeamMember.DoesNotExist:
        return False

def can_generate_reports(user, team):
    """Check if user can generate team/project reports"""
    try:
        if user == team.owner or user.is_project_manager:
            return True
            
        member = TeamMember.objects.get(team=team, user=user)
        return member.role in ['owner', 'manager']
    except TeamMember.DoesNotExist:
        return False

def verify_team_permission(user, team):
    """Verify team access or raise PermissionDenied"""
    if not has_team_permission(user, team):
        raise PermissionDenied("You don't have permission to access this team")

def verify_project_permission(user, project):
    """Verify project access or raise PermissionDenied"""
    if not has_project_permission(user, project):
        raise PermissionDenied("You don't have permission to access this project")

def verify_task_permission(user, task):
    """Verify task access or raise PermissionDenied"""
    if not has_task_permission(user, task):
        raise PermissionDenied("You don't have permission to access this task")