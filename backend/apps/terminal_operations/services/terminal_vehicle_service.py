"""
Terminal Vehicle Service.

Handles CRUD operations for terminal yard equipment (Reach Stackers, Forklifts, etc.).
"""

from django.db import IntegrityError
from django.db.models import QuerySet

from apps.accounts.models import CustomUser
from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService

from ..models import TerminalVehicle


class TerminalVehicleService(BaseService):
    """
    Service for managing terminal vehicles (yard equipment).

    Business rules:
    - Name must be unique across all vehicles
    - Vehicle type must be a valid choice (REACH_STACKER, FORKLIFT, YARD_TRUCK, RTG_CRANE)
    - Operator must be a manager user type (if provided)
    """

    VALID_VEHICLE_TYPES = ["REACH_STACKER", "FORKLIFT", "YARD_TRUCK", "RTG_CRANE"]

    def get_all_vehicles(self, include_inactive: bool = True) -> QuerySet:
        """
        Get all terminal vehicles.

        Args:
            include_inactive: If False, only returns active vehicles

        Returns:
            QuerySet of TerminalVehicle ordered by type and name
        """
        queryset = TerminalVehicle.objects.select_related("operator").order_by(
            "vehicle_type", "name"
        )

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        return queryset

    def get_vehicle_by_id(self, vehicle_id: int) -> TerminalVehicle:
        """
        Get a terminal vehicle by ID.

        Args:
            vehicle_id: ID of the vehicle

        Returns:
            TerminalVehicle instance

        Raises:
            BusinessLogicError: If vehicle not found
        """
        try:
            return TerminalVehicle.objects.select_related("operator").get(id=vehicle_id)
        except TerminalVehicle.DoesNotExist:
            raise BusinessLogicError(
                message=f"Техника с ID {vehicle_id} не найдена",
                error_code="VEHICLE_NOT_FOUND",
            )

    def create_vehicle(
        self,
        name: str,
        vehicle_type: str,
        license_plate: str = "",
        operator_id: int | None = None,
        is_active: bool = True,
    ) -> TerminalVehicle:
        """
        Create a new terminal vehicle.

        Args:
            name: Unique name for the vehicle (e.g., RS-01, Погрузчик-3)
            vehicle_type: Type of vehicle (REACH_STACKER, FORKLIFT, etc.)
            license_plate: Optional government license plate
            operator_id: Optional ID of the user operating this vehicle
            is_active: Whether the vehicle is active

        Returns:
            Created TerminalVehicle instance

        Raises:
            BusinessLogicError: If validation fails
        """
        # Validate vehicle type
        if vehicle_type not in self.VALID_VEHICLE_TYPES:
            raise BusinessLogicError(
                message=f"Недопустимый тип техники: {vehicle_type}",
                error_code="INVALID_VEHICLE_TYPE",
            )

        # Validate name uniqueness
        if TerminalVehicle.objects.filter(name=name).exists():
            raise BusinessLogicError(
                message=f"Техника с названием '{name}' уже существует",
                error_code="DUPLICATE_VEHICLE_NAME",
            )

        # Validate operator if provided
        operator = None
        if operator_id:
            operator = self._validate_operator(operator_id)

        try:
            vehicle = TerminalVehicle.objects.create(
                name=name,
                vehicle_type=vehicle_type,
                license_plate=license_plate,
                operator=operator,
                is_active=is_active,
            )
            self.logger.info(f"Created terminal vehicle: {vehicle.name} ({vehicle_type})")
            return vehicle
        except IntegrityError as e:
            self.logger.error(f"Failed to create vehicle: {e}")
            raise BusinessLogicError(
                message="Не удалось создать технику. Возможно, имя уже занято.",
                error_code="CREATE_FAILED",
            )

    def update_vehicle(
        self,
        vehicle_id: int,
        name: str | None = None,
        vehicle_type: str | None = None,
        license_plate: str | None = None,
        operator_id: int | None = None,
        is_active: bool | None = None,
        clear_operator: bool = False,
    ) -> TerminalVehicle:
        """
        Update a terminal vehicle.

        Args:
            vehicle_id: ID of the vehicle to update
            name: New name (optional)
            vehicle_type: New vehicle type (optional)
            license_plate: New license plate (optional)
            operator_id: New operator ID (optional)
            is_active: New active status (optional)
            clear_operator: If True, remove current operator

        Returns:
            Updated TerminalVehicle instance

        Raises:
            BusinessLogicError: If validation fails
        """
        vehicle = self.get_vehicle_by_id(vehicle_id)

        # Validate and update name
        if name is not None and name != vehicle.name:
            if TerminalVehicle.objects.filter(name=name).exclude(id=vehicle_id).exists():
                raise BusinessLogicError(
                    message=f"Техника с названием '{name}' уже существует",
                    error_code="DUPLICATE_VEHICLE_NAME",
                )
            vehicle.name = name

        # Validate and update vehicle type
        if vehicle_type is not None:
            if vehicle_type not in self.VALID_VEHICLE_TYPES:
                raise BusinessLogicError(
                    message=f"Недопустимый тип техники: {vehicle_type}",
                    error_code="INVALID_VEHICLE_TYPE",
                )
            vehicle.vehicle_type = vehicle_type

        # Update license plate
        if license_plate is not None:
            vehicle.license_plate = license_plate

        # Update operator
        if clear_operator:
            vehicle.operator = None
        elif operator_id is not None:
            vehicle.operator = self._validate_operator(operator_id)

        # Update active status
        if is_active is not None:
            vehicle.is_active = is_active

        vehicle.save()
        self.logger.info(f"Updated terminal vehicle: {vehicle.name} (ID: {vehicle_id})")
        return vehicle

    def delete_vehicle(self, vehicle_id: int) -> None:
        """
        Delete a terminal vehicle.

        Args:
            vehicle_id: ID of the vehicle to delete

        Raises:
            BusinessLogicError: If vehicle not found or has active work orders
        """
        vehicle = self.get_vehicle_by_id(vehicle_id)

        # Check for active work orders
        active_statuses = ["ASSIGNED", "ACCEPTED", "IN_PROGRESS"]
        active_orders = vehicle.work_orders.filter(status__in=active_statuses).count()

        if active_orders > 0:
            raise BusinessLogicError(
                message=f"Нельзя удалить технику с активными нарядами ({active_orders} шт.)",
                error_code="VEHICLE_HAS_ACTIVE_ORDERS",
            )

        vehicle_name = vehicle.name
        vehicle.delete()
        self.logger.info(f"Deleted terminal vehicle: {vehicle_name} (ID: {vehicle_id})")

    def assign_operator(
        self, vehicle_id: int, operator_id: int | None
    ) -> TerminalVehicle:
        """
        Assign or remove an operator from a vehicle.

        Args:
            vehicle_id: ID of the vehicle
            operator_id: ID of the user to assign, or None to remove

        Returns:
            Updated TerminalVehicle instance
        """
        vehicle = self.get_vehicle_by_id(vehicle_id)

        if operator_id is None:
            vehicle.operator = None
            self.logger.info(f"Removed operator from vehicle: {vehicle.name}")
        else:
            operator = self._validate_operator(operator_id)
            vehicle.operator = operator
            self.logger.info(
                f"Assigned operator {operator.full_name} to vehicle: {vehicle.name}"
            )

        vehicle.save()
        return vehicle

    def _validate_operator(self, operator_id: int) -> CustomUser:
        """
        Validate that the operator exists and is a manager.

        Args:
            operator_id: ID of the user

        Returns:
            CustomUser instance

        Raises:
            BusinessLogicError: If user not found or not a manager
        """
        try:
            user = CustomUser.objects.get(id=operator_id)
        except CustomUser.DoesNotExist:
            raise BusinessLogicError(
                message=f"Пользователь с ID {operator_id} не найден",
                error_code="OPERATOR_NOT_FOUND",
            )

        if user.user_type != "manager":
            raise BusinessLogicError(
                message="Оператором может быть только менеджер",
                error_code="INVALID_OPERATOR_TYPE",
            )

        if not user.is_active:
            raise BusinessLogicError(
                message="Выбранный оператор неактивен",
                error_code="OPERATOR_INACTIVE",
            )

        return user

    def get_available_operators(self) -> QuerySet:
        """
        Get list of users who can be assigned as operators (managers).

        Returns:
            QuerySet of CustomUser with user_type='manager' and is_active=True
        """
        return CustomUser.objects.filter(
            user_type="manager",
            is_active=True,
        ).order_by("first_name", "last_name")
