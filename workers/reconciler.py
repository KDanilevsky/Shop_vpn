# workers/reconciler.py v11 (with advisory locks)

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import List, Set

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from db.async_db import SessionLocal
from db.models import SubscriptionTransaction
from workers.process_tx import process_tx
from utils.advisory_locks import acquire_tx_lock, release_tx_lock

from services.heartbeat import heartbeat

logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {"worker": "reconciler"})

BATCH_SIZE = 50
SCAN_INTERVAL_SECONDS = 10
MAX_CONCURRENCY = 8

MAX_RETRIES = 6
JITTER_FACTOR = 0.2
MAX_BACKOFF_SECONDS = 3600

_inflight_tx: Set[int] = set()

reconcile_event = asyncio.Event()


def _now_dt():
    return datetime.now(timezone.utc)


def _compute_scan_backoff() -> float:
    base = SCAN_INTERVAL_SECONDS
    jitter = base * JITTER_FACTOR
    return base + random.uniform(-jitter, jitter)


async def _fetch_candidates(limit: int) -> List[SubscriptionTransaction]:
    async with SessionLocal() as session:
        async with session.begin():
            q = (
                select(SubscriptionTransaction)
                .where(
                    SubscriptionTransaction.status.in_(["pending", "failed_retryable"]),
                    (SubscriptionTransaction.next_run_at.is_(None))
                    | (SubscriptionTransaction.next_run_at <= _now_dt()),
                )
                .order_by(SubscriptionTransaction.created_at)
                .limit(limit)
            )
            res = await session.execute(q)
            return res.scalars().all()


async def _schedule_worker(semaphore: asyncio.Semaphore, tx_id: int):
    try:
        async with semaphore:
            # Acquire advisory lock BEFORE processing
            async with SessionLocal() as session:
                async with session.begin():
                    got_lock = await acquire_tx_lock(session, tx_id)

            if not got_lock:
                logger.info("tx %s locked by another worker, skipping", tx_id)
                return

            _inflight_tx.add(tx_id)

            try:
                await process_tx(tx_id)
            finally:
                # Always release lock
                async with SessionLocal() as session:
                    async with session.begin():
                        await release_tx_lock(session, tx_id)

    except Exception as exc:
        logger.exception("process_tx failed for tx %s: %s", tx_id, exc)
    finally:
        _inflight_tx.discard(tx_id)


async def reconciliation_loop(stop_event: asyncio.Event):
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    tasks: List[asyncio.Task] = []

    logger.info("Reconciler loop started")

    try:
        while not stop_event.is_set():
            await heartbeat("reconciler")
            # 1. Fetch candidates
            try:
                txs = await _fetch_candidates(BATCH_SIZE)
            except SQLAlchemyError:
                logger.exception("DB fetch failed in reconciliation loop")
                await asyncio.sleep(SCAN_INTERVAL_SECONDS)
                continue

            # 2. Schedule tasks
            scheduled = 0
            for tx in txs:
                if stop_event.is_set():
                    break
                if tx.id in _inflight_tx:
                    continue
                if (tx.attempts or 0) >= MAX_RETRIES and tx.status == "failed_retryable":
                    continue

                task = asyncio.create_task(_schedule_worker(semaphore, tx.id))
                tasks.append(task)
                scheduled += 1

            tasks = [t for t in tasks if not t.done()]

            logger.info(
                "Reconciler scanned %d txs, scheduled %d tasks, inflight %d",
                len(txs),
                scheduled,
                len(_inflight_tx),
            )

            # 3. Compute backoff
            backoff = _compute_scan_backoff()

            # 4. Wait for event OR timeout OR stop_event
            try:
                await asyncio.wait_for(
                    asyncio.wait(
                        [
                            stop_event.wait(),
                            reconcile_event.wait(),
                        ],
                        return_when=asyncio.FIRST_COMPLETED,
                    ),
                    timeout=backoff,
                )
            except asyncio.TimeoutError:
                pass

            reconcile_event.clear()

    except asyncio.CancelledError:
        logger.info("Reconciliation loop cancelled")

    finally:
        if tasks:
            logger.info("Waiting for %d outstanding tasks to finish", len(tasks))
            await asyncio.wait(tasks, timeout=60)
        logger.info("Reconciliation loop stopped")


# # workers/reconciler.py v10

# import asyncio
# import logging
# import random
# from datetime import datetime, timezone, timedelta
# from typing import List, Set

# from sqlalchemy import select
# from sqlalchemy.exc import SQLAlchemyError

# from db.async_db import SessionLocal
# from db.models import SubscriptionTransaction
# from workers.process_tx import process_tx

# logger = logging.getLogger(__name__)

# BATCH_SIZE = 50
# SCAN_INTERVAL_SECONDS = 10
# MAX_CONCURRENCY = 8

# MAX_RETRIES = 6
# BASE_BACKOFF_SECONDS = 60
# JITTER_FACTOR = 0.2  # ±20% jitter
# MAX_BACKOFF_SECONDS = 3600  # 1 hour cap for generic backoff

# _inflight_tx: Set[int] = set()

# reconcile_event = asyncio.Event()


# def _now_dt() -> datetime:
#     return datetime.now(timezone.utc)


# def _compute_scan_backoff() -> float:
#     base = SCAN_INTERVAL_SECONDS
#     jitter = base * JITTER_FACTOR
#     return base + random.uniform(-jitter, jitter)


# async def _fetch_candidates(limit: int) -> List[SubscriptionTransaction]:
#     async with SessionLocal() as session:
#         async with session.begin():
#             q = (
#                 select(SubscriptionTransaction)
#                 .where(
#                     SubscriptionTransaction.status.in_(["pending", "failed_retryable"]),
#                     (SubscriptionTransaction.next_run_at.is_(None))
#                     | (SubscriptionTransaction.next_run_at <= _now_dt()),
#                 )
#                 .order_by(SubscriptionTransaction.created_at)
#                 .limit(limit)
#             )
#             res = await session.execute(q)
#             return res.scalars().all()


# async def _schedule_worker(semaphore: asyncio.Semaphore, tx_id: int):
#     try:
#         async with semaphore:
#             _inflight_tx.add(tx_id)
#             await process_tx(tx_id)
#     except Exception as exc:
#         logger.exception("process_tx failed for tx %s: %s", tx_id, exc)
#     finally:
#         _inflight_tx.discard(tx_id)



# async def reconciliation_loop(stop_event: asyncio.Event):
#     semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
#     tasks: List[asyncio.Task] = []

#     logger.info("Reconciler loop started")

#     try:
#         while not stop_event.is_set():

#             # 1. Fetch candidates
#             try:
#                 txs = await _fetch_candidates(BATCH_SIZE)
#             except SQLAlchemyError:
#                 logger.exception("DB fetch failed in reconciliation loop")
#                 await asyncio.sleep(SCAN_INTERVAL_SECONDS)
#                 continue

#             # 2. Schedule tasks
#             scheduled = 0
#             for tx in txs:
#                 if stop_event.is_set():
#                     break
#                 if tx.id in _inflight_tx:
#                     continue
#                 if (tx.attempts or 0) >= MAX_RETRIES and tx.status == "failed_retryable":
#                     continue

#                 task = asyncio.create_task(_schedule_worker(semaphore, tx.id))
#                 tasks.append(task)
#                 scheduled += 1

#             tasks = [t for t in tasks if not t.done()]

#             logger.info(
#                 "Reconciler scanned %d txs, scheduled %d tasks, inflight %d",
#                 len(txs),
#                 scheduled,
#                 len(_inflight_tx),
#             )

#             # 3. Compute backoff
#             backoff = _compute_scan_backoff()

#             # 4. Wait for event OR timeout OR stop_event
#             try:
#                 await asyncio.wait_for(
#                     asyncio.wait(
#                         [
#                             stop_event.wait(),
#                             reconcile_event.wait(),
#                         ],
#                         return_when=asyncio.FIRST_COMPLETED,
#                     ),
#                     timeout=backoff,
#                 )
#             except asyncio.TimeoutError:
#                 pass

#             # 5. Clear event so next NOTIFY wakes us again
#             reconcile_event.clear()

#     except asyncio.CancelledError:
#         logger.info("Reconciliation loop cancelled")

#     finally:
#         if tasks:
#             logger.info("Waiting for %d outstanding tasks to finish", len(tasks))
#             await asyncio.wait(tasks, timeout=60)
#         logger.info("Reconciliation loop stopped")
