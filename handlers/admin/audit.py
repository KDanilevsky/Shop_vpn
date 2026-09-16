from db.async_db import SessionLocal
from db.models import AdminAuditLog
from datetime import datetime

async def audit_log(admin_id, action, target_type, target_id, before, after, reason=None):
    async with SessionLocal() as session:
        entry = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before=before,
            after=after,
            reason=reason,
            created_at=datetime.utcnow(),
        )
        session.add(entry)
        await session.commit()
