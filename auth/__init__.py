"""Authentication and multi-tenant user management for Infinite Canvas."""

from auth.config import auth_mode, is_auth_required

__all__ = ["auth_mode", "is_auth_required"]
