from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_workers_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Список workers", callback_data="admin:workers:list:0")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:dashboard")],
    ])


def admin_workers_list_keyboard(page: int, total: int, page_size: int):
    offset = page * page_size
    buttons = []

    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin:workers:list:{page - 1}"))
    if offset + page_size < total:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin:workers:list:{page + 1}"))

    rows = []
    if buttons:
        rows.append(buttons)

    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin:workers")])
    return InlineKeyboardMarkup(rows)


def admin_worker_view_keyboard(worker):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Restart", callback_data=f"admin:worker:restart:{worker.id}")],
        [InlineKeyboardButton("🧹 Clear queue", callback_data=f"admin:worker:clear_queue:{worker.id}")],
        [InlineKeyboardButton("🔁 Force reconcile", callback_data=f"admin:worker:reconcile:{worker.id}")],
        [InlineKeyboardButton(
            "🟡 Debug OFF" if worker.debug_mode else "⚫ Debug ON",
            callback_data=f"admin:worker:debug_toggle:{worker.id}"
        )],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:workers")],
    ])
