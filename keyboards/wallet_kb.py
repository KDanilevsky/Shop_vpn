from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def wallet_keyboard():
    buttons = [
        [InlineKeyboardButton("Подписки", callback_data="my_accounts")],
        [InlineKeyboardButton("Пополнить баланс", callback_data="balance_top_up")],
        [InlineKeyboardButton("Автопродление", callback_data="auto_pay_subs")],
        [InlineKeyboardButton("Расчитать стоимость на 30 дней 💵", callback_data="count")],
    ]
    return InlineKeyboardMarkup(buttons)
