from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.config import MEMBER_ROLES, VALID_USER_STATUSES
from auth.models import RefreshToken, User
from auth.security import hash_password
from auth.service import get_user_by_username, validate_member_username, validate_password


def member_to_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "account_type": user.account_type,
        "role": user.role,
        "status": user.status,
        "created_at": int(user.created_at.timestamp() * 1000) if user.created_at else 0,
        "last_login_at": int(user.last_login_at.timestamp() * 1000) if user.last_login_at else 0,
    }


async def list_sub_accounts(session: AsyncSession, tenant_id: uuid.UUID) -> list[User]:
    """列表仅含子账号，不含主账号。"""
    result = await session.execute(
        select(User)
        .where(User.tenant_id == tenant_id, User.account_type == "member")
        .order_by(User.created_at.asc())
    )
    return list(result.scalars().all())


async def get_sub_account(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
    result = await session.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.account_type == "member",
        )
    )
    return result.scalar_one_or_none()


async def revoke_user_refresh_tokens(session: AsyncSession, user_id: uuid.UUID) -> None:
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
    )
    now = datetime.now(timezone.utc)
    for record in result.scalars():
        record.revoked_at = now


async def bump_token_version(session: AsyncSession, user: User) -> None:
    user.token_version = int(user.token_version or 0) + 1
    await revoke_user_refresh_tokens(session, user.id)
    await session.flush()


async def create_sub_account(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    username: str,
    password: str,
    role: str = "editor",
) -> User:
    username = validate_member_username(username)
    password = validate_password(password)
    clean_role = (role or "editor").strip().lower()
    if clean_role not in MEMBER_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的角色")

    if await get_user_by_username(session, username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该账号已存在")

    user = User(
        tenant_id=tenant_id,
        username=username,
        password_hash=hash_password(password),
        display_name=username,
        account_type="member",
        role=clean_role,
        status="active",
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该账号已存在") from exc
    return user


async def update_sub_account(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str | None = None,
    status: str | None = None,
) -> User:
    user = await get_sub_account(session, tenant_id, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="子账号不存在")

    changed = False
    if role is not None:
        clean_role = role.strip().lower()
        if clean_role not in MEMBER_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的角色")
        if user.role != clean_role:
            user.role = clean_role
            changed = True
    if status is not None:
        clean_status = status.strip().lower()
        if clean_status not in VALID_USER_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的状态")
        if user.status != clean_status:
            user.status = clean_status
            changed = True
    if changed:
        await bump_token_version(session, user)
    else:
        await session.flush()
    return user


async def delete_sub_account(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    user = await get_sub_account(session, tenant_id, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="子账号不存在")
    await session.delete(user)
    await session.flush()


async def reset_sub_account_password(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    password: str,
) -> User:
    user = await get_sub_account(session, tenant_id, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="子账号不存在")
    user.password_hash = hash_password(validate_password(password))
    await bump_token_version(session, user)
    return user
