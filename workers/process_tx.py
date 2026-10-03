# workers/process_tx.py v13 (aligned with new billing pipeline)

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import os
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from db.async_db import SessionLocal
from db.models import (
    UserSubscription,
    SubscriptionTransaction,
    AllUsers,
    AllInvoices,
    InvoiceItems,
    AllTransactions,
)
from services.provision import provision_subscription_for_user
from services.exceptions import ProvisioningError, NoServerAvailableError
from services.notifications import (
    send_user_settings_string_and_qr_code_then_del_qr,
    send_message_to_user,
)
from utils.advisory_locks import acquire_tx_lock, release_tx_lock
from config import FIRST_USER_IN_DB, STANDART_PARTNER_PROCENT, DISCOUNT_BASE_PROCENTS

logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {"worker": "process_tx"})

ADMIN_USER_ID = FIRST_USER_IN_DB

PROVISION_CALL_TIMEOUT = 60
PROVISION_CONCURRENCY = 10
PROVISION_RATE_PER_SECOND = 5

MAX_RETRIES = 6
BASE_BACKOFF_SECONDS = 60
NO_SERVER_BASE_MULTIPLIER = 8


class RateLimiter:
    def __init__(self, rate: float, capacity: int):
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last
            refill = elapsed * self._rate
            if refill > 0:
                self._tokens = min(self._capacity, self._tokens + refill)
                self._last = now
            if self._tokens >= 1:
                self._tokens -= 1
                return
            needed = (1 - self._tokens) / self._rate
        await asyncio.sleep(needed)
        await self.acquire()


_provision_semaphore = asyncio.Semaphore(PROVISION_CONCURRENCY)
_provision_rate_limiter = RateLimiter(
    rate=PROVISION_RATE_PER_SECOND,
    capacity=PROVISION_RATE_PER_SECOND,
)


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _compute_next_run_for_transient(attempts: int) -> datetime:
    backoff = BASE_BACKOFF_SECONDS * (2 ** max(attempts - 1, 0))
    backoff = min(backoff, 24 * 3600)
    return _now_dt() + timedelta(seconds=backoff)


def _compute_next_run_for_no_server(attempts: int) -> datetime:
    base = BASE_BACKOFF_SECONDS * NO_SERVER_BASE_MULTIPLIER
    backoff = base * (2 ** max(attempts - 1, 0))
    backoff = min(backoff, 7 * 24 * 3600)
    return _now_dt() + timedelta(seconds=backoff)


async def process_tx(tx_id: int) -> None:
    """
    v13:
    - NO balance deduction here (invoice_processor already did it)
    - tx.frozen_amount is set by invoice_processor
    - On success: split frozen_amount to admin/partner, set to 0
    - On permanent failure: refund frozen_amount to user with metadata
    - On retryable failure: keep frozen_amount, schedule retry
    """
    logger.info("process_tx start tx=%s", tx_id)

    # ============================================================
    # 1. Acquire advisory lock (GLOBAL mutex for tx_id)
    # ============================================================
    try:
        async with SessionLocal() as lock_session:
            async with lock_session.begin():
                got_lock = await acquire_tx_lock(lock_session, tx_id)

        if not got_lock:
            logger.info("tx %s locked by another worker, skipping", tx_id)
            return

    except Exception:
        logger.exception("Failed to acquire advisory lock for tx %s", tx_id)
        return

    invoice_id = None
    provision_success = False
    provision_result: Optional[Dict[str, Any]] = None
    no_server_flag = False

    # ============================================================
    # 2. Claim tx, load invoice/items/user (NO money ops here)
    # ============================================================
    try:
        async with SessionLocal() as session:
            async with session.begin():
                r_tx = await session.execute(
                    select(SubscriptionTransaction)
                    .where(SubscriptionTransaction.id == tx_id)
                    .with_for_update()
                )
                tx = r_tx.scalar_one_or_none()
                if not tx:
                    logger.warning("tx %s not found", tx_id)
                    return

                if tx.status == "completed":
                    logger.info("tx %s already completed", tx_id)
                    return

                if tx.status not in ("pending", "failed_retryable", "in_progress"):
                    logger.warning("tx %s in invalid state %s", tx_id, tx.status)
                    return

                tx.status = "in_progress"
                tx.attempts = (tx.attempts or 0) + 1
                tx.error = None

                if not tx.provider_invoice_id:
                    tx.status = "failed_permanent"
                    tx.error = "no_provider_invoice_id"
                    await session.flush()
                    return

                invoice_id = tx.provider_invoice_id

                r_inv = await session.execute(
                    select(AllInvoices).where(AllInvoices.invoice_id == invoice_id)
                )
                invoice = r_inv.scalar_one_or_none()
                if not invoice:
                    tx.status = "failed_permanent"
                    tx.error = "invoice_not_found"
                    await session.flush()
                    return

                r_items = await session.execute(
                    select(InvoiceItems).where(InvoiceItems.invoice_id == invoice_id)
                )
                items = r_items.scalars().all()
                if not items:
                    tx.status = "failed_permanent"
                    tx.error = "no_invoice_items"
                    await session.flush()
                    return

                r_user = await session.execute(
                    select(AllUsers)
                    .where(AllUsers.user_id == invoice.user_id)
                    .with_for_update()
                )
                user = r_user.scalar_one_or_none()
                if not user:
                    tx.status = "failed_permanent"
                    tx.error = "payer_not_found"
                    await session.flush()
                    return

                inviter = None
                if getattr(user, "user_id_who_invited", None):
                    r_inviter = await session.execute(
                        select(AllUsers)
                        .where(AllUsers.user_id == user.user_id_who_invited)
                        .with_for_update()
                    )
                    inviter = r_inviter.scalar_one_or_none()

                total_price_cents = sum(int(it.final_price) for it in items)
                logger.info(
                    "tx %s claimed: invoice=%s user=%s total_price_cents=%s frozen_amount=%s",
                    tx_id,
                    invoice_id,
                    user.user_id,
                    total_price_cents,
                    tx.frozen_amount,
                )

                await session.flush()

    except SQLAlchemyError:
        logger.exception("database error while claiming tx %s", tx_id)
        return
    except Exception:
        logger.exception("unexpected error while claiming tx %s", tx_id)
        return

    # ============================================================
    # 3. Call provisioner (no DB here)
    # ============================================================
    await _provision_rate_limiter.acquire()
    async with _provision_semaphore:
        try:
            logger.info("Calling provision_subscription_for_user for tx %s", tx_id)
            result = await asyncio.wait_for(
                provision_subscription_for_user(tx_id),
                timeout=PROVISION_CALL_TIMEOUT,
            )
            provision_success = True
            provision_result = result or {}
            logger.info("Provision succeeded for tx %s result=%s", tx_id, provision_result)
        except asyncio.TimeoutError:
            provision_success = False
            provision_result = {"error": "provision_timeout"}
            logger.warning("Provision timeout for tx %s", tx_id)
        except NoServerAvailableError as nse:
            provision_success = False
            no_server_flag = True
            server_id = getattr(nse, "server_id", None)
            server_country = getattr(nse, "server_country", None)
            text = f"No free servers for tx {tx_id}. server_id={server_id}, country={server_country}"
            try:
                await send_message_to_user(ADMIN_USER_ID, text)
            except Exception:
                logger.exception("Failed to notify admin about no server for tx %s", tx_id)
            provision_result = {
                "error": "no_server_available",
                "server_id": server_id,
                "server_country": server_country,
            }
            logger.warning(
                "NoServerAvailable for tx %s server=%s country=%s",
                tx_id,
                server_id,
                server_country,
            )
        except ProvisioningError as pe:
            provision_success = False
            provision_result = {"error": "provisioning_error", "detail": str(pe)}
            logger.exception("ProvisioningError for tx %s: %s", tx_id, pe)
        except Exception as exc:
            provision_success = False
            provision_result = {"error": "unexpected", "detail": str(exc)}
            logger.exception("Unexpected exception while provisioning tx %s: %s", tx_id, exc)

    # ============================================================
    # 4. Finalize: split or refund frozen_amount
    # ============================================================
    try:
        async with SessionLocal() as session2:
            async with session2.begin():
                r_tx2 = await session2.execute(
                    select(SubscriptionTransaction)
                    .where(SubscriptionTransaction.id == tx_id)
                    .with_for_update()
                )
                tx2 = r_tx2.scalar_one_or_none()
                if not tx2:
                    logger.error("tx %s disappeared during finalize", tx_id)
                    return

                r_user2 = await session2.execute(
                    select(AllUsers)
                    .where(AllUsers.user_id == tx2.user_id)
                    .with_for_update()
                )
                user2 = r_user2.scalar_one_or_none()
                if not user2:
                    tx2.status = "failed_permanent"
                    tx2.error = "payer_not_found_finalize"
                    await session2.flush()
                    return

                inviter2 = None
                if getattr(user2, "user_id_who_invited", None):
                    r_inviter2 = await session2.execute(
                        select(AllUsers)
                        .where(AllUsers.user_id == user2.user_id_who_invited)
                        .with_for_update()
                    )
                    inviter2 = r_inviter2.scalar_one_or_none()

                frozen_cents = int(tx2.frozen_amount or 0)

                # Load invoice + items again for metadata (for refunds, logging)
                r_inv2 = await session2.execute(
                    select(AllInvoices).where(AllInvoices.invoice_id == tx2.provider_invoice_id)
                )
                invoice2 = r_inv2.scalar_one_or_none()

                r_items2 = await session2.execute(
                    select(InvoiceItems).where(InvoiceItems.invoice_id == tx2.provider_invoice_id)
                )
                items2 = r_items2.scalars().all()

                if provision_success:
                    # --- CHAST' 1: OBNOVLENIE i DOBAVLENIE SLOTOV V SUBD ---
                    slots = provision_result.get("slots") or {}
                    for slot_str, info in slots.items():
                        acc_num = int(slot_str)
                        existing_sub = await session2.execute(
                            select(UserSubscription).where(
                                UserSubscription.user_id == tx2.user_id,
                                UserSubscription.acc_number == acc_num
                            )
                        )
                        sub_obj = existing_sub.scalar_one_or_none()
                        if sub_obj:
                            sub_obj.tariff_id = tx2.payload_meta.get("tariff_id")
                            sub_obj.stop_time = info.get("stop_time")
                            sub_obj.is_active = True
                            sub_obj.gb_limit = tx2.payload_meta.get("gb_limit", 0)
                            sub_obj.device_limit = tx2.payload_meta.get("device_limit", 1)
                        else:
                            sub_obj = UserSubscription(
                                user_id=tx2.user_id,
                                acc_number=acc_num,
                                tariff_id=tx2.payload_meta.get("tariff_id"),
                                sub_id=info.get("sub_id_token"),       # Novyj UUID dlya 3x-ui link
                                client_uuid=info.get("client_uuid"),   # ID klienta v Xray
                                gb_limit=tx2.payload_meta.get("gb_limit", 0),
                                device_limit=tx2.payload_meta.get("device_limit", 1),
                                start_time=_now_dt(),
                                stop_time=info.get("stop_time"),
                                is_active=True
                            )
                            session2.add(sub_obj)

                    tx2.payload_meta = {
                        **tx2.payload_meta,
                        "subscription_links": {k: v["settings_string"] for k, v in slots.items()}
                    }

                    # --- CHAST' 2: FINANSOVAY LOGIKA I RASCHET PARTNERKI (VASH ORIGINAL'NYJ KOD) ---
                    frozen_cents = int(tx2.frozen_amount or 0)
                    if frozen_cents <= 0:
                        tx2.status = "completed"
                        tx2.error = None
                        tx2.updated_at = _now_dt()
                        await session2.flush()
                        logger.info("tx %s completed with zero frozen amount", tx_id)
                    else:
                        inviter_share = 0
                        partner_share = 0
                        admin_share = frozen_cents

                        if inviter2 and DISCOUNT_BASE_PROCENTS and DISCOUNT_BASE_PROCENTS > 0:
                            inviter_share = int(round((frozen_cents * float(DISCOUNT_BASE_PROCENTS)) / 100.0))
                            admin_share = admin_share - inviter_share

                        if inviter2 and STANDART_PARTNER_PROCENT and STANDART_PARTNER_PROCENT > 0  and inviter2.is_partner is True:
                            partner_share = int(round((frozen_cents * float(STANDART_PARTNER_PROCENT)) / 100.0))
                            admin_share = admin_share - partner_share

                        r_admin = await session2.execute(
                            select(AllUsers)
                            .where(AllUsers.user_id == ADMIN_USER_ID)
                            .with_for_update()
                        )
                        admin = r_admin.scalar_one_or_none()

                        if admin_share > 0 and admin:
                            admin.user_balance = (admin.user_balance or 0) + admin_share
                            session2.add(admin)
                            admin_tx = AllTransactions(
                                user_id=ADMIN_USER_ID,
                                trans_time=int(_now_dt().timestamp() * 1000),
                                trans_ammount=admin_share,
                                trans_target="settle_subscription_admin",
                            )
                            session2.add(admin_tx)

                        if inviter_share > 0 and inviter2:
                            inviter2.user_balance = (inviter2.user_balance or 0) + inviter_share
                            inviter2.quantity_guests_paid = (inviter2.quantity_guests_paid or 0) + 1
                            session2.add(inviter2)
                            inviter_tx = AllTransactions(
                                user_id=inviter2.user_id,
                                trans_time=int(_now_dt().timestamp() * 1000),
                                trans_ammount=inviter_share,
                                trans_target="inviter_payout_on_activation",
                            )
                            session2.add(inviter_tx)

                        if partner_share > 0 and inviter2:
                            inviter2.partner_balance = (inviter2.partner_balance or 0) + partner_share
                            # inviter2.quantity_guests_paid = (inviter2.quantity_guests_paid or 0) + 1
                            session2.add(inviter2)
                            partner_tx = AllTransactions(
                                user_id=inviter2.user_id,
                                trans_time=int(_now_dt().timestamp() * 1000),
                                trans_ammount=partner_share,
                                trans_target="partner_payout_on_activation",
                            )
                            session2.add(partner_tx)

                        tx2.frozen_amount = 0
                        tx2.status = "completed"
                        tx2.error = None
                        tx2.updated_at = _now_dt()
                        await session2.flush()

                    # --- CHAST' 3: UPRAVLENIE NOTIFIKACIYAMI POL'ZOVATELYAM ---
                    try:
                        for slot_str, info in slots.items():
                            settings_string = info.get("settings_string")
                            if settings_string:
                                # Otpravlyaem chistyj tekst s ssylkoj podpiski vmesto kartinki
                                text = f"Vasha podpiska dlya Slota #{slot_str} aktivirovana!\n\nSsylka dlya importa v prilozhenie:\n<code>{settings_string}</code>"
                                asyncio.create_task(send_message_to_user(user2.user_id, text))
                        if not slots:
                            text = "Ваша подписка активирована."
                            asyncio.create_task(send_message_to_user(user2.user_id, text))
                    except Exception:
                        logger.exception("Failed to schedule user notifications for tx %s", tx_id)

                    logger.info("tx %s completed, frozen=%s", tx_id, frozen_cents)


                else:
                    # FAILURE: decide retry vs permanent, refund only on permanent
                    tx2.error = str(provision_result)[:1000] if provision_result else "unknown_error"
                    tx2.updated_at = _now_dt()

                    attempts = tx2.attempts or 1
                    if attempts >= MAX_RETRIES:
                        # Permanent failure: refund frozen_amount with metadata
                        if frozen_cents > 0:
                            user2.user_balance = (user2.user_balance or 0) + frozen_cents
                            tx2.frozen_amount = 0
                            session2.add(user2)

                            refund_meta = []
                            for it in items2 or []:
                                refund_meta.append(
                                    {
                                        "acc_number": it.acc_number,
                                        "server_country_id": getattr(it, "server_country_id", None),
                                    }
                                )

                            refund_tx = AllTransactions(
                                user_id=user2.user_id,
                                trans_time=int(_now_dt().timestamp() * 1000),
                                trans_ammount=frozen_cents,
                                trans_target="subscription_refund",
                            )
                            session2.add(refund_tx)

                        # --- QR cleanup on permanent failure ---
                        # for it in items2:
                        #     slot = it.acc_number

                        #     r_sub = await session2.execute(
                        #         select(UserSubscription).where(
                        #             UserSubscription.user_id == user2.user_id,
                        #             UserSubscription.slot_number == slot,
                        #         )
                        #     )
                        #     sub = r_sub.scalar_one_or_none()
                        #     if not sub:
                        #         continue

                        #     # Delete QR file if exists
                        #     if sub.qr_path and os.path.exists(sub.qr_path):
                        #         try:
                        #             os.remove(sub.qr_path)
                        #             logger.info("Deleted QR %s due to permanent failure", sub.qr_path)
                        #         except Exception:
                        #             logger.exception("Failed to delete QR %s on refund", sub.qr_path)

                        #     # Clear subscription QR fields
                        #     sub.qr_path = None
                        #     sub.settings_string = None
                        #     session2.add(sub)

                        tx2.status = "failed_permanent"
                        await session2.flush()
                        logger.warning("tx %s reached max retries, marked failed_permanent", tx_id)

                    else:
                        # Retryable failure: keep frozen_amount, schedule retry
                        tx2.status = "failed_retryable"
                        if no_server_flag:
                            tx2.next_run_at = _compute_next_run_for_no_server(attempts)
                        else:
                            tx2.next_run_at = _compute_next_run_for_transient(attempts)
                        await session2.flush()
                        logger.warning(
                            "tx %s marked failed_retryable (no_server=%s), next_run_at=%s",
                            tx_id,
                            no_server_flag,
                            tx2.next_run_at,
                        )

    except SQLAlchemyError:
        logger.exception("database error while finalizing tx %s", tx_id)
    except Exception:
        logger.exception("unexpected error while finalizing tx %s", tx_id)

    finally:
        # ============================================================
        # 5. ALWAYS release advisory lock
        # ============================================================
        try:
            async with SessionLocal() as unlock_session:
                async with unlock_session.begin():
                    await release_tx_lock(unlock_session, tx_id)
        except Exception:
            logger.exception("Failed to release advisory lock for tx %s", tx_id)


# # workers/process_tx.py v12

# import asyncio
# import logging
# from datetime import datetime, timezone, timedelta
# from typing import Optional, Dict, Any

# from sqlalchemy import select
# from sqlalchemy.exc import SQLAlchemyError

# from db.async_db import SessionLocal
# from db.models import (
#     SubscriptionTransaction,
#     AllUsers,
#     AllInvoices,
#     InvoiceItems,
#     AllTransactions,
# )
# from services.provision import provision_subscription_for_user
# from services.exceptions import ProvisioningError, NoServerAvailableError
# from services.notifications import (
#     send_user_settings_string_and_qr_code_then_del_qr,
#     send_message_to_user,
# )
# from utils.advisory_locks import acquire_tx_lock, release_tx_lock
# from config import FIRST_USER_IN_DB, STANDART_PARTNER_PROCENT

# logger = logging.getLogger(__name__)

# ADMIN_USER_ID = FIRST_USER_IN_DB

# PROVISION_CALL_TIMEOUT = 60
# PROVISION_CONCURRENCY = 10
# PROVISION_RATE_PER_SECOND = 5

# MAX_RETRIES = 6
# BASE_BACKOFF_SECONDS = 60
# NO_SERVER_BASE_MULTIPLIER = 8


# class RateLimiter:
#     def __init__(self, rate: float, capacity: int):
#         self._rate = rate
#         self._capacity = capacity
#         self._tokens = capacity
#         self._last = asyncio.get_event_loop().time()
#         self._lock = asyncio.Lock()

#     async def acquire(self):
#         async with self._lock:
#             now = asyncio.get_event_loop().time()
#             elapsed = now - self._last
#             refill = elapsed * self._rate
#             if refill > 0:
#                 self._tokens = min(self._capacity, self._tokens + refill)
#                 self._last = now
#             if self._tokens >= 1:
#                 self._tokens -= 1
#                 return
#             needed = (1 - self._tokens) / self._rate
#         await asyncio.sleep(needed)
#         await self.acquire()


# _provision_semaphore = asyncio.Semaphore(PROVISION_CONCURRENCY)
# _provision_rate_limiter = RateLimiter(rate=PROVISION_RATE_PER_SECOND, capacity=PROVISION_RATE_PER_SECOND)


# def _now_dt() -> datetime:
#     return datetime.now(timezone.utc)


# def _compute_next_run_for_transient(attempts: int) -> datetime:
#     backoff = BASE_BACKOFF_SECONDS * (2 ** max(attempts - 1, 0))
#     backoff = min(backoff, 24 * 3600)
#     return _now_dt() + timedelta(seconds=backoff)


# def _compute_next_run_for_no_server(attempts: int) -> datetime:
#     base = BASE_BACKOFF_SECONDS * NO_SERVER_BASE_MULTIPLIER
#     backoff = base * (2 ** max(attempts - 1, 0))
#     backoff = min(backoff, 7 * 24 * 3600)
#     return _now_dt() + timedelta(seconds=backoff)


# async def process_tx(tx_id: int) -> None:
#     """
#     v12:
#     - same as v10, but:
#       - tolerant to tx.payload_meta["source"] (manual/autorenew/etc.)
#       - logic unchanged for money: freeze → provision → split/refund
#     """
#     logger.info("process_tx start tx=%s", tx_id)

#     # ============================================================
#     # 1. Acquire advisory lock (GLOBAL mutex for tx_id)
#     # ============================================================
#     try:
#         async with SessionLocal() as lock_session:
#             async with lock_session.begin():
#                 got_lock = await acquire_tx_lock(lock_session, tx_id)

#         if not got_lock:
#             logger.info("tx %s locked by another worker, skipping", tx_id)
#             return

#     except Exception:
#         logger.exception("Failed to acquire advisory lock for tx %s", tx_id)
#         return

#     # ============================================================
#     # 2. Main processing logic (unchanged)
#     # ============================================================

#     invoice_id = None
#     provision_success = False
#     provision_result: Optional[Dict[str, Any]] = None
#     no_server_flag = False

#     try:
#         async with SessionLocal() as session:
#             async with session.begin():
#                 r_tx = await session.execute(
#                     select(SubscriptionTransaction)
#                     .where(SubscriptionTransaction.id == tx_id)
#                     .with_for_update()
#                 )
#                 tx = r_tx.scalar_one_or_none()
#                 if not tx:
#                     logger.warning("tx %s not found", tx_id)
#                     return

#                 if tx.status == "completed":
#                     logger.info("tx %s already completed", tx_id)
#                     return

#                 if tx.status not in ("pending", "failed_retryable", "in_progress"):
#                     logger.warning("tx %s in invalid state %s", tx_id, tx.status)
#                     return

#                 tx.status = "in_progress"
#                 tx.attempts = (tx.attempts or 0) + 1
#                 tx.error = None

#                 if not tx.provider_invoice_id:
#                     tx.status = "failed_permanent"
#                     tx.error = "no_provider_invoice_id"
#                     await session.flush()
#                     return

#                 invoice_id = tx.provider_invoice_id

#                 r_inv = await session.execute(
#                     select(AllInvoices).where(AllInvoices.invoice_id == invoice_id)
#                 )
#                 invoice = r_inv.scalar_one_or_none()
#                 if not invoice:
#                     tx.status = "failed_permanent"
#                     tx.error = "invoice_not_found"
#                     await session.flush()
#                     return

#                 r_items = await session.execute(
#                     select(InvoiceItems).where(InvoiceItems.invoice_id == invoice_id)
#                 )
#                 items = r_items.scalars().all()
#                 if not items:
#                     tx.status = "failed_permanent"
#                     tx.error = "no_invoice_items"
#                     await session.flush()
#                     return

#                 r_user = await session.execute(
#                     select(AllUsers)
#                     .where(AllUsers.user_id == invoice.user_id)
#                     .with_for_update()
#                 )
#                 user = r_user.scalar_one_or_none()
#                 if not user:
#                     tx.status = "failed_permanent"
#                     tx.error = "payer_not_found"
#                     await session.flush()
#                     return

#                 inviter = None
#                 if getattr(user, "user_id_who_invited", None):
#                     r_inviter = await session.execute(
#                         select(AllUsers)
#                         .where(AllUsers.user_id == user.user_id_who_invited)
#                         .with_for_update()
#                     )
#                     inviter = r_inviter.scalar_one_or_none()

#                 total_price_cents = sum(int(it.final_price) for it in items)

#                 if (user.user_balance or 0) < total_price_cents:
#                     tx.status = "failed_retryable"
#                     tx.error = "insufficient_balance_before_provision"
#                     tx.next_run_at = _compute_next_run_for_transient(tx.attempts or 1)
#                     await session.flush()
#                     logger.warning(
#                         "tx %s insufficient balance before provision: balance=%s needed=%s",
#                         tx_id,
#                         user.user_balance,
#                         total_price_cents,
#                     )
#                     return

#                 user.user_balance = (user.user_balance or 0) - total_price_cents
#                 tx.frozen_amount = total_price_cents

#                 await session.flush()

#     except SQLAlchemyError:
#         logger.exception("database error while claiming/freezing tx %s", tx_id)
#         return
#     except Exception:
#         logger.exception("unexpected error while claiming/freezing tx %s", tx_id)
#         return

#     await _provision_rate_limiter.acquire()
#     async with _provision_semaphore:
#         try:
#             logger.info("Calling provision_subscription_for_user for tx %s", tx_id)
#             result = await asyncio.wait_for(
#                 provision_subscription_for_user(tx_id),
#                 timeout=PROVISION_CALL_TIMEOUT,
#             )
#             provision_success = True
#             provision_result = result or {}
#             logger.info("Provision succeeded for tx %s result=%s", tx_id, provision_result)
#         except asyncio.TimeoutError:
#             provision_success = False
#             provision_result = {"error": "provision_timeout"}
#             logger.warning("Provision timeout for tx %s", tx_id)
#         except NoServerAvailableError as nse:
#             provision_success = False
#             no_server_flag = True
#             server_id = getattr(nse, "server_id", None)
#             server_country = getattr(nse, "server_country", None)
#             text = f"No free servers for tx {tx_id}. server_id={server_id}, country={server_country}"
#             try:
#                 await send_message_to_user(ADMIN_USER_ID, text)
#             except Exception:
#                 logger.exception("Failed to notify admin about no server for tx %s", tx_id)
#             provision_result = {
#                 "error": "no_server_available",
#                 "server_id": server_id,
#                 "server_country": server_country,
#             }
#             logger.warning("NoServerAvailable for tx %s server=%s country=%s", tx_id, server_id, server_country)
#         except ProvisioningError as pe:
#             provision_success = False
#             provision_result = {"error": "provisioning_error", "detail": str(pe)}
#             logger.exception("ProvisioningError for tx %s: %s", tx_id, pe)
#         except Exception as exc:
#             provision_success = False
#             provision_result = {"error": "unexpected", "detail": str(exc)}
#             logger.exception("Unexpected exception while provisioning tx %s: %s", tx_id, exc)

#     try:
#         async with SessionLocal() as session2:
#             async with session2.begin():
#                 r_tx2 = await session2.execute(
#                     select(SubscriptionTransaction)
#                     .where(SubscriptionTransaction.id == tx_id)
#                     .with_for_update()
#                 )
#                 tx2 = r_tx2.scalar_one_or_none()
#                 if not tx2:
#                     logger.error("tx %s disappeared during finalize", tx_id)
#                     return

#                 r_user2 = await session2.execute(
#                     select(AllUsers)
#                     .where(AllUsers.user_id == tx2.user_id)
#                     .with_for_update()
#                 )
#                 user2 = r_user2.scalar_one_or_none()
#                 if not user2:
#                     tx2.status = "failed_permanent"
#                     tx2.error = "payer_not_found_finalize"
#                     await session2.flush()
#                     return

#                 inviter2 = None
#                 if getattr(user2, "user_id_who_invited", None):
#                     r_inviter2 = await session2.execute(
#                         select(AllUsers)
#                         .where(AllUsers.user_id == user2.user_id_who_invited)
#                         .with_for_update()
#                     )
#                     inviter2 = r_inviter2.scalar_one_or_none()

#                 frozen_cents = int(tx2.frozen_amount or 0)

#                 if provision_success:
#                     if frozen_cents <= 0:
#                         tx2.status = "completed"
#                         tx2.error = None
#                         tx2.updated_at = _now_dt()
#                         await session2.flush()
#                         logger.info("tx %s completed with zero frozen amount", tx_id)
#                     else:
#                         partner_share = 0
#                         admin_share = frozen_cents

#                         if inviter2 and STANDART_PARTNER_PROCENT and STANDART_PARTNER_PROCENT > 0:
#                             partner_share = frozen_cents * int(STANDART_PARTNER_PROCENT) // 100
#                             admin_share = frozen_cents - partner_share

#                         r_admin = await session2.execute(
#                             select(AllUsers)
#                             .where(AllUsers.user_id == ADMIN_USER_ID)
#                             .with_for_update()
#                         )
#                         admin = r_admin.scalar_one_or_none()

#                         if admin_share > 0 and admin:
#                             admin.user_balance = (admin.user_balance or 0) + admin_share
#                             session2.add(admin)
#                             admin_tx = AllTransactions(
#                                 user_id=ADMIN_USER_ID,
#                                 trans_time=int(_now_dt().timestamp() * 1000),
#                                 trans_ammount=admin_share,
#                                 trans_target="settle_subscription_admin",
#                             )
#                             session2.add(admin_tx)

#                         if partner_share > 0 and inviter2:
#                             inviter2.partner_balance = (inviter2.partner_balance or 0) + partner_share
#                             inviter2.quantity_guests_paid = (inviter2.quantity_guests_paid or 0) + 1
#                             session2.add(inviter2)
#                             partner_tx = AllTransactions(
#                                 user_id=inviter2.user_id,
#                                 trans_time=int(_now_dt().timestamp() * 1000),
#                                 trans_ammount=partner_share,
#                                 trans_target="partner_payout_on_activation",
#                             )
#                             session2.add(partner_tx)

#                         tx2.frozen_amount = 0
#                         tx2.status = "completed"
#                         tx2.error = None
#                         tx2.updated_at = _now_dt()
#                         await session2.flush()

#                     slots = {}
#                     if isinstance(provision_result, dict):
#                         slots = provision_result.get("slots") or {}

#                     try:
#                         for slot_str, info in slots.items():
#                             settings_string = info.get("settings_string")
#                             img_path = info.get("img_path")
#                             if settings_string:
#                                 asyncio.create_task(
#                                     send_user_settings_string_and_qr_code_then_del_qr(
#                                         user2.user_id,
#                                         settings_string,
#                                         img_path,
#                                     )
#                                 )
#                         if not slots:
#                             text = "Ваша подписка активирована."
#                             asyncio.create_task(send_message_to_user(user2.user_id, text))
#                     except Exception:
#                         logger.exception("Failed to schedule user notifications for tx %s", tx_id)

#                     logger.info("tx %s completed, frozen=%s", tx_id, frozen_cents)

#                 else:
#                     tx2.error = str(provision_result)[:1000] if provision_result else "unknown_error"
#                     tx2.updated_at = _now_dt()

#                     if frozen_cents > 0:
#                         user2.user_balance = (user2.user_balance or 0) + frozen_cents
#                         tx2.frozen_amount = 0
#                         session2.add(user2)
#                         refund_tx = AllTransactions(
#                             user_id=user2.user_id,
#                             trans_time=int(_now_dt().timestamp() * 1000),
#                             trans_ammount=frozen_cents,
#                             trans_target="refund_on_provision_failure",
#                         )
#                         session2.add(refund_tx)

#                     attempts = tx2.attempts or 1
#                     if attempts >= MAX_RETRIES:
#                         tx2.status = "failed_permanent"
#                         await session2.flush()
#                         logger.warning("tx %s reached max retries, marked failed_permanent", tx_id)
#                     else:
#                         tx2.status = "failed_retryable"
#                         if no_server_flag:
#                             tx2.next_run_at = _compute_next_run_for_no_server(attempts)
#                         else:
#                             tx2.next_run_at = _compute_next_run_for_transient(attempts)
#                         await session2.flush()
#                         logger.warning(
#                             "tx %s marked failed_retryable (no_server=%s), next_run_at=%s",
#                             tx_id,
#                             no_server_flag,
#                             tx2.next_run_at,
#                         )

#     except SQLAlchemyError:
#         logger.exception("database error while finalizing tx %s", tx_id)
#     except Exception:
#         logger.exception("unexpected error while finalizing tx %s", tx_id)

#     finally:
#         # ============================================================
#         # 3. ALWAYS release advisory lock
#         # ============================================================
#         try:
#             async with SessionLocal() as unlock_session:
#                 async with unlock_session.begin():
#                     await release_tx_lock(unlock_session, tx_id)
#         except Exception:
#             logger.exception("Failed to release advisory lock for tx %s", tx_id)