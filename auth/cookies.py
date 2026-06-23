import os

from fastapi import Response

REFRESH_COOKIE_NAME = "ic_refresh_token"


def refresh_cookie_secure() -> bool:
    return (os.getenv("AUTH_COOKIE_SECURE") or "").strip().lower() in {"1", "true", "yes"}


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    from auth.config import jwt_refresh_expire_days

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=refresh_cookie_secure(),
        samesite="lax",
        path="/",
        max_age=jwt_refresh_expire_days() * 24 * 3600,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/")
