from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import BusinessLogicError
from apps.core.services import BaseService
from telegram_bot.services import TelegramNotificationService

from ..models import VehicleEntry


class VehicleEntryService(BaseService):
    """
    Service for managing vehicle entry/exit operations with business logic validation.

    Status workflow:
        WAITING → ON_TERMINAL → EXITED
        WAITING → CANCELLED
    """

    # Valid status transitions
    ALLOWED_TRANSITIONS = {
        "WAITING": ["ON_TERMINAL", "CANCELLED"],
        "ON_TERMINAL": ["EXITED"],
        "EXITED": [],  # Terminal state
        "CANCELLED": [],  # Terminal state
    }

    def _validate_status_transition(self, current_status: str, new_status: str):
        """
        Validate that a status transition is allowed.

        Args:
            current_status: Current status of the vehicle entry
            new_status: Desired new status

        Raises:
            BusinessLogicError: If transition is not allowed
        """
        allowed = self.ALLOWED_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise BusinessLogicError(
                message=f"Невозможно изменить статус с '{current_status}' на '{new_status}'",
                error_code="INVALID_STATUS_TRANSITION",
                details={
                    "current_status": current_status,
                    "new_status": new_status,
                    "allowed_transitions": allowed,
                },
            )

    @transaction.atomic
    def create_entry(
        self,
        license_plate,
        vehicle_type,
        entry_photos,
        entry_time,
        recorded_by,
        **kwargs,
    ):
        """
        Create a new vehicle entry with business validation

        Args:
            license_plate: Vehicle license plate number
            vehicle_type: LIGHT or CARGO
            entry_photos: List of File instances for entry photos
            entry_time: DateTime of entry
            recorded_by: CustomUser who recorded the entry
            **kwargs: Additional fields based on vehicle type

        Returns:
            VehicleEntry instance

        Raises:
            BusinessLogicError: If validation fails
        """
        # Normalize license plate
        license_plate = license_plate.upper().strip()

        # Check for duplicate entry (vehicle already on terminal)
        if self._has_active_entry(license_plate):
            raise BusinessLogicError(
                message=f"Автомобиль {license_plate} уже находится на терминале",
                error_code="DUPLICATE_ENTRY",
                details={"license_plate": license_plate},
            )

        # Validate required fields based on vehicle type
        self._validate_entry_fields(vehicle_type, **kwargs)

        # Create entry (without photos - M2M requires save first)
        entry = VehicleEntry.objects.create(
            license_plate=license_plate,
            vehicle_type=vehicle_type,
            entry_time=entry_time,
            recorded_by=recorded_by,
            **kwargs,
        )

        # Add photos to ManyToMany field
        if entry_photos:
            entry.entry_photos.add(*entry_photos)

        self.logger.info(
            f"Created vehicle entry {entry.id} for {license_plate} "
            f"({vehicle_type}) at {entry_time}"
        )

        return entry

    @transaction.atomic
    def register_exit(
        self, license_plate, exit_photos, exit_time, exit_load_status=None
    ):
        """
        Register vehicle exit - auto-matches most recent entry

        Args:
            license_plate: Vehicle license plate number
            exit_photos: List of File instances for exit photos
            exit_time: DateTime of exit
            exit_load_status: Load status at exit (for cargo vehicles)

        Returns:
            VehicleEntry instance (updated with exit info or new exit-only record)
        """
        # Normalize license plate
        license_plate = license_plate.upper().strip()

        # Find vehicle that is currently ON_TERMINAL
        entry = (
            VehicleEntry.objects.filter(
                license_plate=license_plate, status="ON_TERMINAL"
            )
            .order_by("-entry_time")
            .first()
        )

        if not entry:
            # Check if vehicle exists with different status
            existing = VehicleEntry.objects.filter(
                license_plate=license_plate, exit_time__isnull=True
            ).first()

            if existing and existing.status == "WAITING":
                raise BusinessLogicError(
                    message=f"Автомобиль {license_plate} ещё не въехал на терминал (статус: Ожидает)",
                    error_code="VEHICLE_NOT_ENTERED",
                    details={
                        "license_plate": license_plate,
                        "current_status": existing.status,
                    },
                )
            else:
                raise BusinessLogicError(
                    message=f"Автомобиль {license_plate} не найден на терминале",
                    error_code="VEHICLE_NOT_ON_TERMINAL",
                    details={"license_plate": license_plate},
                )

        # Validate exit_time is after entry_time
        if entry.entry_time and exit_time < entry.entry_time:
            raise BusinessLogicError(
                message="Время выезда не может быть раньше времени въезда",
                error_code="INVALID_EXIT_TIME",
                details={
                    "entry_time": entry.entry_time.isoformat(),
                    "exit_time": exit_time.isoformat(),
                },
            )

        # Update existing entry with exit information
        if exit_photos:
            entry.exit_photos.add(*exit_photos)
        entry.status = "EXITED"
        entry.exit_time = exit_time
        if exit_load_status:
            entry.exit_load_status = exit_load_status
        entry.save()

        self.logger.info(
            f"Registered exit for vehicle entry {entry.id} - {license_plate} "
            f"at {exit_time}. Dwell time: {entry.dwell_time_hours} hours"
        )

        # Send exit notification to customer
        if entry.customer:
            notification_service = TelegramNotificationService()
            notification_service.notify_vehicle_exited(
                customer=entry.customer,
                license_plate=license_plate,
                exit_time=exit_time,
            )

        return entry

    @transaction.atomic
    def check_in(self, license_plate, entry_photos, recorded_by=None):
        """
        Check in a WAITING vehicle - transition status to ON_TERMINAL

        This is used when a manager at the gate registers arrival of a vehicle
        that was pre-ordered by a customer (created with WAITING status).
        Entry time is automatically set to current time.

        Args:
            license_plate: Vehicle license plate number
            entry_photos: List of File instances for entry photos
            recorded_by: CustomUser (manager) who recorded the check-in

        Returns:
            VehicleEntry instance (updated)

        Raises:
            BusinessLogicError: If vehicle not found or not in WAITING status
        """
        license_plate = license_plate.upper().strip()

        # Find vehicle with WAITING status
        entry = VehicleEntry.objects.filter(
            license_plate=license_plate, status="WAITING"
        ).first()

        if not entry:
            # Check if vehicle exists with different status
            existing = VehicleEntry.objects.filter(
                license_plate=license_plate, exit_time__isnull=True
            ).first()

            if existing:
                raise BusinessLogicError(
                    message=f"Автомобиль {license_plate} уже на терминале (статус: {existing.get_status_display()})",
                    error_code="INVALID_STATUS",
                    details={
                        "license_plate": license_plate,
                        "current_status": existing.status,
                    },
                )
            else:
                raise BusinessLogicError(
                    message=f"Ожидающий автомобиль с номером {license_plate} не найден",
                    error_code="VEHICLE_NOT_FOUND",
                    details={"license_plate": license_plate},
                )

        # Update entry - set entry_time to now
        entry_time = timezone.now()
        entry.status = "ON_TERMINAL"
        entry.entry_time = entry_time
        if recorded_by:
            entry.recorded_by = recorded_by
        entry.save()

        # Add entry photos
        if entry_photos:
            entry.entry_photos.add(*entry_photos)

        self.logger.info(
            f"Checked in vehicle {entry.id} - {license_plate} "
            f"(WAITING → ON_TERMINAL) at {entry_time}"
        )

        # Send notification to customer
        if entry.customer:
            notification_service = TelegramNotificationService()
            notification_service.notify_vehicle_checked_in(
                customer=entry.customer,
                license_plate=license_plate,
                entry_time=entry_time,
            )

        return entry

    @transaction.atomic
    def cancel(self, license_plate):
        """
        Cancel a WAITING vehicle entry (WAITING → CANCELLED).

        Args:
            license_plate: Vehicle license plate number

        Returns:
            VehicleEntry instance (updated)

        Raises:
            BusinessLogicError: If vehicle not found or not in WAITING status
        """
        license_plate = license_plate.upper().strip()

        # Find vehicle with WAITING status
        entry = VehicleEntry.objects.filter(
            license_plate=license_plate, status="WAITING"
        ).first()

        if not entry:
            raise BusinessLogicError(
                message=f"Ожидающий автомобиль с номером {license_plate} не найден",
                error_code="VEHICLE_NOT_FOUND",
                details={"license_plate": license_plate},
            )

        # Validate transition
        self._validate_status_transition(entry.status, "CANCELLED")

        # Update status
        entry.status = "CANCELLED"
        entry.save()

        self.logger.info(
            f"Cancelled vehicle entry {entry.id} - {license_plate} "
            f"(WAITING → CANCELLED)"
        )

        # Send cancellation notification to customer
        if entry.customer:
            notification_service = TelegramNotificationService()
            notification_service.notify_vehicle_cancelled(
                customer=entry.customer,
                license_plate=license_plate,
            )

        return entry

    @transaction.atomic
    def cancel_by_id(self, entry_id):
        """
        Cancel a WAITING vehicle entry by ID (WAITING → CANCELLED).

        Args:
            entry_id: VehicleEntry ID

        Returns:
            VehicleEntry instance (updated)

        Raises:
            BusinessLogicError: If entry not found or not in WAITING status
        """
        entry = VehicleEntry.objects.filter(id=entry_id).first()

        if not entry:
            raise BusinessLogicError(
                message=f"Запись въезда #{entry_id} не найдена",
                error_code="VEHICLE_ENTRY_NOT_FOUND",
                details={"entry_id": entry_id},
            )

        if entry.status != "WAITING":
            raise BusinessLogicError(
                message=f"Можно отменить только ожидающие записи (текущий статус: {entry.get_status_display()})",
                error_code="INVALID_STATUS",
                details={
                    "entry_id": entry_id,
                    "current_status": entry.status,
                },
            )

        # Validate transition
        self._validate_status_transition(entry.status, "CANCELLED")

        # Update status
        entry.status = "CANCELLED"
        entry.save()

        self.logger.info(
            f"Cancelled vehicle entry {entry.id} - {entry.license_plate} "
            f"(WAITING → CANCELLED)"
        )

        # Send cancellation notification to customer
        if entry.customer:
            notification_service = TelegramNotificationService()
            notification_service.notify_vehicle_cancelled(
                customer=entry.customer,
                license_plate=entry.license_plate,
            )

        return entry

    def get_vehicles_on_terminal(self):
        """
        Get all vehicles currently on terminal (status=ON_TERMINAL)

        Returns:
            QuerySet of VehicleEntry instances
        """
        return (
            VehicleEntry.objects.filter(status="ON_TERMINAL")
            .select_related("recorded_by", "destination", "customer")
            .prefetch_related("entry_photos", "exit_photos")
            .order_by("-entry_time")
        )

    def get_entries_by_plate(self, license_plate):
        """
        Get all entries for a specific license plate

        Args:
            license_plate: Vehicle license plate number

        Returns:
            QuerySet of VehicleEntry instances
        """
        return (
            VehicleEntry.objects.filter(license_plate=license_plate.upper().strip())
            .select_related("recorded_by", "destination")
            .prefetch_related("entry_photos", "exit_photos")
            .order_by("-entry_time")
        )

    def _has_active_entry(self, license_plate):
        """
        Check if vehicle has an entry without exit (is on terminal)

        Args:
            license_plate: Vehicle license plate number

        Returns:
            bool: True if vehicle is on terminal
        """
        return VehicleEntry.objects.filter(
            license_plate=license_plate.upper().strip(), exit_time__isnull=True
        ).exists()

    def _validate_entry_fields(self, vehicle_type, **kwargs):
        """
        Validate required fields based on vehicle type and workflow path

        Args:
            vehicle_type: LIGHT or CARGO
            **kwargs: Fields to validate

        Raises:
            BusinessLogicError: If required fields are missing
        """
        if vehicle_type == "LIGHT":
            # Light vehicle must have visitor_type
            if not kwargs.get("visitor_type"):
                raise BusinessLogicError(
                    message="Для легкового автомобиля обязательно указать тип посетителя",
                    error_code="VALIDATION_ERROR",
                    details={"field": "visitor_type"},
                )

        elif vehicle_type == "CARGO":
            # Cargo vehicle must have transport_type and entry_load_status
            if not kwargs.get("transport_type"):
                raise BusinessLogicError(
                    message="Для грузового автомобиля обязательно указать тип транспорта",
                    error_code="VALIDATION_ERROR",
                    details={"field": "transport_type"},
                )

            if not kwargs.get("entry_load_status"):
                raise BusinessLogicError(
                    message="Для грузового автомобиля обязательно указать статус загрузки",
                    error_code="VALIDATION_ERROR",
                    details={"field": "entry_load_status"},
                )

            # If loaded, must have cargo_type
            if kwargs.get("entry_load_status") == "LOADED":
                if not kwargs.get("cargo_type"):
                    raise BusinessLogicError(
                        message="Для груженого автомобиля обязательно указать тип груза",
                        error_code="VALIDATION_ERROR",
                        details={"field": "cargo_type"},
                    )

                # If cargo is container, must have container_size and container_load_status
                if kwargs.get("cargo_type") == "CONTAINER":
                    if not kwargs.get("container_size"):
                        raise BusinessLogicError(
                            message="Для контейнерного груза обязательно указать размер контейнера",
                            error_code="VALIDATION_ERROR",
                            details={"field": "container_size"},
                        )
                    if not kwargs.get("container_load_status"):
                        raise BusinessLogicError(
                            message="Для контейнерного груза обязательно указать статус загрузки контейнера",
                            error_code="VALIDATION_ERROR",
                            details={"field": "container_load_status"},
                        )
