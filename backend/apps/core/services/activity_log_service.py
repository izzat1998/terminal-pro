from django.contrib.contenttypes.models import ContentType

from apps.core.models import TelegramActivityLog
from apps.core.services.base_service import BaseService


class ActivityLogService(BaseService):
    """
    Service for logging Telegram bot activities.
    Provides a simple interface for handlers to log actions.
    """

    def log_container_entry_created(
        self, user, telegram_user_id, container_entry, details=None
    ):
        """Log when a manager creates a container entry."""
        return self._log(
            user=user,
            user_type="manager",
            telegram_user_id=telegram_user_id,
            action="container_entry_created",
            related_object=container_entry,
            details=details or self._entry_details(container_entry),
        )

    def log_container_exit_recorded(
        self, user, telegram_user_id, container_entry, details=None
    ):
        """Log when a manager records a container exit."""
        return self._log(
            user=user,
            user_type="manager",
            telegram_user_id=telegram_user_id,
            action="container_exit_recorded",
            related_object=container_entry,
            details=details or self._exit_details(container_entry),
        )

    def log_crane_operation_added(
        self, user, telegram_user_id, crane_operation, details=None
    ):
        """Log when a manager adds a crane operation."""
        return self._log(
            user=user,
            user_type="manager",
            telegram_user_id=telegram_user_id,
            action="crane_operation_added",
            related_object=crane_operation,
            details=details
            or {
                "container_number": crane_operation.container_entry.container.container_number,
                "operation_date": str(crane_operation.operation_date),
            },
        )

    def log_preorder_created(self, user, telegram_user_id, preorder, details=None):
        """Log when a customer creates a pre-order."""
        return self._log(
            user=user,
            user_type="customer",
            telegram_user_id=telegram_user_id,
            action="preorder_created",
            related_object=preorder,
            details=details or self._preorder_details(preorder),
        )

    def log_preorder_cancelled(self, user, telegram_user_id, preorder, details=None):
        """Log when a customer cancels a pre-order."""
        return self._log(
            user=user,
            user_type="customer",
            telegram_user_id=telegram_user_id,
            action="preorder_cancelled",
            related_object=preorder,
            details=details or self._preorder_details(preorder),
        )

    def log_error(
        self, user, user_type, telegram_user_id, action, error_message, details=None
    ):
        """Log a failed action."""
        return self._log(
            user=user,
            user_type=user_type,
            telegram_user_id=telegram_user_id,
            action=action,
            related_object=None,
            details=details or {},
            success=False,
            error_message=error_message,
        )

    def update_group_notification_status(
        self, activity_log_id: int, status: str, error_message: str = ""
    ) -> None:
        """Update group notification status for an activity log entry."""
        TelegramActivityLog.objects.filter(pk=activity_log_id).update(
            group_notification_status=status,
            group_notification_error=error_message,
        )
        self.logger.debug(
            f"Updated group notification status for log {activity_log_id}: {status}"
        )

    def _log(
        self,
        user,
        user_type,
        telegram_user_id,
        action,
        related_object=None,
        details=None,
        success=True,
        error_message="",
    ):
        """Internal method to create a log entry."""
        content_type = (
            ContentType.objects.get_for_model(related_object)
            if related_object
            else None
        )
        object_id = related_object.pk if related_object else None

        log_entry = TelegramActivityLog.objects.create(
            user=user,
            user_type=user_type,
            telegram_user_id=telegram_user_id,
            action=action,
            content_type=content_type,
            object_id=object_id,
            details=details or {},
            success=success,
            error_message=error_message,
        )

        self.logger.info(
            f"Activity logged: {action} by {user} (telegram_id={telegram_user_id})"
        )
        return log_entry

    def _entry_details(self, entry):
        """Extract details from a ContainerEntry for logging."""
        return {
            "container_number": entry.container.container_number,
            "status": entry.status,
            "transport_type": entry.transport_type,
            "transport_number": entry.transport_number or "",
        }

    def _exit_details(self, entry):
        """Extract exit details from a ContainerEntry."""
        return {
            "container_number": entry.container.container_number,
            "exit_date": str(entry.exit_date) if entry.exit_date else "",
            "exit_transport_type": entry.exit_transport_type or "",
            "exit_transport_number": entry.exit_transport_number or "",
        }

    def _preorder_details(self, preorder):
        """Extract details from a PreOrder for logging."""
        return {
            "plate_number": preorder.plate_number,
            "operation_type": preorder.operation_type,
            "status": preorder.status,
            "batch_id": preorder.batch_id or "",
        }
