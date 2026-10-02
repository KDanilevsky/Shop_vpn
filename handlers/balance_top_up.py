# balance_top_up_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from keyboards.balance_top_up_kb import get_balance_top_up_keyboard

async def handle_balance_top_up(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    user_blocked = context.user_data.get("blocked", 0)
    if user_blocked == 1:
        return

    balance_all = context.user_data.get("balance_all", 0)
    UPDATED_MIN_PAY = context.user_data.get("min_pay", 0)

    data = query.data

    # -----------------------------
    # 1. Определяем выбранную сумму
    # -----------------------------
    selected = None

    if data.startswith("balance_top_up_"):
        # варианты: balance_top_up_10, balance_top_up_10_ch
        parts = data.split("_")
        amount = parts[-1]

        if amount.endswith("ch"):
            # снятие выбора
            selected = None
            context.user_data["balance_top_up"] = 0
        else:
            # установка выбора
            selected = int(float(amount) * 100)
            context.user_data["balance_top_up"] = selected

    # -----------------------------
    # 2. Формируем текст
    # -----------------------------
    text = (
        f"{query.from_user.full_name},\n"
        f"<b>Баланс:</b> {balance_all / 100:.2f} $\n"
        f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY / 100:.2f} $*\n"
        "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, "
        "остаток зачислится на ваш баланс.\n"
    )

    # -----------------------------
    # 3. Генерируем клавиатуру
    # -----------------------------
    keyboard = get_balance_top_up_keyboard(selected)

    # -----------------------------
    # 4. Обновляем caption
    # -----------------------------
    await query.edit_message_caption(
        caption=text,
        reply_markup=keyboard,
        parse_mode="html"
    )
