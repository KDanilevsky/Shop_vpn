import logging
from datetime import datetime, timezone

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
)
from sqlalchemy import select

from db.async_db import SessionLocal
from db.models import AllUsers, AllInvoices, InvoiceItems
from services.events import create_pg_event
from config import (
    UPDATED_PRICE,
    UPDATED_MIN_PAY,
    DISCOUNT_BASE_PROCENTS_PROMO,
    DISCOUNT_BASE_PROCENTS,
    BOT_SHOP_NAME,
)
from services.bitpapa import BitpapaService

logger = logging.getLogger(__name__)

SERVER_LABELS = {
    1: "🇺🇸 USA",
    2: "🇩🇪 Germany",
    3: "🇳🇱 Netherlands",
    4: "🇸🇬 Singapore",
}


def _format_server_label(srv: int | None):
    if srv in (None, 0, "NONE"):
        return "❌ Не выбран"
    return SERVER_LABELS.get(int(srv), f"ID {srv}")


def _now_utc_ms() -> int:
    now = datetime.now(timezone.utc)
    return int(now.timestamp() * 1000)

from db.models import UserSubscription  # new model mapped to user_subscriptions
from config import MAX_SUBSCRIPTION_SLOTS

async def _load_user_slots(session, user_id: int):
    res = await session.execute(
        select(UserSubscription)
        .where(UserSubscription.user_id == user_id)
        .order_by(UserSubscription.slot_number)
    )
    return res.scalars().all()




def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _compute_billable_slots(slots: list[UserSubscription]) -> list[dict]:
    now_ms = _now_utc_ms()
    billable = []
    for s in slots:
        if s.server_country_id not in (None, 0):
            if not s.stop_time or s.stop_time <= now_ms:
                billable.append({"slot": s.slot_number, "server": int(s.server_country_id)})
    return billable

SLOTS_PER_PAGE = 5

# def _build_slots_page_keyboard(
#     slots: list[UserSubscription],
#     page: int,
#     total_slots_allowed: int,
# ):
#     """
#     page: 0-based
#     """
#     start = page * SLOTS_PER_PAGE
#     end = start + SLOTS_PER_PAGE

#     keyboard: list[list[InlineKeyboardButton]] = []

#     # Ensure we show up to total_slots_allowed, even if some slots don't exist yet
#     for idx in range(start, min(end, total_slots_allowed)):
#         slot_number = idx + 1
#         slot = next((s for s in slots if s.slot_number == slot_number), None)

#         if slot and slot.server_id not in (None, 0):
#             label = f"Акк {slot_number}: {_format_server_label(slot.server_id)}"
#         else:
#             label = f"Акк {slot_number}: пусто"

#         keyboard.append([
#             InlineKeyboardButton(
#                 label,
#                 callback_data=f"choose_server:{slot_number}"
#             )
#         ])

#     nav_row = []
#     if page > 0:
#         nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"subs_page:{page-1}"))
#     if end < total_slots_allowed:
#         nav_row.append(InlineKeyboardButton("➡️", callback_data=f"subs_page:{page+1}"))
#     if nav_row:
#         keyboard.append(nav_row)

#     keyboard.append([
#         InlineKeyboardButton("Все сервера выбраны ✅", callback_data="subs_save")
#     ])

#     keyboard.append([InlineKeyboardButton("Назад", callback_data="back:wallet")])

#     return keyboard


def calculate_price(quantity_paid: int, billable_slots: list[dict], promo_active: int):
    """
    billable_slots: list of {"acc": int, "server": int} for slots that need to be paid
    (new or expired). Active slots (stop > now) are NOT included here.
    """
    subs_chosen = len(billable_slots)
    if subs_chosen == 0:
        return 0.0, 0, []

    details = []

    # PROMO: first paid subscription gets promo discount, others full price
    if promo_active == 1:
        total_price = 0.0
        for i, item in enumerate(billable_slots):
            if i == 0:
                discount_percent = DISCOUNT_BASE_PROCENTS_PROMO
            else:
                discount_percent = 0
            discount_amount = UPDATED_PRICE * discount_percent / 100
            final_price = UPDATED_PRICE - discount_amount
            details.append(
                {
                    "acc": item["acc"],
                    "server": item["server"],
                    "is_free": False,
                    "discount_percent": int(discount_percent),
                    "discount_amount": round(discount_amount, 2),
                    "base_price": UPDATED_PRICE,
                    "final_price": round(final_price, 2),
                }
            )
            total_price += final_price
        return round(total_price, 2), 0, details

    # BASE DISCOUNT LOGIC (non-promo)
    # quantity_paid = already paid subscriptions historically
    # subs_chosen = number of billable slots in this purchase
    T = quantity_paid + subs_chosen
    total_discount = T * 2.5  # your existing logic

    free_acc = int(total_discount // 100)
    free_acc = min(free_acc, subs_chosen)
    remaining_discount = total_discount - free_acc * 100

    total_price = 0.0
    paid_accounts = subs_chosen - free_acc

    free_indices = set(range(free_acc))
    first_paid_index = free_acc if paid_accounts > 0 else None

    for i, item in enumerate(billable_slots):
        if i in free_indices:
            discount_percent = 100
            discount_amount = UPDATED_PRICE
            final_price = 0.0
            is_free = True
        else:
            if first_paid_index is not None and i == first_paid_index:
                discount_percent = remaining_discount
            else:
                discount_percent = 0
            discount_amount = UPDATED_PRICE * discount_percent / 100
            final_price = UPDATED_PRICE - discount_amount
            is_free = False

        details.append(
            {
                "acc": item["acc"],
                "server": item["server"],
                "is_free": is_free,
                "discount_percent": int(discount_percent),
                "discount_amount": round(discount_amount, 2),
                "base_price": UPDATED_PRICE,
                "final_price": round(final_price, 2),
            }
        )
        total_price += final_price

    return round(total_price, 2), free_acc, details


# def _init_buffered_servers(context, user_db: AllUsers, now_ms: int):
#     """
#     Returns list of desired servers per slot (1..5), taking into account
#     pending server changes (subscription_server_next_id_X) if subscription is active.
#     """
#     buf = context.user_data.get("subs_servers")
#     if buf is not None:
#         return buf

#     servers = []
#     for i in range(1, 6):
#         current = getattr(user_db, f"subscription_server_id_{i}")
#         next_id = getattr(user_db, f"subscription_server_next_id_{i}", 0)
#         pending = getattr(user_db, f"subscription_server_pending_{i}", False)
#         stop = getattr(user_db, f"subscription_stop_id_{i}")

#         if pending and next_id and stop and stop > now_ms:
#             servers.append(next_id)
#         else:
#             servers.append(current)

#     context.user_data["subs_servers"] = servers
#     logger.debug("Init subs_servers buffer from DB: %s", servers)
#     return servers

async def count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("subs_busy"):
        return
    context.user_data["subs_busy"] = True

    try:
        # Determine source of update
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            tg_user = query.from_user
            message = query.message
        else:
            tg_user = update.effective_user
            message = update.effective_message

        async with SessionLocal() as session:
            user_db = await session.get(AllUsers, tg_user.id)
            if not user_db:
                return

            # Load existing slots ONLY
            res = await session.execute(
                select(UserSubscription)
                .where(UserSubscription.user_id == tg_user.id)
                .order_by(UserSubscription.slot_number)
            )
            slots = res.scalars().all()

            now = datetime.now(timezone.utc)
            now_ms = int(now.timestamp() * 1000)

            # Compute remaining days
            remaining_days: dict[int, int] = {}
            for slot in slots:
                if slot.stop_time:
                    acc_time = slot.stop_time.astimezone(timezone.utc)
                    remaining_days[slot.slot_number] = (acc_time - now).days
                else:
                    remaining_days[slot.slot_number] = 0

            # Billable slots
            billable_slots = []
            for slot in slots:
                if slot.server_country_id not in (None, 0):
                    if not slot.stop_time or slot.stop_time <= now:
                        billable_slots.append({
                            "acc": slot.slot_number,
                            "server": slot.server_country_id,
                        })

            quantity_paid = int(getattr(user_db, "quantity_guests_paid", 0))
            promo_active = getattr(user_db, "user_promo_new", 0)
            promo_until = getattr(user_db, "user_promo_new_days", 0)
            balance_all = int(user_db.user_balance or 0)

            if promo_active == 1 and now_ms > promo_until:
                user_db.user_promo_new = 0
                promo_active = 0
                await session.commit()

            total_price, free_acc, invoice_details = calculate_price(
                quantity_paid,
                billable_slots,
                promo_active,
            )

            subs_chosen = len(billable_slots)

            # Save context for invoice creation
            context.user_data["accounts_amount"] = subs_chosen
            context.user_data["counted_price_last"] = total_price
            context.user_data["quantity_guests_paid_last"] = quantity_paid
            context.user_data["invoice_details"] = invoice_details

            saved = context.user_data.get("subs_saved_to_db", False)

            # Build keyboard
            keyboard = []
            slots_by_number = {s.slot_number: s for s in slots}
            existing_numbers = sorted(slots_by_number.keys())

            # 1) Show all existing slots
            for slot_number in existing_numbers:
                slot = slots_by_number[slot_number]
                server = slot.server_country_id

                if server not in (None, 0):
                    keyboard.append([
                        InlineKeyboardButton(
                            f"Изменить сервер для Акк {slot_number}",
                            callback_data=f"choose_server:{slot_number}"
                        )
                    ])
                else:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"Выбрать сервер для Акк {slot_number}",
                            callback_data=f"choose_server:{slot_number}"
                        )
                    ])

            # 2) Show "add new slot" button if allowed
            all_existing_filled = all(
                slots_by_number[s].server_country_id not in (None, 0)
                for s in existing_numbers
            )

            if (
                all_existing_filled
                and len(existing_numbers) < MAX_SUBSCRIPTION_SLOTS
            ):
                keyboard.append([
                    InlineKeyboardButton(
                        f"Выбрать сервер для Акк {len(existing_numbers) + 1}",
                        callback_data=f"choose_server:{len(existing_numbers) + 1}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton("Все сервера выбраны ✅", callback_data="subs_save")
            ])

            if subs_chosen > 0 and saved:
                keyboard.append([
                    InlineKeyboardButton("Выставить счет 💳", callback_data="create_invoice")
                ])

            keyboard.append([InlineKeyboardButton("Назад", callback_data="back:wallet")])

            # Build text
            text = f"{tg_user.full_name},\n"

            if promo_active == 1:
                text += (
                    f"<b>Активен промо-период.</b> "
                    f"Скидка {DISCOUNT_BASE_PROCENTS_PROMO}% на первую подписку.\n"
                )
            text += f"<b>Баланс:</b> {balance_all / 100:.2f} $\n"
            text += f"<b>Бесплатных аккаунтов:</b> {free_acc}\n"
            text += f"<b>Цена продления:</b> {total_price} $\n"
            text += f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $\n\n"

            # Show slot info
            for slot_number in existing_numbers:
                slot = slots_by_number[slot_number]
                server = slot.server_country_id
                days_left = remaining_days.get(slot_number, 0)

                if server not in (None, 0):
                    text += (
                        f"<b>Акк {slot_number}:</b> "
                        f"{_format_server_label(server)}, "
                        f"осталось {days_left} дней\n"
                    )
                else:
                    text += f"<b>Акк {slot_number}:</b> пусто\n"

            text += f"\n<i>Обновлено: {int(datetime.now().timestamp())}</i>"

            # Render
            try:
                if message.caption:
                    await message.edit_caption(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="html"
                    )
                else:
                    await message.edit_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="html"
                    )
            except Exception as e:
                logger.warning("Edit message failed for user %s: %s", tg_user.id, e)

    finally:
        context.user_data["subs_busy"] = False




# async def count(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     Main subscription screen:
#     - shows current servers and remaining days
#     - lets user choose/change servers
#     - calculates price ONLY for slots that need to be paid (new/expired)
#     """
#     if context.user_data.get("subs_busy"):
#         return
#     context.user_data["subs_busy"] = True

#     try:
#         if update.callback_query:
#             query = update.callback_query
#             await query.answer()
#             tg_user = query.from_user
#             message = query.message
#         else:
#             tg_user = update.effective_user
#             message = update.effective_message

#         async with SessionLocal() as session:
#             user_db = await session.get(AllUsers, tg_user.id)
#             if not user_db:
#                 return

#             balance_all = user_db.user_balance
#             quantity_paid = int(getattr(user_db, "quantity_guests_paid", 0))
#             promo_active = getattr(user_db, "user_promo_new", 0)
#             promo_until = getattr(user_db, "user_promo_new_days", 0)

#             now = datetime.now(timezone.utc)
#             now_ms = int(now.timestamp() * 1000)

#             subs_times = [
#                 user_db.subscription_stop_id_1,
#                 user_db.subscription_stop_id_2,
#                 user_db.subscription_stop_id_3,
#                 user_db.subscription_stop_id_4,
#                 user_db.subscription_stop_id_5,
#             ]

#             remaining_days = []
#             for t in subs_times:
#                 if t and t >= now_ms:
#                     acc_time = datetime.fromtimestamp(int(str(t)[:10])).astimezone(timezone.utc)
#                     remaining_days.append((acc_time - now).days)
#                 else:
#                     remaining_days.append(0)

#             if promo_active == 1 and now_ms > promo_until:
#                 user_db.user_promo_new = 0
#                 promo_active = 0
#                 await session.commit()

#             servers = _init_buffered_servers(context, user_db, now_ms)

#             # Determine which slots are billable (new or expired)
#             billable_slots = []
#             for i in range(5):
#                 acc_id = i + 1
#                 srv = servers[i]
#                 stop = subs_times[i]
#                 if srv not in (None, 0, "NONE"):
#                     # If no active subscription (stop <= now), this slot needs to be paid
#                     if not stop or stop <= now_ms:
#                         billable_slots.append({"acc": acc_id, "server": int(srv)})

#             total_price, free_acc, invoice_details = calculate_price(
#                 quantity_paid, billable_slots, promo_active
#             )

#             # accounts_amount = number of billable slots (not total selected)
#             subs_chosen = len(billable_slots)

#             context.user_data["accounts_amount"] = subs_chosen
#             context.user_data["counted_price_last"] = total_price
#             context.user_data["quantity_guests_paid_last"] = quantity_paid
#             context.user_data["invoice_details"] = invoice_details

#             text = f"{tg_user.full_name},\n"

#             if promo_active == 1:
#                 text += (
#                     f"<b>Активен промо-период.</b> "
#                     f"Скидка {DISCOUNT_BASE_PROCENTS_PROMO}% на первую подписку.\n"
#                 )

#             text += (
#                 f"<b>Баланс:</b> {balance_all} $\n"
#                 f"<b>Бесплатных аккаунтов (по скидке):</b> {free_acc}\n"
#                 f"<b>Цена продления (только новые/просроченные):</b> {total_price} $\n"
#                 f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $\n\n"
#             )

#             keyboard = []
#             first_empty_found = False

#             for i in range(5):
#                 acc_id = i + 1
#                 buf_srv = servers[i]
#                 days_left = remaining_days[i]

#                 current_srv = getattr(user_db, f"subscription_server_id_{acc_id}")
#                 next_srv = getattr(user_db, f"subscription_server_next_id_{acc_id}", 0)
#                 pending = getattr(user_db, f"subscription_server_pending_{acc_id}", False)
#                 stop = subs_times[i]

#                 if pending and next_srv and stop and stop > now_ms:
#                     text += (
#                         f"<b>Акк {acc_id}:</b> "
#                         f"Текущий: {_format_server_label(current_srv)}, "
#                         f"Следующий: {_format_server_label(buf_srv)}, "
#                         f"осталось {days_left} дней\n"
#                     )
#                 else:
#                     text += (
#                         f"<b>Акк {acc_id}:</b> "
#                         f"{_format_server_label(buf_srv)}, "
#                         f"осталось {days_left} дней\n"
#                     )

#                 if buf_srv not in (None, 0, "NONE"):
#                     keyboard.append([
#                         InlineKeyboardButton(
#                             f"Изменить сервер для Акк {acc_id}",
#                             callback_data=f"choose_server:{acc_id}"
#                         )
#                     ])
#                 else:
#                     if not first_empty_found:
#                         keyboard.append([
#                             InlineKeyboardButton(
#                                 f"Выбрать сервер для Акк {acc_id}",
#                                 callback_data=f"choose_server:{acc_id}"
#                             )
#                         ])
#                         first_empty_found = True

#             keyboard.append([
#                 InlineKeyboardButton("Все сервера выбраны ✅", callback_data="subs_save")
#             ])

#             # Invoice is only meaningful if there is at least one billable slot
#             if subs_chosen > 0 and context.user_data.get("subs_saved_to_db"):
#                 keyboard.append([
#                     InlineKeyboardButton("Выставить счет 💳", callback_data="create_invoice")
#                 ])

#             keyboard.append([InlineKeyboardButton("Назад", callback_data="back:wallet")])

#             reply_markup = InlineKeyboardMarkup(keyboard)
#             text += f"\n<i>Обновлено: {int(datetime.now().timestamp())}</i>"

#             try:
#                 if message.caption:
#                     await message.edit_caption(text, reply_markup=reply_markup, parse_mode="html")
#                 else:
#                     await message.edit_text(text, reply_markup=reply_markup, parse_mode="html")
#             except Exception as e:
#                 logger.warning("Edit message failed for user %s: %s", tg_user.id, e)
#     finally:
#         context.user_data["subs_busy"] = False

async def select_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, slot_str, server_str = query.data.split(":")
    slot_number = int(slot_str)
    server = int(server_str)

    async with SessionLocal() as session:
        async with session.begin():
            res = await session.execute(
                select(UserSubscription)
                .where(
                    UserSubscription.user_id == query.from_user.id,
                    UserSubscription.slot_number == slot_number,
                )
                .with_for_update()
            )
            slot = res.scalar_one_or_none()

            if not slot:
                slot = UserSubscription(user_id=query.from_user.id, slot_number=slot_number)
                session.add(slot)

            slot.server_country_id = server or None

    context.user_data["subs_saved_to_db"] = False
    await count(update, context)




async def choose_server_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, acc_id = query.data.split(":")
    acc_id = int(acc_id)

    servers_list = [
        (1, SERVER_LABELS[1]),
        (2, SERVER_LABELS[2]),
        (3, SERVER_LABELS[3]),
        (4, SERVER_LABELS[4]),
    ]

    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"select_server:{acc_id}:{sid}")]
        for sid, label in servers_list
    ]

    keyboard.append([
        InlineKeyboardButton("❌ Пусто / Отменить", callback_data=f"select_server:{acc_id}:0")
    ])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="count_back")])

    await query.edit_message_caption(
        caption=f"Выберите сервер для Аккаунта {acc_id}:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="html",
    )


# async def select_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     _, acc_id, server = query.data.split(":")
#     acc_id = int(acc_id)
#     server = int(server)

#     servers = context.user_data.get("subs_servers")
#     if servers is None:
#         async with SessionLocal() as session:
#             user_db = await session.get(AllUsers, query.from_user.id)
#             now_ms = _now_utc_ms()
#             servers = _init_buffered_servers(context, user_db, now_ms)

#     servers[acc_id - 1] = server
#     context.user_data["subs_saved_to_db"] = False

#     await count(update, context)

async def subs_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Сохранено!", show_alert=False)

    async with SessionLocal() as session:
        async with session.begin():
            slots = await _load_user_slots(session, query.from_user.id)

            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

            for slot in slots:
                if slot.server_country_id not in (None, 0):
                    if slot.stop_time and slot.stop_time > now_ms:
                        slot.server_next_id = slot.server_country_id
                        slot.server_pending = True
                    else:
                        slot.server_next_id = 0
                        slot.server_pending = False

    context.user_data["subs_saved_to_db"] = True
    await count(update, context)

# async def subs_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     Persist chosen servers:
#     - if subscription active (stop > now): set next_id + pending
#     - else: set current server immediately
#     """
#     query = update.callback_query
#     await query.answer("Сохранено!", show_alert=False)

#     servers = context.user_data.get("subs_servers")
#     if not servers:
#         return await count(update, context)

#     now_ms = _now_utc_ms()

#     async with SessionLocal() as session:
#         user_db = await session.get(AllUsers, query.from_user.id)
#         if not user_db:
#             return

#         for i in range(1, 6):
#             desired = servers[i - 1] or 0
#             stop = getattr(user_db, f"subscription_stop_id_{i}")

#             if stop and stop > now_ms:
#                 setattr(user_db, f"subscription_server_next_id_{i}", desired)
#                 setattr(user_db, f"subscription_server_pending_{i}", True)
#             else:
#                 setattr(user_db, f"subscription_server_id_{i}", desired)
#                 setattr(user_db, f"subscription_server_next_id_{i}", 0)
#                 setattr(user_db, f"subscription_server_pending_{i}", False)

#         await session.commit()

#     context.user_data["subs_saved_to_db"] = True

#     await count(update, context)


async def count_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await count(update, context)


async def create_invoice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Called when user presses 'Выставить счет 💳'.

    Decision:
    - if user balance >= price_cents -> create internal invoice
    - else -> create Bitpapa invoice
    """
    query = update.callback_query
    await query.answer()

    bitpapa: BitpapaService = context.application.bot_data["bitpapa_service"]
    user_id = query.from_user.id

    accounts_amount = context.user_data.get("accounts_amount")
    price = context.user_data.get("counted_price_last")
    quantity_guests_paid_last = context.user_data.get("quantity_guests_paid_last")
    invoice_details = context.user_data.get("invoice_details") or []

    if not accounts_amount or price is None or not invoice_details:
        await query.message.reply_text(
            "Ошибка: данные о подписке не найдены. Попробуйте снова."
        )
        return

    async with SessionLocal() as session:
        async with session.begin():
            # 1. Lock user
            user_db = await session.get(AllUsers, user_id, with_for_update=True)
            if not user_db or getattr(user_db, "user_blocked", 0) == 1:
                await query.message.reply_text("Невозможно продлить подписку.")
                return

            # 2. CANCEL older pending subscription invoices (Option C)
            q = (
                select(AllInvoices)
                .where(
                    AllInvoices.user_id == user_id,
                    AllInvoices.invoice_target.in_(["subscription_renew", "subscription_renew_internal"]),
                    AllInvoices.invoice_status == "pending",
                    AllInvoices.processing_status.in_(["pending", "processing"]),
                )
                .with_for_update()
            )
            r = await session.execute(q)
            old_invoices = r.scalars().all()

            for inv in old_invoices:
                inv.processing_status = "canceled"
                inv.invoice_status = "canceled"
                inv.invoice_updated_at = datetime.now(timezone.utc)
                session.add(inv)

            # 3. Compute price
            price_cents = int(max(price, UPDATED_MIN_PAY) * 100)

            # 4. INTERNAL invoice path
            if (user_db.user_balance or 0) >= price_cents:
                invoice_id = await _create_internal_invoice_for_subscription(
                    session,
                    user_db,
                    accounts_amount,
                    price_cents,
                    invoice_details,
                )
                await query.message.reply_text(
                    f"Сумма {price}$ списана с баланса. Подписка будет продлена автоматически."
                )
                return

            # 5. BITPAPA invoice path
            url, final_price = await _create_bitpapa_invoice_for_subscription(
                session,
                bitpapa,
                user_db,
                accounts_amount,
                price,
                invoice_details,
            )

    # 6. Send payment link
    keyboard = [[InlineKeyboardButton("Оплатить", url=url)]]

    text = (
        f"Продление подписки {BOT_SHOP_NAME}: 30 дней\n"
        f"Аккаунтов (новых/просроченных): {accounts_amount}\n"
        f"Стоимость: {price} $\n"
        f"Скидка: {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n\n"
        "Скидка начисляется последовательно:\n"
        "До 100% — на 1-й аккаунт, свыше — на 2-й, и т.д.\n"
        f"{url}\n"
    )

    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def _create_internal_invoice_for_subscription(
    session,
    user_db: AllUsers,
    accounts_amount: int,
    price_cents: int,
    invoice_details: list[dict],
) -> str:
    now = datetime.now(timezone.utc)
    invoice_id = f"int_{user_db.user_id}_{int(now.timestamp() * 1000)}"

    invoice_db = AllInvoices(
        user_id=user_db.user_id,
        username=user_db.username,
        user_full_name=user_db.user_full_name,
        invoice_id=invoice_id,
        invoice_curency="USDT",
        accounts_ammount=accounts_amount,
        invoice_ammount=price_cents,
        invoice_ammount_fact=price_cents,
        invoice_status="pending",          # <‑‑ NOT PAID YET
        processing_status="pending",       # <‑‑ invoice_processor will pick it up
        invoice_created_at=now,
        invoice_updated_at=now,
        invoice_target="subscription_renew_internal",
        invoice_source="internal_balance",
        promo=getattr(user_db, "user_promo_new", 0),
        quantity_guests_paid=getattr(user_db, "quantity_guests_paid", 0),
        invoice_url=None,
    )
    session.add(invoice_db)

    for d in invoice_details:
        item = InvoiceItems(
            invoice_id=invoice_id,
            acc_number=d["acc"],
            server_country_id=d["server"],   # <‑‑ correct field
            is_free=d["is_free"],
            discount_percent=d["discount_percent"],
            discount_amount=d["discount_amount"],
            price=d["base_price"],
            final_price=d["final_price"],
            provisioned=False,
            provisioned_at=None,
        )
        session.add(item)

    await session.flush()

    # DO NOT fire invoice_paid here
    # invoice_processor will pick it up via periodic scan or event "invoice_created"
    await create_pg_event("int_invoice_created", {"invoice_id": invoice_id}, session=session)

    return invoice_id

async def _create_bitpapa_invoice_for_subscription(
    session,
    bitpapa: BitpapaService,
    user_db: AllUsers,
    accounts_amount: int,
    price: float,
    invoice_details: list[dict],
):
    final_price = max(price, UPDATED_MIN_PAY)
    invoice_result = await bitpapa.create_invoice("USDT", final_price)
    res_invoice_amount = int(invoice_result.invoice.amount * 100)

    created_at = datetime.fromisoformat(invoice_result.invoice.created_at)
    updated_at = datetime.fromisoformat(invoice_result.invoice.updated_at)

    invoice_db = AllInvoices(
        user_id=user_db.user_id,
        username=user_db.username,
        user_full_name=user_db.user_full_name,
        invoice_id=invoice_result.invoice.id,
        invoice_curency=invoice_result.invoice.currency_code,  # "USDT"
        accounts_ammount=accounts_amount,
        invoice_ammount=res_invoice_amount,                    # what Bitpapa expects
        invoice_ammount_fact=int(round(price * 100)),              # what user should pay logically
        invoice_status=invoice_result.invoice.status,          # "pending"
        processing_status="pending",
        invoice_created_at=created_at,
        invoice_updated_at=updated_at,
        invoice_target="subscription_renew",
        invoice_source="bitpapa",
        promo=getattr(user_db, "user_promo_new", 0),
        quantity_guests_paid=getattr(user_db, "quantity_guests_paid", 0),
        invoice_url=invoice_result.invoice.url,
    )
    session.add(invoice_db)

    for d in invoice_details:
        item = InvoiceItems(
            invoice_id=invoice_result.invoice.id,
            acc_number=d["acc"],
            server_country_id=d["server"],   # <‑‑ IMPORTANT: country, not server_id
            is_free=d["is_free"],
            discount_percent=d["discount_percent"],
            discount_amount=d["discount_amount"],
            price=d["base_price"],
            final_price=d["final_price"],
            provisioned=False,
            provisioned_at=None,
        )
        session.add(item)

    return invoice_result.invoice.url, final_price

# async def bitpappa_create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     Create Bitpapa invoice ONLY for billable slots (new/expired).
#     Active slots (stop > now) are not charged here.
#     """
#     query = update.callback_query
#     await query.answer()

#     bitpapa: BitpapaService = context.application.bot_data["bitpapa_service"]
#     user_id = query.from_user.id

#     async with SessionLocal() as session:
#         async with session.begin():
#             result = await session.execute(
#                 select(AllUsers)
#                 .where(AllUsers.user_id == user_id)
#                 .with_for_update()
#             )
#             user_db = result.scalar_one_or_none()

#     if not user_db or getattr(user_db, "user_blocked", 0) == 1:
#         keyboard = [[InlineKeyboardButton("Выбрать доп аккаунт 💵", callback_data="count")]]
#         await query.message.reply_text(
#             "Невозможно продлить подписку.",
#             reply_markup=InlineKeyboardMarkup(keyboard),
#         )
#         return

#     accounts_amount = context.user_data.get("accounts_amount")
#     price = context.user_data.get("counted_price_last")
#     quantity_guests_paid_last = context.user_data.get("quantity_guests_paid_last")
#     invoice_details = context.user_data.get("invoice_details") or []

#     if not accounts_amount or price is None or not invoice_details:
#         await query.message.reply_text(
#             "Ошибка: данные о подписке не найдены. Попробуйте снова."
#         )
#         return

#     now = datetime.now(timezone.utc)
#     now_ms = int(now.timestamp() * 1000)

#     subs_times = [
#         user_db.subscription_stop_id_1,
#         user_db.subscription_stop_id_2,
#         user_db.subscription_stop_id_3,
#         user_db.subscription_stop_id_4,
#         user_db.subscription_stop_id_5,
#     ]

#     remaining_days = []
#     for t in subs_times:
#         if t and t >= now_ms:
#             acc_time = datetime.fromtimestamp(int(str(t)[:10])).astimezone(timezone.utc)
#             remaining_days.append((acc_time - now).days)
#         else:
#             remaining_days.append(0)

#     chosen_accs = [d["acc"] for d in invoice_details]
#     make_invoice = any(remaining_days[acc - 1] <= 15 for acc in chosen_accs)

#     if not make_invoice:
#         keyboard = [[InlineKeyboardButton("Выбрать доп аккаунт 💵", callback_data="count")]]
#         await query.message.reply_text(
#             "Продление возможно только если осталось меньше 15 дней.",
#             reply_markup=InlineKeyboardMarkup(keyboard),
#         )
#         return

#     final_price = max(price, UPDATED_MIN_PAY)
#     invoice_result = await bitpapa.create_invoice("USDT", final_price)
#     res_invoice_amount = int(invoice_result.invoice.amount * 100)

#     async with SessionLocal() as session:
#         async with session.begin():
#             invoice_db = AllInvoices(
#                 user_id=user_id,
#                 username=query.from_user.username,
#                 user_full_name=query.from_user.full_name,
#                 invoice_id=invoice_result.invoice.id,
#                 invoice_curency=invoice_result.invoice.currency_code,
#                 accounts_ammount=accounts_amount,
#                 invoice_ammount=res_invoice_amount,
#                 invoice_ammount_fact=int(price * 100),
#                 invoice_status=invoice_result.invoice.status,
#                 invoice_created_at=datetime.fromisoformat(invoice_result.invoice.created_at),
#                 invoice_updated_at=datetime.fromisoformat(invoice_result.invoice.updated_at),
#                 invoice_target="subscription_renew",
#                 promo=getattr(user_db, "user_promo_new", 0),
#                 quantity_guests_paid=getattr(user_db, "quantity_guests_paid", 0),
#                 invoice_url=invoice_result.invoice.url,
#             )
#             session.add(invoice_db)

#             for d in invoice_details:
#                 item = InvoiceItems(
#                     invoice_id=invoice_result.invoice.id,
#                     acc_number=d["acc"],
#                     server_country_id=d["server"],
#                     is_free=d["is_free"],
#                     discount_percent=d["discount_percent"],
#                     discount_amount=d["discount_amount"],
#                     price=d["base_price"],
#                     final_price=d["final_price"],
#                     provisioned=False,
#                     provisioned_at=None,
#                 )
#                 session.add(item)

#     keyboard = [[InlineKeyboardButton("Оплатить", url=invoice_result.invoice.url)]]

#     text = (
#         f"Продление подписки {BOT_SHOP_NAME}: 30 дней\n"
#         f"Аккаунтов (новых/просроченных): {accounts_amount}\n"
#         f"Стоимость: {price} $\n"
#         f"Скидка: {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n\n"
#         "Скидка начисляется последовательно:\n"
#         "До 100% — на 1-й аккаунт, свыше — на 2-й, и т.д.\n"
#         f"{invoice_result.invoice.url}\n"
#     )

#     await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


def register_subscription_handlers(application):
    application.add_handler(CallbackQueryHandler(choose_server_menu, pattern=r"^choose_server:\d+$"))
    application.add_handler(CallbackQueryHandler(select_server, pattern=r"^select_server:\d+:\d+$"))
    application.add_handler(CallbackQueryHandler(subs_save, pattern=r"^subs_save$"))
    application.add_handler(CallbackQueryHandler(count_back, pattern=r"^count_back$"))
    # application.add_handler(CallbackQueryHandler(bitpappa_create_invoice, pattern=r"^create_invoice$"))
    application.add_handler(CallbackQueryHandler(create_invoice_handler, pattern="^create_invoice$"))


# import logging
# from datetime import datetime, timezone

# from telegram import (
#     Update,
#     InlineKeyboardButton,
#     InlineKeyboardMarkup,
# )
# from telegram.ext import (
#     ContextTypes,
#     CallbackQueryHandler,
# )
# from sqlalchemy import select

# from db.async_db import SessionLocal
# from db.models import AllUsers, AllInvoices, InvoiceItems
# from config import (
#     UPDATED_PRICE,
#     UPDATED_MIN_PAY,
#     DISCOUNT_BASE_PROCENTS_PROMO,
#     DISCOUNT_BASE_PROCENTS,
#     BOT_SHOP_NAME,
# )
# from services.bitpapa import BitpapaService  # adjust import

# logger = logging.getLogger(__name__)

# SERVER_LABELS = {
#     1: "🇺🇸 USA",
#     2: "🇩🇪 Germany",
#     3: "🇳🇱 Netherlands",
#     4: "🇸🇬 Singapore",
# }


# def _format_server_label(srv: int | None):
#     if srv in (None, 0, "NONE"):
#         return "❌ Не выбран"
#     return SERVER_LABELS.get(int(srv), f"ID {srv}")


# def _now_utc_ms() -> int:
#     now = datetime.now(timezone.utc)
#     return int(now.timestamp() * 1000)


# def calculate_price(quantity_paid: int, servers: list[int | None], promo_active: int):
#     chosen = []
#     for idx, srv in enumerate(servers, start=1):
#         if srv not in (None, 0, "NONE"):
#             chosen.append({"acc": idx, "server": int(srv)})

#     subs_chosen = len(chosen)
#     if subs_chosen == 0:
#         return 0.0, 0, []

#     details = []

#     if promo_active == 1:
#         total_price = 0.0
#         for i, item in enumerate(chosen):
#             if i == 0:
#                 discount_percent = DISCOUNT_BASE_PROCENTS_PROMO
#             else:
#                 discount_percent = 0
#             discount_amount = UPDATED_PRICE * discount_percent / 100
#             final_price = UPDATED_PRICE - discount_amount
#             details.append(
#                 {
#                     "acc": item["acc"],
#                     "server": item["server"],
#                     "is_free": False,
#                     "discount_percent": int(discount_percent),
#                     "discount_amount": round(discount_amount, 2),
#                     "base_price": UPDATED_PRICE,
#                     "final_price": round(final_price, 2),
#                 }
#             )
#             total_price += final_price
#         return round(total_price, 2), 0, details

#     T = quantity_paid + subs_chosen
#     total_discount = T * 2.5

#     free_acc = int(total_discount // 100)
#     free_acc = min(free_acc, subs_chosen)
#     remaining_discount = total_discount - free_acc * 100

#     total_price = 0.0
#     paid_accounts = subs_chosen - free_acc

#     free_indices = set(range(free_acc))
#     first_paid_index = free_acc if paid_accounts > 0 else None

#     for i, item in enumerate(chosen):
#         if i in free_indices:
#             discount_percent = 100
#             discount_amount = UPDATED_PRICE
#             final_price = 0.0
#             is_free = True
#         else:
#             if first_paid_index is not None and i == first_paid_index:
#                 discount_percent = remaining_discount
#             else:
#                 discount_percent = 0
#             discount_amount = UPDATED_PRICE * discount_percent / 100
#             final_price = UPDATED_PRICE - discount_amount
#             is_free = False

#         details.append(
#             {
#                 "acc": item["acc"],
#                 "server": item["server"],
#                 "is_free": is_free,
#                 "discount_percent": int(discount_percent),
#                 "discount_amount": round(discount_amount, 2),
#                 "base_price": UPDATED_PRICE,
#                 "final_price": round(final_price, 2),
#             }
#         )
#         total_price += final_price

#     return round(total_price, 2), free_acc, details


# def _init_buffered_servers(context, user_db: AllUsers, now_ms: int):
#     buf = context.user_data.get("subs_servers")
#     if buf is not None:
#         return buf

#     servers = []
#     for i in range(1, 6):
#         current = getattr(user_db, f"subscription_server_id_{i}")
#         next_id = getattr(user_db, f"subscription_server_next_id_{i}", 0)
#         pending = getattr(user_db, f"subscription_server_pending_{i}", False)
#         stop = getattr(user_db, f"subscription_stop_id_{i}")

#         if pending and next_id and stop and stop > now_ms:
#             servers.append(next_id)
#         else:
#             servers.append(current)

#     context.user_data["subs_servers"] = servers
#     logger.debug("Init subs_servers buffer from DB: %s", servers)
#     return servers


# async def count(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if context.user_data.get("subs_busy"):
#         return
#     context.user_data["subs_busy"] = True

#     try:
#         if update.callback_query:
#             query = update.callback_query
#             await query.answer()
#             tg_user = query.from_user
#             message = query.message
#         else:
#             tg_user = update.effective_user
#             message = update.effective_message

#         async with SessionLocal() as session:
#             user_db = await session.get(AllUsers, tg_user.id)
#             if not user_db:
#                 return

#             balance_all = user_db.user_balance
#             quantity_paid = int(user_db.quantity_guests_paid)
#             promo_active = user_db.user_promo_new
#             promo_until = user_db.user_promo_new_days

#             now = datetime.now(timezone.utc)
#             now_ms = int(now.timestamp() * 1000)

#             subs_times = [
#                 user_db.subscription_stop_id_1,
#                 user_db.subscription_stop_id_2,
#                 user_db.subscription_stop_id_3,
#                 user_db.subscription_stop_id_4,
#                 user_db.subscription_stop_id_5,
#             ]

#             remaining_days = []
#             for t in subs_times:
#                 if t and t >= now_ms:
#                     acc_time = datetime.fromtimestamp(int(str(t)[:10])).astimezone(timezone.utc)
#                     remaining_days.append((acc_time - now).days)
#                 else:
#                     remaining_days.append(0)

#             if promo_active == 1 and now_ms > promo_until:
#                 user_db.user_promo_new = 0
#                 promo_active = 0
#                 await session.commit()

#             servers = _init_buffered_servers(context, user_db, now_ms)

#             total_price, free_acc, invoice_details = calculate_price(
#                 quantity_paid, servers, promo_active
#             )
#             subs_chosen = len([s for s in servers if s not in (None, 0, "NONE")])

#             context.user_data["accounts_amount"] = subs_chosen
#             context.user_data["counted_price_last"] = total_price
#             context.user_data["quantity_guests_paid_last"] = quantity_paid
#             context.user_data["invoice_details"] = invoice_details

#             text = f"{tg_user.full_name},\n"

#             if promo_active == 1:
#                 text += (
#                     f"<b>Активен промо-период.</b> "
#                     f"Скидка {DISCOUNT_BASE_PROCENTS_PROMO}% на первую подписку.\n"
#                 )

#             text += (
#                 f"<b>Баланс:</b> {balance_all} $\n"
#                 f"<b>Бесплатных аккаунтов:</b> {free_acc}\n"
#                 f"<b>Цена продления:</b> {total_price} $\n"
#                 f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $\n\n"
#             )

#             keyboard = []
#             first_empty_found = False

#             for i in range(5):
#                 acc_id = i + 1
#                 buf_srv = servers[i]
#                 days_left = remaining_days[i]

#                 current_srv = getattr(user_db, f"subscription_server_id_{acc_id}")
#                 next_srv = getattr(user_db, f"subscription_server_next_id_{acc_id}", 0)
#                 pending = getattr(user_db, f"subscription_server_pending_{acc_id}", False)
#                 stop = subs_times[i]

#                 if pending and next_srv and stop and stop > now_ms:
#                     text += (
#                         f"<b>Акк {acc_id}:</b> "
#                         f"Текущий: {_format_server_label(current_srv)}, "
#                         f"Следующий: {_format_server_label(buf_srv)}, "
#                         f"осталось {days_left} дней\n"
#                     )
#                 else:
#                     text += (
#                         f"<b>Акк {acc_id}:</b> "
#                         f"{_format_server_label(buf_srv)}, "
#                         f"осталось {days_left} дней\n"
#                     )

#                 if buf_srv not in (None, 0, "NONE"):
#                     keyboard.append([
#                         InlineKeyboardButton(
#                             f"Изменить сервер для Акк {acc_id}",
#                             callback_data=f"choose_server:{acc_id}"
#                         )
#                     ])
#                 else:
#                     if not first_empty_found:
#                         keyboard.append([
#                             InlineKeyboardButton(
#                                 f"Выбрать сервер для Акк {acc_id}",
#                                 callback_data=f"choose_server:{acc_id}"
#                             )
#                         ])
#                         first_empty_found = True

#             keyboard.append([
#                 InlineKeyboardButton("Все сервера выбраны ✅", callback_data="subs_save")
#             ])

#             if context.user_data.get("subs_saved_to_db"):
#                 keyboard.append([
#                     InlineKeyboardButton("Выставить счет 💳", callback_data="create_invoice")
#                 ])

#             keyboard.append([InlineKeyboardButton("Назад", callback_data="back:wallet")])

#             reply_markup = InlineKeyboardMarkup(keyboard)
#             text += f"\n<i>Обновлено: {int(datetime.now().timestamp())}</i>"

#             try:
#                 if message.caption:
#                     await message.edit_caption(text, reply_markup=reply_markup, parse_mode="html")
#                 else:
#                     await message.edit_text(text, reply_markup=reply_markup, parse_mode="html")
#             except Exception as e:
#                 logger.warning("Edit message failed for user %s: %s", tg_user.id, e)
#     finally:
#         context.user_data["subs_busy"] = False


# async def choose_server_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     _, acc_id = query.data.split(":")
#     acc_id = int(acc_id)

#     servers_list = [
#         (1, SERVER_LABELS[1]),
#         (2, SERVER_LABELS[2]),
#         (3, SERVER_LABELS[3]),
#         (4, SERVER_LABELS[4]),
#     ]

#     keyboard = [
#         [InlineKeyboardButton(label, callback_data=f"select_server:{acc_id}:{sid}")]
#         for sid, label in servers_list
#     ]

#     keyboard.append([
#         InlineKeyboardButton("❌ Пусто / Отменить", callback_data=f"select_server:{acc_id}:0")
#     ])

#     keyboard.append([InlineKeyboardButton("Назад", callback_data="count_back")])

#     await query.edit_message_caption(
#         caption=f"Выберите сервер для Аккаунта {acc_id}:",
#         reply_markup=InlineKeyboardMarkup(keyboard),
#         parse_mode="html",
#     )


# async def select_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     _, acc_id, server = query.data.split(":")
#     acc_id = int(acc_id)
#     server = int(server)

#     servers = context.user_data.get("subs_servers")
#     if servers is None:
#         async with SessionLocal() as session:
#             user_db = await session.get(AllUsers, query.from_user.id)
#             now_ms = _now_utc_ms()
#             servers = _init_buffered_servers(context, user_db, now_ms)

#     servers[acc_id - 1] = server
#     context.user_data["subs_saved_to_db"] = False

#     await count(update, context)


# async def subs_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer("Сохранено!", show_alert=False)

#     servers = context.user_data.get("subs_servers")
#     if not servers:
#         return await count(update, context)

#     now_ms = _now_utc_ms()

#     async with SessionLocal() as session:
#         user_db = await session.get(AllUsers, query.from_user.id)
#         if not user_db:
#             return

#         for i in range(1, 6):
#             desired = servers[i - 1] or 0
#             stop = getattr(user_db, f"subscription_stop_id_{i}")

#             if stop and stop > now_ms:
#                 setattr(user_db, f"subscription_server_next_id_{i}", desired)
#                 setattr(user_db, f"subscription_server_pending_{i}", True)
#             else:
#                 setattr(user_db, f"subscription_server_id_{i}", desired)
#                 setattr(user_db, f"subscription_server_next_id_{i}", 0)
#                 setattr(user_db, f"subscription_server_pending_{i}", False)

#         await session.commit()

#     context.user_data["subs_saved_to_db"] = True

#     await count(update, context)


# async def count_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await count(update, context)


# async def bitpappa_create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     bitpapa: BitpapaService = context.application.bot_data["bitpapa_service"]
#     user_id = query.from_user.id

#     async with SessionLocal() as session:
#         async with session.begin():
#             result = await session.execute(
#                 select(AllUsers)
#                 .where(AllUsers.user_id == user_id)
#                 .with_for_update()
#             )
#             user_db = result.scalar_one_or_none()

#     if not user_db or user_db.user_blocked == 1:
#         keyboard = [[InlineKeyboardButton("Выбрать доп аккаунт 💵", callback_data="count")]]
#         await query.message.reply_text(
#             "Невозможно продлить подписку.",
#             reply_markup=InlineKeyboardMarkup(keyboard),
#         )
#         return

#     accounts_amount = context.user_data.get("accounts_amount")
#     price = context.user_data.get("counted_price_last")
#     quantity_guests_paid_last = context.user_data.get("quantity_guests_paid_last")
#     invoice_details = context.user_data.get("invoice_details") or []

#     if not accounts_amount or price is None or not invoice_details:
#         await query.message.reply_text(
#             "Ошибка: данные о подписке не найдены. Попробуйте снова."
#         )
#         return

#     now = datetime.now(timezone.utc)
#     now_ms = int(now.timestamp() * 1000)

#     subs_times = [
#         user_db.subscription_stop_id_1,
#         user_db.subscription_stop_id_2,
#         user_db.subscription_stop_id_3,
#         user_db.subscription_stop_id_4,
#         user_db.subscription_stop_id_5,
#     ]

#     remaining_days = []
#     for t in subs_times:
#         if t and t >= now_ms:
#             acc_time = datetime.fromtimestamp(int(str(t)[:10])).astimezone(timezone.utc)
#             remaining_days.append((acc_time - now).days)
#         else:
#             remaining_days.append(0)

#     chosen_accs = [d["acc"] for d in invoice_details]
#     make_invoice = any(remaining_days[acc - 1] <= 15 for acc in chosen_accs)

#     if not make_invoice:
#         keyboard = [[InlineKeyboardButton("Выбрать доп аккаунт 💵", callback_data="count")]]
#         await query.message.reply_text(
#             "Продление возможно только если осталось меньше 15 дней.",
#             reply_markup=InlineKeyboardMarkup(keyboard),
#         )
#         return

#     final_price = max(price, UPDATED_MIN_PAY)
#     invoice_result = await bitpapa.create_invoice("USDT", final_price)
#     res_invoice_amount = int(invoice_result.invoice.amount * 100)

#     async with SessionLocal() as session:
#         async with session.begin():
#             invoice_db = AllInvoices(
#                 user_id=user_id,
#                 username=query.from_user.username,
#                 user_full_name=query.from_user.full_name,
#                 invoice_id=invoice_result.invoice.id,
#                 invoice_curency=invoice_result.invoice.currency_code,
#                 accounts_ammount=accounts_amount,
#                 invoice_ammount=res_invoice_amount,
#                 invoice_ammount_fact=int(price * 100),
#                 invoice_status=invoice_result.invoice.status,
#                 invoice_created_at=datetime.fromisoformat(invoice_result.invoice.created_at),
#                 invoice_updated_at=datetime.fromisoformat(invoice_result.invoice.updated_at),
#                 invoice_target="subscription_renew",
#                 promo=user_db.user_promo_new,
#                 quantity_guests_paid=user_db.quantity_guests_paid,
#                 invoice_url=invoice_result.invoice.url,
#             )
#             session.add(invoice_db)

#             for d in invoice_details:
#                 item = InvoiceItems(
#                     invoice_id=invoice_result.invoice.id,
#                     acc_number=d["acc"],
#                     server_id=d["server"],
#                     is_free=d["is_free"],
#                     discount_percent=d["discount_percent"],
#                     discount_amount=d["discount_amount"],
#                     price=d["base_price"],
#                     final_price=d["final_price"],
#                     provisioned=False,
#                     provisioned_at=None,
#                 )
#                 session.add(item)

#     keyboard = [[InlineKeyboardButton("Оплатить", url=invoice_result.invoice.url)]]

#     text = (
#         f"Продление подписки {BOT_SHOP_NAME}: 30 дней\n"
#         f"Аккаунтов: {accounts_amount}\n"
#         f"Стоимость: {price} $\n"
#         f"Скидка: {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n\n"
#         "Скидка начисляется последовательно:\n"
#         "До 100% — на 1-й аккаунт, свыше — на 2-й, и т.д.\n"
#         f"{invoice_result.invoice.url}\n"
#     )

#     await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# def register_subscription_handlers(application):
#     application.add_handler(CallbackQueryHandler(choose_server_menu, pattern=r"^choose_server:\d+$"))
#     application.add_handler(CallbackQueryHandler(select_server, pattern=r"^select_server:\d+:\d+$"))
#     application.add_handler(CallbackQueryHandler(subs_save, pattern=r"^subs_save$"))
#     application.add_handler(CallbackQueryHandler(count_back, pattern=r"^count_back$"))
#     application.add_handler(CallbackQueryHandler(bitpappa_create_invoice, pattern=r"^create_invoice$"))
