"""
Handler for creating container entries from Telegram group messages.

Flow:
1. User sends a message with container number (e.g., "HDMU1234567") in a group
2. User sends photos (single or album) within 60 seconds
3. Bot collects all photos and creates an entry with the container number
4. Bot replies with confirmation or error message

Alternative flow:
- User sends photos with container number in caption (all in one message)

Defaults:
- status: LADEN
- transport_type: TRUCK
- iso_type: 42G1 (40ft standard)
- container_owner: Auto-detected from group ID if configured
"""

import asyncio
import logging
import re
import time
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.types import Message
from asgiref.sync import sync_to_async
from django.core.files.uploadedfile import InMemoryUploadedFile

from apps.accounts.models import CustomUser
from apps.terminal_operations.models import ContainerOwner
from telegram_bot.services.entry_service import BotEntryService


logger = logging.getLogger(__name__)
router = Router()

# Container number pattern: 4 letters + 7 digits
CONTAINER_PATTERN = re.compile(r"[A-Z]{4}[0-9]{7}")

# Default values for group entries
# Status and iso_type are "-" because the bot cannot determine them from group messages.
# Operators must manually verify and set correct values.
DEFAULT_STATUS = "-"
DEFAULT_TRANSPORT_TYPE = "TRUCK"
DEFAULT_ISO_TYPE = "-"

# Timing settings
MEDIA_GROUP_COLLECTION_DELAY = 1.0  # Wait 1s for all photos in album to arrive
PENDING_CONTAINER_TIMEOUT = 60  # Container number valid for 60 seconds
CLEANUP_TIMEOUT = 300  # Clean up abandoned data after 5 minutes
MAX_PENDING_ENTRIES = 500  # Maximum pending entries to keep in memory

# Temporary storage for pending container numbers (text message sent, waiting for photos)
# Format: {(chat_id, user_id): {'container_number': str, 'timestamp': float}}
pending_container_numbers: dict = {}

# Temporary storage for photo collection (photos arrived, collecting album)
# Format: {media_group_id: {'photos': [file_ids], 'message': Message, 'bot': Bot,
#          'container_number': str, 'timestamp': float}}
# OR for photos without caption using pending container:
# Format: {(chat_id, user_id): {'photos': [file_ids], 'message': Message, 'bot': Bot,
#          'container_number': str, 'timestamp': float, 'media_group_id': str|None}}
photo_collections: dict = {}

# Store task references to prevent garbage collection
_processing_tasks: set = set()


async def cleanup_old_data() -> None:
    """Clean up abandoned pending data to prevent memory leak"""
    current_time = time.time()

    # Clean up old pending container numbers
    expired_pending = [
        key
        for key, data in pending_container_numbers.items()
        if current_time - data["timestamp"] > CLEANUP_TIMEOUT
    ]
    for key in expired_pending:
        logger.debug(f"Cleaning up expired pending container: {key}")
        del pending_container_numbers[key]

    # Clean up old photo collections
    expired_collections = [
        key
        for key, data in photo_collections.items()
        if current_time - data["timestamp"] > CLEANUP_TIMEOUT
    ]
    for key in expired_collections:
        logger.debug(f"Cleaning up expired photo collection: {key}")
        del photo_collections[key]

    # Enforce max size limits
    if len(pending_container_numbers) > MAX_PENDING_ENTRIES:
        sorted_items = sorted(
            pending_container_numbers.items(), key=lambda x: x[1]["timestamp"]
        )
        to_remove = len(pending_container_numbers) - MAX_PENDING_ENTRIES
        for key, _ in sorted_items[:to_remove]:
            del pending_container_numbers[key]

    if len(photo_collections) > MAX_PENDING_ENTRIES:
        sorted_items = sorted(
            photo_collections.items(), key=lambda x: x[1]["timestamp"]
        )
        to_remove = len(photo_collections) - MAX_PENDING_ENTRIES
        for key, _ in sorted_items[:to_remove]:
            del photo_collections[key]


def extract_container_number(text: str) -> str | None:
    """
    Extract container number from text.
    Returns normalized container number or None if not found.
    """
    if not text:
        return None

    # Remove all non-alphanumeric and convert to uppercase
    cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()

    # Find container number pattern
    match = CONTAINER_PATTERN.search(cleaned)
    if match:
        return match.group(0)

    return None


@sync_to_async
def get_container_owner_by_group(chat_id: int | str) -> ContainerOwner | None:
    """
    Find ContainerOwner by Telegram group ID.
    Returns the owner if found, None otherwise.
    """
    chat_id_str = str(chat_id)

    try:
        return ContainerOwner.objects.filter(
            telegram_group_id=chat_id_str,
            notifications_enabled=True,
        ).first()
    except Exception as e:
        logger.error(f"Error finding container owner for group {chat_id}: {e}")
        return None


@sync_to_async
def get_manager_by_telegram_id(telegram_user_id: int) -> CustomUser | None:
    """
    Find manager by Telegram user ID.
    Returns the user if they are a registered manager with bot access.
    """
    try:
        return CustomUser.objects.filter(
            telegram_user_id=telegram_user_id,
            user_type__in=["manager", "admin"],
            is_active=True,
            bot_access=True,
        ).first()
    except Exception as e:
        logger.error(f"Error finding manager for telegram_id {telegram_user_id}: {e}")
        return None


@sync_to_async
def _validate_container_number(entry_service: BotEntryService, container_number: str) -> bool:
    """Sync wrapper for container number validation."""
    return entry_service.validate_container_number(container_number)


@sync_to_async
def _check_active_entry(entry_service: BotEntryService, container_number: str):
    """Sync wrapper for checking active entry."""
    return entry_service.check_active_entry(container_number)


@sync_to_async
def _create_entry(entry_service: BotEntryService, **kwargs):
    """Sync wrapper for creating entry."""
    return entry_service.create_entry(**kwargs)


async def download_photo(bot: Bot, file_id: str, filename: str) -> InMemoryUploadedFile:
    """Download a photo from Telegram and return as Django InMemoryUploadedFile."""
    file = await bot.get_file(file_id)
    photo_bytes = await bot.download_file(file.file_path)

    # Create BytesIO and seek to beginning
    photo_io = BytesIO(photo_bytes.read())
    photo_io.seek(0)

    # Convert to Django InMemoryUploadedFile
    django_file = InMemoryUploadedFile(
        photo_io,
        None,
        filename,
        "image/jpeg",
        photo_io.getbuffer().nbytes,
        None,
    )

    return django_file


async def download_all_photos(
    bot: Bot, file_ids: list[str], container_number: str
) -> list[InMemoryUploadedFile]:
    """Download multiple photos from Telegram."""
    photos = []
    for idx, file_id in enumerate(file_ids):
        try:
            filename = f"{container_number}_group_{idx + 1}.jpg"
            photo_file = await download_photo(bot, file_id, filename)
            photos.append(photo_file)
        except Exception as e:
            logger.error(f"Failed to download photo {file_id}: {e}")
    return photos


async def create_container_entry(
    message: Message,
    bot: Bot,
    container_number: str,
    photo_file_ids: list[str],
) -> None:
    """Create a container entry with the given photos."""
    logger.info(
        f"Creating entry for {container_number} with {len(photo_file_ids)} photos "
        f"from group {message.chat.id} by user {message.from_user.id}"
    )

    try:
        # Get container owner from group ID
        owner = await get_container_owner_by_group(message.chat.id)
        owner_id = owner.id if owner else None

        # Check if sender is a registered manager
        manager = await get_manager_by_telegram_id(message.from_user.id)

        # Download all photos
        photos = await download_all_photos(bot, photo_file_ids, container_number)

        if not photos:
            logger.warning(f"Group entry: no photos downloaded for {container_number}")
            return

        # Create the entry
        entry_service = BotEntryService()

        # Validate container number format
        if not await _validate_container_number(entry_service, container_number):
            logger.warning(f"Group entry: invalid container format: {container_number}")
            return

        # Check for duplicate entry
        existing = await _check_active_entry(entry_service, container_number)
        if existing:
            logger.info(
                f"Group entry skipped: {container_number} already on terminal "
                f"(entry {existing.id})"
            )
            return

        # Create entry with all photos
        entry = await _create_entry(
            entry_service,
            container_number=container_number,
            container_iso_type=DEFAULT_ISO_TYPE,
            status=DEFAULT_STATUS,
            transport_type=DEFAULT_TRANSPORT_TYPE,
            transport_number="",
            photos=photos,
            container_owner_id=owner_id,
            manager=manager,
        )

        manager_info = f" by {manager.full_name}" if manager else ""
        logger.info(
            f"Group entry created: {entry.id} for container {container_number} "
            f"with {len(photos)} photos{manager_info}"
        )

    except Exception as e:
        logger.exception(f"Error creating group entry for {container_number}: {e}")


async def process_photo_collection(collection_key: str | tuple) -> None:
    """
    Process collected photos after debounce delay.
    Creates the container entry with all collected photos.
    """
    await asyncio.sleep(MEDIA_GROUP_COLLECTION_DELAY)

    if collection_key not in photo_collections:
        return

    collection = photo_collections[collection_key]
    del photo_collections[collection_key]

    await create_container_entry(
        message=collection["message"],
        bot=collection["bot"],
        container_number=collection["container_number"],
        photo_file_ids=collection["photos"],
    )


def get_pending_container(chat_id: int, user_id: int) -> str | None:
    """
    Get pending container number for user in chat if still valid.
    Returns container number or None if expired/not found.
    """
    key = (chat_id, user_id)
    if key not in pending_container_numbers:
        return None

    data = pending_container_numbers[key]
    if time.time() - data["timestamp"] > PENDING_CONTAINER_TIMEOUT:
        # Expired
        del pending_container_numbers[key]
        return None

    return data["container_number"]


def clear_pending_container(chat_id: int, user_id: int) -> None:
    """Clear pending container number for user in chat."""
    key = (chat_id, user_id)
    pending_container_numbers.pop(key, None)


# =============================================================================
# Handler for text messages with container numbers
# =============================================================================
@router.message(
    F.chat.type.in_(["group", "supergroup"]),
    F.text,
)
async def handle_container_number_text(message: Message):
    """
    Handle text messages in groups that contain a container number.
    Stores the container number temporarily, waiting for photos to follow.
    """
    text = message.text or ""
    container_number = extract_container_number(text)

    if not container_number:
        return

    # Validate container number
    entry_service = BotEntryService()
    if not await _validate_container_number(entry_service, container_number):
        return

    # Check for duplicate entry
    existing = await _check_active_entry(entry_service, container_number)
    if existing:
        logger.info(
            f"Group entry: {container_number} already on terminal (entry {existing.id})"
        )
        return

    # Store pending container number
    key = (message.chat.id, message.from_user.id)
    pending_container_numbers[key] = {
        "container_number": container_number,
        "timestamp": time.time(),
    }

    logger.info(
        f"Group entry: Stored pending container {container_number} "
        f"for user {message.from_user.id} in group {message.chat.id}"
    )


# =============================================================================
# Handler for photo messages
# =============================================================================
@router.message(
    F.chat.type.in_(["group", "supergroup"]),
    F.photo,
)
async def handle_group_photo(message: Message, bot: Bot):
    """
    Handle photo messages in groups.

    Supports two flows:
    1. Photos with container number in caption
    2. Photos following a text message with container number
    """
    photo = message.photo[-1]  # Get largest resolution
    media_group_id = message.media_group_id
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Periodic cleanup
    await cleanup_old_data()

    # Determine collection key (media_group_id for albums, (chat_id, user_id) for single photos)
    collection_key = media_group_id or (chat_id, user_id)

    # FIRST: Check if we're adding to an existing collection (for album photos 2, 3, 4...)
    if collection_key in photo_collections:
        # Add photo to existing collection
        photo_collections[collection_key]["photos"].append(photo.file_id)
        logger.debug(
            f"Added photo to collection {collection_key}, "
            f"total: {len(photo_collections[collection_key]['photos'])}"
        )
        return

    # SECOND: Try to get container number from caption
    caption = message.caption or ""
    container_number = extract_container_number(caption)

    # If no container in caption, check for pending container number
    if not container_number:
        container_number = get_pending_container(chat_id, user_id)
        if container_number:
            logger.debug(
                f"Using pending container {container_number} for photos "
                f"from user {user_id} in group {chat_id}"
            )

    if not container_number:
        # No container number available, ignore
        return

    # Start new collection
    logger.info(
        f"Group entry: Starting photo collection for {container_number} "
        f"from group {chat_id} by user {user_id}"
    )

    # Validate before starting collection
    entry_service = BotEntryService()
    if not await _validate_container_number(entry_service, container_number):
        logger.warning(f"Group entry: invalid container format: {container_number}")
        return

    # Check for duplicate entry
    existing = await _check_active_entry(entry_service, container_number)
    if existing:
        logger.info(
            f"Group entry skipped: {container_number} already on terminal "
            f"(entry {existing.id})"
        )
        clear_pending_container(chat_id, user_id)
        return

    # Initialize new collection
    photo_collections[collection_key] = {
        "photos": [photo.file_id],
        "message": message,
        "bot": bot,
        "container_number": container_number,
        "timestamp": time.time(),
    }

    # Clear pending container since we're now using it
    clear_pending_container(chat_id, user_id)

    # Start delayed processing task
    task = asyncio.create_task(process_photo_collection(collection_key))
    _processing_tasks.add(task)
    task.add_done_callback(_processing_tasks.discard)
