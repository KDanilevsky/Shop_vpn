import asyncio
from db.models import Base
from concurrent.futures import TimeoutError
from db.async_db import engine
from db.async_db import SessionLocal
from db.crud import create_admin
from utils.settings_bootstrap import bootstrap_settings


async def _init_db_async(engine):
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created.")


async def _drop_db_async(engine):
    async with engine.begin() as conn:
        print("Dropping tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Tables dropped.")


def init_db(engine):
    asyncio.run(_init_db_async(engine))


def drop_db(engine):
    asyncio.run(_drop_db_async(engine))

def run_db_tasks(engine, loop=None, timeout=None):
    async def _recreate():
        await _drop_db_async(engine)
        await _init_db_async(engine)

        # Initialize settings BEFORE creating admin
        await bootstrap_settings()

        await create_admin()

    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None

    if running is not None:
        # We're inside a running loop — caller should `await` instead
        raise RuntimeError("Already inside an event loop; use 'await' to run DB tasks.")
    if loop is not None:
        future = asyncio.run_coroutine_threadsafe(_recreate(), loop)
        return future.result(timeout)
    return asyncio.run(_recreate())