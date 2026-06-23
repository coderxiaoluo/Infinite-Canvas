from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from auth.config import database_url, is_auth_required

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _normalize_async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def get_engine() -> AsyncEngine | None:
    global _engine, _session_factory
    url = database_url()
    if not url:
        return None
    if _engine is None:
        _engine = create_async_engine(_normalize_async_url(url), pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    get_engine()
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("未配置 DATABASE_URL，无法连接认证数据库")
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def check_database_connection() -> tuple[bool, str | None]:
    """Return (connected, error_message)."""
    if not database_url():
        return False, None
    engine = get_engine()
    if engine is None:
        return False, "engine 未初始化"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        return False, str(exc)


async def init_auth_database() -> None:
    """Startup hook: verify DB when auth is required."""
    if not is_auth_required():
        return
    if not database_url():
        raise RuntimeError("AUTH_MODE=required 时必须配置 DATABASE_URL")
    connected, error = await check_database_connection()
    if not connected:
        raise RuntimeError(f"认证数据库连接失败: {error}")


async def dispose_auth_database() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
