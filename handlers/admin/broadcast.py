from telegram import Update
from telegram.ext import ContextTypes

from keyboards.admin.broadcast import (
    admin_broadcast_menu_keyboard,
    # admin_broadcast_segment_keyboard,
    admin_broadcast_confirm_keyboard,
)

from handlers.admin.permissions import require_permission
from handlers.admin.audit import audit_log

from db.async_db import SessionLocal
from db.models import AllUsers, UserSubscription
from sqlalchemy import select
from datetime import datetime


# -----------------------------
# Router
# -----------------------------
async def admin_broadcast_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "admin:broadcast":
        return await admin_broadcast_menu(update, context)

    if data.startswith("admin:broadcast:segment:"):
        segment = data.split(":")[-1]
        return await admin_broadcast_segment(update, context, segment)

    if data == "admin:broadcast:compose":
        return await admin_broadcast_compose(update, context)

    if data == "admin:broadcast:confirm":
        return await admin_broadcast_confirm(update, context)

    if data == "admin:broadcast:send":
        return await admin_broadcast_send(update, context)


# -----------------------------
# Main menu
# -----------------------------
@require_permission("broadcast.send")
async def admin_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "<b>📢 Broadcast — Admin Panel</b>\n\nВыберите аудиторию:"
    await query.message.edit_text(
        text,
        reply_markup=admin_broadcast_menu_keyboard(),
        parse_mode="HTML",
    )


# -----------------------------
# Choose segment
# -----------------------------
@require_permission("broadcast.send")
async def admin_broadcast_segment(update: Update, context: ContextTypes.DEFAULT_TYPE, segment: str):
    query = update.callback_query
    await query.answer()

    context.user_data["broadcast_segment"] = segment

    text = (
        f"<b>📢 Broadcast</b>\n\n"
        f"Аудитория: <b>{segment}</b>\n\n"
        "Введите текст сообщения:"
    )

    context.user_data["admin_state"] = "awaiting_broadcast_text"

    await query.message.edit_text(text, parse_mode="HTML")


# -----------------------------
# Receive message text
# -----------------------------
@require_permission("broadcast.send")
async def admin_broadcast_compose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("admin_state") != "awaiting_broadcast_text":
        return

    context.user_data["admin_state"] = None
    context.user_data["broadcast_text"] = update.message.text

    text = (
        "<b>📢 Предпросмотр сообщения</b>\n\n"
        f"{update.message.text}\n\n"
        "<i>Отправить?</i>"
    )

    await update.message.reply_text(
        text,
        reply_markup=admin_broadcast_confirm_keyboard(),
        parse_mode="HTML",
    )


# -----------------------------
# Confirm broadcast
# -----------------------------
@require_permission("broadcast.send")
async def admin_broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = context.user_data.get("broadcast_text")
    segment = context.user_data.get("broadcast_segment")

    await query.message.edit_text(
        f"<b>📢 Подтверждение</b>\n\n"
        f"Аудитория: <b>{segment}</b>\n"
        f"Сообщение:\n{text}\n\n"
        "Отправить?",
        reply_markup=admin_broadcast_confirm_keyboard(),
        parse_mode="HTML",
    )


# -----------------------------
# Send broadcast
# -----------------------------
@require_permission("broadcast.send")
async def admin_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = context.user_data.get("broadcast_text")
    segment = context.user_data.get("broadcast_segment")

    # Select audience
    async with SessionLocal() as session:
        if segment == "all":
            users = (await session.execute(select(AllUsers.user_id))).scalars().all()

        elif segment == "active":
            users = (
                await session.execute(
                    select(UserSubscription.user_id).where(UserSubscription.status == "active")
                )
            ).scalars().all()

        elif segment == "low_balance":
            users = (
                await session.execute(
                    select(AllUsers.user_id).where(AllUsers.balance < 2)
                )
            ).scalars().all()

        else:
            users = []

    # Throttled sending
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, text)
            sent += 1
        except Exception:
            pass  # ignore failures

    # Audit
    await audit_log(
        admin_id=update.effective_user.id,
        action="broadcast.send",
        target_type="broadcast",
        target_id=0,
        before={},
        after={"segment": segment, "sent": sent},
        reason="Admin broadcast",
    )

    await query.message.edit_text(
        f"📢 Рассылка завершена.\nОтправлено: <b>{sent}</b>",
        parse_mode="HTML",
    )
