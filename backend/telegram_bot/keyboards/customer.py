from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from telegram_bot.translations import get_text


def get_customer_main_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Customer main menu keyboard.
    Shows: Create Order, My Orders, My Containers, Cancel Order, Help, Language
    """
    builder = ReplyKeyboardBuilder()

    # Row 1: Create Order, My Orders
    builder.button(text=get_text("btn_create_order", lang))
    builder.button(text=get_text("btn_my_orders", lang))

    # Row 2: My Containers, Cancel Order
    builder.button(text=get_text("btn_my_containers", lang))
    builder.button(text=get_text("btn_cancel_order", lang))

    # Row 3: Help, Language
    builder.button(text=get_text("btn_help", lang))
    builder.button(text=get_text("btn_change_language", lang))

    builder.adjust(2, 2, 2)  # 2 buttons per row
    return builder.as_markup(resize_keyboard=True)


def get_customer_cancel_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Keyboard shown during order creation.
    Shows: Cancel, Help
    """
    builder = ReplyKeyboardBuilder()

    builder.button(text=get_text("btn_cancel_operation", lang))
    builder.button(text=get_text("btn_help", lang))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_operation_type_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Keyboard for selecting operation type (Load/Unload).
    """
    builder = InlineKeyboardBuilder()

    # Load = Погрузка = Ортишга (customer bringing empty container)
    builder.button(text=get_text("btn_load", lang), callback_data="operation_LOAD")
    # Unload = Разгрузка = Тушуришга (customer bringing full container)
    builder.button(text=get_text("btn_unload", lang), callback_data="operation_UNLOAD")

    builder.adjust(2)
    return builder.as_markup()


def get_plate_confirmation_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Keyboard for confirming recognized plate number.
    """
    builder = (())

    builder.button(text=get_text("btn_confirm", lang), callback_data="plate_confirm")
    builder.button(text=get_text("btn_edit", lang), callback_data="plate_edit")

    builder.adjust(2)
    return builder.as_markup()


def get_order_confirmation_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Keyboard for final order confirmation.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text=get_text("btn_confirm", lang), callback_data="order_confirm")
    builder.button(text=get_text("btn_cancel", lang), callback_data="order_cancel")

    builder.adjust(2)
    return builder.as_markup()


def get_order_list_keyboard(orders, lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Keyboard showing list of pending orders for cancellation.

    Args:
        orders: List/QuerySet of PreOrder instances
        lang: Language code
    """
    builder = InlineKeyboardBuilder()

    for order in orders:
        # Show plate number and operation type
        operation_text = (
            get_text("operation_load_short", lang)
            if order.operation_type == "LOAD"
            else get_text("operation_unload_short", lang)
        )
        btn_text = f"{order.plate_number} - {operation_text}"
        builder.button(text=btn_text, callback_data=f"cancel_order_{order.id}")

    # Back button
    builder.button(text=get_text("btn_back", lang), callback_data="back_to_menu")

    # 1 button per row
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_order_confirm_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Confirmation keyboard for order cancellation.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text=get_text("btn_confirm_cancel", lang), callback_data="cancel_confirm_yes"
    )
    builder.button(text=get_text("btn_no", lang), callback_data="cancel_confirm_no")

    builder.adjust(2)
    return builder.as_markup()


# ============ CONTAINER CABINET KEYBOARDS ============


def get_container_list_keyboard(
    containers, page: int, total_pages: int, lang: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Keyboard for container list with pagination.

    Args:
        containers: List of ContainerEntry objects
        page: Current page number
        total_pages: Total number of pages
        lang: Language code
    """
    builder = InlineKeyboardBuilder()

    # Container buttons
    for entry in containers:
        container_number = entry.container.container_number
        dwell_days = entry.dwell_time_days or 0
        btn_text = f"📦 {container_number} ({dwell_days} {get_text('days_short', lang)})"
        builder.button(text=btn_text, callback_data=f"cnt_{entry.id}")

    # Pagination row
    pagination_buttons = []

    if page > 1:
        pagination_buttons.append(("◀️", f"cnt_page_{page - 1}"))

    # Page indicator (not clickable, but we make it a callback for layout)
    page_text = f"{page}/{total_pages}"
    pagination_buttons.append((page_text, "cnt_page_current"))

    if page < total_pages:
        pagination_buttons.append(("▶️", f"cnt_page_{page + 1}"))

    for text, callback in pagination_buttons:
        builder.button(text=text, callback_data=callback)

    # Action row: Search, Back to menu
    builder.button(
        text=get_text("btn_search_container", lang), callback_data="cnt_search"
    )
    builder.button(text=get_text("btn_back", lang), callback_data="cnt_back_to_menu")

    # Layout: containers (1 per row), pagination (2-3), actions (2)
    container_count = len(containers)
    pagination_count = len(pagination_buttons)
    builder.adjust(*([1] * container_count), pagination_count, 2)

    return builder.as_markup()


def get_container_list_empty_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for empty container list - just back button"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("btn_back", lang), callback_data="cnt_back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_container_detail_keyboard(
    entry_id: int, photo_count: int, lang: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Keyboard for container detail view.

    Args:
        entry_id: ContainerEntry ID
        photo_count: Number of photos attached
        lang: Language code
    """
    builder = InlineKeyboardBuilder()

    # Photos button (only if there are photos)
    if photo_count > 0:
        btn_text = f"📸 {get_text('btn_photos', lang)} ({photo_count})"
        builder.button(text=btn_text, callback_data=f"cnt_photos_{entry_id}")

    # Back to list
    builder.button(
        text=get_text("btn_back_to_list", lang), callback_data="cnt_back_to_list"
    )

    # Layout: photos button + back, or just back
    if photo_count > 0:
        builder.adjust(1, 1)
    else:
        builder.adjust(1)

    return builder.as_markup()


def get_container_search_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard during container search - just cancel button"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_cancel_search", lang), callback_data="cnt_cancel_search"
    )
    builder.adjust(1)
    return builder.as_markup()
