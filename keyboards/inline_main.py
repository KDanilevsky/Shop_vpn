from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_inline_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Buy", callback_data="buy")],
        [InlineKeyboardButton("Sell", callback_data="sell")],
        [InlineKeyboardButton("Settings", callback_data="settings")]
    ])
