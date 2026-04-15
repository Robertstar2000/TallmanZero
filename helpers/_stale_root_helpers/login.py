from flask import session
import hashlib
import os

def get_current_user():
    """Get the currently logged in user from session."""
    return session.get("user")

def get_current_user_id():
    """Get the currently logged in user ID from session."""
    user = get_current_user()
    return user["id"] if user else None

def is_login_required():
    """Return True if authentication is enabled."""
    # We now always require auth unless explicitly disabled via environment
    return os.getenv("AUTH_DISABLED", "false").lower() != "true"
