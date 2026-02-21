import os
from telegram import InputMediaPhoto, Update, InputFile
from telegram.ext import ContextTypes
from keyboards.help_kb import help_keyboard
from config import ASSETS_DIR, FIRST_USER_IN_DB, MESSTOADM

from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters
# from config import MESSTOADM

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_path = os.path.join(ASSETS_DIR, "help.jpg")
    reply_markup = help_keyboard()

    query = update.callback_query
    # If called from a callback query, edit the existing message
    if query is not None:
        await query.answer()
        # If the message already contains a photo, edit caption
        try:
            await query.edit_message_caption(
                caption="Помощь:",
                reply_markup=reply_markup
            )
        except Exception:
            # Fallback: replace media if caption edit fails
            with open(photo_path, "rb") as f:
                media = InputMediaPhoto(f, caption="Помощь:")
                await query.edit_message_media(media=media, reply_markup=reply_markup)
        return

    # Otherwise it's a normal message, send a new photo
    # use with open to ensure file is closed
    with open(photo_path, "rb") as f:
        await update.message.reply_photo(photo=f, caption="Помощь:", reply_markup=reply_markup)

# async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     photo_path = os.path.join(ASSETS_DIR, "help.jpg")

#     await update.message.reply_photo(
#         photo=open(photo_path, "rb"),
#         caption="Помощь:",
#         reply_markup=help_keyboard()
#     )


async def help_callback_router(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "call_adm":
        await call_adm(query, context)

    # elif data.startswith("back:"):
    #     target = data.split(":", 1)[1]
    elif data == "back:help":
        # вызываем функцию, которая показывает админ-меню
        return await help_handler(update, context)


async def call_adm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Если у вас возникли проблемы или вопроссы,\n"
        "Вы можете написать сообщение администратору.\n"
        "Для этого, нажмите: /send_mes_adm\n"
        "\n"
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back:help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def send_mes_adm(update, context):
    text = (
        'Введите текст сообщения для администратора.\n'
        'Нажмите /cancel для отмены отправки\n'
    )
    await update.message.reply_text(text)
    return MESSTOADM

async def enter_mess_adm(update, context):
    bot = context.bot
    text = (
        'Сообщение администратору:'
        f'from user: id: {update.message.from_user.id} \n'
        f'from user: name: {update.message.from_user.name} \n'
        f'from user: text: {update.message.text} \n'
    )
    await bot.send_message(chat_id=FIRST_USER_IN_DB, text=text)
    await bot.send_message(chat_id=update.message.from_user.id, text='Сообщение отправлено администратору.\nДождитесь ответа.\n')

    return ConversationHandler.END

async def cancel_send_mes_adm(update, context):
    """Cancels and ends the conversation."""
    user = update.message.from_user
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back:help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # reply_markup=ReplyKeyboardRemove()
    # await update.message.reply_text(
    #     "Отмена отправки", reply_markup=ReplyKeyboardRemove()
    # )
    await update.message.reply_text(
        "Отмена отправки", reply_markup=reply_markup
    )

    # await update.message.edit_caption(caption="Отмена отправки", reply_markup=reply_markup, parse_mode="html")

    return ConversationHandler.END

def get_admin_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("send_mes_adm", send_mes_adm)],
        states={
            MESSTOADM: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_mess_adm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_send_mes_adm)],
    )