import os
import logging
from telegram import InputMediaPhoto, Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from keyboards.wallet_kb import wallet_keyboard
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from db.models import AllUsers, FriendlyAccount, SecretToken
from services.helpers import get_or_create_secret_token

from db.async_db import SessionLocal
from db.models import AllUsers, AllTransactions
from config import ASSETS_DIR, ADMINS_LIST, MAXIMUM_FRIENDLY_ACCOUNTS

from services.subscriptions import count

logger = logging.getLogger(__name__)


async def _safe_edit(message, text, keyboard):
    """Safely edit a message, falling back to sending a new one."""
    try:
        if message.caption:
            await message.edit_caption(
                caption=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="html",
            )
        else:
            await message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="html",
            )
    except Exception:
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="html",
        )

def _now_utc():
    return datetime.now(timezone.utc)

def _now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_path = os.path.join(ASSETS_DIR, "wallet.jpg")
    reply_markup = wallet_keyboard()

    query = update.callback_query
    text = ''
    # If called from a callback query, edit the existing message
    if query is not None:
        await query.answer()

        tg_user = query.from_user
        message = query.message

        user = None
        async with SessionLocal() as session:
            user = await session.get(AllUsers, tg_user.id)
            if not user:
                await message.reply_text("Пользователь не найден.")
                return
        
        now_ms = _now_ms()

        # Count active subscriptions + find nearest renewal
        active_subs = 0
        nearest_renewal = None
        renewal_slot = None

        for slot in range(1, 6):
            stop_ms = getattr(user, f"subscription_stop_id_{slot}")
            server_id = getattr(user, f"subscription_server_id_{slot}")

            if server_id and stop_ms and stop_ms > now_ms:
                active_subs += 1

                if nearest_renewal is None or stop_ms < nearest_renewal:
                    nearest_renewal = stop_ms
                    renewal_slot = slot

        balance = (user.user_balance or 0) / 100
        partner_balance = (user.partner_balance or 0) / 100
        invited = user.quantity_guests or 0
        invited_paid = user.quantity_guests_paid or 0

        # Emoji indicators
        if active_subs == 0:
            subs_status = "❌ Нет активных подписок"
        elif active_subs == 1:
            subs_status = "🟢 1 активная подписка"
        else:
            subs_status = f"🟢 {active_subs} активных подписок"

        # Nearest renewal
        if nearest_renewal:
            dt = datetime.fromtimestamp(nearest_renewal / 1000, tz=timezone.utc)
            nearest_text = f"{dt.strftime('%d.%m.%Y %H:%M UTC')} (Акк {renewal_slot})"
        else:
            nearest_text = "—"

        text = (
                "<b>💼 Ваш кошелёк</b>\n\n"
                f"<b>Баланс:</b> {balance:.2f} $\n"
                f"<b>Подписки:</b> {subs_status}\n"
                f"<b>Ближайшее продление:</b> {nearest_text}\n\n"
                # f"<b>Партнёрский баланс:</b> {partner_balance:.2f} $\n"
                f"<b>Приглашённых пользователей/Оплативших:</b> {invited}/{invited_paid}\n"
            )
        if user.is_partner:  # Show partner balance only for partners and admins
            text += f"\n<b>Партнёрский баланс:</b> {partner_balance:.2f} $\n"
        # If the message already contains a photo, edit caption
        try:
            await query.edit_message_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="html"
            )
        except Exception:
            # Fallback: replace media if caption edit fails
            
            with open(photo_path, "rb") as f:
                media = InputMediaPhoto(f, caption=text, parse_mode="html")
                await query.edit_message_media(media=media, reply_markup=reply_markup)
        return

    else:
        tg_user = update.effective_user
        message = update.effective_message

        user = None
        async with SessionLocal() as session:
            user = await session.get(AllUsers, tg_user.id)
            if not user:
                await message.reply_text("Пользователь не найден.")
                return
        
        now_ms = _now_ms()

        # Count active subscriptions + find nearest renewal
        active_subs = 0
        nearest_renewal = None
        renewal_slot = None

        for slot in range(1, 6):
            stop_ms = getattr(user, f"subscription_stop_id_{slot}")
            server_id = getattr(user, f"subscription_server_id_{slot}")

            if server_id and stop_ms and stop_ms > now_ms:
                active_subs += 1

                if nearest_renewal is None or stop_ms < nearest_renewal:
                    nearest_renewal = stop_ms
                    renewal_slot = slot

        balance = (user.user_balance or 0) / 100
        partner_balance = (user.partner_balance or 0) / 100
        invited = user.quantity_guests or 0
        invited_paid = user.quantity_guests_paid or 0

        # Emoji indicators
        if active_subs == 0:
            subs_status = "❌ Нет активных подписок"
        elif active_subs == 1:
            subs_status = "🟢 1 активная подписка"
        else:
            subs_status = f"🟢 {active_subs} активных подписок"

        # Nearest renewal
        if nearest_renewal:
            dt = datetime.fromtimestamp(nearest_renewal / 1000, tz=timezone.utc)
            nearest_text = f"{dt.strftime('%d.%m.%Y %H:%M UTC')} (Акк {renewal_slot})"
        else:
            nearest_text = "—"

        text = (
                "<b>💼 Ваш кошелёк</b>\n\n"
                f"<b>Баланс:</b> {balance:.2f} $\n"
                f"<b>Подписки:</b> {subs_status}\n"
                f"<b>Ближайшее продление:</b> {nearest_text}\n\n"
                # f"<b>Партнёрский баланс:</b> {partner_balance:.2f} $\n"
                f"<b>Приглашённых пользователей/Оплативших:</b> {invited}/{invited_paid}\n"
            )
        if user.is_partner:  # Show partner balance only for partners and admins
            text += f"\n<b>Партнёрский баланс:</b> {partner_balance:.2f} $\n"

    # Otherwise it's a normal message, send a new photo
    # use with open to ensure file is closed
        with open(photo_path, "rb") as f:
            await update.message.reply_photo(photo=f, caption=text, reply_markup=reply_markup, parse_mode="html")


# async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     photo_path = os.path.join(ASSETS_DIR, "wallet.jpg")

#     await update.message.reply_photo(
#         photo=open(photo_path, "rb"),
#         caption="Ваш Баланс:",
#         reply_markup=wallet_keyboard()
#     )


async def wallet_callback_router(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    # if data == "my_subscriptions":
    #     # await query.answer()
    #     await query.edit_message_caption("Ваши подписки...", reply_markup=None)


    if data == "balance_top_up":
        # await query.answer()
        await query.edit_message_caption("Пополнение баланса...", reply_markup=None)
    elif data == "auto_pay_subs":
        # await query.answer()
        await query.edit_message_caption("Автопродление...", reply_markup=None)
    elif data == "count":
        # await query.answer()
        await count(update, context)
        # await query.edit_message_caption("Расчет стоимости...", reply_markup=None)

    # elif data.startswith("back:"):
    #     target = data.split(":", 1)[1]
    elif data == "back:wallet":
        # вызываем функцию, которая показывает админ-меню
        return await wallet_handler(update, context)
    


async def wallet_my_paying_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        user = await session.get(AllUsers, query.from_user.id)
        if not user:
            await query.message.reply_text("Пользователь не найден.")
            return

        # token = await _get_or_create_payfor_token(session, user.user_id)
        token = await get_or_create_secret_token(session, user.user_id, "payfor", days=1) # metadata={"subs_id": subs_id} - можно сохранять в metadata любые данные, которые могут понадобиться при обработке токена (например, ID подписки для которой создается токен)

    bot_username = context.bot.username
    link = f"https://t.me/{bot_username}?start=payfor_{token}"
    now = _now_utc().strftime("%d.%m.%Y %H:%M UTC")
    now_ends = _now_utc() + timedelta(days=1)


    text = (
        "<b>🔗 Ваша платёжная ссылка</b>\n\n"
        "Отправьте её человеку, который будет пополнять ваш баланс.\n\n"
        f"<b>Ссылка действительна до:</b> {now_ends}\n\n"
        f"<code>{link}</code>"
    )

    keyboard = [
        [InlineKeyboardButton("Добавить в список для пополнения", url=link)],
        # [InlineKeyboardButton("⬅️ Назад", callback_data="back:wallet")],
    ]

    await _safe_edit(query.message, text, keyboard)


# ---------------------------------------------------------
# FRIENDLY ACCOUNTS (who I pay for)
# ---------------------------------------------------------

async def wallet_friendly_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        result = await session.execute(
            select(FriendlyAccount)
            .where(FriendlyAccount.owner_user_id == query.from_user.id)
            .order_by(FriendlyAccount.created_at.asc())
            .limit(MAXIMUM_FRIENDLY_ACCOUNTS)
        )
        friends = result.scalars().all()

    text = "<b>👨‍👩‍👧 Аккаунты, которые вы пополняете</b>\n\n"

    keyboard = []
    if not friends:
        text += "Пока здесь пусто.\n"
    else:
        for idx, fa in enumerate(friends, start=1):
            uname = f"@{fa.friend_username}" if fa.friend_username else "(без username)"
            fname = fa.friend_fullname or ""
            text += f"{idx}. {uname} {fname}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Удалить {idx}",
                    callback_data=f"wallet_friendly_remove:{fa.id}",
                )
            ])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back:wallet")])

    await _safe_edit(query.message, text, keyboard)


async def wallet_friendly_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, fa_id = query.data.split(":")
    fa_id = int(fa_id)

    async with SessionLocal() as session:
        fa = await session.get(FriendlyAccount, fa_id)
        if not fa or fa.owner_user_id != query.from_user.id:
            await query.message.reply_text("Запись не найдена.")
            return
        await session.delete(fa)
        await session.commit()

    await wallet_friendly_accounts(update, context)


async def wallet_friendly_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, owner_id = query.data.split(":")
    owner_id = int(owner_id)

    async with SessionLocal() as session:
        owner = await session.get(AllUsers, owner_id)
        if not owner:
            await query.message.reply_text("Пользователь не найден.")
            return

        result = await session.execute(
            select(FriendlyAccount).where(
                FriendlyAccount.owner_user_id == query.from_user.id,
                FriendlyAccount.friend_user_id == owner.user_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            await query.message.reply_text("Этот аккаунт уже есть в вашем списке.")
            return

        result = await session.execute(
            select(func.count(FriendlyAccount.id)).where(
                FriendlyAccount.owner_user_id == query.from_user.id
            )
        )
        count = result.scalar_one()
        if count >= MAXIMUM_FRIENDLY_ACCOUNTS:
            await query.message.reply_text(f"У вас уже {MAXIMUM_FRIENDLY_ACCOUNTS} аккаунтов, которые вы пополняете. Это максимальное количество. Удалите кого-то из списка, чтобы добавить нового.")
            return
        if owner.user_id == query.from_user.id:
            await query.message.reply_text("Вы не можете добавить себя в список для пополнения баланса.")
            return

        fa = FriendlyAccount(
            owner_user_id=query.from_user.id,
            friend_user_id=owner.user_id,
            friend_username=owner.username,
            friend_fullname=owner.user_full_name,
        )
        session.add(fa)
        await session.commit()

    await query.message.reply_text("Аккаунт добавлен в список тех, кому вы пополняете баланс.")
# ---------------------------------------------------------
# TRANSACTION HISTORY
# ---------------------------------------------------------


async def wallet_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        result = await session.execute(
            select(AllTransactions)
            .where(AllTransactions.user_id == query.from_user.id)
            .order_by(AllTransactions.trans_time.desc())
            .limit(20)
        )
        txs = result.scalars().all()

    if not txs:
        text = "<b>📜 История транзакций</b>\n\nНет транзакций."
    else:
        text = "<b>📜 История транзакций</b>\n\n"

        for tx in txs:
            # dt = datetime.fromtimestamp(tx.trans_time / 1000, tz=timezone.utc)
            dt = tx.trans_time.strftime('%d.%m.%Y %H:%M')
            amount = tx.trans_ammount / 100

            if tx.trans_target == "wallet_topup_multi":
                label = "Пополнение (мульти-топап)"
            elif tx.trans_target == "wallet_topup_self":
                label = "Пополнение баланса"
            else:
                label = tx.trans_target

            text += (
                f"{dt.strftime('%d.%m.%Y %H:%M')} — "
                f"<b>+{amount:.2f}$</b> — {label}\n"
            )

    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back:wallet")],
    ]

    await query.edit_message_caption(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="html")
    # await _safe_edit(query.message, text, keyboard)


def register_wallet_handlers(application):
    # application.add_handler(CallbackQueryHandler(wallet_menu, pattern=r"^wallet$"))
    # application.add_handler(CallbackQueryHandler(wallet_partner_link, pattern=r"^wallet_partner_link$"))
    application.add_handler(CallbackQueryHandler(wallet_my_paying_info, pattern=r"^wallet_my_paying_info$"))
    application.add_handler(CallbackQueryHandler(wallet_friendly_accounts, pattern=r"^wallet_friendly_accounts$"))
    application.add_handler(CallbackQueryHandler(wallet_friendly_remove, pattern=r"^wallet_friendly_remove:\d+$"))
    application.add_handler(CallbackQueryHandler(wallet_friendly_add, pattern=r"^wallet_friendly_add:\d+$"))
    application.add_handler(CallbackQueryHandler(wallet_history, pattern=r"^wallet_history$"))