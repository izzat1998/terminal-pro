"""
Telegram notification service for sending messages to users from Django context.
Bridges sync Django with async aiogram Bot API.
"""

import logging
import os

from aiogram import Bot
from aiogram.enums import ParseMode
from asgiref.sync import async_to_sync
from django.conf import settings

from telegram_bot.translations import get_text


logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """
    Service for sending Telegram notifications from Django sync context.
    Used to notify customers about vehicle status changes.
    """

    def __init__(self):
        self.bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None) or os.getenv(
            "TELEGRAM_BOT_TOKEN"
        )
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured - notifications disabled")

    async def _send_message(self, chat_id: int, text: str) -> bool:
        """
        Internal async method to send a Telegram message.

        Args:
            chat_id: Telegram user ID
            text: Message text (HTML format supported)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot_token:
            return False

        bot = Bot(token=self.bot_token)
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
            return False
        finally:
            await bot.session.close()

    def send_message(self, chat_id: int, text: str) -> bool:
        """
        Send a Telegram message (sync wrapper).

        Args:
            chat_id: Telegram user ID
            text: Message text (HTML format supported)

        Returns:
            True if sent successfully, False otherwise
        """
        # Use async_to_sync for proper event loop handling in any context
        return async_to_sync(self._send_message)(chat_id, text)

    def _get_customer_language(self, customer) -> str:
        """Get customer's preferred language, defaulting to Russian."""
        return getattr(customer, "language", "ru") or "ru"

    def notify_vehicle_checked_in(self, customer, license_plate: str, entry_time) -> bool:
        """
        Notify customer that their vehicle has been checked in.

        Args:
            customer: CustomUser instance (customer who created pre-order)
            license_plate: Vehicle license plate number
            entry_time: DateTime when vehicle entered

        Returns:
            True if notification sent, False otherwise
        """
        if not customer or not customer.telegram_user_id:
            logger.info(
                f"Cannot notify customer for {license_plate}: "
                f"no customer or telegram_user_id"
            )
            return False

        # Format time for display
        time_str = entry_time.strftime("%d.%m.%Y %H:%M")

        # Get message text in customer's preferred language
        lang = self._get_customer_language(customer)
        text = get_text(
            "customer_vehicle_entered",
            lang=lang,
            plate=license_plate,
            time=time_str,
        )

        success = self.send_message(customer.telegram_user_id, text)

        if success:
            logger.info(
                f"Sent check-in notification to customer {customer.id} "
                f"for vehicle {license_plate} (lang={lang})"
            )
        else:
            logger.warning(
                f"Failed to send check-in notification to customer {customer.id} "
                f"for vehicle {license_plate}"
            )

        return success

    def notify_vehicle_exited(self, customer, license_plate: str, exit_time) -> bool:
        """
        Notify customer that their vehicle has exited the terminal.

        Args:
            customer: CustomUser instance (customer who created pre-order)
            license_plate: Vehicle license plate number
            exit_time: DateTime when vehicle exited

        Returns:
            True if notification sent, False otherwise
        """
        if not customer or not customer.telegram_user_id:
            logger.info(
                f"Cannot notify customer for {license_plate} exit: "
                f"no customer or telegram_user_id"
            )
            return False

        # Format time for display
        time_str = exit_time.strftime("%d.%m.%Y %H:%M")

        # Get message text in customer's preferred language
        lang = self._get_customer_language(customer)
        text = get_text(
            "customer_vehicle_exited",
            lang=lang,
            plate=license_plate,
            time=time_str,
        )

        success = self.send_message(customer.telegram_user_id, text)

        if success:
            logger.info(
                f"Sent exit notification to customer {customer.id} "
                f"for vehicle {license_plate} (lang={lang})"
            )
        else:
            logger.warning(
                f"Failed to send exit notification to customer {customer.id} "
                f"for vehicle {license_plate}"
            )

        return success

    def notify_vehicle_cancelled(self, customer, license_plate: str) -> bool:
        """
        Notify customer that their vehicle entry has been cancelled.

        Args:
            customer: CustomUser instance (customer who created pre-order)
            license_plate: Vehicle license plate number

        Returns:
            True if notification sent, False otherwise
        """
        if not customer or not customer.telegram_user_id:
            logger.info(
                f"Cannot notify customer for {license_plate} cancellation: "
                f"no customer or telegram_user_id"
            )
            return False

        # Get message text in customer's preferred language
        lang = self._get_customer_language(customer)
        text = get_text(
            "customer_vehicle_cancelled",
            lang=lang,
            plate=license_plate,
        )

        success = self.send_message(customer.telegram_user_id, text)

        if success:
            logger.info(
                f"Sent cancellation notification to customer {customer.id} "
                f"for vehicle {license_plate} (lang={lang})"
            )
        else:
            logger.warning(
                f"Failed to send cancellation notification to customer {customer.id} "
                f"for vehicle {license_plate}"
            )

        return success
