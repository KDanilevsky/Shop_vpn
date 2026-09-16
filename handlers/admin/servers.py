from telegram import Update
from telegram.ext import ContextTypes

from keyboards.admin.servers import (
    admin_servers_menu_keyboard,
    admin_servers_list_keyboard,
    admin_server_view_keyboard,
    admin_server_capacity_keyboard,
    admin_server_status_keyboard,
)

from handlers.admin.permissions import require_permission
from handlers.admin.audit import audit_log

from db.async_db import SessionLocal
from db.models import AllServers, UserSubscription
from sqlalchemy import select, func


# -----------------------------
# Router
# -----------------------------
async def admin_servers_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "admin:servers":
        return await admin_servers_menu(update, context)

    if data.startswith("admin:servers:list:"):
        page = int(data.split(":")[-1])
        return await admin_servers_list(update, context, page)

    if data.startswith("admin:server:view:"):
        server_id = int(data.split(":")[-1])
        return await admin_server_view(update, context, server_id)

    if data.startswith("admin:server:capacity:"):
        server_id = int(data.split(":")[-1])
        return await admin_server_capacity_prompt(update, context, server_id)

    if data.startswith("admin:server:capacity:set:"):
        _, _, _, server_id, capacity = data.split(":")
        return await admin_server_capacity_set(update, context, int(server_id), int(capacity))

    if data.startswith("admin:server:status:"):
        server_id = int(data.split(":")[-1])
        return await admin_server_status_prompt(update, context, server_id)

    if data.startswith("admin:server:status:set:"):
        _, _, _, server_id, status = data.split(":")
        return await admin_server_status_set(update, context, int(server_id), status)

    if data.startswith("admin:server:drain:"):
        server_id = int(data.split(":")[-1])
        return await admin_server_drain(update, context, server_id)


# -----------------------------
# Main menu
# -----------------------------
@require_permission("servers.view")
async def admin_servers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "<b>🖥 Servers — Admin Panel</b>\n\nВыберите действие:"
    await query.message.edit_text(
        text,
        reply_markup=admin_servers_menu_keyboard(),
        parse_mode="HTML",
    )


# -----------------------------
# Servers list (paginated)
# -----------------------------
@require_permission("servers.view")
async def admin_servers_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    query = update.callback_query
    await query.answer()

    PAGE_SIZE = 10
    offset = page * PAGE_SIZE

    async with SessionLocal() as session:
        result = await session.execute(
            select(AllServers)
            .order_by(AllServers.id.asc())
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        servers = result.scalars().all()

        total = await session.scalar(select(func.count()).select_from(AllServers))

    text = f"<b>🖥 Servers (page {page + 1})</b>\n\n"

    if not servers:
        text += "Нет серверов."
    else:
        for s in servers:
            load_pct = int((s.load / s.capacity) * 100) if s.capacity else 0
            text += (
                f"• #{s.id} — {s.country}, {s.ip}\n"
                f"  load: {s.load}/{s.capacity} ({load_pct}%), status: {s.status}\n"
            )

    await query.message.edit_text(
        text,
        reply_markup=admin_servers_list_keyboard(page, total, PAGE_SIZE),
        parse_mode="HTML",
    )


# -----------------------------
# Server detail view
# -----------------------------
@require_permission("servers.view")
async def admin_server_view(update: Update, context: ContextTypes.DEFAULT_TYPE, server_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        server = await session.get(AllServers, server_id)
        if not server:
            return await query.message.edit_text("❌ Сервер не найден.")

        subs_count = await session.scalar(
            select(func.count()).select_from(UserSubscription).where(UserSubscription.server_id == server_id)
        )

    load_pct = int((server.load / server.capacity) * 100) if server.capacity else 0

    text = (
        f"<b>🖥 Сервер #{server.id}</b>\n\n"
        f"Страна: <b>{server.country}</b>\n"
        f"IP: <b>{server.ip}</b>\n"
        f"Статус: <b>{server.status}</b>\n"
        f"Нагрузка: <b>{server.load}/{server.capacity}</b> ({load_pct}%)\n"
        f"Подписок: {subs_count}\n"
        f"Последний heartbeat: {server.last_heartbeat}\n"
    )

    await query.message.edit_text(
        text,
        reply_markup=admin_server_view_keyboard(server),
        parse_mode="HTML",
    )


# -----------------------------
# Capacity change
# -----------------------------
@require_permission("servers.edit")
async def admin_server_capacity_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, server_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        server = await session.get(AllServers, server_id)

    await query.message.edit_text(
        "<b>📈 Изменить capacity</b>\n\nВыберите новое значение:",
        reply_markup=admin_server_capacity_keyboard(server_id, server.capacity),
        parse_mode="HTML",
    )


@require_permission("servers.edit")
async def admin_server_capacity_set(update: Update, context: ContextTypes.DEFAULT_TYPE, server_id: int, capacity: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        server = await session.get(AllServers, server_id)
        before = server.capacity
        server.capacity = capacity
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="server.capacity.change",
        target_type="server",
        target_id=server_id,
        before={"capacity": before},
        after={"capacity": capacity},
    )

    await admin_server_view(update, context, server_id)


# -----------------------------
# Status change (online/offline/draining)
# -----------------------------
@require_permission("servers.edit")
async def admin_server_status_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, server_id: int):
    query = update.callback_query
    await query.answer()

    await query.message.edit_text(
        "<b>⚙️ Изменить статус сервера</b>",
        reply_markup=admin_server_status_keyboard(server_id),
        parse_mode="HTML",
    )


@require_permission("servers.edit")
async def admin_server_status_set(update: Update, context: ContextTypes.DEFAULT_TYPE, server_id: int, status: str):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        server = await session.get(AllServers, server_id)
        before = server.status
        server.status = status
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="server.status.change",
        target_type="server",
        target_id=server_id,
        before={"status": before},
        after={"status": status},
    )

    await admin_server_view(update, context, server_id)


# -----------------------------
# Drain server (no new subs)
# -----------------------------
@require_permission("servers.edit")
async def admin_server_drain(update: Update, context: ContextTypes.DEFAULT_TYPE, server_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        server = await session.get(AllServers, server_id)
        before = server.status
        server.status = "draining"
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="server.drain",
        target_type="server",
        target_id=server_id,
        before={"status": before},
        after={"status": "draining"},
    )

    await admin_server_view(update, context, server_id)
