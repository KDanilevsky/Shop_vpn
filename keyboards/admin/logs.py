from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_logs_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Provisioning", callback_data="admin:logs:list:provision:0")],
        [InlineKeyboardButton("🔄 Renewals", callback_data="admin:logs:list:renewal:0")],
        [InlineKeyboardButton("💳 Payments", callback_data="admin:logs:list:payment:0")],
        [InlineKeyboardButton("⚠️ Worker Errors", callback_data="admin:logs:list:worker:0")],
        [InlineKeyboardButton("📝 Admin Audit", callback_data="admin:logs:list:audit:0")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:dashboard")],
    ])


def admin_logs_list_keyboard(log_type: str, page: int, total: int, page_size: int):
    offset = page * page_size
    buttons = []

    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin:logs:list:{log_type}:{page - 1}"))
    if offset + page_size < total:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin:logs:list:{log_type}:{page + 1}"))

    rows = []
    if buttons:
        rows.append(buttons)

    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin:logs")])
    return InlineKeyboardMarkup(rows)
