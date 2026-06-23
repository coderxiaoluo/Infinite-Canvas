from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError

from auth.config import is_auth_required
from auth.security import decode_access_token


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    tenant_id: str
    account_type: str
    role: str
    display_name: str = ""
    token_version: int = 0
    is_anonymous: bool = False


ANONYMOUS_USER = CurrentUser(
    user_id="anonymous",
    tenant_id="",
    account_type="member",
    role="editor",
    display_name="",
    is_anonymous=True,
)


def get_request_user(request: Request) -> CurrentUser | None:
    return getattr(request.state, "user", None)


def resolve_current_user(request: Request) -> CurrentUser:
    user = get_request_user(request)
    if user is not None:
        return user
    if not is_auth_required():
        return ANONYMOUS_USER
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期")


async def get_current_user(request: Request) -> CurrentUser:
    return resolve_current_user(request)


async def get_optional_current_user(request: Request) -> CurrentUser | None:
    user = get_request_user(request)
    if user is not None:
        return user
    if not is_auth_required():
        return ANONYMOUS_USER
    return None


def parse_bearer_token(request: Request) -> str | None:
    auth_header = (request.headers.get("Authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        return token or None
    return None


def user_from_access_token(token: str) -> CurrentUser:
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效或已过期的访问令牌") from exc
    user_id = str(payload.get("sub") or "").strip()
    tenant_id = str(payload.get("tenant_id") or "").strip()
    if not user_id or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌缺少用户信息")
    return CurrentUser(
        user_id=user_id,
        tenant_id=tenant_id,
        account_type=str(payload.get("account_type") or "member"),
        role=str(payload.get("role") or "editor"),
        token_version=int(payload.get("token_version") or 0),
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
