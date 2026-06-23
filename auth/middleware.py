import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from auth.config import auth_public_paths, is_auth_required
from auth.database import session_scope
from auth.deps import ANONYMOUS_USER, CurrentUser, parse_bearer_token, user_from_access_token
from auth.service import get_user_by_id
from auth.tenant import clear_request_scope, scope_from_user, set_request_scope


async def _resolve_authenticated_user(token: str) -> CurrentUser | None:
    try:
        jwt_user = user_from_access_token(token)
    except Exception:
        return None
    async with session_scope() as session:
        db_user = await get_user_by_id(session, uuid.UUID(jwt_user.user_id))
        if not db_user or db_user.status != "active":
            return None
        if int(db_user.token_version or 0) != int(jwt_user.token_version or 0):
            return None
        return CurrentUser(
            user_id=str(db_user.id),
            tenant_id=str(db_user.tenant_id),
            account_type=db_user.account_type,
            role=db_user.role,
            display_name=db_user.display_name or db_user.username,
            token_version=int(db_user.token_version or 0),
        )


class AuthMiddleware(BaseHTTPMiddleware):
    """Attach request.state.user. Enforce JWT when AUTH_MODE=required."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if not is_auth_required():
            request.state.user = ANONYMOUS_USER
            scope = scope_from_user(ANONYMOUS_USER)
            request.state.data_scope = scope
            set_request_scope(scope)
            try:
                return await call_next(request)
            finally:
                clear_request_scope()

        if not path.startswith("/api/"):
            return await call_next(request)

        if path in auth_public_paths():
            return await call_next(request)

        token = parse_bearer_token(request)
        if not token:
            return JSONResponse(status_code=401, content={"detail": "需要登录"})
        user = await _resolve_authenticated_user(token)
        if not user:
            return JSONResponse(status_code=401, content={"detail": "无效或已过期的访问令牌"})
        request.state.user = user

        scope = scope_from_user(request.state.user)
        request.state.data_scope = scope
        set_request_scope(scope)
        try:
            return await call_next(request)
        finally:
            clear_request_scope()
