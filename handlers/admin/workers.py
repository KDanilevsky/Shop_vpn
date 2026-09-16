from telegram import Update
from telegram.ext import ContextTypes

from keyboards.admin.workers import (
    admin_workers_menu_keyboard,
    admin_workers_list_keyboard,
    admin_worker_view_keyboard,
)

from handlers.admin.permissions import require_permission
from handlers.admin.audit import audit_log

from db.async_db import SessionLocal
from db.models import Workers
from sqlalchemy import select, func
from datetime import datetime


# -----------------------------
# Router
# -----------------------------
async def admin_workers_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "admin:workers":
        return await admin_workers_menu(update, context)

    if data.startswith("admin:workers:list:"):
        page = int(data.split(":")[-1])
        return await admin_workers_list(update, context, page)

    if data.startswith("admin:worker:view:"):
        worker_id = int(data.split(":")[-1])
        return await admin_worker_view(update, context, worker_id)

    if data.startswith("admin:worker:restart:"):
        worker_id = int(data.split(":")[-1])
        return await admin_worker_restart(update, context, worker_id)

    if data.startswith("admin:worker:clear_queue:"):
        worker_id = int(data.split(":")[-1])
        return await admin_worker_clear_queue(update, context, worker_id)

    if data.startswith("admin:worker:reconcile:"):
        worker_id = int(data.split(":")[-1])
        return await admin_worker_force_reconcile(update, context, worker_id)

    if data.startswith("admin:worker:debug_toggle:"):
        worker_id = int(data.split(":")[-1])
        return await admin_worker_debug_toggle(update, context, worker_id)


# -----------------------------
# Main menu
# -----------------------------
@require_permission("workers.view")
async def admin_workers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "<b>⚙️ Workers — Admin Panel</b>\n\nВыберите действие:"
    await query.message.edit_text(
        text,
        reply_markup=admin_workers_menu_keyboard(),
        parse_mode="HTML",
    )


# -----------------------------
# Workers list (paginated)
# -----------------------------
@require_permission("workers.view")
async def admin_workers_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    query = update.callback_query
    await query.answer()

    PAGE_SIZE = 10
    offset = page * PAGE_SIZE

    async with SessionLocal() as session:
        result = await session.execute(
            select(Workers)
            .order_by(Workers.id.asc())
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        workers = result.scalars().all()

        total = await session.scalar(select(func.count()).select_from(Workers))

    text = f"<b>⚙️ Workers (page {page + 1})</b>\n\n"

    if not workers:
        text += "Нет рабочих процессов."
    else:
        for w in workers:
            status = "🟢 healthy" if w.is_healthy else "🔴 dead"
            text += (
                f"• #{w.id} — {w.name}\n"
                f"  status: {status}, queue: {w.queue_size}, last heartbeat: {w.last_heartbeat}\n"
            )

    await query.message.edit_text(
        text,
        reply_markup=admin_workers_list_keyboard(page, total, PAGE_SIZE),
        parse_mode="HTML",
    )


# -----------------------------
# Worker detail view
# -----------------------------
@require_permission("workers.view")
async def admin_worker_view(update: Update, context: ContextTypes.DEFAULT_TYPE, worker_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        worker = await session.get(Workers, worker_id)
        if not worker:
            return await query.message.edit_text("❌ Worker не найден.")

    status = "🟢 healthy" if worker.is_healthy else "🔴 dead"

    text = (
        f"<b>⚙️ Worker #{worker.id}</b>\n\n"
        f"Название: <b>{worker.name}</b>\n"
        f"Статус: {status}\n"
        f"Очередь: <b>{worker.queue_size}</b>\n"
        f"Последний heartbeat: {worker.last_heartbeat}\n"
        f"Последняя ошибка: {worker.last_error or '—'}\n"
        f"Debug mode: {'🟡 ON' if worker.debug_mode else '⚫ OFF'}\n"
    )

    await query.message.edit_text(
        text,
        reply_markup=admin_worker_view_keyboard(worker),
        parse_mode="HTML",
    )


# -----------------------------
# Restart worker
# -----------------------------
@require_permission("workers.edit")
async def admin_worker_restart(update: Update, context: ContextTypes.DEFAULT_TYPE, worker_id: int):
    query = update.callback_query
    await query.answer()

    # Here you would signal your supervisor to restart the worker
    # supervisor.restart(worker_id)

    await audit_log(
        admin_id=update.effective_user.id,
        action="worker.restart",
        target_type="worker",
        target_id=worker_id,
        before={},
        after={},
    )

    await query.message.edit_text("🔄 Worker перезапущен.")
    await admin_worker_view(update, context, worker_id)


# -----------------------------
# Clear queue
# -----------------------------
@require_permission("workers.edit")
async def admin_worker_clear_queue(update: Update, context: ContextTypes.DEFAULT_TYPE, worker_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        worker = await session.get(Workers, worker_id)
        before = worker.queue_size
        worker.queue_size = 0
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="worker.clear_queue",
        target_type="worker",
        target_id=worker_id,
        before={"queue_size": before},
        after={"queue_size": 0},
    )

    await admin_worker_view(update, context, worker_id)


# -----------------------------
# Force reconcile
# -----------------------------
@require_permission("workers.edit")
async def admin_worker_force_reconcile(update: Update, context: ContextTypes.DEFAULT_TYPE, worker_id: int):
    query = update.callback_query
    await query.answer()

    # Here you enqueue a reconcile job
    # reconcile_queue.put(worker_id)

    await audit_log(
        admin_id=update.effective_user.id,
        action="worker.reconcile",
        target_type="worker",
        target_id=worker_id,
        before={},
        after={},
    )

    await query.message.edit_text("🔁 Запущена принудительная сверка.")
    await admin_worker_view(update, context, worker_id)


# -----------------------------
# Toggle debug mode
# -----------------------------
@require_permission("workers.edit")
async def admin_worker_debug_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, worker_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        worker = await session.get(Workers, worker_id)
        before = worker.debug_mode
        worker.debug_mode = not worker.debug_mode
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="worker.debug_toggle",
        target_type="worker",
        target_id=worker_id,
        before={"debug_mode": before},
        after={"debug_mode": not before},
    )

    await admin_worker_view(update, context, worker_id)
