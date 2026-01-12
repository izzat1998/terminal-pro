"""
Tests for VehicleEntry КПП (Checkpoint Journal) functionality.

Focused on:
1. Workflow actions (Check-in, Cancel, Revert, Exit)
2. Business logic validation
3. API endpoint smoke tests
4. Field cascade clearing (complex logic)
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from apps.core.exceptions import BusinessLogicError
from apps.vehicles.filters import VehicleEntryFilter
from apps.vehicles.models import VehicleEntry
from apps.vehicles.serializers import VehicleEntrySerializer
from apps.vehicles.services.vehicle_entry_service import VehicleEntryService


# ============================================================================
# CHECK-IN Workflow (WAITING → ON_TERMINAL)
# ============================================================================


@pytest.mark.django_db
class TestCheckInWorkflow:
    """Tests for check-in workflow."""

    def test_check_in_success(self, customer_user, destination, admin_user):
        """Test successful check-in sets status and entry_time."""
        entry = VehicleEntry.objects.create(
            license_plate="CHECKIN01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="WAITING",
            customer=customer_user,
            destination=destination,
        )

        service = VehicleEntryService()
        result = service.check_in(
            license_plate=entry.license_plate,
            entry_photos=[],
            recorded_by=admin_user,
        )

        assert result.status == "ON_TERMINAL"
        assert result.entry_time is not None
        assert result.recorded_by == admin_user

    def test_check_in_wrong_status_fails(self, vehicle_entry):
        """Test check-in fails for vehicle already ON_TERMINAL."""
        service = VehicleEntryService()

        with pytest.raises(BusinessLogicError) as exc:
            service.check_in(license_plate=vehicle_entry.license_plate, entry_photos=[])

        assert "уже на терминале" in str(exc.value).lower()

    def test_check_in_case_insensitive(self, customer_user, destination, admin_user):
        """Test check-in works with lowercase license plate."""
        entry = VehicleEntry.objects.create(
            license_plate="UPPER01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="WAITING",
            customer=customer_user,
            destination=destination,
        )

        service = VehicleEntryService()
        result = service.check_in(
            license_plate="  upper01  ",  # lowercase + spaces
            entry_photos=[],
            recorded_by=admin_user,
        )

        assert result.id == entry.id


# ============================================================================
# CANCEL Workflow (WAITING → CANCELLED)
# ============================================================================


@pytest.mark.django_db
class TestCancelWorkflow:
    """Tests for cancel workflow."""

    def test_cancel_success(self, customer_user, destination):
        """Test successful cancellation."""
        entry = VehicleEntry.objects.create(
            license_plate="CANCEL01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="WAITING",
            customer=customer_user,
            destination=destination,
        )

        service = VehicleEntryService()
        result = service.cancel_by_id(entry_id=entry.id)

        assert result.status == "CANCELLED"

    def test_cancel_wrong_status_fails(self, vehicle_entry):
        """Test cancel fails for ON_TERMINAL vehicle."""
        service = VehicleEntryService()

        with pytest.raises(BusinessLogicError) as exc:
            service.cancel_by_id(entry_id=vehicle_entry.id)

        assert "только ожидающие" in str(exc.value).lower()


# ============================================================================
# REVERT Workflow (EXITED → ON_TERMINAL)
# ============================================================================


@pytest.mark.django_db
class TestRevertWorkflow:
    """Tests for admin revert functionality."""

    def test_revert_clears_exit_data(self, admin_user, destination):
        """Test revert clears exit_time and exit_load_status."""
        entry = VehicleEntry.objects.create(
            license_plate="REVERT01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="EXITED",
            destination=destination,
            entry_time=timezone.now() - timedelta(hours=3),
            exit_time=timezone.now() - timedelta(hours=1),
            exit_load_status="EMPTY",
            recorded_by=admin_user,
        )

        serializer = VehicleEntrySerializer(
            entry,
            data={
                "license_plate": entry.license_plate,
                "vehicle_type": entry.vehicle_type,
                "status": "ON_TERMINAL",
                "exit_time": None,
                "exit_load_status": None,
            },
            partial=True,
        )

        assert serializer.is_valid()
        result = serializer.save()
        result.refresh_from_db()

        assert result.status == "ON_TERMINAL"
        assert result.exit_time is None
        assert result.exit_load_status is None

    def test_revert_preserves_entry_time(self, admin_user, destination):
        """Test revert does not lose entry_time."""
        original_entry_time = timezone.now() - timedelta(hours=5)
        entry = VehicleEntry.objects.create(
            license_plate="REVERT02",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="EXITED",
            destination=destination,
            entry_time=original_entry_time,
            exit_time=timezone.now(),
            recorded_by=admin_user,
        )

        serializer = VehicleEntrySerializer(
            entry,
            data={"status": "ON_TERMINAL", "exit_time": None},
            partial=True,
        )
        serializer.is_valid()
        result = serializer.save()

        assert result.entry_time == original_entry_time


# ============================================================================
# EXIT Workflow (ON_TERMINAL → EXITED)
# ============================================================================


@pytest.mark.django_db
class TestExitWorkflow:
    """Tests for exit workflow."""

    def test_exit_success(self, vehicle_entry):
        """Test successful exit sets status and exit_time."""
        service = VehicleEntryService()
        exit_time = timezone.now()

        result = service.register_exit(
            license_plate=vehicle_entry.license_plate,
            exit_photos=[],
            exit_time=exit_time,
        )

        assert result.status == "EXITED"
        assert result.exit_time == exit_time

    def test_exit_time_before_entry_time_fails(self, admin_user, destination):
        """Test exit fails if exit_time < entry_time."""
        entry_time = timezone.now()
        entry = VehicleEntry.objects.create(
            license_plate="TIMEVAL01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            destination=destination,
            entry_time=entry_time,
            recorded_by=admin_user,
            status="ON_TERMINAL",
        )

        service = VehicleEntryService()
        past_time = entry_time - timedelta(hours=1)

        with pytest.raises(BusinessLogicError) as exc:
            service.register_exit(
                license_plate=entry.license_plate,
                exit_photos=[],
                exit_time=past_time,
            )

        assert "раньше" in str(exc.value).lower()

    def test_exit_waiting_vehicle_fails(self, customer_user, destination):
        """Test cannot exit vehicle that hasn't entered yet."""
        entry = VehicleEntry.objects.create(
            license_plate="WAIT01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="WAITING",
            customer=customer_user,
            destination=destination,
        )

        service = VehicleEntryService()

        with pytest.raises(BusinessLogicError) as exc:
            service.register_exit(
                license_plate=entry.license_plate,
                exit_photos=[],
                exit_time=timezone.now(),
            )

        assert "не въехал" in str(exc.value).lower()


# ============================================================================
# Field Cascade Clearing (Complex Business Logic)
# ============================================================================


@pytest.mark.django_db
class TestFieldCascadeClearing:
    """Tests for field cascade clearing - this is complex logic worth testing."""

    def test_cargo_to_light_clears_all_cargo_fields(self, admin_user, destination):
        """Test CARGO→LIGHT clears transport_type, load_status, cargo_type, container fields."""
        entry = VehicleEntry.objects.create(
            license_plate="CASCADE01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            entry_load_status="LOADED",
            cargo_type="CONTAINER",
            container_size="40F",
            container_load_status="LOADED",
            destination=destination,
            entry_time=timezone.now(),
            recorded_by=admin_user,
            status="ON_TERMINAL",
        )

        serializer = VehicleEntrySerializer(
            entry,
            data={
                "license_plate": entry.license_plate,
                "vehicle_type": "LIGHT",
                "visitor_type": "GUEST",
            },
            partial=True,
        )

        assert serializer.is_valid()
        result = serializer.save()
        result.refresh_from_db()

        # All cargo fields should be cleared
        assert result.transport_type is None
        assert result.entry_load_status is None
        assert result.cargo_type is None
        assert result.container_size is None
        assert result.container_load_status is None

    def test_loaded_to_empty_clears_cargo_details(self, admin_user, destination):
        """Test LOADED→EMPTY clears cargo_type and container fields."""
        entry = VehicleEntry.objects.create(
            license_plate="CASCADE02",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            entry_load_status="LOADED",
            cargo_type="CONTAINER",
            container_size="40F",
            container_load_status="LOADED",
            destination=destination,
            entry_time=timezone.now(),
            recorded_by=admin_user,
            status="ON_TERMINAL",
        )

        serializer = VehicleEntrySerializer(
            entry,
            data={
                "license_plate": entry.license_plate,
                "vehicle_type": "CARGO",
                "entry_load_status": "EMPTY",
            },
            partial=True,
        )

        assert serializer.is_valid()
        result = serializer.save()
        result.refresh_from_db()

        assert result.entry_load_status == "EMPTY"
        assert result.cargo_type is None
        assert result.container_size is None
        assert result.container_load_status is None


# ============================================================================
# Conditional Validation (Business Rules)
# ============================================================================


@pytest.mark.django_db
class TestConditionalValidation:
    """Tests for conditional field validation."""

    def test_light_requires_visitor_type(self):
        """LIGHT vehicle must have visitor_type."""
        serializer = VehicleEntrySerializer(
            data={"license_plate": "VAL01", "vehicle_type": "LIGHT"}
        )

        assert not serializer.is_valid()
        assert "visitor_type" in str(serializer.errors).lower()

    def test_cargo_requires_transport_and_load_status(self):
        """CARGO vehicle must have transport_type and entry_load_status."""
        serializer = VehicleEntrySerializer(
            data={"license_plate": "VAL02", "vehicle_type": "CARGO"}
        )

        assert not serializer.is_valid()
        errors = str(serializer.errors).lower()
        assert "transport_type" in errors or "entry_load_status" in errors

    def test_loaded_cargo_requires_cargo_type(self):
        """LOADED cargo must specify cargo_type."""
        serializer = VehicleEntrySerializer(
            data={
                "license_plate": "VAL03",
                "vehicle_type": "CARGO",
                "transport_type": "TRUCK",
                "entry_load_status": "LOADED",
                # Missing cargo_type
            }
        )

        assert not serializer.is_valid()
        assert "cargo_type" in str(serializer.errors).lower()

    def test_container_requires_size_and_status(self):
        """CONTAINER cargo must have container_size and container_load_status."""
        serializer = VehicleEntrySerializer(
            data={
                "license_plate": "VAL04",
                "vehicle_type": "CARGO",
                "transport_type": "TRUCK",
                "entry_load_status": "LOADED",
                "cargo_type": "CONTAINER",
                # Missing container_size and container_load_status
            }
        )

        assert not serializer.is_valid()
        errors = str(serializer.errors).lower()
        assert "container_size" in errors or "container_load_status" in errors


# ============================================================================
# API Endpoint Smoke Tests
# ============================================================================


@pytest.mark.django_db
class TestAPIEndpoints:
    """Smoke tests for API endpoints."""

    def test_list_entries(self, authenticated_client, vehicle_entry):
        """Test GET /entries/ returns list."""
        response = authenticated_client.get("/api/vehicles/entries/")
        assert response.status_code == status.HTTP_200_OK

    def test_create_vehicle(self, authenticated_client):
        """Test POST /entries/ creates vehicle."""
        response = authenticated_client.post(
            "/api/vehicles/entries/",
            {
                "license_plate": "API01",
                "vehicle_type": "LIGHT",
                "visitor_type": "GUEST",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "ON_TERMINAL"

    def test_exit_endpoint(self, authenticated_client, vehicle_entry):
        """Test POST /entries/exit/ exits vehicle."""
        response = authenticated_client.post(
            "/api/vehicles/entries/exit/",
            {
                "license_plate": vehicle_entry.license_plate,
                "exit_time": timezone.now().isoformat(),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["status"] == "EXITED"

    def test_statistics_endpoint(self, authenticated_client, vehicle_entry):
        """Test GET /statistics/ returns stats."""
        response = authenticated_client.get("/api/vehicles/statistics/")
        assert response.status_code == status.HTTP_200_OK
        assert "current" in response.data["data"]


# ============================================================================
# Filter Tests (Only Key Custom Logic)
# ============================================================================


@pytest.mark.django_db
class TestFilters:
    """Tests for custom filter logic - not testing django-filters itself."""

    @pytest.fixture
    def sample_entries(self, admin_user, customer_user, destination):
        """Create sample entries for filter testing."""
        VehicleEntry.objects.create(
            license_plate="LIGHT01",
            vehicle_type="LIGHT",
            visitor_type="EMPLOYEE",
            status="ON_TERMINAL",
            entry_time=timezone.now(),
            recorded_by=admin_user,
        )
        VehicleEntry.objects.create(
            license_plate="CARGO01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="EXITED",
            destination=destination,
            entry_time=timezone.now() - timedelta(hours=2),
            exit_time=timezone.now(),
            recorded_by=admin_user,
        )
        VehicleEntry.objects.create(
            license_plate="WAIT01",
            vehicle_type="CARGO",
            transport_type="GAZELLE",
            status="WAITING",
            customer=customer_user,
            destination=destination,
        )

    def test_filter_by_russian_status(self, sample_entries):
        """Test our custom Russian status mapping works."""
        qs = VehicleEntry.objects.all()
        filterset = VehicleEntryFilter(data={"status": "На терминале"}, queryset=qs)
        assert filterset.qs.count() == 1

    def test_filter_combined(self, sample_entries):
        """Test combining multiple filters."""
        qs = VehicleEntry.objects.all()
        filterset = VehicleEntryFilter(
            data={"status": "WAITING", "vehicle_type": "CARGO"},
            queryset=qs,
        )
        assert filterset.qs.count() == 1
        assert filterset.qs.first().license_plate == "WAIT01"

    def test_search_text_comprehensive(self, sample_entries):
        """Test search_text searches across multiple fields."""
        qs = VehicleEntry.objects.all()
        filterset = VehicleEntryFilter(data={"search_text": "LIGHT"}, queryset=qs)
        assert filterset.qs.count() == 1


# ============================================================================
# Statistics Tests
# ============================================================================


@pytest.mark.django_db
class TestStatistics:
    """Tests for statistics calculations."""

    def test_on_terminal_count(self, admin_user, destination):
        """Test total_on_terminal count is accurate."""
        from apps.vehicles.services.statistics_service import VehicleStatisticsService

        # Create 3 ON_TERMINAL vehicles
        for i in range(3):
            VehicleEntry.objects.create(
                license_plate=f"STAT0{i}",
                vehicle_type="LIGHT",
                visitor_type="GUEST",
                status="ON_TERMINAL",
                entry_time=timezone.now(),
                recorded_by=admin_user,
            )
        # Create 1 EXITED (should not count)
        VehicleEntry.objects.create(
            license_plate="STAT_EXIT",
            vehicle_type="LIGHT",
            visitor_type="GUEST",
            status="EXITED",
            entry_time=timezone.now() - timedelta(hours=1),
            exit_time=timezone.now(),
            recorded_by=admin_user,
        )

        service = VehicleStatisticsService()
        stats = service.get_current_statistics()

        assert stats["total_on_terminal"] == 3

    def test_overstayer_detection(self, admin_user, destination):
        """Test overstayer detection with threshold."""
        from apps.vehicles.services.statistics_service import VehicleStatisticsService

        # Vehicle on terminal for 30 hours
        VehicleEntry.objects.create(
            license_plate="OVERSTAY01",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="ON_TERMINAL",
            destination=destination,
            entry_time=timezone.now() - timedelta(hours=30),
            recorded_by=admin_user,
        )

        service = VehicleStatisticsService()

        # With 24h threshold, should detect 1 overstayer
        result = service.get_overstayers(threshold_hours=24)
        assert result["count"] == 1

        # With 48h threshold, should detect 0
        result = service.get_overstayers(threshold_hours=48)
        assert result["count"] == 0
