# advisory_locks.py

import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Key-space separation
# ------------------------------------------------------------
# We separate invoice locks and tx locks so they never collide.
#
# invoice lock key = 1_000_000_000 + invoice_id
# tx lock key       = 2_000_000_000 + tx_id
#
# This guarantees:
# - invoice_id=123 and tx_id=123 do NOT conflict
# - future lock types can be added safely
# ------------------------------------------------------------

INVOICE_LOCK_OFFSET = 1_000_000_000
TX_LOCK_OFFSET = 2_000_000_000


def _invoice_lock_key(invoice_id: int) -> int:
    return INVOICE_LOCK_OFFSET + int(invoice_id)


def _tx_lock_key(tx_id: int) -> int:
    return TX_LOCK_OFFSET + int(tx_id)


# ------------------------------------------------------------
# Generic helpers
# ------------------------------------------------------------

# async def _try_lock(session: AsyncSession, key: int) -> bool:
#     """
#     Try to acquire a PostgreSQL advisory lock.
#     Returns True if lock acquired, False otherwise.
#     """
#     try:
#         r = await session.execute(
#             text("SELECT pg_try_advisory_lock(:key)"),
#             {"key": key},
#         )
#         return bool(r.scalar())
#     except Exception:
#         logger.exception("Failed to acquire advisory lock %s", key)
#         return False


# async def _unlock(session: AsyncSession, key: int) -> None:
#     """
#     Release a PostgreSQL advisory lock.
#     """
#     try:
#         await session.execute(
#             text("SELECT pg_advisory_unlock(:key)"),
#             {"key": key},
#         )
#     except Exception:
#         logger.exception("Failed to release advisory lock %s", key)

async def _try_lock(session: AsyncSession, key: int) -> bool:
    """
    Используем транзакционный замок pg_try_advisory_xact_lock.
    Он автоматически уничтожается базой данных при commit или rollback.
    """
    try:
        r = await session.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"),
            {"key": key},
        )
        return bool(r.scalar())
    except Exception:
        logger.exception("Failed to acquire transaction advisory lock %s", key)
        return False

async def _unlock(session: AsyncSession, key: int) -> None:
    """
    Для xact-замков ручной unlock не требуется, база сделает это сама.
    Оставляем функцию пустой, чтобы не переписывать блоки finally в воркерах.
    """
    pass

# ------------------------------------------------------------
# Invoice locks
# ------------------------------------------------------------

async def acquire_invoice_lock(session: AsyncSession, invoice_id: int) -> bool:
    """
    Acquire a global lock for invoice_id.
    Prevents multiple workers (webhook, reconciler, processor)
    from processing the same invoice concurrently.
    """
    key = _invoice_lock_key(invoice_id)
    return await _try_lock(session, key)


async def release_invoice_lock(session: AsyncSession, invoice_id: int) -> None:
    key = _invoice_lock_key(invoice_id)
    await _unlock(session, key)


# ------------------------------------------------------------
# Transaction locks
# ------------------------------------------------------------

async def acquire_tx_lock(session: AsyncSession, tx_id: int) -> bool:
    """
    Acquire a global lock for tx_id.
    Ensures only one worker processes a subscription transaction.
    """
    key = _tx_lock_key(tx_id)
    return await _try_lock(session, key)


async def release_tx_lock(session: AsyncSession, tx_id: int) -> None:
    key = _tx_lock_key(tx_id)
    await _unlock(session, key)
