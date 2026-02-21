from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def topup_keyboard():
    buttons = [
        [InlineKeyboardButton("Пополнить баланс", callback_data="balance_top_up")],
        [InlineKeyboardButton("Инструкция по оплате \U0001F4D6", url="https://telegra.ph/Instrukciya-po-oplate-02-20")],
        [InlineKeyboardButton("Аккаунт не оплатился", callback_data="apeal_account_didnt_paid")],
    ]
    return InlineKeyboardMarkup(buttons)