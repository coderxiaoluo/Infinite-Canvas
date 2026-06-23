from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.config import AUTH_BOOTSTRAP_FILE
from auth.models import RefreshToken, Tenant, User
from auth.security import (
    create_access_token,
    create_refresh_token_value,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_password,
)

USERNAME_RE = re.compile(r"^[\w\u4e00-\u9fff.-]{2,80}$")
MEMBER_USERNAME_RE = re.compile(r"^[a-zA-Z0-9]{4,80}$")


def normalize_username(username: str) -> str:
    return (username or "").strip()


def validate_username(username: str) -> str:
    normalized = normalize_username(username)
    if not normalized or not USERNAME_RE.match(normalized):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账号格式不正确（2～80 位，支持中文、字母、数字）")
    return normalized


def validate_member_username(username: str) -> str:
    normalized = normalize_username(username)
    if not normalized or not MEMBER_USERNAME_RE.match(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="子账号名须为 4～80 位字母或数字",
        )
    return normalized


def validate_password(password: str) -> str:
    text = password or ""
    if len(text) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码至少 6 位")
    if len(text) > 128:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码过长")
    return text


def user_to_dict(user: User, tenant: Tenant | None = None) -> dict:
    return {
        "id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "username": user.username,
        "account_type": user.account_type,
        "role": user.role,
        "status": user.status,
    }


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == normalize_username(username)))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_tenant_by_id(session: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalar_one_or_none()


async def count_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(User))
    return int(result.scalar_one() or 0)


async def count_owners(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count()).select_from(User).where(User.account_type == "owner")
    )
    return int(result.scalar_one() or 0)


def mark_bootstrap_complete() -> None:
    os.makedirs(os.path.dirname(AUTH_BOOTSTRAP_FILE), exist_ok=True)
    payload = {"complete": True, "completed_at": datetime.now(timezone.utc).isoformat()}
    with open(AUTH_BOOTSTRAP_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


async def register_owner(
    session: AsyncSession,
    *,
    username: str,
    password: str,
) -> tuple[User, Tenant]:
    username = validate_username(username)
    password = validate_password(password)

    if (await count_owners(session)) > 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="系统已初始化，无法再次创建主账号")

    existing = await get_user_by_username(session, username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该账号已存在")

    tenant = Tenant(name="系统工作区")
    user = User(
        tenant=tenant,
        username=username,
        password_hash=hash_password(password),
        display_name=username,
        account_type="owner",
        role="owner",
        status="active",
    )
    session.add(tenant)
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该账号已存在") from exc

    mark_bootstrap_complete()
    return user, tenant


async def authenticate_user(session: AsyncSession, *, username: str, password: str) -> User:
    username = validate_username(username)
    password = validate_password(password)
    user = await get_user_by_username(session, username)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    tenant = await get_tenant_by_id(session, user.tenant_id)
    if not tenant or tenant.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="组织不可用")
    user.last_login_at = datetime.now(timezone.utc)
    await session.flush()
    return user


async def login_or_bootstrap(session: AsyncSession, *, username: str, password: str) -> tuple[User, Tenant]:
    if (await count_owners(session)) == 0:
        return await register_owner(session, username=username, password=password)
    user = await authenticate_user(session, username=username, password=password)
    tenant = await get_tenant_by_id(session, user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="组织数据异常")
    return user, tenant


async def issue_tokens(session: AsyncSession, user: User) -> tuple[str, str]:
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        account_type=user.account_type,
        role=user.role,
        token_version=user.token_version,
    )
    refresh_raw = create_refresh_token_value()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_raw),
            expires_at=refresh_token_expires_at(),
        )
    )
    await session.flush()
    return access_token, refresh_raw


async def refresh_session(session: AsyncSession, refresh_raw: str) -> tuple[str, str, User]:
    token_hash = hash_refresh_token(refresh_raw)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if not record or record.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token 无效")
    if record.expires_at.tzinfo is None:
        expires_at = record.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = record.expires_at
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token 已过期")

    user = await get_user_by_id(session, record.user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")

    record.revoked_at = datetime.now(timezone.utc)
    access_token, new_refresh_raw = await issue_tokens(session, user)
    return access_token, new_refresh_raw, user


async def logout_session(session: AsyncSession, refresh_raw: str | None) -> None:
    if not refresh_raw:
        return
    token_hash = hash_refresh_token(refresh_raw)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        await session.flush()
