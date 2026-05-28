import threading

_thread_local = threading.local()

def get_current_user():
    """Get the current user from thread-local storage."""
    return getattr(_thread_local, 'user', None)

def set_current_user(user):
    """Set the current user in thread-local storage."""
    _thread_local.user = user