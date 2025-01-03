from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend that supports both username and email login
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to fetch the user by username or email
            user = User.objects.get(
                Q(username=username) | Q(email=username)
            )
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None