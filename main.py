from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.start import start
from handlers.bottom_menu import bottom_menu_router
from handlers.inline_router import inline_router

def main():
    app = Application.builder().token("YOUR_TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(inline_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bottom_menu_router))

    app.run_polling()

if __name__ == "__main__":
    main()
