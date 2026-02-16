from telegram import Update
from telegram.ext import ContextTypes

async def bottom_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "💼 Wallet":
        await update.message.reply_text("Your wallet info here.")

    elif text == "📊 Deals":
        await update.message.reply_text("Your deals here.")

    elif text == "👤 Profile":
        await update.message.reply_text("Your profile here.")

    elif text == "🛠 Support":
        await update.message.reply_text("Support options here.")
