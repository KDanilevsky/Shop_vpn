from telegram import Update
from telegram.ext import ContextTypes

from handlers.admin.dashboard import admin_dashboard
from handlers.admin.permissions import ADMIN_ROLES

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMIN_ROLES:
        return await update.message.reply_text("⛔ У вас нет доступа.")

    return await admin_dashboard(update, context)
