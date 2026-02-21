from telegram import Update
from telegram.ext import ContextTypes

from handlers.wallet import wallet_handler
from handlers.topup import topup_handler
from handlers.about import about_handler
from handlers.settings import settings_handler
from handlers.admin import admin_handler
from handlers.share import share_handler
from handlers.help import help_handler

async def bottom_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "💼 Аккаунт":
        return await wallet_handler(update, context)

    elif text == "📊 Пополнение":
        return await topup_handler(update, context)

    elif text == "👤 О Сервисе":
        return await about_handler(update, context)

    elif text == "🛠 Настройки":
        return await settings_handler(update, context)

    elif text == "⭐ Админ":
        return await admin_handler(update, context)
    
    elif text == "⭐ Помощь":
        return await help_handler(update, context)

    elif text == "🎁 Поделиться":
        return await share_handler(update, context)
