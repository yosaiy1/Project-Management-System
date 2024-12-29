from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction  # Add this import
import logging

# Import models and utils
from ..models import Team
from .permissions import has_team_permission

# Initialize logger
logger = logging.getLogger(__name__)

def handle_view_errors(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"View error: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred.")
            return redirect('homepage')
    return wrapper

def transaction_handler(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            with transaction.atomic():
                return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Transaction error: {str(e)}")
            messages.error(request, "An error occurred.")
            return redirect('homepage')
    return wrapper

def team_permission_required(view_func):
    @wraps(view_func)
    def wrapper(request, team_id, *args, **kwargs):
        team = get_object_or_404(Team, id=team_id)
        if not has_team_permission(request.user, team):
            messages.error(request, "Permission denied.")
            return redirect('homepage')
        return view_func(request, team_id, *args, **kwargs)
    return wrapper