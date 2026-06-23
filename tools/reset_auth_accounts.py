"""清空认证账号并允许重新初始化主账号。

用法（需 PostgreSQL 已启动）:
  set DATABASE_URL=postgresql+asyncpg://infinite_canvas:infinite_canvas@127.0.0.1:5433/infinite_canvas
  python tools/reset_auth_accounts.py

加 --yes 跳过确认。
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, func, select

from auth.config import AUTH_BOOTSTRAP_FILE, DATA_DIR
from auth.database import session_scope
from auth.models import RefreshToken, Tenant, User


async def counts() -> tuple[int, int, int]:
    async with session_scope() as session:
        users = int((await session.execute(select(func.count()).select_from(User))).scalar_one() or 0)
        owners = int(
            (await session.execute(select(func.count()).select_from(User).where(User.account_type == "owner"))).scalar_one()
            or 0
        )
        tenants = int((await session.execute(select(func.count()).select_from(Tenant))).scalar_one() or 0)
        return users, owners, tenants


async def reset_accounts() -> None:
    async with session_scope() as session:
        await session.execute(delete(RefreshToken))
        await session.execute(delete(User))
        await session.execute(delete(Tenant))

    bootstrap = Path(AUTH_BOOTSTRAP_FILE)
    if bootstrap.is_file():
        bootstrap.unlink()

    migration_flag = Path(DATA_DIR) / "auth_tenant_migration.json"
    if migration_flag.is_file():
        migration_flag.unlink()


def load_env_from_api_dotenv() -> None:
    env_file = ROOT / "API" / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


async def main() -> None:
    load_env_from_api_dotenv()
    if not (os.getenv("DATABASE_URL") or os.getenv("AUTH_DATABASE_URL")):
        print("错误：未配置 DATABASE_URL，请先设置环境变量或填写 API/.env")
        sys.exit(1)

    users, owners, tenants = await counts()
    print(f"当前：users={users}, owners={owners}, tenants={tenants}")

    args = parse_args()
    if not args.yes:
        print("\n将删除所有账号、租户、Refresh Token，并清除初始化标记。")
        answer = input("确认继续？输入 yes 执行: ").strip().lower()
        if answer != "yes":
            print("已取消。")
            return

    await reset_accounts()
    users, owners, tenants = await counts()
    print(f"完成。当前：users={users}, owners={owners}, tenants={tenants}")
    print("请重启服务后访问 /login，用新账号初始化主账号。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset Infinite Canvas auth accounts")
    parser.add_argument("--yes", action="store_true", help="跳过确认")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main())
