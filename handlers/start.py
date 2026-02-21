from telegram import Update
from telegram.ext import ContextTypes

from keyboards.reply import bottom_menu
from keyboards.inline_main import main_inline_menu


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start command handler.
    Shows the persistent bottom menu + the main inline menu.
    """

    # Send welcome message with bottom menu (ReplyKeyboard)
    await update.message.reply_text(
        "Welcome! Use the bottom menu to navigate:",
        reply_markup=bottom_menu(update, context)
    )

    # Send main inline menu (InlineKeyboard)
    await update.message.reply_text(
        "Choose an option:",
        reply_markup=main_inline_menu()
    )
