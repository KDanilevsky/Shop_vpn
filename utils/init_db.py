from utils.db import engine
from utils.models import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Run it once manually:
# python -m utils.init_db