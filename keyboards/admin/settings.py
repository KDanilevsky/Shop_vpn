from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_settings_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧩 Feature Flags", callback_data="admin:settings:features")],
        [InlineKeyboardButton("🛠 Maintenance Mode", callback_data="admin:settings:maintenance")],
        [InlineKeyboardButton("👮 Admin Roles", callback_data="admin:settings:roles")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:dashboard")],
    ])


def admin_settings_feature_flags_keyboard(flags: dict):
    rows = []
    for key, value in flags.items():
        label = f"{key}: {'🟢 ON' if value == 'on' else '🔴 OFF'}"
        rows.append([
            InlineKeyboardButton(label, callback_data=f"admin:settings:feature_toggle:{key}")
        ])

    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin:settings")])
    return InlineKeyboardMarkup(rows)


def admin_settings_maintenance_keyboard(current: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 ON", callback_data="admin:settings:maintenance:set:on")],
        [InlineKeyboardButton("🔴 OFF", callback_data="admin:settings:maintenance:set:off")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:settings")],
    ])


def admin_settings_roles_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:settings")],
    ])
