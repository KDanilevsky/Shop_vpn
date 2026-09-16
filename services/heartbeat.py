# # services/heartbeat.py

from datetime import datetime
from sqlalchemy import select
from db.async_db import SessionLocal
from db.models import Workers




# async def register_worker(name: str):
#     async with SessionLocal() as session:
#         worker = (await session.execute(
#             select(Workers).where(Workers.name == name)
#         )).scalar_one_or_none()

#         if not worker:
#             worker = Workers(name=name)
#             session.add(worker)

#         worker.last_heartbeat = datetime.utcnow()
#         worker.is_healthy = True
#         await session.commit()


async def get_heartbeats():
    async with SessionLocal() as session:
        workers = (await session.execute(select(Workers))).scalars().all()

    return [
        {
            "name": w.name,
            "last_heartbeat": w.last_heartbeat.isoformat() if w.last_heartbeat else None,
            "is_healthy": w.is_healthy,
            "queue_size": w.queue_size,
            "last_error": w.last_error,
            "debug_mode": w.debug_mode,
        }
        for w in workers
    ]


# async def get_heartbeat(worker_name: str):
#     async with SessionLocal() as session:
#         worker = (
#             await session.execute(
#                 select(Workers).where(Workers.name == worker_name)
#             )
#         ).scalar_one_or_none()

#         if not worker:
#             return None

#         return {
#             "name": worker.name,
#             "last_heartbeat": worker.last_heartbeat,
#             "is_healthy": worker.is_healthy,
#             "queue_size": worker.queue_size,
#             "last_error": worker.last_error,
#             "debug_mode": worker.debug_mode,
#         }


async def heartbeat(worker_name: str):
    async with SessionLocal() as session:
        worker = (
            await session.execute(
                select(Workers).where(Workers.name == worker_name)
            )
        ).scalar_one_or_none()

        if not worker:
            worker = Workers(name=worker_name)
            session.add(worker)

        worker.last_heartbeat = datetime.utcnow()
        worker.is_healthy = True

        await session.commit()

# async def heartbeat(name: str):
#     async with SessionLocal() as session:
#         worker = (await session.execute(
#             select(Workers).where(Workers.name == name)
#         )).scalar_one()

#         worker.last_heartbeat = datetime.utcnow()
#         worker.is_healthy = True
#         await session.commit()

async def report_error(name: str, error: str):
    async with SessionLocal() as session:
        worker = (await session.execute(
            select(Workers).where(Workers.name == name)
        )).scalar_one()

        worker.last_error = error
        worker.is_healthy = False
        await session.commit()


async def supervisor_check():
    async with SessionLocal() as session:
        workers = (await session.execute(select(Workers))).scalars().all()

    now = datetime.utcnow()

    for w in workers:
        if not w.last_heartbeat:
            continue

        delta = now - w.last_heartbeat

        if delta.total_seconds() > 30:
            # worker is dead
            restart_worker(w.name)


# import time
# from typing import Dict

# # worker_name -> last_heartbeat_ts
# HEARTBEATS: Dict[str, float] = {}

# def beat(worker_name: str):
#     HEARTBEATS[worker_name] = time.time()

# def get_heartbeats():
#     return HEARTBEATS.copy()
