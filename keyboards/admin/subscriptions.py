from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_subscriptions_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Список подписок", callback_data="admin:subscriptions:list:0")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:dashboard")],
    ])


def admin_subscription_view_keyboard(sub):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ Продлить", callback_data=f"admin:subscription:extend:{sub.id}")],
        [InlineKeyboardButton("🖥 Сменить сервер", callback_data=f"admin:subscription:change_server:{sub.id}")],
        [InlineKeyboardButton("🔄 Переподготовить", callback_data=f"admin:subscription:reprovision:{sub.id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"admin:subscription:delete:{sub.id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:subscriptions")],
    ])


def admin_subscription_extend_keyboard(sub_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("7 дней", callback_data=f"admin:subscription:extend:confirm:{sub_id}:7")],
        [InlineKeyboardButton("30 дней", callback_data=f"admin:subscription:extend:confirm:{sub_id}:30")],
        [InlineKeyboardButton("90 дней", callback_data=f"admin:subscription:extend:confirm:{sub_id}:90")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"admin:subscription:view:{sub_id}")],
    ])


def admin_subscription_change_server_keyboard(sub_id, servers):
    rows = []
    for s in servers:
        rows.append([
            InlineKeyboardButton(
                f"{s.country} ({s.id}) — load {s.load}/{s.capacity}",
                callback_data=f"admin:subscription:change_server:confirm:{sub_id}:{s.id}"
            )
        ])

    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"admin:subscription:view:{sub_id}")])
    return InlineKeyboardMarkup(rows)
