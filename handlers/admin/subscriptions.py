from telegram import Update
from telegram.ext import ContextTypes

from keyboards.admin.subscriptions import (
    admin_subscriptions_menu_keyboard,
    admin_subscription_view_keyboard,
    admin_subscription_extend_keyboard,
    admin_subscription_change_server_keyboard,
)

from handlers.admin.permissions import require_permission
from handlers.admin.audit import audit_log

from db.async_db import SessionLocal
from db.models import UserSubscription, AllUsers, AllServers
from sqlalchemy import select, func


# -----------------------------
# Router
# -----------------------------
async def admin_subscriptions_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    # admin:subscriptions
    if data == "admin:subscriptions":
        return await admin_subscriptions_menu(update, context)

    # admin:subscriptions:list:<page>
    if data.startswith("admin:subscriptions:list:"):
        page = int(data.split(":")[-1])
        return await admin_subscriptions_list(update, context, page)

    # admin:subscription:view:<id>
    if data.startswith("admin:subscription:view:"):
        sub_id = int(data.split(":")[-1])
        return await admin_subscription_view(update, context, sub_id)

    # admin:subscription:extend:<id>
    if data.startswith("admin:subscription:extend:"):
        sub_id = int(data.split(":")[-1])
        return await admin_subscription_extend_prompt(update, context, sub_id)

    # admin:subscription:extend:confirm:<id>:<days>
    if data.startswith("admin:subscription:extend:confirm:"):
        _, _, _, sub_id, days = data.split(":")
        return await admin_subscription_extend_confirm(update, context, int(sub_id), int(days))

    # admin:subscription:change_server:<id>
    if data.startswith("admin:subscription:change_server:"):
        sub_id = int(data.split(":")[-1])
        return await admin_subscription_change_server_prompt(update, context, sub_id)

    # admin:subscription:change_server:confirm:<id>:<server_id>
    if data.startswith("admin:subscription:change_server:confirm:"):
        _, _, _, sub_id, server_id = data.split(":")
        return await admin_subscription_change_server_confirm(update, context, int(sub_id), int(server_id))

    # admin:subscription:reprovision:<id>
    if data.startswith("admin:subscription:reprovision:"):
        sub_id = int(data.split(":")[-1])
        return await admin_subscription_reprovision(update, context, sub_id)

    # admin:subscription:delete:<id>
    if data.startswith("admin:subscription:delete:"):
        sub_id = int(data.split(":")[-1])
        return await admin_subscription_delete(update, context, sub_id)


# -----------------------------
# Main menu
# -----------------------------
@require_permission("subscriptions.view")
async def admin_subscriptions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "<b>🧾 Subscriptions — Admin Panel</b>\n\nВыберите действие:"
    await query.message.edit_text(
        text,
        reply_markup=admin_subscriptions_menu_keyboard(),
        parse_mode="HTML"
    )


# -----------------------------
# Subscription list (paginated)
# -----------------------------
@require_permission("subscriptions.view")
async def admin_subscriptions_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    query = update.callback_query
    await query.answer()

    PAGE_SIZE = 10
    offset = page * PAGE_SIZE

    async with SessionLocal() as session:
        result = await session.execute(
            select(UserSubscription)
            .order_by(UserSubscription.created_at.desc())
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        subs = result.scalars().all()

        total = await session.scalar(select(func.count()).select_from(UserSubscription))

    text = f"<b>🧾 Subscriptions (page {page + 1})</b>\n\n"

    if not subs:
        text += "Нет подписок."
    else:
        for s in subs:
            text += f"• #{s.id} — user {s.user_id}, server {s.server_id}, expires {s.expires_at.date()}\n"

    # Pagination buttons
    buttons = []
    if page > 0:
        buttons.append(("⬅️ Prev", f"admin:subscriptions:list:{page - 1}"))
    if offset + PAGE_SIZE < total:
        buttons.append(("Next ➡️", f"admin:subscriptions:list:{page + 1}"))

    keyboard = [
        [InlineKeyboardButton(text, callback_data=data)] for text, data in buttons
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin:subscriptions")])

    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# -----------------------------
# Subscription detail view
# -----------------------------
@require_permission("subscriptions.view")
async def admin_subscription_view(update: Update, context: ContextTypes.DEFAULT_TYPE, sub_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        sub = await session.get(UserSubscription, sub_id)
        if not sub:
            return await query.message.edit_text("❌ Подписка не найдена.")

        user = await session.get(AllUsers, sub.user_id)
        server = await session.get(AllServers, sub.server_id)

    text = (
        f"<b>🧾 Подписка #{sub.id}</b>\n\n"
        f"Пользователь: <b>{user.user_id}</b> (@{user.username})\n"
        f"Сервер: <b>{server.country} ({server.id})</b>\n"
        f"Статус: <b>{sub.status}</b>\n"
        f"Истекает: <b>{sub.expires_at}</b>\n"
        f"Создана: {sub.created_at}\n"
    )

    await query.message.edit_text(
        text,
        reply_markup=admin_subscription_view_keyboard(sub),
        parse_mode="HTML"
    )


# -----------------------------
# Extend subscription
# -----------------------------
@require_permission("subscriptions.edit")
async def admin_subscription_extend_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, sub_id: int):
    query = update.callback_query
    await query.answer()

    await query.message.edit_text(
        "<b>⏳ Продлить подписку</b>\n\nВыберите срок:",
        reply_markup=admin_subscription_extend_keyboard(sub_id),
        parse_mode="HTML"
    )


@require_permission("subscriptions.edit")
async def admin_subscription_extend_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, sub_id: int, days: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        sub = await session.get(UserSubscription, sub_id)
        before = sub.expires_at
        sub.expires_at += timedelta(days=days)
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="subscription.extend",
        target_type="subscription",
        target_id=sub_id,
        before={"expires_at": str(before)},
        after={"expires_at": str(before + timedelta(days=days))},
    )

    await admin_subscription_view(update, context, sub_id)


# -----------------------------
# Change server
# -----------------------------
@require_permission("subscriptions.edit")
async def admin_subscription_change_server_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, sub_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        servers = (await session.execute(select(AllServers))).scalars().all()

    await query.message.edit_text(
        "<b>🖥 Выберите новый сервер</b>",
        reply_markup=admin_subscription_change_server_keyboard(sub_id, servers),
        parse_mode="HTML"
    )


@require_permission("subscriptions.edit")
async def admin_subscription_change_server_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, sub_id: int, server_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        sub = await session.get(UserSubscription, sub_id)
        before = sub.server_id
        sub.server_id = server_id
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="subscription.change_server",
        target_type="subscription",
        target_id=sub_id,
        before={"server_id": before},
        after={"server_id": server_id},
    )

    await admin_subscription_view(update, context, sub_id)


# -----------------------------
# Re-provision subscription
# -----------------------------
@require_permission("subscriptions.edit")
async def admin_subscription_reprovision(update: Update, context: ContextTypes.DEFAULT_TYPE, sub_id: int):
    query = update.callback_query
    await query.answer()

    # Here you enqueue a provisioning job
    # provision_queue.put(sub_id)

    await audit_log(
        admin_id=update.effective_user.id,
        action="subscription.reprovision",
        target_type="subscription",
        target_id=sub_id,
        before={},
        after={},
    )

    await query.message.edit_text("🔄 Подписка отправлена на переподготовку.")
    await admin_subscription_view(update, context, sub_id)


# -----------------------------
# Delete subscription
# -----------------------------
@require_permission("subscriptions.edit")
async def admin_subscription_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, sub_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        sub = await session.get(UserSubscription, sub_id)
        before = {"status": sub.status}
        sub.status = "deleted"
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="subscription.delete",
        target_type="subscription",
        target_id=sub_id,
        before=before,
        after={"status": "deleted"},
    )

    await query.message.edit_text("🗑 Подписка удалена.")
