from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404

class InventoryPermissionRequiredMixin(PermissionRequiredMixin):
    """
    Mixin that:
    - Requires user to be logged in (via PermissionRequiredMixin, which inherits from LoginRequiredMixin).
    - If logged in but lacks the required permission, raises Http404 instead of redirecting to login,
      to avoid revealing the existence of a resource to unauthorized users.
    """
    def handle_no_permission(self):
        # If the user is not authenticated, let the parent class redirect to login (standard behaviour).
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        # User is authenticated but doesn't have permission → 404
        raise Http404