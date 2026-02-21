import os
from telegram import InputMediaPhoto, Update, InputFile
from telegram.ext import ContextTypes
from keyboards.topup_kb import topup_keyboard
from config import ASSETS_DIR


async def topup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_path = os.path.join(ASSETS_DIR, "topup.jpg")
    reply_markup = topup_keyboard()

    query = update.callback_query
    # If called from a callback query, edit the existing message
    if query is not None:
        await query.answer()
        # If the message already contains a photo, edit caption
        try:
            await query.edit_message_caption(
                caption="Баланс:",
                reply_markup=reply_markup
            )
        except Exception:
            # Fallback: replace media if caption edit fails
            with open(photo_path, "rb") as f:
                media = InputMediaPhoto(f, caption="Баланс:")
                await query.edit_message_media(media=media, reply_markup=reply_markup)
        return

    # Otherwise it's a normal message, send a new photo
    # use with open to ensure file is closed
    with open(photo_path, "rb") as f:
        await update.message.reply_photo(photo=f, caption="Баланс:", reply_markup=reply_markup)


# async def topup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     photo_path = os.path.join(ASSETS_DIR, "topup.jpg")

#     await update.message.reply_photo(
#         photo=open(photo_path, "rb"),
#         caption="Баланс:",
#         reply_markup=topup_keyboard()
#     )


async def topup_callback_router(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "balance_top_up":
        # await query.answer()
        await query.edit_message_caption("Пополнение баланса...", reply_markup=None)
    elif data == "pay_help":
        # await query.answer()
        await query.edit_message_caption("Инструкция по оплате...", reply_markup=None)
    elif data == "apeal_account_didnt_paid":
        # await query.answer()
        await query.edit_message_caption("Расчет стоимости...", reply_markup=None)

    # elif data.startswith("back:"):
    #     target = data.split(":", 1)[1]
    elif data == "back:topup":
        # вызываем функцию, которая показывает админ-меню
        return await topup_handler(update, context)