
import os
from telegram import InputMediaPhoto, Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import helpers
from keyboards.share_kb import share_keyboard
from config import ASSETS_DIR, BOT_SHOP_NAME


async def share_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_path = os.path.join(ASSETS_DIR, "share.jpg")
    reply_markup = share_keyboard()

    query = update.callback_query
    # If called from a callback query, edit the existing message
    if query is not None:
        await query.answer()
        # If the message already contains a photo, edit caption
        try:
            await query.edit_message_caption(
                caption="Поделитесь сервисом, для этого:\n1. Нажмите на кнопку ниже\n2. Поделитесь реферальной ссылкой с друзьями\n3. Получите скидку до 100% за каждого приглашенного друга, используещего сервис!\n",
                reply_markup=reply_markup
            )
        except Exception:
            # Fallback: replace media if caption edit fails
            with open(photo_path, "rb") as f:
                media = InputMediaPhoto(f, caption="Поделитесь сервисом, для этого:\n1. Нажмите на кнопку ниже\n2. Поделитесь реферальной ссылкой с друзьями\n3. Получите скидку до 100% за каждого приглашенного друга, используещего сервис!\n")
                await query.edit_message_media(media=media, reply_markup=reply_markup)
        return

    # Otherwise it's a normal message, send a new photo
    # use with open to ensure file is closed
    with open(photo_path, "rb") as f:
        await update.message.reply_photo(photo=f, caption="Поделитесь сервисом, для этого:\n1. Нажмите на кнопку ниже\n2. Поделитесь реферальной ссылкой с друзьями\n3. Получите скидку до 100% за каждого приглашенного друга, используещего сервис!\n", reply_markup=reply_markup)

# async def share_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     photo_path = os.path.join(ASSETS_DIR, "share.jpg")

#     await update.message.reply_photo(
#         photo=open(photo_path, "rb"),
#         caption="Поделитесь сервисом, для этого:\n1. Нажмите на кнопку ниже\n2. Поделитесь реферальной ссылкой с друзьями\n3. Получите скидку до 100% за каждого приглашенного друга, используещего сервис!\n",
#         reply_markup=share_keyboard()
#     )

async def referal_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    cont = str(update.from_user.id)
    url = helpers.create_deep_linked_url(bot.username, str(cont), group=False)
    text = (
        f"\U0001F30E {BOT_SHOP_NAME} \U0001F525 \n"
        "Бесплатный доступ в интернет без границ:\n"
        "5 дней\n"
    )
    keyboard = [
        [InlineKeyboardButton(text="\U0001F381 Получить", url=url)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")