from sqlalchemy import select
from utils.db import SessionLocal
from utils.models import User

async def get_or_create_user(tg_id, username):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()

        if not user:
            user = User(tg_id=tg_id, username=username)
            session.add(user)

        await session.commit()
        return user
