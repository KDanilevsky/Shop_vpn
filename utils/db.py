from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config import DATABASE_URL_PG


def create_engine_and_sessionmaker():
    engine = create_async_engine(DATABASE_URL_PG, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    return engine, SessionLocal

