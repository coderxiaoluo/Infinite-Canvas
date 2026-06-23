"""Migrate legacy global JSON data into tenant-scoped storage."""

from __future__ import annotations

import json
import os
import shutil

from auth.config import AUTH_BOOTSTRAP_FILE, DATA_DIR, is_auth_required
from auth.tenant import (
    TENANT_MIGRATION_FLAG,
    api_providers_path,
    asset_library_path,
    conversation_root,
    ensure_data_dirs,
    projects_path,
)

CANVAS_DIR = os.path.join(DATA_DIR, "canvases")
CONVERSATION_DIR = os.path.join(DATA_DIR, "conversations")
LEGACY_PROVIDERS = os.path.join(DATA_DIR, "api_providers.json")
LEGACY_PROJECTS = os.path.join(DATA_DIR, "projects.json")
LEGACY_ASSET_LIB = os.path.join(DATA_DIR, "asset_library.json")


def ensure_auth_data_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    ensure_data_dirs()


def _load_flag() -> dict:
    if not os.path.isfile(TENANT_MIGRATION_FLAG):
        return {}
    try:
        with open(TENANT_MIGRATION_FLAG, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_flag(payload: dict) -> None:
    ensure_auth_data_dirs()
    with open(TENANT_MIGRATION_FLAG, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


async def _resolve_migration_target() -> tuple[str, str, str] | None:
    if not is_auth_required():
        return None
    from sqlalchemy import select

    from auth.database import session_scope
    from auth.models import Tenant, User

    async with session_scope() as session:
        tenant_result = await session.execute(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            return None
        user_result = await session.execute(
            select(User)
            .where(User.tenant_id == tenant.id)
            .order_by(User.created_at.asc())
            .limit(1)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return None
        return str(tenant.id), str(user.id), user.username


def _migrate_canvases(tenant_id: str, user_id: str, username: str) -> int:
    if not os.path.isdir(CANVAS_DIR):
        return 0
    changed = 0
    for filename in os.listdir(CANVAS_DIR):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(CANVAS_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        updated = False
        if not data.get("tenant_id"):
            data["tenant_id"] = tenant_id
            updated = True
        if not data.get("created_by"):
            data["created_by"] = user_id
            updated = True
        if not data.get("owner"):
            data["owner"] = username[:40]
            updated = True
        if updated:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            changed += 1
    return changed


def _migrate_providers(tenant_id: str) -> bool:
    target = api_providers_path(tenant_id)
    if os.path.isfile(target):
        return False
    if not os.path.isfile(LEGACY_PROVIDERS):
        return False
    shutil.copy2(LEGACY_PROVIDERS, target)
    return True


def _migrate_projects(tenant_id: str) -> bool:
    target = projects_path(tenant_id)
    if os.path.isfile(target):
        return False
    if not os.path.isfile(LEGACY_PROJECTS):
        return False
    shutil.copy2(LEGACY_PROJECTS, target)
    return True


def _migrate_asset_library(tenant_id: str) -> bool:
    target = asset_library_path(tenant_id)
    if os.path.isfile(target):
        return False
    if not os.path.isfile(LEGACY_ASSET_LIB):
        return False
    shutil.copy2(LEGACY_ASSET_LIB, target)
    return True


def _migrate_conversations(tenant_id: str) -> int:
    if not os.path.isdir(CONVERSATION_DIR):
        return 0
    target_root = conversation_root(tenant_id)
    os.makedirs(target_root, exist_ok=True)
    moved = 0
    for name in os.listdir(CONVERSATION_DIR):
        src = os.path.join(CONVERSATION_DIR, name)
        if not os.path.isdir(src):
            continue
        if name == tenant_id:
            continue
        dst = os.path.join(target_root, name)
        if os.path.exists(dst):
            continue
        shutil.move(src, dst)
        moved += 1
    return moved


def migrate_tenant_data_sync(tenant_id: str, user_id: str, username: str) -> dict:
    ensure_auth_data_dirs()
    flag = _load_flag()
    if flag.get("complete") and flag.get("tenant_id") == tenant_id:
        return flag

    summary = {
        "complete": True,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "username": username,
        "canvases_updated": _migrate_canvases(tenant_id, user_id, username),
        "providers_migrated": _migrate_providers(tenant_id),
        "projects_migrated": _migrate_projects(tenant_id),
        "asset_library_migrated": _migrate_asset_library(tenant_id),
        "conversation_dirs_moved": _migrate_conversations(tenant_id),
    }
    _save_flag(summary)

    bootstrap = {}
    if os.path.isfile(AUTH_BOOTSTRAP_FILE):
        try:
            with open(AUTH_BOOTSTRAP_FILE, "r", encoding="utf-8") as f:
                bootstrap = json.load(f) or {}
        except Exception:
            bootstrap = {}
    bootstrap["tenant_data_migrated"] = True
    bootstrap["tenant_id"] = tenant_id
    with open(AUTH_BOOTSTRAP_FILE, "w", encoding="utf-8") as f:
        json.dump(bootstrap, f, ensure_ascii=False, indent=2)
    return summary


async def migrate_tenant_data_if_needed() -> None:
    if not is_auth_required():
        return
    flag = _load_flag()
    if flag.get("complete"):
        return
    target = await _resolve_migration_target()
    if not target:
        return
    tenant_id, user_id, username = target
    summary = migrate_tenant_data_sync(tenant_id, user_id, username)
    print(f"租户数据迁移完成: {json.dumps(summary, ensure_ascii=False)}")
