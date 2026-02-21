from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from config import ADMINS_LIST

def bottom_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = None
    if  update.message.from_user.id  in ADMINS_LIST or update.from_user.id  in ADMINS_LIST:
        keyboard = [
            ["💼 Аккаунт", "📊 Пополнение"],
            ["👤 О Сервисе", "🛠 Настройки"],
            ["⭐ Админ", "\U0001F381 Поделиться"]  
        ]
    else:
        keyboard = [
            ["💼 Аккаунт", "📊 Пополнение"],
            ["👤 О Сервисе", "🛠 Настройки"],
            ["⭐ Помощь", "\U0001F381 Поделиться"]  
        ]

    # наоборот для тестов
    # if  update.message.from_user.id  in ADMINS_LIST or update.from_user.id  in ADMINS_LIST:
    #     keyboard = [
    #         ["💼 Аккаунт", "📊 Пополнение"],
    #         ["👤 О Сервисе", "🛠 Настройки"],
    #         ["⭐ Помощь", "\U0001F381 Поделиться"]  
    #     ]
    # else:
    #     keyboard = [
    #         ["💼 Аккаунт", "📊 Пополнение"],
    #         ["👤 О Сервисе", "🛠 Настройки"],
    #         ["⭐ Админ", "\U0001F381 Поделиться"]  
    #     ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
