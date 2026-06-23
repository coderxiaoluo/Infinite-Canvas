"""Multi-tenant data scope for JSON storage isolation."""

from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status

from auth.config import DATA_DIR, is_auth_required
from auth.deps import ANONYMOUS_USER, CurrentUser, get_request_user

PROVIDERS_DIR = os.path.join(DATA_DIR, "providers")
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
ASSET_LIBS_DIR = os.path.join(DATA_DIR, "asset_libraries")
TENANT_MIGRATION_FLAG = os.path.join(DATA_DIR, "auth_tenant_migration.json")

_scope_var: ContextVar[Optional["DataScope"]] = ContextVar("data_scope", default=None)


@dataclass(frozen=True)
class DataScope:
    tenant_id: str
    user_id: str
    account_type: str
    role: str
    auth_required: bool

    @property
    def is_legacy(self) -> bool:
        return not self.auth_required

    def is_owner(self) -> bool:
        return self.account_type == "owner" or self.role == "owner"

    def can_manage_providers(self) -> bool:
        return not self.auth_required or self.is_owner()

    def can_manage_members(self) -> bool:
        return not self.auth_required or self.is_owner()

    def can_write_canvas(self, canvas: dict) -> bool:
        if not self.auth_required:
            return True
        if self.role == "viewer":
            return False
        if self.is_owner():
            return True
        created_by = str(canvas.get("created_by") or "").strip()
        return not created_by or created_by == self.user_id


def legacy_scope() -> DataScope:
    return DataScope(tenant_id="", user_id="", account_type="owner", role="owner", auth_required=False)


def scope_from_user(user: CurrentUser) -> DataScope:
    if not is_auth_required() or user.is_anonymous:
        return legacy_scope()
    return DataScope(
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        account_type=user.account_type,
        role=user.role,
        auth_required=True,
    )


def scope_from_request(request: Request) -> DataScope:
    cached = getattr(request.state, "data_scope", None)
    if cached is not None:
        return cached
    user = get_request_user(request) or ANONYMOUS_USER
    return scope_from_user(user)


def set_request_scope(scope: DataScope) -> None:
    _scope_var.set(scope)


def clear_request_scope() -> None:
    _scope_var.set(None)


def get_active_scope() -> DataScope:
    scope = _scope_var.get()
    if scope is not None:
        return scope
    if not is_auth_required():
        return legacy_scope()
    return legacy_scope()


def resolve_tenant_id(tenant_id: str | None = None) -> str:
    if tenant_id is not None:
        return tenant_id
    return get_active_scope().tenant_id


def api_providers_path(tenant_id: str | None = None) -> str:
    tid = resolve_tenant_id(tenant_id)
    if not tid:
        return os.path.join(DATA_DIR, "api_providers.json")
    os.makedirs(PROVIDERS_DIR, exist_ok=True)
    return os.path.join(PROVIDERS_DIR, f"{tid}.json")


def projects_path(tenant_id: str | None = None) -> str:
    tid = resolve_tenant_id(tenant_id)
    if not tid:
        return os.path.join(DATA_DIR, "projects.json")
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    return os.path.join(PROJECTS_DIR, f"{tid}.json")


def asset_library_path(tenant_id: str | None = None) -> str:
    tid = resolve_tenant_id(tenant_id)
    if not tid:
        return os.path.join(DATA_DIR, "asset_library.json")
    os.makedirs(ASSET_LIBS_DIR, exist_ok=True)
    return os.path.join(ASSET_LIBS_DIR, f"{tid}.json")


def conversation_root(tenant_id: str | None = None) -> str:
    tid = resolve_tenant_id(tenant_id)
    root = os.path.join(DATA_DIR, "conversations")
    if tid:
        root = os.path.join(root, tid)
    return root


def auth_user_id(scope: DataScope) -> str:
    if scope.auth_required and scope.user_id:
        return scope.user_id
    return ""


def canvas_belongs_to_scope(canvas: dict, scope: DataScope) -> bool:
    if not scope.auth_required:
        return True
    canvas_tenant = str(canvas.get("tenant_id") or "").strip()
    if canvas_tenant and canvas_tenant != scope.tenant_id:
        return False
    if scope.is_owner():
        return True
    if scope.role == "viewer":
        return True
    created_by = str(canvas.get("created_by") or "").strip()
    return not created_by or created_by == scope.user_id


def assert_canvas_read(canvas: dict, scope: DataScope) -> None:
    if not canvas_belongs_to_scope(canvas, scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="画布不存在")


def assert_canvas_write(canvas: dict, scope: DataScope) -> None:
    assert_canvas_read(canvas, scope)
    if not scope.can_write_canvas(canvas):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此画布")


def assert_provider_manage(scope: DataScope) -> None:
    if not scope.can_manage_providers():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改 API 配置")


def assert_manage_members(user) -> None:
    from auth.deps import CurrentUser

    if not isinstance(user, CurrentUser) or user.is_anonymous:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    if user.account_type != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅主账号可访问管理后台")


def stamp_canvas(canvas: dict, scope: DataScope, username: str = "") -> dict:
    if not scope.auth_required:
        return canvas
    canvas.setdefault("tenant_id", scope.tenant_id)
    canvas.setdefault("created_by", scope.user_id)
    if username and not canvas.get("owner"):
        canvas["owner"] = username[:40]
    return canvas


def ensure_data_dirs() -> None:
    os.makedirs(PROVIDERS_DIR, exist_ok=True)
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    os.makedirs(ASSET_LIBS_DIR, exist_ok=True)
