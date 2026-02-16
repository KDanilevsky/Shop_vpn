from telegram import Update
from telegram.ext import ContextTypes
from keyboards.inline_main import main_inline_menu
from handlers.pagination import paginated_menu

async def inline_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "buy":
        await query.edit_message_text("Buy menu:", reply_markup=paginated_menu(0))

    elif data.startswith("page_"):
        page = int(data.split("_")[1])
        await query.edit_message_text(f"Page {page+1}:", reply_markup=paginated_menu(page))

    elif data == "back_main":
        await query.edit_message_text("Main menu:", reply_markup=main_inline_menu())
