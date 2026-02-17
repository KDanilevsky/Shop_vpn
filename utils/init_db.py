from utils.db import engine
from utils.models import Base
from sqlalchemy.exc import OperationalError


async def drop_db():
    """Drop all tables if they exist."""
    try:
        async with engine.begin() as conn:
            print("Dropping all tables...")
            await conn.run_sync(Base.metadata.drop_all)
            print("All tables dropped.")
    except OperationalError as e:
        print("Database drop failed:", e)


async def init_db():
    """Create all tables."""
    try:
        async with engine.begin() as conn:
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("Tables created.")
    except OperationalError as e:
        print("Database init failed:", e)


# Run it once manually:
# python -m utils.init_db