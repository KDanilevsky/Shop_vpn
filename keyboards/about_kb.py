from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def about_keyboard():
    buttons = [
        [InlineKeyboardButton("Преимущества сервиса \U0001F4A5", url="https://telegra.ph/Preimushchestva-servisa-02-20")],
        [InlineKeyboardButton("Использовать сервис Бесплатно \U0001F525", url="https://telegra.ph/Ispolzovat-servis-Besplatno-02-20")],
        [InlineKeyboardButton("Условия использования \U0001F4DD", url="https://telegra.ph/Usloviya-ispolzovaniya-02-20-3")],
        [InlineKeyboardButton("Реферальная сылка \U0001F381", callback_data="ref")],
    ]
    return InlineKeyboardMarkup(buttons)