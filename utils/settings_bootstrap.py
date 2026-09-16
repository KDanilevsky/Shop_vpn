from db.async_db import SessionLocal
from db.models import Settings

DEFAULT_SETTINGS = {
    "maintenance_mode": "off",
    "feature_new_payment_flow": "off",
    "feature_new_server_selector": "off",
}

async def bootstrap_settings():
    async with SessionLocal() as session:
        for key, value in DEFAULT_SETTINGS.items():
            exists = await session.get(Settings, key)
            if not exists:
                session.add(Settings(key=key, value=value))
        await session.commit()
