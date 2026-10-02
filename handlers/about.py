import os
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import helpers
from keyboards.about_kb import about_keyboard
from config import ASSETS_DIR, BOT_SHOP_NAME


async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_path = os.path.join(ASSETS_DIR, "about.jpg")
    reply_markup = about_keyboard()

    query = update.callback_query
    # If called from a callback query, edit the existing message
    if query is not None:
        await query.answer()
        # If the message already contains a photo, edit caption
        try:
            await query.edit_message_caption(
                caption="О Сервисе:",
                reply_markup=reply_markup
            )
        except Exception:
            # Fallback: replace media if caption edit fails
            with open(photo_path, "rb") as f:
                media = InputMediaPhoto(f, caption="О Сервисе:")
                await query.edit_message_media(media=media, reply_markup=reply_markup)
        return

    # Otherwise it's a normal message, send a new photo
    # use with open to ensure file is closed
    with open(photo_path, "rb") as f:
        await update.message.reply_photo(photo=f, caption="О Сервисе:", reply_markup=reply_markup)


# async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     photo_path = os.path.join(ASSETS_DIR, "about.jpg")

#     await update.message.reply_photo(
#         photo=open(photo_path, "rb"),
#         caption="О Сервисе:",
#         reply_markup=about_keyboard()
#     )


async def about_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "pluses":
        # await query.answer()
        await pluses(update, context)


    elif data == "free":
        # await query.answer()
        await free(update, context)
    elif data == "usl":
        # await query.answer()
        await usloviya(update, context)
    elif data == "ref":
        await referal_link(update, context)
        # await query.edit_message_caption("Реферальная сылка...", reply_markup=None)

    # elif data.startswith("back:"):
    #     target = data.split(":", 1)[1]
    elif data == "back:about":
        # вызываем функцию, которая показывает админ-меню
        return await about_handler(update, context)

async def pluses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = ("Наши плюсы:\n"
            "- Нет ограничения скорости\n"
            "- Нет ограничения трафика\n"
            "- Нет сбора и перепродажи личных данных\n"
            "- Нет рекламы (рекламу могут показывать приложения через которые вы подключаетесь к сервису)\n"
            "- Бесплатный промо период\n"
            "- Демократичные цены\n"
            "- Помесячная оплата\n"
            "- Есть возможность использования сервиса полностью бесплатно и без ограничений по скорости и трафику!\n"
            "- Автоматическое продление бесплатного использования при соблюдении всех условий\n"
            )
    
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back:about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query = update.callback_query
    await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")


async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Как использовать сервис полностью Бесплатно:\n"
        "\n"
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back:about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
    query = update.callback_query
    await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")


async def usloviya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Условия использования:\n"
        f"Сервис {BOT_SHOP_NAME} создан исключительно в развлекательных целях.\n"
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back:about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
    query = update.callback_query
    await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")


async def referal_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    # bot = Bot.initialize(TELEGRAM_TOKEN)
    # print(await bot)
    cont = str(update.effective_user.id)
    url = helpers.create_deep_linked_url(bot.username, str(cont), group=False)
    # text = f"Бесплатный доступ в интернет без границ на 5 дней NoBordersShop:\n\n {url} \n"
    text = (
        f"\U0001F30E {BOT_SHOP_NAME} \U0001F525 \n"
        "Бесплатный доступ в интернет без границ:\n"
        "5 дней\n"
    )
    # keyboard = InlineKeyboardMarkup.from_button(
    #     InlineKeyboardButton(text="\U0001F381 Получить", url=url)
    # )
    keyboard = [
        [InlineKeyboardButton(text="\U0001F381 Получить", url=url)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(f'{text}', reply_markup=keyboard)
    query = update.callback_query
    await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")