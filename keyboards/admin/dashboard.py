from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def admin_dashboard_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Users", callback_data="admin:users")],
        [InlineKeyboardButton("🧾 Subscriptions", callback_data="admin:subscriptions")],
        [InlineKeyboardButton("💳 Payments", callback_data="admin:payments")],
        [InlineKeyboardButton("🖥 Servers", callback_data="admin:servers")],
        [InlineKeyboardButton("⚙️ Workers", callback_data="admin:workers")],
        [InlineKeyboardButton("📚 Logs", callback_data="admin:logs")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast")],
        [InlineKeyboardButton("🔐 Settings", callback_data="admin:settings")],
    ])
