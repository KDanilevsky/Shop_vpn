from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def help_keyboard():
    buttons = [
        [InlineKeyboardButton("Отправить сообщение админу", callback_data="call_adm")],
    ]
    return InlineKeyboardMarkup(buttons)