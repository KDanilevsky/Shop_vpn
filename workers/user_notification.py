from datetime import datetime, timezone, timedelta
import asyncio
import logging
from telegram.error import RetryAfter
from db.async_db import SessionLocal
from db.models import UserNotifications
from sqlalchemy import select

from services.heartbeat import heartbeat


logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {"worker": "user_notification"})

MAX_ATTEMPTS = 5
BATCH_SIZE = 50

notify_event = asyncio.Event()

def build_notification_text(reason: str, payload: dict | None) -> str:
    payload = payload or {}

    # -----------------------------
    # WALLET / BALANCE
    # -----------------------------
    if reason == "wallet_topup_multi":
        amount = payload.get("amount", 0) / 100
        from_username = payload.get("from_username")
        if from_username:
            return f"Ваш баланс пополнен на {amount:.2f}$ пользователем @{from_username}."
        return f"Ваш баланс пополнен на {amount:.2f}$."

    if reason == "wallet_topup":
        amount = payload.get("amount", 0) / 100
        return f"Ваш баланс пополнен на {amount:.2f}$."

    # -----------------------------
    # SUBSCRIPTION — PROVISIONING
    # -----------------------------
    if reason == "subscription_provisioned":
        slot = payload.get("slot")
        server_id = payload.get("server_id")
        return (
            f"Подписка для Акк {slot} успешно активирована.\n"
            f"Сервер: {server_id}.\n"
            f"Ваши новые настройки готовы к использованию."
        )

    if reason == "subscription_server_changed":
        slot = payload.get("slot")
        old_server = payload.get("old_server_id")
        new_server = payload.get("new_server_id")
        old_until = payload.get("old_valid_until")

        if old_until:
            dt = datetime.fromtimestamp(old_until / 1000).strftime("%d.%m %H:%M")
            return (
                f"Акк {slot}: сервер изменён.\n"
                f"Старый сервер ({old_server}) будет работать до {dt}.\n"
                f"Новый сервер: {new_server}.\n"
                f"Ваши новые настройки готовы."
            )
        return (
            f"Акк {slot}: сервер изменён с {old_server} на {new_server}.\n"
            f"Ваши новые настройки готовы."
        )

    # -----------------------------
    # SUBSCRIPTION — AUTORENEW
    # -----------------------------
    if reason == "subscription_autorenew_success":
        count = payload.get("active_subs", 1)
        price = payload.get("total_price_usd", 0) / 100
        return (
            f"Автопродление выполнено успешно.\n"
            f"Продлено подписок: {count}.\n"
            f"Списано: {price:.2f}$."
        )

    if reason == "subscription_autorenew_insufficient_funds":
        count = payload.get("active_subs", 1)
        price = payload.get("total_price_usd", 0) / 100
        return (
            f"Недостаточно средств для автопродления {count} подписок.\n"
            f"Необходимо: {price:.2f}$.\n"
            f"Пополните баланс или уменьшите количество подписок."
        )

    # -----------------------------
    # SUBSCRIPTION — REMINDERS
    # -----------------------------
    if reason == "subscription_reminder":
        count = payload.get("active_subs", 1)
        days = payload.get("days_left", 1)
        return (
            f"У вас {count} активных подписок.\n"
            f"Они истекают через {days} дн.\n"
            f"Пополните баланс или ожидайте автопродления."
        )

    if reason == "subscription_expired_deleted":
        slot = payload.get("slot")
        grace = payload.get("grace_days", 2)
        return (
            f"Подписка Акк {slot} удалена.\n"
            f"Счёт не был оплачен в течение {grace} дней после окончания."
        )

    # -----------------------------
    # PROMO PERIOD
    # -----------------------------
    if reason == "promo_period_ended":
        return (
            "Ваш промо‑период завершён.\n"
            "Скидка больше не действует."
        )

    if reason == "promo_period_ending_soon":
        days = payload.get("days_left", 1)
        return (
            f"Ваш промо‑период заканчивается через {days} дн.\n"
            f"Успейте продлить подписки со скидкой!"
        )

    # -----------------------------
    # FALLBACK
    # -----------------------------
    return "У вас новое уведомление."



def _now_utc():
    return datetime.now(timezone.utc)


def compute_next_attempt(attempt_count: int) -> datetime | None:
    if attempt_count == 0:
        return _now_utc()
    if attempt_count == 1:
        return _now_utc() + timedelta(minutes=1)
    if attempt_count == 2:
        return _now_utc() + timedelta(minutes=5)
    if attempt_count == 3:
        return _now_utc() + timedelta(minutes=30)
    if attempt_count == 4:
        return _now_utc() + timedelta(hours=3)
    return None  # DLQ


async def process_pending_notifications(bot):
    while True:
        async with SessionLocal() as session:
            # async with session.begin():
            now = _now_utc()

            q = (
                select(UserNotifications)
                .where(
                    UserNotifications.sent_at.is_(None),
                    UserNotifications.failed_permanently.is_(False),
                    (UserNotifications.next_attempt_at.is_(None)) |
                    (UserNotifications.next_attempt_at <= now),
                )
                .limit(BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            r = await session.execute(q)
            notifs = r.scalars().all()

            if not notifs:
                await session.commit()
                await asyncio.sleep(2)
                continue
                

            for n in notifs:
                text = build_notification_text(n.reason, n.payload)

                try:
                    await bot.send_message(chat_id=n.user_id, text=text)
                    n.sent_at = _now_utc()
                    n.last_error = None
                    session.add(n)
                    await session.commit()

                except RetryAfter as e:
                    # Telegram says: wait X seconds
                    n.attempt_count += 1
                    n.last_error = f"RetryAfter: {e.retry_after}s"
                    n.next_attempt_at = _now_utc() + timedelta(seconds=e.retry_after)
                    session.add(n)
                    await session.commit()
                    await asyncio.sleep(e.retry_after)
                    continue

                except Exception as exc:
                    n.attempt_count += 1
                    n.last_error = str(exc)[:500]

                    next_at = compute_next_attempt(n.attempt_count)
                    if next_at is None or n.attempt_count >= MAX_ATTEMPTS:
                        n.failed_permanently = True
                        n.next_attempt_at = None
                    else:
                        n.next_attempt_at = next_at

                session.add(n)
                await session.commit()

                # THROTTLING: avoid hitting Telegram limits
                await asyncio.sleep(0.05)  # 50 ms

            # commit all updates

async def notification_worker(bot):
    while True:
        await heartbeat("notification_worker")
        try:
            # Wait for event OR timeout
            try:
                await asyncio.wait_for(notify_event.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                pass  # timeout → fallback polling

            # Clear event (so next NOTIFY will wake it again)
            notify_event.clear()

            # Process notifications
            await process_pending_notifications(bot)
            await asyncio.sleep(1)

        except Exception:
            logger.exception("notification_worker failed")
            await asyncio.sleep(5)


# async def notification_worker(bot):
#     while True:
#         try:
#             async with SessionLocal() as session:
#                 async with session.begin():
#                     now = _now_utc()

#                     q = (
#                         select(UserNotifications)
#                         .where(
#                             UserNotifications.sent_at.is_(None),
#                             UserNotifications.failed_permanently.is_(False),
#                             (UserNotifications.next_attempt_at.is_(None)) |
#                             (UserNotifications.next_attempt_at <= now),
#                         )
#                         .limit(BATCH_SIZE)
#                         .with_for_update(skip_locked=True)
#                     )
#                     r = await session.execute(q)
#                     notifs = r.scalars().all()

#                     if not notifs:
#                         await session.commit()
#                         await asyncio.sleep(2)
#                         continue

#                     for n in notifs:
#                         text = build_notification_text(n.reason, n.payload)

#                         try:
#                             await bot.send_message(chat_id=n.user_id, text=text)
#                             n.sent_at = _now_utc()
#                             n.last_error = None

#                         except RetryAfter as e:
#                             # Telegram says: wait X seconds
#                             n.attempt_count += 1
#                             n.last_error = f"RetryAfter: {e.retry_after}s"
#                             n.next_attempt_at = _now_utc() + timedelta(seconds=e.retry_after)
#                             session.add(n)
#                             await session.commit()
#                             await asyncio.sleep(e.retry_after)
#                             continue

#                         except Exception as exc:
#                             n.attempt_count += 1
#                             n.last_error = str(exc)[:500]

#                             next_at = compute_next_attempt(n.attempt_count)
#                             if next_at is None or n.attempt_count >= MAX_ATTEMPTS:
#                                 n.failed_permanently = True
#                                 n.next_attempt_at = None
#                             else:
#                                 n.next_attempt_at = next_at

#                         session.add(n)

#                         # THROTTLING: avoid hitting Telegram limits
#                         await asyncio.sleep(0.05)  # 50 ms

#                 # commit all updates
#             await asyncio.sleep(1)

#         except Exception:
#             logger.exception("notification_worker iteration failed")
#             await asyncio.sleep(5)
