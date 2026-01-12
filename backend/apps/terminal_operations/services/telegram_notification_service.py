"""
Service for sending Telegram notifications about container entries to groups.
Uses best-effort approach: logs errors but never raises exceptions.
"""


from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaPhoto
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from apps.core.services.base_service import BaseService
from apps.files.models import FileAttachment
from apps.terminal_operations.models import ContainerEntry


class TelegramNotificationService(BaseService):
    """
    Service for sending Telegram group notifications about container entries.
    Best-effort: all methods log errors but never raise exceptions.

    Notifications are configured per Company via:
    - company.notifications_enabled: Toggle notifications on/off
    - company.telegram_group_id: Target Telegram group chat ID
    """

    def __init__(self):
        """Initialize service with bot token from settings."""
        super().__init__()
        self.bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)

    async def notify_group_about_entry(self, entry: ContainerEntry) -> bool:
        """
        Send notification to appropriate Telegram group about new container entry.
        Only sends for InterRail entries with photos.

        Args:
            entry: ContainerEntry instance

        Returns:
            bool: True if notification sent successfully, False otherwise (logs errors)
        """
        try:
            # Check if we should notify (async-safe)
            should_notify = await self._should_notify_async(entry)
            if not should_notify:
                return False

            # Get photos (async-safe)
            photos = await self._get_entry_photos_async(entry)
            if not photos:
                self.logger.info(f"Entry {entry.id}: No photos attached, skipping notification")
                return False

            # Determine target group
            group_id = self._get_target_group_id(entry)
            if not group_id:
                self.logger.warning(f"Entry {entry.id}: Unknown status '{entry.status}', cannot determine group")
                return False

            # Build caption (async-safe)
            caption = await self._format_caption_async(entry)

            # Send notification
            success = await self._send_media_album(group_id, photos, caption)

            if success:
                self.logger.info(
                    f"Entry {entry.id}: Successfully sent notification to group {group_id} with {len(photos)} photo(s)"
                )
            else:
                self.logger.warning(f"Entry {entry.id}: Failed to send notification to group {group_id}")

            return success

        except Exception as e:
            self.logger.error(
                f"Entry {entry.id if entry else 'unknown'}: Unexpected error in notify_group_about_entry: {e}",
                exc_info=True,
            )
            return False

    def _should_notify(self, entry: ContainerEntry) -> bool:
        """
        Check if entry should trigger a notification based on company config.

        Args:
            entry: ContainerEntry instance

        Returns:
            bool: True if should notify, False otherwise
        """
        # Check if company exists and has notifications enabled
        if not entry.company:
            return False

        # Check if company has notifications enabled and has a group configured
        return bool(entry.company.notifications_enabled and entry.company.telegram_group_id)

    def _get_target_group_id(self, entry: ContainerEntry) -> str | None:
        """
        Get Telegram group ID from company configuration.

        Args:
            entry: ContainerEntry instance

        Returns:
            str: Group chat ID from company config, or None if not configured
        """
        if entry.company and entry.company.telegram_group_id:
            return entry.company.telegram_group_id
        return None

    def _get_entry_photos(self, entry: ContainerEntry) -> list[FileAttachment]:
        """
        Fetch photos attached to the container entry.
        Returns up to 10 photos (Telegram media group limit).

        Args:
            entry: ContainerEntry instance

        Returns:
            List of FileAttachment objects with valid image files
        """
        try:
            content_type = ContentType.objects.get_for_model(ContainerEntry)
            attachments = FileAttachment.objects.filter(
                content_type=content_type,
                object_id=entry.id,
                attachment_type="container_photo",
                file__is_active=True,
            ).select_related("file")[:10]  # Telegram limit: 10 photos per album

            # Filter to only valid image files
            valid_photos = []
            for attachment in attachments:
                if attachment.file and attachment.file.file:
                    valid_photos.append(attachment)

            return valid_photos

        except Exception as e:
            self.logger.error(f"Entry {entry.id}: Error fetching photos: {e}", exc_info=True)
            return []

    def _format_caption(self, entry: ContainerEntry) -> str:
        """
        Format caption with entry details in Russian.

        Args:
            entry: ContainerEntry instance

        Returns:
            str: Formatted caption text
        """
        # Get display values (Russian)
        status_display = entry.get_status_display()
        transport_display = entry.get_transport_type_display()

        # Get company name for caption
        company_name = entry.company.name if entry.company else "Unknown"

        # Build caption lines
        lines = [
            f"✅ Новый контейнер ({company_name})",
            "",
            f"📦 Контейнер: {entry.container.container_number}",
            f"📏 Тип: {entry.container.iso_type}",
            f"📊 Статус: {status_display}",
            f"🚛 Транспорт: {transport_display}",
        ]

        # Add transport number if available
        if entry.transport_number:
            lines.append(f"🔢 Номер ТС: {entry.transport_number}")

        # Add train number if available
        if entry.entry_train_number:
            lines.append(f"🚂 Номер поезда: {entry.entry_train_number}")

        # Add manager name if available
        if entry.recorded_by:
            manager_name = entry.recorded_by.get_full_name() or entry.recorded_by.username
            lines.append(f"👤 Менеджер: {manager_name}")

        # Add entry time
        from django.utils import timezone

        entry_time_str = timezone.localtime(entry.entry_time).strftime("%d.%m.%Y %H:%M")
        lines.append(f"📅 Время: {entry_time_str}")

        # Add entry ID
        lines.append(f"🆔 ID: {entry.id}")

        return "\n".join(lines)

    async def _send_media_album(self, chat_id: str, photos: list[FileAttachment], caption: str) -> bool:
        """
        Send photos as media album to Telegram group.

        Args:
            chat_id: Telegram group chat ID
            photos: List of FileAttachment objects
            caption: Caption text for the album

        Returns:
            bool: True if sent successfully, False otherwise
        """
        bot = None
        try:
            # Check bot token
            if not self.bot_token:
                self.logger.error("TELEGRAM_BOT_TOKEN not configured in settings")
                return False

            # Create bot instance
            bot = Bot(token=self.bot_token)

            # Prepare media group
            media_group = []
            for idx, attachment in enumerate(photos):
                try:
                    # Get file path
                    file_path = attachment.file.file.path

                    # Create input file
                    input_file = FSInputFile(file_path)

                    # First photo gets caption, others don't
                    if idx == 0:
                        media_group.append(InputMediaPhoto(media=input_file, caption=caption))
                    else:
                        media_group.append(InputMediaPhoto(media=input_file))

                except Exception as e:
                    self.logger.warning(f"Failed to prepare photo {attachment.id}: {e}")
                    continue

            # Check if we have any photos to send
            if not media_group:
                self.logger.error("No valid photos to send after preparation")
                return False

            # Send media group
            await bot.send_media_group(chat_id=chat_id, media=media_group)

            return True

        except Exception as e:
            self.logger.error(f"Failed to send media album to group {chat_id}: {e}", exc_info=True)
            return False

        finally:
            # Clean up bot session
            if bot:
                try:
                    await bot.session.close()
                except Exception as e:
                    self.logger.debug(f"Error closing bot session: {e}")

    # Async-safe wrappers for database access
    async def _should_notify_async(self, entry: ContainerEntry) -> bool:
        """Async-safe wrapper for _should_notify that accesses database."""
        return await sync_to_async(self._should_notify)(entry)

    async def _get_entry_photos_async(self, entry: ContainerEntry) -> list[FileAttachment]:
        """Async-safe wrapper for _get_entry_photos that accesses database."""
        return await sync_to_async(self._get_entry_photos)(entry)

    async def _format_caption_async(self, entry: ContainerEntry) -> str:
        """Async-safe wrapper for _format_caption that accesses related objects."""
        return await sync_to_async(self._format_caption)(entry)

    # ========== Customer Notifications ==========

    async def notify_customer_vehicle_entered(self, vehicle_entry) -> bool:
        """
        Send notification to customer when their vehicle enters the terminal.
        Best-effort: logs errors but never raises exceptions.

        Args:
            vehicle_entry: VehicleEntry instance with customer

        Returns:
            bool: True if notification sent successfully, False otherwise
        """
        bot = None
        try:
            # Check if customer exists and has telegram_user_id
            customer = await sync_to_async(lambda: vehicle_entry.customer)()
            if not customer:
                self.logger.debug(f"VehicleEntry {vehicle_entry.id}: No customer, skipping notification")
                return False

            telegram_user_id = customer.telegram_user_id
            if not telegram_user_id:
                self.logger.debug(f"VehicleEntry {vehicle_entry.id}: Customer has no telegram_user_id")
                return False

            # Check bot token
            if not self.bot_token:
                self.logger.error("TELEGRAM_BOT_TOKEN not configured")
                return False

            # Get customer's language preference (default to Russian)
            # We'll use Redis to get the stored language, fallback to 'ru'
            language = await self._get_customer_language(telegram_user_id)

            # Format message
            from django.utils import timezone

            entry_time = vehicle_entry.entry_time or timezone.now()
            entry_time_str = timezone.localtime(entry_time).strftime("%d.%m.%Y %H:%M")

            from telegram_bot.translations import get_text

            message = get_text("customer_vehicle_entered", language).format(
                plate=vehicle_entry.license_plate, time=entry_time_str
            )

            # Create bot and send message
            bot = Bot(token=self.bot_token)
            await bot.send_message(chat_id=telegram_user_id, text=message, parse_mode="HTML")

            self.logger.info(
                f"VehicleEntry {vehicle_entry.id}: Sent entry notification to customer "
                f"{customer.first_name} ({telegram_user_id})"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"VehicleEntry {vehicle_entry.id if vehicle_entry else 'unknown'}: Failed to notify customer: {e}",
                exc_info=True,
            )
            return False

        finally:
            if bot:
                try:
                    await bot.session.close()
                except Exception:
                    pass

    async def notify_customer_vehicle_exited(self, vehicle_entry) -> bool:
        """
        Send notification to customer when their vehicle exits the terminal.
        Best-effort: logs errors but never raises exceptions.

        Args:
            vehicle_entry: VehicleEntry instance with customer

        Returns:
            bool: True if notification sent successfully, False otherwise
        """
        bot = None
        try:
            # Check if customer exists and has telegram_user_id
            customer = await sync_to_async(lambda: vehicle_entry.customer)()
            if not customer:
                return False

            telegram_user_id = customer.telegram_user_id
            if not telegram_user_id:
                return False

            if not self.bot_token:
                return False

            language = await self._get_customer_language(telegram_user_id)

            from django.utils import timezone

            exit_time = vehicle_entry.exit_time or timezone.now()
            exit_time_str = timezone.localtime(exit_time).strftime("%d.%m.%Y %H:%M")

            from telegram_bot.translations import get_text

            message = get_text("customer_vehicle_exited", language).format(
                plate=vehicle_entry.license_plate, time=exit_time_str
            )

            bot = Bot(token=self.bot_token)
            await bot.send_message(chat_id=telegram_user_id, text=message, parse_mode="HTML")

            self.logger.info(
                f"VehicleEntry {vehicle_entry.id}: Sent exit notification to customer "
                f"{customer.first_name} ({telegram_user_id})"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"VehicleEntry {vehicle_entry.id if vehicle_entry else 'unknown'}: "
                f"Failed to notify customer about exit: {e}",
                exc_info=True,
            )
            return False

        finally:
            if bot:
                try:
                    await bot.session.close()
                except Exception:
                    pass

    async def _get_customer_language(self, telegram_user_id: int) -> str:
        """
        Get customer's language preference from Redis FSM storage.
        Falls back to 'ru' if not found.

        Args:
            telegram_user_id: Telegram user ID

        Returns:
            str: Language code ('ru' or 'uz')
        """
        try:
            import redis

            redis_client = redis.Redis(
                host=getattr(settings, "REDIS_HOST", "localhost"),
                port=getattr(settings, "REDIS_PORT", 6379),
                db=getattr(settings, "REDIS_DB", 0),
                decode_responses=True,
            )

            # Try to get language from FSM state
            # The key format depends on how aiogram stores FSM data
            key = f"fsm:{telegram_user_id}:{telegram_user_id}:data"
            data = redis_client.get(key)

            if data:
                import json

                state_data = json.loads(data)
                return state_data.get("language", "ru")

            return "ru"

        except Exception as e:
            self.logger.debug(f"Could not get language from Redis: {e}")
            return "ru"
