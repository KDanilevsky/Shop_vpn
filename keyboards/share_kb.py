from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def share_keyboard():
    buttons = [
        [InlineKeyboardButton("Реферальная сылка \U0001F381", callback_data="ref")],
    ]
    return InlineKeyboardMarkup(buttons)