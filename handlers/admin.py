import os
from telegram import InputMediaPhoto, Update, InputFile
from telegram.ext import ContextTypes
from keyboards.admin_kb import admin_keyboard
from config import ASSETS_DIR, FIRST_USER_IN_DB, MESSTOADM

from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters


from telegram import InlineKeyboardButton, InlineKeyboardMarkup


from handlers.admin.dashboard import admin_dashboard
from handlers.admin.permissions import ADMIN_ROLES

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMIN_ROLES:
        return await update.message.reply_text("⛔ У вас нет доступа.")

    return await admin_dashboard(update, context)


# async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     photo_path = os.path.join(ASSETS_DIR, "admin.jpg")
#     reply_markup = admin_keyboard()

#     query = update.callback_query
#     # If called from a callback query, edit the existing message
#     if query is not None:
#         await query.answer()
#         # If the message already contains a photo, edit caption
#         try:
#             await query.edit_message_caption(
#                 caption="Админ панель:",
#                 reply_markup=reply_markup
#             )
#         except Exception:
#             # Fallback: replace media if caption edit fails
#             with open(photo_path, "rb") as f:
#                 media = InputMediaPhoto(f, caption="Админ панель:")
#                 await query.edit_message_media(media=media, reply_markup=reply_markup)
#         return

#     # Otherwise it's a normal message, send a new photo
#     # use with open to ensure file is closed
#     with open(photo_path, "rb") as f:
#         await update.message.reply_photo(photo=f, caption="Админ панель:", reply_markup=reply_markup)

# # async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
# #     photo_path = os.path.join(ASSETS_DIR, "admin.jpg")

# #     await update.message.reply_photo(
# #         photo=open(photo_path, "rb"),
# #         caption="Админ панель:",
# #         reply_markup=admin_keyboard()
# #     )


# async def admin_callback_router(update, context):
#     query = update.callback_query
#     await query.answer()
#     data = query.data

#     # if data == "call_adm":
#     #     await call_adm(query, context)

#     if data == "admin_reply":
#         await query.answer()
#         await query.edit_message_text("Пополнение баланса...")
#     elif data == "admin_send_all":
#         await query.answer()
#         await query.edit_message_text("Автопродление...")
#     elif data == "admin_mark_all_users_on_server":
#         await query.answer()
#         await query.edit_message_text("Расчет стоимости...")


#     elif data == "adm_plus_usr_days":
#         await query.answer()
#         await query.edit_message_text("Пополнение дней в подписке...")
#     elif data == "adm_user_info":
#         await query.answer()
#         await query.edit_message_text("Информация о пользователе...")
#     elif data == "adm_block_user":
#         await query.answer()
#         await query.edit_message_text("Блокировка пользователя...")


#     elif data == "adm_unblock_user":
#         await query.answer()
#         await query.edit_message_text("Разблокировка пользователя...")
#     elif data == "adm_part_info":
#         await query.answer()
#         await query.edit_message_text("Информация о партнере...")
#     elif data == "adm_add_partner":
#         await query.answer()
#         await query.edit_message_text("Добавление партнера...")


#     elif data == "adm_show_partners":
#         await query.answer()
#         await query.edit_message_text("Показать всех партнеров...")
#     elif data == "adm_pay_partner":
#         await query.answer()
#         await query.edit_message_text("Выплата партнеру...")

#     elif data == "back:admin":
#         # вызываем функцию, которая показывает админ-меню
#         return await admin_handler(update, context)
