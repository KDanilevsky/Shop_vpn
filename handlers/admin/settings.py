from telegram import Update
from telegram.ext import ContextTypes

from keyboards.admin.settings import (
    admin_settings_menu_keyboard,
    admin_settings_feature_flags_keyboard,
    admin_settings_maintenance_keyboard,
    admin_settings_roles_keyboard,
)

from handlers.admin.permissions import require_permission, ADMIN_ROLES
from handlers.admin.audit import audit_log

from db.async_db import SessionLocal
from db.models import Settings
from sqlalchemy import select


# -----------------------------
# Router
# -----------------------------
async def admin_settings_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "admin:settings":
        return await admin_settings_menu(update, context)

    if data == "admin:settings:features":
        return await admin_settings_feature_flags(update, context)

    if data.startswith("admin:settings:feature_toggle:"):
        key = data.split(":")[-1]
        return await admin_settings_feature_toggle(update, context, key)

    if data == "admin:settings:maintenance":
        return await admin_settings_maintenance(update, context)

    if data.startswith("admin:settings:maintenance:set:"):
        mode = data.split(":")[-1]
        return await admin_settings_maintenance_set(update, context, mode)

    if data == "admin:settings:roles":
        return await admin_settings_roles(update, context)

    if data.startswith("admin:settings:roles:add:"):
        _, _, _, _, telegram_id, role = data.split(":")
        return await admin_settings_roles_add(update, context, int(telegram_id), role)

    if data.startswith("admin:settings:roles:remove:"):
        _, _, _, _, telegram_id = data.split(":")
        return await admin_settings_roles_remove(update, context, int(telegram_id))


# -----------------------------
# Main menu
# -----------------------------
@require_permission("settings.edit")
async def admin_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "<b>🔐 Settings — Admin Panel</b>\n\nВыберите категорию:"
    await query.message.edit_text(
        text,
        reply_markup=admin_settings_menu_keyboard(),
        parse_mode="HTML",
    )


# -----------------------------
# Feature flags
# -----------------------------
@require_permission("settings.edit")
async def admin_settings_feature_flags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        result = await session.execute(select(Settings))
        settings = result.scalars().all()

    flags = {s.key: s.value for s in settings if s.key.startswith("feature_")}

    text = "<b>🧩 Feature Flags</b>\n\nВключите или выключите функции:"
    await query.message.edit_text(
        text,
        reply_markup=admin_settings_feature_flags_keyboard(flags),
        parse_mode="HTML",
    )


@require_permission("settings.edit")
async def admin_settings_feature_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        setting = await session.get(Settings, key)
        before = setting.value
        setting.value = "off" if setting.value == "on" else "on"
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="settings.feature_toggle",
        target_type="settings",
        target_id=key,
        before={"value": before},
        after={"value": setting.value},
    )

    return await admin_settings_feature_flags(update, context)


# -----------------------------
# Maintenance mode
# -----------------------------
@require_permission("settings.edit")
async def admin_settings_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        mode = await session.get(Settings, "maintenance_mode")

    text = (
        "<b>🛠 Maintenance Mode</b>\n\n"
        f"Текущее состояние: <b>{mode.value}</b>"
    )

    await query.message.edit_text(
        text,
        reply_markup=admin_settings_maintenance_keyboard(mode.value),
        parse_mode="HTML",
    )


@require_permission("settings.edit")
async def admin_settings_maintenance_set(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
    query = update.callback_query
    await query.answer()

    async with SessionLocal() as session:
        setting = await session.get(Settings, "maintenance_mode")
        before = setting.value
        setting.value = mode
        await session.commit()

    await audit_log(
        admin_id=update.effective_user.id,
        action="settings.maintenance",
        target_type="settings",
        target_id="maintenance_mode",
        before={"value": before},
        after={"value": mode},
    )

    return await admin_settings_maintenance(update, context)


# -----------------------------
# Admin roles
# -----------------------------
@require_permission("roles.edit")
async def admin_settings_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "<b>👮 Admin Roles</b>\n\nТекущие администраторы:"
    for uid, role in ADMIN_ROLES.items():
        text += f"\n• <b>{uid}</b> — {role}"

    text += "\n\nВведите Telegram ID и роль через пробел:\nНапример: <code>123456789 ADMIN</code>"

    context.user_data["admin_state"] = "awaiting_role_assignment"

    await query.message.edit_text(
        text,
        reply_markup=admin_settings_roles_keyboard(),
        parse_mode="HTML",
    )

@require_permission("roles.edit")
async def admin_settings_roles_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only handle if we are in the correct state
    if context.user_data.get("admin_state") != "awaiting_role_assignment":
        return

    text = update.message.text.strip()

    # Expect: "<id> <role>"
    parts = text.split()
    if len(parts) != 2:
        return await update.message.reply_text(
            "❌ Формат неверный.\nВведите: <code>ID ROLE</code>\nНапример: <code>123456789 ADMIN</code>",
            parse_mode="HTML",
        )

    telegram_id_str, role = parts

    # Validate ID
    if not telegram_id_str.isdigit():
        return await update.message.reply_text("❌ ID должен быть числом.")

    telegram_id = int(telegram_id_str)

    # Apply role
    ADMIN_ROLES[telegram_id] = role.upper()

    # Audit log
    await audit_log(
        admin_id=update.effective_user.id,
        action="roles.add",
        target_type="admin",
        target_id=telegram_id,
        before={},
        after={"role": role.upper()},
    )

    # Reset state
    context.user_data["admin_state"] = None

    # Return to roles menu
    return await admin_settings_roles(update, context)



@require_permission("roles.edit")
async def admin_settings_roles_add(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int, role: str):
    ADMIN_ROLES[telegram_id] = role

    await audit_log(
        admin_id=update.effective_user.id,
        action="roles.add",
        target_type="admin",
        target_id=telegram_id,
        before={},
        after={"role": role},
    )

    await update.callback_query.message.edit_text("Добавлено.")
    return await admin_settings_roles(update, context)


@require_permission("roles.edit")
async def admin_settings_roles_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int):
    before = ADMIN_ROLES.get(telegram_id)
    ADMIN_ROLES.pop(telegram_id, None)

    await audit_log(
        admin_id=update.effective_user.id,
        action="roles.remove",
        target_type="admin",
        target_id=telegram_id,
        before={"role": before},
        after={},
    )

    await update.callback_query.message.edit_text("Удалено.")
    return await admin_settings_roles(update, context)
