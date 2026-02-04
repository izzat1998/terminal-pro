"""
Service for creating container entries directly via Django ORM
"""

import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional


if TYPE_CHECKING:
    from apps.accounts.models import CustomUser

from django.db import transaction
from django.utils import timezone

from apps.containers.models import Container
from apps.core.exceptions import BusinessLogicError, DuplicateEntryError
from apps.files.models import File, FileAttachment
from apps.terminal_operations.models import ContainerEntry, CraneOperation


logger = logging.getLogger(__name__)


class BotEntryService:
    """Service for bot to create container entries using direct Django access"""

    @transaction.atomic
    def create_entry(
        self,
        container_number: str,
        container_iso_type: str,
        status: str,
        transport_type: str,
        transport_number: str = "",
        photos: list | None = None,
        container_owner_id: int | None = None,
        manager: Optional["CustomUser"] = None,
    ) -> ContainerEntry:
        """
        Create container entry with photos and optional container owner.
        Uses direct Django ORM access.

        Args:
            manager: CustomUser instance (manager) who is creating this entry via Telegram bot
        """
        # Normalize container number
        container_number = container_number.upper()

        # Get or create container (container_number is unique)
        container, created = Container.objects.get_or_create(
            container_number=container_number, defaults={"iso_type": container_iso_type}
        )

        # Update ISO type if changed
        if not created and container.iso_type != container_iso_type:
            container.iso_type = container_iso_type
            container.save(update_fields=["iso_type"])

        # Check for duplicate entries (same container, same day)
        today = timezone.now().date()
        if ContainerEntry.objects.filter(
            container=container, entry_time__date=today
        ).exists():
            raise DuplicateEntryError(container_number)

        # Create entry with manager reference (manager is a CustomUser with user_type='manager')
        entry = ContainerEntry.objects.create(
            container=container,
            status=status,
            transport_type=transport_type,
            transport_number=transport_number,
            container_owner_id=container_owner_id,  # Can be None
            recorded_by=manager,  # Manager (CustomUser) who created this entry via bot
        )

        # Process photos if provided
        if photos:
            logger.info(f"Processing {len(photos)} photos for entry {entry.id}")
            for idx, photo_file in enumerate(photos, 1):
                try:
                    logger.debug(
                        f"Uploading photo {idx}/{len(photos)}: {photo_file.name}"
                    )

                    # Create File object
                    file_obj = File.objects.create_from_upload(
                        uploaded_file=photo_file,
                        category_code="container_image",
                        user=None,
                        is_public=False,
                    )

                    logger.debug(f"Created File object: {file_obj.id}")

                    # Attach to entry
                    FileAttachment.objects.create(
                        file=file_obj,
                        content_object=entry,
                        attachment_type="container_photo",
                        description="Uploaded via Telegram bot",
                    )

                    logger.info(f"Photo {idx} uploaded successfully: {file_obj.id}")

                except Exception as e:
                    logger.error(
                        f"Error uploading photo {idx}: {e!s}", exc_info=True
                    )
                    # Re-raise the exception so the transaction fails
                    raise
        else:
            logger.info(f"No photos provided for entry {entry.id}")

        return entry

    def validate_container_number(self, number: str) -> bool:
        """
        Validate container number format (4 letters + 7 digits).
        Accepts various input formats: "MSKU1234567", "MSKU 1234567", "MSKU | 1234567".
        """
        # Remove all non-alphanumeric characters and normalize
        cleaned = re.sub(r'[^A-Za-z0-9]', '', number).upper()
        pattern = r"^[A-Z]{4}[0-9]{7}$"
        return bool(re.match(pattern, cleaned))

    def normalize_container_number(self, number: str) -> str:
        """
        Normalize container number by removing all non-alphanumeric characters
        and converting to uppercase.
        Examples:
            "MSKU 1234567" -> "MSKU1234567"
            "TEMU | 1234567" -> "TEMU1234567"
            "temu-123-4567" -> "TEMU1234567"
        """
        return re.sub(r'[^A-Za-z0-9]', '', number).upper()

    def check_active_entry(self, container_number: str) -> ContainerEntry | None:
        """
        Check if container has an active entry (no exit date).
        Returns the active entry if found, otherwise None.
        """
        container_number = container_number.upper()

        # Query for active entries (no exit_date means container is still on terminal)
        # Use select_related to eagerly load related objects (container, container_owner)
        active_entry = (
            ContainerEntry.objects.filter(
                container__container_number=container_number, exit_date__isnull=True
            )
            .select_related("container", "container_owner")
            .first()
        )

        return active_entry

    def check_exited_entry(self, container_number: str) -> ContainerEntry | None:
        """
        Check if container has a recent exited entry (exit_date is set).
        Returns the most recent exited entry if found, otherwise None.
        """
        container_number = container_number.upper()

        exited_entry = (
            ContainerEntry.objects.filter(
                container__container_number=container_number,
                exit_date__isnull=False,
            )
            .select_related("container")
            .order_by("-exit_date")
            .first()
        )

        return exited_entry

    @transaction.atomic
    def update_exit(
        self,
        entry_id: int,
        exit_data: dict[str, Any],
        photos: list | None = None,
        crane_operations: list[dict] | None = None,
        manager: Optional["CustomUser"] = None,
    ) -> ContainerEntry:
        """
        Update container entry with exit information.

        Args:
            entry_id: ID of the ContainerEntry to update
            exit_data: Dict containing exit information:
                - exit_date: datetime when container exits (required)
                - exit_transport_type: TRUCK/WAGON/TRAIN (required)
                - exit_transport_number: vehicle identifier (required)
                - exit_train_number: train number (optional, if TRAIN type)
                - destination_station: where container is going (optional)
            photos: Optional list of photo files (exit photos)
            crane_operations: Optional list of dicts with 'operation_date' key
            manager: CustomUser instance (for audit purposes)

        Returns:
            Updated ContainerEntry instance

        Raises:
            ContainerEntry.DoesNotExist: If entry not found
        """
        try:
            entry = ContainerEntry.objects.select_for_update().get(id=entry_id)
        except ContainerEntry.DoesNotExist:
            logger.error(f"Entry with id {entry_id} not found")
            raise

        # Guard against double-exit (race condition between two managers)
        if entry.exit_date is not None:
            raise BusinessLogicError(
                "Выезд для этого контейнера уже зарегистрирован",
                code="ALREADY_EXITED",
            )

        # Validate exit_date is not before entry_time
        exit_date = exit_data.get("exit_date")
        if exit_date and exit_date < entry.entry_time:
            raise BusinessLogicError(
                "Дата выезда не может быть раньше даты въезда",
                code="EXIT_BEFORE_ENTRY",
            )

        # Update exit fields
        entry.exit_date = exit_data.get("exit_date")
        entry.exit_transport_type = exit_data.get("exit_transport_type")
        entry.exit_transport_number = exit_data.get("exit_transport_number", "")
        entry.exit_train_number = exit_data.get("exit_train_number", "")
        entry.save(
            update_fields=[
                "exit_date",
                "exit_transport_type",
                "exit_transport_number",
                "exit_train_number",
            ]
        )

        logger.info(f"Updated exit information for entry {entry_id}")

        # Process exit photos if provided
        if photos:
            logger.info(f"Processing {len(photos)} exit photos for entry {entry_id}")
            for idx, photo_file in enumerate(photos, 1):
                try:
                    logger.debug(
                        f"Uploading exit photo {idx}/{len(photos)}: {photo_file.name}"
                    )

                    # Create File object
                    file_obj = File.objects.create_from_upload(
                        uploaded_file=photo_file,
                        category_code="container_image",
                        user=None,
                        is_public=False,
                    )

                    logger.debug(f"Created File object: {file_obj.id}")

                    # Attach to entry as exit photo
                    FileAttachment.objects.create(
                        file=file_obj,
                        content_object=entry,
                        attachment_type="container_exit_photo",
                        description="Exit photo uploaded via Telegram bot",
                    )

                    logger.info(
                        f"Exit photo {idx} uploaded successfully: {file_obj.id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error uploading exit photo {idx}: {e!s}", exc_info=True
                    )
                    raise

        # Create crane operations if provided
        if crane_operations:
            logger.info(
                f"Creating {len(crane_operations)} crane operations for entry {entry_id}"
            )
            for op_data in crane_operations:
                try:
                    operation_date = op_data.get("operation_date")
                    if operation_date:
                        CraneOperation.objects.create(
                            container_entry=entry, operation_date=operation_date
                        )
                        logger.info(f"Created crane operation: {operation_date}")
                except Exception as e:
                    logger.error(
                        f"Error creating crane operation: {e!s}", exc_info=True
                    )
                    raise

        logger.info(f"Successfully updated exit for entry {entry_id}")
        return entry

    @transaction.atomic
    def add_crane_operation(
        self, entry_id: int, operation_date: datetime
    ) -> tuple[CraneOperation, int]:
        """
        Add a crane operation to a container entry.

        Args:
            entry_id: ID of the ContainerEntry
            operation_date: DateTime of the crane operation

        Returns:
            Tuple of (CraneOperation instance, total count of operations for entry)

        Raises:
            ContainerEntry.DoesNotExist: If entry not found
        """
        try:
            entry = ContainerEntry.objects.get(id=entry_id)
        except ContainerEntry.DoesNotExist:
            logger.error(f"Entry with id {entry_id} not found")
            raise

        # Create the crane operation
        operation = CraneOperation.objects.create(
            container_entry=entry, operation_date=operation_date
        )

        # Get total count of operations for this entry
        total_count = CraneOperation.objects.filter(container_entry=entry).count()

        logger.info(
            f"Added crane operation to entry {entry_id} at {operation_date}. Total: {total_count}"
        )
        return operation, total_count
