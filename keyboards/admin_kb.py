from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def admin_keyboard():
    buttons = [
        # [InlineKeyboardButton("Отправить сообщение админу", callback_data="call_adm")],
        [InlineKeyboardButton("Отправить ответ от админа", callback_data="admin_reply")],
        [InlineKeyboardButton("Объявление Администратора", callback_data="admin_send_all")],
        [InlineKeyboardButton("Отметить юзеров на заблок сервере", callback_data="admin_mark_all_users_on_server")],
        [InlineKeyboardButton("Добавить дней к подписке", callback_data="adm_plus_usr_days")],
        [InlineKeyboardButton("Узнать инфо юзера", callback_data="adm_user_info")],
        [InlineKeyboardButton("Заблокировать юзера", callback_data="adm_block_user")],
        [InlineKeyboardButton("Разблокировать юзера", callback_data="adm_unblock_user")],
        [InlineKeyboardButton("Инфо", callback_data="adm_part_info")],
        [InlineKeyboardButton("Добавить партнера", callback_data="adm_add_partner")],
        [InlineKeyboardButton("Показать всех партнеров", callback_data="adm_show_partners")],
        [InlineKeyboardButton("Выплатить партнеру", callback_data="adm_pay_partner")],
    ]
    return InlineKeyboardMarkup(buttons)