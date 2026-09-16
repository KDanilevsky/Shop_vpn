# handlers/start.py
from telegram import Update, helpers, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.crud import get_or_create_user_with_promo
# from services.server_api import provision_subscription_for_user, fetch_subscription_end_from_server, send_user_settings_string_and_qr_code_then_del_qr

from keyboards.reply import bottom_menu

from db.async_db import SessionLocal
from db.models import SubscriptionTransaction, AllUsers, SecretToken, FriendlyAccount
from sqlalchemy import select, func
from datetime import datetime, timezone
from config import BOT_SHOP_NAME

from services.provision import provision_subscription_for_user
from services.notifications import send_user_settings_string_and_qr_code_then_del_qr

def _now_utc():
    return datetime.now(timezone.utc)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    tg_id = user.id
    username = user.username
    full_name = user.full_name

    # ---------------------------------------------------------
    # 1. Detect special deep links
    # ---------------------------------------------------------
    if context.args:
        arg = context.args[0]

        # PAYFOR TOKEN
        if arg.startswith("payfor_"):
            return await handle_start_with_payfor(update, context)

        # INVITE TOKEN
        if arg.startswith("invite_"):
            return await handle_start_with_invite(update, context)

        # LEGACY INVITER ID (old system)
        # try:
        #     inviter_id = int(arg)
        # except (TypeError, ValueError):
        #     inviter_id = None
    else:
        inviter_id = None

    # ---------------------------------------------------------
    # 2. Normal start flow (your existing logic)
    # ---------------------------------------------------------
    db_user, tx = await get_or_create_user_with_promo(
        tg_id=tg_id,
        username=username,
        full_name=full_name,
        user_id_who_invited=inviter_id
    )
    if not db_user:
        await message.reply_text("Ошибка при создании пользователя. Пожалуйста, попробуйте снова.")
        return

    # # ---------------------------------------------------------
    # # 3. Provisioning logic (unchanged)
    # # ---------------------------------------------------------
    # if tx:
    #     try:
    #         result = await provision_subscription_for_user(
    #             user_id=tx.user_id,
    #             requested_end_ts=tx.requested_end_ts,
    #             tx_id=tx.id
    #         )

    #         server_end_ts = result.get("end_ts")
    #         external_id = result.get("external_id")

    #         async with SessionLocal() as session:
    #             async with session.begin():
    #                 from db.models import SubscriptionTransaction, AllUsers

    #                 r = await session.execute(
    #                     select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx.id)
    #                 )
    #                 tx_row = r.scalar_one_or_none()
    #                 if tx_row:
    #                     tx_row.status = "completed"
    #                     tx_row.external_id = external_id
    #                     await session.flush()

    #                 r = await session.execute(
    #                     select(AllUsers).where(AllUsers.user_id == tg_id)
    #                 )
    #                 user_row = r.scalar_one_or_none()
    #                 if user_row:
    #                     user_row.user_promo_new = 1
    #                     user_row.user_promo_new_days = server_end_ts or user_row.user_promo_new_days
    #                     await session.flush()

    #         client_settings_string = result.get("settings_string")
    #         img_path = result.get("img_path")
    #         if client_settings_string and img_path:
    #             await send_user_settings_string_and_qr_code_then_del_qr(
    #                 tg_id, client_settings_string, img_path
    #             )

    #     except Exception as exc:
    #         async with SessionLocal() as session:
    #             async with session.begin():
    #                 from db.models import SubscriptionTransaction
    #                 r = await session.execute(
    #                     select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx.id)
    #                 )
    #                 tx_row = r.scalar_one_or_none()
    #                 if tx_row:
    #                     tx_row.status = "failed"
    #                     tx_row.error = str(exc)[:2000]
    #                     await session.flush()

    # ---------------------------------------------------------
    # 4. Welcome message
    # ---------------------------------------------------------
    bot = context.bot
    url = helpers.create_deep_linked_url(bot.username, str(tg_id), group=False)
    text = f"{full_name}, Добро пожаловать в {BOT_SHOP_NAME} — Интернет без границ.\n\n{url}"
    await bot.send_message(chat_id=tg_id, text=text, reply_markup=bottom_menu(update, context))


# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user = update.effective_user
#     message = update.effective_message
#     if user is None or message is None:
#         return

#     tg_id = user.id
#     username = user.username
#     full_name = user.full_name

#     inviter_id = None
#     if context.args:
#         try:
#             inviter_id = int(context.args[0])
#         except (TypeError, ValueError):
#             inviter_id = None

#     # create user and possibly a pending subscription transaction
#     db_user, tx = await get_or_create_user_with_promo(
#         tg_id=tg_id,
#         username=username,
#         full_name=full_name,
#         user_id_who_invited=inviter_id
#     )
#     if not db_user:
#         await message.reply_text("Ошибка при создании пользователя. Пожалуйста, попробуйте снова.")
#         return

#     # If a transaction was created, run provisioning outside DB transaction
#     if tx:
#         # call your async provisioning function; it must be idempotent using tx.id or user id
#         try:
#             # provision_subscription_for_user should return dict with external_id and actual_end_ts
#             result = await provision_subscription_for_user(
#                 user_id=tx.user_id,
#                 requested_end_ts=tx.requested_end_ts,
#                 tx_id=tx.id
#             )
#             # verify server state optionally
#             server_end_ts = result.get("end_ts")
#             external_id = result.get("external_id")

#             # update transaction status to completed
#             async with SessionLocal() as session:
#                 async with session.begin():
#                     # re-fetch tx and update
#                     from db.models import SubscriptionTransaction, AllUsers
#                     r = await session.execute(select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx.id))
#                     tx_row = r.scalar_one_or_none()
#                     if tx_row:
#                         tx_row.status = "completed"
#                         tx_row.external_id = external_id
#                         tx_row.previous_end_ts = tx_row.previous_end_ts
#                         await session.flush()

#                     # optionally update user fields if needed
#                     r = await session.execute(select(AllUsers).where(AllUsers.user_id == tg_id))
#                     user_row = r.scalar_one_or_none()
#                     if user_row:
#                         user_row.user_promo_new = 1
#                         user_row.user_promo_new_days = server_end_ts or user_row.user_promo_new_days
#                         await session.flush()

#             # send settings/QR if provisioning returned them
#             client_settings_string = result.get("settings_string")
#             img_path = result.get("img_path")
#             if client_settings_string and img_path:
#                 await send_user_settings_string_and_qr_code_then_del_qr(tg_id, client_settings_string, img_path)

#         except Exception as exc:
#             # mark tx as failed and store error for reconciliation
#             async with SessionLocal() as session:
#                 async with session.begin():
#                     from db.models import SubscriptionTransaction
#                     r = await session.execute(select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx.id))
#                     tx_row = r.scalar_one_or_none()
#                     if tx_row:
#                         tx_row.status = "failed"
#                         tx_row.error = str(exc)[:2000]
#                         await session.flush()
#             # do not raise; keep user experience smooth

#     # send welcome message
#     bot = context.bot
#     url = helpers.create_deep_linked_url(bot.username, str(tg_id), group=False)
#     text = f"{full_name}, Добро пожаловать в {BOT_SHOP_NAME} — Интернет без границ.\n\n{url}"
#     await bot.send_message(chat_id=tg_id, text=text, reply_markup=bottom_menu(update, context))


# ---------------------------------------------------------
# /start payfor_<token>
# ---------------------------------------------------------

async def handle_start_with_payfor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].startswith("payfor_"):
        return

    token = parts[1][len("payfor_") :]

    async with SessionLocal() as session:
        now = _now_utc()
        result = await session.execute(
            select(SecretToken)
            .where(
                SecretToken.token == token,
                SecretToken.purpose == "payfor",
                (SecretToken.expires_at.is_(None)) | (SecretToken.expires_at > now),
            )
        )
        st = result.scalar_one_or_none()
        if not st:
            await message.reply_text("Ссылка недействительна или устарела.")
            return

        owner = await session.get(AllUsers, st.owner_user_id)
        if not owner:
            await message.reply_text("Пользователь не найден.")
            return

        result = await session.execute(
            select(func.count(FriendlyAccount.id)).where(
                FriendlyAccount.owner_user_id == message.from_user.id
            )
        )
        count = result.scalar_one()
        if count >= 5:
            await message.reply_text("У вас уже 5 аккаунтов, которые вы пополняете.")
            return

        owner_uname = owner.username or ""
        owner_fullname = owner.user_full_name or ""

    text = (
        "<b>Добавить аккаунт для пополнения</b>\n\n"
        f"Вы хотите добавить пользователя {owner_fullname} "
        f"(@{owner_uname}) в список тех, кому вы пополняете баланс?"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Да", callback_data=f"wallet_friendly_add:{st.owner_user_id}"
            ),
            InlineKeyboardButton("❌ Нет", callback_data="back:wallet"),
        ]
    ]

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="html")


async def handle_start_with_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles /start invite_<token>
    Adds inviter → invited relationship safely.
    Does NOT reveal inviter info unless token is valid.
    """
    message = update.message
    tg_user = update.effective_user

    # Extract token
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply_text("Некорректная ссылка приглашения.")

    token = parts[1][len("invite_") :]

    async with SessionLocal() as session:
        now = _now_utc()

        # 1. Validate token
        result = await session.execute(
            select(SecretToken)
            .where(
                SecretToken.token == token,
                SecretToken.purpose == "invite",
                (SecretToken.expires_at.is_(None)) | (SecretToken.expires_at > now),
            )
        )
        st = result.scalar_one_or_none()
        if not st:
            return await message.reply_text("Ссылка приглашения недействительна или устарела.")

        inviter_id = st.owner_user_id

        # 2. Prevent self-invite
        if inviter_id == tg_user.id:
            return await message.reply_text("Вы не можете использовать собственную ссылку приглашения.")

        # 3. Fetch inviter info
        inviter = await session.get(AllUsers, inviter_id)
        if not inviter:
            return await message.reply_text("Пользователь, отправивший приглашение, не найден.")

        # 4. Check if user already exists
        invited_user = await session.get(AllUsers, tg_user.id)
        if invited_user:
            # Already registered → no need to create again
            # But do NOT overwrite inviter_id if already set
            if invited_user.user_id_who_invited:
                return await message.reply_text(
                    "Вы уже зарегистрированы и у вас уже есть пригласивший."
                )

            # If user exists but has no inviter → set inviter
            # invited_user.user_id_who_invited = inviter_id
            # await session.commit()

            # return await message.reply_text(
            #     f"Вы успешно присоединились по приглашению от {inviter.full_name}!"
            # )

        # 5. New user → create with inviter
        # We reuse your existing logic
        new_user, tx = await get_or_create_user_with_promo(
            tg_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            user_id_who_invited=inviter_id
        )

        if not new_user:
            return await message.reply_text("Ошибка при создании пользователя. Попробуйте снова.")

    # 6. Send welcome message
    return await message.reply_text(
        f"Добро пожаловать! Вы присоединились по приглашению."
        # f"Добро пожаловать! Вы присоединились по приглашению от {inviter.full_name}."
    )
