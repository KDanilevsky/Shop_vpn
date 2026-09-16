# from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# def balance_top_up_keyboard():
#     keyboard = [
#             [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
#             [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
#             [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
#             [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
#             [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
#             [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
#             [InlineKeyboardButton("Назад", callback_data="back:topup")],
#         ]
#     return InlineKeyboardMarkup(keyboard)

# def balance_top_up_keyboard_1():
#     keyboard = [
#             [InlineKeyboardButton("+ 10 $ \u2714", callback_data="balance_top_up_1_ch")],
#             [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
#             [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
#             [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
#             [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
#             [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
#             [InlineKeyboardButton("Назад", callback_data="back:topup")],
#         ]
#     return InlineKeyboardMarkup(keyboard)

# def balance_top_up_keyboard_2():
#     keyboard = [
#             [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
#             [InlineKeyboardButton("+ 15 $ \u2714", callback_data="balance_top_up_2_ch")],
#             [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
#             [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
#             [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
#             [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
#             [InlineKeyboardButton("Назад", callback_data="back:topup")],
#         ]
#     return InlineKeyboardMarkup(keyboard)

# def balance_top_up_keyboard_3():
#     keyboard = [
#             [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
#             [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
#             [InlineKeyboardButton("+ 20 $ \u2714", callback_data="balance_top_up_3_ch")],
#             [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
#             [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
#             [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
#             [InlineKeyboardButton("Назад", callback_data="back:topup")],
#         ]
#     return InlineKeyboardMarkup(keyboard)

# def balance_top_up_keyboard_4():
#     keyboard = [
#             [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
#             [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
#             [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
#             [InlineKeyboardButton("+ 25 $ \u2714", callback_data="balance_top_up_4_ch")],
#             [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
#             [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
#             [InlineKeyboardButton("Назад", callback_data="back:topup")],
#         ]
#     return InlineKeyboardMarkup(keyboard)

# def balance_top_up_keyboard_5():
#     keyboard = [
#             [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
#             [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
#             [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
#             [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
#             [InlineKeyboardButton("+ 30 $ \u2714", callback_data="balance_top_up_5_ch")],
#             [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
#             [InlineKeyboardButton("Назад", callback_data="back:topup")],
#         ]
#     return InlineKeyboardMarkup(keyboard)

# balance_top_up_kb.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

AMOUNTS = [10, 15, 20, 25, 30]

def get_balance_top_up_keyboard(selected: float | None = None) -> InlineKeyboardMarkup:
    keyboard = []

    for amount in AMOUNTS:
        label = f"+ {amount} $"
        callback = f"balance_top_up_{amount}"

        if selected == amount:
            label += " \u2714"
            callback += "_ch"

        keyboard.append([InlineKeyboardButton(label, callback_data=callback)])

    keyboard.append([InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")])
    keyboard.append([InlineKeyboardButton("Назад", callback_data="start")])

    return InlineKeyboardMarkup(keyboard)
