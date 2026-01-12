import asyncio
import threading

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.core.exceptions import BusinessLogicError
from apps.core.services import BaseService
from apps.vehicles.models import VehicleEntry


class VehicleEntryService(BaseService):
    """
    Business logic for vehicle entries.
    Tracks vehicle status from WAITING (pre-order) through terminal workflow.
    """

    def _notify_customer_async(self, vehicle_entry, notification_type: str):
        """
        Send customer notification in background thread.
        Best-effort: errors are logged but don't affect the main flow.

        Args:
            vehicle_entry: VehicleEntry instance
            notification_type: 'entered' or 'exited'
        """
        # Capture ID and data before spawning thread (Django ORM objects aren't thread-safe)
        vehicle_entry_id = vehicle_entry.id

        def run_notification():
            try:
                # Import inside thread to get fresh Django setup
                import django

                django.setup()

                from apps.terminal_operations.services.telegram_notification_service import (
                    TelegramNotificationService,
                )
                from apps.vehicles.models import VehicleEntry as VE

                # Reload object in this thread's DB connection
                try:
                    entry = VE.objects.select_related("customer").get(
                        id=vehicle_entry_id
                    )
                except VE.DoesNotExist:
                    return

                notification_service = TelegramNotificationService()

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if notification_type == "entered":
                        loop.run_until_complete(
                            notification_service.notify_customer_vehicle_entered(entry)
                        )
                    elif notification_type == "exited":
                        loop.run_until_complete(
                            notification_service.notify_customer_vehicle_exited(entry)
                        )
                finally:
                    loop.close()
            except Exception as e:
                # Can't use self.logger here (might not be thread-safe)
                import logging

                logging.getLogger(__name__).error(
                    f"Background notification failed: {e}"
                )

        # Run in background thread to not block the main flow
        thread = threading.Thread(target=run_notification, daemon=True)
        thread.start()

    def _normalize_plate(self, plate_number):
        """
        Normalize plate number for consistent matching.
        Removes spaces, dashes, converts to uppercase.

        Args:
            plate_number: Raw plate number string

        Returns:
            Normalized plate number
        """
        if not plate_number:
            return ""
        return plate_number.upper().replace(" ", "").replace("-", "").replace(".", "")

    @transaction.atomic
    def create_vehicle_entry(self, license_plate, customer=None, vehicle_type="CARGO"):
        """
        Create new vehicle entry with WAITING status.
        Called when customer submits a pre-order.

        Args:
            license_plate: Vehicle license plate number
            customer: CustomUser instance (customer) - optional
            vehicle_type: Vehicle type (LIGHT or CARGO)

        Returns:
            VehicleEntry instance

        Raises:
            BusinessLogicError: If validation fails
        """
        # Validate plate number
        if not license_plate or len(license_plate.strip()) < 3:
            raise BusinessLogicError(
                message="Номер автомобиля должен содержать минимум 3 символа",
                error_code="INVALID_PLATE_NUMBER",
                details={"license_plate": license_plate},
            )

        # Normalize plate number
        normalized_plate = self._normalize_plate(license_plate)

        # Create vehicle entry with WAITING status (entry_time is None since not arrived yet)
        vehicle_entry = VehicleEntry.objects.create(
            license_plate=normalized_plate,
            customer=customer,
            vehicle_type=vehicle_type,
            status="WAITING",
            entry_time=None,  # Not arrived yet
        )

        self.logger.info(
            f"Created vehicle entry #{vehicle_entry.id} for plate {normalized_plate} "
            f"(customer: {customer.first_name if customer else 'N/A'})"
        )

        return vehicle_entry

    def get_by_id(self, vehicle_entry_id):
        """
        Get vehicle entry by ID.

        Args:
            vehicle_entry_id: VehicleEntry ID

        Returns:
            VehicleEntry instance

        Raises:
            BusinessLogicError: If not found
        """
        try:
            return VehicleEntry.objects.select_related(
                "customer", "recorded_by", "destination"
            ).get(id=vehicle_entry_id)
        except VehicleEntry.DoesNotExist:
            raise BusinessLogicError(
                message="Запись въезда автомобиля не найдена",
                error_code="VEHICLE_ENTRY_NOT_FOUND",
                details={"vehicle_entry_id": vehicle_entry_id},
            )

    def get_waiting_vehicles(self, limit=100):
        """
        Get all vehicles with WAITING status.

        Args:
            limit: Maximum number of results

        Returns:
            QuerySet of VehicleEntry instances
        """
        return (
            VehicleEntry.objects.filter(status="WAITING")
            .select_related("customer", "destination")
            .order_by("-created_at")[:limit]
        )

    def get_vehicles_by_status(self, status, limit=100):
        """
        Get vehicles filtered by status.

        Args:
            status: Status to filter by
            limit: Maximum number of results

        Returns:
            QuerySet of VehicleEntry instances
        """
        return (
            VehicleEntry.objects.filter(status=status)
            .select_related("customer", "recorded_by", "destination")
            .order_by("-created_at")[:limit]
        )

    def get_customer_vehicles(self, customer, status=None, limit=None):
        """
        Get all vehicle entries for a customer.

        Args:
            customer: CustomUser instance
            status: Optional status filter
            limit: Optional limit on results

        Returns:
            QuerySet of VehicleEntry instances
        """
        queryset = VehicleEntry.objects.filter(customer=customer)

        if status:
            queryset = queryset.filter(status=status)

        queryset = queryset.select_related("destination", "recorded_by").order_by(
            "-created_at"
        )

        if limit:
            queryset = queryset[:limit]

        return queryset

    def find_by_plate(self, license_plate, status=None):
        """
        Find vehicle entry by license plate.

        Args:
            license_plate: Vehicle license plate number
            status: Optional status filter

        Returns:
            VehicleEntry instance or None
        """
        normalized_plate = self._normalize_plate(license_plate)

        if not normalized_plate:
            return None

        queryset = VehicleEntry.objects.filter(license_plate=normalized_plate)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related("customer", "destination").first()

    def find_waiting_by_plate(self, license_plate):
        """
        Find WAITING vehicle by license plate (for gate matching).

        Args:
            license_plate: Vehicle plate scanned at gate

        Returns:
            VehicleEntry instance or None
        """
        return self.find_by_plate(license_plate, status="WAITING")

    @transaction.atomic
    def mark_on_terminal(self, vehicle_entry, recorded_by=None):
        """
        Mark vehicle as entered terminal (WAITING -> ON_TERMINAL).

        Args:
            vehicle_entry: VehicleEntry instance
            recorded_by: Manager who processed entry

        Returns:
            Updated VehicleEntry instance

        Raises:
            BusinessLogicError: If not in WAITING status
        """
        if vehicle_entry.status != "WAITING":
            raise BusinessLogicError(
                message="Только ожидающие автомобили могут въехать на терминал",
                error_code="INVALID_STATUS_TRANSITION",
                details={
                    "vehicle_entry_id": vehicle_entry.id,
                    "current_status": vehicle_entry.status,
                },
            )

        vehicle_entry.status = "ON_TERMINAL"
        vehicle_entry.entry_time = timezone.now()
        if recorded_by:
            vehicle_entry.recorded_by = recorded_by
        vehicle_entry.save()

        self.logger.info(f"Vehicle {vehicle_entry.license_plate} entered terminal")

        # Notify customer in background (if customer exists)
        if vehicle_entry.customer:
            self._notify_customer_async(vehicle_entry, "entered")

        return vehicle_entry

    @transaction.atomic
    def mark_exited(self, vehicle_entry, recorded_by=None):
        """
        Mark vehicle as exited terminal (ON_TERMINAL -> EXITED).

        Args:
            vehicle_entry: VehicleEntry instance
            recorded_by: Manager who processed exit

        Returns:
            Updated VehicleEntry instance

        Raises:
            BusinessLogicError: If not in ON_TERMINAL status
        """
        if vehicle_entry.status != "ON_TERMINAL":
            raise BusinessLogicError(
                message="Только автомобили на терминале могут выехать",
                error_code="INVALID_STATUS_TRANSITION",
                details={
                    "vehicle_entry_id": vehicle_entry.id,
                    "current_status": vehicle_entry.status,
                },
            )

        vehicle_entry.status = "EXITED"
        vehicle_entry.exit_time = timezone.now()
        vehicle_entry.save()

        self.logger.info(f"Vehicle {vehicle_entry.license_plate} exited terminal")

        # Notify customer in background (if customer exists)
        if vehicle_entry.customer:
            self._notify_customer_async(vehicle_entry, "exited")

        return vehicle_entry

    @transaction.atomic
    def cancel(self, vehicle_entry):
        """
        Cancel a waiting vehicle entry (WAITING -> CANCELLED).

        Args:
            vehicle_entry: VehicleEntry instance

        Returns:
            Updated VehicleEntry instance

        Raises:
            BusinessLogicError: If not in WAITING status
        """
        if vehicle_entry.status != "WAITING":
            raise BusinessLogicError(
                message="Можно отменить только ожидающие автомобили",
                error_code="CANNOT_CANCEL",
                details={
                    "vehicle_entry_id": vehicle_entry.id,
                    "current_status": vehicle_entry.status,
                },
            )

        vehicle_entry.status = "CANCELLED"
        vehicle_entry.save()

        self.logger.info(f"Vehicle entry {vehicle_entry.license_plate} cancelled")

        return vehicle_entry

    @transaction.atomic
    def update_status(
        self, vehicle_entry_id, new_status, processed_by=None, notes=None
    ):
        """
        Update vehicle entry status with validation.

        Args:
            vehicle_entry_id: VehicleEntry ID
            new_status: New status to set
            processed_by: Manager who made the change
            notes: Optional notes (not supported in current model)

        Returns:
            Updated VehicleEntry instance

        Raises:
            BusinessLogicError: If transition not allowed
        """
        vehicle_entry = self.get_by_id(vehicle_entry_id)

        # Status transition mapping
        status_handlers = {
            "ON_TERMINAL": self.mark_on_terminal,
            "EXITED": self.mark_exited,
            "CANCELLED": self.cancel,
        }

        handler = status_handlers.get(new_status)
        if not handler:
            raise BusinessLogicError(
                message=f"Неизвестный статус: {new_status}",
                error_code="INVALID_STATUS",
                details={"status": new_status},
            )

        if new_status == "CANCELLED":
            vehicle_entry = handler(vehicle_entry)
        else:
            vehicle_entry = handler(vehicle_entry, processed_by)

        return vehicle_entry

    def get_stats(self):
        """
        Get vehicle entry statistics.

        Returns:
            Dict with statistics
        """
        stats = VehicleEntry.objects.aggregate(
            total=Count("id"),
            waiting=Count("id", filter=Q(status="WAITING")),
            on_terminal=Count("id", filter=Q(status="ON_TERMINAL")),
            exited=Count("id", filter=Q(status="EXITED")),
            cancelled=Count("id", filter=Q(status="CANCELLED")),
        )

        return stats
