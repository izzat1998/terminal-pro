"""
Container Event Service - Business logic for container lifecycle event tracking.

Provides event creation, timeline queries, and initial event generation for existing data.
"""

from datetime import datetime
from typing import Optional

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.core.services.base_service import BaseService

from ..models import ContainerEntry, ContainerEvent


class ContainerEventService(BaseService):
    """
    Service for managing container lifecycle events.

    Handles:
    - Event creation with validation
    - Timeline queries for containers
    - Initial event generation for existing data
    """

    # Valid event types
    VALID_EVENT_TYPES = [
        "ENTRY_CREATED",
        "STATUS_CHANGED",
        "POSITION_ASSIGNED",
        "POSITION_REMOVED",
        "CRANE_OPERATION",
        "WORK_ORDER_CREATED",
        "WORK_ORDER_COMPLETED",
        "EXIT_RECORDED",
    ]

    # Valid sources
    VALID_SOURCES = ["API", "TELEGRAM_BOT", "EXCEL_IMPORT", "SYSTEM"]

    def create_event(
        self,
        container_entry: ContainerEntry,
        event_type: str,
        details: dict,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
        event_time: Optional[datetime] = None,
    ) -> ContainerEvent:
        """
        Create a new event for a container.

        Args:
            container_entry: The container this event belongs to
            event_type: One of EVENT_TYPE_CHOICES
            details: Event-specific data dictionary
            performed_by: User who triggered the event (optional)
            source: How the event was triggered (API, TELEGRAM_BOT, etc.)
            event_time: When the event occurred (defaults to now)

        Returns:
            Created ContainerEvent instance

        Raises:
            ValueError: If event_type or source is invalid
        """
        if event_type not in self.VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type: {event_type}")

        if source not in self.VALID_SOURCES:
            raise ValueError(f"Invalid source: {source}")

        if event_time is None:
            event_time = timezone.now()

        event = ContainerEvent.objects.create(
            container_entry=container_entry,
            event_type=event_type,
            event_time=event_time,
            performed_by=performed_by,
            source=source,
            details=details or {},
        )

        self.logger.info(
            f"Created {event_type} event for container "
            f"{container_entry.container.container_number} (entry_id={container_entry.id})"
        )

        return event

    def get_container_timeline(
        self,
        container_entry: ContainerEntry,
    ) -> QuerySet[ContainerEvent]:
        """
        Get all events for a container, ordered chronologically.

        Args:
            container_entry: The container to get events for

        Returns:
            QuerySet of ContainerEvent ordered by event_time (oldest first)
        """
        return (
            ContainerEvent.objects.filter(container_entry=container_entry)
            .select_related("performed_by")
            .order_by("event_time", "created_at")
        )

    def create_entry_created_event(
        self,
        container_entry: ContainerEntry,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create ENTRY_CREATED event with standard details."""
        details = {
            "status": container_entry.status,
            "transport_type": container_entry.transport_type,
            "transport_number": container_entry.transport_number or "",
            "entry_train_number": container_entry.entry_train_number or "",
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="ENTRY_CREATED",
            details=details,
            performed_by=performed_by,
            source=source,
            event_time=container_entry.entry_time,
        )

    def create_status_changed_event(
        self,
        container_entry: ContainerEntry,
        old_status: str,
        new_status: str,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
        reason: str = "",
    ) -> ContainerEvent:
        """Helper to create STATUS_CHANGED event."""
        details = {
            "old_status": old_status,
            "new_status": new_status,
        }
        if reason:
            details["reason"] = reason
        return self.create_event(
            container_entry=container_entry,
            event_type="STATUS_CHANGED",
            details=details,
            performed_by=performed_by,
            source=source,
        )

    def create_position_assigned_event(
        self,
        container_entry: ContainerEntry,
        zone: str,
        row: int,
        bay: int,
        tier: int,
        sub_slot: str,
        auto_assigned: bool = False,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create POSITION_ASSIGNED event."""
        coordinate = f"{zone}-R{row:02d}-B{bay:02d}-T{tier}-{sub_slot}"
        details = {
            "zone": zone,
            "row": row,
            "bay": bay,
            "tier": tier,
            "sub_slot": sub_slot,
            "coordinate": coordinate,
            "auto_assigned": auto_assigned,
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="POSITION_ASSIGNED",
            details=details,
            performed_by=performed_by,
            source=source,
        )

    def create_position_removed_event(
        self,
        container_entry: ContainerEntry,
        previous_zone: str,
        previous_row: int,
        previous_bay: int,
        previous_tier: int,
        previous_sub_slot: str,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create POSITION_REMOVED event."""
        coordinate = f"{previous_zone}-R{previous_row:02d}-B{previous_bay:02d}-T{previous_tier}-{previous_sub_slot}"
        details = {
            "previous_zone": previous_zone,
            "previous_row": previous_row,
            "previous_bay": previous_bay,
            "previous_tier": previous_tier,
            "previous_sub_slot": previous_sub_slot,
            "previous_coordinate": coordinate,
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="POSITION_REMOVED",
            details=details,
            performed_by=performed_by,
            source=source,
        )

    def create_crane_operation_event(
        self,
        container_entry: ContainerEntry,
        operation_date: datetime,
        crane_operation_id: int,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create CRANE_OPERATION event."""
        details = {
            "operation_date": operation_date.isoformat(),
            "crane_operation_id": crane_operation_id,
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="CRANE_OPERATION",
            details=details,
            performed_by=performed_by,
            source=source,
            event_time=operation_date,
        )

    def create_work_order_created_event(
        self,
        container_entry: ContainerEntry,
        order_number: str,
        target_coordinate: str,
        priority: str,
        work_order_id: int,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create WORK_ORDER_CREATED event."""
        details = {
            "order_number": order_number,
            "target_coordinate": target_coordinate,
            "priority": priority,
            "work_order_id": work_order_id,
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="WORK_ORDER_CREATED",
            details=details,
            performed_by=performed_by,
            source=source,
        )

    def create_work_order_completed_event(
        self,
        container_entry: ContainerEntry,
        order_number: str,
        work_order_id: int,
        completed_at: datetime,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create WORK_ORDER_COMPLETED event."""
        details = {
            "order_number": order_number,
            "work_order_id": work_order_id,
            "completed_at": completed_at.isoformat(),
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="WORK_ORDER_COMPLETED",
            details=details,
            performed_by=performed_by,
            source=source,
            event_time=completed_at,
        )

    def create_exit_recorded_event(
        self,
        container_entry: ContainerEntry,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create EXIT_RECORDED event."""
        details = {
            "exit_transport_type": container_entry.exit_transport_type or "",
            "exit_transport_number": container_entry.exit_transport_number or "",
            "exit_train_number": container_entry.exit_train_number or "",
            "destination_station": container_entry.destination_station or "",
            "dwell_time_days": container_entry.dwell_time_days,
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="EXIT_RECORDED",
            details=details,
            performed_by=performed_by,
            source=source,
            event_time=container_entry.exit_date,
        )
