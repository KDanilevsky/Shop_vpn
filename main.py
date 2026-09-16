import asyncio

import logging
from services.helpers import init_servers_cache, ServersSettings
# from workers.entrypoint import start_workers # your worker startup
logger = logging.getLogger(__name__)
from telegram.ext import ApplicationBuilder, Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from services.listener import PgListener

from config import DATABASE_URL_PG, DATABASE_URL_PG_PG, TELEGRAM_TOKEN, PAYMENT_PROVIDER_TOKEN

from services.bitpapa import BitpapaService

from services.subscriptions import register_subscription_handlers
# from services.provision import provision_subscription_for_user
from services.events import on_event
# from utils.db import create_engine_and_sessionmaker
from handlers.help import get_admin_conversation_handler

from handlers.start import start
from handlers.bottom_menu import bottom_menu_router
# from handlers.inline_router import inline_router
# from handlers.shop import register_shop_handlers

from handlers.wallet import wallet_handler, wallet_callback_router, register_wallet_handlers
from handlers.my_subscriptions import register_my_subscriptions_handlers
from handlers.topup import topup_handler, topup_callback_router, register_topup_handlers
# from handlers.admin import admin_handler, admin_callback_router
from handlers.about import about_handler, about_callback_router
from handlers.help import help_handler, help_callback_router

from handlers.share import share_handler, referal_link
from handlers.settings import settings
from handlers.plusses import pluses
from api.webhook import invoice_webhook
from handlers.paying_methods import confirm_top_up_balance
# bitpappa_create_invoice
from handlers.balance_top_up import handle_balance_top_up

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from db.models import Base
from db.async_db import SessionLocal
from db.async_db import engine



# engine = create_async_engine(DATABASE_URL_PG, echo=False)
# SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# # OPTIONAL DB INIT
from db.init_db import run_db_tasks

from handlers.admin.router import admin_router
from handlers.admin.users import admin_users_search_text
from handlers.admin.broadcast import admin_broadcast_compose
from handlers.admin.settings import admin_settings_roles_input

from handlers.admin.entry import admin_handler


def register_handlers(application):
    # Admin entry point (button "⭐ Админ")
    application.add_handler(MessageHandler(filters.Regex("^⭐ Админ$"), admin_handler))

    # Admin callback router
    application.add_handler(CallbackQueryHandler(admin_router, pattern="^admin:"))

    # Admin text input handlers (search, broadcast text, role assignment)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_users_search_text))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_compose))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_settings_roles_input))



# async def startup():
#     settings = ServersSettings()
#     # loads .env and env vars
#     await init_servers_cache(settings)
#     # start workers and bot after cache initialized
#     await start_workers()

# async def on_tx(tx_id: int):
#     # здесь твоя логика обработки транзакции
#     print(f"Received tx_id={tx_id} from NOTIFY")

# create_event notify for user_notification worker when balance top-up happens, so it can send message to user about successful top-up without delay
# notify_event = asyncio.Event()

# async def on_event(payload: str):
#     if payload == "notify":
#         notify_event.set()  # wake the user_notification worker instantly

#     elif payload.startswith("tx:"):
#         tx_id = int(payload.split(":", 1)[1])
#         await process_subscription_transaction(tx_id)

#     elif payload.startswith("invoice:"):
#         invoice_id = payload.split(":", 1)[1]
#         await process_invoice(invoice_id)

#     elif payload.startswith("user:"):
#         user_id = int(payload.split(":", 1)[1])
#         await process_user_event(user_id)

#     else:
#         logger.warning("Unknown event payload: %s", payload)



async def _init_app(app):
    svc: BitpapaService = app.bot_data["bitpapa_service"]
    await svc.init()
    print("BitpapaService initialized")

async def _shutdown(app):
    svc: BitpapaService | None = app.bot_data.get("bitpapa_service")
    if svc is not None:
        await svc.close()
        print("BitpapaService closed")

# --- PgListener hooks must be registered on builder ---
async def start_listener(app):
    listener = PgListener(
        dsn=DATABASE_URL_PG_PG,
        channel="events",
        callback=on_event,
    )
    app.bot_data["pg_listener"] = listener
    await listener.start()

async def stop_listener(app):
    listener = app.bot_data.get("pg_listener")
    if listener:
        await listener.stop()


def main():

    builder = ( ApplicationBuilder()
                .token(TELEGRAM_TOKEN)
                .post_init(_init_app) # регистрируем init до build
                .post_init(start_listener)
                .post_shutdown(_shutdown) # регистрируем shutdown до build
                .post_shutdown(stop_listener)
    )
    app = builder.build()

    # один экземпляр на всё приложение
    app.bot_data["bitpapa_service"] = BitpapaService(
        api_token=PAYMENT_PROVIDER_TOKEN,
        max_retries=3,
        base_delay=1.0,
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(get_admin_conversation_handler())

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bottom_menu_router))

    # app.add_handler(CallbackQueryHandler(inline_router, pattern="^(buy|page_|back_main)$"))
    app.add_handler(CallbackQueryHandler(wallet_callback_router, pattern="^(my_accounts|balance_top_up|auto_pay_subs|count|back:wallet)$"))
    # app.add_handler(CallbackQueryHandler(topup_callback_router, pattern="^(pay_help|apeal_account_didnt_paid|back:topup)$"))
    # app.add_handler(CallbackQueryHandler(admin_callback_router, pattern="^(admin_reply|admin_send_all|admin_mark_all_users_on_server|adm_plus_usr_days|adm_user_info|adm_block_user|adm_unblock_user|adm_part_info|adm_add_partner|adm_show_partners|adm_pay_partner|back:admin)$"))
    app.add_handler(CallbackQueryHandler(about_callback_router, pattern="^(pluses|free|usl|ref|back:about)$"))
    app.add_handler(CallbackQueryHandler(help_callback_router, pattern="^(call_adm|back:help)$"))
    
    # app.add_handler(CallbackQueryHandler(bitpappa_create_invoice, pattern="^(create_invoice)$"))
    app.add_handler(CallbackQueryHandler(handle_balance_top_up, pattern="^balance_top_up_"))
    app.add_handler(CallbackQueryHandler(confirm_top_up_balance, pattern="^confirm_top_up_balance$"))
    # app.add_handler(CallbackQueryHandler(bitpappa_create_invoice, pattern=r"^create_invoice$"))


    # app.add_handler(CallbackQueryHandler(register_subscription_handlers(app)))

    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_users_search_text))
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_compose))
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_settings_roles_input))


    register_handlers(app)
    register_subscription_handlers(app)
    register_my_subscriptions_handlers(app)
    register_wallet_handlers(app)
    register_topup_handlers(app)
    # app.post_shutdown(shutdown_bitpapa)

    # отладка: показать доступные хуки (можно убрать в проде)
    print("Builder/hooks registered via builder. App object:", type(app))

    # запуск (blocking)
    app.run_polling()

    # try:
    #     await app.run_polling()
    # finally:
    #     # Корректно останавливаем listener
    #     await listener.stop()

if __name__ == "__main__":
    # run_db_tasks(engine)  # Uncomment to reset DB (drops and recreates tables)
    # asyncio.run(main())
    main()
