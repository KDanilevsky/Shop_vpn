from datetime import datetime, date, timezone, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select, func

from db.async_db import SessionLocal
from db.models import AllUsers, UserSubscription, AllInvoices, AllServers, Workers
from keyboards.admin.dashboard import admin_dashboard_keyboard
from handlers.admin.permissions import require_permission


def _now_utc():
    return datetime.now(timezone.utc)

def _now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


@require_permission("dashboard.view")
async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = update.message

    # Determine target message (callback or message)
    if query:
        await query.answer()
        target = query.message
    else:
        target = message

    # --- Fetch real stats ---
    async with SessionLocal() as session:
        # Total users
        total_users = await session.scalar(select(func.count()).select_from(AllUsers))

        # Active subscriptions
        now_ms = _now_ms()

        active_subs = await session.scalar(
            select(func.count()).select_from(UserSubscription).where(
                (UserSubscription.stop_time != None) &
                (UserSubscription.stop_time > now_ms)
            )
        )

        # Today's revenue

        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        end_of_day = start_of_day + timedelta(days=1)

        today_revenue = await session.scalar(
            select(func.coalesce(func.sum(AllInvoices.amount), 0)).where(
                AllInvoices.status == "paid",
                AllInvoices.created_at >= start_of_day,
                AllInvoices.created_at < end_of_day,
            )
        )


        # Online servers
        servers_online = await session.scalar(
            select(func.count()).select_from(AllServers).where(AllServers.is_online == True)
        )

        # Healthy workers
        workers_healthy = await session.scalar(
            select(func.count()).select_from(Workers).where(Workers.is_healthy == True)
        )

    # --- Build dashboard text ---
    text = (
        "<b>📊 Dashboard</b>\n\n"
        f"👤 Пользователи: <b>{total_users}</b>\n"
        f"🧾 Активные подписки: <b>{active_subs}</b>\n"
        f"💳 Доход сегодня: <b>{today_revenue} USDT</b>\n"
        f"🖥 Серверов онлайн: <b>{servers_online}</b>\n"
        f"⚙️ Рабочих процессов: <b>{workers_healthy}</b>\n"
    )

    # --- Send or edit message depending on update type ---
    if query:
        return await target.edit_text(
            text,
            reply_markup=admin_dashboard_keyboard(),
            parse_mode="HTML",
        )

    return await target.reply_text(
        text,
        reply_markup=admin_dashboard_keyboard(),
        parse_mode="HTML",
    )

# from telegram import Update
# from telegram.ext import ContextTypes
# from keyboards.admin.dashboard import admin_dashboard_keyboard
# from handlers.admin.permissions import require_permission

# @require_permission("dashboard.view")
# async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     if query:
#         await query.answer()

#     # Example metrics (replace with real DB queries)
#     stats = {
#         "total_users": 1523,
#         "active_subs": 874,
#         "today_revenue": 129.50,
#         "servers_online": 7,
#         "workers_healthy": 5,
#     }

#     text = (
#         "<b>📊 Dashboard</b>\n\n"
#         f"👤 Пользователи: <b>{stats['total_users']}</b>\n"
#         f"🧾 Активные подписки: <b>{stats['active_subs']}</b>\n"
#         f"💳 Доход сегодня: <b>{stats['today_revenue']} USDT</b>\n"
#         f"🖥 Серверов онлайн: <b>{stats['servers_online']}</b>\n"
#         f"⚙️ Рабочих процессов: <b>{stats['workers_healthy']}</b>\n"
#     )

#     await query.message.edit_text(
#         text,
#         reply_markup=admin_dashboard_keyboard(),
#         parse_mode="HTML"
#     )
