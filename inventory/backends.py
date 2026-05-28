"""
Custom authentication backend that returns inactive users so the login form
can show a specific "pending activation" message instead of a generic
"invalid username or password" error.
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class AllowInactiveModelBackend(ModelBackend):
    """
    Behaves like ModelBackend, but returns the user object even if
    is_active=False.  The AuthenticationForm.confirm_login_allowed()
    method is then responsible for rejecting the login with a clear
    message (handled by our CustomAuthenticationForm).
    """

    def user_can_authenticate(self, user):
        # Always allow — let the form decide
        return True
