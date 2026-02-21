from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def settings_keyboard():
    buttons = [
        [InlineKeyboardButton("Iphone \U0001F4A5", url="https://telegra.ph/Nastrojki-telefona-02-19")],
        [InlineKeyboardButton("Android \U0001F525", url="https://telegra.ph/Nastrojki-telefona-02-19")],
        [InlineKeyboardButton("PC (компьютер) \U0001F4DD", url="https://telegra.ph/Nastrojki-telefona-02-19")],
        [InlineKeyboardButton("TV (тв-приставка) \U0001F381", url="https://telegra.ph/Nastrojki-telefona-02-19")],
        [InlineKeyboardButton("WIFI Router \U0001F381", url="https://telegra.ph/Nastrojki-telefona-02-19")],

        # [InlineKeyboardButton("Iphone \U0001F4A5", callback_data="settings_iphone")],
        # [InlineKeyboardButton("Android \U0001F525", callback_data="settings_android")],
        # [InlineKeyboardButton("PC (компьютер) \U0001F4DD", callback_data="settings_pc")],
        # [InlineKeyboardButton("TV (тв-приставка) \U0001F381", callback_data="settings_tv")],
        # [InlineKeyboardButton("WIFI Router \U0001F381", callback_data="settings_wifi_router")],
    ]
    return InlineKeyboardMarkup(buttons)