from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.terminal_operations.models import ContainerOwner
from telegram_bot.translations import get_text


def get_iso_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting container ISO type - organized by size"""
    builder = InlineKeyboardBuilder()

    # Organized by size for easy visual scanning
    # 20-foot containers (22)
    iso_20 = [
        ("22G1", "22G1"),
        ("22R1", "22R1"),
        ("22U1", "22U1"),
        ("22P1", "22P1"),
        ("22T1", "22T1"),
    ]

    # 40-foot containers (42)
    iso_40 = [
        ("42G1", "42G1"),
        ("42R1", "42R1"),
        ("42U1", "42U1"),
        ("42P1", "42P1"),
        ("42T1", "42T1"),
    ]

    # 40HC containers (45)
    iso_40hc = [
        ("45G1", "45G1"),
        ("45R1", "45R1"),
        ("45U1", "45U1"),
        ("45P1", "45P1"),
    ]

    # 45-foot containers (L5)
    iso_45 = [
        ("L5G1", "L5G1"),
        ("L5R1", "L5R1"),
    ]

    # Add 20' section
    for code, label in iso_20:
        builder.button(text=label, callback_data=f"iso_{code}")
    builder.adjust(5)  # 5 buttons in one row for 20'

    # Add 40' section
    for code, label in iso_40:
        builder.button(text=label, callback_data=f"iso_{code}")
    builder.adjust(5, 5)  # Keep 20' row, add 5 buttons for 40'

    # Add 40HC section
    for code, label in iso_40hc:
        builder.button(text=label, callback_data=f"iso_{code}")
    builder.adjust(5, 5, 4)  # 20', 40', 40HC rows

    # Add 45' section
    for code, label in iso_45:
        builder.button(text=label, callback_data=f"iso_{code}")
    builder.adjust(5, 5, 4, 2)  # All rows

    return builder.as_markup()


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for language selection"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.button(text="🇺🇿 O'zbek", callback_data="lang_uz")

    builder.adjust(2)
    return builder.as_markup()


def get_status_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for selecting container status"""
    builder = InlineKeyboardBuilder()

    builder.button(text=get_text("btn_laden", lang), callback_data="status_LADEN")
    builder.button(text=get_text("btn_empty", lang), callback_data="status_EMPTY")

    builder.adjust(2)
    return builder.as_markup()


def get_transport_type_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for selecting transport type"""
    builder = InlineKeyboardBuilder()

    builder.button(text=get_text("btn_truck", lang), callback_data="transport_TRUCK")
    builder.button(text=get_text("btn_wagon", lang), callback_data="transport_WAGON")

    builder.adjust(2)
    return builder.as_markup()


def get_photo_skip_keyboard(
    lang: str = "ru", has_photos: bool = False
) -> InlineKeyboardMarkup:
    """
    Keyboard for photo upload step.

    Args:
        lang: Language code
        has_photos: If True, shows only "Done" button. If False, shows both "Skip" and "Done"
    """
    builder = InlineKeyboardBuilder()

    if has_photos:
        # User already uploaded photos - only show "Done" button
        builder.button(text=get_text("btn_done", lang), callback_data="done_photos")
        builder.adjust(1)
    else:
        # No photos yet - show both "Skip" and "Done" buttons
        builder.button(text=get_text("btn_skip", lang), callback_data="skip_photos")
        builder.button(text=get_text("btn_done", lang), callback_data="done_photos")
        builder.adjust(2)

    return builder.as_markup()


def get_plate_confirmation_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for confirming or editing detected plate number"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text=get_text("btn_confirm_plate", lang), callback_data="confirm_plate"
    )
    builder.button(text=get_text("btn_edit_plate", lang), callback_data="edit_plate")

    builder.adjust(2)
    return builder.as_markup()


async def get_container_owner_keyboard(
    lang: str = "ru",
) -> tuple[InlineKeyboardMarkup, bool]:
    """
    Keyboard for selecting container owner.
    Fetches owners from database asynchronously and displays them with skip option.

    Args:
        lang: Language code

    Returns:
        Tuple of (InlineKeyboardMarkup with owner buttons (2 per row) and skip button on separate row,
                  bool indicating if there are owners available)
    """
    from asgiref.sync import sync_to_async

    builder = InlineKeyboardBuilder()

    # Fetch all container owners from database asynchronously
    owners = await sync_to_async(list)(ContainerOwner.objects.all().order_by("name"))
    has_owners = len(owners) > 0

    # Add button for each owner
    for owner in owners:
        builder.button(text=owner.name, callback_data=f"owner_{owner.id}")

    # Adjust layout: 2 buttons per row
    if has_owners:
        # Calculate rows needed for owners (2 per row)
        owner_rows = [2] * (len(owners) // 2)
        if len(owners) % 2 == 1:
            owner_rows.append(1)

        # Add skip button on separate row
        builder.button(
            text=get_text("btn_skip_owner", lang), callback_data="owner_skip"
        )
        builder.adjust(*owner_rows, 1)  # owners in rows of 2, then skip on separate row
    else:
        # No owners in database - only show skip button
        builder.button(
            text=get_text("btn_skip_owner", lang), callback_data="owner_skip"
        )
        builder.adjust(1)

    return builder.as_markup(), has_owners


def get_confirmation_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for final confirmation"""
    builder = InlineKeyboardBuilder()

    builder.button(text=get_text("btn_confirm", lang), callback_data="confirm_yes")
    builder.button(text=get_text("btn_cancel", lang), callback_data="confirm_no")

    builder.adjust(2)
    return builder.as_markup()


def get_request_access_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for requesting bot access"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text=get_text("btn_request_access", lang), callback_data="request_bot_access"
    )

    return builder.as_markup()


def get_phone_share_keyboard(lang: str = "ru"):
    """Keyboard for sharing phone number (ReplyKeyboardMarkup with contact button)"""
    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

    button = KeyboardButton(
        text=get_text("btn_share_phone", lang), request_contact=True
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button]], resize_keyboard=True, one_time_keyboard=True
    )

    return keyboard


def get_exit_transport_type_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for selecting exit transport type (TRUCK, WAGON)"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text=get_text("btn_truck", lang), callback_data="exit_transport_TRUCK"
    )
    builder.button(
        text=get_text("btn_wagon", lang), callback_data="exit_transport_WAGON"
    )

    builder.adjust(2)  # 2 buttons in one row
    return builder.as_markup()


def get_skip_optional_field_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for skipping optional fields (destination station, crane operations)"""
    builder = InlineKeyboardBuilder()

    builder.button(text=get_text("btn_skip", lang), callback_data="skip_optional_field")
    builder.button(text=get_text("btn_done", lang), callback_data="done_optional_field")

    builder.adjust(2)
    return builder.as_markup()


def get_done_crane_operations_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for completing crane operations entry"""
    builder = InlineKeyboardBuilder()

    builder.button(text=get_text("btn_skip", lang), callback_data="skip_crane_ops")
    builder.button(text=get_text("btn_done", lang), callback_data="done_crane_ops")

    builder.adjust(2)
    return builder.as_markup()


def get_crane_operation_actions_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for add more or done after adding crane operation"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text=get_text("btn_add_more_crane_op", lang), callback_data="crane_op_add_more"
    )
    builder.button(
        text=get_text("btn_done_crane_op", lang), callback_data="crane_op_done"
    )

    builder.adjust(2)
    return builder.as_markup()
