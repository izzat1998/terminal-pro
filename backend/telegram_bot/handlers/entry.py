import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from asgiref.sync import sync_to_async

from apps.core.services import ActivityLogService
from apps.terminal_operations.services.gate_matching_service import GateMatchingService
from telegram_bot.handlers.photos import (
    cancel_photo_confirmation_task,
    download_photos_from_telegram,
    handle_photo_upload,
)
from telegram_bot.keyboards.inline import (
    get_confirmation_keyboard,
    get_container_owner_keyboard,
    get_iso_type_keyboard,
    get_photo_skip_keyboard,
    get_plate_confirmation_keyboard,
    get_status_keyboard,
    get_transport_type_keyboard,
)
from telegram_bot.keyboards.reply import get_cancel_keyboard, get_main_keyboard
from telegram_bot.middleware import require_manager_access
from telegram_bot.services.entry_service import BotEntryService
from telegram_bot.services.owner_notification_service import OwnerNotificationService
from telegram_bot.services.plate_recognizer_service import PlateRecognizerService
from telegram_bot.states.entry import EntryForm
from telegram_bot.translations import (
    get_status_display,
    get_text,
    get_transport_display,
)
from telegram_bot.utils import format_container_number


# Configure logger
logger = logging.getLogger(__name__)

# Valid callback data values for security validation
VALID_ISO_TYPES = {
    "22G1",  # 20ft standard
    "25G1",  # 20ft high cube
    "42G1",  # 40ft standard
    "45G1",  # 40ft high cube
}
VALID_STATUSES = {"LADEN", "EMPTY"}
VALID_TRANSPORT_TYPES = {"TRUCK", "WAGON"}

router = Router()
entry_service = BotEntryService()
plate_recognizer_service = PlateRecognizerService()
gate_matching_service = GateMatchingService()
activity_log_service = ActivityLogService()
owner_notification_service = OwnerNotificationService()


async def get_user_language(state: FSMContext) -> str:
    """Get user's selected language from state, default to Russian"""
    data = await state.get_data()
    return data.get("language", "ru")


async def check_preorder_match(
    plate_number: str, state: FSMContext, message: Message, lang: str
) -> dict:
    """
    Check if there's a matching pre-order for the given plate number.
    If found, stores the preorder_id in state and sends a notification.
    Returns the match result dict.
    """
    try:
        match_result = await sync_to_async(gate_matching_service.check_preorder_match)(
            plate_number
        )

        if match_result.get("matched"):
            # Store the matched preorder ID in state for later use
            await state.update_data(matched_preorder_id=match_result["preorder_id"])

            # Get operation type display text
            operation_type = match_result.get("operation_type", "")
            if operation_type == "LOAD":
                operation_display = get_text("preorder_match_operation_load", lang)
            else:
                operation_display = get_text("preorder_match_operation_unload", lang)

            # Send notification to security
            await message.answer(
                get_text(
                    "preorder_match_found",
                    lang,
                    customer_name=match_result.get("customer_name", "Unknown"),
                    plate_number=match_result.get("plate_number", plate_number),
                    operation_type=operation_display,
                ),
                parse_mode="HTML",
            )
            logger.info(
                f"Pre-order match found for plate {plate_number}: order #{match_result['preorder_id']}"
            )

        return match_result

    except Exception as e:
        logger.error(f"Error checking pre-order match: {e}")
        return {"matched": False}


async def build_summary(data: dict, lang: str) -> str:
    """Build progressive summary of entered data with HTML escaping for user inputs"""
    summary_parts = []

    if "container_number" in data:
        # Container numbers are standardized format, but escape for safety
        # Format as PREFIX | POSTFIX for better readability
        formatted_number = format_container_number(data['container_number'])
        summary_parts.append(
            f"✅ {get_text('summary_container', lang)}: {escape(formatted_number)}"
        )

    if "container_iso_type" in data:
        # ISO types are standardized, but escape for safety
        summary_parts.append(
            f"✅ {get_text('summary_iso', lang)}: {escape(data['container_iso_type'])}"
        )

    if "container_owner_id" in data:
        # Owner was selected - MUST escape user data
        owner_name = data.get("container_owner_name", "")
        summary_parts.append(
            f"✅ {get_text('summary_owner', lang)}: {escape(owner_name)}"
        )
    elif "container_owner_skipped" in data:
        # Owner was skipped
        summary_parts.append(
            f"✅ {get_text('summary_owner', lang)}: {get_text('owner_not_specified', lang)}"
        )

    if "status" in data:
        # Status display comes from translations - no need to escape
        status_display = get_status_display(data["status"], lang)
        summary_parts.append(
            f"✅ {get_text('summary_status', lang)}: {status_display}"
        )

    if "transport_type" in data:
        # Transport display comes from translations - no need to escape
        transport_display = get_transport_display(data["transport_type"], lang)
        summary_parts.append(
            f"✅ {get_text('summary_transport', lang)}: {transport_display}"
        )

    if "transport_number" in data:
        # Transport number is user-provided - MUST escape
        summary_parts.append(
            f"✅ {get_text('summary_transport_num', lang)}: {escape(data['transport_number'])}"
        )

    return "\n".join(summary_parts)


@router.message(Command("create"))
@require_manager_access
async def cmd_create_entry(message: Message, state: FSMContext, user=None):
    """Start container entry creation flow (requires manager access)"""
    lang = await get_user_language(state)
    # Clear state but preserve language
    await state.clear()
    await state.update_data(language=lang)
    await state.set_state(EntryForm.container_number)
    await message.answer(
        get_text("start_entry", lang), reply_markup=get_cancel_keyboard(lang)
    )


@router.message(EntryForm.container_number)
@require_manager_access
async def process_container_number(message: Message, state: FSMContext, user=None):
    """Process container number input"""
    lang = await get_user_language(state)

    if not message.text:
        await message.answer(
            get_text("error_text_only", lang), reply_markup=get_cancel_keyboard(lang)
        )
        return

    raw_input = message.text.strip()

    # Validate format (accepts with or without spaces)
    if not entry_service.validate_container_number(raw_input):
        await message.answer(
            get_text("invalid_container_format", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    # Normalize: remove spaces and uppercase (e.g., "MSKU 1234567" -> "MSKU1234567")
    container_number = entry_service.normalize_container_number(raw_input)

    # Check if container is already active on terminal (no exit date)
    active_entry = await sync_to_async(entry_service.check_active_entry)(
        container_number
    )
    if active_entry:
        # Format entry date
        entry_date = active_entry.entry_time.strftime("%d.%m.%Y %H:%M")
        # Get localized transport type
        transport_display = get_transport_display(active_entry.transport_type, lang)

        # Send error message with existing entry details
        await message.answer(
            get_text(
                "container_already_active",
                lang,
                container_number=container_number,
                entry_date=entry_date,
                transport_type=transport_display,
            )
        )
        return

    await state.update_data(container_number=container_number)
    await state.set_state(EntryForm.container_iso_type)

    # Build summary and show ISO type selection
    data = await state.get_data()
    summary = await build_summary(data, lang)

    await message.answer(
        f"{summary}\n\n{get_text('ask_iso_type', lang)}",
        reply_markup=get_iso_type_keyboard(lang),
    )


@router.callback_query(F.data.startswith("iso_"), EntryForm.container_iso_type)
@require_manager_access
async def process_iso_type(callback: CallbackQuery, state: FSMContext, user=None):
    """Process ISO type selection"""
    lang = await get_user_language(state)
    iso_type = callback.data.replace("iso_", "")

    # Validate callback data
    if iso_type not in VALID_ISO_TYPES:
        logger.warning(f"Invalid ISO type callback data: {callback.data}")
        await callback.answer(get_text("invalid_selection", lang), show_alert=True)
        return

    await state.update_data(container_iso_type=iso_type)
    await state.set_state(EntryForm.container_owner)

    # Build summary and show container owner selection
    data = await state.get_data()
    summary = await build_summary(data, lang)

    # Get keyboard and check if owners are available (now async)
    keyboard, has_owners = await get_container_owner_keyboard(lang)

    # Build message based on whether owners are available
    if has_owners:
        message_text = f"{summary}\n\n{get_text('ask_owner', lang)}"
    else:
        message_text = f"{summary}\n\n{get_text('no_owners_available', lang)}"

    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("owner_"), EntryForm.container_owner)
@require_manager_access
async def process_container_owner(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """Process container owner selection"""
    lang = await get_user_language(state)

    if callback.data == "owner_skip":
        # User skipped owner selection
        await state.update_data(container_owner_skipped=True)
    else:
        # User selected an owner
        owner_id = int(callback.data.replace("owner_", ""))

        # Fetch owner name from database
        from apps.terminal_operations.models import ContainerOwner

        try:
            owner = await sync_to_async(ContainerOwner.objects.get)(id=owner_id)
            await state.update_data(
                container_owner_id=owner_id, container_owner_name=owner.name
            )
        except ContainerOwner.DoesNotExist:
            # Owner was deleted between showing keyboard and selection
            # Show error alert and re-display the owner selection keyboard
            await callback.answer(get_text("owner_not_found", lang), show_alert=True)

            # Refresh the keyboard with current owners
            data = await state.get_data()
            summary = await build_summary(data, lang)
            keyboard, has_owners = await get_container_owner_keyboard(lang)

            if has_owners:
                message_text = f"{summary}\n\n{get_text('ask_owner', lang)}"
            else:
                message_text = f"{summary}\n\n{get_text('no_owners_available', lang)}"

            try:
                await callback.message.edit_text(message_text, reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Failed to refresh owner keyboard: {e}")
            return

    await state.set_state(EntryForm.status)

    # Build summary and show status selection
    data = await state.get_data()
    summary = await build_summary(data, lang)

    await callback.message.edit_text(
        f"{summary}\n\n{get_text('ask_status', lang)}",
        reply_markup=get_status_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("status_"), EntryForm.status)
@require_manager_access
async def process_status(callback: CallbackQuery, state: FSMContext, user=None):
    """Process status selection"""
    lang = await get_user_language(state)
    status = callback.data.replace("status_", "")

    # Validate callback data
    if status not in VALID_STATUSES:
        logger.warning(f"Invalid status callback data: {callback.data}")
        await callback.answer(get_text("invalid_selection", lang), show_alert=True)
        return

    await state.update_data(status=status)

    # If EMPTY status: auto-select TRUCK and go to combined photos step
    if status == "EMPTY":
        await state.update_data(transport_type="TRUCK")
        await state.set_state(EntryForm.photos)

        data = await state.get_data()
        summary = await build_summary(data, lang)

        await callback.message.edit_text(
            f"{summary}\n\n{get_text('ask_all_photos_truck', lang)}",
            reply_markup=get_photo_skip_keyboard(lang, has_photos=False),
        )
    else:
        # LADEN status: ask for transport type
        await state.set_state(EntryForm.transport_type)

        data = await state.get_data()
        summary = await build_summary(data, lang)

        await callback.message.edit_text(
            f"{summary}\n\n{get_text('ask_transport_type', lang)}",
            reply_markup=get_transport_type_keyboard(lang),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("transport_"), EntryForm.transport_type)
@require_manager_access
async def process_transport_type(callback: CallbackQuery, state: FSMContext, user=None):
    """Process transport type selection"""
    lang = await get_user_language(state)
    transport_type = callback.data.replace("transport_", "")

    # Validate callback data
    if transport_type not in VALID_TRANSPORT_TYPES:
        logger.warning(f"Invalid transport type callback data: {callback.data}")
        await callback.answer(get_text("invalid_selection", lang), show_alert=True)
        return

    await state.update_data(transport_type=transport_type)

    # Build summary
    data = await state.get_data()
    summary = await build_summary(data, lang)

    # If TRUCK: go to combined photos step (will try plate recognition on each photo)
    if transport_type == "TRUCK":
        await state.set_state(EntryForm.photos)
        await callback.message.edit_text(
            f"{summary}\n\n{get_text('ask_all_photos_truck', lang)}",
            reply_markup=get_photo_skip_keyboard(lang, has_photos=False),
        )
    else:
        # WAGON: ask for manual input
        await state.set_state(EntryForm.transport_number)
        await callback.message.edit_text(
            f"{summary}\n\n{get_text('ask_transport_number', lang)}"
        )
    await callback.answer()


@router.message(EntryForm.transport_plate_photo, F.photo)
@require_manager_access
async def process_truck_plate_photo(
    message: Message, state: FSMContext, bot: Bot, user=None
):
    """Process truck plate photo: save photo and recognize plate number"""
    lang = await get_user_language(state)
    photo = message.photo[-1]  # Get highest resolution

    # Save truck photo file_id to state (will be included in entry photos)
    await state.update_data(truck_photo_file_id=photo.file_id)

    # Check if plate recognizer API is configured
    if not plate_recognizer_service.api_key:
        # No API: save photo and ask for manual plate entry
        await state.set_state(EntryForm.transport_number)
        data = await state.get_data()
        summary = await build_summary(data, lang)
        await message.answer(
            f"{summary}\n\n{get_text('plate_recognition_failed', lang)}"
        )
        return

    # Show processing message
    processing_msg = await message.answer(get_text("plate_recognizing", lang))

    # Download photo from Telegram
    try:
        file = await bot.get_file(photo.file_id)
        photo_io = await bot.download_file(file.file_path)  # Returns BytesIO
        photo_bytes = photo_io.read()

        # Recognize plate
        result = await plate_recognizer_service.recognize_plate(photo_bytes)

        # Delete processing message
        await processing_msg.delete()

        # Check if recognition was successful
        if (
            result.success and result.confidence >= 0.50
        ):  # 50% confidence threshold (lenient)
            # Success: Show detected plate with confidence
            formatted_plate = plate_recognizer_service.format_plate_number(
                result.plate_number
            )
            await state.update_data(
                detected_plate_number=formatted_plate,
                plate_confidence=result.confidence,
            )

            # Build summary
            data = await state.get_data()
            summary = await build_summary(data, lang)

            # Show result with confirmation keyboard (bound confidence 0-100)
            confidence_percent = max(0, min(100, int(result.confidence * 100)))
            await message.answer(
                f"{summary}\n\n{get_text('plate_recognized', lang, plate=formatted_plate, confidence=confidence_percent)}",
                reply_markup=get_plate_confirmation_keyboard(lang),
                parse_mode="HTML",
            )
        else:
            # Failed: Fall back to manual entry (photo already saved)
            await state.set_state(EntryForm.transport_number)

            data = await state.get_data()
            summary = await build_summary(data, lang)

            await message.answer(
                f"{summary}\n\n{get_text('plate_recognition_failed', lang)}"
            )

    except Exception as e:
        logger.error(f"Error processing plate photo: {e!s}", exc_info=True)

        # Delete processing message if still exists
        try:
            await processing_msg.delete()
        except Exception as e:
            logger.debug(f"Could not delete processing message: {e}")

        # Fallback to manual entry on any error (photo already saved)
        await state.set_state(EntryForm.transport_number)

        data = await state.get_data()
        summary = await build_summary(data, lang)

        await message.answer(
            f"{summary}\n\n{get_text('plate_recognition_failed', lang)}"
        )


@router.message(EntryForm.transport_plate_photo)
@require_manager_access
async def process_truck_plate_photo_invalid(
    message: Message, state: FSMContext, user=None
):
    """Handle non-photo input in plate photo state"""
    lang = await get_user_language(state)
    await message.answer(get_text("ask_truck_plate_photo", lang))


@router.callback_query(F.data == "confirm_plate", EntryForm.transport_plate_photo)
@require_manager_access
async def confirm_detected_plate(callback: CallbackQuery, state: FSMContext, user=None):
    """User confirmed detected plate number - go to confirmation (photos already collected)"""
    lang = await get_user_language(state)
    data = await state.get_data()

    detected_plate = data.get("detected_plate_number", "")

    # Set as transport number
    await state.update_data(transport_number=detected_plate)

    # Check for pre-order match
    await check_preorder_match(detected_plate, state, callback.message, lang)

    # Photos already collected - go directly to confirmation
    await show_confirmation(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "edit_plate", EntryForm.transport_plate_photo)
@require_manager_access
async def edit_detected_plate(callback: CallbackQuery, state: FSMContext, user=None):
    """User wants to manually enter/edit plate number"""
    lang = await get_user_language(state)

    await state.set_state(EntryForm.transport_number)

    data = await state.get_data()
    summary = await build_summary(data, lang)

    await callback.message.edit_text(
        f"{summary}\n\n{get_text('ask_transport_number', lang)}"
    )
    await callback.answer()


@router.message(EntryForm.transport_number)
@require_manager_access
async def process_transport_number(message: Message, state: FSMContext, user=None):
    """Process transport number input"""
    lang = await get_user_language(state)

    if not message.text:
        await message.answer(get_text("error_transport_text", lang))
        return

    transport_number = message.text.strip()

    # Validate transport number is not empty after stripping
    if not transport_number:
        await message.answer(get_text("error_transport_empty", lang))
        return

    await state.update_data(transport_number=transport_number)

    # Check for pre-order match (only for trucks - plate number matching)
    data = await state.get_data()
    if data.get("transport_type") == "TRUCK":
        await check_preorder_match(transport_number, state, message, lang)
        # For TRUCK: photos already collected, go to confirmation
        await show_confirmation(message, state)
    else:
        # For WAGON: ask for photos
        await state.set_state(EntryForm.photos)

        # Build summary and ask for photos (refresh data after potential preorder update)
        data = await state.get_data()
        summary = await build_summary(data, lang)

        # No photos yet, show both Skip and Done buttons
        await message.answer(
            f"{summary}\n\n{get_text('ask_photos', lang)}",
            reply_markup=get_photo_skip_keyboard(lang, has_photos=False),
        )


@router.message(EntryForm.photos, F.photo)
@require_manager_access
async def process_photo(message: Message, state: FSMContext, bot: Bot, user=None):
    """Process photo upload with plate recognition for TRUCK transport type"""
    lang = await get_user_language(state)
    data = await state.get_data()
    transport_type = data.get("transport_type")

    # For TRUCK: try plate recognition if no plate detected yet
    if transport_type == "TRUCK" and not data.get("detected_plate_number"):
        photo = message.photo[-1]

        # Try plate recognition only if API is configured
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
                    logger.info(f"Plate recognized from photo: {formatted_plate} ({result.confidence*100:.0f}%)")
            except Exception as e:
                logger.error(f"Error during plate recognition: {e}")
                # Continue without plate - will ask for manual entry later

    # Delegate to shared photo handling (collects photos, shows loading, etc.)
    await handle_photo_upload(message, state, summary_builder=build_summary)


@router.callback_query(F.data == "skip_photos", EntryForm.photos)
@require_manager_access
async def skip_photos(callback: CallbackQuery, state: FSMContext, user=None):
    """Skip photo upload - handle plate entry for TRUCK"""
    user_id = callback.from_user.id
    lang = await get_user_language(state)
    data = await state.get_data()
    loading_msg_id = data.get("photo_loading_msg_id")
    transport_type = data.get("transport_type")

    # Cancel any pending photo confirmation task
    cancel_photo_confirmation_task(user_id)

    await state.update_data(
        photos=[], last_photo_timestamp=None, photo_loading_msg_id=None
    )

    # For TRUCK: need to ask for manual plate entry (no photos = no plate recognized)
    if transport_type == "TRUCK":
        await state.set_state(EntryForm.transport_number)
        summary = await build_summary(data, lang)

        msg_text = f"{summary}\n\n{get_text('ask_transport_number', lang)}"

        if loading_msg_id:
            try:
                await callback.message.bot.edit_message_text(
                    chat_id=callback.message.chat.id,
                    message_id=loading_msg_id,
                    text=msg_text,
                )
            except Exception as e:
                logger.error(f"Failed to edit message: {e}")
                await callback.message.answer(msg_text)
        else:
            await callback.message.answer(msg_text)
    else:
        # WAGON or other: go directly to confirmation
        await show_confirmation(callback.message, state, edit_message_id=loading_msg_id)

    await callback.answer()


@router.callback_query(F.data == "done_photos", EntryForm.photos)
@require_manager_access
async def done_photos(callback: CallbackQuery, state: FSMContext, user=None):
    """Finish photo upload - handle plate confirmation for TRUCK"""
    user_id = callback.from_user.id
    lang = await get_user_language(state)
    data = await state.get_data()
    loading_msg_id = data.get("photo_loading_msg_id")
    transport_type = data.get("transport_type")

    # Cancel any pending photo confirmation task
    cancel_photo_confirmation_task(user_id)

    if "photos" not in data:
        await state.update_data(photos=[])

    # Clear timestamp and loading message to prevent pending confirmation
    await state.update_data(last_photo_timestamp=None, photo_loading_msg_id=None)

    # For TRUCK: need to handle plate number
    if transport_type == "TRUCK":
        detected_plate = data.get("detected_plate_number")

        if detected_plate:
            # Plate was detected - show confirmation
            await state.set_state(EntryForm.transport_plate_photo)
            confidence = data.get("plate_confidence", 0)
            confidence_percent = max(0, min(100, int(confidence * 100)))

            summary = await build_summary(data, lang)

            msg_text = f"{summary}\n\n{get_text('plate_recognized', lang, plate=detected_plate, confidence=confidence_percent)}"

            if loading_msg_id:
                try:
                    await callback.message.bot.edit_message_text(
                        chat_id=callback.message.chat.id,
                        message_id=loading_msg_id,
                        text=msg_text,
                        reply_markup=get_plate_confirmation_keyboard(lang),
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.error(f"Failed to edit message: {e}")
                    await callback.message.answer(
                        msg_text,
                        reply_markup=get_plate_confirmation_keyboard(lang),
                        parse_mode="HTML",
                    )
            else:
                await callback.message.answer(
                    msg_text,
                    reply_markup=get_plate_confirmation_keyboard(lang),
                    parse_mode="HTML",
                )
        else:
            # No plate detected - ask for manual entry
            await state.set_state(EntryForm.transport_number)
            summary = await build_summary(data, lang)

            msg_text = f"{summary}\n\n{get_text('plate_recognition_failed', lang)}"

            if loading_msg_id:
                try:
                    await callback.message.bot.edit_message_text(
                        chat_id=callback.message.chat.id,
                        message_id=loading_msg_id,
                        text=msg_text,
                    )
                except Exception as e:
                    logger.error(f"Failed to edit message: {e}")
                    await callback.message.answer(msg_text)
            else:
                await callback.message.answer(msg_text)
    else:
        # WAGON or other: go directly to confirmation
        await show_confirmation(callback.message, state, edit_message_id=loading_msg_id)

    await callback.answer()


async def show_confirmation(
    message: Message, state: FSMContext, edit_message_id: int = None
):
    """Show confirmation with all collected data"""
    data = await state.get_data()
    lang = data.get("language", "ru")
    await state.set_state(EntryForm.confirmation)

    # Build summary with checkmarks
    summary = await build_summary(data, lang)

    # Count all photos
    photo_count = len(data.get("photos", []))

    # Show better text when no photos
    if photo_count == 0:
        photo_text = (
            f"✅ {get_text('summary_photos', lang)}: {get_text('no_photos', lang)}"
        )
    else:
        photo_text = f"✅ {get_text('summary_photos', lang)}: {photo_count}"

    confirmation_msg = (
        f"{get_text('confirmation_header', lang)}\n\n"
        f"{summary}\n"
        f"{photo_text}\n\n"
        f"{get_text('confirmation_question', lang)}"
    )

    # Edit existing message if message_id provided, otherwise send new
    if edit_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=edit_message_id,
                text=confirmation_msg,
                reply_markup=get_confirmation_keyboard(lang),
            )
        except Exception as e:
            logger.error(f"Failed to edit confirmation message: {e}")
            # If edit fails, send new message
            await message.answer(
                confirmation_msg, reply_markup=get_confirmation_keyboard(lang)
            )
    else:
        # No message to edit, send new
        await message.answer(
            confirmation_msg, reply_markup=get_confirmation_keyboard(lang)
        )


@router.callback_query(F.data == "confirm_yes", EntryForm.confirmation)
@require_manager_access
async def confirm_entry(
    callback: CallbackQuery, state: FSMContext, bot: Bot, user=None
):
    """Create entry after confirmation"""
    data = await state.get_data()
    lang = data.get("language", "ru")

    # Validate all required fields exist before processing
    required_fields = [
        "container_number",
        "container_iso_type",
        "status",
        "transport_type",
        "transport_number",
    ]

    for field in required_fields:
        if field not in data:
            logger.error(
                f"Missing required field: {field} for user {user.id if user else 'unknown'}"
            )
            await state.clear()
            await state.update_data(language=lang)
            await callback.message.edit_text(
                get_text(
                    "error_creating", lang, error=get_text("error_missing_data", lang)
                ),
                reply_markup=None,
            )
            await callback.message.answer(
                get_text("choose_action", lang), reply_markup=get_main_keyboard(lang)
            )
            await callback.answer()
            return

    try:
        # Get all photo file_ids
        all_photo_file_ids = data.get("photos", [])

        # Download all photos from Telegram using shared utility
        photos = await download_photos_from_telegram(bot, all_photo_file_ids)

        # Create entry via service (wrap Django ORM in sync_to_async)
        # Get container owner ID if selected (None if skipped)
        container_owner_id = data.get("container_owner_id", None)

        entry = await sync_to_async(entry_service.create_entry)(
            container_number=data["container_number"],
            container_iso_type=data["container_iso_type"],
            status=data["status"],  # Already in English (LADEN/EMPTY)
            transport_type=data["transport_type"],  # Already in English (TRUCK/WAGON)
            transport_number=data["transport_number"],
            photos=photos if photos else None,
            container_owner_id=container_owner_id,
            manager=user,  # Pass user (CustomUser) who created this entry
        )

        # Log activity
        activity_log = await sync_to_async(activity_log_service.log_container_entry_created)(
            user=user,
            telegram_user_id=callback.from_user.id,
            container_entry=entry,
        )

        # Send notification to container owner's Telegram group
        notification_result = await owner_notification_service.notify_container_entry(
            bot=bot,
            entry=entry,
            manager=user,
            photo_file_ids=all_photo_file_ids if all_photo_file_ids else None,
        )

        # Update activity log with notification result
        await sync_to_async(activity_log_service.update_group_notification_status)(
            activity_log_id=activity_log.id,
            status=notification_result.status,
            error_message=notification_result.error_message,
        )

        # Complete pre-order match if one was found
        matched_preorder_id = data.get("matched_preorder_id")
        if matched_preorder_id:
            try:
                await sync_to_async(gate_matching_service.complete_match)(
                    preorder_id=matched_preorder_id, entry=entry
                )
                logger.info(
                    f"Pre-order #{matched_preorder_id} matched to entry #{entry.id}"
                )
                # Show additional success message for pre-order match
                await callback.message.answer(
                    get_text(
                        "preorder_matched_success", lang, order_id=matched_preorder_id
                    )
                )
            except Exception as match_error:
                logger.error(f"Failed to complete pre-order match: {match_error}")
                # Don't fail the entry creation if match fails

        # Extract display data in sync context
        def get_entry_display_data(e):
            return {
                "id": e.id,
                "container_number": e.container.container_number,
                "entry_time": e.entry_time.strftime("%d.%m.%Y %H:%M"),
            }

        display_data = await sync_to_async(get_entry_display_data)(entry)

        await callback.message.edit_text(
            get_text(
                "entry_created",
                lang,
                id=display_data["id"],
                container=format_container_number(display_data["container_number"]),
                time=display_data["entry_time"],
            )
        )
        # Show main keyboard after success
        await callback.message.answer(
            get_text("choose_action", lang), reply_markup=get_main_keyboard(lang)
        )

    except Exception as e:
        from apps.core.exceptions import DuplicateEntryError

        logger.error(f"Error creating entry: {e!s}", exc_info=True)

        if isinstance(e, DuplicateEntryError):
            await callback.message.edit_text(
                get_text(
                    "duplicate_entry", lang, container_number=data["container_number"]
                )
            )
        else:
            error_msg = str(e)
            # Truncate very long error messages
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."

            await callback.message.edit_text(
                get_text("error_creating", lang, error=error_msg)
            )
        # Show main keyboard after error
        await callback.message.answer(
            get_text("choose_action", lang), reply_markup=get_main_keyboard(lang)
        )

    # Cleanup: preserve language and cancel pending tasks
    user_id = callback.from_user.id
    cancel_photo_confirmation_task(user_id)

    await state.clear()
    await state.update_data(language=lang)
    await callback.answer()


@router.callback_query(F.data == "confirm_no", EntryForm.confirmation)
@require_manager_access
async def cancel_entry(callback: CallbackQuery, state: FSMContext, user=None):
    """Cancel entry creation"""
    data = await state.get_data()
    lang = data.get("language", "ru")
    user_id = callback.from_user.id

    # Cancel any pending tasks
    cancel_photo_confirmation_task(user_id)

    await state.clear()
    await state.update_data(language=lang)
    await callback.message.edit_text(get_text("entry_cancelled", lang))
    # Show main keyboard after cancellation
    await callback.message.answer(
        get_text("choose_action", lang), reply_markup=get_main_keyboard(lang)
    )
    await callback.answer()


# ============== BACK NAVIGATION HANDLERS ==============


@router.callback_query(F.data == "back_to_container_number", EntryForm.container_iso_type)
@require_manager_access
async def back_to_container_number(callback: CallbackQuery, state: FSMContext, user=None):
    """Go back to container number input"""
    lang = await get_user_language(state)

    # Clear container data - get current data and remove keys
    data = await state.get_data()
    data.pop("container_number", None)
    data.pop("container_iso_type", None)
    await state.set_data(data)
    await state.set_state(EntryForm.container_number)

    await callback.message.edit_text(get_text("start_entry", lang))
    await callback.answer()


@router.callback_query(F.data == "back_to_iso_type", EntryForm.container_owner)
@require_manager_access
async def back_to_iso_type(callback: CallbackQuery, state: FSMContext, user=None):
    """Go back to ISO type selection"""
    lang = await get_user_language(state)

    # Clear owner and iso data - get current data and remove keys
    data = await state.get_data()
    data.pop("container_iso_type", None)
    data.pop("container_owner_id", None)
    data.pop("container_owner_name", None)
    data.pop("container_owner_skipped", None)
    await state.set_data(data)
    await state.set_state(EntryForm.container_iso_type)

    # Build summary and show ISO type selection
    summary = await build_summary(data, lang)

    await callback.message.edit_text(
        f"{summary}\n\n{get_text('ask_iso_type', lang)}",
        reply_markup=get_iso_type_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_owner", EntryForm.status)
@require_manager_access
async def back_to_owner(callback: CallbackQuery, state: FSMContext, user=None):
    """Go back to owner selection"""
    lang = await get_user_language(state)

    # Clear status and owner data - get current data and remove keys
    data = await state.get_data()
    data.pop("status", None)
    data.pop("container_owner_id", None)
    data.pop("container_owner_name", None)
    data.pop("container_owner_skipped", None)
    await state.set_data(data)
    await state.set_state(EntryForm.container_owner)

    # Build summary and show owner selection
    summary = await build_summary(data, lang)

    keyboard, has_owners = await get_container_owner_keyboard(lang)
    if has_owners:
        message_text = f"{summary}\n\n{get_text('ask_owner', lang)}"
    else:
        message_text = f"{summary}\n\n{get_text('no_owners_available', lang)}"

    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "back_to_status", EntryForm.transport_type)
@require_manager_access
async def back_to_status(callback: CallbackQuery, state: FSMContext, user=None):
    """Go back to status selection"""
    lang = await get_user_language(state)

    # Clear transport and status data - get current data and remove keys
    data = await state.get_data()
    data.pop("status", None)
    data.pop("transport_type", None)
    await state.set_data(data)
    await state.set_state(EntryForm.status)

    # Build summary and show status selection
    summary = await build_summary(data, lang)

    await callback.message.edit_text(
        f"{summary}\n\n{get_text('ask_status', lang)}",
        reply_markup=get_status_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_transport_type", EntryForm.transport_plate_photo)
@require_manager_access
async def back_to_transport_type_from_plate(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """Go back from plate confirmation - to photos step to re-take photos"""
    lang = await get_user_language(state)

    # Get current data
    data = await state.get_data()

    # Clear plate data but keep photos (user may want to add more or retake)
    data.pop("detected_plate_number", None)
    data.pop("plate_confidence", None)
    data.pop("transport_number", None)
    await state.set_data(data)
    await state.set_state(EntryForm.photos)

    summary = await build_summary(data, lang)
    photos = data.get("photos", [])

    await callback.message.edit_text(
        f"{summary}\n\n{get_text('ask_all_photos_truck', lang)}",
        reply_markup=get_photo_skip_keyboard(lang, has_photos=len(photos) > 0),
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_transport_number", EntryForm.photos)
@require_manager_access
async def back_to_transport_number(callback: CallbackQuery, state: FSMContext, user=None):
    """Go back from photos - to status/transport_type (TRUCK) or transport_number (WAGON)"""
    lang = await get_user_language(state)

    # Clear photos and related data
    data = await state.get_data()
    transport_type = data.get("transport_type")
    status = data.get("status")
    data.pop("photos", None)
    data.pop("matched_preorder_id", None)
    data.pop("detected_plate_number", None)
    data.pop("plate_confidence", None)
    data.pop("last_photo_timestamp", None)
    data.pop("photo_loading_msg_id", None)

    # For TRUCK: photos come right after status/transport_type selection
    if transport_type == "TRUCK":
        # Clear transport data
        data.pop("transport_type", None)

        if status == "EMPTY":
            # EMPTY auto-selected TRUCK - go back to status
            data.pop("status", None)
            await state.set_data(data)
            await state.set_state(EntryForm.status)

            summary = await build_summary(data, lang)
            await callback.message.edit_text(
                f"{summary}\n\n{get_text('ask_status', lang)}",
                reply_markup=get_status_keyboard(lang),
            )
        else:
            # LADEN - go back to transport type
            await state.set_data(data)
            await state.set_state(EntryForm.transport_type)

            summary = await build_summary(data, lang)
            await callback.message.edit_text(
                f"{summary}\n\n{get_text('ask_transport_type', lang)}",
                reply_markup=get_transport_type_keyboard(lang),
            )
    else:
        # For WAGON: go back to transport number input
        data.pop("transport_number", None)
        await state.set_data(data)
        await state.set_state(EntryForm.transport_number)

        summary = await build_summary(data, lang)
        await callback.message.edit_text(
            f"{summary}\n\n{get_text('ask_transport_number', lang)}"
        )
    await callback.answer()
