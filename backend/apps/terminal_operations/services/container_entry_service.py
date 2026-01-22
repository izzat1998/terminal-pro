from django.db import transaction
from django.utils import timezone

from apps.containers.models import Container
from apps.core.exceptions import BusinessLogicError, DuplicateEntryError
from apps.core.services import BaseService

from ..models import ContainerEntry, ContainerPosition, CraneOperation
from .container_event_service import ContainerEventService


class ContainerEntryService(BaseService):
    def __init__(self):
        super().__init__()
        self._event_service = None

    @property
    def event_service(self):
        if self._event_service is None:
            self._event_service = ContainerEventService()
        return self._event_service
    @transaction.atomic
    def create_entry(
        self,
        container_number,
        container_iso_type,
        status,
        transport_type,
        user,
        # Optional Stage 1 fields
        transport_number="",
        entry_train_number="",
        entry_time=None,
        recorded_by=None,
        # Optional Stage 2 fields (business info)
        client_name="",
        company=None,
        container_owner=None,
        cargo_name="",
        cargo_weight=None,
        location="",
        additional_crane_operation_date=None,
        note="",
        # Optional Stage 3 fields (exit info)
        exit_date=None,
        exit_transport_type=None,
        exit_train_number="",
        exit_transport_number="",
        destination_station="",
    ):
        """
        Create a new container entry with business validation.
        Supports full data entry for historical/bulk imports (admin).
        """
        # Get or create container with iso_type
        container, created = Container.objects.get_or_create(
            container_number=container_number.upper(),
            defaults={"iso_type": container_iso_type},
        )

        # If container exists but has different iso_type, update it
        if not created and container.iso_type != container_iso_type:
            self.logger.info(
                f"Updating container {container_number} ISO type from {container.iso_type} to {container_iso_type}"
            )
            container.iso_type = container_iso_type
            container.save(update_fields=["iso_type"])

        # Check for duplicate entries (business rule) - only if using today's date
        if entry_time is None or entry_time.date() == timezone.now().date():
            if self._has_recent_entry(container):
                raise DuplicateEntryError(container_number)

        # Use provided recorded_by (admin override) or authenticated user
        final_recorded_by = recorded_by if recorded_by else user

        # Build create kwargs, only include entry_time if provided
        create_kwargs = {
            "container": container,
            "status": status,
            "transport_type": transport_type,
            "transport_number": transport_number,
            "entry_train_number": entry_train_number,
            "recorded_by": final_recorded_by,
            # Stage 2 fields
            "client_name": client_name,
            "company": company,
            "container_owner": container_owner,
            "cargo_name": cargo_name,
            "cargo_weight": cargo_weight,
            "location": location,
            "additional_crane_operation_date": additional_crane_operation_date,
            "note": note,
            # Stage 3 fields
            "exit_date": exit_date,
            "exit_transport_type": exit_transport_type,
            "exit_train_number": exit_train_number,
            "exit_transport_number": exit_transport_number,
            "destination_station": destination_station,
        }

        # Only include entry_time if explicitly provided (allows model default to work)
        if entry_time is not None:
            create_kwargs["entry_time"] = entry_time

        entry = ContainerEntry.objects.create(**create_kwargs)

        # Emit ENTRY_CREATED event
        self.event_service.create_entry_created_event(
            container_entry=entry,
            performed_by=final_recorded_by,
            source="API",
        )

        # Sync additional_crane_operation_date to CraneOperation model for backward compatibility
        if additional_crane_operation_date:
            self._sync_crane_operation_date(entry, additional_crane_operation_date)

        self.logger.info(
            f"Created entry for container {container_number} ({container_iso_type}) with entry_time={entry.entry_time}"
        )
        return entry

    def get_recent_entries(self, date=None):
        """Get entries for a specific date (defaults to today)"""
        if date is None:
            date = timezone.now().date()

        return (
            ContainerEntry.objects.select_related("container", "recorded_by")
            .filter(entry_time__date=date)
            .order_by("-entry_time")
        )

    def get_entries_by_container(self, container_number):
        """Get all entries for a specific container"""
        return (
            ContainerEntry.objects.select_related("container", "recorded_by")
            .filter(container__container_number=container_number.upper())
            .order_by("-entry_time")
        )

    def _get_container(self, container_number):
        """Get container by number, raise error if not found"""
        try:
            return Container.objects.get(container_number=container_number.upper())
        except Container.DoesNotExist:
            raise BusinessLogicError(
                message=f"Контейнер {container_number} не найден",
                error_code="CONTAINER_NOT_FOUND",
            )

    @transaction.atomic
    def update_entry(
        self,
        entry,
        container_number=None,
        container_iso_type=None,
        status=None,
        transport_type=None,
        transport_number=None,
        entry_train_number=None,
        client_name=None,
        company=None,
        container_owner=None,
        cargo_name=None,
        exit_date=None,
        exit_transport_type=None,
        exit_train_number=None,
        exit_transport_number=None,
        destination_station=None,
        location=None,
        additional_crane_operation_date=None,
        note=None,
        cargo_weight=None,
    ):
        """Update an existing container entry"""
        # Track old status for event emission
        old_status = entry.status

        # Handle container number change
        if (
            container_number is not None
            and container_number.upper() != entry.container.container_number
        ):
            # Moving entry to a different container
            final_iso_type = (
                container_iso_type if container_iso_type else entry.container.iso_type
            )
            container, created = Container.objects.get_or_create(
                container_number=container_number.upper(),
                defaults={"iso_type": final_iso_type},
            )

            # Update ISO type if provided and different
            if (
                not created
                and container_iso_type
                and container.iso_type != container_iso_type
            ):
                self.logger.info(
                    f"Updating container {container_number} ISO type from {container.iso_type} to {container_iso_type}"
                )
                container.iso_type = container_iso_type
                container.save(update_fields=["iso_type"])

            entry.container = container

        # Handle ISO type change for same container
        elif (
            container_iso_type is not None
            and container_iso_type != entry.container.iso_type
        ):
            self.logger.info(
                f"Updating container {entry.container.container_number} ISO type from {entry.container.iso_type} to {container_iso_type}"
            )
            entry.container.iso_type = container_iso_type
            entry.container.save(update_fields=["iso_type"])

        # Update entry fields
        if status is not None:
            entry.status = status
        if transport_type is not None:
            entry.transport_type = transport_type
        if transport_number is not None:
            entry.transport_number = transport_number
        if entry_train_number is not None:
            entry.entry_train_number = entry_train_number

        # Update additional information fields
        if client_name is not None:
            entry.client_name = client_name
        if company is not None:
            entry.company = company
            # Auto-populate client_name from company if not explicitly provided
            if company and not client_name:
                entry.client_name = company.name
        if container_owner is not None:
            entry.container_owner = container_owner
        if cargo_name is not None:
            entry.cargo_name = cargo_name

        # Update exit fields
        if exit_date is not None:
            entry.exit_date = exit_date
            # Remove position when container exits (free up terminal space)
            if hasattr(entry, "position") and entry.position:
                position_coord = entry.position.coordinate_string
                entry.position.delete()
                entry.location = ""  # Clear location field
                self.logger.info(
                    f"Removed position {position_coord} for exited container {entry.container.container_number}"
                )
        if exit_transport_type is not None:
            entry.exit_transport_type = exit_transport_type
        if exit_train_number is not None:
            entry.exit_train_number = exit_train_number
        if exit_transport_number is not None:
            entry.exit_transport_number = exit_transport_number
        if destination_station is not None:
            entry.destination_station = destination_station
        if location is not None:
            entry.location = location
        if additional_crane_operation_date is not None:
            entry.additional_crane_operation_date = additional_crane_operation_date
            # Sync to CraneOperation model for backward compatibility
            self._sync_crane_operation_date(entry, additional_crane_operation_date)
        if note is not None:
            entry.note = note
        if cargo_weight is not None:
            entry.cargo_weight = cargo_weight

        entry.save()

        # Emit STATUS_CHANGED event if status changed
        if status is not None and status != old_status:
            self.event_service.create_status_changed_event(
                container_entry=entry,
                old_status=old_status,
                new_status=status,
            )

        # Emit EXIT_RECORDED event if exit_date was set
        if exit_date is not None:
            self.event_service.create_exit_recorded_event(
                container_entry=entry,
            )

        self.logger.info(
            f"Updated entry {entry.id} for container {entry.container.container_number}"
        )
        return entry

    def _has_recent_entry(self, container):
        """Check if container has entry from today (business rule)"""
        today = timezone.now().date()
        return ContainerEntry.objects.filter(
            container=container, entry_time__date=today
        ).exists()

    @transaction.atomic
    def add_crane_operation(self, entry_id, operation_date):
        """
        Add a crane operation to a container entry.

        Args:
            entry_id: ID of the ContainerEntry
            operation_date: DateTime of the crane operation

        Returns:
            CraneOperation instance
        """
        try:
            entry = ContainerEntry.objects.get(id=entry_id)
        except ContainerEntry.DoesNotExist:
            raise BusinessLogicError(
                message=f"Запись контейнера с ID {entry_id} не найдена",
                error_code="CONTAINER_ENTRY_NOT_FOUND",
            )

        operation = CraneOperation.objects.create(
            container_entry=entry, operation_date=operation_date
        )

        # Emit CRANE_OPERATION event
        self.event_service.create_crane_operation_event(
            container_entry=entry,
            operation_date=operation_date,
            crane_operation_id=operation.id,
        )

        self.logger.info(
            f"Added crane operation to entry {entry_id} at {operation_date}"
        )
        return operation

    def get_crane_operations(self, entry_id):
        """Get all crane operations for a container entry"""
        return CraneOperation.objects.filter(container_entry_id=entry_id).order_by(
            "-operation_date"
        )

    def _sync_crane_operation_date(self, entry, additional_crane_operation_date):
        """
        Sync the additional_crane_operation_date field with CraneOperation records.
        If a date is provided and no matching CraneOperation exists, create one.
        This maintains backward compatibility while populating the new model.
        """
        if additional_crane_operation_date:
            # Check if a CraneOperation already exists for this date
            operation_exists = CraneOperation.objects.filter(
                container_entry=entry, operation_date=additional_crane_operation_date
            ).exists()

            if not operation_exists:
                CraneOperation.objects.create(
                    container_entry=entry,
                    operation_date=additional_crane_operation_date,
                )
                self.logger.info(
                    f"Created CraneOperation for entry {entry.id} at {additional_crane_operation_date}"
                )

    def get_container_stats(self) -> dict:
        """
        Get comprehensive container entry statistics for dashboard.

        Returns:
            Dict with:
            - total: Total container entries
            - on_terminal: Containers currently on terminal (not exited)
            - laden: Laden containers on terminal
            - empty: Empty containers on terminal
            - entered_today: Containers entered today
            - exited_today: Containers exited today
            - companies: List of companies with container counts and laden/empty breakdown
            - total_storage_cost_usd: Total storage cost for containers on terminal (USD)
            - total_storage_cost_uzs: Total storage cost for containers on terminal (UZS)
        """
        from decimal import Decimal

        from django.db.models import Count, Q

        from apps.billing.services import StorageCostService

        today = timezone.now().date()

        # Handle both Russian and English status values (data migration inconsistency)
        laden_filter = Q(status="LADEN") | Q(status="Гружёный")
        empty_filter = Q(status="EMPTY") | Q(status="Порожний")

        # Aggregate all container stats in single query
        stats = ContainerEntry.objects.aggregate(
            total=Count("id"),
            on_terminal=Count("id", filter=Q(exit_date__isnull=True)),
            laden=Count("id", filter=Q(exit_date__isnull=True) & laden_filter),
            empty=Count("id", filter=Q(exit_date__isnull=True) & empty_filter),
            entered_today=Count("id", filter=Q(entry_time__date=today)),
            exited_today=Count("id", filter=Q(exit_date__date=today)),
        )

        # Company breakdown with laden/empty counts in single query
        company_stats = (
            ContainerEntry.objects.filter(exit_date__isnull=True, company__isnull=False)
            .values("company__id", "company__name", "company__slug")
            .annotate(
                count=Count("id"),
                laden=Count("id", filter=laden_filter),
                empty=Count("id", filter=empty_filter),
            )
            .filter(count__gt=0)
            .order_by("-count")
        )

        # Calculate total storage cost for containers on terminal
        total_usd = Decimal("0.00")
        total_uzs = Decimal("0.00")
        try:
            on_terminal_entries = ContainerEntry.objects.filter(
                exit_date__isnull=True
            ).select_related("container", "company")

            if on_terminal_entries.exists():
                storage_service = StorageCostService()
                cost_results = storage_service.calculate_bulk_costs(on_terminal_entries)
                for result in cost_results:
                    total_usd += result.total_usd
                    total_uzs += result.total_uzs
        except Exception as e:
            self.logger.warning(f"Failed to calculate storage costs for stats: {e}")

        self.logger.info(f"Retrieved container stats: {stats}")

        return {
            **stats,
            "companies": list(company_stats),
            "total_storage_cost_usd": str(total_usd),
            "total_storage_cost_uzs": str(total_uzs),
        }
