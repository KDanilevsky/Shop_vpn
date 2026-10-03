import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from telegram.ext import (
    ApplicationBuilder, 
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters
)

from services.helpers import init_servers_cache, ServersSettings
from services.listener import PgListener
from config import DATABASE_URL_PG, DATABASE_URL_PG_PG, TELEGRAM_TOKEN, PAYMENT_PROVIDER_TOKEN, CRYPTOMUS_MERCHANT_ID, CRYPTOMUS_API_KEY
from services.bitpapa import BitpapaService
from services.cryptomus import CryptomusService
from services.subscriptions import register_subscription_handlers
from services.events import on_event

from handlers.help import get_admin_conversation_handler, help_handler, help_callback_router
from handlers.start import start
from handlers.bottom_menu import bottom_menu_router
from handlers.wallet import wallet_handler, wallet_callback_router, register_wallet_handlers
from handlers.my_subscriptions import register_my_subscriptions_handlers
from handlers.topup import topup_handler, topup_callback_router, register_topup_handlers
from handlers.about import about_handler, about_callback_router
from handlers.share import share_handler, referal_link
from handlers.settings import settings
from handlers.plusses import pluses
from api.webhook import invoice_webhook
from handlers.paying_methods import confirm_top_up_balance
from handlers.balance_top_up import handle_balance_top_up

from db.models import Base
from db.async_db import SessionLocal, engine
from db.init_db import run_db_tasks

from handlers.admin.router import admin_router
from handlers.admin.users import admin_users_search_text
from handlers.admin.broadcast import admin_broadcast_compose
from handlers.admin.settings import admin_settings_roles_input
from handlers.admin.entry import admin_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def app_startup(app: Application):
    """
    Объединенный хук инициализации. Вызывается строго ОДИН раз при старте приложения,
    что гарантирует правильный запуск всех зависимых асинхронных сервисов.
    """
    # 1. Инициализация BitpapaService
    svc: BitpapaService = app.bot_data["bitpapa_service"]
    await svc.init()
    logger.info("BitpapaService успешно инициализирован.")

    # 2. Инициализация и запуск PgListener
    listener = PgListener(
        dsn=DATABASE_URL_PG_PG,
        channel="events",
        callback=on_event,
    )
    app.bot_data["pg_listener"] = listener
    await listener.start()
    logger.info("PgListener успешно запущен на канале 'events'.")

async def app_shutdown(app: Application):
    """
    Объединенный хук graceful shutdown. Гарантирует закрытие всех сессий
    и сетевых портов при остановке бота без утечек памяти.
    """
    # 1. Остановка PgListener
    listener = app.bot_data.get("pg_listener")
    if listener:
        await listener.stop()
        logger.info("PgListener успешно остановлен.")

    # 2. Закрытие BitpapaService
    svc: BitpapaService | None = app.bot_data.get("bitpapa_service")
    if svc is not None:
        await svc.close()
        logger.info("BitpapaService успешно закрыт.")

def main():
    # Настраиваем жизненный цикл приложения через единые хуки
    builder = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(app_startup)
        .post_shutdown(app_shutdown)
    )

    app = builder.build()

    # Сохраняем единственный экземпляр BitpapaService на все приложение в bot_data
    app.bot_data["bitpapa_service"] = BitpapaService(
        api_token=PAYMENT_PROVIDER_TOKEN,
        max_retries=3,
        base_delay=1.0,
    )

    # Сохраняем единственный экземпляр CryptomusService на все приложение в bot_data
    app. bot_data["cryptomus_service"] = CryptomusService(
        merchant_id=CRYPTOMUS_MERCHANT_ID,
        api_key=CRYPTOMUS_API_KEY
    )
    logger.info("CryptomusService успешно добавлен в bot_data приложения.")

    # --- РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ КОМАНД И ДИАЛОГОВ ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(get_admin_conversation_handler())

    # Точка входа в админку по кнопке
    app.add_handler(MessageHandler(filters.Regex("^⭐ Админ$"), admin_handler))
    
    # Роутер инлайн-кнопок админки
    app.add_handler(CallbackQueryHandler(admin_router, pattern="^admin:"))

    # Роутеры инлайн-кнопок для пользовательского интерфейса
    app.add_handler(CallbackQueryHandler(wallet_callback_router, pattern="^(my_accounts|balance_top_up|auto_pay_subs|count|back:wallet)$"))
    app.add_handler(CallbackQueryHandler(about_callback_router, pattern="^(pluses|free|usl|ref|back:about)$"))
    app.add_handler(CallbackQueryHandler(help_callback_router, pattern="^(call_adm|back:help)$"))
    app.add_handler(CallbackQueryHandler(handle_balance_top_up, pattern="^balance_top_up_"))
    app.add_handler(CallbackQueryHandler(confirm_top_up_balance, pattern="^confirm_top_up_balance$"))

    # Подключение остальных модулей хэндлеров
    register_subscription_handlers(app)
    register_my_subscriptions_handlers(app)
    register_wallet_handlers(app)
    register_topup_handlers(app)

    # ВАЖНО: Главное текстовое меню должно быть в самом низу списка,
    # чтобы не перехватывать и не ломать ввод данных (поиск, рассылку и т.д.)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bottom_menu_router))

    logger.info("Все хэндлеры и роутеры успешно зарегистрированы. Запуск polling...")
    
    # Запуск бота (блокирующий вызов)
    app.run_polling()

if __name__ == "__main__":
    main()

