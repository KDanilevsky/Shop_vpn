# from bitpapa_pay import BitpapaPay
from config import PAYMENT_PROVIDER_TOKEN, BASE_PRICE_IN_USDT, DISCOUNT_BASE_PROCENTS
from db.async_db import SessionLocal
from db.models import AllInvoices, AllUsers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import jsonpickle
from datetime import datetime, timezone
from sqlalchemy import select

from config import BOT_SHOP_NAME, UPDATED_MIN_PAY


# handlers/paying_methods.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler  # или что ты используешь

from db.async_db import SessionLocal
from db.models import AllInvoices, AllUsers
from sqlalchemy import select
from services.bitpapa import BitpapaService


async def confirm_top_up_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bitpapa: BitpapaService = context.application.bot_data["bitpapa_service"]

    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(AllUsers)
                .where(AllUsers.user_id == update.effective_user.id)
                .with_for_update()
            )
            user_db = result.scalar_one_or_none()

    if not user_db or user_db.user_blocked == 1:
        keyboard = [
            [InlineKeyboardButton("Выбрать доп аккаунт 💵", callback_data="count")],
        ]
        await update.effective_chat.send_message(
            "Невозможно пополнить баланс.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    final_price = context.user_data["balance_top_up"]

    # создаём инвойс с retry
    invoice_result = await bitpapa.create_invoice("USDT", final_price)

    res_invoice_amount = int(invoice_result.invoice.amount * 100)

    async with SessionLocal() as session:
        async with session.begin():
            invoice_db = AllInvoices(
                user_id=update.effective_user.id,
                username=update.effective_user.name,
                user_full_name=update.effective_user.full_name,
                invoice_id=invoice_result.invoice.id,
                invoice_curency=invoice_result.invoice.currency_code,
                accounts_ammount=0,
                invoice_ammount=res_invoice_amount,
                invoice_ammount_fact=res_invoice_amount,
                invoice_status=invoice_result.invoice.status,
                invoice_created_at=datetime.fromisoformat(invoice_result.invoice.created_at),
                invoice_updated_at=datetime.fromisoformat(invoice_result.invoice.updated_at),
                invoice_target="popolnenie_balance",
                promo=user_db.user_promo_new,
                quantity_guests_paid=user_db.quantity_guests_paid,
                invoice_url=invoice_result.invoice.url,
            )
            session.add(invoice_db)

    keyboard = [[InlineKeyboardButton("Оплатить", url=invoice_result.invoice.url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_chat.send_message(
        f"Пополнение Баланса на {final_price} $\n{invoice_result.invoice.url}",
        reply_markup=reply_markup,
    )


# # пример регистрации, если нужно из bot.py
# confirm_top_up_balance_handler = CallbackQueryHandler(
#     confirm_top_up_balance,
#     pattern="^top_up_balance$",  # или твой pattern
# )



# # session = SessionLocal()
# async def confirm_top_up_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_db = None
#     promo = None
#     quant = None
#     async with SessionLocal() as session:
#         async with session.begin():
#             user_db = await session.execute(
#                     select(AllUsers).where(AllUsers.user_id == update.effective_user.id).with_for_update()
#                 )
#             user_db = user_db.scalar_one_or_none()
#     # user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()
#     if user_db:
#         promo = user_db.user_promo_new
#         quant = user_db.quantity_guests_paid

#     accounts_amount = 0

#     make_invoice = True

#     # проверка на бан юзера
#     if user_db.user_blocked == 1:
#         make_invoice = False

#     if make_invoice is True:
#         bitpapa_pay = BitpapaPay(api_token=PAYMENT_PROVIDER_TOKEN)

#         final_price = context.user_data['balance_top_up']
        
#         result = await bitpapa_pay.create_invoice("USDT", final_price)
#         print(result.model_dump())
#         print(
#             result.invoice.id,
#             result.invoice.currency_code,
#             result.invoice.amount,
#             result.invoice.status,
#             result.invoice.created_at,
#             result.invoice.updated_at,
#             result.invoice.url
#         )
#         json_string = jsonpickle.encode(result)
#         await bitpapa_pay.close()

#         res_invoice_amount = int(result.invoice.amount*100)

#         async with SessionLocal() as session:
#             async with session.begin():
#                 invoice_db = AllInvoices(user_id=update.effective_user.id, username=update.effective_user.name, user_full_name=update.effective_user.full_name,invoice_id=result.invoice.id,invoice_curency=result.invoice.currency_code,accounts_ammount=accounts_amount,invoice_ammount=res_invoice_amount,invoice_ammount_fact=res_invoice_amount, invoice_status=result.invoice.status,invoice_created_at=result.invoice.created_at,invoice_updated_at=result.invoice.updated_at,invoice_target='popolnenie_balance', promo = promo, quantity_guests_paid=quant, invoice_url=result.invoice.url)
#                 session.add(invoice_db)
#                 # session.commit()
#         keyboard = [
#             [InlineKeyboardButton("Оплатить", url=result.invoice.url)],
#         ]

#         reply_markup = InlineKeyboardMarkup(keyboard)
#         text = (
#             f"Пополнение Баланса на {final_price} $\n"
#             f"{result.invoice.url} \n"
#         )
#         await update.message.reply_text(text, reply_markup=reply_markup)
#     else:
#         keyboard = [
#             [InlineKeyboardButton("Выбрать доп аккаунт \U0001F4B5", callback_data="count")],
#         ]

#         reply_markup = InlineKeyboardMarkup(keyboard)
#         text = (
#             "Невозможно пополнить баланс.\n"
#         )
#         await update.message.reply_text(text, reply_markup=reply_markup)

        





# async def bitpappa_create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):

#     user_db = None
#     promo = None
#     quant = None
#     async with SessionLocal() as session:
#         async with session.begin():
#             user_db = await session.execute(
#                     select(AllUsers).where(AllUsers.user_id == update.effective_user.id).with_for_update()
#                 )
#             user_db = user_db.scalar_one_or_none()
#     # user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()
#     if user_db:
#         promo = user_db.user_promo_new
#         quant = user_db.quantity_guests_paid

#     # user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()
#     # promo = user_db.user_promo_new
#     # quant = user_db.quantity_guests_paid

#     subscript_stop_1 = user_db.subscription_stop_id_1
#     subscript_stop_2 = user_db.subscription_stop_id_2
#     subscript_stop_3 = user_db.subscription_stop_id_3
#     subscript_stop_4 = user_db.subscription_stop_id_4
#     subscript_stop_5 = user_db.subscription_stop_id_5

#     subs_stop_list = []
#     subs_stop_list.append({"subscript_time":subscript_stop_1,"subscript_delta":None})
#     subs_stop_list.append({"subscript_time":subscript_stop_2,"subscript_delta":None})
#     subs_stop_list.append({"subscript_time":subscript_stop_3,"subscript_delta":None})
#     subs_stop_list.append({"subscript_time":subscript_stop_4,"subscript_delta":None})
#     subs_stop_list.append({"subscript_time":subscript_stop_5,"subscript_delta":None})

#     datetime_now = datetime.now(timezone.utc)
#     datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

#     for subs in subs_stop_list:
#         if subs["subscript_time"] is not None:
#             if subs["subscript_time"] >= datetime_now_int:
#                 acc_time = datetime.fromtimestamp(int(str(subs["subscript_time"])[:10])).astimezone(tz=timezone.utc)
#                 delta_ostatok = acc_time - datetime_now
#                 subs["subscript_delta"] = delta_ostatok.days
#             else:
#                 subs["subscript_delta"] = 0
#         else:
#                 subs["subscript_delta"] = 0

#     delta_ostatok_1 = subs_stop_list[0]["subscript_delta"]
#     delta_ostatok_2 = subs_stop_list[1]["subscript_delta"]
#     delta_ostatok_3 = subs_stop_list[2]["subscript_delta"]
#     delta_ostatok_4 = subs_stop_list[3]["subscript_delta"]
#     delta_ostatok_5 = subs_stop_list[4]["subscript_delta"]

#     accounts_amount = context.user_data['accounts_amount']

#     make_invoice = False
#     if accounts_amount == 1:
#         if delta_ostatok_1 <= 15:
#             make_invoice = True
#     if accounts_amount == 2:
#         if delta_ostatok_2 <= 15:
#             make_invoice = True
#     if accounts_amount == 3:
#         if delta_ostatok_3 <= 15:
#             make_invoice = True
#     if accounts_amount == 4:
#         if delta_ostatok_4 <= 15:
#             make_invoice = True
#     if accounts_amount == 5:
#         if delta_ostatok_5 <= 15:
#             make_invoice = True

#     # проверка на бан
#     if user_db.user_blocked == 1:
#         make_invoice = False

#     if make_invoice is True:
#         bitpapa_pay = BitpapaPay(api_token=PAYMENT_PROVIDER_TOKEN)

#         price = context.user_data['counted_price_last']
#         final_price = None
#         inv_price = None
#         if price < UPDATED_MIN_PAY:
#             final_price = UPDATED_MIN_PAY
#             inv_price = price
#         else:
#             final_price = price
#             inv_price = price
#         print(final_price)

#         result = await bitpapa_pay.create_invoice("USDT", final_price)
#         print(result.model_dump())
#         print(
#             result.invoice.id,
#             result.invoice.currency_code,
#             result.invoice.amount,
#             result.invoice.status,
#             result.invoice.created_at,
#             result.invoice.updated_at,
#             result.invoice.url
#         )
#         json_string = jsonpickle.encode(result)
#         await bitpapa_pay.close()


#         async with SessionLocal() as session:
#             async with session.begin():
#                 invoice_db = AllInvoices(user_id=update.from_user.id, user_name=update.from_user.name, user_full_name=update.from_user.full_name,invoice_id=result.invoice.id,invoice_curency=result.invoice.currency_code,accounts_ammount=accounts_amount,invoice_ammount=result.invoice.amount,invoice_ammount_fact=inv_price,invoice_status=result.invoice.status,invoice_created_at=result.invoice.created_at,invoice_updated_at=result.invoice.updated_at,invoice_target='popolnenie_invoice_schet', promo = promo, quantity_guests_paid=quant, invoice_url=result.invoice.url)
#                 session.add(invoice_db)
#                 # session.commit()
#         keyboard = [
#             [InlineKeyboardButton("Оплатить", url=result.invoice.url)],
#         ]

#         reply_markup = InlineKeyboardMarkup(keyboard)
#         text = (
#             f"Подписка {BOT_SHOP_NAME}: 30 дней \n"
#             f"Количество аккаунтов: {context.user_data['accounts_amount']}\n"
#             f"Стоимость: {context.user_data['counted_price_last']} $\n"
#             f"Скидка на акк.: {context.user_data['quantity_guests_paid_last'] * DISCOUNT_BASE_PROCENTS} %\n\n"
#             "Скидка начисляется последовательно: \n"
#             "До 100% - на 1-й акк, свыше - на 2-й, и т.д.\n"
#             f"{result.invoice.url} \n"
#         )
#         await update.message.reply_text(text, reply_markup=reply_markup)
#     else:
#         keyboard = [
#             [InlineKeyboardButton("Выбрать доп аккаунт \U0001F4B5", callback_data="count")],
#         ]

#         reply_markup = InlineKeyboardMarkup(keyboard)
#         text = (
#             "Невозможно продлить подписку.\n"
#             "Т.к. продление возможно, если осталось меньше 15 дней.\n"
#         )
#         await update.message.reply_text(text, reply_markup=reply_markup)


# async def bitpappa_get_invoices():
#     bitpapa_pay = BitpapaPay(api_token=PAYMENT_PROVIDER_TOKEN)
#     result = await bitpapa_pay.get_invoices()
#     for invoice in result.invoices:
#         print(
#             invoice.id,
#             invoice.currency_code,
#             invoice.amount,
#             invoice.status,
#             invoice.created_at,
#             invoice.updated_at,
#             invoice.url
#         )
#     json_string = jsonpickle.encode(result)
#     await bitpapa_pay.close()
#     # print(json_string)
#     return result

async def bitpappa_create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    bitpapa: BitpapaService = context.application.bot_data["bitpapa_service"]
    user_id = query.from_user.id

    # ============================
    # Load user with row lock
    # ============================
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(AllUsers)
                .where(AllUsers.user_id == user_id)
                .with_for_update()
            )
            user_db = result.scalar_one_or_none()

    if not user_db or user_db.user_blocked == 1:
        keyboard = [[InlineKeyboardButton("Выбрать доп аккаунт 💵", callback_data="count")]]
        await query.message.reply_text(
            "Невозможно продлить подписку.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # ============================
    # Data from count()
    # ============================
    accounts_amount = context.user_data.get("accounts_amount")
    price = context.user_data.get("counted_price_last")
    quantity_guests_paid_last = context.user_data.get("quantity_guests_paid_last")

    if not accounts_amount or price is None:
        await query.message.reply_text("Ошибка: данные о подписке не найдены. Попробуйте снова.")
        return

    # ============================
    # Remaining days check
    # ============================
    subs_times = [
        user_db.subscription_stop_id_1,
        user_db.subscription_stop_id_2,
        user_db.subscription_stop_id_3,
        user_db.subscription_stop_id_4,
        user_db.subscription_stop_id_5,
    ]

    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)

    remaining_days = []
    for t in subs_times:
        if t and t >= now_ms:
            acc_time = datetime.fromtimestamp(int(str(t)[:10])).astimezone(timezone.utc)
            remaining_days.append((acc_time - now).days)
        else:
            remaining_days.append(0)

    # 15-day rule
    make_invoice = remaining_days[accounts_amount - 1] <= 15

    if not make_invoice:
        keyboard = [[InlineKeyboardButton("Выбрать доп аккаунт 💵", callback_data="count")]]
        await query.message.reply_text(
            "Продление возможно только если осталось меньше 15 дней.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # ============================
    # Create invoice
    # ============================
    final_price = max(price, UPDATED_MIN_PAY)

    invoice_result = await bitpapa.create_invoice("USDT", final_price)

    # ============================
    # Save invoice to DB
    # ============================
    async with SessionLocal() as session:
        async with session.begin():
            invoice_db = AllInvoices(
                user_id=user_id,
                username=query.from_user.username,
                user_full_name=query.from_user.full_name,
                invoice_id=invoice_result.invoice.id,
                invoice_curency=invoice_result.invoice.currency_code,
                accounts_ammount=accounts_amount,
                invoice_ammount=int(invoice_result.invoice.amount * 100),
                invoice_ammount_fact=price,
                invoice_status=invoice_result.invoice.status,
                invoice_created_at=datetime.fromisoformat(invoice_result.invoice.created_at),
                invoice_updated_at=datetime.fromisoformat(invoice_result.invoice.updated_at),
                invoice_target="subscription_renew",
                promo=user_db.user_promo_new,
                quantity_guests_paid=user_db.quantity_guests_paid,
                invoice_url=invoice_result.invoice.url,
            )
            session.add(invoice_db)

    # ============================
    # Send invoice to user
    # ============================
    keyboard = [[InlineKeyboardButton("Оплатить", url=invoice_result.invoice.url)]]

    text = (
        f"Продление подписки {BOT_SHOP_NAME}: 30 дней\n"
        f"Аккаунтов: {accounts_amount}\n"
        f"Стоимость: {price} $\n"
        f"Скидка: {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n\n"
        "Скидка начисляется последовательно:\n"
        "До 100% — на 1-й аккаунт, свыше — на 2-й, и т.д.\n"
        f"{invoice_result.invoice.url}\n"
    )

    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
