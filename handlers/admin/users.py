from telegram import Update
from telegram.ext import ContextTypes

from keyboards.admin.users import (
    admin_users_menu_keyboard,
    admin_user_view_keyboard,
    admin_user_balance_confirm_keyboard,
)

from handlers.admin.permissions import require_permission
from handlers.admin.audit import audit_log

from db.async_db import SessionLocal
from db.models import AllUsers, UserSubscription, AllInvoices


# -----------------------------
# Router for all user callbacks
# -----------------------------
async def admin_users_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    # admin:users
    if data == "admin:users":
        return await admin_users_menu(update, context)

    # admin:users:search
    if data == "admin:users:search":
        return await admin_users_search_prompt(update, context)

    # admin:user:view:<id>
    if data.startswith("admin:user:view:"):
        user_id = int(data.split(":")[-1])
        return await admin_user_view(update, context, user_id)

    # admin:user:balance:add:<id>
    if data.startswith("admin:user:balance:add:"):
        user_id = int(data.split(":")[-1])
        return await admin_user_balance_add_prompt(update, context, user_id)

    # admin:user:balance:confirm:<id>
    if data.startswith("admin:user:balance:confirm:"):
        user_id = int(data.split(":")[-1])
        return await admin_user_balance_confirm(update, context, user_id)

    # admin:user:block:<id>
    if data.startswith("admin:user:block:"):
        user_id = int(data.split(":")[-1])
        return await admin_user_block(update, context, user_id)

    # admin:user:unblock:<id>
    if data.startswith("admin:user:unblock:"):
        user_id = int(data.split(":")[-1])
        return await admin_user_unblock(update, context, user_id)


# -----------------------------
# Users main menu
# -----------------------------
@require_permission("users.view")
async def admin_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "<b>👤 Users — Admin Panel</b>\n\nВыберите действие:"
    await query.message.edit_text(
        text,
        reply_markup=admin_users_menu_keyboard(),
        parse_mode="HTML"
    )


# -----------------------------
# Search prompt
# -----------------------------
@require_permission("users.view")
async def admin_users_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["admin_state"] = "awaiting_user_search"

    await query.message.edit_text(
        "<b>🔍 Поиск пользователя</b>\n\nВведите username, user_id или Telegram ID:",
        parse_mode="HTML"
    )


# -----------------------------
# Handle search text
# -----------------------------
@require_permission("users.view")
async def admin_users_search_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("admin_state") != "awaiting_user_search":
        return

    context.user_data["admin_state"] = None
    query_text = update.message.text.strip()

    async with SessionLocal() as session:
        # Search by username or ID
        user = None

        if query_text.isdigit():
            user = await session.get(AllUsers, int(query_text))
        else:
            result = await session.execute(
                select(AllUsers).where(AllUsers.username == query_text)
            )
            user = result.scalar_one_or_none()

    if not user:
        return await update.message.reply_text("❌ Пользователь не найден.")

    return await admin_user_view(update, context, user.user_id)


# -----------------------------
# User detail view
# -----------------------------
@require_permission("users.view")
async def admin_user_view(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query

    async with SessionLocal() as session:
        user = await session.get(AllUsers, user_id)
        if not user:
            return await query.message.edit_text("❌ Пользователь не найден.")

        # Count subscriptions
        subs_count = await session.scalar(
            select(func.count()).select_from(UserSubscription).where(UserSubscription.user_id == user_id)
        )

        # Count invoices
        inv_count = await session.scalar(
            select(func.count()).select_from(AllInvoices).where(AllInvoices.user_id == user_id)
        )

    text = (
        f"<b>👤 Пользователь #{user.user_id}</b>\n\n"
        f"Username: @{user.username}\n"
        f"Баланс: <b>{user.balance} USDT</b>\n"
        f"Статус: {'🟢 Активен' if not user.blocked else '🔴 Заблокирован'}\n"
        f"Подписок: {subs_count}\n"
        f"Платежей: {inv_count}\n"
    )

    await query.message.edit_text(
        text,
        reply_markup=admin_user_view_keyboard(user),
        parse_mode="HTML"
    )


# -----------------------------
# Add balance — prompt
# -----------------------------
@require_permission("users.edit")
async def admin_user_balance_add_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    await query.answer()

    context.user_data["admin_state"] = f"awaiting_balance_amount:{user_id}"

    await query.message.edit_text(
        "<b>💰 Добавить баланс</b>\n\nВведите сумму:",
        parse_mode="HTML"
    )


# -----------------------------
# Add balance — confirm
# -----------------------------
@require_permission("users.edit")
async def admin_user_balance_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    await query.answer()

    amount = context.user_data.get("balance_amount")
    if amount is None:
        return await query.message.edit_text("Ошибка: сумма не найдена.")

    async with SessionLocal() as session:
        user = await session.get(AllUsers, user_id)
        before = user.balance
        user.balance += amount
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="user.balance.add",
        target_type="user",
        target_id=user_id,
        before={"balance": before},
        after={"balance": before + amount},
        reason="Admin manual balance adjustment"
    )

    await query.message.edit_text(
        f"Баланс обновлён: <b>{before} → {before + amount}</b>",
        parse_mode="HTML"
    )


# -----------------------------
# Block user
# -----------------------------
@require_permission("users.edit")
async def admin_user_block(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        user = await session.get(AllUsers, user_id)
        user.blocked = True
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="user.block",
        target_type="user",
        target_id=user_id,
        before={"blocked": False},
        after={"blocked": True},
    )

    await admin_user_view(update, context, user_id)


# -----------------------------
# Unblock user
# -----------------------------
@require_permission("users.edit")
async def admin_user_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        user = await session.get(AllUsers, user_id)
        user.blocked = False
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="user.unblock",
        target_type="user",
        target_id=user_id,
        before={"blocked": True},
        after={"blocked": False},
    )

    await admin_user_view(update, context, user_id)
