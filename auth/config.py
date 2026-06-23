import os
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
AUTH_BOOTSTRAP_FILE = os.path.join(DATA_DIR, "auth_bootstrap.json")

VALID_AUTH_MODES = frozenset({"off", "required"})
VALID_ACCOUNT_TYPES = frozenset({"owner", "member"})
VALID_ROLES = frozenset({"owner", "admin", "editor", "viewer"})
MEMBER_ROLES = frozenset({"editor", "viewer"})
VALID_USER_STATUSES = frozenset({"active", "disabled"})


def auth_mode() -> str:
    mode = (os.getenv("AUTH_MODE") or "off").strip().lower()
    return mode if mode in VALID_AUTH_MODES else "off"


def is_auth_required() -> bool:
    return auth_mode() == "required"


def database_url() -> str | None:
    raw = (os.getenv("DATABASE_URL") or os.getenv("AUTH_DATABASE_URL") or "").strip()
    return raw or None


def sync_database_url() -> str | None:
    """Return a sync driver URL suitable for Alembic / psycopg2."""
    url = database_url()
    if not url:
        return None
    return (
        url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        .replace("postgresql+asyncpg:", "postgresql+psycopg2:", 1)
    )


@lru_cache(maxsize=1)
def jwt_secret() -> str:
    secret = (os.getenv("JWT_SECRET") or "").strip()
    if secret:
        return secret
    if is_auth_required():
        raise RuntimeError("AUTH_MODE=required 时必须设置 JWT_SECRET 环境变量")
    return "dev-insecure-change-me"


def jwt_access_expire_minutes() -> int:
    try:
        return max(5, min(24 * 60, int(os.getenv("JWT_ACCESS_EXPIRE_MIN", "30"))))
    except (TypeError, ValueError):
        return 30


def jwt_refresh_expire_days() -> int:
    try:
        return max(1, min(90, int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))))
    except (TypeError, ValueError):
        return 7


def auth_public_paths() -> frozenset[str]:
    return frozenset(
        {
            "/api/auth/status",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
            "/api/auth/logout",
        }
    )
