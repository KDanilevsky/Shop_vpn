# invoice_processor.py
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import and_, select

from db.async_db import SessionLocal
from db.models import (
    AllInvoices,
    AllTransactions,
    AllUsers,
    InvoiceItems,
    InvoiceTopupTargets,
    SubscriptionTransaction,
)
from services.events import create_pg_event
from services.heartbeat import heartbeat
from utils.advisory_locks import acquire_invoice_lock, release_invoice_lock

logger = logging.LoggerAdapter(logging.getLogger(__name__), {"worker": "invoice_processor"})
invoice_event = asyncio.Event()


async def _fetch_invoices_to_process(session):
    result = await session.execute(
        select(AllInvoices)
        .where(
            (
                (AllInvoices.invoice_status == "paid")
                & AllInvoices.processing_status.in_(["pending", "error"])
            )
            | (
                (AllInvoices.invoice_status == "pending")
                & (AllInvoices.invoice_source == "internal_balance")
                & AllInvoices.processing_status.in_(["pending", "error"])
            )
        )
        .with_for_update(skip_locked=True)
    )
    return result.scalars().all()


async def _has_tx_with_target(session, invoice_id: str, target: str) -> bool:
    result = await session.execute(
        select(AllTransactions.id).where(
            and_(
                AllTransactions.invoice_id == invoice_id,
                AllTransactions.trans_target == target,
            )
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _load_invoice_for_update(session, invoice_id: str):
    result = await session.execute(
        select(AllInvoices)
        .where(AllInvoices.invoice_id == invoice_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def _load_invoice_items(session, invoice_id: str):
    result = await session.execute(
        select(InvoiceItems).where(InvoiceItems.invoice_id == invoice_id)
    )
    items = result.scalars().all()
    if not items:
        raise RuntimeError("No invoice_items for subscription invoice")
    return items


def _calc_subscription_cost(items):
    return sum(int(item.final_price) for item in items)


async def _create_subscription_tx(session, invoice, user, items, subs_cost):
    # provider_invoice_id is unique, so this is the durable idempotency key.
    result = await session.execute(
        select(SubscriptionTransaction)
        .where(SubscriptionTransaction.provider_invoice_id == invoice.invoice_id)
        .with_for_update()
    )
    existing = result.scalar_one_or_none()
    if existing:
        return int(existing.id)

    tx = SubscriptionTransaction(
        user_id=user.user_id,
        source="invoice_processor",
        subs_id=invoice.accounts_ammount or 1,
        requested_end_ts=int(datetime.now(timezone.utc).timestamp() * 1000),
        status="pending",
        provider_invoice_id=invoice.invoice_id,
        amount=subs_cost,
        frozen_amount=subs_cost,
        payload_meta={
            "invoice_id": invoice.invoice_id,
            "tariff_id": invoice.tariff_id,  # ДОБАВЛЕНО: передаем ID тарифа для provision.py
            "invoice_amount": int(invoice.invoice_ammount or 0),
            "subscription_cost": subs_cost,
            "items": [
                {
                    "acc_number": item.acc_number,
                    "server_country_id": item.server_country_id,
                    "price": float(item.price),
                    "final_price": float(item.final_price),
                }
                for item in items
            ],
        },
    )

    session.add(tx)
    await session.flush()
    return int(tx.id)


async def _process_single_invoice(session, candidate):
    invoice_id = candidate.invoice_id
    if not await acquire_invoice_lock(session, invoice_id):
        return

    try:
        invoice = await _load_invoice_for_update(session, invoice_id)
        if not invoice or invoice.processing_status not in ("pending", "error"):
            return

        invoice.processing_status = "processing"
        user_result = await session.execute(
            select(AllUsers)
            .where(AllUsers.user_id == invoice.user_id)
            .with_for_update()
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise RuntimeError("User not found")

        if invoice.invoice_target == "wallet_topup_multi":
            if not await _has_tx_with_target(session, invoice_id, "wallet_topup_multi"):
                targets_result = await session.execute(
                    select(InvoiceTopupTargets).where(
                        InvoiceTopupTargets.invoice_id == invoice_id
                    )
                )
                targets = targets_result.scalars().all()
                if not targets:
                    raise RuntimeError("No topup targets found")
                amount = int(invoice.invoice_ammount) // len(targets)

                remainder = int(invoice.invoice_ammount) % len(targets)
                for idx, target in enumerate(targets):
                    recipient = user if target.target_type == "self" else await session.get(
                        AllUsers, target.friend_user_id, with_for_update=True
                    )
                    if recipient:
                        recipient.user_balance = (recipient.user_balance or 0) + amount
                        if idx == 0:
                            recipient.user_balance = (recipient.user_balance or 0) + remainder
                        session.add(AllTransactions(
                            user_id=recipient.user_id,
                            trans_time=datetime.now(timezone.utc),
                            trans_ammount=amount,
                            trans_target="wallet_topup_multi",
                            invoice_id=invoice_id,
                        ))
            invoice.processing_status = "completed"
            return

        if invoice.invoice_target not in ("subscription_renew", "subscription_renew_internal"):
            raise RuntimeError(f"Unknown invoice_target: {invoice.invoice_target}")

        items = await _load_invoice_items(session, invoice_id)
        subs_cost = _calc_subscription_cost(items)
        if not await _has_tx_with_target(session, invoice_id, "subscription_cost"):
            if (user.user_balance or 0) < subs_cost:
                raise RuntimeError("Insufficient balance for subscription cost")
            user.user_balance = (user.user_balance or 0) - subs_cost
            session.add(AllTransactions(
                user_id=user.user_id,
                trans_time=datetime.now(timezone.utc),
                trans_ammount=-subs_cost,
                trans_target="subscription_cost",
                invoice_id=invoice_id,
            ))

        if invoice.invoice_status != "paid":
            invoice.invoice_status = "paid"
            invoice.invoice_updated_at = datetime.now(timezone.utc)

        tx_id = await _create_subscription_tx(session, invoice, user, items, subs_cost)
        invoice.subscription_tx_id = tx_id
        invoice.processing_status = "waiting_tx"
        await create_pg_event("tx", {"tx_id": tx_id}, session=session)
    except Exception:
        invoice.processing_status = "error"
        logger.exception("Failed to process invoice %s", invoice_id)
    finally:
        await release_invoice_lock(session, invoice_id)


async def _process_pending_invoices():
    async with SessionLocal() as session:
        async with session.begin():
            for invoice in await _fetch_invoices_to_process(session):
                await _process_single_invoice(session, invoice)


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
