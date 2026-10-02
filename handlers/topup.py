import os
from telegram import InputMediaPhoto, Update, InputFile
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db.models import AllUsers, AllInvoices, FriendlyAccount, InvoiceTopupTargets
from keyboards.topup_kb import topup_keyboard
from config import ASSETS_DIR
from db.async_db import SessionLocal
from services.bitpapa import BitpapaService
from sqlalchemy import select
from datetime import datetime

from handlers.balance_top_up import handle_balance_top_up


# async def _safe_edit(message, text, keyboard):
#     print("SAFE_EDIT: message.photo =", bool(message.photo))
#     print("SAFE_EDIT: trying edit_caption")

#     markup = InlineKeyboardMarkup(keyboard)

#     try:
#         if message.photo:
#             await message.edit_caption(
#                 caption=text,
#                 reply_markup=markup,
#                 parse_mode="html",
#             )
#             print("SAFE_EDIT: edit_caption OK")
#             return
#         else:
#             print("SAFE_EDIT: no photo, trying edit_text")
#             await message.edit_text(
#                 text,
#                 reply_markup=markup,
#                 parse_mode="html",
#             )
#             print("SAFE_EDIT: edit_text OK")
#             return
#     except Exception as e:
#         print("SAFE_EDIT: edit_caption/edit_text FAILED:", e)

#     # Try replacing media
#     try:
#         print("SAFE_EDIT: trying edit_media")
#         photo_path = os.path.join(ASSETS_DIR, "topup.jpg")
#         with open(photo_path, "rb") as f:
#             media = InputMediaPhoto(f, caption=text, parse_mode="html")
#             await message.edit_media(media=media, reply_markup=markup)
#         print("SAFE_EDIT: edit_media OK")
#     except Exception as e:
#         print("SAFE_EDIT: edit_media FAILED:", e)

async def _safe_edit(message, text, keyboard):
    markup = InlineKeyboardMarkup(keyboard)

    try:
        if message.photo:
            await message.edit_caption(
                caption=text,
                reply_markup=markup,
                parse_mode="html",
            )
        else:
            await message.edit_text(
                text,
                reply_markup=markup,
                parse_mode="html",
            )
    except Exception:
        # Try replacing media (photo)
        try:
            photo_path = os.path.join(ASSETS_DIR, "topup.jpg")
            with open(photo_path, "rb") as f:
                media = InputMediaPhoto(f, caption=text, parse_mode="html")
                await message.edit_media(media=media, reply_markup=markup)
        except Exception:
            pass




async def topup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_path = os.path.join(ASSETS_DIR, "topup.jpg")
    reply_markup = InlineKeyboardMarkup(topup_keyboard())

    query = update.callback_query
    if query is not None:
        await query.answer()
        with open(photo_path, "rb") as f:
            media = InputMediaPhoto(f, caption="Баланс:")
            await query.edit_message_media(media=media, reply_markup=reply_markup)
        return

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
        # await wallet_topup_select_targets(update, context)
        # await query.answer()
        await handle_balance_top_up(update, context)
        # await query.edit_message_caption("Пополнение баланса...", reply_markup=None)
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
    

# ---------------------------------------------------------
# TOPUP FLOW (targets + amount; Bitpapa hook)
# ---------------------------------------------------------

async def wallet_topup_select_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        user = await session.get(AllUsers, query.from_user.id)
        if not user:
            await query.message.reply_text("Пользователь не найден.")
            return

        result = await session.execute(
            select(FriendlyAccount)
            .where(FriendlyAccount.owner_user_id == user.user_id)
            .order_by(FriendlyAccount.created_at.asc())
            .limit(5)
        )
        friends = result.scalars().all()

    # -------------------------
    # FIX: do NOT reset targets
    # -------------------------
    targets = context.user_data.get("wallet_topup_targets")

    if not targets:
        targets = {"self": True}
        for fa in friends:
            targets[f"fa_{fa.id}"] = True
        context.user_data["wallet_topup_targets"] = targets

    text = "<b>Кому пополнить баланс?</b>\n\nОтметьте аккаунты:\n"
    keyboard = []

    mark = "✅" if targets.get("self") else "☑️"
    keyboard.append([
        InlineKeyboardButton(
            f"{mark} Я сам",
            callback_data="wallet_topup_toggle:self",
        )
    ])

    for fa in friends:
        key = f"fa_{fa.id}"
        mark = "✅" if targets.get(key) else "☑️"
        uname = f"@{fa.friend_username}" if fa.friend_username else "(без username)"
        fname = fa.friend_fullname or ""
        keyboard.append([
            InlineKeyboardButton(
                f"{mark} {uname} {fname}",
                callback_data=f"wallet_topup_toggle:{key}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton("Продолжить", callback_data="wallet_topup_choose_amount")
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="back:topup")
    ])

    await _safe_edit(query.message, text, keyboard)



async def wallet_topup_toggle_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # print("🔥 TOGGLE HANDLER REACHED:", update.callback_query.data)

    query = update.callback_query
    await query.answer()

    _, key = query.data.split(":")
    targets = context.user_data.get("wallet_topup_targets") or {}
    if key in targets:
        targets[key] = not targets[key]
    context.user_data["wallet_topup_targets"] = targets

    await wallet_topup_select_targets(update, context)


async def wallet_topup_choose_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    targets = context.user_data.get("wallet_topup_targets") or {}
    if not any(targets.values()):
        await query.message.reply_text("Нужно выбрать хотя бы один аккаунт.")
        return

    text = (
        "<b>Выберите сумму пополнения (за одного аккаунта)</b>\n\n"
        "Итоговая сумма будет умножена на количество выбранных аккаунтов.\n"
    )

    keyboard = [
        [InlineKeyboardButton("$5", callback_data="wallet_topup_amount:500")],
        [InlineKeyboardButton("$10", callback_data="wallet_topup_amount:1000")],
        [InlineKeyboardButton("$20", callback_data="wallet_topup_amount:2000")],
        [InlineKeyboardButton("$50", callback_data="wallet_topup_amount:5000")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="wallet_topup_select_targets")],
    ]

    await _safe_edit(query.message, text, keyboard)


async def wallet_topup_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, amount_str = query.data.split(":")
    per_account_cents = int(amount_str)
    targets = context.user_data.get("wallet_topup_targets") or {}

    selected_keys = [k for k, v in targets.items() if v]
    if not selected_keys:
        await query.message.reply_text("Нужно выбрать хотя бы один аккаунт.")
        return

    accounts_count = len(selected_keys)
    total_cents = per_account_cents * accounts_count

    context.user_data["wallet_topup_per_account_cents"] = per_account_cents
    context.user_data["wallet_topup_total_cents"] = total_cents
    context.user_data["wallet_topup_selected_keys"] = selected_keys

    text = (
        "<b>Подтверждение пополнения</b>\n\n"
        f"Сумма за одного аккаунта: {per_account_cents / 100:.2f} $\n"
        f"Количество аккаунтов: {accounts_count}\n"
        f"Итоговая сумма: {total_cents / 100:.2f} $\n\n"
        "После оплаты баланс каждого выбранного аккаунта будет увеличен на указанную сумму."
    )

    keyboard = [
        [InlineKeyboardButton("Перейти к оплате", callback_data="wallet_topup_pay")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="wallet_topup_choose_amount")],
    ]

    await _safe_edit(query.message, text, keyboard)


async def wallet_topup_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    bitpapa: BitpapaService = context.application.bot_data["bitpapa_service"]

    total_cents = context.user_data.get("wallet_topup_total_cents")
    per_account_cents = context.user_data.get("wallet_topup_per_account_cents")
    selected_keys = context.user_data.get("wallet_topup_selected_keys") or []

    if not total_cents or not selected_keys:
        return await query.message.reply_text("Ошибка: нет данных для пополнения.")

    tg_id = query.from_user.id

    # ---------------------------------------------------------
    # 1. Load user with FOR UPDATE
    # ---------------------------------------------------------
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(AllUsers)
                .where(AllUsers.user_id == tg_id)
                .with_for_update()
            )
            user_db = result.scalar_one_or_none()

    if not user_db or user_db.user_blocked == 1:
        keyboard = [
            [InlineKeyboardButton("Выбрать доп аккаунт 💵", callback_data="count")],
        ]
        return await query.message.reply_text(
            "Невозможно пополнить баланс.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # ---------------------------------------------------------
    # 2. Create Bitpapa invoice
    # ---------------------------------------------------------
    final_price = total_cents / 100  # convert to dollars for Bitpapa

    invoice_result = await bitpapa.create_invoice("USDT", final_price)
    invoice_amount_cents = int(invoice_result.invoice.amount * 100)

    # ---------------------------------------------------------
    # 3. Save invoice + selected accounts to DB
    # ---------------------------------------------------------
    # === ИСПРАВЛЕННЫЙ БЛОК СОХРАНЕНИЯ ===
    # Все операции выполняются строго внутри одной сессии и транзакции
    async with SessionLocal() as session:
        async with session.begin():
            invoice_db = AllInvoices(
                invoice_id=invoice_result.invoice.id,
                user_id=tg_id,
                username=update.effective_user.username,
                user_full_name=update.effective_user.full_name,
                invoice_curency=invoice_result.invoice.currency,
                invoice_status=invoice_result.invoice.status,
                invoice_ammount=int(float(invoice_result.invoice.amount)),
                invoice_ammount_fact=int(float(invoice_result.invoice.amount_fact or 0)),
                accounts_ammount=len(selected_keys),
                invoice_target="topup",
                invoice_source="bitpapa",
                invoice_url=invoice_result.invoice.url,
                invoice_created_at=datetime.fromisoformat(invoice_result.invoice.created_at),
                invoice_updated_at=datetime.fromisoformat(invoice_result.invoice.updated_at),
                processing_status="pending"
            )
            session.add(invoice_db)
            
            # Цикл сохранения целей теперь находится ВНУТРИ транзакции
            for key in selected_keys:
                if key == "self":
                    target = InvoiceTopupTargets(
                        invoice_id=invoice_result.invoice.id,
                        target_type="self"
                    )
                    session.add(target)
                elif key.startswith("friend_"):
                    friend_id = int(key.split("_")[1])
                    target = InvoiceTopupTargets(
                        invoice_id=invoice_result.invoice.id,
                        target_type="friend",
                        friend_user_id=friend_id
                    )
                    session.add(target)
                    
            # SQLAlchemy автоматически сделает commit здесь при выходе из context manager
    # === КОНЕЦ ИСПРАВЛЕННОГО БЛОКА ===


    # ---------------------------------------------------------
    # 4. Show payment button
    # ---------------------------------------------------------
    keyboard = [[InlineKeyboardButton("Оплатить", url=invoice_result.invoice.url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "<b>Оплата</b>\n\n"
        f"Итоговая сумма: {final_price:.2f} $\n"
        "После оплаты баланс каждого выбранного аккаунта будет увеличен."
    )

    await _safe_edit(query.message, text, keyboard)



def register_topup_handlers(application):
    application.add_handler(CallbackQueryHandler(wallet_topup_toggle_target, pattern="^wallet_topup_toggle:.+"))
    application.add_handler(CallbackQueryHandler(wallet_topup_select_targets, pattern="^wallet_topup_select_targets$"))
    application.add_handler(CallbackQueryHandler(wallet_topup_choose_amount, pattern="^wallet_topup_choose_amount$"))
    application.add_handler(CallbackQueryHandler(wallet_topup_amount, pattern="^wallet_topup_amount:\d+$"))
    application.add_handler(CallbackQueryHandler(wallet_topup_pay, pattern="^wallet_topup_pay$"))

    # Router LAST
    application.add_handler(
        CallbackQueryHandler(topup_callback_router, pattern="^(balance_top_up|pay_help|apeal_account_didnt_paid|back:topup)$")
    )