from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ROLES
# ADMIN_ROLES = {
#     # telegram_id: role
#     123456789: "OWNER",
#     987654321: "ADMIN",
# }

ROLE_PERMISSIONS = {
    "OWNER": {"*"},
    "ADMIN": {
        "dashboard.view",
        "users.view", "users.edit",
        "subscriptions.view", "subscriptions.edit",
        "payments.view", "payments.edit",
        "servers.view", "servers.edit",
        "workers.view", "workers.edit",
        "logs.view",
        "broadcast.send",
        "settings.edit",
    },
    "SUPPORT": {
        "dashboard.view",
        "users.view",
        "subscriptions.view",
        "payments.view",
        "logs.view",
    },
    "READONLY": {
        "dashboard.view",
        "users.view",
        "subscriptions.view",
        "payments.view",
        "servers.view",
        "workers.view",
        "logs.view",
    },
}

def require_permission(permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            role = ADMIN_ROLES.get(user_id)

            if not role:
                return await update.effective_message.reply_text("⛔ Access denied")

            perms = ROLE_PERMISSIONS.get(role, set())

            if "*" not in perms and permission not in perms:
                return await update.effective_message.reply_text("⛔ Permission denied")

            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator
