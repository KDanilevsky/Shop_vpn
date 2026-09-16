# api/webhook.py
import os
import logging
from datetime import datetime, timezone

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import FastAPI, APIRouter, Request, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from config import FIRST_USER_IN_DB

from services.helpers import enqueue_notification
from services.events import create_pg_event

from db.async_db import SessionLocal  # AsyncSession factory
from db.models import (
    AllInvoices,
    InvoiceItems,
    AllUsers,
    AllTransactions,
    PartnerTransactions,
    SubscriptionTransaction,
)

logger = logging.getLogger(__name__)
app = FastAPI()
router = APIRouter()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "blablabla123")
PROVISION_CHANNEL = "provision_queue"  # Postgres NOTIFY channel


def _verify_secret(provided: str | None) -> bool:
    return provided == WEBHOOK_SECRET


# webhook.py (updated)

@router.post("/webhook/invoice")
async def invoice_webhook(request: Request):
    payload = await request.json()

    if payload.get("secret_key") != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="invalid secret")

    invoice_id = payload.get("invoice_id")
    status_str = payload.get("status")

    if not invoice_id or status_str != "paid":
        return {"status": "ignored"}

    now_dt = datetime.now(timezone.utc)

    async with SessionLocal() as session:
        async with session.begin():
            q = (
                select(AllInvoices)
                .where(AllInvoices.invoice_id == invoice_id)
                .with_for_update()
            )
            r = await session.execute(q)
            invoice = r.scalar_one_or_none()

            if not invoice:
                raise HTTPException(status_code=404, detail="invoice not found")

            # Idempotent
            if invoice.invoice_status == "paid":
                await create_pg_event("invoice_paid", {"invoice_id": invoice_id}, session=session)
                return {"status": "already_paid"}

            invoice.invoice_status = "paid"
            invoice.processing_status = "pending"
            invoice.invoice_updated_at = now_dt
            session.add(invoice)

        # After commit
        await create_pg_event("invoice_paid", {"invoice_id": invoice_id})

    return {"status": "accepted"}


# async def _notify_tx_via_pg(tx_id: int, session: Optional[AsyncSession] | None = None) -> None:
#     """
#     Send NOTIFY provision_queue, '<tx_id>'.
#     If session is provided, use its connection; otherwise open a short-lived connection.
#     This is best-effort: failures are logged but non-fatal.
#     """
#     payload = str(tx_id)
#     try:
#         if session is not None:
#             # Use the same connection (no extra commit needed)
#             conn = await session.connection()
#             await conn.execute(text("NOTIFY provision_queue, :payload"), {"payload": payload})
#             return

#         # Open a short-lived session/connection to notify
#         async with SessionLocal() as s:
#             async with s.begin():
#                 conn = await s.connection()
#                 await conn.execute(text("NOTIFY provision_queue, :payload"), {"payload": payload})
#     except Exception:
#         logger.exception("Failed to NOTIFY provision_queue for tx %s", tx_id)


# # @router.post("/webhook/invoice")
# @router.post("/webhook/invoice")
# async def invoice_webhook(request: Request):
#     """
#     Webhook v9:
#     - Validates secret
#     - Loads invoice with FOR UPDATE
#     - If already paid → idempotent return
#     - Marks invoice as paid
#     - For top-up: immediately credits balance + creates AllTransactions
#     - For buy_subscription: creates SubscriptionTransaction(status='pending')
#       (NO partner/admin payouts here — they happen AFTER provisioning)
#     - Returns quickly and notifies worker
#     """
#     try:
#         payload = await request.json()
#     except Exception:
#         raise HTTPException(status_code=400, detail="invalid json")

#     provided_secret = payload.get("secret_key")
#     if not _verify_secret(provided_secret):
#         raise HTTPException(status_code=401, detail="invalid secret")

#     status_str = payload.get("status")
#     invoice_id = payload.get("invoice_id")

#     if not invoice_id or status_str is None:
#         raise HTTPException(status_code=400, detail="missing invoice_id or status")

#     # We only process "paid"
#     if status_str != "paid":
#         return {"status": "ignored"}

#     now_dt = datetime.now(timezone.utc)
#     now_ms = int(now_dt.timestamp() * 1000)

#     tx_id = None

#     try:
#         async with SessionLocal() as session:
#             async with session.begin():
#                 # Lock invoice row
#                 q = select(AllInvoices).where(AllInvoices.invoice_id == invoice_id).with_for_update()
#                 r = await session.execute(q)
#                 invoice = r.scalar_one_or_none()

#                 if not invoice:
#                     raise HTTPException(status_code=404, detail="invoice not found")

#                 # Idempotency: invoice already paid
#                 if invoice.invoice_status == "paid":
#                     # Try to find existing SubscriptionTransaction
#                     q2 = select(SubscriptionTransaction).where(
#                         SubscriptionTransaction.provider_invoice_id == invoice_id
#                     )
#                     r2 = await session.execute(q2)
#                     existing_tx = r2.scalar_one_or_none()

#                     if existing_tx:
#                         tx_id = int(existing_tx.id)
#                         await create_pg_event("tx", tx_id, session=session)
#                         # await _notify_tx_via_pg(tx_id, session=session)
#                         return {"status": "already_paid", "invoice_id": invoice_id, "tx_id": tx_id}

#                     # If invoice is paid but no tx exists → continue to create tx

#                 # Mark invoice as paid
#                 invoice.invoice_status = "paid"
#                 invoice.invoice_updated_at = now_dt
#                 session.add(invoice)

#                 # Load payer
#                 r = await session.execute(
#                     select(AllUsers).where(AllUsers.user_id == invoice.user_id).with_for_update()
#                 )
#                 user_paid = r.scalar_one_or_none()
#                 if not user_paid:
#                     raise HTTPException(status_code=404, detail="user not found")

#                 # Load inviter (if any)
#                 inviter = None
#                 if user_paid.user_id_who_invited:
#                     r2 = await session.execute(
#                         select(AllUsers)
#                         .where(AllUsers.user_id == user_paid.user_id_who_invited)
#                         .with_for_update()
#                     )
#                     inviter = r2.scalar_one_or_none()

#                 # ============================
#                 # CASE 1: TOP-UP BALANCE
#                 # ============================
#                 # if invoice.invoice_target == "popolnenie_balance":
#                 #     tx_db = AllTransactions(
#                 #         user_id=user_paid.user_id,
#                 #         trans_time=now_dt,
#                 #         trans_ammount=invoice.invoice_ammount,
#                 #         trans_target=invoice.invoice_target,
#                 #         accounts_ammount=invoice.accounts_ammount,
#                 #         quantity_guests_paid=invoice.quantity_guests_paid,
#                 #         promo=invoice.promo,
#                 #     )
#                 #     session.add(tx_db)

#                 #     # credit balance
#                 #     user_paid.user_balance = (user_paid.user_balance or 0) + invoice.invoice_ammount
#                 #     session.add(user_paid)

#                 #     # No SubscriptionTransaction here
#                 #     tx_id = None

#                 # ============================
#                 # CASE 1: TOP-UP MULTI BALANCE
#                 # ============================
#                 if invoice.invoice_target == "wallet_topup_multi":

#                     # Idempotency: check if already processed
#                     existing_tx = await session.execute(
#                         select(AllTransactions).where(
#                             AllTransactions.invoice_id == invoice_id,
#                             AllTransactions.trans_target == "wallet_topup_multi"
#                         )
#                     )
#                     if existing_tx.scalar_one_or_none():
#                         tx_id = None
#                         continue

#                     # Load targets from DB
#                     targets_result = await session.execute(
#                         select(InvoiceTopupTargets).where(
#                             InvoiceTopupTargets.invoice_id == invoice_id
#                         )
#                     )
#                     targets = targets_result.scalars().all()

#                     if not targets:
#                         raise HTTPException(status_code=500, detail="no topup targets found")

#                     accounts_count = len(targets)
#                     if accounts_count == 0:
#                         raise HTTPException(status_code=500, detail="no accounts selected")

#                     # Compute per-account amount
#                     per_account_cents = invoice.invoice_ammount // accounts_count

#                     # Distribute funds
#                     for t in targets:

#                         # SELF TOPUP
#                         if t.target_type == "self":
#                             user_paid.user_balance = (user_paid.user_balance or 0) + per_account_cents
#                             session.add(user_paid)

#                             session.add(AllTransactions(
#                                 user_id=user_paid.user_id,
#                                 trans_time=now_dt,
#                                 trans_ammount=per_account_cents,
#                                 trans_target="wallet_topup_multi",
#                                 invoice_id=invoice_id,
#                                 accounts_ammount=1,
#                                 quantity_guests_paid=invoice.quantity_guests_paid,
#                                 promo=invoice.promo,
#                             ))

#                             # Notify payer
#                             await enqueue_notification(
#                                 session=session,
#                                 user_id=user_paid.user_id,
#                                 reason="wallet_topup_multi",
#                                 invoice_id=invoice_id,
#                                 payload={
#                                     "amount": per_account_cents,
#                                     "from_username": user_paid.username,
#                                 },
#                             )
#                             # await create_pg_event("notify", session=session)

#                             continue

#                         # FRIEND TOPUP
#                         if t.target_type == "friend":
#                             friend = await session.get(AllUsers, t.friend_user_id)
#                             if not friend:
#                                 continue

#                             friend.user_balance = (friend.user_balance or 0) + per_account_cents
#                             session.add(friend)

#                             session.add(AllTransactions(
#                                 user_id=friend.user_id,
#                                 trans_time=now_dt,
#                                 trans_ammount=per_account_cents,
#                                 trans_target="wallet_topup_multi",
#                                 invoice_id=invoice_id,
#                                 accounts_ammount=1,
#                                 quantity_guests_paid=invoice.quantity_guests_paid,
#                                 promo=invoice.promo,
#                             ))
#                             # Notify friend
#                             await enqueue_notification(
#                                 session=session,
#                                 user_id=friend.user_id,
#                                 reason="wallet_topup_multi",
#                                 invoice_id=invoice_id,
#                                 payload={
#                                     "amount": per_account_cents,
#                                     "from_username": user_paid.username,
#                                 },
#                             )
#                             # await create_pg_event("notify", session=session)

#                     tx_id = None


#                 # ============================
#                 # CASE 2: BUY SUBSCRIPTION
#                 # ============================
#                 elif invoice.invoice_target == "subscription_renew":
#                     # inviter logic (unchanged)
#                     # if inviter:
#                     #     if inviter.subscription_stop_id_1 and now_ms <= inviter.subscription_stop_id_1:
#                     #         inviter.quantity_guests_paid = (inviter.quantity_guests_paid or 0) + invoice.accounts_ammount
#                     #     else:
#                     #         inviter.quantity_guests_paid_potent = (inviter.quantity_guests_paid_potent or 0) + invoice.accounts_ammount
#                     #     session.add(inviter)

#                     # record transaction (user paid money)
#                     tx_db = AllTransactions(
#                         user_id=user_paid.user_id,
#                         trans_time=now_dt,
#                         trans_ammount=invoice.invoice_ammount,
#                         trans_target=invoice.invoice_target,
#                         accounts_ammount=invoice.accounts_ammount,
#                         quantity_guests_paid=invoice.quantity_guests_paid,
#                         promo=invoice.promo,
#                     )
#                     session.add(tx_db)

#                     # add money to user balance (later provisioning will deduct)
#                     user_paid.user_balance = (user_paid.user_balance or 0) + invoice.invoice_ammount
#                     session.add(user_paid)

#                     # Notify payer
#                     await enqueue_notification(
#                         session=session,
#                         user_id=user_paid.user_id,
#                         reason="subscription_renew_paid",
#                         invoice_id=invoice_id,
#                         payload={
#                             "amount": per_account_cents,
#                             "from_username": user_paid.username,
#                         },
#                     )

#                     # ============================
#                     # Create SubscriptionTransaction (pending)
#                     # ============================

#                     # Load invoice items for this invoice_id
#                     items_result = await session.execute(
#                         select(InvoiceItems).where(InvoiceItems.invoice_id == invoice_id)
#                     )
#                     invoice_items = items_result.scalars().all()

#                     if not invoice_items:
#                         # This is a hard error: subscription invoice without items
#                         raise HTTPException(status_code=500, detail="no invoice_items for subscription invoice")

#                     # You can derive subs_id / requested_end_ts from invoice or items if needed,
#                     # or keep them generic and let provisioning decide.
#                     # For now we just store invoice_id and snapshot of items in payload_meta.

#                     tx = SubscriptionTransaction(
#                         user_id=user_paid.user_id,
#                         source="buy_subscription_webhook",
#                         subs_id=invoice.accounts_ammount,  # or some meaningful value, or 0
#                         requested_end_ts=now_ms,           # or derive from business logic
#                         status="pending",                  # provisioning will complete it
#                         provider_invoice_id=invoice_id,
#                         payload_meta={
#                             "invoice_id": invoice_id,
#                             "invoice_target": invoice.invoice_target,
#                             "invoice_amount": int(invoice.invoice_ammount),
#                             "accounts_amount": invoice.accounts_ammount,
#                             "promo": invoice.promo,
#                             "quantity_guests_paid": invoice.quantity_guests_paid,
#                             "items": [
#                                 {
#                                     "acc_number": it.acc_number,
#                                     "server_id": it.server_id,
#                                     "is_free": it.is_free,
#                                     "discount_percent": it.discount_percent,
#                                     "discount_amount": float(it.discount_amount),
#                                     "price": float(it.price),
#                                     "final_price": float(it.final_price),
#                                 }
#                                 for it in invoice_items
#                             ],
#                             "webhook_payload": payload,
#                         },
#                     )
#                     session.add(tx)
#                     await session.flush()
#                     tx_id = int(tx.id)


#                     # ============================
#                     # IMPORTANT:
#                     # NO partner/admin payouts here.
#                     # They will happen AFTER provisioning.
#                     # ============================

#                 else:
#                     raise HTTPException(status_code=400, detail="unknown invoice_target")

#             # end of session.begin()

#     except HTTPException:
#         raise
#     except Exception:
#         logger.exception("Webhook processing failed for invoice %s", invoice_id)
#         raise HTTPException(status_code=500, detail="internal error")
  
#     # Best-effort notify after commit (if not already notified)
#     try:
#         await create_pg_event("notify", session=session)
#         if tx_id is not None:
#             await create_pg_event("tx", tx_id)
#     except Exception:
#         logger.exception("Failed to notify worker for tx %s", tx_id)

#     return {"status": "accepted", "tx_id": tx_id}

app.include_router(router)
