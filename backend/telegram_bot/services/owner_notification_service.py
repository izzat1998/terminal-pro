"""
Owner notification service for sending container entry and exit notifications
to container owner Telegram groups.
"""

import logging
from dataclasses import dataclass
from html import escape

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InputMediaPhoto
from asgiref.sync import sync_to_async
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.terminal_operations.models import ContainerEntry


logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    """Result of a notification attempt."""

    status: str  # 'sent', 'skipped', 'error'
    error_message: str = ""


@dataclass
class NotificationData:
    """Data extracted from entry for notification (sync-safe)."""

    entry_id: int
    owner_name: str | None
    owner_notifications_enabled: bool
    owner_telegram_group_id: str | None
    container_number: str
    iso_type: str
    status_display: str
    transport_display: str
    transport_number: str
    entry_time_str: str
    manager_name: str


@dataclass
class ExitNotificationData:
    """Data extracted from entry for exit notification (sync-safe)."""

    entry_id: int
    owner_name: str | None
    owner_notifications_enabled: bool
    owner_telegram_group_id: str | None
    container_number: str
    iso_type: str
    status_display: str
    # Entry info
    entry_transport_display: str
    entry_transport_number: str
    client_name: str
    cargo_name: str
    cargo_weight: str
    location: str
    # Exit info
    exit_transport_display: str
    exit_transport_number: str
    entry_time_str: str
    exit_time_str: str
    dwell_time_days: int
    manager_name: str


class OwnerNotificationService:
    """Send notifications to container owner Telegram groups."""

    def _extract_notification_data(
        self, entry: ContainerEntry, manager: CustomUser
    ) -> NotificationData:
        """
        Extract all needed data from entry in sync context.
        Must be called via sync_to_async.
        """
        owner = entry.container_owner

        return NotificationData(
            entry_id=entry.id,
            owner_name=owner.name if owner else None,
            owner_notifications_enabled=owner.notifications_enabled if owner else False,
            owner_telegram_group_id=owner.telegram_group_id if owner else None,
            container_number=entry.container.container_number,
            iso_type=entry.container.iso_type or "-",
            status_display=entry.get_status_display(),
            transport_display=entry.get_transport_type_display(),
            transport_number=entry.transport_number or "-",
            entry_time_str=timezone.localtime(entry.entry_time).strftime("%d.%m.%Y %H:%M"),
            manager_name=manager.get_full_name() or manager.username,
        )

    async def notify_container_entry(
        self,
        bot: Bot,
        entry: ContainerEntry,
        manager: CustomUser,
        photo_file_ids: list[str] | None = None,
    ) -> NotificationResult:
        """
        Send entry notification to container owner's group.

        Args:
            bot: aiogram Bot instance
            entry: ContainerEntry that was created
            manager: CustomUser (manager) who created the entry
            photo_file_ids: Optional list of Telegram photo file_ids

        Returns:
            NotificationResult with status ('sent', 'skipped', 'error') and error_message
        """
        # Extract all data in sync context to avoid async ORM issues
        data = await sync_to_async(self._extract_notification_data)(entry, manager)

        # Check if container owner is set and notifications enabled
        if not data.owner_name:
            logger.debug(f"No container owner for entry {data.entry_id}, skipping notification")
            return NotificationResult(status="skipped", error_message="Владелец не указан")

        if not data.owner_notifications_enabled:
            logger.debug(f"Notifications disabled for owner {data.owner_name}, skipping")
            return NotificationResult(status="skipped", error_message="Уведомления отключены")

        if not data.owner_telegram_group_id:
            logger.debug(f"No telegram_group_id for owner {data.owner_name}, skipping")
            return NotificationResult(status="skipped", error_message="Группа не настроена")

        # Build notification message
        message = self._build_message_from_data(data)

        try:
            # Send to group (supports both numeric ID and @username)
            chat_id = data.owner_telegram_group_id.strip()

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
                f"Sent container entry notification to {data.owner_name} "
                f"(group: {chat_id}) for entry {data.entry_id}"
            )
            return NotificationResult(status="sent")

        except Exception as e:
            # Silent fail - log error but don't interrupt entry creation
            logger.error(
                f"Failed to send notification to owner {data.owner_name} "
                f"(group: {data.owner_telegram_group_id}): {e}"
            )
            return NotificationResult(status="error", error_message=str(e))

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

    def _build_message_from_data(self, data: NotificationData) -> str:
        """Build notification message in Russian from extracted data."""
        # Format container number with space for readability (e.g., TEMU 1234567)
        container_num = data.container_number
        if len(container_num) >= 4:
            display_container = f"{container_num[:4]} {container_num[4:]}"
        else:
            display_container = container_num

        # Title based on container status
        if data.status_display == "Порожний":
            title = "📦 Прием порожнего контейнера"
        else:
            title = "📦 Прием груженого контейнера"

        message = (
            f"<b>{title}</b>\n"
            f"\n"
            f"📋 Контейнер: <code>{escape(display_container)}</code>\n"
            f"📐 ISO тип: {escape(data.iso_type)}\n"
            f"📊 Статус: {escape(data.status_display)}\n"
            f"🚛 Транспорт: {escape(data.transport_display)} ({escape(data.transport_number)})\n"
            f"🕐 Время въезда: {data.entry_time_str}\n"
            f"👤 Менеджер: {escape(data.manager_name)}"
        )

        return message

    def _extract_exit_notification_data(
        self, entry: ContainerEntry, manager: CustomUser
    ) -> ExitNotificationData:
        """
        Extract all needed data from entry for exit notification in sync context.
        Must be called via sync_to_async.
        """
        owner = entry.container_owner

        # Format cargo weight for display
        cargo_weight = ""
        if entry.cargo_weight:
            cargo_weight = str(entry.cargo_weight).rstrip("0").rstrip(".")

        return ExitNotificationData(
            entry_id=entry.id,
            owner_name=owner.name if owner else None,
            owner_notifications_enabled=owner.notifications_enabled if owner else False,
            owner_telegram_group_id=owner.telegram_group_id if owner else None,
            container_number=entry.container.container_number,
            iso_type=entry.container.iso_type or "-",
            status_display=entry.get_status_display(),
            # Entry info
            entry_transport_display=entry.get_transport_type_display(),
            entry_transport_number=entry.transport_number or "",
            client_name=entry.client_name or "",
            cargo_name=entry.cargo_name or "",
            cargo_weight=cargo_weight,
            location=entry.location or "",
            # Exit info
            exit_transport_display=entry.get_exit_transport_type_display(),
            exit_transport_number=entry.exit_transport_number or "-",
            entry_time_str=timezone.localtime(entry.entry_time).strftime("%d.%m.%Y %H:%M"),
            exit_time_str=timezone.localtime(entry.exit_date).strftime("%d.%m.%Y %H:%M") if entry.exit_date else "-",
            dwell_time_days=entry.dwell_time_days or 0,
            manager_name=manager.get_full_name() or manager.username,
        )

    def _build_exit_message_from_data(self, data: ExitNotificationData) -> str:
        """Build exit notification message in Russian from extracted data."""
        # Format container number with space for readability (e.g., TEMU 1234567)
        container_num = data.container_number
        if len(container_num) >= 4:
            display_container = f"{container_num[:4]} {container_num[4:]}"
        else:
            display_container = container_num

        # Title based on container status
        if data.status_display == "Порожний":
            title = "🚪 Выезд порожнего контейнера"
        else:
            title = "🚪 Выезд груженого контейнера"

        lines = [
            f"<b>{title}</b>",
            "",
            f"📋 Контейнер: <code>{escape(display_container)}</code>",
            f"📐 ISO тип: {escape(data.iso_type)}",
            f"📊 Статус: {escape(data.status_display)}",
        ]

        # Entry details (if available)
        if data.client_name:
            lines.append(f"👤 Клиент: {escape(data.client_name)}")

        # Entry transport
        entry_transport = escape(data.entry_transport_display)
        if data.entry_transport_number:
            entry_transport += f" ({escape(data.entry_transport_number)})"
        lines.append(f"🚛 Въезд: {entry_transport} — {data.entry_time_str}")

        # Exit transport
        lines.append(
            f"🚛 Выезд: {escape(data.exit_transport_display)} "
            f"({escape(data.exit_transport_number)}) — {data.exit_time_str}"
        )

        # Dwell time
        lines.append(f"⏱️ Время на терминале: <b>{data.dwell_time_days} дн.</b>")
        lines.append(f"👤 Менеджер: {escape(data.manager_name)}")

        return "\n".join(lines)

    async def notify_container_exit(
        self,
        bot: Bot,
        entry: ContainerEntry,
        manager: CustomUser,
        photo_file_ids: list[str] | None = None,
    ) -> NotificationResult:
        """
        Send exit notification to container owner's group.

        Args:
            bot: aiogram Bot instance
            entry: ContainerEntry that was updated with exit info
            manager: CustomUser (manager) who processed the exit
            photo_file_ids: Optional list of Telegram photo file_ids (exit photos)

        Returns:
            NotificationResult with status ('sent', 'skipped', 'error') and error_message
        """
        # Extract all data in sync context to avoid async ORM issues
        data = await sync_to_async(self._extract_exit_notification_data)(entry, manager)

        # Check if container owner is set and notifications enabled
        if not data.owner_name:
            logger.debug(f"No container owner for entry {data.entry_id}, skipping exit notification")
            return NotificationResult(status="skipped", error_message="Владелец не указан")

        if not data.owner_notifications_enabled:
            logger.debug(f"Notifications disabled for owner {data.owner_name}, skipping exit notification")
            return NotificationResult(status="skipped", error_message="Уведомления отключены")

        if not data.owner_telegram_group_id:
            logger.debug(f"No telegram_group_id for owner {data.owner_name}, skipping exit notification")
            return NotificationResult(status="skipped", error_message="Группа не настроена")

        # Build notification message
        message = self._build_exit_message_from_data(data)

        try:
            # Send to group (supports both numeric ID and @username)
            chat_id = data.owner_telegram_group_id.strip()

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
                f"Sent container exit notification to {data.owner_name} "
                f"(group: {chat_id}) for entry {data.entry_id}"
            )
            return NotificationResult(status="sent")

        except Exception as e:
            # Silent fail - log error but don't interrupt exit processing
            logger.error(
                f"Failed to send exit notification to owner {data.owner_name} "
                f"(group: {data.owner_telegram_group_id}): {e}"
            )
            return NotificationResult(status="error", error_message=str(e))
