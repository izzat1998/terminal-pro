"""
Owner notification service for sending container entry notifications
to container owner Telegram groups.
"""

import logging
from html import escape

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InputMediaPhoto

from apps.accounts.models import CustomUser
from apps.terminal_operations.models import ContainerEntry


logger = logging.getLogger(__name__)


class OwnerNotificationService:
    """Send notifications to container owner Telegram groups."""

    async def notify_container_entry(
        self,
        bot: Bot,
        entry: ContainerEntry,
        manager: CustomUser,
        photo_file_ids: list[str] | None = None,
    ) -> bool:
        """
        Send entry notification to container owner's group.

        Args:
            bot: aiogram Bot instance
            entry: ContainerEntry that was created
            manager: CustomUser (manager) who created the entry
            photo_file_ids: Optional list of Telegram photo file_ids

        Returns:
            True if sent, False if skipped/failed (silent failure)
        """
        # Check if container owner is set and notifications enabled
        owner = entry.container_owner
        if not owner:
            logger.debug(f"No container owner for entry {entry.id}, skipping notification")
            return False

        if not owner.notifications_enabled:
            logger.debug(f"Notifications disabled for owner {owner.name}, skipping")
            return False

        if not owner.telegram_group_id:
            logger.debug(f"No telegram_group_id for owner {owner.name}, skipping")
            return False

        # Build notification message
        message = self._build_message(entry, manager)

        try:
            # Send to group (supports both numeric ID and @username)
            chat_id = owner.telegram_group_id.strip()

            if photo_file_ids:
                # Send photos as media group with caption on first photo
                await self._send_with_photos(bot, chat_id, message, photo_file_ids)
            else:
                # Send text-only message
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                )

            logger.info(
                f"Sent container entry notification to {owner.name} "
                f"(group: {chat_id}) for entry {entry.id}"
            )
            return True

        except Exception as e:
            # Silent fail - log error but don't interrupt entry creation
            logger.error(
                f"Failed to send notification to owner {owner.name} "
                f"(group: {owner.telegram_group_id}): {e}"
            )
            return False

    async def _send_with_photos(
        self,
        bot: Bot,
        chat_id: str,
        caption: str,
        photo_file_ids: list[str],
    ) -> None:
        """Send photos as media group with caption on first photo."""
        media_group = []

        for idx, file_id in enumerate(photo_file_ids):
            if idx == 0:
                # First photo gets the caption
                media_group.append(
                    InputMediaPhoto(media=file_id, caption=caption, parse_mode=ParseMode.HTML)
                )
            else:
                media_group.append(InputMediaPhoto(media=file_id))

        await bot.send_media_group(chat_id=chat_id, media=media_group)

    def _build_message(self, entry: ContainerEntry, manager: CustomUser) -> str:
        """Build notification message in Russian."""
        # Format container number with space (e.g., MSKU 1234567)
        container_num = entry.container.container_number
        if len(container_num) >= 4:
            formatted_container = f"{container_num[:4]} {container_num[4:]}"
        else:
            formatted_container = container_num

        # Get ISO type
        iso_type = entry.container.iso_type or "-"

        # Get status display (Russian)
        status_display = entry.get_status_display()

        # Get transport display (Russian)
        transport_display = entry.get_transport_type_display()
        transport_number = entry.transport_number or "-"

        # Format entry time
        entry_time = entry.entry_time.strftime("%d.%m.%Y %H:%M")

        # Manager name (escape for HTML safety)
        manager_name = escape(manager.get_full_name() or manager.username)

        message = (
            f"📦 <b>Новый контейнер на терминале</b>\n"
            f"\n"
            f"📋 Контейнер: <code>{escape(formatted_container)}</code>\n"
            f"📐 ISO тип: {escape(iso_type)}\n"
            f"📊 Статус: {escape(status_display)}\n"
            f"🚛 Транспорт: {escape(transport_display)} ({escape(transport_number)})\n"
            f"🕐 Время въезда: {entry_time}\n"
            f"👤 Менеджер: {manager_name}"
        )

        return message
