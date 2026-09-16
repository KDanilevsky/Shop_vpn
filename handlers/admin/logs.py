from telegram import Update
from telegram.ext import ContextTypes

from keyboards.admin.logs import (
    admin_logs_menu_keyboard,
    admin_logs_list_keyboard,
)

from handlers.admin.permissions import require_permission

from db.async_db import SessionLocal
from db.models import (
    ProvisioningLog,
    RenewalLog,
    PaymentLog,
    WorkerErrorLog,
    AdminAuditLog,
)
from sqlalchemy import select, func


# -----------------------------
# Router
# -----------------------------
async def admin_logs_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "admin:logs":
        return await admin_logs_menu(update, context)

    # admin:logs:list:<type>:<page>
    if data.startswith("admin:logs:list:"):
        _, _, _, log_type, page = data.split(":")
        return await admin_logs_list(update, context, log_type, int(page))

    # admin:logs:view:<type>:<id>
    if data.startswith("admin:logs:view:"):
        _, _, _, log_type, log_id = data.split(":")
        return await admin_logs_view(update, context, log_type, int(log_id))


# -----------------------------
# Logs main menu
# -----------------------------
@require_permission("logs.view")
async def admin_logs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "<b>📚 Logs — Admin Panel</b>\n\nВыберите категорию:"
    await query.message.edit_text(
        text,
        reply_markup=admin_logs_menu_keyboard(),
        parse_mode="HTML",
    )


# -----------------------------
# Log list (paginated)
# -----------------------------
@require_permission("logs.view")
async def admin_logs_list(update: Update, context: ContextTypes.DEFAULT_TYPE, log_type: str, page: int):
    query = update.callback_query
    await query.answer()

    PAGE_SIZE = 10
    offset = page * PAGE_SIZE

    model = {
        "provision": ProvisioningLog,
        "renewal": RenewalLog,
        "payment": PaymentLog,
        "worker": WorkerErrorLog,
        "audit": AdminAuditLog,
    }.get(log_type)

    if not model:
        return await query.message.edit_text("❌ Unknown log type.")

    async with SessionLocal() as session:
        result = await session.execute(
            select(model)
            .order_by(model.created_at.desc())
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        logs = result.scalars().all()

        total = await session.scalar(select(func.count()).select_from(model))

    text = f"<b>📚 Logs: {log_type} (page {page + 1})</b>\n\n"

    if not logs:
        text += "Нет записей."
    else:
        for log in logs:
            text += f"• #{log.id} — {log.created_at} — {log.summary()}\n"

    await query.message.edit_text(
        text,
        reply_markup=admin_logs_list_keyboard(log_type, page, total, PAGE_SIZE),
        parse_mode="HTML",
    )


# -----------------------------
# Log detail view
# -----------------------------
@require_permission("logs.view")
async def admin_logs_view(update: Update, context: ContextTypes.DEFAULT_TYPE, log_type: str, log_id: int):
    query = update.callback_query
    await query.answer()

    model = {
        "provision": ProvisioningLog,
        "renewal": RenewalLog,
        "payment": PaymentLog,
        "worker": WorkerErrorLog,
        "audit": AdminAuditLog,
    }.get(log_type)

    if not model:
        return await query.message.edit_text("❌ Unknown log type.")

    async with SessionLocal() as session:
        log = await session.get(model, log_id)
        if not log:
            return await query.message.edit_text("❌ Запись не найдена.")

    text = (
        f"<b>📄 Log #{log.id}</b>\n\n"
        f"<b>Тип:</b> {log_type}\n"
        f"<b>Время:</b> {log.created_at}\n\n"
        f"<b>Данные:</b>\n<code>{log.details()}</code>"
    )

    await query.message.edit_text(
        text,
        reply_markup=admin_logs_menu_keyboard(),
        parse_mode="HTML",
    )
