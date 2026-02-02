"""
Handlers for container exit flow via Telegram bot
"""

import html
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError

from apps.core.exceptions import (
    BusinessLogicError,
    ContainerNotFoundError,
    DuplicateEntryError,
)
from apps.core.services import ActivityLogService

# Import shared photo handling utilities
from telegram_bot.handlers.photos import (
    cancel_photo_confirmation_task,
    download_photos_from_telegram,
    handle_photo_upload,
)
from telegram_bot.keyboards import inline, reply
from telegram_bot.middleware import require_manager_access
from telegram_bot.services.entry_service import BotEntryService
from telegram_bot.services.owner_notification_service import OwnerNotificationService
from telegram_bot.services.plate_recognizer_service import PlateRecognizerService
from telegram_bot.states.entry import ExitForm
from telegram_bot.translations import (
    get_status_display,
    get_text,
    get_transport_display,
)
from telegram_bot.utils import format_container_number


logger = logging.getLogger(__name__)

# Create router for exit handlers
exit_router = Router()

# Service instances
entry_service = BotEntryService()
activity_log_service = ActivityLogService()
plate_recognizer_service = PlateRecognizerService()
owner_notification_service = OwnerNotificationService()

# Valid callback data values for validation
VALID_TRANSPORT_TYPES = {"TRUCK", "WAGON"}


def extract_entry_info(active_entry) -> dict:
    """
    Extract entry info from ContainerEntry object.
    Must be called in a synchronous context (via sync_to_async).
    """
    from django.contrib.contenttypes.models import ContentType

    from apps.files.models import FileAttachment

    owner_name = ""
    if active_entry.container_owner:
        owner_name = active_entry.container_owner.name

    # Get count of existing entry photos (container_photo type)
    content_type = ContentType.objects.get_for_model(active_entry)
    entry_photos_count = FileAttachment.objects.filter(
        content_type=content_type,
        object_id=active_entry.id,
        attachment_type="container_photo",
    ).count()

    return {
        "entry_id": active_entry.id,
        "container_number": active_entry.container.container_number,
        "iso_type": active_entry.container.iso_type,
        "status": active_entry.status,
        "entry_date": active_entry.entry_time.strftime("%Y-%m-%d %H:%M"),
        "transport_type": active_entry.transport_type,
        "transport_number": active_entry.transport_number or "",
        "entry_train_number": active_entry.entry_train_number or "",
        "client_name": active_entry.client_name or "",
        "cargo_name": active_entry.cargo_name or "",
        "container_owner": owner_name,
        "location": active_entry.location or "",
        "cargo_weight": active_entry.cargo_weight or "",
        "entry_photos_count": entry_photos_count,
    }


async def get_user_language(state: FSMContext) -> str:
    """Get user's language from state"""
    data = await state.get_data()
    return data.get("language", "ru")


async def build_exit_summary(entry_data: dict, lang: str) -> str:
    """Build a formatted HTML summary of collected exit data with entry information"""
    lines = []

    # Entry information section
    if entry_data.get("entry_info"):
        entry_info = entry_data["entry_info"]
        # Format container number as PREFIX | POSTFIX for better readability
        formatted_container = format_container_number(str(entry_info.get('container_number', '')))
        lines.append(f"<b>📦 {get_text('summary_container', lang)}:</b>")
        lines.append(
            f"<code>{html.escape(formatted_container)}</code> ({html.escape(str(entry_info.get('iso_type')))})"
        )
        lines.append("")

        # Entry entry details
        lines.append(f"<b>🕐 {get_text('summary_transport', lang)}:</b>")
        entry_date_str = entry_info.get("entry_date", "")
        lines.append(f"<i>{html.escape(entry_date_str)}</i>")

        entry_transport = entry_info.get("transport_type", "")
        if entry_transport:
            display_transport = get_transport_display(entry_transport, lang)
            lines.append(f"<code>{html.escape(display_transport)}</code>")

        if entry_info.get("transport_number"):
            lines.append(f"#{html.escape(str(entry_info.get('transport_number')))}")

        # Business info (with HTML escaping for user data)
        if entry_info.get("client_name"):
            lines.append(
                f"<b>👤 {get_text('exit_entry_client', lang)}:</b> {html.escape(str(entry_info.get('client_name')))}"
            )

        if entry_info.get("cargo_name"):
            lines.append(
                f"<b>📦 {get_text('exit_entry_cargo', lang)}:</b> {html.escape(str(entry_info.get('cargo_name')))}"
            )

        if entry_info.get("container_owner"):
            lines.append(
                f"<b>🏢 {get_text('exit_entry_owner', lang)}:</b> {html.escape(str(entry_info.get('container_owner')))}"
            )

        if entry_info.get("location"):
            lines.append(
                f"<b>📍 {get_text('exit_entry_location', lang)}:</b> {html.escape(str(entry_info.get('location')))}"
            )

        if entry_info.get("cargo_weight"):
            lines.append(
                f"<b>⚖️ {get_text('exit_entry_weight', lang)}:</b> {html.escape(str(entry_info.get('cargo_weight')))} т"
            )

        # Container status
        status = entry_info.get("status", "")
        if status:
            display_status = get_status_display(status, lang)
            lines.append(
                f"<b>📊 {get_text('summary_status', lang)}:</b> {display_status}"
            )

        # Entry photos (photos from when container entered terminal)
        entry_photos_count = entry_info.get("entry_photos_count", 0)
        if entry_photos_count > 0:
            lines.append(
                f"<b>📸 {get_text('entry_photos_header', lang)}:</b> {entry_photos_count} ✅"
            )

        lines.append("")

    # Exit information section
    if (
        entry_data.get("exit_date")
        or entry_data.get("exit_transport_type")
        or entry_data.get("exit_transport_number")
    ):
        lines.append(f"<b>🚪 {get_text('exit_confirmation_header', lang)}</b>")

        # Exit date
        if entry_data.get("exit_date"):
            # Format exit date for display (parse from ISO format if needed)
            exit_date_display = entry_data["exit_date"]
            try:
                from datetime import datetime as dt

                exit_dt = dt.fromisoformat(entry_data["exit_date"])
                exit_date_display = exit_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass  # Keep original format if parsing fails
            lines.append(
                f"<b>📅 {get_text('summary_exit_date', lang)}:</b> <code>{html.escape(exit_date_display)}</code> ✅"
            )

        # Exit transport type
        if entry_data.get("exit_transport_type"):
            display_type = get_transport_display(
                entry_data.get("exit_transport_type"), lang
            )
            lines.append(
                f"<b>🚛 {get_text('summary_exit_transport', lang)}:</b> <code>{html.escape(display_type)}</code> ✅"
            )

        # Exit transport number
        if entry_data.get("exit_transport_number"):
            lines.append(
                f"<b>📝 {get_text('summary_exit_transport_num', lang)}:</b> <code>{html.escape(entry_data['exit_transport_number'])}</code> ✅"
            )

        # Exit train number (optional)
        if entry_data.get("exit_train_number"):
            lines.append(
                f"<b>🚂 {get_text('summary_exit_train_num', lang)}:</b> <code>{html.escape(entry_data['exit_train_number'])}</code> ✅"
            )

        # Photos - only show if 'show_photos' flag is True (when user has reached photo step)
        if entry_data.get("show_photos"):
            if entry_data.get("photos"):
                lines.append(
                    f"<b>📸 {get_text('summary_photos', lang)}:</b> {len(entry_data['photos'])} ✅"
                )
            else:
                lines.append(
                    f"<b>📸 {get_text('summary_photos', lang)}:</b> {get_text('no_photos', lang)}"
                )

        lines.append("")

    return "\n".join(lines)


@exit_router.message(Command("exit"))
@require_manager_access
async def cmd_exit_container(message: Message, state: FSMContext, user=None):
    """Start container exit flow"""
    lang = await get_user_language(state)

    await state.clear()
    await state.update_data(language=lang)
    await state.set_state(ExitForm.container_number)

    await message.answer(
        get_text("start_exit", lang), reply_markup=reply.get_cancel_keyboard(lang)
    )


@exit_router.message(ExitForm.container_number)
@require_manager_access
async def process_exit_container_number(message: Message, state: FSMContext, user=None):
    """Process container number for exit"""
    lang = await get_user_language(state)

    if not message.text:
        await message.answer(
            get_text("error_text_only", lang),
            reply_markup=reply.get_cancel_keyboard(lang),
        )
        return

    raw_input = message.text.strip()

    # Validate format (accepts with or without spaces)
    # Note: validate_container_number is pure Python regex, no DB access
    if not entry_service.validate_container_number(raw_input):
        await message.answer(
            get_text("invalid_container_format", lang),
            reply_markup=reply.get_cancel_keyboard(lang),
        )
        return

    # Normalize: remove spaces and uppercase (e.g., "MSKU 1234567" -> "MSKU1234567")
    container_number = entry_service.normalize_container_number(raw_input)

    # Check if container has active entry
    active_entry = await sync_to_async(entry_service.check_active_entry)(
        container_number
    )

    if not active_entry:
        await message.answer(
            get_text("container_not_found", lang, container_number=container_number),
            reply_markup=reply.get_cancel_keyboard(lang),
        )
        return

    # Extract entry info in synchronous context to avoid async database access issues
    entry_info = await sync_to_async(extract_entry_info)(active_entry)

    # Auto-set exit date to current time (skip manual entry)
    from django.utils import timezone

    exit_date = timezone.now()
    # Store ISO format to preserve timezone information
    exit_date_str = exit_date.isoformat()

    await state.update_data(
        entry_info=entry_info,
        container_number=container_number,
        exit_date=exit_date_str,
        photos=[],
    )
    await state.set_state(ExitForm.exit_transport_type)

    # Show entry info and ask for exit transport type
    # (skip exit date step - auto-set to current time)
    summary = await build_exit_summary(
        {"entry_info": entry_info, "exit_date": exit_date_str, "photos": []}, lang
    )
    await message.answer(
        f"{summary}\n\n{get_text('ask_exit_transport_type', lang)}",
        reply_markup=inline.get_exit_transport_type_keyboard(lang),
        parse_mode="HTML",
    )


@exit_router.callback_query(
    F.data.startswith("exit_transport_"), ExitForm.exit_transport_type
)
@require_manager_access
async def process_exit_transport_type(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """Process exit transport type selection"""
    lang = await get_user_language(state)

    transport_type = callback.data.replace("exit_transport_", "")

    # Validate callback data
    if transport_type not in VALID_TRANSPORT_TYPES:
        logger.warning(f"Invalid exit transport type callback data: {callback.data}")
        await callback.answer(get_text("invalid_selection", lang), show_alert=True)
        return

    await state.update_data(exit_transport_type=transport_type, exit_train_number="")

    if transport_type == "TRUCK":
        # TRUCK: Go to combined photos step with plate recognition
        await state.update_data(photos=[], show_photos=True)
        await state.set_state(ExitForm.photos)

        data = await state.get_data()
        summary = await build_exit_summary(data, lang)
        await callback.message.edit_text(
            f"{summary}\n\n{get_text('ask_all_photos_truck', lang)}",
            reply_markup=inline.get_exit_photo_keyboard(lang, has_photos=False),
            parse_mode="HTML",
        )
    else:
        # WAGON: Ask for transport number (manual entry)
        await state.set_state(ExitForm.exit_transport_number)
        await callback.message.delete()
        await callback.message.answer(
            get_text("ask_exit_transport_number", lang),
            reply_markup=reply.get_cancel_keyboard(lang),
        )

    await callback.answer()


@exit_router.message(ExitForm.exit_train_number)
@require_manager_access
async def process_exit_train_number(message: Message, state: FSMContext, user=None):
    """Process train number for exit"""
    lang = await get_user_language(state)

    if not message.text:
        await message.answer(get_text("error_exit_text", lang))
        return

    train_number = message.text.strip()
    await state.update_data(exit_train_number=train_number)
    await state.set_state(ExitForm.exit_transport_number)

    await message.answer(
        get_text("ask_exit_transport_number", lang),
        reply_markup=reply.get_cancel_keyboard(lang),
    )


@exit_router.message(ExitForm.exit_transport_number)
@require_manager_access
async def process_exit_transport_number(message: Message, state: FSMContext, user=None):
    """Process exit transport number"""
    lang = await get_user_language(state)

    if not message.text:
        await message.answer(get_text("error_exit_text", lang))
        return

    transport_number = message.text.strip()
    if not transport_number:
        await message.answer(get_text("error_exit_text", lang))
        return

    await state.update_data(exit_transport_number=transport_number)

    data = await state.get_data()
    transport_type = data.get("exit_transport_type")

    if transport_type == "TRUCK":
        # TRUCK: photos already taken during plate recognition step
        await state.update_data(show_photos=True)
        await state.set_state(ExitForm.confirmation)

        data = await state.get_data()
        summary = await build_exit_summary(data, lang)
        await message.answer(
            f"{get_text('exit_confirmation_header', lang)}\n\n{summary}\n\n{get_text('exit_confirmation_question', lang)}",
            reply_markup=inline.get_confirmation_keyboard(lang),
            parse_mode="HTML",
        )
    else:
        # WAGON: ask for exit photos
        await state.update_data(show_photos=True)
        await state.set_state(ExitForm.photos)

        data = await state.get_data()
        summary = await build_exit_summary(data, lang)
        await message.answer(
            f"{summary}\n\n{get_text('ask_exit_photos', lang)}",
            reply_markup=inline.get_photo_skip_keyboard(lang, has_photos=False),
            parse_mode="HTML",
        )


@exit_router.message(ExitForm.photos, F.photo)
@require_manager_access
async def process_exit_photo(
    message: Message, state: FSMContext, bot: Bot, user=None
):
    """Process exit photos with plate recognition for TRUCK transport type"""
    lang = await get_user_language(state)
    data = await state.get_data()
    transport_type = data.get("exit_transport_type")

    # For TRUCK: try plate recognition if no plate detected yet
    if transport_type == "TRUCK" and not data.get("detected_plate_number"):
        photo = message.photo[-1]  # Get highest resolution photo
        if plate_recognizer_service.api_key:
            try:
                file = await bot.get_file(photo.file_id)
                photo_io = await bot.download_file(file.file_path)
                photo_bytes = photo_io.read()
                result = await plate_recognizer_service.recognize_plate(photo_bytes)
                if result.success and result.confidence >= 0.50:
                    formatted_plate = plate_recognizer_service.format_plate_number(
                        result.plate_number
                    )
                    await state.update_data(
                        detected_plate_number=formatted_plate,
                        plate_confidence=result.confidence,
                    )
                    logger.info(
                        f"Exit: Detected plate {formatted_plate} "
                        f"(confidence: {result.confidence:.2%})"
                    )
            except Exception as e:
                logger.error(f"Error during plate recognition in exit flow: {e}")

    # Use exit-specific keyboard for photo upload
    await handle_photo_upload(
        message,
        state,
        summary_builder=build_exit_summary,
        keyboard_func=inline.get_exit_photo_keyboard,
    )


@exit_router.callback_query(F.data == "done_photos", ExitForm.photos)
@require_manager_access
async def done_exit_photos(callback: CallbackQuery, state: FSMContext, user=None):
    """Complete photo upload and move to confirmation"""
    user_id = callback.from_user.id
    lang = await get_user_language(state)

    # Cancel any pending photo confirmation task
    cancel_photo_confirmation_task(user_id)

    # Clear photo loading state
    await state.update_data(last_photo_timestamp=None, photo_loading_msg_id=None)
    await state.set_state(ExitForm.confirmation)

    data = await state.get_data()
    summary = await build_exit_summary(data, lang)

    await callback.message.edit_text(
        f"{get_text('exit_confirmation_header', lang)}\n\n{summary}\n\n{get_text('exit_confirmation_question', lang)}",
        reply_markup=inline.get_confirmation_keyboard(lang),
        parse_mode="HTML",
    )
    await callback.answer()


@exit_router.callback_query(F.data == "skip_photos", ExitForm.photos)
@require_manager_access
async def skip_exit_photos(callback: CallbackQuery, state: FSMContext, user=None):
    """Skip photos and go to confirmation"""
    user_id = callback.from_user.id
    lang = await get_user_language(state)

    # Cancel any pending photo confirmation task
    cancel_photo_confirmation_task(user_id)

    await state.update_data(
        photos=[],
        show_photos=True,
        last_photo_timestamp=None,
        photo_loading_msg_id=None,
    )
    await state.set_state(ExitForm.confirmation)

    data = await state.get_data()
    summary = await build_exit_summary(data, lang)

    await callback.message.edit_text(
        f"{get_text('exit_confirmation_header', lang)}\n\n{summary}\n\n{get_text('exit_confirmation_question', lang)}",
        reply_markup=inline.get_confirmation_keyboard(lang),
        parse_mode="HTML",
    )
    await callback.answer()


# ============ TRUCK EXIT FLOW HANDLERS (with plate recognition) ============


@exit_router.callback_query(F.data == "done_exit_photos", ExitForm.photos)
@require_manager_access
async def done_exit_truck_photos(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """Complete TRUCK photo upload - check for plate detection"""
    user_id = callback.from_user.id
    lang = await get_user_language(state)

    # Cancel any pending photo confirmation task
    cancel_photo_confirmation_task(user_id)

    # Clear photo loading state
    await state.update_data(last_photo_timestamp=None, photo_loading_msg_id=None)

    data = await state.get_data()
    detected_plate = data.get("detected_plate_number")
    confidence = data.get("plate_confidence", 0)

    if detected_plate:
        # Plate was detected - show confirmation
        await state.set_state(ExitForm.exit_transport_plate_photo)

        summary = await build_exit_summary(data, lang)
        plate_text = get_text(
            "plate_recognized",
            lang,
            plate=detected_plate,
            confidence=f"{confidence:.0%}",
        )
        await callback.message.edit_text(
            f"{summary}\n\n{plate_text}",
            reply_markup=inline.get_exit_plate_confirmation_keyboard(lang),
            parse_mode="HTML",
        )
    else:
        # No plate detected - ask for manual entry
        await state.set_state(ExitForm.exit_transport_number)

        await callback.message.delete()
        await callback.message.answer(
            get_text("ask_exit_transport_number", lang),
            reply_markup=reply.get_cancel_keyboard(lang),
        )

    await callback.answer()


@exit_router.callback_query(F.data == "skip_exit_photos", ExitForm.photos)
@require_manager_access
async def skip_exit_truck_photos(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """Skip TRUCK photos - ask for manual transport number entry"""
    user_id = callback.from_user.id
    lang = await get_user_language(state)

    # Cancel any pending photo confirmation task
    cancel_photo_confirmation_task(user_id)

    await state.update_data(
        photos=[],
        show_photos=True,
        last_photo_timestamp=None,
        photo_loading_msg_id=None,
        detected_plate_number=None,
        plate_confidence=None,
    )
    await state.set_state(ExitForm.exit_transport_number)

    await callback.message.delete()
    await callback.message.answer(
        get_text("ask_exit_transport_number", lang),
        reply_markup=reply.get_cancel_keyboard(lang),
    )
    await callback.answer()


@exit_router.callback_query(
    F.data == "confirm_exit_plate", ExitForm.exit_transport_plate_photo
)
@require_manager_access
async def confirm_exit_detected_plate(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """User confirmed detected plate number - proceed to destination"""
    lang = await get_user_language(state)
    data = await state.get_data()

    # Save detected plate as exit transport number
    detected_plate = data.get("detected_plate_number", "")
    await state.update_data(exit_transport_number=detected_plate, show_photos=True)
    await state.set_state(ExitForm.confirmation)

    # Show confirmation summary
    data = await state.get_data()
    summary = await build_exit_summary(data, lang)
    await callback.message.edit_text(
        f"{get_text('exit_confirmation_header', lang)}\n\n{summary}\n\n{get_text('exit_confirmation_question', lang)}",
        reply_markup=inline.get_confirmation_keyboard(lang),
        parse_mode="HTML",
    )
    await callback.answer()


@exit_router.callback_query(
    F.data == "edit_exit_plate", ExitForm.exit_transport_plate_photo
)
@require_manager_access
async def edit_exit_detected_plate(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """User wants to edit detected plate - ask for manual entry"""
    lang = await get_user_language(state)

    # Clear detected plate and go to manual entry
    await state.update_data(detected_plate_number=None, plate_confidence=None)
    await state.set_state(ExitForm.exit_transport_number)

    await callback.message.delete()
    await callback.message.answer(
        get_text("ask_exit_transport_number", lang),
        reply_markup=reply.get_cancel_keyboard(lang),
    )
    await callback.answer()


@exit_router.callback_query(
    F.data == "back_to_exit_transport_type", ExitForm.photos
)
@require_manager_access
async def back_to_exit_transport_type(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """Go back from photos to transport type selection"""
    lang = await get_user_language(state)
    user_id = callback.from_user.id

    # Cancel any pending photo confirmation task
    cancel_photo_confirmation_task(user_id)

    # Clear photo-related state
    await state.update_data(
        photos=[],
        exit_transport_type=None,
        show_photos=False,
        last_photo_timestamp=None,
        photo_loading_msg_id=None,
        detected_plate_number=None,
        plate_confidence=None,
    )
    await state.set_state(ExitForm.exit_transport_type)

    data = await state.get_data()
    summary = await build_exit_summary(data, lang)
    await callback.message.edit_text(
        f"{summary}\n\n{get_text('ask_exit_transport_type', lang)}",
        reply_markup=inline.get_exit_transport_type_keyboard(lang),
        parse_mode="HTML",
    )
    await callback.answer()


@exit_router.callback_query(
    F.data == "back_to_exit_photos", ExitForm.exit_transport_plate_photo
)
@require_manager_access
async def back_to_exit_photos(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """Go back from plate confirmation to photos"""
    lang = await get_user_language(state)

    # Clear detected plate and go back to photos
    await state.update_data(detected_plate_number=None, plate_confidence=None)
    await state.set_state(ExitForm.photos)

    data = await state.get_data()
    photos = data.get("photos", [])
    summary = await build_exit_summary(data, lang)

    has_photos = len(photos) > 0
    await callback.message.edit_text(
        f"{summary}\n\n{get_text('ask_all_photos_truck', lang)}",
        reply_markup=inline.get_exit_photo_keyboard(lang, has_photos=has_photos),
        parse_mode="HTML",
    )
    await callback.answer()


@exit_router.callback_query(F.data == "confirm_yes", ExitForm.confirmation)
@require_manager_access
async def confirm_exit(callback: CallbackQuery, state: FSMContext, user=None):
    """Confirm and create exit record"""
    lang = await get_user_language(state)

    data = await state.get_data()

    try:
        from datetime import datetime as dt

        # Prepare exit data
        exit_date_str = data.get("exit_date", "")
        # Parse ISO format datetime (preserves timezone from when it was created)
        exit_date = dt.fromisoformat(exit_date_str)

        exit_data = {
            "exit_date": exit_date,
            "exit_transport_type": data.get("exit_transport_type"),
            "exit_transport_number": data.get("exit_transport_number", ""),
            "exit_train_number": data.get("exit_train_number", ""),
        }

        # Download photos from Telegram using shared utility
        # Normalize photo data (handle both old dict format and new file_id format)
        raw_photos = data.get("photos", [])
        photo_file_ids = [
            p.get("file_id") if isinstance(p, dict) else p for p in raw_photos
        ]
        photos = await download_photos_from_telegram(callback.bot, photo_file_ids)
        if photos:
            logger.info(f"Downloaded {len(photos)} exit photos from Telegram")

        # Get crane operations if any
        crane_ops = data.get("crane_operations")

        # Call service to update exit
        entry_id = data.get("entry_info", {}).get("entry_id")
        updated_entry = await sync_to_async(entry_service.update_exit)(
            entry_id=entry_id,
            exit_data=exit_data,
            photos=photos if photos else None,  # Pass None if no photos
            crane_operations=crane_ops,
            manager=user,  # Pass user who recorded this exit
        )

        # Log activity
        await sync_to_async(activity_log_service.log_container_exit_recorded)(
            user=user,
            telegram_user_id=callback.from_user.id,
            container_entry=updated_entry,
        )

        # Send notification to container owner's Telegram group
        await owner_notification_service.notify_container_exit(
            bot=callback.bot,
            entry=updated_entry,
            manager=user,
            photo_file_ids=photo_file_ids if photo_file_ids else None,
        )

        # Extract data in synchronous context to avoid async database access
        def get_exit_display_info(entry):
            return {
                "container": format_container_number(entry.container.container_number),
                "exit_date": entry.exit_date.strftime("%Y-%m-%d %H:%M"),
                "dwell_time": entry.dwell_time_days or 0,
            }

        display_info = await sync_to_async(get_exit_display_info)(updated_entry)

        await callback.message.edit_text(
            get_text(
                "exit_created",
                lang,
                container=display_info["container"],
                exit_date=display_info["exit_date"],
                dwell_time=display_info["dwell_time"],
            )
        )

        # Clear state and show main menu
        lang = await get_user_language(state)
        await state.clear()
        await state.update_data(language=lang)

        await callback.message.answer(
            get_text("welcome", lang), reply_markup=reply.get_main_keyboard(lang)
        )

    except DuplicateEntryError as e:
        logger.warning(f"Duplicate entry error on exit: {e.message}")
        await callback.message.edit_text(
            get_text(
                "duplicate_entry",
                lang,
                container_number=data.get("container_number", ""),
            )
        )
        await state.clear()
        await state.update_data(language=lang)
        await callback.message.answer(
            get_text("choose_action", lang), reply_markup=reply.get_main_keyboard(lang)
        )
    except ContainerNotFoundError as e:
        logger.warning(f"Container not found on exit: {e.message}")
        await callback.message.edit_text(
            get_text(
                "container_not_found",
                lang,
                container_number=data.get("container_number", ""),
            )
        )
        await state.clear()
        await state.update_data(language=lang)
        await callback.message.answer(
            get_text("choose_action", lang), reply_markup=reply.get_main_keyboard(lang)
        )
    except ValidationError as e:
        logger.warning(f"Validation error on exit: {e!s}")
        error_msg = str(e)[:100]  # Truncate long error messages
        await callback.message.edit_text(
            get_text("error_exit_creating", lang, error=error_msg)
        )
        await state.clear()
        await state.update_data(language=lang)
        await callback.message.answer(
            get_text("choose_action", lang), reply_markup=reply.get_main_keyboard(lang)
        )
    except BusinessLogicError as e:
        logger.warning(f"Business logic error on exit: {e.message}")
        await callback.message.edit_text(
            get_text("error_exit_creating", lang, error=e.message)
        )
        await state.clear()
        await state.update_data(language=lang)
        await callback.message.answer(
            get_text("choose_action", lang), reply_markup=reply.get_main_keyboard(lang)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating exit: {e!s}", exc_info=True)
        await callback.message.edit_text(
            get_text(
                "error_exit_creating", lang, error=get_text("error_unexpected", lang)
            )
        )
        await state.clear()
        await state.update_data(language=lang)
        await callback.message.answer(
            get_text("choose_action", lang), reply_markup=reply.get_main_keyboard(lang)
        )

    await callback.answer()


@exit_router.callback_query(F.data == "confirm_no", ExitForm.confirmation)
@require_manager_access
async def cancel_exit(callback: CallbackQuery, state: FSMContext, user=None):
    """Cancel exit process"""
    lang = await get_user_language(state)

    await state.clear()
    await state.update_data(language=lang)

    # edit_text can only use InlineKeyboardMarkup, so remove it first
    await callback.message.edit_text(
        get_text("exit_cancelled", lang), reply_markup=None
    )
    # Then send main keyboard in a new message
    await callback.message.answer(
        get_text("choose_action", lang), reply_markup=reply.get_main_keyboard(lang)
    )
    await callback.answer()
