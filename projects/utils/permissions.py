from django.shortcuts import get_object_or_404
from ..models import TeamMember, Team, Project, Task

def has_team_permission(user, team):
    """Check if user has permission to access team"""
    return TeamMember.objects.filter(user=user, team=team).exists() or user == team.owner

def has_project_permission(user, project):
    """Check if user has permission to access project"""
    return has_team_permission(user, project.team)

def has_task_permission(user, task):
    """Check if user has permission to access/modify task"""
    return (user == task.assigned_to or 
            has_team_permission(user, task.project.team))

def is_team_owner(user, team):
    """Check if user is team owner"""
    return user == team.owner

def can_manage_team(user, team):
    """Check if user can manage team settings"""
    return is_team_owner(user, team)

def can_manage_project(user, project):
    """Check if user can manage project settings"""
    return is_team_owner(user, project.team)

def can_manage_task(user, task):
    """Check if user can manage task"""
    return (user == task.created_by or 
            user == task.assigned_to or
            is_team_owner(user, task.project.team))