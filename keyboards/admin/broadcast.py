from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_broadcast_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Все пользователи", callback_data="admin:broadcast:segment:all")],
        [InlineKeyboardButton("🟢 Активные подписчики", callback_data="admin:broadcast:segment:active")],
        [InlineKeyboardButton("💸 Низкий баланс", callback_data="admin:broadcast:segment:low_balance")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:dashboard")],
    ])


def admin_broadcast_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✔️ Отправить", callback_data="admin:broadcast:send")],
        [InlineKeyboardButton("❌ Отмена", callback_data="admin:broadcast")],
    ])
