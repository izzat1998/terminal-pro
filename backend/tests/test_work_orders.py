"""
Tests for WorkOrder model, service, and API endpoints.

Simplified 2-status workflow: PENDING → COMPLETED
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry, WorkOrder, TerminalVehicle
from apps.terminal_operations.services.work_order_service import (
    WorkOrderAlreadyExistsError,
    WorkOrderNotFoundError,
    WorkOrderService,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return CustomUser.objects.create_user(
        username="testadmin",
        email="admin@example.com",
        password="testpass123",
        user_type="admin",
        is_staff=True,
    )


@pytest.fixture
def operator(db):
    """Create an operator user."""
    return CustomUser.objects.create(
        username="operator_test",
        first_name="Test Operator",
        phone_number="+998901234567",
        user_type="manager",
        bot_access=True,
    )


@pytest.fixture
def terminal_vehicle(db, operator):
    """Create a terminal vehicle."""
    return TerminalVehicle.objects.create(
        name="Погрузчик-01",
        vehicle_type="REACHSTACKER",
        is_active=True,
        operator=operator,
    )


@pytest.fixture
def container(db):
    """Create a test container."""
    return Container.objects.create(
        container_number="MSKU1234567",
        iso_type="42G1",
    )


@pytest.fixture
def container_entry(container, admin_user):
    """Create a test container entry."""
    return ContainerEntry.objects.create(
        container=container,
        status="LADEN",
        transport_type="TRUCK",
        transport_number="ABC123",
        recorded_by=admin_user,
    )


@pytest.fixture
def container_entry_factory(db, admin_user):
    """Factory for creating container entries."""

    def _create_entry(container_number=None):
        import random
        import string

        if container_number is None:
            prefix = "".join(random.choices(string.ascii_uppercase, k=4))
            suffix = "".join(random.choices(string.digits, k=7))
            container_number = f"{prefix}{suffix}"

        container = Container.objects.create(
            container_number=container_number,
            iso_type="42G1",
        )
        return ContainerEntry.objects.create(
            container=container,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="TEST001",
            recorded_by=admin_user,
        )

    return _create_entry


@pytest.fixture
def work_order(container_entry, admin_user):
    """Create a test work order (PENDING status)."""
    return WorkOrder.objects.create(
        container_entry=container_entry,
        status="PENDING",
        priority="MEDIUM",
        target_zone="A",
        target_row=1,
        target_bay=1,
        target_tier=1,
        target_sub_slot="A",
        created_by=admin_user,
    )


@pytest.fixture
def assigned_work_order(work_order, terminal_vehicle):
    """Create a work order assigned to a vehicle."""
    work_order.assigned_to_vehicle = terminal_vehicle
    work_order.save()
    return work_order


@pytest.fixture
def work_order_service():
    """Create WorkOrderService instance."""
    return WorkOrderService()


# ============================================================================
# Model Tests
# ============================================================================


@pytest.mark.django_db
class TestWorkOrderModel:
    """Tests for WorkOrder model."""

    def test_work_order_creation(self, container_entry, admin_user):
        """Test creating a work order with valid data."""
        work_order = WorkOrder.objects.create(
            container_entry=container_entry,
            status="PENDING",
            priority="HIGH",
            target_zone="A",
            target_row=3,
            target_bay=5,
            target_tier=2,
            target_sub_slot="A",
            created_by=admin_user,
        )

        assert work_order.container_entry == container_entry
        assert work_order.status == "PENDING"
        assert work_order.priority == "HIGH"
        assert work_order.order_number is not None
        assert work_order.order_number.startswith("WO-")

    def test_work_order_auto_generated_order_number(self, container_entry, admin_user):
        """Test that order numbers are auto-generated uniquely."""
        order1 = WorkOrder.objects.create(
            container_entry=container_entry,
            target_zone="A",
            target_row=1,
            target_bay=1,
            target_tier=1,
            created_by=admin_user,
        )
        order2 = WorkOrder.objects.create(
            container_entry=container_entry,
            target_zone="A",
            target_row=1,
            target_bay=2,
            target_tier=1,
            created_by=admin_user,
        )

        assert order1.order_number != order2.order_number
        assert order1.order_number.startswith("WO-")
        assert order2.order_number.startswith("WO-")

    def test_target_coordinate_string(self, work_order):
        """Test target_coordinate_string property."""
        work_order.target_zone = "B"
        work_order.target_row = 5
        work_order.target_bay = 10
        work_order.target_tier = 3
        work_order.target_sub_slot = "B"
        work_order.save()

        assert work_order.target_coordinate_string == "B-R05-B10-T3-B"

    def test_status_choices(self, container_entry, admin_user):
        """Test valid status choices (simplified 2-status workflow)."""
        statuses = ["PENDING", "COMPLETED"]

        for status_choice in statuses:
            work_order = WorkOrder.objects.create(
                container_entry=container_entry,
                status=status_choice,
                target_zone="A",
                target_row=1,
                target_bay=1,
                target_tier=1,
                created_by=admin_user,
            )
            assert work_order.status == status_choice

    def test_priority_choices(self, container_entry, admin_user):
        """Test all valid priority choices."""
        priorities = ["LOW", "MEDIUM", "HIGH", "URGENT"]

        for priority in priorities:
            work_order = WorkOrder.objects.create(
                container_entry=container_entry,
                priority=priority,
                target_zone="A",
                target_row=1,
                target_bay=1,
                target_tier=1,
                created_by=admin_user,
            )
            assert work_order.priority == priority


# ============================================================================
# Service Tests
# ============================================================================


@pytest.mark.django_db
class TestWorkOrderServiceCreation:
    """Tests for WorkOrderService.create_work_order()."""

    def test_create_work_order_with_position(
        self, container_entry, admin_user, work_order_service
    ):
        """Test creating work order with explicit position."""
        work_order = work_order_service.create_work_order(
            container_entry_id=container_entry.id,
            zone="A",
            row=3,
            bay=5,
            tier=2,
            sub_slot="A",
            priority="HIGH",
            created_by=admin_user,
        )

        assert work_order.status == "PENDING"
        assert work_order.priority == "HIGH"
        assert work_order.target_zone == "A"
        assert work_order.target_row == 3
        assert work_order.target_bay == 5
        assert work_order.target_tier == 2

    def test_create_work_order_with_vehicle(
        self, container_entry, terminal_vehicle, admin_user, work_order_service
    ):
        """Test creating work order with vehicle assigned."""
        work_order = work_order_service.create_work_order(
            container_entry_id=container_entry.id,
            zone="A",
            row=3,
            bay=5,
            tier=2,
            assigned_to_vehicle_id=terminal_vehicle.id,
            created_by=admin_user,
        )

        assert work_order.status == "PENDING"  # Status stays PENDING until completed
        assert work_order.assigned_to_vehicle == terminal_vehicle

    def test_create_work_order_duplicate_active(
        self, container_entry, admin_user, work_order_service
    ):
        """Test that duplicate active work orders are rejected."""
        # Create first work order
        work_order_service.create_work_order(
            container_entry_id=container_entry.id,
            zone="A",
            row=1,
            bay=1,
            tier=1,
            created_by=admin_user,
        )

        # Try to create another for same container
        with pytest.raises(WorkOrderAlreadyExistsError):
            work_order_service.create_work_order(
                container_entry_id=container_entry.id,
                zone="A",
                row=1,
                bay=2,
                tier=1,
                created_by=admin_user,
            )


@pytest.mark.django_db
class TestWorkOrderServiceCreationEdgeCases:
    """Tests for WorkOrderService.create_work_order() edge cases."""

    def test_create_work_order_container_not_found(
        self, admin_user, work_order_service
    ):
        """Test error when container entry doesn't exist."""
        from apps.core.exceptions import BusinessLogicError

        with pytest.raises(BusinessLogicError) as exc_info:
            work_order_service.create_work_order(
                container_entry_id=99999,
                zone="A",
                row=1,
                bay=1,
                tier=1,
                created_by=admin_user,
            )

        assert "не найдена" in str(exc_info.value)
        assert exc_info.value.error_code == "CONTAINER_ENTRY_NOT_FOUND"

    def test_create_work_order_with_notes(
        self, container_entry, admin_user, work_order_service
    ):
        """Test creating work order with notes."""
        work_order = work_order_service.create_work_order(
            container_entry_id=container_entry.id,
            zone="A",
            row=1,
            bay=1,
            tier=1,
            notes="Handle with care - fragile cargo",
            created_by=admin_user,
        )

        assert work_order.notes == "Handle with care - fragile cargo"


@pytest.mark.django_db
class TestWorkOrderServiceAssignment:
    """Tests for WorkOrderService assignment methods."""

    def test_assign_to_vehicle(
        self, work_order, terminal_vehicle, work_order_service
    ):
        """Test assigning work order to vehicle."""
        result = work_order_service.assign_to_vehicle(
            work_order_id=work_order.id,
            vehicle_id=terminal_vehicle.id,
        )

        assert result.assigned_to_vehicle == terminal_vehicle

    def test_assign_work_order_not_found(self, terminal_vehicle, work_order_service):
        """Test error when work order doesn't exist."""
        with pytest.raises(WorkOrderNotFoundError):
            work_order_service.assign_to_vehicle(
                work_order_id=99999,
                vehicle_id=terminal_vehicle.id,
            )


@pytest.mark.django_db
class TestWorkOrderServiceWorkflow:
    """Tests for WorkOrderService workflow (simplified 2-status)."""

    def test_complete_order(self, assigned_work_order, operator, work_order_service):
        """Test completing work order."""
        # Mock the placement service to avoid actual position creation
        with patch.object(work_order_service, 'placement_service') as mock_placement:
            result = work_order_service.complete_order(
                work_order_id=assigned_work_order.id,
                operator=operator,
            )

            assert result.status == "COMPLETED"
            assert result.completed_at is not None
            mock_placement.assign_position.assert_called_once()

    def test_complete_order_from_pending(self, work_order, operator, work_order_service):
        """Test completing unassigned work order."""
        with patch.object(work_order_service, 'placement_service') as mock_placement:
            result = work_order_service.complete_order(
                work_order_id=work_order.id,
                operator=operator,
            )

            assert result.status == "COMPLETED"


@pytest.mark.django_db
class TestWorkOrderServiceQueries:
    """Tests for WorkOrderService query methods."""

    def test_get_vehicle_orders(
        self, container_entry_factory, terminal_vehicle, admin_user, work_order_service
    ):
        """Test getting orders assigned to a vehicle."""
        # Create multiple orders for this vehicle
        for i in range(3):
            entry = container_entry_factory()
            work_order_service.create_work_order(
                container_entry_id=entry.id,
                zone="A",
                row=i + 1,
                bay=1,
                tier=1,
                assigned_to_vehicle_id=terminal_vehicle.id,
                created_by=admin_user,
            )

        orders = work_order_service.get_vehicle_orders(vehicle_id=terminal_vehicle.id)

        assert len(orders) == 3

    def test_get_pending_orders(
        self, container_entry_factory, admin_user, work_order_service
    ):
        """Test getting unassigned pending orders."""
        # Create unassigned orders
        for i in range(2):
            entry = container_entry_factory()
            work_order_service.create_work_order(
                container_entry_id=entry.id,
                zone="A",
                row=i + 1,
                bay=1,
                tier=1,
                created_by=admin_user,
            )

        orders = work_order_service.get_pending_orders()
        assert len(orders) == 2
        for order in orders:
            assert order.status == "PENDING"

    def test_get_all_active_orders(
        self,
        container_entry_factory,
        terminal_vehicle,
        admin_user,
        work_order_service,
    ):
        """Test getting all active orders for control room dashboard."""
        # Create orders - all PENDING in simplified workflow
        entry1 = container_entry_factory()
        work_order_service.create_work_order(
            container_entry_id=entry1.id,
            zone="A",
            row=1,
            bay=1,
            tier=1,
            created_by=admin_user,
        )  # PENDING, unassigned

        entry2 = container_entry_factory()
        work_order_service.create_work_order(
            container_entry_id=entry2.id,
            zone="A",
            row=2,
            bay=1,
            tier=1,
            assigned_to_vehicle_id=terminal_vehicle.id,
            created_by=admin_user,
        )  # PENDING, assigned

        # Get all active orders
        orders = work_order_service.get_all_active_orders()

        assert len(orders) == 2
        for order in orders:
            assert order.status == "PENDING"


# ============================================================================
# API Tests
# ============================================================================


@pytest.mark.django_db
class TestWorkOrderAPI:
    """Tests for WorkOrder API endpoints."""

    def test_list_work_orders_authenticated(self, api_client, admin_user, work_order):
        """Test listing work orders requires authentication."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/terminal/work-orders/")

        assert response.status_code == status.HTTP_200_OK

    def test_list_work_orders_unauthenticated(self, api_client):
        """Test listing work orders without auth fails."""
        response = api_client.get("/api/terminal/work-orders/")
        # DRF can return either 401 or 403 depending on authentication backend
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_create_work_order_api(
        self, api_client, admin_user, container_entry
    ):
        """Test creating work order via API."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            "/api/terminal/work-orders/",
            {
                "container_entry_id": container_entry.id,
                "zone": "A",
                "row": 1,
                "bay": 1,
                "tier": 1,
                "priority": "HIGH",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["status"] == "PENDING"

    def test_assign_work_order_api(
        self, api_client, admin_user, work_order, terminal_vehicle
    ):
        """Test assigning work order via API."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f"/api/terminal/work-orders/{work_order.id}/assign/",
            {"vehicle_id": terminal_vehicle.id},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_pending_orders_api(self, api_client, admin_user, work_order):
        """Test getting pending orders."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/terminal/work-orders/pending/")

        assert response.status_code == status.HTTP_200_OK
        # Response can be paginated (results) or non-paginated (data)
        data = response.data.get("results") or response.data.get("data", [])
        assert len(data) >= 1

    def test_work_order_stats_api(self, api_client, admin_user, work_order):
        """Test work order statistics endpoint."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/terminal/work-orders/stats/")

        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.data
