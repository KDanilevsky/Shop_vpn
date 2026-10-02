import os
from telegram import InputMediaPhoto, Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import helpers
from keyboards.settings_kb import settings_keyboard
from config import ASSETS_DIR, BOT_SHOP_NAME


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_path = os.path.join(ASSETS_DIR, "settings.jpg")
    reply_markup = settings_keyboard()

    query = update.callback_query
    # If called from a callback query, edit the existing message
    if query is not None:
        await query.answer()
        # If the message already contains a photo, edit caption
        try:
            await query.edit_message_caption(
                caption="Настройки:",
                reply_markup=reply_markup
            )
        except Exception:
            # Fallback: replace media if caption edit fails
            with open(photo_path, "rb") as f:
                media = InputMediaPhoto(f, caption="Настройки:")
                await query.edit_message_media(media=media, reply_markup=reply_markup)
        return

    # Otherwise it's a normal message, send a new photo
    # use with open to ensure file is closed
    with open(photo_path, "rb") as f:
        await update.message.reply_photo(photo=f, caption="Настройки:", reply_markup=reply_markup)

# async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     photo_path = os.path.join(ASSETS_DIR, "settings.jpg")

#     await update.message.reply_photo(
#         photo=open(photo_path, "rb"),
#         caption="Инструкции для настройки ваших устройств.\nВыберите устройство из списка ниже:",
#         reply_markup=settings_keyboard()
#     )


# async def settings_callback_router(update, context):
#     query = update.callback_query
#     await query.answer()
#     data = query.data

#     if data == "settings_iphone":
#         # await query.answer()
#         await settings_iphone(query, context)

#     elif data == "settings_android":
#         # await query.answer()
#         await settings_android(query, context)
#     elif data == "settings_pc":
#         # await query.answer()
#         await settings_pc(query, context)
#     elif data == "settings_tv":
#         # await query.answer()
#         await settings_tv(query, context)
#     elif data == "settings_wifi_router":
#         # await query.answer()
#         await settings_wifi_router(query, context)

    # elif data.startswith("back:"):
    #     target = data.split(":", 1)[1]
    #     if target == "settings":
    #         # вызываем функцию, которая показывает админ-меню
    #         return await settings_handler(update, context)



async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    chat_id = update.effective_chat.id
    
    text_intro = "Установите приложения для своего устройства из списка на фото:\n"
    await bot.send_message(chat_id=chat_id, text=text_intro)
    
    photo_path = os.path.join(ASSETS_DIR, "prilogeniya.jpg")
    with open(photo_path, 'rb') as f:
        await bot.send_document(chat_id=chat_id, document=f)
        
    text_instruction = ("Нажмите на плюс в правом верхнем углу приложения:\n"
                        "Выберите пункт - Считать Qr код\n"
                        "Наведите на полученный Qr код\n"
                        "Разрешите изменение сетевых настроек\n\n"
                        "Запускайте и Выключайте сервис через кнопку в приложении\n")
                        
    keyboard = [
        [InlineKeyboardButton("Главное меню", callback_data="back:settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
            
    await bot.send_message(
        chat_id=chat_id,
        text=text_instruction,
        reply_markup=reply_markup,
        parse_mode="html"
    )