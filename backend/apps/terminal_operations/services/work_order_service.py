"""
Work Order Service - Business logic for container placement work orders.

Manages the assignment, tracking, and completion of placement tasks
for yard managers in the Telegram Mini App.
"""

from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService
from apps.terminal_operations.models import ContainerEntry, TerminalVehicle, WorkOrder

from .container_event_service import ContainerEventService
from .placement_service import PlacementService


# Custom exceptions for work orders
class WorkOrderNotFoundError(BusinessLogicError):
    """Raised when work order is not found."""

    def __init__(self, order_id: int):
        super().__init__(
            message=f"Наряд #{order_id} не найден",
            error_code="WORK_ORDER_NOT_FOUND",
            details={"work_order_id": order_id},
        )


class WorkOrderAlreadyExistsError(BusinessLogicError):
    """Raised when container already has an active work order."""

    def __init__(self, container_number: str, order_number: str):
        super().__init__(
            message=f"Контейнер {container_number} уже имеет активный наряд {order_number}",
            error_code="WORK_ORDER_EXISTS",
            details={
                "container_number": container_number,
                "existing_order_number": order_number,
            },
        )


class WorkOrderService(BaseService):
    """
    Service for managing container placement work orders.

    Handles the full lifecycle of work orders:
    - Creation with auto-suggested positions
    - Assignment to yard managers
    - Completion with position confirmation
    """

    def __init__(self):
        super().__init__()
        self.placement_service = PlacementService()
        self._event_service = None

    @property
    def event_service(self):
        if self._event_service is None:
            self._event_service = ContainerEventService()
        return self._event_service

    def create_work_order(
        self,
        container_entry_id: int,
        zone: Optional[str] = None,
        row: Optional[int] = None,
        bay: Optional[int] = None,
        tier: Optional[int] = None,
        sub_slot: str = "A",
        priority: str = "MEDIUM",
        assigned_to_vehicle_id: Optional[int] = None,
        created_by: Optional[CustomUser] = None,
        notes: str = "",
    ) -> WorkOrder:
        """
        Create a new work order for container placement.

        If position is not specified, uses PlacementService to auto-suggest.

        Args:
            container_entry_id: Container to be placed
            zone, row, bay, tier, sub_slot: Target position (optional, auto-suggested if not provided)
            priority: Order priority (LOW, MEDIUM, HIGH, URGENT)
            assigned_to_vehicle_id: Terminal vehicle to assign (optional)
            created_by: User creating the order
            notes: Additional notes

        Returns:
            Created WorkOrder

        Raises:
            WorkOrderAlreadyExistsError: If container has active work order
            BusinessLogicError: If container not found or invalid position
        """
        # Get container entry
        try:
            entry = ContainerEntry.objects.select_related("container").get(
                id=container_entry_id
            )
        except ContainerEntry.DoesNotExist:
            raise BusinessLogicError(
                message=f"Запись контейнера #{container_entry_id} не найдена",
                error_code="CONTAINER_ENTRY_NOT_FOUND",
            )

        # Check for existing active work order
        existing_order = WorkOrder.objects.filter(
            container_entry=entry,
            status="PENDING",
        ).first()

        if existing_order:
            raise WorkOrderAlreadyExistsError(
                entry.container.container_number,
                existing_order.order_number,
            )

        # If position not specified, auto-suggest
        if zone is None:
            suggestion = self.placement_service.suggest_position(
                container_entry_id=container_entry_id,
                zone_preference=None,
            )
            pos = suggestion["suggested_position"]
            zone = pos["zone"]
            row = pos["row"]
            bay = pos["bay"]
            tier = pos["tier"]
            sub_slot = pos["sub_slot"]

        # Validate priority
        valid_priorities = ["LOW", "MEDIUM", "HIGH", "URGENT"]
        if priority not in valid_priorities:
            raise BusinessLogicError(
                message=f"Недопустимый приоритет: {priority}",
                error_code="INVALID_PRIORITY",
            )

        # Create work order
        work_order = WorkOrder(
            container_entry=entry,
            status="PENDING",
            priority=priority,
            target_zone=zone,
            target_row=row,
            target_bay=bay,
            target_tier=tier,
            target_sub_slot=sub_slot,
            created_by=created_by,
            notes=notes,
        )

        # Assign to vehicle if specified
        if assigned_to_vehicle_id:
            try:
                vehicle = TerminalVehicle.objects.get(
                    id=assigned_to_vehicle_id,
                    is_active=True,
                )
                work_order.assigned_to_vehicle = vehicle
            except TerminalVehicle.DoesNotExist:
                raise BusinessLogicError(
                    message=f"Техника #{assigned_to_vehicle_id} не найдена",
                    error_code="VEHICLE_NOT_FOUND",
                )

        work_order.save()

        # Emit WORK_ORDER_CREATED event
        self.event_service.create_work_order_created_event(
            container_entry=entry,
            order_number=work_order.order_number,
            target_coordinate=work_order.target_coordinate_string,
            priority=priority,
            work_order_id=work_order.id,
            performed_by=created_by,
        )

        self.logger.info(
            f"Created work order {work_order.order_number} for container "
            f"{entry.container.container_number} → {work_order.target_coordinate_string}"
        )

        return work_order

    def assign_to_vehicle(self, work_order_id: int, vehicle_id: int) -> WorkOrder:
        """Assign a work order to a terminal vehicle."""
        work_order = self._get_work_order(work_order_id)

        if work_order.status != "PENDING":
            raise BusinessLogicError(
                message="Только ожидающие наряды можно назначить",
                error_code="INVALID_STATUS",
            )

        try:
            vehicle = TerminalVehicle.objects.get(id=vehicle_id, is_active=True)
        except TerminalVehicle.DoesNotExist:
            raise BusinessLogicError(
                message=f"Техника #{vehicle_id} не найдена или неактивна",
                error_code="VEHICLE_NOT_FOUND",
            )

        work_order.assigned_to_vehicle = vehicle
        work_order.save(update_fields=["assigned_to_vehicle", "updated_at"])

        self.logger.info(f"Assigned work order {work_order.order_number} to vehicle {vehicle.name}")
        return work_order

    @transaction.atomic
    def complete_order(
        self,
        work_order_id: int,
        vehicle_id: Optional[int] = None,
        operator: Optional[CustomUser] = None,
    ) -> WorkOrder:
        """Complete a work order - container is physically placed."""
        work_order = self._get_work_order(work_order_id)

        if work_order.status != "PENDING":
            raise BusinessLogicError(
                message="Только ожидающие наряды можно завершить",
                error_code="INVALID_STATUS",
            )

        # If vehicle_id provided, validate assignment
        if vehicle_id and work_order.assigned_to_vehicle_id != vehicle_id:
            raise BusinessLogicError(
                message="Наряд не назначен этой технике",
                error_code="NOT_ASSIGNED_TO_VEHICLE",
            )

        # Create actual container position via PlacementService
        self.placement_service.assign_position(
            container_entry_id=work_order.container_entry_id,
            zone=work_order.target_zone,
            row=work_order.target_row,
            bay=work_order.target_bay,
            tier=work_order.target_tier,
            sub_slot=work_order.target_sub_slot,
            auto_assigned=False,
        )

        # Update work order
        work_order.status = "COMPLETED"
        work_order.completed_at = timezone.now()
        work_order.save(update_fields=["status", "completed_at", "updated_at"])

        # Emit WORK_ORDER_COMPLETED event
        self.event_service.create_work_order_completed_event(
            container_entry=work_order.container_entry,
            order_number=work_order.order_number,
            work_order_id=work_order.id,
            completed_at=work_order.completed_at,
            performed_by=operator,
        )

        operator_name = operator.get_full_name() if operator else "Operator"
        self.logger.info(f"Work order {work_order.order_number} completed by {operator_name}")
        return work_order

    def get_vehicle_orders(self, vehicle_id: int, include_completed: bool = False) -> list:
        """Get work orders assigned to a specific vehicle."""
        queryset = (
            WorkOrder.objects.filter(assigned_to_vehicle_id=vehicle_id)
            .select_related("container_entry__container", "container_entry__company", "assigned_to_vehicle")
            .order_by("-priority", "-created_at")
        )
        if not include_completed:
            queryset = queryset.filter(status="PENDING")
        return queryset

    def get_pending_orders(self) -> list:
        """Get unassigned work orders."""
        return (
            WorkOrder.objects.filter(status="PENDING", assigned_to_vehicle__isnull=True)
            .select_related("container_entry__container", "container_entry__company")
            .order_by("-priority", "-created_at")
        )

    def get_all_active_orders(self) -> list:
        """Get all pending work orders."""
        return (
            WorkOrder.objects.filter(status="PENDING")
            .select_related("container_entry__container", "container_entry__company", "assigned_to_vehicle")
            .order_by("-priority", "-created_at")
        )

    # Private helper methods

    def _get_work_order(self, work_order_id: int) -> WorkOrder:
        """Get work order by ID or raise error."""
        try:
            return WorkOrder.objects.select_related(
                "container_entry__container",
                "assigned_to_vehicle",
            ).get(id=work_order_id)
        except WorkOrder.DoesNotExist:
            raise WorkOrderNotFoundError(work_order_id)
