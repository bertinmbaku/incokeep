from .current_user import set_current_user

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set the current user before the view is called
        set_current_user(request.user if request.user.is_authenticated else None)
        try:
            response = self.get_response(request)
        finally:
            # Clear the current user after the request to prevent leakage
            set_current_user(None)
        return response