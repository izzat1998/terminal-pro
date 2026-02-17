"""
Owner notification service for sending container entry and exit notifications
to container owner Telegram groups.
"""

import logging
from dataclasses import dataclass, field
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
    message_ids: list[int] = field(default_factory=list)
    chat_id: str = ""


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
                msg_ids = await self._send_with_photos(bot, chat_id, message, photo_file_ids)
            else:
                # Send text-only message
                sent_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                )
                msg_ids = [sent_msg.message_id]

            logger.info(
                f"Sent container entry notification to {data.owner_name} "
                f"(group: {chat_id}) for entry {data.entry_id}"
            )
            return NotificationResult(status="sent", message_ids=msg_ids, chat_id=chat_id)

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
    ) -> list[int]:
        """Send photos as media group with caption on first photo. Returns list of message_ids."""
        media_group = []

        for idx, file_id in enumerate(photo_file_ids):
            if idx == 0:
                # First photo gets the caption
                media_group.append(
                    InputMediaPhoto(media=file_id, caption=caption, parse_mode=ParseMode.HTML)
                )
            else:
                media_group.append(InputMediaPhoto(media=file_id))

        sent_messages = await bot.send_media_group(chat_id=chat_id, media=media_group)
        return [msg.message_id for msg in sent_messages]

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

    def _build_combined_exit_message(self, data_list: list[ExitNotificationData]) -> str:
        """Build combined exit notification for multiple containers belonging to same owner."""
        count = len(data_list)
        lines = [f"<b>🚪 Выезд контейнеров ({count} шт.)</b>"]

        for idx, data in enumerate(data_list, 1):
            container_num = data.container_number
            if len(container_num) >= 4:
                display_container = f"{container_num[:4]} {container_num[4:]}"
            else:
                display_container = container_num

            lines.append("")
            lines.append(f"📋 Контейнер {idx}: <code>{escape(display_container)}</code>")
            lines.append(f"📐 ISO тип: {escape(data.iso_type)} | 📊 {escape(data.status_display)}")

            if data.client_name:
                lines.append(f"👤 Клиент: {escape(data.client_name)}")

            entry_transport = escape(data.entry_transport_display)
            if data.entry_transport_number:
                entry_transport += f" ({escape(data.entry_transport_number)})"
            lines.append(f"🚛 Въезд: {entry_transport} — {data.entry_time_str}")
            lines.append(f"⏱️ На терминале: <b>{data.dwell_time_days} дн.</b>")

        # Shared exit info from the first entry (all share same exit transport)
        first = data_list[0]
        lines.append("")
        lines.append(
            f"🚛 Выезд: {escape(first.exit_transport_display)} "
            f"({escape(first.exit_transport_number)}) — {first.exit_time_str}"
        )
        lines.append(f"👤 Менеджер: {escape(first.manager_name)}")

        return "\n".join(lines)

    async def notify_container_exits_batch(
        self,
        bot: Bot,
        entries: list[ContainerEntry],
        manager: CustomUser,
        photo_file_ids: list[str] | None = None,
    ) -> list[NotificationResult]:
        """
        Send exit notifications for multiple entries, combining entries that share
        the same owner group into a single message.

        Args:
            bot: aiogram Bot instance
            entries: list of ContainerEntry objects with exit info
            manager: CustomUser (manager) who processed the exit
            photo_file_ids: Optional list of Telegram photo file_ids (exit photos)

        Returns:
            List of NotificationResult for each owner group notified
        """
        # Extract data for all entries in sync context
        def extract_all():
            return [self._extract_exit_notification_data(e, manager) for e in entries]

        all_data = await sync_to_async(extract_all)()

        # Group by owner_telegram_group_id
        groups: dict[str, list[ExitNotificationData]] = {}
        results: list[NotificationResult] = []

        for data in all_data:
            if not data.owner_name:
                logger.debug(f"No container owner for entry {data.entry_id}, skipping exit notification")
                results.append(NotificationResult(status="skipped", error_message="Владелец не указан"))
                continue
            if not data.owner_notifications_enabled:
                logger.debug(f"Notifications disabled for owner {data.owner_name}, skipping exit notification")
                results.append(NotificationResult(status="skipped", error_message="Уведомления отключены"))
                continue
            if not data.owner_telegram_group_id:
                logger.debug(f"No telegram_group_id for owner {data.owner_name}, skipping exit notification")
                results.append(NotificationResult(status="skipped", error_message="Группа не настроена"))
                continue

            group_id = data.owner_telegram_group_id.strip()
            groups.setdefault(group_id, []).append(data)

        # Send one message per owner group
        for chat_id, data_list in groups.items():
            if len(data_list) == 1:
                message = self._build_exit_message_from_data(data_list[0])
            else:
                message = self._build_combined_exit_message(data_list)

            try:
                if photo_file_ids:
                    msg_ids = await self._send_with_photos(bot, chat_id, message, photo_file_ids)
                else:
                    sent_msg = await bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode=ParseMode.HTML,
                    )
                    msg_ids = [sent_msg.message_id]

                entry_ids = [d.entry_id for d in data_list]
                owner_name = data_list[0].owner_name
                logger.info(
                    f"Sent combined exit notification to {owner_name} "
                    f"(group: {chat_id}) for entries {entry_ids}"
                )
                results.append(NotificationResult(status="sent", message_ids=msg_ids, chat_id=chat_id))

            except Exception as e:
                owner_name = data_list[0].owner_name
                logger.error(
                    f"Failed to send exit notification to owner {owner_name} "
                    f"(group: {chat_id}): {e}"
                )
                results.append(NotificationResult(status="error", error_message=str(e)))

        return results

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
                msg_ids = await self._send_with_photos(bot, chat_id, message, photo_file_ids)
            else:
                # Send text-only message
                sent_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                )
                msg_ids = [sent_msg.message_id]

            logger.info(
                f"Sent container exit notification to {data.owner_name} "
                f"(group: {chat_id}) for entry {data.entry_id}"
            )
            return NotificationResult(status="sent", message_ids=msg_ids, chat_id=chat_id)

        except Exception as e:
            # Silent fail - log error but don't interrupt exit processing
            logger.error(
                f"Failed to send exit notification to owner {data.owner_name} "
                f"(group: {data.owner_telegram_group_id}): {e}"
            )
            return NotificationResult(status="error", error_message=str(e))
