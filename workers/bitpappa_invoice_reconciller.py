# bitpappa_invoice_reconciller.py

import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select

from db.async_db import SessionLocal
from db.models import AllInvoices
from services.events import create_pg_event
from services.bitpapa import BitpapaService

from services.heartbeat import heartbeat

logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {"worker": "bitpappa_invoice_reconciller"})

bitpappa_event = asyncio.Event()


async def bitpappa_get_invoices(bitpapa_service: BitpapaService):
    """Fetch invoices from Bitpapa API."""
    result = await bitpapa_service.get_invoices()
    return result.invoices


async def _fetch_unfinished_invoices(session):
    """Fetch invoices that still need reconciliation."""
    q = (
        select(AllInvoices)
        .where(AllInvoices.invoice_status.not_in(["paid", "cancelled"]))
    )
    r = await session.execute(q)
    return r.scalars().all()

# bitpappa_invoice_reconciller.py (updated)

async def _sync_invoice(session, db_inv, bitpapa_inv):
    if db_inv.invoice_status == bitpapa_inv.status:
        return
    
    logger.info(
        "Invoice %s status changed: %s → %s",
        db_inv.invoice_id, db_inv.invoice_status, bitpapa_inv.status
    )

    db_inv.invoice_status = bitpapa_inv.status
    db_inv.invoice_updated_at = datetime.now(timezone.utc)

    if bitpapa_inv.status == "paid":
        db_inv.processing_status = "pending"
        await create_pg_event("invoice_paid", {"invoice_id": db_inv.invoice_id}, session=session)


# async def _sync_invoice(session, db_inv, bitpapa_inv):
#     """Compare DB invoice with Bitpapa invoice and update if needed."""
#     if db_inv.status == bitpapa_inv.status:
#         return

#     logger.info(
#         "Invoice %s status changed: %s → %s",
#         db_inv.id, db_inv.status, bitpapa_inv.status
#     )

#     db_inv.status = bitpapa_inv.status
#     db_inv.updated_at = datetime.now(timezone.utc)

#     # If invoice is paid → trigger tx processing
#     if bitpapa_inv.status == "paid" and db_inv.tx_id:
#         await create_pg_event("tx", db_inv.tx_id, session=session)


async def _process_bitpapa_invoices(bitpapa_service: BitpapaService):
    """Full reconciliation pass."""
    invoices = await bitpappa_get_invoices(bitpapa_service)
    bitpapa_map = {inv.id: inv for inv in invoices}

    async with SessionLocal() as session:
        async with session.begin():
            db_invoices = await _fetch_unfinished_invoices(session)

            for db_inv in db_invoices:
                inv = bitpapa_map.get(db_inv.invoice_id)
                if inv:
                    await _sync_invoice(session, db_inv, inv)


async def bitpappa_invoice_reconciller(bitpapa_service: BitpapaService):
    """Main worker loop."""
    logger.info("Bitpapa invoice reconciller started")

    while True:
        await heartbeat("bitpappa_invoice_reconciller")
        try:
            # Wait for event OR fallback timeout
            try:
                await asyncio.wait_for(bitpappa_event.wait(), timeout=300.0)
            except asyncio.TimeoutError:
                pass

            bitpappa_event.clear()

            await _process_bitpapa_invoices(bitpapa_service)

        except Exception:
            logger.exception("bitpappa_invoice_reconciller failed")
            await asyncio.sleep(5)
