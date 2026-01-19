"""
Crane Operation Service.

Handles business logic for crane operation management.
"""

from datetime import datetime
from typing import Optional

from django.db import transaction
from django.db.models import QuerySet

from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService

from ..models import ContainerEntry, CraneOperation


class CraneOperationService(BaseService):
    """
    Service for managing crane operations on container entries.
    """

    def get_operations_for_entry(self, entry_id: int) -> QuerySet[CraneOperation]:
        """
        Get all crane operations for a specific container entry.

        Args:
            entry_id: Container entry ID

        Returns:
            QuerySet of CraneOperation objects
        """
        return (
            CraneOperation.objects.select_related(
                "container_entry", "container_entry__container"
            )
            .filter(container_entry_id=entry_id)
            .order_by("-operation_date")
        )

    def _get_container_entry(self, entry_id: int) -> ContainerEntry:
        """
        Get container entry by ID or raise error.

        Args:
            entry_id: Container entry ID

        Returns:
            ContainerEntry instance

        Raises:
            BusinessLogicError: If entry not found
        """
        try:
            return ContainerEntry.objects.get(id=entry_id)
        except ContainerEntry.DoesNotExist:
            raise BusinessLogicError(
                message=f"Запись контейнера с ID {entry_id} не найдена",
                error_code="CONTAINER_ENTRY_NOT_FOUND",
            )

    @transaction.atomic
    def create_operation(
        self,
        entry_id: int,
        operation_date: datetime,
    ) -> CraneOperation:
        """
        Create a new crane operation for a container entry.

        Args:
            entry_id: Container entry ID
            operation_date: Date/time of the crane operation

        Returns:
            Created CraneOperation instance

        Raises:
            BusinessLogicError: If entry_id is missing or entry not found
        """
        if not entry_id:
            raise BusinessLogicError(
                message="Необходимо указать ID записи контейнера",
                error_code="MISSING_PARAMETER",
            )

        entry = self._get_container_entry(entry_id)

        operation = CraneOperation.objects.create(
            container_entry=entry,
            operation_date=operation_date,
        )

        self.logger.info(
            f"Created crane operation for entry {entry_id} "
            f"(container: {entry.container.container_number})"
        )

        return operation

    @transaction.atomic
    def delete_operation(self, operation_id: int) -> bool:
        """
        Delete a crane operation.

        Args:
            operation_id: Crane operation ID

        Returns:
            True if deleted successfully

        Raises:
            BusinessLogicError: If operation not found
        """
        try:
            operation = CraneOperation.objects.select_related(
                "container_entry__container"
            ).get(id=operation_id)
        except CraneOperation.DoesNotExist:
            raise BusinessLogicError(
                message=f"Крановая операция с ID {operation_id} не найдена",
                error_code="CRANE_OPERATION_NOT_FOUND",
            )

        container_number = operation.container_entry.container.container_number
        operation.delete()

        self.logger.info(
            f"Deleted crane operation {operation_id} (container: {container_number})"
        )

        return True

    def get_operations_queryset(
        self,
        entry_id: Optional[int] = None,
    ) -> QuerySet[CraneOperation]:
        """
        Get crane operations queryset with optional filtering.

        Args:
            entry_id: Optional container entry ID to filter by

        Returns:
            QuerySet of CraneOperation objects
        """
        queryset = CraneOperation.objects.select_related(
            "container_entry", "container_entry__container"
        ).all()

        if entry_id:
            queryset = queryset.filter(container_entry_id=entry_id)

        return queryset
