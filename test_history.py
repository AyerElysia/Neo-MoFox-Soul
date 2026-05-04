import asyncio
import os
import sys

sys.path.append("/root/Elysia/Neo-MoFox")

from src.kernel.db.core.engine import configure_engine, get_session_maker
from src.core.managers.stream_manager import StreamManager
from src.core.models.db_models import Messages
from src.core.managers.stream_manager import get_stream_manager
from src.kernel.db.api.query import QueryBuilder

async def test():
    configure_engine("sqlite+aiosqlite:////root/Elysia/Neo-MoFox/data/MoFox.db")
    sm = StreamManager()
    
    stream_id = "5750ede86191a7126b731cc03325ba9c520f8bf00fba38775b73259621bff177"
    ctx = await sm.load_stream_context(stream_id, 1000)
    print(f"Loaded {len(ctx.history_messages)} messages for stream {stream_id}")

if __name__ == "__main__":
    asyncio.run(test())
