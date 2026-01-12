"""
Tests for VehicleEntry and Destination models.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.vehicles.models import Destination, VehicleEntry


User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return CustomUser.objects.create_user(
        username="testoperator", email="operator@terminal.com", password="testpass123"
    )


@pytest.fixture
def customer():
    """Create a customer user."""
    return CustomUser.objects.create(
        username="customer_test",
        first_name="Test Customer",
        phone_number="+998901234567",
        user_type="customer",
    )


@pytest.fixture
def destination():
    """Create a test destination."""
    return Destination.objects.create(
        name="Warehouse A",
        zone="K1",
    )


@pytest.fixture
def vehicle_entry(user, destination):
    """Create a test vehicle entry."""
    return VehicleEntry.objects.create(
        license_plate="01A123BC",
        vehicle_type="CARGO",
        transport_type="TRUCK",
        entry_load_status="LOADED",
        cargo_type="CONTAINER",
        destination=destination,
        entry_time=timezone.now(),
        recorded_by=user,
        status="ON_TERMINAL",
    )


@pytest.mark.django_db
class TestDestinationModel:
    """Tests for Destination model."""

    def test_destination_creation(self):
        """Test creating a destination with valid data."""
        dest = Destination.objects.create(
            name="Container Yard",
            zone="K2",
        )

        assert dest.name == "Container Yard"
        assert dest.zone == "K2"
        assert dest.is_active is True
        assert dest.code == "container-yard"  # Auto-generated slug

    def test_destination_auto_code_generation(self):
        """Test that code is auto-generated from name."""
        dest = Destination.objects.create(
            name="Main Loading Area",
            zone="H1",
        )
        assert dest.code == "main-loading-area"

    def test_destination_custom_code(self):
        """Test that custom code is preserved."""
        dest = Destination.objects.create(
            name="Custom Area",
            code="custom-code-123",
            zone="K3",
        )
        assert dest.code == "custom-code-123"

    def test_destination_str_representation(self):
        """Test string representation."""
        dest = Destination.objects.create(name="Test Area", zone="K1")
        assert str(dest) == "Test Area (K1)"

    def test_destination_ordering(self):
        """Test destinations are ordered by zone, then name."""
        Destination.objects.create(name="Area B", zone="K2")
        Destination.objects.create(name="Area A", zone="K1")
        Destination.objects.create(name="Area C", zone="K1")

        destinations = list(Destination.objects.all())
        assert destinations[0].zone == "K1"
        assert destinations[0].name == "Area A"
        assert destinations[1].zone == "K1"
        assert destinations[1].name == "Area C"
        assert destinations[2].zone == "K2"

    def test_destination_unique_name(self):
        """Test that destination names must be unique."""
        Destination.objects.create(name="Unique Destination", zone="K1")

        with pytest.raises(IntegrityError):
            Destination.objects.create(name="Unique Destination", zone="K2")


@pytest.mark.django_db
class TestVehicleEntryModel:
    """Tests for VehicleEntry model."""

    def test_vehicle_entry_creation(self, user, destination):
        """Test creating a vehicle entry with valid data."""
        entry = VehicleEntry.objects.create(
            license_plate="01A456BC",
            vehicle_type="CARGO",
            transport_type="PLATFORM",
            entry_load_status="LOADED",
            cargo_type="METAL",
            destination=destination,
            entry_time=timezone.now(),
            recorded_by=user,
        )

        assert entry.license_plate == "01A456BC"
        assert entry.vehicle_type == "CARGO"
        assert entry.transport_type == "PLATFORM"
        assert entry.status == "ON_TERMINAL"  # Default status

    def test_vehicle_entry_light_vehicle(self, user):
        """Test creating a light vehicle entry."""
        entry = VehicleEntry.objects.create(
            license_plate="01A789BC",
            vehicle_type="LIGHT",
            visitor_type="EMPLOYEE",
            entry_time=timezone.now(),
            recorded_by=user,
        )

        assert entry.vehicle_type == "LIGHT"
        assert entry.visitor_type == "EMPLOYEE"
        assert entry.transport_type is None  # Not required for light vehicles

    def test_vehicle_entry_str_representation(self, vehicle_entry):
        """Test string representation."""
        expected = f"{vehicle_entry.license_plate} - Грузовой автомобиль - На терминале"
        assert str(vehicle_entry) == expected

    def test_is_on_terminal_property(self, vehicle_entry):
        """Test is_on_terminal property."""
        assert vehicle_entry.is_on_terminal is True

        vehicle_entry.status = "EXITED"
        assert vehicle_entry.is_on_terminal is False

    def test_dwell_time_hours_property(self, vehicle_entry):
        """Test dwell time calculation."""
        # No exit time - should return None
        assert vehicle_entry.dwell_time_hours is None

        # Set exit time 2 hours after entry
        vehicle_entry.exit_time = vehicle_entry.entry_time + timedelta(hours=2)
        vehicle_entry.save()

        assert vehicle_entry.dwell_time_hours == 2.0

    def test_unique_active_vehicle_constraint(self, user):
        """Test that same plate can't be ON_TERMINAL twice."""
        VehicleEntry.objects.create(
            license_plate="UNIQUE123",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="ON_TERMINAL",
            entry_time=timezone.now(),
            recorded_by=user,
        )

        # Should raise error for duplicate active plate
        with pytest.raises(IntegrityError):
            VehicleEntry.objects.create(
                license_plate="UNIQUE123",
                vehicle_type="CARGO",
                transport_type="TRUCK",
                status="ON_TERMINAL",
                entry_time=timezone.now(),
                recorded_by=user,
            )

    def test_same_plate_allowed_after_exit(self, user):
        """Test that same plate can enter again after exiting."""
        # First entry - exits
        entry1 = VehicleEntry.objects.create(
            license_plate="REENTRY123",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="EXITED",
            entry_time=timezone.now() - timedelta(hours=5),
            exit_time=timezone.now() - timedelta(hours=2),
            recorded_by=user,
        )

        # Second entry - should succeed
        entry2 = VehicleEntry.objects.create(
            license_plate="REENTRY123",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="ON_TERMINAL",
            entry_time=timezone.now(),
            recorded_by=user,
        )

        assert entry2.id is not None
        assert entry1.license_plate == entry2.license_plate

    def test_vehicle_entry_with_customer(self, customer, destination):
        """Test vehicle entry linked to customer (pre-order flow)."""
        entry = VehicleEntry.objects.create(
            license_plate="CUST001",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="WAITING",  # Customer pre-order status
            customer=customer,
            destination=destination,
        )

        assert entry.customer == customer
        assert entry.status == "WAITING"

    def test_vehicle_entry_status_transitions(self, vehicle_entry):
        """Test status transitions."""
        # WAITING -> ON_TERMINAL
        vehicle_entry.status = "WAITING"
        vehicle_entry.save()
        assert vehicle_entry.status == "WAITING"

        vehicle_entry.status = "ON_TERMINAL"
        vehicle_entry.entry_time = timezone.now()
        vehicle_entry.save()
        assert vehicle_entry.is_on_terminal is True

        # ON_TERMINAL -> EXITED
        vehicle_entry.status = "EXITED"
        vehicle_entry.exit_time = timezone.now()
        vehicle_entry.save()
        assert vehicle_entry.is_on_terminal is False

    def test_container_cargo_fields(self, user, destination):
        """Test container-specific cargo fields."""
        entry = VehicleEntry.objects.create(
            license_plate="CONT001",
            vehicle_type="CARGO",
            transport_type="PLATFORM",
            entry_load_status="LOADED",
            cargo_type="CONTAINER",
            container_size="40F",
            container_load_status="LOADED",
            destination=destination,
            entry_time=timezone.now(),
            recorded_by=user,
        )

        assert entry.cargo_type == "CONTAINER"
        assert entry.container_size == "40F"
        assert entry.container_load_status == "LOADED"


@pytest.mark.django_db
class TestVehicleEntryWorkflow:
    """Integration tests for vehicle entry workflow."""

    def test_complete_cargo_vehicle_workflow(self, user, destination):
        """Test complete workflow: entry -> on terminal -> exit."""
        # Step 1: Vehicle enters terminal
        entry = VehicleEntry.objects.create(
            license_plate="WORKFLOW01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            entry_load_status="LOADED",
            cargo_type="EQUIPMENT",
            destination=destination,
            entry_time=timezone.now(),
            recorded_by=user,
            status="ON_TERMINAL",
        )
        assert entry.is_on_terminal is True

        # Step 2: Vehicle exits terminal
        entry.status = "EXITED"
        entry.exit_time = timezone.now() + timedelta(hours=3)
        entry.exit_load_status = "EMPTY"
        entry.save()

        assert entry.is_on_terminal is False
        assert entry.exit_load_status == "EMPTY"
        assert entry.dwell_time_hours is not None

    def test_preorder_to_entry_workflow(self, customer, user, destination):
        """Test workflow from customer pre-order to actual entry."""
        # Step 1: Customer creates pre-order (WAITING status)
        entry = VehicleEntry.objects.create(
            license_plate="PREORD01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="WAITING",
            customer=customer,
            destination=destination,
        )
        assert entry.status == "WAITING"
        assert entry.entry_time is None  # Not yet entered

        # Step 2: Manager checks in the vehicle at gate
        entry.status = "ON_TERMINAL"
        entry.entry_time = timezone.now()
        entry.recorded_by = user
        entry.entry_load_status = "LOADED"
        entry.cargo_type = "CONTAINER"
        entry.save()

        assert entry.is_on_terminal is True
        assert entry.recorded_by == user

    def test_create_vehicle_via_serializer_without_photos(self, user, destination):
        """Test creating vehicle via serializer without photos (web interface use case)."""
        from apps.vehicles.serializers import VehicleEntrySerializer

        # When: Create vehicle without entry_photo_files (allowed for web interface)
        serializer = VehicleEntrySerializer(
            data={
                "license_plate": "NOPHOTO01",
                "vehicle_type": "CARGO",
                "transport_type": "TRUCK",
                "entry_load_status": "LOADED",
                "cargo_type": "METAL",
                "destination": destination.id,
            }
        )

        # Then: Should be valid without photos
        assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
        entry = serializer.save(recorded_by=user)

        assert entry.license_plate == "NOPHOTO01"
        assert entry.vehicle_type == "CARGO"
        assert entry.transport_type == "TRUCK"
        assert entry.entry_load_status == "LOADED"
        assert entry.cargo_type == "METAL"
        assert entry.destination == destination
        assert entry.recorded_by == user
        # Should have no photos
        assert entry.entry_photos.count() == 0


@pytest.mark.django_db
class TestVehicleExitWorkflow:
    """Integration tests for vehicle exit workflow and auto-status logic."""

    def test_exit_via_service_sets_status_and_notifies(self, user, destination):
        """Test exit via service layer auto-sets status to EXITED."""
        from apps.vehicles.services.vehicle_entry_service import VehicleEntryService

        # Given: Vehicle on terminal
        entry = VehicleEntry.objects.create(
            license_plate="SERVICE01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            entry_load_status="LOADED",
            cargo_type="GENERAL",
            destination=destination,
            entry_time=timezone.now() - timedelta(hours=2),
            recorded_by=user,
            status="ON_TERMINAL",
        )
        assert entry.status == "ON_TERMINAL"

        # When: Register exit via service
        service = VehicleEntryService()
        exit_time = timezone.now()

        updated_entry = service.register_exit(
            license_plate=entry.license_plate,
            exit_photos=[],
            exit_time=exit_time,
            exit_load_status="EMPTY",
        )

        # Then: Status auto-changed to EXITED
        assert updated_entry.status == "EXITED"
        assert updated_entry.exit_time == exit_time
        assert updated_entry.exit_load_status == "EMPTY"
        assert updated_entry.is_on_terminal is False
        # Note: Notification testing requires mocking TelegramNotificationService

    def test_exit_via_serializer_auto_sets_status(self, user, destination):
        """Test exit via serializer auto-sets status (safety net)."""
        from apps.vehicles.serializers import VehicleEntrySerializer

        # Given: Vehicle on terminal
        entry = VehicleEntry.objects.create(
            license_plate="SERIAL01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            entry_load_status="LOADED",
            cargo_type="GENERAL",
            destination=destination,
            entry_time=timezone.now() - timedelta(hours=2),
            recorded_by=user,
            status="ON_TERMINAL",
        )
        assert entry.status == "ON_TERMINAL"

        # When: Update via serializer with exit_time
        exit_time = timezone.now()
        serializer = VehicleEntrySerializer(
            entry,
            data={
                "license_plate": entry.license_plate,
                "vehicle_type": entry.vehicle_type,
                "exit_time": exit_time.isoformat(),
            },
            partial=True,
        )
        assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
        updated_entry = serializer.save()

        # Then: Status auto-changed to EXITED
        updated_entry.refresh_from_db()
        assert updated_entry.status == "EXITED"
        assert updated_entry.exit_time is not None
        assert updated_entry.is_on_terminal is False

    def test_exit_time_validation_service_layer(self, user, destination):
        """Test service validates exit_time must be after entry_time."""
        from apps.core.exceptions import BusinessLogicError
        from apps.vehicles.services.vehicle_entry_service import VehicleEntryService

        # Given: Vehicle entered 2 hours ago
        entry_time = timezone.now() - timedelta(hours=2)
        entry = VehicleEntry.objects.create(
            license_plate="TIMEVAL01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            destination=destination,
            entry_time=entry_time,
            recorded_by=user,
            status="ON_TERMINAL",
        )

        # When: Try to set exit time BEFORE entry time
        service = VehicleEntryService()
        past_time = entry_time - timedelta(hours=1)

        # Then: Raises BusinessLogicError
        with pytest.raises(BusinessLogicError) as exc_info:
            service.register_exit(
                license_plate=entry.license_plate,
                exit_photos=[],
                exit_time=past_time,
            )

        assert "раньше" in str(exc_info.value).lower()  # "earlier" in Russian

    def test_cannot_exit_already_exited_vehicle(self, user, destination):
        """Test cannot exit vehicle that already exited."""
        from apps.core.exceptions import BusinessLogicError
        from apps.vehicles.services.vehicle_entry_service import VehicleEntryService

        # Given: Vehicle already exited
        entry = VehicleEntry.objects.create(
            license_plate="EXITED01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            destination=destination,
            entry_time=timezone.now() - timedelta(hours=3),
            exit_time=timezone.now() - timedelta(hours=1),
            recorded_by=user,
            status="EXITED",
        )

        # When: Try to exit again
        service = VehicleEntryService()

        # Then: Raises BusinessLogicError
        with pytest.raises(BusinessLogicError) as exc_info:
            service.register_exit(
                license_plate=entry.license_plate,
                exit_photos=[],
                exit_time=timezone.now(),
            )

        assert entry.license_plate in str(exc_info.value)

    def test_serializer_does_not_change_status_if_explicitly_set(
        self, user, destination
    ):
        """Test serializer respects explicitly set status."""
        from apps.vehicles.serializers import VehicleEntrySerializer

        # Given: Vehicle on terminal
        entry = VehicleEntry.objects.create(
            license_plate="EXPLICIT01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            destination=destination,
            entry_time=timezone.now() - timedelta(hours=2),
            recorded_by=user,
            status="ON_TERMINAL",
        )

        # When: Update with exit_time AND explicit status
        exit_time = timezone.now()
        serializer = VehicleEntrySerializer(
            entry,
            data={
                "license_plate": entry.license_plate,
                "vehicle_type": entry.vehicle_type,
                "exit_time": exit_time.isoformat(),
                "status": "ON_TERMINAL",  # Explicitly keep ON_TERMINAL
            },
            partial=True,
        )
        assert serializer.is_valid()
        updated_entry = serializer.save()

        # Then: Status remains ON_TERMINAL (respects explicit setting)
        updated_entry.refresh_from_db()
        assert updated_entry.status == "ON_TERMINAL"
        assert updated_entry.exit_time is not None

    def test_dwell_time_calculation_with_exit(self, user, destination):
        """Test dwell_time_hours property calculates correctly with exit time."""
        # Given: Vehicle entry and exit times
        entry_time = timezone.now() - timedelta(hours=5)
        exit_time = timezone.now() - timedelta(hours=2)

        entry = VehicleEntry.objects.create(
            license_plate="DWELL01",
            vehicle_type="LIGHT",
            visitor_type="GUEST",
            entry_time=entry_time,
            exit_time=exit_time,
            recorded_by=user,
            status="EXITED",
        )

        # Then: Dwell time calculated correctly
        assert entry.dwell_time_hours == pytest.approx(3.0, rel=0.01)
