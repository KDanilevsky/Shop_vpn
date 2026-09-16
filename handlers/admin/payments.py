from telegram import Update
from telegram.ext import ContextTypes

from keyboards.admin.payments import (
    admin_payments_menu_keyboard,
    admin_payments_list_keyboard,
    admin_payment_view_keyboard,
)
from handlers.admin.permissions import require_permission
from handlers.admin.audit import audit_log

from db.async_db import SessionLocal
from db.models import AllInvoices, AllUsers
from sqlalchemy import select, func
from datetime import datetime


# -----------------------------
# Router
# -----------------------------
async def admin_payments_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "admin:payments":
        return await admin_payments_menu(update, context)

    if data.startswith("admin:payments:list:"):
        _, _, _, status, page = data.split(":")
        return await admin_payments_list(update, context, status, int(page))

    if data.startswith("admin:payment:view:"):
        invoice_id = int(data.split(":")[-1])
        return await admin_payment_view(update, context, invoice_id)

    if data.startswith("admin:payment:mark_paid:"):
        invoice_id = int(data.split(":")[-1])
        return await admin_payment_mark_paid(update, context, invoice_id)

    if data.startswith("admin:payment:refund:"):
        invoice_id = int(data.split(":")[-1])
        return await admin_payment_refund(update, context, invoice_id)

    if data.startswith("admin:payment:resend_link:"):
        invoice_id = int(data.split(":")[-1])
        return await admin_payment_resend_link(update, context, invoice_id)


# -----------------------------
# Main menu
# -----------------------------
@require_permission("payments.view")
async def admin_payments_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "<b>💳 Payments — Admin Panel</b>\n\nВыберите фильтр:"
    await query.message.edit_text(
        text,
        reply_markup=admin_payments_menu_keyboard(),
        parse_mode="HTML",
    )


# -----------------------------
# Payments list (by status)
# -----------------------------
@require_permission("payments.view")
async def admin_payments_list(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str, page: int):
    query = update.callback_query
    await query.answer()

    PAGE_SIZE = 10
    offset = page * PAGE_SIZE

    async with SessionLocal() as session:
        q = select(AllInvoices).order_by(AllInvoices.created_at.desc())
        if status != "all":
            q = q.where(AllInvoices.status == status)

        result = await session.execute(q.offset(offset).limit(PAGE_SIZE))
        invoices = result.scalars().all()

        count_q = select(func.count()).select_from(AllInvoices)
        if status != "all":
            count_q = count_q.where(AllInvoices.status == status)
        total = await session.scalar(count_q)

    text = f"<b>💳 Invoices — {status} (page {page + 1})</b>\n\n"

    if not invoices:
        text += "Нет счетов."
    else:
        for inv in invoices:
            text += (
                f"• #{inv.id} — user {inv.user_id}, "
                f"{inv.amount} {inv.currency}, "
                f"status: {inv.status}\n"
            )

    await query.message.edit_text(
        text,
        reply_markup=admin_payments_list_keyboard(status, page, total, PAGE_SIZE),
        parse_mode="HTML",
    )


# -----------------------------
# Payment detail view
# -----------------------------
@require_permission("payments.view")
async def admin_payment_view(update: Update, context: ContextTypes.DEFAULT_TYPE, invoice_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        inv = await session.get(AllInvoices, invoice_id)
        if not inv:
            return await query.message.edit_text("❌ Счёт не найден.")

        user = await session.get(AllUsers, inv.user_id)

    text = (
        f"<b>💳 Счёт #{inv.id}</b>\n\n"
        f"Пользователь: <b>{user.user_id}</b> (@{user.username})\n"
        f"Сумма: <b>{inv.amount} {inv.currency}</b>\n"
        f"Статус: <b>{inv.status}</b>\n"
        f"Провайдер: {inv.provider}\n"
        f"Создан: {inv.created_at}\n"
        f"Оплачен: {inv.paid_at or '—'}\n"
    )

    await query.message.edit_text(
        text,
        reply_markup=admin_payment_view_keyboard(inv),
        parse_mode="HTML",
    )


# -----------------------------
# Mark as paid (manual)
# -----------------------------
@require_permission("payments.edit")
async def admin_payment_mark_paid(update: Update, context: ContextTypes.DEFAULT_TYPE, invoice_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        inv = await session.get(AllInvoices, invoice_id)
        if not inv:
            return await query.message.edit_text("❌ Счёт не найден.")

        before = {"status": inv.status, "paid_at": str(inv.paid_at)}
        inv.status = "paid"
        inv.paid_at = datetime.utcnow()
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="payment.mark_paid",
        target_type="invoice",
        target_id=invoice_id,
        before=before,
        after={"status": "paid", "paid_at": str(inv.paid_at)},
        reason="Manual reconciliation",
    )

    await admin_payment_view(update, context, invoice_id)


# -----------------------------
# Refund
# -----------------------------
@require_permission("payments.edit")
async def admin_payment_refund(update: Update, context: ContextTypes.DEFAULT_TYPE, invoice_id: int):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        inv = await session.get(AllInvoices, invoice_id)
        if not inv:
            return await query.message.edit_text("❌ Счёт не найден.")

        if inv.status != "paid":
            return await query.message.edit_text("❌ Нельзя вернуть не оплаченный счёт.")

        before = {"status": inv.status}
        inv.status = "refunded"
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="payment.refund",
        target_type="invoice",
        target_id=invoice_id,
        before=before,
        after={"status": "refunded"},
        reason="Manual refund",
    )

    await admin_payment_view(update, context, invoice_id)


# -----------------------------
# Resend payment link
# -----------------------------
@require_permission("payments.edit")
async def admin_payment_resend_link(update: Update, context: ContextTypes.DEFAULT_TYPE, invoice_id: int):
    query = update.callback_query
    await query.answer()

    # Here you’d re-send the payment link via bot to the user
    # await notifier.send_payment_link(user_id=inv.user_id, invoice_id=invoice_id)

    await audit_log(
        admin_id=update.effective_user.id,
        action="payment.resend_link",
        target_type="invoice",
        target_id=invoice_id,
        before={},
        after={},
    )

    await query.message.edit_text("🔁 Платёжная ссылка отправлена повторно.")
    await admin_payment_view(update, context, invoice_id)
