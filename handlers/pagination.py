from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def paginated_menu(page: int, items_per_page=5):
    items = [f"Item {i}" for i in range(1, 26)]  # Example list

    start = page * items_per_page
    end = start + items_per_page
    page_items = items[start:end]

    keyboard = [
        [InlineKeyboardButton(item, callback_data=f"item_{item}")]
        for item in page_items
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"page_{page-1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton("Next ➡", callback_data=f"page_{page+1}"))

    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton("⬅ Back", callback_data="back_main")])

    return InlineKeyboardMarkup(keyboard)
