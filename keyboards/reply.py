from telegram import ReplyKeyboardMarkup

def bottom_menu():
    keyboard = [
        ["💼 Wallet", "📊 Deals"],
        ["👤 Profile", "🛠 Support"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
