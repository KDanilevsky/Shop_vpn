import os
from telegram import InputMediaPhoto, Update, InputFile
from telegram.ext import ContextTypes
from keyboards.admin_kb import admin_keyboard
from config import ASSETS_DIR, FIRST_USER_IN_DB, MESSTOADM

from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters
# from config import MESSTOADM

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_path = os.path.join(ASSETS_DIR, "admin.jpg")
    reply_markup = admin_keyboard()

    query = update.callback_query
    # If called from a callback query, edit the existing message
    if query is not None:
        await query.answer()
        # If the message already contains a photo, edit caption
        try:
            await query.edit_message_caption(
                caption="Админ панель:",
                reply_markup=reply_markup
            )
        except Exception:
            # Fallback: replace media if caption edit fails
            with open(photo_path, "rb") as f:
                media = InputMediaPhoto(f, caption="Админ панель:")
                await query.edit_message_media(media=media, reply_markup=reply_markup)
        return

    # Otherwise it's a normal message, send a new photo
    # use with open to ensure file is closed
    with open(photo_path, "rb") as f:
        await update.message.reply_photo(photo=f, caption="Админ панель:", reply_markup=reply_markup)

# async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     photo_path = os.path.join(ASSETS_DIR, "admin.jpg")

#     await update.message.reply_photo(
#         photo=open(photo_path, "rb"),
#         caption="Админ панель:",
#         reply_markup=admin_keyboard()
#     )


async def admin_callback_router(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    # if data == "call_adm":
    #     await call_adm(query, context)

    if data == "admin_reply":
        await query.answer()
        await query.edit_message_text("Пополнение баланса...")
    elif data == "admin_send_all":
        await query.answer()
        await query.edit_message_text("Автопродление...")
    elif data == "admin_mark_all_users_on_server":
        await query.answer()
        await query.edit_message_text("Расчет стоимости...")


    elif data == "adm_plus_usr_days":
        await query.answer()
        await query.edit_message_text("Пополнение дней в подписке...")
    elif data == "adm_user_info":
        await query.answer()
        await query.edit_message_text("Информация о пользователе...")
    elif data == "adm_block_user":
        await query.answer()
        await query.edit_message_text("Блокировка пользователя...")


    elif data == "adm_unblock_user":
        await query.answer()
        await query.edit_message_text("Разблокировка пользователя...")
    elif data == "adm_part_info":
        await query.answer()
        await query.edit_message_text("Информация о партнере...")
    elif data == "adm_add_partner":
        await query.answer()
        await query.edit_message_text("Добавление партнера...")


    elif data == "adm_show_partners":
        await query.answer()
        await query.edit_message_text("Показать всех партнеров...")
    elif data == "adm_pay_partner":
        await query.answer()
        await query.edit_message_text("Выплата партнеру...")

    
    # elif data.startswith("back:"):
    #     target = data.split(":", 1)[1]
    elif data == "back:admin":
        # вызываем функцию, которая показывает админ-меню
        return await admin_handler(update, context)



# async def call_adm(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     text = (
#         "Если у вас возникли проблемы или вопроссы,\n"
#         "Вы можете написать сообщение администратору.\n"
#         "Для этого, нажмите: /send_mes_adm\n"
#         "\n"
#     )
#     keyboard = [
#         [InlineKeyboardButton("Назад", callback_data="start")],
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

# async def send_mes_adm(update, context):
#     text = (
#         'Введите текст сообщения для администратора.\n'
#         'Нажмите /cancel для отмены отправки\n'
#     )
#     await update.message.reply_text(text)
#     return MESSTOADM

# async def enter_mess_adm(update, context):
#     bot = context.bot
#     text = (
#         'Сообщение администратору:'
#         f'from user: id: {update.message.from_user.id} \n'
#         f'from user: name: {update.message.from_user.name} \n'
#         f'from user: text: {update.message.text} \n'
#     )
#     await bot.send_message(chat_id=FIRST_USER_IN_DB, text=text)
#     await bot.send_message(chat_id=update.message.from_user.id, text='Сообщение отправлено администратору.\nДождитесь ответа.\n')

#     return ConversationHandler.END

# async def cancel(update, context):
#     """Cancels and ends the conversation."""
#     user = update.message.from_user
#     keyboard = [
#         [InlineKeyboardButton("Главное меню", callback_data="start")],
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     # reply_markup=ReplyKeyboardRemove()
#     # await update.message.reply_text(
#     #     "Отмена отправки", reply_markup=ReplyKeyboardRemove()
#     # )
#     await update.message.reply_text(
#         "Отмена отправки", reply_markup=reply_markup
#     )

#     # await update.message.edit_caption(caption="Отмена отправки", reply_markup=reply_markup, parse_mode="html")

#     return ConversationHandler.END

# def get_admin_conversation_handler():
#     return ConversationHandler(
#         entry_points=[CommandHandler("send_mes_adm", send_mes_adm)],
#         states={
#             MESSTOADM: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_mess_adm)],
#         },
#         fallbacks=[CommandHandler("cancel", cancel)],
#     )
