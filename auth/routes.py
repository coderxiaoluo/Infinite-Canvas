import json
import os
import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status

from auth.config import (
    AUTH_BOOTSTRAP_FILE,
    auth_mode,
    database_url,
    is_auth_required,
    jwt_access_expire_minutes,
    jwt_refresh_expire_days,
)
from auth.cookies import REFRESH_COOKIE_NAME, clear_refresh_cookie, set_refresh_cookie
from auth.database import check_database_connection, session_scope
from auth.deps import CurrentUserDep
from auth.schemas import (
    AuthCredentialsRequest,
    AuthStatusResponse,
    LogoutResponse,
    MeResponse,
    RefreshRequest,
    TokenResponse,
    UserPublic,
)
from auth.service import (
    count_owners,
    count_users,
    get_tenant_by_id,
    get_user_by_id,
    issue_tokens,
    login_or_bootstrap,
    logout_session,
    refresh_session,
    register_owner,
    user_to_dict,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def load_bootstrap_state() -> dict:
    if not os.path.isfile(AUTH_BOOTSTRAP_FILE):
        return {}
    try:
        with open(AUTH_BOOTSTRAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def require_auth_database() -> None:
    if not is_auth_required():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前 AUTH_MODE=off，无需登录")
    if not database_url():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="未配置 DATABASE_URL")


def read_refresh_token(request: Request, body_token: str = "") -> str:
    cookie_token = (request.cookies.get(REFRESH_COOKIE_NAME) or "").strip()
    if cookie_token:
        return cookie_token
    return (body_token or "").strip()


def build_token_response(response: Response, access_token: str, refresh_token: str, user_dict: dict) -> TokenResponse:
    set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=jwt_access_expire_minutes() * 60,
        user=UserPublic(**user_dict),
    )


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status() -> AuthStatusResponse:
    configured = bool(database_url())
    connected = False
    db_error = None
    has_users = False
    has_owner = False
    if configured:
        connected, db_error = await check_database_connection()
        if connected:
            try:
                async with session_scope() as session:
                    has_users = (await count_users(session)) > 0
                    has_owner = (await count_owners(session)) > 0
            except Exception:
                has_users = False
                has_owner = False

    bootstrap = load_bootstrap_state()
    bootstrap_complete = bool(bootstrap.get("complete"))

    return AuthStatusResponse(
        auth_mode=auth_mode(),
        auth_required=is_auth_required(),
        database_configured=configured,
        database_connected=connected,
        database_error=db_error,
        bootstrap_complete=bootstrap_complete,
        jwt_access_expire_minutes=jwt_access_expire_minutes(),
        jwt_refresh_expire_days=jwt_refresh_expire_days(),
        has_users=has_users,
        has_owner=has_owner,
    )


@router.post("/register", response_model=TokenResponse)
async def auth_register(payload: AuthCredentialsRequest, response: Response) -> TokenResponse:
    """系统初始化：创建全局唯一主账号（仅当尚未存在主账号时）。"""
    require_auth_database()
    async with session_scope() as session:
        if (await count_owners(session)) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="系统已初始化，请使用主账号登录；子账号由主账号在管理后台创建",
            )
        user, tenant = await register_owner(session, username=payload.username, password=payload.password)
        access_token, refresh_token = await issue_tokens(session, user)
        user_dict = user_to_dict(user, tenant)
    return build_token_response(response, access_token, refresh_token, user_dict)


@router.post("/login", response_model=TokenResponse)
async def auth_login(payload: AuthCredentialsRequest, response: Response) -> TokenResponse:
    require_auth_database()
    async with session_scope() as session:
        user, tenant = await login_or_bootstrap(session, username=payload.username, password=payload.password)
        access_token, refresh_token = await issue_tokens(session, user)
        user_dict = user_to_dict(user, tenant)
    return build_token_response(response, access_token, refresh_token, user_dict)


@router.post("/refresh", response_model=TokenResponse)
async def auth_refresh(request: Request, response: Response, payload: RefreshRequest | None = None) -> TokenResponse:
    require_auth_database()
    refresh_raw = read_refresh_token(request, (payload.refresh_token if payload else ""))
    if not refresh_raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 Refresh Token")

    async with session_scope() as session:
        access_token, refresh_token, user = await refresh_session(session, refresh_raw)
        tenant = await get_tenant_by_id(session, user.tenant_id)
        user_dict = user_to_dict(user, tenant)
    return build_token_response(response, access_token, refresh_token, user_dict)


@router.post("/logout", response_model=LogoutResponse)
async def auth_logout(request: Request, response: Response, payload: RefreshRequest | None = None) -> LogoutResponse:
    refresh_raw = read_refresh_token(request, (payload.refresh_token if payload else ""))
    if database_url() and refresh_raw:
        async with session_scope() as session:
            await logout_session(session, refresh_raw)
    clear_refresh_cookie(response)
    return LogoutResponse(ok=True)


@router.get("/me", response_model=MeResponse)
async def auth_me(user: CurrentUserDep) -> MeResponse:
    if not is_auth_required():
        return MeResponse(
            auth_required=False,
            user=None,
            is_owner=True,
            can_manage_providers=True,
            can_manage_members=True,
        )

    if user.is_anonymous:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    async with session_scope() as session:
        db_user = await get_user_by_id(session, uuid.UUID(user.user_id))
        if not db_user or db_user.status != "active":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")
        tenant = await get_tenant_by_id(session, db_user.tenant_id)
        user_dict = user_to_dict(db_user, tenant)

    from auth.deps import CurrentUser
    from auth.tenant import scope_from_user
    scope = scope_from_user(CurrentUser(
        user_id=str(db_user.id),
        tenant_id=str(db_user.tenant_id),
        account_type=db_user.account_type,
        role=db_user.role,
    ))
    is_owner = scope.is_owner()
    return MeResponse(
        auth_required=True,
        user=UserPublic(**user_dict),
        is_owner=is_owner,
        can_manage_providers=scope.can_manage_providers(),
        can_manage_members=scope.can_manage_members(),
    )
