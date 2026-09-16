from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_users_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Поиск пользователя", callback_data="admin:users:search")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:dashboard")],
    ])


def admin_user_view_keyboard(user):
    buttons = [
        [InlineKeyboardButton("💰 Добавить баланс", callback_data=f"admin:user:balance:add:{user.user_id}")],
    ]

    if user.blocked:
        buttons.append([InlineKeyboardButton("🟢 Разблокировать", callback_data=f"admin:user:unblock:{user.user_id}")])
    else:
        buttons.append([InlineKeyboardButton("🔴 Заблокировать", callback_data=f"admin:user:block:{user.user_id}")])

    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin:users")])

    return InlineKeyboardMarkup(buttons)


def admin_user_balance_confirm_keyboard(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✔️ Подтвердить", callback_data=f"admin:user:balance:confirm:{user_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"admin:user:view:{user_id}")],
    ])
