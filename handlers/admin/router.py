from telegram import Update
from telegram.ext import ContextTypes

from handlers.admin.dashboard import admin_dashboard
from handlers.admin.users import admin_users_router
from handlers.admin.subscriptions import admin_subscriptions_router
from handlers.admin.payments import admin_payments_router
from handlers.admin.servers import admin_servers_router
from handlers.admin.workers import admin_workers_router
from handlers.admin.logs import admin_logs_router
from handlers.admin.broadcast import admin_broadcast_router
from handlers.admin.settings import admin_settings_router


async def admin_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("admin:dashboard"):
        return await admin_dashboard(update, context)

    if data.startswith("admin:users"):
        return await admin_users_router(update, context)

    if data.startswith("admin:subscriptions"):
        return await admin_subscriptions_router(update, context)

    if data.startswith("admin:payments"):
        return await admin_payments_router(update, context)

    if data.startswith("admin:servers"):
        return await admin_servers_router(update, context)

    if data.startswith("admin:workers"):
        return await admin_workers_router(update, context)

    if data.startswith("admin:logs"):
        return await admin_logs_router(update, context)

    if data.startswith("admin:broadcast"):
        return await admin_broadcast_router(update, context)

    if data.startswith("admin:settings"):
        return await admin_settings_router(update, context)


# async def admin_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     data = query.data

#     if data == "admin:dashboard":
#         return await admin_dashboard(update, context)

#     if data.startswith("admin:users"):
#         return await admin_users_router(update, context)

#     if data.startswith("admin:subscriptions"):
#         return await admin_subscriptions_router(update, context)

#     if data.startswith("admin:payments"):
#         return await admin_payments_router(update, context)

#     if data.startswith("admin:servers"):
#         return await admin_servers_router(update, context)

#     if data.startswith("admin:workers"):
#         return await admin_workers_router(update, context)

#     if data.startswith("admin:logs"):
#         return await admin_logs_router(update, context)

#     if data.startswith("admin:broadcast"):
#         return await admin_broadcast_router(update, context)

#     if data.startswith("admin:settings"):
#         return await admin_settings_router(update, context)
