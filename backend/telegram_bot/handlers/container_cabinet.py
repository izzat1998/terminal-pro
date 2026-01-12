"""
Handlers for customer container cabinet.
Allows customers to view their company's containers on terminal.
"""

import html
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from asgiref.sync import sync_to_async

from telegram_bot.keyboards.customer import (
    get_container_detail_keyboard,
    get_container_list_empty_keyboard,
    get_container_list_keyboard,
    get_container_search_keyboard,
    get_customer_main_keyboard,
)
from telegram_bot.middleware import require_customer_access
from telegram_bot.services.container_cabinet_service import ContainerCabinetService
from telegram_bot.states.customer import CustomerContainerCabinet
from telegram_bot.translations import get_text


logger = logging.getLogger(__name__)

router = Router()
cabinet_service = ContainerCabinetService()


async def get_user_language(state: FSMContext) -> str:
    """Get user's language from state"""
    data = await state.get_data()
    return data.get("language", "ru")


def format_container_detail(entry, lang: str) -> str:
    """Format container entry details for display"""
    # Basic info
    text = get_text("container_detail", lang).format(
        number=html.escape(entry.container.container_number),
        status=entry.get_status_display(),
        iso_type=entry.container.iso_type,
        entry_date=entry.entry_time.strftime("%d.%m.%Y %H:%M"),
        dwell_days=entry.dwell_time_days or 0,
    )

    # Optional fields
    if entry.cargo_name:
        text += get_text("container_detail_cargo", lang).format(
            cargo=html.escape(entry.cargo_name)
        ) + "\n"

    if entry.cargo_weight:
        text += get_text("container_detail_weight", lang).format(
            weight=f"{entry.cargo_weight:,.0f}"
        ) + "\n"

    if entry.location:
        text += get_text("container_detail_location", lang).format(
            location=html.escape(entry.location)
        ) + "\n"

    if entry.container_owner:
        text += get_text("container_detail_owner", lang).format(
            owner=html.escape(entry.container_owner.name)
        ) + "\n"

    if entry.transport_number:
        text += get_text("container_detail_transport", lang).format(
            type=entry.get_transport_type_display(),
            number=html.escape(entry.transport_number),
        ) + "\n"

    return text


# ============ LIST VIEW ============


@router.message(F.text.in_(["📦 Мои контейнеры", "📦 Mening konteynerlarim"]))
@require_customer_access
async def cmd_my_containers(message: Message, state: FSMContext, user=None):
    """Show paginated container list"""
    lang = await get_user_language(state)
    customer = user

    # Check if customer has a company
    company = await sync_to_async(cabinet_service.get_customer_company)(customer)

    if not company:
        await message.answer(
            get_text("container_no_company", lang),
            reply_markup=get_customer_main_keyboard(lang),
        )
        return

    # Fetch containers
    result = await sync_to_async(cabinet_service.get_active_containers)(customer, page=1)

    if result.total_count == 0:
        await message.answer(
            get_text("container_list_empty", lang),
            reply_markup=get_container_list_empty_keyboard(lang),
        )
        await state.set_state(CustomerContainerCabinet.viewing_list)
        return

    # Store current page in state
    await state.update_data(container_page=1)
    await state.set_state(CustomerContainerCabinet.viewing_list)

    # Show list
    text = get_text("container_list_header", lang).format(count=result.total_count)
    await message.answer(
        text,
        reply_markup=get_container_list_keyboard(
            result.containers, result.page, result.total_pages, lang
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("cnt_page_"), CustomerContainerCabinet.viewing_list)
@require_customer_access
async def navigate_container_page(callback: CallbackQuery, state: FSMContext, user=None):
    """Handle pagination navigation"""
    lang = await get_user_language(state)
    customer = user

    # Handle current page indicator click (no-op)
    if callback.data == "cnt_page_current":
        await callback.answer()
        return

    # Extract page number
    try:
        page = int(callback.data.replace("cnt_page_", ""))
    except ValueError:
        await callback.answer(get_text("invalid_selection", lang), show_alert=True)
        return

    # Fetch containers for requested page
    result = await sync_to_async(cabinet_service.get_active_containers)(customer, page=page)

    if result.total_count == 0:
        await callback.message.edit_text(
            get_text("container_list_empty", lang),
            reply_markup=get_container_list_empty_keyboard(lang),
        )
        await callback.answer()
        return

    # Update state and message
    await state.update_data(container_page=page)

    text = get_text("container_list_header", lang).format(count=result.total_count)
    await callback.message.edit_text(
        text,
        reply_markup=get_container_list_keyboard(
            result.containers, result.page, result.total_pages, lang
        ),
        parse_mode="HTML",
    )
    await callback.answer()


# ============ CONTAINER DETAIL ============


@router.callback_query(
    F.data.regexp(r"^cnt_\d+$"),  # Match only cnt_{number} pattern
    CustomerContainerCabinet.viewing_list,
)
@require_customer_access
async def show_container_detail(callback: CallbackQuery, state: FSMContext, user=None):
    """Show container detail card"""
    lang = await get_user_language(state)
    customer = user

    # Extract entry ID
    try:
        entry_id = int(callback.data.replace("cnt_", ""))
    except ValueError:
        await callback.answer(get_text("invalid_selection", lang), show_alert=True)
        return

    # Get container with access validation
    entry = await sync_to_async(cabinet_service.get_container_by_id)(customer, entry_id)

    if not entry:
        await callback.answer(get_text("container_search_not_found", lang), show_alert=True)
        return

    # Get photo count
    photo_count = await sync_to_async(cabinet_service.get_photo_count)(entry_id)

    # Store current entry ID for back navigation
    await state.update_data(current_entry_id=entry_id)
    await state.set_state(CustomerContainerCabinet.viewing_details)

    # Format and show detail
    text = format_container_detail(entry, lang)
    await callback.message.edit_text(
        text,
        reply_markup=get_container_detail_keyboard(entry_id, photo_count, lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "cnt_back_to_list", CustomerContainerCabinet.viewing_details)
@require_customer_access
async def back_to_container_list(callback: CallbackQuery, state: FSMContext, user=None):
    """Return to container list from detail view"""
    lang = await get_user_language(state)
    customer = user

    # Get current page from state
    data = await state.get_data()
    page = data.get("container_page", 1)

    # Fetch containers
    result = await sync_to_async(cabinet_service.get_active_containers)(customer, page=page)

    await state.set_state(CustomerContainerCabinet.viewing_list)

    if result.total_count == 0:
        await callback.message.edit_text(
            get_text("container_list_empty", lang),
            reply_markup=get_container_list_empty_keyboard(lang),
        )
    else:
        text = get_text("container_list_header", lang).format(count=result.total_count)
        await callback.message.edit_text(
            text,
            reply_markup=get_container_list_keyboard(
                result.containers, result.page, result.total_pages, lang
            ),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(F.data == "cnt_back_to_menu", CustomerContainerCabinet.viewing_list)
@require_customer_access
async def container_cabinet_back_to_menu(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """Return to main menu from container cabinet"""
    lang = await get_user_language(state)

    # Delete the inline keyboard message
    await callback.message.delete()

    # Send main menu
    await callback.message.answer(
        get_text("choose_action", lang),
        reply_markup=get_customer_main_keyboard(lang),
    )

    # Clear state but keep language
    await state.clear()
    await state.update_data(language=lang)
    await callback.answer()


# ============ SEARCH ============


@router.callback_query(F.data == "cnt_search", CustomerContainerCabinet.viewing_list)
@require_customer_access
async def start_container_search(callback: CallbackQuery, state: FSMContext, user=None):
    """Start container search flow"""
    lang = await get_user_language(state)

    await state.set_state(CustomerContainerCabinet.searching)

    await callback.message.edit_text(
        get_text("container_search_prompt", lang),
        reply_markup=get_container_search_keyboard(lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "cnt_cancel_search", CustomerContainerCabinet.searching)
@require_customer_access
async def cancel_container_search(callback: CallbackQuery, state: FSMContext, user=None):
    """Cancel search and return to list"""
    lang = await get_user_language(state)
    customer = user

    # Fetch containers
    result = await sync_to_async(cabinet_service.get_active_containers)(customer, page=1)

    await state.update_data(container_page=1)
    await state.set_state(CustomerContainerCabinet.viewing_list)

    if result.total_count == 0:
        await callback.message.edit_text(
            get_text("container_list_empty", lang),
            reply_markup=get_container_list_empty_keyboard(lang),
        )
    else:
        text = get_text("container_list_header", lang).format(count=result.total_count)
        await callback.message.edit_text(
            text,
            reply_markup=get_container_list_keyboard(
                result.containers, result.page, result.total_pages, lang
            ),
            parse_mode="HTML",
        )

    await callback.answer()


@router.message(CustomerContainerCabinet.searching, F.text)
@require_customer_access
async def process_container_search(message: Message, state: FSMContext, user=None):
    """Process container search query"""
    lang = await get_user_language(state)
    customer = user

    search_query = message.text.strip()

    # Search container
    entry = await sync_to_async(cabinet_service.search_container)(customer, search_query)

    if not entry:
        await message.answer(
            get_text("container_search_not_found", lang),
            reply_markup=get_container_search_keyboard(lang),
        )
        return

    # Get photo count
    photo_count = await sync_to_async(cabinet_service.get_photo_count)(entry.id)

    # Show detail
    await state.update_data(current_entry_id=entry.id)
    await state.set_state(CustomerContainerCabinet.viewing_details)

    text = format_container_detail(entry, lang)
    await message.answer(
        text,
        reply_markup=get_container_detail_keyboard(entry.id, photo_count, lang),
        parse_mode="HTML",
    )


# ============ PHOTOS ============


@router.callback_query(F.data.startswith("cnt_photos_"), CustomerContainerCabinet.viewing_details)
@require_customer_access
async def send_container_photos(callback: CallbackQuery, state: FSMContext, user=None):
    """Send container photos as media album"""
    lang = await get_user_language(state)
    customer = user

    # Extract entry ID
    try:
        entry_id = int(callback.data.replace("cnt_photos_", ""))
    except ValueError:
        await callback.answer(get_text("invalid_selection", lang), show_alert=True)
        return

    # Validate access
    entry = await sync_to_async(cabinet_service.get_container_by_id)(customer, entry_id)
    if not entry:
        await callback.answer(get_text("container_search_not_found", lang), show_alert=True)
        return

    # Get photos
    photos = await sync_to_async(cabinet_service.get_container_photos)(entry_id)

    if not photos:
        await callback.answer(get_text("photos_none", lang), show_alert=True)
        return

    # Show sending indicator
    await callback.answer(get_text("photos_sending", lang))

    try:
        # Build media group
        media_group = []
        for idx, attachment in enumerate(photos):
            file_path = attachment.file.file.path
            input_file = FSInputFile(file_path)

            if idx == 0:
                caption = f"📦 {entry.container.container_number}"
                media_group.append(InputMediaPhoto(media=input_file, caption=caption))
            else:
                media_group.append(InputMediaPhoto(media=input_file))

        # Send album
        await callback.bot.send_media_group(
            chat_id=callback.from_user.id,
            media=media_group,
        )

        # Confirmation message
        await callback.message.answer(
            get_text("photos_sent", lang).format(count=len(media_group)),
        )

    except Exception as e:
        logger.error(f"Error sending photos for entry {entry_id}: {e}")
        await callback.message.answer(get_text("photos_none", lang))
