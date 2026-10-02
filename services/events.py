import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.async_db import SessionLocal

logger = logging.getLogger(__name__)
CURRENT_EVENT_VERSION = 1


async def create_pg_event(
    event_type: str,
    payload: dict | None = None,
    session: AsyncSession | None = None,
    channel: str = "events",
) -> None:
    event = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "version": CURRENT_EVENT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
    serialized = json.dumps(event, ensure_ascii=False)

    try:
        if session is not None:
            connection = await session.connection()
            await connection.execute(
                text("SELECT pg_notify(:channel, :payload)"),
                {"channel": channel, "payload": serialized},
            )
            return

        async with SessionLocal() as local_session:
            async with local_session.begin():
                connection = await local_session.connection()
                await connection.execute(
                    text("SELECT pg_notify(:channel, :payload)"),
                    {"channel": channel, "payload": serialized},
                )
    except Exception:
        logger.exception("Failed to emit event %s", event_type)


async def on_event(raw_payload: str):
    """Parse and dispatch an event without importing workers at module load time."""
    try:
        event = json.loads(raw_payload)
    except (TypeError, json.JSONDecodeError):
        logger.error("Invalid event payload: %s", raw_payload)
        return

    event_type = event.get("type")
    version = event.get("version")
    payload = event.get("payload") or {}

    if not event_type or version != CURRENT_EVENT_VERSION:
        logger.warning("Malformed or unsupported event: %s", event)
        return

    try:
        if event_type in {"int_invoice_created", "invoice_paid"}:
            from workers.invoice_processor import invoice_event
            invoice_event.set()
        elif event_type == "tx":
            tx_id = payload.get("tx_id")
            if tx_id is None:
                logger.error("tx event has no tx_id: %s", event)
                return
            from workers.process_tx import process_tx
            # asyncio.create_task(process_tx(int(tx_id)))

            # Запускаем параллельную задачу (семафоры и блокировки отработают внутри)
            task = asyncio.create_task(process_tx(int(tx_id)))
            
            # Жестко фиксируем задачу в памяти, чтобы Garbage Collector её не удалил
            if not hasattr(asyncio, "_running_events_tasks"):
                asyncio._running_events_tasks = set()
            
            asyncio._running_events_tasks.add(task)
            # Как только задача сама завершится, она удалится из памяти
            task.add_done_callback(asyncio._running_events_tasks.discard)
        elif event_type == "bitpapa":
            from workers.bitpappa_invoice_reconciller import bitpapa_event
            bitpapa_event.set()
        elif event_type == "reconcile":
            from workers.reconciler import reconcile_event
            reconcile_event.set()
        elif event_type == "notify":
            from workers.user_notification import notify_event
            notify_event.set()
        elif event_type == "restart_worker":
            worker_name = payload.get("worker_name")
            if worker_name:
                from workers.supervisor import cancel_worker_by_name
                cancel_worker_by_name(worker_name)
        else:
            logger.warning("Unknown event type: %s", event_type)
    except Exception:
        logger.exception("Handler failed for event %s", event_type)
