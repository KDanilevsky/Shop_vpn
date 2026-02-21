import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import TELEGRAM_TOKEN

from utils.db import create_engine_and_sessionmaker
from handlers.help import get_admin_conversation_handler

from handlers.start import start
from handlers.bottom_menu import bottom_menu_router
from handlers.inline_router import inline_router
from handlers.shop import register_shop_handlers

from handlers.wallet import wallet_handler, wallet_callback_router
from handlers.topup import topup_handler, topup_callback_router
from handlers.admin import admin_handler, admin_callback_router
from handlers.about import about_handler, about_callback_router
from handlers.help import help_handler, help_callback_router

from handlers.share import share_handler, referal_link
from handlers.settings import settings
from handlers.plusses import pluses

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config import DATABASE_URL_PG

from utils.models import Base

# # engine, SessionLocal = create_engine_and_sessionmaker()
engine = create_async_engine(DATABASE_URL_PG, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# # OPTIONAL DB INIT
from utils.init_db import run_db_tasks


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    # Pass SessionLocal to handlers
    register_shop_handlers(app, SessionLocal)

    app.add_handler(get_admin_conversation_handler())

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bottom_menu_router))

    app.add_handler(CallbackQueryHandler(inline_router, pattern="^(buy|page_|back_main)$"))
    app.add_handler(CallbackQueryHandler(wallet_callback_router, pattern="^(my_accounts|balance_top_up|auto_pay_subs|count|back:wallet)$"))
    app.add_handler(CallbackQueryHandler(topup_callback_router, pattern="^(balance_top_up|pay_help|apeal_account_didnt_paid|back:topup)$"))
    app.add_handler(CallbackQueryHandler(admin_callback_router, pattern="^(admin_reply|admin_send_all|admin_mark_all_users_on_server|adm_plus_usr_days|adm_user_info|adm_block_user|adm_unblock_user|adm_part_info|adm_add_partner|adm_show_partners|adm_pay_partner|back:admin)$"))
    app.add_handler(CallbackQueryHandler(about_callback_router, pattern="^(pluses|free|usl|ref|back:about)$"))
    app.add_handler(CallbackQueryHandler(help_callback_router, pattern="^(call_adm|back:help)$"))
    

    # app.add_handler(CommandHandler("create_invoice", bitpappa_create_invoice))
    # app.add_handler(CommandHandler("ref", referal_link))
    # app.add_handler(CommandHandler("settings", settings))
    # app.add_handler(CommandHandler("pluses", pluses))

    app.run_polling()


if __name__ == "__main__":
    # run_db_tasks(engine)  # Uncomment to reset DB (drops and recreates tables)
    main()
