# workers/autorenew_worker.py v15 — bundle renew, internal invoice, notifier, overlap-safe

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from db.async_db import SessionLocal
from db.models import (
    AllUsers,
    UserSubscription,
    AllInvoices,
    InvoiceItems,
    SubscriptionTransaction,
    ServerClientDeletion,
)
from services.notifications import enqueue_notification
from services.events import create_pg_event
from config import (
    UPDATED_PRICE,
    UPDATED_MIN_PAY,
    DISCOUNT_BASE_PROCENTS,
    DISCOUNT_BASE_PROCENTS_PROMO,
    BOT_SHOP_NAME,
)

from services.heartbeat import heartbeat

logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {"worker": "autorenew_worker"})


RENEW_BEFORE_HOURS = 24
GRACE_PERIOD_DAYS = 2
REMIND_BEFORE_DAYS = 5
PERIODIC_SCAN_MINUTES = 30
TARGET_HOUR_UTC = 2
TARGET_MINUTE_UTC = 0


def _now():
    return datetime.now(timezone.utc)


def _now_ms():
    return int(_now().timestamp() * 1000)


def _calc_price_for_slot(quantity_paid: int, promo_active: int) -> float:
    if promo_active == 1:
        discount_percent = DISCOUNT_BASE_PROCENTS_PROMO
        discount_amount = UPDATED_PRICE * discount_percent / 100
        return round(UPDATED_PRICE - discount_amount, 2)

    T = quantity_paid + 1
    total_discount = T * 2.5

    if total_discount >= 100:
        return 0.0

    discount_percent = total_discount
    discount_amount = UPDATED_PRICE * discount_percent / 100
    return round(UPDATED_PRICE - discount_amount, 2)


async def _create_internal_autorenew_invoice(session, user, subs, total_price_cents):
    invoice_id = f"auto_{user.user_id}_{int(_now().timestamp())}"

    inv = AllInvoices(
        invoice_id=invoice_id,
        user_id=user.user_id,
        invoice_target="subscription_autorenew_internal",
        invoice_status="pending",
        processing_status="pending",
        invoice_ammount=int(total_price_cents),
        invoice_ammount_fact=int(total_price_cents),
        invoice_created_at=_now(),
        invoice_updated_at=_now(),
    )
    session.add(inv)

    for sub in subs:
        item = InvoiceItems(
            invoice_id=invoice_id,
            acc_number=sub.slot_number,
            server_country_id=sub.server_country_id,
            server_id=sub.server_id,
            price=int(round(UPDATED_PRICE * 100)),
            final_price=int(total_price_cents),
        )
        session.add(item)

    tx = SubscriptionTransaction(
        user_id=user.user_id,
        provider_invoice_id=invoice_id,
        status="pending",
        attempts=0,
        frozen_amount=0,
        payload_meta={"source": "autorenew"},
    )
    session.add(tx)

    return invoice_id


async def _process_user(user: AllUsers):
    now = _now()
    now_ms = _now_ms()

    # --- PROMO PERIOD LOGIC ---
    promo_active = getattr(user, "user_promo_new", 0)
    promo_until = getattr(user, "user_promo_new_days", 0)
    last_notified = getattr(user, "user_promo_last_notified", 0) or 0

    # 1. Promo expired → disable + notify once
    if promo_active == 1 and now_ms > promo_until:
        async with SessionLocal() as session:
            async with session.begin():
                db_user = await session.get(AllUsers, user.user_id, with_for_update=True)
                if db_user and db_user.user_promo_new == 1:
                    db_user.user_promo_new = 0
                    session.add(db_user)

                    await enqueue_notification(
                        session=session,
                        user_id=user.user_id,
                        reason="promo_period_ended",
                        payload={
                            "promo_until": promo_until,
                        },
                    )
                    await create_pg_event("notify", session=session)
        # After disabling promo, continue with normal autorenew logic
        promo_active = 0

    # 2. Promo active → daily reminder if ending soon
    if promo_active == 1 and now_ms < promo_until:
        days_left = max(1, int((promo_until - now_ms) / (24 * 60 * 60 * 1000)))

        if days_left <= 2:
            # Notify once per day
            # last_notified stores ms timestamp of last reminder
            if now_ms - last_notified >= 24 * 60 * 60 * 1000:
                async with SessionLocal() as session:
                    async with session.begin():
                        db_user = await session.get(AllUsers, user.user_id, with_for_update=True)
                        if db_user:
                            db_user.user_promo_last_notified = now_ms
                            session.add(db_user)

                            await enqueue_notification(
                                session=session,
                                user_id=user.user_id,
                                reason="promo_period_ending_soon",
                                payload={
                                    "days_left": days_left,
                                    "promo_until": promo_until,
                                },
                            )
                            await create_pg_event("notify", session=session)


    # Lock subscriptions for this user
    async with SessionLocal() as session:
        async with session.begin():
            r = await session.execute(
                select(UserSubscription)
                .where(UserSubscription.user_id == user.user_id)
                .with_for_update(skip_locked=True)
            )
            subs = r.scalars().all()

    active_subs = []
    expired_subs = []

    for sub in subs:
        if not sub.stop_time:
            continue

        if sub.stop_time > now_ms:
            active_subs.append(sub)
        elif sub.stop_time + GRACE_PERIOD_DAYS * 86400 * 1000 > now_ms:
            expired_subs.append(sub)
        else:
            # Hard expired → delete subscription + enqueue deletion + notify
            async with SessionLocal() as session:
                async with session.begin():
                    db_sub = await session.get(UserSubscription, sub.id)
                    if db_sub:
                        deletion = ServerClientDeletion(
                            user_id=user.user_id,
                            slot_number=sub.slot_number,
                            server_id=sub.server_id,
                            client_email=f"{user.user_id}-slot{sub.slot_number}",
                            delete_not_before_ts=sub.stop_time,
                        )
                        session.add(deletion)

                        db_sub.server_id = None
                        db_sub.next_server_id = 0
                        db_sub.pending = False
                        db_sub.stop_time = None
                        db_sub.settings_string = None
                        db_sub.qr_path = None

                    await enqueue_notification(
                        session=session,
                        user_id=user.user_id,
                        reason="subscription_expired_deleted",
                        payload={
                            "slot": sub.slot_number,
                            "grace_days": GRACE_PERIOD_DAYS,
                        },
                    )
                    await create_pg_event("notify", session=session)

    if not active_subs:
        return

    earliest_stop = min(sub.stop_time for sub in active_subs)
    earliest_stop_dt = datetime.fromtimestamp(earliest_stop / 1000, tz=timezone.utc)

    # Reminder
    remaining_days = (earliest_stop_dt - now).days
    if 0 < remaining_days <= REMIND_BEFORE_DAYS:
        async with SessionLocal() as session:
            async with session.begin():
                await enqueue_notification(
                    session=session,
                    user_id=user.user_id,
                    reason="subscription_reminder",
                    payload={
                        "active_subs": len(active_subs),
                        "days_left": remaining_days,
                    },
                )
                await create_pg_event("notify", session=session)

    # Autoreneew window
    if earliest_stop_dt <= now + timedelta(hours=RENEW_BEFORE_HOURS):
        quantity_paid = getattr(user, "quantity_guests_paid", 0)
        promo = getattr(user, "user_promo_new", 0)

        prices = [_calc_price_for_slot(quantity_paid, promo) for _ in active_subs]
        total_price_usd = sum(prices)
        total_price_cents = int(max(total_price_usd, UPDATED_MIN_PAY) * 100)

        if (user.user_balance or 0) >= total_price_cents:
            async with SessionLocal() as session:
                async with session.begin():
                    invoice_id = await _create_internal_autorenew_invoice(
                        session, user, active_subs, total_price_cents
                    )

                await enqueue_notification(
                    session=session,
                    user_id=user.user_id,
                    reason="subscription_autorenew_success",
                    payload={
                        "active_subs": len(active_subs),
                        "total_price_usd": total_price_usd,
                        "invoice_id": invoice_id,
                    },
                )
                await create_pg_event("notify", session=session)
        else:
            async with SessionLocal() as session:
                async with session.begin():
                    await enqueue_notification(
                        session=session,
                        user_id=user.user_id,
                        reason="subscription_autorenew_insufficient_funds",
                        payload={
                            "active_subs": len(active_subs),
                            "total_price_usd": total_price_usd,
                        },
                    )
                    await create_pg_event("notify", session=session)


async def _scan():
    async with SessionLocal() as session:
        async with session.begin():
            r = await session.execute(
                select(AllUsers).with_for_update(skip_locked=True)
            )
            users = r.scalars().all()

    for user in users:
        try:
            await _process_user(user)
        except Exception:
            logger.exception(f"Error processing user {user.user_id}")


async def autorenew_loop(stop_event: asyncio.Event):
    logger.info("Autorenew loop started")

    try:
        while not stop_event.is_set():
            await heartbeat("autorenew_worker")
            now = _now()

            next_daily = now.replace(
                hour=TARGET_HOUR_UTC,
                minute=TARGET_MINUTE_UTC,
                second=0,
                microsecond=0,
            )
            if next_daily <= now:
                next_daily += timedelta(days=1)

            next_periodic = now + timedelta(minutes=PERIODIC_SCAN_MINUTES)
            next_run = min(next_daily, next_periodic)
            sleep_seconds = (next_run - now).total_seconds()

            logger.info(f"Next autorenew scan at {next_run.isoformat()} UTC")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=sleep_seconds)
                break
            except asyncio.TimeoutError:
                pass

            await _scan()

    except asyncio.CancelledError:
        logger.info("Autorenew loop cancelled")
    finally:
        logger.info("Autorenew loop stopped")

# # workers/autorenew_worker.py v15 — fully patched

# import asyncio
# import logging
# from datetime import datetime, timezone, timedelta

# from sqlalchemy import select
# from db.async_db import SessionLocal
# from db.models import (
#     AllUsers,
#     UserSubscription,
#     AllInvoices,
#     InvoiceItems,
#     SubscriptionTransaction,
#     ServerClientDeletion,
# )
# from services.notifications import enqueue_notification
# from services.pg_events import create_pg_event
# from config import (
#     UPDATED_PRICE,
#     UPDATED_MIN_PAY,
#     DISCOUNT_BASE_PROCENTS,
#     DISCOUNT_BASE_PROCENTS_PROMO,
#     BOT_SHOP_NAME,
# )

# logger = logging.getLogger(__name__)

# RENEW_BEFORE_HOURS = 24
# GRACE_PERIOD_DAYS = 2
# REMIND_BEFORE_DAYS = 5
# PERIODIC_SCAN_MINUTES = 30
# TARGET_HOUR_UTC = 2
# TARGET_MINUTE_UTC = 0


# def _now():
#     return datetime.now(timezone.utc)


# def _now_ms():
#     return int(_now().timestamp() * 1000)


# def _calc_price_for_slot(quantity_paid: int, promo_active: int) -> float:
#     if promo_active == 1:
#         discount_percent = DISCOUNT_BASE_PROCENTS_PROMO
#         discount_amount = UPDATED_PRICE * discount_percent / 100
#         return round(UPDATED_PRICE - discount_amount, 2)

#     T = quantity_paid + 1
#     total_discount = T * 2.5

#     if total_discount >= 100:
#         return 0.0

#     discount_percent = total_discount
#     discount_amount = UPDATED_PRICE * discount_percent / 100
#     return round(UPDATED_PRICE - discount_amount, 2)


# async def _create_internal_autorenew_invoice(session, user, subs, total_price_cents):
#     invoice_id = f"auto_{user.user_id}_{int(_now().timestamp())}"

#     inv = AllInvoices(
#         invoice_id=invoice_id,
#         user_id=user.user_id,
#         invoice_target="subscription_autorenew_internal",
#         invoice_status="pending",
#         processing_status="pending",
#         invoice_ammount=total_price_cents,
#         invoice_ammount_fact=total_price_cents,
#         invoice_created_at=_now(),
#         invoice_updated_at=_now(),
#     )
#     session.add(inv)

#     for sub in subs:
#         item = InvoiceItems(
#             invoice_id=invoice_id,
#             acc_number=sub.slot_number,
#             server_country_id=sub.server_country_id,
#             server_id=sub.server_id,
#             price=UPDATED_PRICE,
#             final_price=total_price_cents / 100,
#         )
#         session.add(item)

#     tx = SubscriptionTransaction(
#         user_id=user.user_id,
#         provider_invoice_id=invoice_id,
#         status="pending",
#         attempts=0,
#         frozen_amount=0,
#         payload_meta={"source": "autorenew"},
#     )
#     session.add(tx)

#     return invoice_id


# async def _process_user(user: AllUsers):
#     now = _now()
#     now_ms = _now_ms()

#     # Load subscriptions with locking
#     async with SessionLocal() as session:
#         async with session.begin():
#             r = await session.execute(
#                 select(UserSubscription)
#                 .where(UserSubscription.user_id == user.user_id)
#                 .with_for_update(skip_locked=True)
#             )
#             subs = r.scalars().all()

#     active_subs = []
#     expired_subs = []

#     for sub in subs:
#         if not sub.stop_time:
#             continue

#         if sub.stop_time > now_ms:
#             active_subs.append(sub)
#         elif sub.stop_time + GRACE_PERIOD_DAYS * 86400 * 1000 > now_ms:
#             expired_subs.append(sub)
#         else:
#             # Hard expired → delete subscription
#             async with SessionLocal() as session:
#                 async with session.begin():
#                     db_sub = await session.get(UserSubscription, sub.id)
#                     if db_sub:
#                         deletion = ServerClientDeletion(
#                             user_id=user.user_id,
#                             slot_number=sub.slot_number,
#                             server_id=sub.server_id,
#                             client_email=f"{user.user_id}-slot{sub.slot_number}",
#                             delete_not_before_ts=sub.stop_time,
#                         )
#                         session.add(deletion)

#                         db_sub.server_id = None
#                         db_sub.next_server_id = 0
#                         db_sub.pending = False
#                         db_sub.stop_time = None
#                         db_sub.settings_string = None
#                         db_sub.qr_path = None

#                 await enqueue_notification(
#                     session=session,
#                     user_id=user.user_id,
#                     reason="subscription_expired_deleted",
#                     payload={
#                         "slot": sub.slot_number,
#                         "grace_days": GRACE_PERIOD_DAYS,
#                     },
#                 )
#                 await create_pg_event("notify", session=session)

#     if not active_subs:
#         return

#     earliest_stop = min(sub.stop_time for sub in active_subs)
#     earliest_stop_dt = datetime.fromtimestamp(earliest_stop / 1000, tz=timezone.utc)

#     # Reminder
#     remaining_days = (earliest_stop_dt - now).days
#     if 0 < remaining_days <= REMIND_BEFORE_DAYS:
#         async with SessionLocal() as session:
#             async with session.begin():
#                 await enqueue_notification(
#                     session=session,
#                     user_id=user.user_id,
#                     reason="subscription_reminder",
#                     payload={
#                         "active_subs": len(active_subs),
#                         "days_left": remaining_days,
#                     },
#                 )
#                 await create_pg_event("notify", session=session)

#     # Autoreneew window
#     if earliest_stop_dt <= now + timedelta(hours=RENEW_BEFORE_HOURS):
#         quantity_paid = getattr(user, "quantity_guests_paid", 0)
#         promo = getattr(user, "user_promo_new", 0)

#         prices = [_calc_price_for_slot(quantity_paid, promo) for _ in active_subs]
#         total_price_usd = sum(prices)
#         total_price_cents = int(max(total_price_usd, UPDATED_MIN_PAY) * 100)

#         if (user.user_balance or 0) >= total_price_cents:
#             async with SessionLocal() as session:
#                 async with session.begin():
#                     invoice_id = await _create_internal_autorenew_invoice(
#                         session, user, active_subs, total_price_cents
#                     )

#                 await enqueue_notification(
#                     session=session,
#                     user_id=user.user_id,
#                     reason="subscription_autorenew_success",
#                     payload={
#                         "active_subs": len(active_subs),
#                         "total_price_usd": total_price_usd,
#                         "invoice_id": invoice_id,
#                     },
#                 )
#                 await create_pg_event("notify", session=session)
#         else:
#             async with SessionLocal() as session:
#                 async with session.begin():
#                     await enqueue_notification(
#                         session=session,
#                         user_id=user.user_id,
#                         reason="subscription_autorenew_insufficient_funds",
#                         payload={
#                             "active_subs": len(active_subs),
#                             "total_price_usd": total_price_usd,
#                         },
#                     )
#                     await create_pg_event("notify", session=session)


# async def _scan():
#     async with SessionLocal() as session:
#         async with session.begin():
#             r = await session.execute(
#                 select(AllUsers).with_for_update(skip_locked=True)
#             )
#             users = r.scalars().all()

#     for user in users:
#         try:
#             await _process_user(user)
#         except Exception:
#             logger.exception(f"Error processing user {user.user_id}")


# async def autorenew_loop(stop_event: asyncio.Event):
#     logger.info("Autorenew loop started")

#     try:
#         while not stop_event.is_set():
#             now = _now()

#             next_daily = now.replace(
#                 hour=TARGET_HOUR_UTC,
#                 minute=TARGET_MINUTE_UTC,
#                 second=0,
#                 microsecond=0,
#             )
#             if next_daily <= now:
#                 next_daily += timedelta(days=1)

#             next_periodic = now + timedelta(minutes=PERIODIC_SCAN_MINUTES)
#             next_run = min(next_daily, next_periodic)
#             sleep_seconds = (next_run - now).total_seconds()

#             logger.info(f"Next autorenew scan at {next_run.isoformat()} UTC")

#             try:
#                 await asyncio.wait_for(stop_event.wait(), timeout=sleep_seconds)
#                 break
#             except asyncio.TimeoutError:
#                 pass

#             await _scan()

#     except asyncio.CancelledError:
#         logger.info("Autorenew loop cancelled")
#     finally:
#         logger.info("Autorenew loop stopped")
