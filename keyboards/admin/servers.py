from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_servers_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Список серверов", callback_data="admin:servers:list:0")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:dashboard")],
    ])


def admin_servers_list_keyboard(page: int, total: int, page_size: int):
    offset = page * page_size
    buttons = []

    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin:servers:list:{page - 1}"))
    if offset + page_size < total:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin:servers:list:{page + 1}"))

    rows = []
    if buttons:
        rows.append(buttons)

    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin:servers")])
    return InlineKeyboardMarkup(rows)


def admin_server_view_keyboard(server):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Capacity", callback_data=f"admin:server:capacity:{server.id}")],
        [InlineKeyboardButton("⚙️ Статус", callback_data=f"admin:server:status:{server.id}")],
        [InlineKeyboardButton("🟡 Drain", callback_data=f"admin:server:drain:{server.id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin:servers")],
    ])


def admin_server_capacity_keyboard(server_id: int, current_capacity: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{current_capacity - 50}", callback_data=f"admin:server:capacity:set:{server_id}:{current_capacity - 50}")],
        [InlineKeyboardButton(f"{current_capacity}", callback_data=f"admin:server:capacity:set:{server_id}:{current_capacity}")],
        [InlineKeyboardButton(f"{current_capacity + 50}", callback_data=f"admin:server:capacity:set:{server_id}:{current_capacity + 50}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"admin:server:view:{server_id}")],
    ])


def admin_server_status_keyboard(server_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 online", callback_data=f"admin:server:status:set:{server_id}:online")],
        [InlineKeyboardButton("🔴 offline", callback_data=f"admin:server:status:set:{server_id}:offline")],
        [InlineKeyboardButton("🟡 draining", callback_data=f"admin:server:status:set:{server_id}:draining")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"admin:server:view:{server_id}")],
    ])
