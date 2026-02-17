import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import TELEGRAM_TOKEN
from handlers.start import start
from handlers.bottom_menu import bottom_menu_router
from handlers.inline_router import inline_router
from handlers.shop import show_products

# OPTIONAL DB INIT
from utils.init_db import init_db, drop_db


async def main():
    # Uncomment to DROP all tables
    await drop_db()


    # Uncomment this line to create tables
    await init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("products", show_products))

    app.add_handler(CallbackQueryHandler(inline_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bottom_menu_router))

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
