import asyncio
import os
import sys

sys.path.append("/root/Elysia/Neo-MoFox")

from src.kernel.db.core.engine import configure_engine, get_session_maker
from src.core.managers.stream_manager import StreamManager
from src.core.models.db_models import Messages

async def check_history():
    configure_engine("sqlite+aiosqlite:////root/Elysia/Neo-MoFox/data/MoFox.db")
    async_session = get_session_maker()
    
    async with async_session() as session:
        from sqlalchemy import select
        stmt = select(Messages).filter_by(stream_id="live_broadcast").order_by(Messages.id.desc()).limit(10)
        result = await session.execute(stmt)
        messages = result.scalars().all()
        
        print(f"Total found in recent 10 for live_broadcast: {len(messages)}")
        for m in reversed(messages):
            print(f"[{m.message_type}] {m.sender_name}: {m.content[:50]}")

if __name__ == "__main__":
    asyncio.run(check_history())
