# invoice_processor.py

# A subscription invoice is only truly completed when:
# 1. User balance is credited (external invoice)

# 2. User balance is debited (internal invoice)

# 3. SubscriptionTransaction is created

# 4. SubscriptionTransaction is successfully processed by tx_processor

# 5. Provisioning succeeds

# 6. Admin/partner payouts are created

# 7. Frozen amounts are cleared

# 8. Notifications are sent

# Only after all of this is done is the invoice “fully processed”.


import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, and_

from db.async_db import SessionLocal
from db.models import (
    AllInvoices,
    AllUsers,
    AllTransactions,
    SubscriptionTransaction,
    InvoiceItems,
    InvoiceTopupTargets,
)
from services.events import create_pg_event
from utils.advisory_locks import acquire_invoice_lock, release_invoice_lock

from services.heartbeat import heartbeat

logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {"worker": "invoice_processor"})

invoice_event = asyncio.Event()


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
async def _fetch_invoices_to_process(session):
    """
    Process:
    - paid invoices (Bitpapa or internal already marked paid)
    - pending internal_balance invoices (need to deduct from balance)
    """
    q = (
        select(AllInvoices)
        .where(
            (
                (AllInvoices.invoice_status == "paid")
                & (AllInvoices.processing_status.in_(["pending", "error"]))
            )
            | (
                (AllInvoices.invoice_status == "pending")
                & (AllInvoices.invoice_source == "internal_balance")
                & (AllInvoices.processing_status.in_(["pending", "error"]))
            )
        )
        .with_for_update(skip_locked=True)
    )
    r = await session.execute(q)
    return r.scalars().all()


async def _has_tx_with_target(session, invoice_id: str, target: str) -> bool:
    q = select(AllTransactions).where(
        and_(
            AllTransactions.invoice_id == invoice_id,
            AllTransactions.trans_target == target,
        )
    )
    r = await session.execute(q)
    return r.scalars().first() is not None


async def _cancel_if_superseded(session, invoice: AllInvoices) -> bool:
    """
    Cancel stale subscription invoices if there is a newer one
    for the same user and target.
    """
    if invoice.invoice_target not in ("subscription_renew", "subscription_renew_internal"):
        return False

    q = (
        select(AllInvoices)
        .where(
            AllInvoices.user_id == invoice.user_id,
            AllInvoices.invoice_target.in_(["subscription_renew", "subscription_renew_internal"]),
            AllInvoices.invoice_created_at > invoice.invoice_created_at,
            AllInvoices.invoice_status.in_(["pending", "paid"]),
            AllInvoices.processing_status.in_(["pending", "processing"]),
        )
        .limit(1)
    )
    r = await session.execute(q)
    newer = r.scalars().first()
    if newer:
        invoice.processing_status = "canceled"
        session.add(invoice)
        return True
    return False


# ---------------------------------------------------------
# WALLET TOPUP MULTI
# ---------------------------------------------------------
async def _process_wallet_topup_multi(session, invoice: AllInvoices, user_paid: AllUsers):
    now_dt = datetime.now(timezone.utc)

    # idempotency: if already processed, skip
    if await _has_tx_with_target(session, invoice.invoice_id, "wallet_topup_multi"):
        return

    targets_result = await session.execute(
        select(InvoiceTopupTargets).where(
            InvoiceTopupTargets.invoice_id == invoice.invoice_id
        )
    )
    targets = targets_result.scalars().all()

    if not targets:
        raise RuntimeError("No topup targets found")

    per_account_cents = invoice.invoice_ammount // len(targets)

    for t in targets:
        if t.target_type == "self":
            user_paid.user_balance = (user_paid.user_balance or 0) + per_account_cents
            session.add(user_paid)

            session.add(
                AllTransactions(
                    user_id=user_paid.user_id,
                    trans_time=now_dt,
                    trans_ammount=per_account_cents,
                    trans_target="wallet_topup_multi",
                    invoice_id=invoice.invoice_id,
                )
            )

        elif t.target_type == "friend":
            friend = await session.get(AllUsers, t.friend_user_id, with_for_update=True)
            if not friend:
                continue

            friend.user_balance = (friend.user_balance or 0) + per_account_cents
            session.add(friend)

            session.add(
                AllTransactions(
                    user_id=friend.user_id,
                    trans_time=now_dt,
                    trans_ammount=per_account_cents,
                    trans_target="wallet_topup_multi",
                    invoice_id=invoice.invoice_id,
                )
            )


# ---------------------------------------------------------
# SUBSCRIPTION RENEWAL
# ---------------------------------------------------------
async def _load_invoice_items(session, invoice_id: str) -> list[InvoiceItems]:
    items_result = await session.execute(
        select(InvoiceItems).where(InvoiceItems.invoice_id == invoice_id)
    )
    items = items_result.scalars().all()
    if not items:
        raise RuntimeError("No invoice_items for subscription invoice")
    return items


def _calc_subscription_cost(items: list[InvoiceItems]) -> int:
    return sum(int(it.final_price) for it in items)


async def _topup_full_amount_if_needed(session, invoice: AllInvoices, user_paid: AllUsers):
    """
    For Bitpapa invoices: top-up full paid amount to user balance once.
    """
    if invoice.invoice_source != "bitpapa":
        return

    # idempotency: if already topped up, skip
    if await _has_tx_with_target(session, invoice.invoice_id, "wallet_topup_invoice"):
        return

    now_dt = datetime.now(timezone.utc)
    amount = int(invoice.invoice_ammount or 0)
    if amount <= 0:
        return

    user_paid.user_balance = (user_paid.user_balance or 0) + amount
    session.add(user_paid)

    session.add(
        AllTransactions(
            user_id=user_paid.user_id,
            trans_time=now_dt,
            trans_ammount=amount,
            trans_target="wallet_topup_invoice",
            invoice_id=invoice.invoice_id,
        )
    )


async def _deduct_subscription_cost(
    session,
    invoice: AllInvoices,
    user_paid: AllUsers,
    subs_cost: int,
):
    """
    Deduct subscription cost from user balance (internal or Bitpapa after topup).
    """
    # idempotency: if already deducted, skip
    if await _has_tx_with_target(session, invoice.invoice_id, "subscription_cost"):
        return

    if (user_paid.user_balance or 0) < subs_cost:
        raise RuntimeError("Insufficient balance for subscription cost")

    now_dt = datetime.now(timezone.utc)

    user_paid.user_balance = (user_paid.user_balance or 0) - subs_cost
    session.add(user_paid)

    session.add(
        AllTransactions(
            user_id=user_paid.user_id,
            trans_time=now_dt,
            trans_ammount=-subs_cost,
            trans_target="subscription_cost",
            invoice_id=invoice.invoice_id,
        )
    )


async def _create_subscription_tx(
    session,
    invoice: AllInvoices,
    user_paid: AllUsers,
    items: list[InvoiceItems],
    subs_cost: int,
) -> int:
    now_dt = datetime.now(timezone.utc)
    now_ms = int(now_dt.timestamp() * 1000)

    tx = SubscriptionTransaction(
        user_id=user_paid.user_id,
        source="invoice_processor",
        subs_id=invoice.accounts_ammount,
        requested_end_ts=now_ms,
        status="pending",
        provider_invoice_id=invoice.invoice_id,
        payload_meta={
            "invoice_id": invoice.invoice_id,
            "invoice_amount": int(invoice.invoice_ammount or 0),
            "subscription_cost": subs_cost,
            "items": [
                {
                    "acc_number": it.acc_number,
                    "server_country_id": it.server_country_id,
                    "price": float(it.price),
                    "final_price": float(it.final_price),
                }
                for it in items
            ],
        },
    )
    session.add(tx)
    await session.flush()
    return int(tx.id)


async def _process_subscription_renew(session, invoice: AllInvoices, user_paid: AllUsers):
    # cancel if superseded by newer invoice
    if await _cancel_if_superseded(session, invoice):
        return None

    items = await _load_invoice_items(session, invoice.invoice_id)
    subs_cost = _calc_subscription_cost(items)

    # Bitpapa: top-up full amount first
    if invoice.invoice_source == "bitpapa" and invoice.invoice_status == "paid":
        await _topup_full_amount_if_needed(session, invoice, user_paid)

    # Internal: invoice_status may be pending, we still deduct from balance
    await _deduct_subscription_cost(session, invoice, user_paid, subs_cost)

    # Mark invoice as paid if it was internal pending
    if invoice.invoice_status != "paid":
        invoice.invoice_status = "paid"
        invoice.invoice_updated_at = datetime.now(timezone.utc)
        session.add(invoice)

    tx_id = await _create_subscription_tx(session, invoice, user_paid, items, subs_cost)
    return tx_id


# ---------------------------------------------------------
# PROCESS A SINGLE INVOICE
# ---------------------------------------------------------
async def _process_single_invoice(session, invoice: AllInvoices):
    got_lock = await acquire_invoice_lock(session, invoice.invoice_id)
    if not got_lock:
        logger.info("Invoice %s locked by another worker", invoice.invoice_id)
        return

    try:
        # lock invoice row explicitly
        inv_row = await session.get(AllInvoices, invoice.invoice_id, with_for_update=True)
        if not inv_row:
            return
        invoice = inv_row

        invoice.processing_status = "processing"
        session.add(invoice)

        user_paid = await session.get(AllUsers, invoice.user_id, with_for_update=True)
        if not user_paid:
            raise RuntimeError("User not found")

        # WALLET TOPUP
        if invoice.invoice_target == "wallet_topup_multi":
            await _process_wallet_topup_multi(session, invoice, user_paid)
            invoice.processing_status = "completed"
            return

        # SUBSCRIPTION RENEWAL
        if invoice.invoice_target in ("subscription_renew", "subscription_renew_internal"):
            tx_id = await _process_subscription_renew(session, invoice, user_paid)
            if tx_id is None:
                # superseded / canceled
                invoice.processing_status = "canceled"
                return

            invoice.processing_status = "waiting_tx"
            session.add(invoice)

            # tx_processor will:
            # - provision
            # - on failure: refund subscription_cost with metadata
            await create_pg_event("tx", {"tx_id": tx_id}, session=session)
            return

        raise RuntimeError(f"Unknown invoice_target: {invoice.invoice_target}")

    except Exception:
        # invoice stays paid if it was paid; processing_status marks error
        invoice.processing_status = "error"
        logger.exception("Failed to process invoice %s", invoice.invoice_id)

    finally:
        await release_invoice_lock(session, invoice.invoice_id)


# ---------------------------------------------------------
# PROCESS ALL PENDING INVOICES
# ---------------------------------------------------------
async def _process_pending_invoices():
    async with SessionLocal() as session:
        async with session.begin():
            invoices = await _fetch_invoices_to_process(session)
            for inv in invoices:
                await _process_single_invoice(session, inv)


# ---------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------
async def invoice_processor():
    logger.info("Invoice processor started")

    while True:
        await heartbeat("invoice_processor")
        try:
            try:
                await asyncio.wait_for(invoice_event.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass

            invoice_event.clear()
            await _process_pending_invoices()

        except Exception:
            logger.exception("invoice_processor failed")
            await asyncio.sleep(5)


# import asyncio
# import logging
# from datetime import datetime, timezone
# from sqlalchemy import select

# from db.async_db import SessionLocal
# from db.models import AllInvoices, AllUsers, AllTransactions, SubscriptionTransaction, InvoiceItems, InvoiceTopupTargets
# from services.events import create_pg_event
# from utils.advisory_locks import acquire_invoice_lock, release_invoice_lock

# logger = logging.getLogger(__name__)

# invoice_event = asyncio.Event()


# async def _fetch_invoices_to_process(session):
#     q = (
#         select(AllInvoices)
#         .where(
#             AllInvoices.invoice_status == "paid",
#             AllInvoices.processing_status.in_(["pending", "error"])
#         )
#         .with_for_update(skip_locked=True)
#     )
#     r = await session.execute(q)
#     return r.scalars().all()


# async def _process_wallet_topup_multi(session, invoice, user_paid):
#     now_dt = datetime.now(timezone.utc)

#     # Load targets
#     targets_result = await session.execute(
#         select(InvoiceTopupTargets).where(
#             InvoiceTopupTargets.invoice_id == invoice.invoice_id
#         )
#     )
#     targets = targets_result.scalars().all()

#     if not targets:
#         raise RuntimeError("No topup targets found")

#     per_account_cents = invoice.invoice_ammount // len(targets)

#     for t in targets:
#         if t.target_type == "self":
#             user_paid.user_balance += per_account_cents
#             session.add(user_paid)

#             session.add(AllTransactions(
#                 user_id=user_paid.user_id,
#                 trans_time=now_dt,
#                 trans_ammount=per_account_cents,
#                 trans_target="wallet_topup_multi",
#                 invoice_id=invoice.invoice_id,
#             ))

#         elif t.target_type == "friend":
#             friend = await session.get(AllUsers, t.friend_user_id)
#             if not friend:
#                 continue

#             friend.user_balance += per_account_cents
#             session.add(friend)

#             session.add(AllTransactions(
#                 user_id=friend.user_id,
#                 trans_time=now_dt,
#                 trans_ammount=per_account_cents,
#                 trans_target="wallet_topup_multi",
#                 invoice_id=invoice.invoice_id,
#             ))

#     # No tx event for topup
#     return None


# async def _process_subscription_renew(session, invoice, user_paid):
#     now_dt = datetime.now(timezone.utc)
#     now_ms = int(now_dt.timestamp() * 1000)

#     # Record payment
#     session.add(AllTransactions(
#         user_id=user_paid.user_id,
#         trans_time=now_dt,
#         trans_ammount=invoice.invoice_ammount,
#         trans_target="subscription_renew",
#         invoice_id=invoice.invoice_id,
#     ))

#     # Add money to balance
#     user_paid.user_balance += invoice.invoice_ammount
#     session.add(user_paid)

#     # Load invoice items
#     items_result = await session.execute(
#         select(InvoiceItems).where(InvoiceItems.invoice_id == invoice.invoice_id)
#     )
#     invoice_items = items_result.scalars().all()

#     if not invoice_items:
#         raise RuntimeError("No invoice_items for subscription invoice")

#     # Create SubscriptionTransaction
#     tx = SubscriptionTransaction(
#         user_id=user_paid.user_id,
#         source="invoice_processor",
#         subs_id=invoice.accounts_ammount,
#         requested_end_ts=now_ms,
#         status="pending",
#         provider_invoice_id=invoice.invoice_id,
#         payload_meta={
#             "invoice_id": invoice.invoice_id,
#             "invoice_amount": int(invoice.invoice_ammount),
#             "items": [
#                 {
#                     "acc_number": it.acc_number,
#                     "server_id": it.server_id,
#                     "price": float(it.price),
#                     "final_price": float(it.final_price),
#                 }
#                 for it in invoice_items
#             ],
#         },
#     )
#     session.add(tx)
#     await session.flush()

#     return int(tx.id)


# async def _process_single_invoice(session, invoice):
#     # Acquire advisory lock
#     got_lock = await acquire_invoice_lock(session, invoice.invoice_id)
#     if not got_lock:
#         logger.info("Invoice %s locked by another worker", invoice.invoice_id)
#         return

#     try:
#         invoice.processing_status = "processing"
#         session.add(invoice)

#         # Load payer
#         user_paid = await session.get(AllUsers, invoice.user_id, with_for_update=True)
#         if not user_paid:
#             raise RuntimeError("User not found")

#         if invoice.invoice_target == "wallet_topup_multi":
#             await _process_wallet_topup_multi(session, invoice, user_paid)
#             invoice.processing_status = "completed"
#             return

#         if invoice.invoice_target == "subscription_renew":
#             tx_id = await _process_subscription_renew(session, invoice, user_paid)
#             invoice.processing_status = "completed"

#             # Emit tx event
#             await create_pg_event("tx", {"tx_id": tx_id}, session=session)
#             return

#         raise RuntimeError(f"Unknown invoice_target: {invoice.invoice_target}")

#     except Exception:
#         invoice.processing_status = "error"
#         logger.exception("Failed to process invoice %s", invoice.invoice_id)

#     finally:
#         await release_invoice_lock(session, invoice.invoice_id)


# async def _process_pending_invoices():
#     async with SessionLocal() as session:
#         async with session.begin():
#             invoices = await _fetch_invoices_to_process(session)
#             for inv in invoices:
#                 await _process_single_invoice(session, inv)


# async def invoice_processor():
#     logger.info("Invoice processor started")

#     while True:
#         try:
#             try:
#                 await asyncio.wait_for(invoice_event.wait(), timeout=5)
#             except asyncio.TimeoutError:
#                 pass

#             invoice_event.clear()
#             await _process_pending_invoices()

#         except Exception:
#             logger.exception("invoice_processor failed")
#             await asyncio.sleep(5)
