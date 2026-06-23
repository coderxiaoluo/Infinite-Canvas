import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from auth.config import jwt_access_expire_minutes, jwt_refresh_expire_days, jwt_secret

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    *,
    user_id: str,
    tenant_id: str,
    account_type: str,
    role: str,
    token_version: int = 0,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=jwt_access_expire_minutes())
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "account_type": account_type,
        "role": role,
        "token_version": token_version,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, jwt_secret(), algorithm=ALGORITHM)


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=jwt_refresh_expire_days())


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, jwt_secret(), algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("invalid token type")
    return payload
