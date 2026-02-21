from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.models import Product


def register_shop_handlers(app, SessionLocal):

    async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
        async with SessionLocal() as session:
            result = await session.execute(Product.__table__.select())
            products = result.fetchall()

        if not products:
            await update.message.reply_text("No products available.")
            return

        text = "Available products:\n\n"
        for p in products:
            text += f"• {p.name} — {p.price} USDT\n"

        await update.message.reply_text(text)

    app.add_handler(CommandHandler("shop", show_products))

