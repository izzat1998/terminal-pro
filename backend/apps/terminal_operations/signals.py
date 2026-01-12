"""
Django signals for terminal_operations app.
Handles automatic notifications when entries are created.
"""

import asyncio
import logging
import threading

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.terminal_operations.models import ContainerEntry


logger = logging.getLogger(__name__)


@receiver(post_save, sender=ContainerEntry)
def notify_telegram_groups_on_entry(sender, instance, created, **kwargs):
    """
    Send Telegram notification to appropriate group when a new entry is created.
    Runs asynchronously in background thread to avoid blocking the save operation.

    Uses transaction.on_commit() to ensure notifications are only sent after
    the database transaction successfully commits.

    Args:
        sender: Model class (ContainerEntry)
        instance: ContainerEntry instance that was saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional signal arguments
    """
    # Only trigger on creation, not updates
    if not created:
        return

    # Import here to avoid circular imports
    from apps.terminal_operations.services.telegram_notification_service import (
        TelegramNotificationService,
    )

    def send_notification_in_background():
        """Run async notification in new event loop (background thread)."""
        try:
            # Re-fetch entry with all required relationships to avoid cache misses
            # This ensures container_owner, container, recorded_by, and company are pre-loaded
            entry = ContainerEntry.objects.select_related("container_owner", "container", "recorded_by", "company").get(
                pk=instance.pk
            )

            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Create service and send notification
                service = TelegramNotificationService()
                loop.run_until_complete(service.notify_group_about_entry(entry))
            finally:
                # Clean up event loop
                loop.close()

        except Exception as e:
            logger.error(
                f"Failed to send background notification for entry {getattr(instance, 'id', 'unknown')}: {e}",
                exc_info=True,
            )

    def schedule_notification():
        """Schedule notification to run after transaction commits."""
        # Launch background thread (daemon so it doesn't block shutdown)
        thread = threading.Thread(
            target=send_notification_in_background,
            daemon=True,
            name=f"telegram-notify-{instance.id}",
        )
        thread.start()
        logger.debug(f"Entry {instance.id}: Launched background notification thread")

    # Only send notification after transaction commits successfully
    transaction.on_commit(schedule_notification)
