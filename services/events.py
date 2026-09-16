import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from db.async_db import SessionLocal
import logging
import asyncio

logger = logging.getLogger(__name__)

CURRENT_EVENT_VERSION = 1


async def create_pg_event(
    event_type: str,
    payload: dict | None = None,
    session: AsyncSession | None = None,
    channel: str = "events",
) -> None:
    """
    Unified event emitter for PostgreSQL LISTEN/NOTIFY.
    Produces a versioned, traceable event envelope:

    {
        "id": "...",
        "type": "invoice_paid",
        "version": 1,
        "timestamp": "...",
        "payload": {...}
    }
    """

    # --- Build event envelope ---
    evt = {
        "id": str(uuid.uuid4()),  # traceability
        "type": event_type,
        "version": CURRENT_EVENT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }

    # --- Serialize ---
    json_payload = json.dumps(evt, ensure_ascii=False)

    try:
        if session is not None:
            conn = await session.connection()
            await conn.execute(
                text("SELECT pg_notify(:channel, :payload)"),
                {"channel": channel, "payload": json_payload},
            )
            return

        # No session provided → create a temporary one
        async with SessionLocal() as s:
            async with s.begin():
                conn = await s.connection()
                await conn.execute(
                    text("SELECT pg_notify(:channel, :payload)"),
                    {"channel": channel, "payload": json_payload},
                )

    except Exception:
        logger.exception(
            "Failed to emit event %s with payload %s", event_type, payload
        )


# events.py (continued)

from workers.invoice_processor import invoice_event
from workers.bitpappa_invoice_reconciller import bitpappa_event
from workers.reconciler import reconcile_event
from workers.user_notification import notify_event

async def on_event(raw_payload: str):
    """
    Called by PgListener when NOTIFY arrives.
    Parses JSON, validates schema, dispatches to correct worker.
    """

    # --- Parse JSON ---
    try:
        evt = json.loads(raw_payload)
    except Exception:
        logger.error("Invalid event payload: %s", raw_payload)
        return

    # --- Validate envelope ---
    etype = evt.get("type")
    version = evt.get("version")
    payload = evt.get("payload") or {}

    if not etype or version is None:
        logger.error("Malformed event: %s", evt)
        return

    if version != CURRENT_EVENT_VERSION:
        logger.warning(
            "Unknown event version %s (current %s)",
            version, CURRENT_EVENT_VERSION
        )
        return

    # --- Dispatch table ---
    handlers = {
        "int_invoice_created": lambda: invoice_event.set(),
        "invoice_paid": lambda: invoice_event.set(),
        "bitpapa": lambda: bitpappa_event.set(),
        "reconcile": lambda: reconcile_event.set(),
        "notify": lambda: notify_event.set(),
    }

    handler = handlers.get(etype)

    if handler:
        try:
            result = handler()
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            logger.exception("Handler failed for event %s", etype)
    else:
        logger.warning("Unknown event type: %s", etype)

