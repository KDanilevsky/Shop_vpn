# handlers/my_subscriptions.py v2

import logging
from datetime import datetime, timezone
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from db.async_db import SessionLocal
from db.models import AllUsers
from services.subscriptions import SERVER_LABELS  # reuse your mapping

logger = logging.getLogger(__name__)


def _now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


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


async def my_subscriptions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu: shows all subscription slots with server + remaining days."""
    query = update.callback_query
    if query:
        await query.answer()
        tg_user = query.from_user
        message = query.message
    else:
        tg_user = update.effective_user
        message = update.effective_message

    async with SessionLocal() as session:
        user = await session.get(AllUsers, tg_user.id)
        if not user:
            await message.reply_text("Пользователь не найден.")
            return

        now_ms = _now_ms()
        text = "<b>Мои подписки / сервера</b>\n\n"
        keyboard = []

        for slot in range(1, 6):
            server_id = getattr(user, f"subscription_server_id_{slot}")
            stop_ms = getattr(user, f"subscription_stop_id_{slot}")

            if not server_id:
                text += f"Акк {slot}: ❌ Нет подписки\n"
                continue

            label = SERVER_LABELS.get(server_id, f"ID {server_id}")

            if stop_ms and stop_ms > now_ms:
                days_left = (
                    datetime.fromtimestamp(stop_ms / 1000, tz=timezone.utc)
                    - datetime.now(timezone.utc)
                ).days
                text += f"Акк {slot}: {label}, осталось {days_left} дней\n"
            else:
                text += f"Акк {slot}: {label}, <b>истекла</b>\n"

            keyboard.append([
                InlineKeyboardButton(label, callback_data=f"my_subs_open:{slot}")
            ])

        keyboard.append([
            InlineKeyboardButton("Купить подписку 💳", callback_data="count")
        ])
        keyboard.append([
            InlineKeyboardButton("Назад", callback_data="back:wallet")
        ])

        await _safe_edit(message, text, keyboard)


async def my_subscriptions_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show QR + settings for a specific slot."""
    query = update.callback_query
    await query.answer()

    _, slot = query.data.split(":")
    slot = int(slot)

    async with SessionLocal() as session:
        user = await session.get(AllUsers, query.from_user.id)
        if not user:
            await query.message.reply_text("Пользователь не найден.")
            return

        server_id = getattr(user, f"subscription_server_id_{slot}")
        stop_ms = getattr(user, f"subscription_stop_id_{slot}")
        settings_string = getattr(user, f"subscription_settings_string_{slot}")
        qr_path = getattr(user, f"subscription_qr_path_{slot}")

        if not server_id:
            await query.message.reply_text("Подписка отсутствует.")
            return

        label = SERVER_LABELS.get(server_id, f"ID {server_id}")

        text = f"<b>Акк {slot}: {label}</b>\n\n"

        if stop_ms:
            stop_dt = datetime.fromtimestamp(stop_ms / 1000, tz=timezone.utc)
            text += f"Действует до: {stop_dt.strftime('%d.%m.%Y %H:%M UTC')}\n\n"

        if not settings_string:
            text += "Настройки пока недоступны."
        else:
            text += "Ваши настройки готовы.\n"

        keyboard = [
            # [InlineKeyboardButton("⬅️ Назад", callback_data="my_subs_back")]
            [InlineKeyboardButton("⬅️ Назад", callback_data="my_subscriptions")]
        ]

        # Always send a new message for QR/settings
        if qr_path:
            try:
                await query.message.reply_photo(
                    photo=open(qr_path, "rb"),
                    caption=text,
                    # reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="html",
                )
            except Exception:
                logger.exception("Failed to send QR")
                await query.message.reply_text(
                    text,
                    # reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="html",
                )
        else:
            await query.message.reply_text(
                text,
                # reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="html",
            )

        # Send settings file separately
            # Send settings file separately
        if settings_string:
            import io
            settings_bytes = settings_string.encode("utf-8")
            bio = io.BytesIO(settings_bytes)
            await query.message.reply_document(
                document=bio,
                filename=f"settings_slot_{slot}.txt",
                caption="Ваши настройки"
            )

        # if settings_string:
        #     settings_bytes = settings_string.encode("utf-8")
        #     await query.message.reply_document(
        #         document=InputFile(
        #             settings_bytes,
        #             filename=f"settings_slot_{slot}.txt"
        #         ),
        #         caption="Ваши настройки"
        #     )


async def my_subscriptions_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await my_subscriptions_menu(update, context)


def register_my_subscriptions_handlers(application):
    application.add_handler(CallbackQueryHandler(my_subscriptions_menu, pattern=r"^(my_subscriptions|my_subs_back)$"))
    application.add_handler(CallbackQueryHandler(my_subscriptions_open, pattern=r"^my_subs_open:\d+$"))

    # application.add_handler(CallbackQueryHandler(my_subscriptions_menu, pattern=r"^my_subscriptions$"))
    # application.add_handler(CallbackQueryHandler(my_subscriptions_open, pattern=r"^my_subs_open:\d+$"))
    # application.add_handler(CallbackQueryHandler(my_subscriptions_back, pattern=r"^my_subs_back$"))
