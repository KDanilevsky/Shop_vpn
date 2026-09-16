from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_payments_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Все", callback_data="admin:payments:list:all:0")],
        [InlineKeyboardButton("Ожидают", callback_data="admin:payments:list:pending:0")],
        [InlineKeyboardButton("Оплачены", callback_data="admin:payments:list:paid:0")],
        [InlineKeyboardButton("Просрочены", callback_data="admin:payments:list:expired:0")],
        [InlineKeyboardButton("Возвраты", callback_data="admin:payments:list:refunded:0")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:dashboard")],
    ])


def admin_payments_list_keyboard(status: str, page: int, total: int, page_size: int):
    offset = page * page_size
    buttons = []

    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin:payments:list:{status}:{page - 1}"))
    if offset + page_size < total:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin:payments:list:{status}:{page + 1}"))

    rows = []
    if buttons:
        rows.append(buttons)

    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin:payments")])
    return InlineKeyboardMarkup(rows)


def admin_payment_view_keyboard(inv):
    buttons = []

    if inv.status in ("pending", "expired"):
        buttons.append([InlineKeyboardButton("✔️ Отметить как оплаченный", callback_data=f"admin:payment:mark_paid:{inv.id}")])

    if inv.status == "paid":
        buttons.append([InlineKeyboardButton("↩️ Возврат", callback_data=f"admin:payment:refund:{inv.id}")])

    buttons.append([InlineKeyboardButton("🔁 Отправить ссылку", callback_data=f"admin:payment:resend_link:{inv.id}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin:payments")])

    return InlineKeyboardMarkup(buttons)
