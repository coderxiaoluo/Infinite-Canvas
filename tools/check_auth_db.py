import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from auth.database import session_scope
from auth.service import count_owners, count_users


async def main() -> None:
    async with session_scope() as session:
        print("users:", await count_users(session))
        print("owners:", await count_owners(session))


if __name__ == "__main__":
    asyncio.run(main())
