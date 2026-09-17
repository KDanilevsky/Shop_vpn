import hmac
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, FastAPI, HTTPException, Request
from sqlalchemy import select

from db.async_db import SessionLocal
from db.models import AllInvoices
from services.events import create_pg_event

logger = logging.getLogger(__name__)
app = FastAPI()
router = APIRouter()

# No fallback is intentional: a missing secret must disable webhook processing.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


def _verify_secret(provided: str | None) -> bool:
    if not WEBHOOK_SECRET or not provided:
        return False
    return hmac.compare_digest(provided, WEBHOOK_SECRET)


@router.post("/webhook/invoice")
async def invoice_webhook(request: Request):
    if not WEBHOOK_SECRET:
        logger.error("WEBHOOK_SECRET is not configured")
        raise HTTPException(status_code=503, detail="webhook is not configured")

    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid json")

    if not isinstance(payload, dict) or not _verify_secret(payload.get("secret_key")):
        raise HTTPException(status_code=401, detail="invalid secret")

    invoice_id = payload.get("invoice_id")
    status_str = payload.get("status")
    if not invoice_id or status_str is None:
        raise HTTPException(status_code=400, detail="missing invoice_id or status")
    if status_str != "paid":
        return {"status": "ignored"}

    now_dt = datetime.now(timezone.utc)
    already_paid = False

    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(AllInvoices)
                .where(AllInvoices.invoice_id == str(invoice_id))
                .with_for_update()
            )
            invoice = result.scalar_one_or_none()
            if not invoice:
                raise HTTPException(status_code=404, detail="invoice not found")

            already_paid = invoice.invoice_status == "paid"
            if not already_paid:
                invoice.invoice_status = "paid"
                invoice.processing_status = "pending"
                invoice.invoice_updated_at = now_dt
                session.add(invoice)

    # The invoice processor owns all business processing. The webhook only marks paid.
    await create_pg_event("invoice_paid", {"invoice_id": str(invoice_id)})
    return {"status": "already_paid" if already_paid else "accepted"}


app.include_router(router)
