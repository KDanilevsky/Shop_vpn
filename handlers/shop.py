from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from utils.db import SessionLocal
from utils.models import Product


async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with SessionLocal() as session:
        result = await session.execute(select(Product))
        products = result.scalars().all()

    if not products:
        await update.message.reply_text("No products available.")
        return

    text = "\n".join(f"{p.id}. {p.name} — {p.price}$" for p in products)
    await update.message.reply_text(text)
