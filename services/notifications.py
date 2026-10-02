import os
from telegram import Bot
from config import TELEGRAM_TOKEN, BOT_TOP_IMAGE, ASSETS_DIR

# ИСПРАВЛЕНО: Создаем один глобальный экземпляр бота.
# Сессия инициализируется один раз при старте и не течет в памяти.
bot = Bot(token=TELEGRAM_TOKEN)

async def send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path):
    await bot.send_message(chat_id=new_tg_id, text=client_setttings_string)
    
    # ИСПРАВЛЕНО: Безопасно читаем файл с диска перед отправкой
    if os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            await bot.send_photo(chat_id=new_tg_id, photo=f)
        os.remove(img_path)

async def send_message_to_user(new_tg_id, text, reply_markup=None):
    photo_path = os.path.join(ASSETS_DIR, BOT_TOP_IMAGE)
    
    if os.path.exists(photo_path):
        with open(photo_path, 'rb') as f:
            if reply_markup:
                await bot.send_photo(
                    chat_id=new_tg_id, 
                    photo=f, 
                    caption=text, 
                    reply_markup=reply_markup, 
                    parse_mode="html"
                )
            else:
                await bot.send_photo(
                    chat_id=new_tg_id, 
                    photo=f, 
                    caption=text, 
                    parse_mode="html"
                )
    else:
        # Резервный вариант, если картинка-топ не найдена в assets
        await bot.send_message(chat_id=new_tg_id, text=text, reply_markup=reply_markup, parse_mode="html")

# import os
# from telegram import Bot
# from config import TELEGRAM_TOKEN, BOT_TOP_IMAGE, ASSETS_DIR

# async def send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path):
#     bot = Bot(token=TELEGRAM_TOKEN)
#     await bot.send_message(chat_id=new_tg_id, text=client_setttings_string)
#     await bot.send_photo(chat_id=new_tg_id, photo=open(img_path, 'rb'))
#     if os.path.exists(img_path):
#         os.remove(img_path)

# async def send_message_to_user(new_tg_id, text, reply_markup=None):
#     bot = Bot(token=TELEGRAM_TOKEN)
#     photo_path = os.path.join(ASSETS_DIR, BOT_TOP_IMAGE)
#     if reply_markup:
#         # await bot.send_message(chat_id=new_tg_id, text=text, reply_markup=reply_markup)
#         await bot.send_photo(chat_id=new_tg_id, photo=open(photo_path, 'rb'), caption=text, reply_markup=reply_markup, parse_mode="html")
#     else:
#         # await bot.send_message(chat_id=new_tg_id, text=text)
#         await bot.send_photo(chat_id=new_tg_id, photo=open(photo_path, 'rb'), caption=text, parse_mode="html")