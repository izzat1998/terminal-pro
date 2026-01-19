"""
Work Order Service - Business logic for container placement work orders.

Manages the assignment, tracking, and completion of placement tasks
for yard managers in the Telegram Mini App.
"""

from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService
from apps.terminal_operations.models import ContainerEntry, TerminalVehicle, WorkOrder

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


class InvalidStatusTransitionError(BusinessLogicError):
    """Raised when status transition is not allowed."""

    def __init__(self, current_status: str, target_status: str, order_number: str):
        super().__init__(
            message=f"Невозможно изменить статус с '{current_status}' на '{target_status}'",
            error_code="INVALID_STATUS_TRANSITION",
            details={
                "order_number": order_number,
                "current_status": current_status,
                "target_status": target_status,
            },
        )


class NotAssignedToVehicleError(BusinessLogicError):
    """Raised when trying to work on order not assigned to the vehicle."""

    def __init__(self, order_number: str, vehicle_name: str):
        super().__init__(
            message=f"Наряд {order_number} не назначен технике {vehicle_name}",
            error_code="NOT_ASSIGNED_TO_VEHICLE",
            details={"order_number": order_number, "vehicle_name": vehicle_name},
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


# SLA configuration (in minutes)
SLA_BY_PRIORITY = {
    "LOW": 120,  # 2 hours
    "MEDIUM": 60,  # 1 hour
    "HIGH": 30,  # 30 minutes
    "URGENT": 15,  # 15 minutes
}

# Valid status transitions
VALID_TRANSITIONS = {
    "PENDING": ["ASSIGNED"],
    "ASSIGNED": ["ACCEPTED", "PENDING"],  # Can reassign (back to PENDING)
    "ACCEPTED": ["IN_PROGRESS", "ASSIGNED"],  # Can reject (back to ASSIGNED)
    "IN_PROGRESS": ["COMPLETED", "FAILED"],
    "COMPLETED": ["VERIFIED", "FAILED"],
    "VERIFIED": [],  # Terminal state
    "FAILED": ["PENDING"],  # Can retry
}


class WorkOrderService(BaseService):
    """
    Service for managing container placement work orders.

    Handles the full lifecycle of work orders:
    - Creation with auto-suggested positions
    - Assignment to yard managers
    - Status tracking (accept, start, complete)
    - Photo verification on completion
    """

    def __init__(self):
        super().__init__()
        self.placement_service = PlacementService()

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
        active_statuses = ["PENDING", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"]
        existing_order = WorkOrder.objects.filter(
            container_entry=entry,
            status__in=active_statuses,
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
        if priority not in SLA_BY_PRIORITY:
            raise BusinessLogicError(
                message=f"Недопустимый приоритет: {priority}",
                error_code="INVALID_PRIORITY",
            )

        # Calculate SLA deadline
        sla_minutes = SLA_BY_PRIORITY[priority]
        sla_deadline = timezone.now() + timedelta(minutes=sla_minutes)

        # Determine initial status
        initial_status = "ASSIGNED" if assigned_to_vehicle_id else "PENDING"

        # Create work order
        work_order = WorkOrder(
            container_entry=entry,
            status=initial_status,
            priority=priority,
            target_zone=zone,
            target_row=row,
            target_bay=bay,
            target_tier=tier,
            target_sub_slot=sub_slot,
            sla_deadline=sla_deadline,
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
                work_order.assigned_at = timezone.now()
            except TerminalVehicle.DoesNotExist:
                raise BusinessLogicError(
                    message=f"Техника #{assigned_to_vehicle_id} не найдена",
                    error_code="VEHICLE_NOT_FOUND",
                )

        work_order.save()

        self.logger.info(
            f"Created work order {work_order.order_number} for container "
            f"{entry.container.container_number} → {work_order.target_coordinate_string}"
        )

        return work_order

    def assign_to_vehicle(
        self,
        work_order_id: int,
        vehicle_id: int,
    ) -> WorkOrder:
        """
        Assign a work order to a terminal vehicle.

        Args:
            work_order_id: Work order to assign
            vehicle_id: Vehicle to assign to

        Returns:
            Updated WorkOrder
        """
        work_order = self._get_work_order(work_order_id)

        # Validate status transition
        self._validate_transition(work_order, "ASSIGNED")

        # Get vehicle
        try:
            vehicle = TerminalVehicle.objects.get(
                id=vehicle_id,
                is_active=True,
            )
        except TerminalVehicle.DoesNotExist:
            raise BusinessLogicError(
                message=f"Техника #{vehicle_id} не найдена или неактивна",
                error_code="VEHICLE_NOT_FOUND",
            )

        # Update work order
        work_order.assigned_to_vehicle = vehicle
        work_order.assigned_at = timezone.now()
        work_order.status = "ASSIGNED"
        work_order.save(
            update_fields=["assigned_to_vehicle", "assigned_at", "status", "updated_at"]
        )

        self.logger.info(
            f"Assigned work order {work_order.order_number} to vehicle {vehicle.name}"
        )

        return work_order

    def accept_order(
        self,
        work_order_id: int,
        vehicle_id: int,
        operator: Optional[CustomUser] = None,
    ) -> WorkOrder:
        """
        Accept a work order for a specific vehicle.

        Args:
            work_order_id: Work order to accept
            vehicle_id: Vehicle accepting the order
            operator: Operator who is accepting (optional, for logging)

        Returns:
            Updated WorkOrder

        Raises:
            NotAssignedToVehicleError: If order not assigned to this vehicle
        """
        work_order = self._get_work_order(work_order_id)

        # Validate vehicle assignment
        self._validate_vehicle_assignment(work_order, vehicle_id)

        # Validate status transition
        self._validate_transition(work_order, "ACCEPTED")

        # Update work order
        work_order.status = "ACCEPTED"
        work_order.accepted_at = timezone.now()
        work_order.save(update_fields=["status", "accepted_at", "updated_at"])

        operator_name = operator.get_full_name() if operator else "Operator"
        self.logger.info(
            f"Work order {work_order.order_number} accepted by {operator_name}"
        )

        return work_order

    def start_order(
        self,
        work_order_id: int,
        vehicle_id: int,
        operator: Optional[CustomUser] = None,
    ) -> WorkOrder:
        """
        Start working on a work order (navigating to location).

        Args:
            work_order_id: Work order to start
            vehicle_id: Vehicle starting the order
            operator: Operator who is starting (optional, for logging)

        Returns:
            Updated WorkOrder
        """
        work_order = self._get_work_order(work_order_id)

        # Validate vehicle assignment
        self._validate_vehicle_assignment(work_order, vehicle_id)

        # Validate status transition
        self._validate_transition(work_order, "IN_PROGRESS")

        # Update work order
        work_order.status = "IN_PROGRESS"
        work_order.started_at = timezone.now()
        work_order.save(update_fields=["status", "started_at", "updated_at"])

        operator_name = operator.get_full_name() if operator else "Operator"
        self.logger.info(
            f"Work order {work_order.order_number} started by {operator_name}"
        )

        return work_order

    @transaction.atomic
    def complete_order(
        self,
        work_order_id: int,
        vehicle_id: int,
        operator: Optional[CustomUser] = None,
        placement_photo=None,
    ) -> WorkOrder:
        """
        Complete a work order with photo confirmation.

        This also creates the actual ContainerPosition via PlacementService.

        Args:
            work_order_id: Work order to complete
            vehicle_id: Vehicle completing the order
            operator: Operator who is completing (optional, for logging)
            placement_photo: Photo file confirming placement

        Returns:
            Updated WorkOrder
        """
        work_order = self._get_work_order(work_order_id)

        # Validate vehicle assignment
        self._validate_vehicle_assignment(work_order, vehicle_id)

        # Validate status transition
        self._validate_transition(work_order, "COMPLETED")

        # Create actual container position via PlacementService
        try:
            self.placement_service.assign_position(
                container_entry_id=work_order.container_entry_id,
                zone=work_order.target_zone,
                row=work_order.target_row,
                bay=work_order.target_bay,
                tier=work_order.target_tier,
                sub_slot=work_order.target_sub_slot,
                auto_assigned=False,
            )
        except Exception as e:
            # If placement fails, mark as failed
            work_order.status = "FAILED"
            work_order.verification_notes = f"Ошибка размещения: {e!s}"
            work_order.save(
                update_fields=["status", "verification_notes", "updated_at"]
            )
            raise

        # Update work order
        work_order.status = "COMPLETED"
        work_order.completed_at = timezone.now()
        work_order.verification_status = "PENDING"

        if placement_photo:
            work_order.placement_photo = placement_photo

        work_order.save(
            update_fields=[
                "status",
                "completed_at",
                "placement_photo",
                "verification_status",
                "updated_at",
            ]
        )

        operator_name = operator.get_full_name() if operator else "Operator"
        self.logger.info(
            f"Work order {work_order.order_number} completed by {operator_name}"
        )

        return work_order

    def verify_placement(
        self,
        work_order_id: int,
        is_correct: bool,
        notes: str = "",
        verified_by: Optional[CustomUser] = None,
    ) -> WorkOrder:
        """
        Verify a completed placement (by control room or automatically).

        Args:
            work_order_id: Work order to verify
            is_correct: Whether placement is correct
            notes: Verification notes
            verified_by: User performing verification

        Returns:
            Updated WorkOrder
        """
        work_order = self._get_work_order(work_order_id)

        if work_order.status != "COMPLETED":
            raise InvalidStatusTransitionError(
                work_order.status,
                "VERIFIED" if is_correct else "FAILED",
                work_order.order_number,
            )

        if is_correct:
            work_order.status = "VERIFIED"
            work_order.verification_status = "CORRECT"
        else:
            work_order.status = "FAILED"
            work_order.verification_status = "INCORRECT"

        work_order.verified_at = timezone.now()
        work_order.verification_notes = notes
        work_order.save(
            update_fields=[
                "status",
                "verification_status",
                "verified_at",
                "verification_notes",
                "updated_at",
            ]
        )

        self.logger.info(
            f"Work order {work_order.order_number} verified: "
            f"{'CORRECT' if is_correct else 'INCORRECT'}"
        )

        return work_order

    def fail_order(
        self,
        work_order_id: int,
        reason: str,
        vehicle_id: Optional[int] = None,
    ) -> WorkOrder:
        """
        Mark a work order as failed.

        Args:
            work_order_id: Work order to fail
            reason: Reason for failure
            vehicle_id: Vehicle reporting failure (optional)

        Returns:
            Updated WorkOrder
        """
        work_order = self._get_work_order(work_order_id)

        # If vehicle_id provided, validate assignment
        if vehicle_id:
            self._validate_vehicle_assignment(work_order, vehicle_id)

        # Validate status (can fail from IN_PROGRESS or COMPLETED)
        if work_order.status not in ["IN_PROGRESS", "COMPLETED"]:
            raise InvalidStatusTransitionError(
                work_order.status,
                "FAILED",
                work_order.order_number,
            )

        work_order.status = "FAILED"
        work_order.verification_status = "INCORRECT"
        work_order.verification_notes = reason
        work_order.save(
            update_fields=[
                "status",
                "verification_status",
                "verification_notes",
                "updated_at",
            ]
        )

        self.logger.info(f"Work order {work_order.order_number} failed: {reason}")

        return work_order

    def get_vehicle_orders(
        self,
        vehicle_id: int,
        status_filter: Optional[list] = None,
        include_completed: bool = False,
    ) -> list:
        """
        Get work orders assigned to a specific vehicle.

        Args:
            vehicle_id: Vehicle to filter by
            status_filter: List of statuses to include (optional)
            include_completed: Include COMPLETED/VERIFIED orders

        Returns:
            QuerySet of WorkOrder
        """
        queryset = (
            WorkOrder.objects.filter(assigned_to_vehicle_id=vehicle_id)
            .select_related(
                "container_entry__container",
                "container_entry__company",
                "assigned_to_vehicle",
            )
            .order_by("-priority", "-created_at")
        )

        if status_filter:
            queryset = queryset.filter(status__in=status_filter)
        elif not include_completed:
            # Default: active orders only
            queryset = queryset.filter(
                status__in=["ASSIGNED", "ACCEPTED", "IN_PROGRESS"]
            )

        return queryset

    def get_pending_orders(self) -> list:
        """
        Get unassigned work orders (for control room to assign).

        Returns:
            QuerySet of WorkOrder with status PENDING
        """
        return (
            WorkOrder.objects.filter(status="PENDING")
            .select_related(
                "container_entry__container",
                "container_entry__company",
            )
            .order_by("-priority", "-created_at")
        )

    def get_all_active_orders(self) -> list:
        """
        Get all active work orders (for control room dashboard).

        Returns:
            QuerySet of active WorkOrders
        """
        return (
            WorkOrder.objects.filter(
                status__in=["PENDING", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"]
            )
            .select_related(
                "container_entry__container",
                "container_entry__company",
                "assigned_to_vehicle",
            )
            .order_by("-priority", "-created_at")
        )

    def get_overdue_orders(self) -> list:
        """
        Get work orders that have passed their SLA deadline.

        Returns:
            QuerySet of overdue WorkOrders
        """
        return (
            WorkOrder.objects.filter(
                status__in=["PENDING", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"],
                sla_deadline__lt=timezone.now(),
            )
            .select_related(
                "container_entry__container",
                "assigned_to_vehicle",
            )
            .order_by("sla_deadline")
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

    def _validate_transition(self, work_order: WorkOrder, target_status: str) -> None:
        """Validate status transition is allowed."""
        allowed = VALID_TRANSITIONS.get(work_order.status, [])
        if target_status not in allowed:
            raise InvalidStatusTransitionError(
                work_order.status,
                target_status,
                work_order.order_number,
            )

    def _validate_vehicle_assignment(
        self,
        work_order: WorkOrder,
        vehicle_id: int,
    ) -> None:
        """Validate work order is assigned to the given vehicle."""
        if work_order.assigned_to_vehicle_id != vehicle_id:
            vehicle_name = f"#{vehicle_id}"
            if work_order.assigned_to_vehicle:
                vehicle_name = work_order.assigned_to_vehicle.name
            raise NotAssignedToVehicleError(
                work_order.order_number,
                vehicle_name,
            )
