from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def wallet_keyboard():
    buttons = [
        [InlineKeyboardButton("🌐 Мои подписки/сервера", callback_data="my_subscriptions")],
        [InlineKeyboardButton("💳 Пополнить баланс", callback_data="wallet_topup_select_targets")],
        # [InlineKeyboardButton("Автопродление", callback_data="auto_pay_subs")],
        [InlineKeyboardButton("💵 Выбрать/Сменить сервер", callback_data="count")],
        [InlineKeyboardButton("🔗 Моя платёжная ссылка", callback_data="wallet_my_paying_info")],
        [InlineKeyboardButton("👨‍👩‍👧 Аккаунты, которые я пополняю", callback_data="wallet_friendly_accounts")],
        [InlineKeyboardButton("📜 История транзакций", callback_data="wallet_history")],
    ]
    return InlineKeyboardMarkup(buttons)
