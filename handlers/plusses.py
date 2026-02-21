from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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
        [InlineKeyboardButton("Главное меню", callback_data="start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")