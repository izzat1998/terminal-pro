"""
Shared photo handling utilities for Telegram bot.

This module provides reusable photo collection logic with:
- Media group (album) support with debounced collection
- Single photo handling with debounced confirmation
- Task cancellation to prevent race conditions
- Memory cleanup for abandoned uploads

Used by both entry and exit flows.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from django.core.files.uploadedfile import InMemoryUploadedFile

from telegram_bot.keyboards.inline import get_photo_skip_keyboard
from telegram_bot.translations import get_text


logger = logging.getLogger(__name__)

# Constants
MEDIA_GROUP_COLLECTION_DELAY = 1.0  # Wait 1s for all photos in album to arrive
PHOTO_DEBOUNCE_DELAY = 2.5  # Wait 2.5s before finalizing photo upload
MEDIA_GROUP_CLEANUP_TIMEOUT = 300  # Clean up abandoned media groups after 5 minutes
MAX_MEDIA_GROUPS = 1000  # Maximum media groups to keep in memory

# Temporary storage for media groups (albums)
# Format: {media_group_id: {'photos': [file_ids], 'message': Message, 'state': FSMContext, 'timestamp': float, 'on_complete': callable}}
media_groups: dict = {}

# Track active photo confirmation tasks for cleanup
# Format: {user_id: asyncio.Task}
photo_confirmation_tasks: dict = {}


async def cleanup_old_media_groups() -> None:
    """Clean up abandoned media groups to prevent memory leak"""
    current_time = time.time()
    expired_groups = []

    for media_group_id, group_data in media_groups.items():
        if current_time - group_data["timestamp"] > MEDIA_GROUP_CLEANUP_TIMEOUT:
            expired_groups.append(media_group_id)

    for media_group_id in expired_groups:
        logger.warning(f"Cleaning up abandoned media group: {media_group_id}")
        del media_groups[media_group_id]

    # Also enforce max size limit
    if len(media_groups) > MAX_MEDIA_GROUPS:
        sorted_groups = sorted(media_groups.items(), key=lambda x: x[1]["timestamp"])
        to_remove = len(media_groups) - MAX_MEDIA_GROUPS
        for media_group_id, _ in sorted_groups[:to_remove]:
            logger.warning(f"Removing media group due to size limit: {media_group_id}")
            del media_groups[media_group_id]


def cancel_photo_confirmation_task(user_id: int) -> None:
    """Cancel any pending photo confirmation task for user"""
    if user_id in photo_confirmation_tasks:
        task = photo_confirmation_tasks[user_id]
        if not task.done():
            task.cancel()
            logger.debug(f"Cancelled photo confirmation task for user {user_id}")
        del photo_confirmation_tasks[user_id]


async def get_user_language(state: FSMContext) -> str:
    """Get user's selected language from state, default to Russian"""
    data = await state.get_data()
    return data.get("language", "ru")


# Type alias for the summary builder callback
SummaryBuilder = Callable[[dict, str], Awaitable[str]]

# Type alias for keyboard builder callback
KeyboardBuilder = Callable[[str, bool], "InlineKeyboardMarkup"]


async def _process_media_group(
    media_group_id: str,
    summary_builder: SummaryBuilder | None = None,
    keyboard_func: KeyboardBuilder | None = None,
) -> None:
    """
    Process collected media group after debounce delay.

    Args:
        media_group_id: The Telegram media group ID
        summary_builder: Optional async function to build summary text
        keyboard_func: Optional function to build keyboard (default: get_photo_skip_keyboard)
    """
    await asyncio.sleep(MEDIA_GROUP_COLLECTION_DELAY)

    if media_group_id not in media_groups:
        return

    group_data = media_groups[media_group_id]
    message = group_data["message"]
    state = group_data["state"]
    group_photos = group_data["photos"]
    user_id = message.from_user.id

    # Get current state data and add all group photos
    data = await state.get_data()
    lang = data.get("language", "ru")
    existing_photos = data.get("photos", [])
    all_photos = existing_photos + group_photos

    # Update state with all photos
    photo_timestamp = time.time()
    loading_msg_id = data.get("photo_loading_msg_id")

    # Loading message text
    loading_text = get_text("photo_loading", lang, count=len(all_photos))

    # Send or update loading message
    if not loading_msg_id:
        sent_msg = await message.answer(loading_text)
        loading_msg_id = sent_msg.message_id

    await state.update_data(
        photos=all_photos,
        last_photo_timestamp=photo_timestamp,
        photo_loading_msg_id=loading_msg_id,
    )

    # Update loading message with count
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id, message_id=loading_msg_id, text=loading_text
        )
    except Exception as e:
        logger.error(f"Failed to edit loading message: {e}")

    # Clean up media group storage
    del media_groups[media_group_id]

    # Cancel any existing photo confirmation task for this user
    cancel_photo_confirmation_task(user_id)

    # Start debounced confirmation and track it
    task = asyncio.create_task(
        _send_photo_confirmation(
            message, state, photo_timestamp, summary_builder, keyboard_func
        )
    )
    photo_confirmation_tasks[user_id] = task


async def _send_photo_confirmation(
    message: Message,
    state: FSMContext,
    photo_timestamp: float,
    summary_builder: SummaryBuilder | None = None,
    keyboard_func: KeyboardBuilder | None = None,
) -> None:
    """
    Send photo confirmation after debounce delay.

    Args:
        message: The Telegram message
        state: FSM context
        photo_timestamp: Timestamp when photos were added
        summary_builder: Optional async function to build summary text
        keyboard_func: Optional function to build keyboard (default: get_photo_skip_keyboard)
    """
    user_id = message.from_user.id
    # Use default keyboard if not specified
    get_keyboard = keyboard_func or get_photo_skip_keyboard

    try:
        await asyncio.sleep(PHOTO_DEBOUNCE_DELAY)

        # Check if another photo was added during wait
        data = await state.get_data()
        if data.get("last_photo_timestamp") != photo_timestamp:
            return  # Another photo arrived, this task is cancelled

        # No new photos, send final confirmation
        lang = data.get("language", "ru")
        photos = data.get("photos", [])
        loading_msg_id = data.get("photo_loading_msg_id")

        # Build summary if builder provided
        if summary_builder:
            summary = await summary_builder(data, lang)
            final_text = f"{summary}\n\n{get_text('photo_received', lang, count=len(photos))}"
        else:
            final_text = get_text("photo_received", lang, count=len(photos))

        # Edit the loading message with final summary and keyboard
        has_photos = len(photos) > 0
        if loading_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=loading_msg_id,
                    text=final_text,
                    reply_markup=get_keyboard(lang, has_photos=has_photos),
                )
            except Exception as e:
                logger.error(f"Failed to edit photo confirmation message: {e}")
                # If edit fails, send new message
                await message.answer(
                    final_text,
                    reply_markup=get_keyboard(lang, has_photos=has_photos),
                )
    except asyncio.CancelledError:
        logger.debug("Photo confirmation task was cancelled")
        raise  # Re-raise to properly handle cancellation
    finally:
        # Clean up task reference to prevent memory leak
        photo_confirmation_tasks.pop(user_id, None)


async def handle_photo_upload(
    message: Message,
    state: FSMContext,
    summary_builder: SummaryBuilder | None = None,
    keyboard_func: KeyboardBuilder | None = None,
) -> None:
    """
    Handle photo upload - supports both single photos and media groups (albums).

    This function:
    1. Collects photos from albums with 1s debounce
    2. Debounces confirmation by 2.5s to allow multiple uploads
    3. Shows loading message with photo count
    4. Shows skip/done keyboard when ready

    Args:
        message: The Telegram message containing the photo
        state: FSM context for the current conversation
        summary_builder: Optional async function(data, lang) -> str to build summary
        keyboard_func: Optional function to build keyboard (default: get_photo_skip_keyboard)
    """
    lang = await get_user_language(state)
    photo = message.photo[-1]  # Get highest resolution
    media_group_id = message.media_group_id
    user_id = message.from_user.id

    # Periodic cleanup of old media groups
    await cleanup_old_media_groups()

    # CASE 1: Photo is part of a media group (album)
    if media_group_id:
        if media_group_id not in media_groups:
            # First photo in group - initialize
            media_groups[media_group_id] = {
                "photos": [photo.file_id],
                "message": message,
                "state": state,
                "timestamp": time.time(),
            }
            # Start collection task
            asyncio.create_task(
                _process_media_group(media_group_id, summary_builder, keyboard_func)
            )
        else:
            # Additional photo in same group - append
            media_groups[media_group_id]["photos"].append(photo.file_id)
        return  # Don't process yet, wait for full group

    # CASE 2: Single photo (not part of a group)
    data = await state.get_data()
    photos = data.get("photos", [])
    loading_msg_id = data.get("photo_loading_msg_id")

    photos.append(photo.file_id)
    photo_timestamp = time.time()

    # Loading message text
    loading_text = get_text("photo_loading", lang, count=len(photos))

    # First photo: send loading message
    if not loading_msg_id:
        sent_msg = await message.answer(loading_text)
        await state.update_data(
            photos=photos,
            last_photo_timestamp=photo_timestamp,
            photo_loading_msg_id=sent_msg.message_id,
        )
    else:
        # Subsequent photos: edit existing message
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id, message_id=loading_msg_id, text=loading_text
            )
        except Exception as e:
            logger.error(f"Failed to edit loading message for single photo: {e}")
            # If edit fails (message too old), send new one
            sent_msg = await message.answer(loading_text)
            loading_msg_id = sent_msg.message_id
            await state.update_data(photo_loading_msg_id=loading_msg_id)

        await state.update_data(photos=photos, last_photo_timestamp=photo_timestamp)

    # Cancel any existing photo confirmation task for this user
    cancel_photo_confirmation_task(user_id)

    # Start debounced confirmation task and track it
    task = asyncio.create_task(
        _send_photo_confirmation(
            message, state, photo_timestamp, summary_builder, keyboard_func
        )
    )
    photo_confirmation_tasks[user_id] = task


async def download_photos_from_telegram(
    bot: Bot,
    photo_file_ids: list[str],
) -> list[InMemoryUploadedFile]:
    """
    Download photos from Telegram and convert to Django uploadable files.

    Args:
        bot: Telegram bot instance
        photo_file_ids: List of Telegram file IDs

    Returns:
        List of InMemoryUploadedFile objects ready for Django
    """
    photos = []
    for file_id in photo_file_ids:
        try:
            file = await bot.get_file(file_id)
            photo_io = await bot.download_file(file.file_path)  # Returns BytesIO

            # Convert to Django uploadable file
            photo_io.seek(0)  # Reset to beginning
            django_file = InMemoryUploadedFile(
                photo_io,
                None,
                f"{file_id}.jpg",
                "image/jpeg",
                photo_io.getbuffer().nbytes,
                None,
            )
            photos.append(django_file)
        except Exception as e:
            logger.error(f"Failed to download photo {file_id}: {e}")

    return photos


def clear_photo_state_data(data: dict) -> dict:
    """
    Return state update dict to clear photo-related fields.

    Use with: await state.update_data(**clear_photo_state_data(data))
    """
    return {
        "photos": [],
        "last_photo_timestamp": None,
        "photo_loading_msg_id": None,
    }
