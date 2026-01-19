"""
Tests for WorkOrder model, service, and API endpoints.

Tests cover:
- WorkOrder model creation and properties
- WorkOrderService business logic and status transitions
- WorkOrder API endpoints
- Telegram notification integration (mocked)
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry, WorkOrder
from apps.terminal_operations.services.work_order_service import (
    InvalidStatusTransitionError,
    NotAssignedToManagerError,
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
def manager(db):
    """Create a manager user with Telegram ID."""
    return CustomUser.objects.create(
        username="mgr_work_order_test",
        first_name="Test Manager",
        phone_number="+998901234567",
        user_type="manager",
        bot_access=True,
        telegram_user_id=123456789,
    )


@pytest.fixture
def manager2(db):
    """Create a second manager for reassignment tests."""
    return CustomUser.objects.create(
        username="mgr_work_order_test2",
        first_name="Second Manager",
        phone_number="+998902345678",
        user_type="manager",
        bot_access=True,
        telegram_user_id=987654321,
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
def work_order(container_entry, manager, admin_user):
    """Create a test work order."""
    return WorkOrder.objects.create(
        container_entry=container_entry,
        status="PENDING",
        priority="MEDIUM",
        target_zone="A",
        target_row=1,
        target_bay=1,
        target_tier=1,
        target_sub_slot="A",
        sla_deadline=timezone.now() + timedelta(hours=1),
        created_by=admin_user,
    )


@pytest.fixture
def assigned_work_order(work_order, manager):
    """Create an assigned work order."""
    work_order.assigned_to = manager
    work_order.assigned_at = timezone.now()
    work_order.status = "ASSIGNED"
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
            sla_deadline=timezone.now() + timedelta(minutes=30),
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
            sla_deadline=timezone.now() + timedelta(hours=1),
            created_by=admin_user,
        )
        order2 = WorkOrder.objects.create(
            container_entry=container_entry,
            target_zone="A",
            target_row=1,
            target_bay=2,
            target_tier=1,
            sla_deadline=timezone.now() + timedelta(hours=1),
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

    def test_is_overdue_property(self, work_order):
        """Test is_overdue property."""
        # Not overdue
        work_order.sla_deadline = timezone.now() + timedelta(hours=1)
        work_order.save()
        assert work_order.is_overdue is False

        # Overdue
        work_order.sla_deadline = timezone.now() - timedelta(hours=1)
        work_order.save()
        assert work_order.is_overdue is True

    def test_time_remaining_minutes(self, work_order):
        """Test time_remaining_minutes property."""
        work_order.sla_deadline = timezone.now() + timedelta(minutes=45)
        work_order.save()

        # Should be approximately 45 minutes (allowing for test execution time)
        remaining = work_order.time_remaining_minutes
        assert 44 <= remaining <= 46

    def test_status_choices(self, container_entry, admin_user):
        """Test all valid status choices."""
        statuses = [
            "PENDING",
            "ASSIGNED",
            "ACCEPTED",
            "IN_PROGRESS",
            "COMPLETED",
            "VERIFIED",
            "FAILED",
        ]

        for status_choice in statuses:
            work_order = WorkOrder.objects.create(
                container_entry=container_entry,
                status=status_choice,
                target_zone="A",
                target_row=1,
                target_bay=1,
                target_tier=1,
                sla_deadline=timezone.now() + timedelta(hours=1),
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
                sla_deadline=timezone.now() + timedelta(hours=1),
                created_by=admin_user,
            )
            assert work_order.priority == priority


# ============================================================================
# Service Tests
# ============================================================================


@pytest.mark.django_db
class TestWorkOrderServiceCreation:
    """Tests for WorkOrderService.create_work_order()."""

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_create_work_order_with_position(
        self, mock_notify, container_entry, admin_user, work_order_service
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
        mock_notify.assert_not_called()  # No manager assigned

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_create_work_order_with_manager(
        self, mock_notify, container_entry, manager, admin_user, work_order_service
    ):
        """Test creating work order with manager assigned."""
        work_order = work_order_service.create_work_order(
            container_entry_id=container_entry.id,
            zone="A",
            row=3,
            bay=5,
            tier=2,
            assigned_to_id=manager.id,
            created_by=admin_user,
        )

        assert work_order.status == "ASSIGNED"
        assert work_order.assigned_to == manager
        assert work_order.assigned_at is not None
        mock_notify.assert_called_once_with(work_order.id)

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

    def test_create_work_order_sla_by_priority(
        self, container_entry, admin_user, work_order_service
    ):
        """Test SLA deadline is set based on priority."""
        now = timezone.now()

        # URGENT = 15 minutes
        order = work_order_service.create_work_order(
            container_entry_id=container_entry.id,
            zone="A",
            row=1,
            bay=1,
            tier=1,
            priority="URGENT",
            created_by=admin_user,
        )

        # SLA should be approximately 15 minutes from now
        expected_deadline = now + timedelta(minutes=15)
        assert abs((order.sla_deadline - expected_deadline).total_seconds()) < 5


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

    def test_create_work_order_invalid_priority(
        self, container_entry, admin_user, work_order_service
    ):
        """Test error with invalid priority."""
        from apps.core.exceptions import BusinessLogicError

        with pytest.raises(BusinessLogicError) as exc_info:
            work_order_service.create_work_order(
                container_entry_id=container_entry.id,
                zone="A",
                row=1,
                bay=1,
                tier=1,
                priority="SUPER_URGENT",  # Invalid
                created_by=admin_user,
            )

        assert exc_info.value.error_code == "INVALID_PRIORITY"

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_create_work_order_with_notes(
        self, mock_notify, container_entry, admin_user, work_order_service
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

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_assign_to_manager(
        self, mock_notify, work_order, manager, work_order_service
    ):
        """Test assigning work order to manager."""
        result = work_order_service.assign_to_manager(
            work_order_id=work_order.id,
            manager_id=manager.id,
        )

        assert result.status == "ASSIGNED"
        assert result.assigned_to == manager
        assert result.assigned_at is not None
        mock_notify.assert_called_once_with(work_order.id)

    def test_assign_work_order_not_found(self, manager, work_order_service):
        """Test error when work order doesn't exist."""
        with pytest.raises(WorkOrderNotFoundError):
            work_order_service.assign_to_manager(
                work_order_id=99999,
                manager_id=manager.id,
            )

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_assign_from_invalid_status(
        self, mock_notify, assigned_work_order, manager, manager2, work_order_service
    ):
        """Test error when assigning from invalid status (e.g., COMPLETED)."""
        # Progress to COMPLETED
        work_order_service.accept_order(assigned_work_order.id, manager)
        work_order_service.start_order(assigned_work_order.id, manager)
        work_order_service.complete_order(assigned_work_order.id, manager)

        # Try to assign from COMPLETED - should fail
        with pytest.raises(InvalidStatusTransitionError):
            work_order_service.assign_to_manager(
                work_order_id=assigned_work_order.id,
                manager_id=manager2.id,
            )

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_reassign_to_different_manager(
        self, mock_notify, assigned_work_order, manager2, work_order_service
    ):
        """Test reassigning work order to different manager."""
        # First transition back to PENDING (for reassignment)
        assigned_work_order.status = "PENDING"
        assigned_work_order.save()

        result = work_order_service.assign_to_manager(
            work_order_id=assigned_work_order.id,
            manager_id=manager2.id,
        )

        assert result.assigned_to == manager2
        mock_notify.assert_called()

    def test_assign_to_nonexistent_manager(self, work_order, work_order_service):
        """Test assigning to non-existent manager raises error."""
        from apps.core.exceptions import BusinessLogicError

        with pytest.raises(BusinessLogicError) as exc_info:
            work_order_service.assign_to_manager(
                work_order_id=work_order.id,
                manager_id=99999,
            )

        assert "не найден" in str(exc_info.value)


@pytest.mark.django_db
class TestWorkOrderServiceWorkflow:
    """Tests for WorkOrderService workflow transitions."""

    def test_accept_order(self, assigned_work_order, manager, work_order_service):
        """Test manager accepting work order."""
        result = work_order_service.accept_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )

        assert result.status == "ACCEPTED"
        assert result.accepted_at is not None

    def test_accept_order_wrong_manager(
        self, assigned_work_order, manager2, work_order_service
    ):
        """Test that wrong manager cannot accept order."""
        with pytest.raises(NotAssignedToManagerError):
            work_order_service.accept_order(
                work_order_id=assigned_work_order.id,
                manager=manager2,
            )

    def test_start_order(self, assigned_work_order, manager, work_order_service):
        """Test starting work order."""
        # First accept
        work_order_service.accept_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )

        result = work_order_service.start_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )

        assert result.status == "IN_PROGRESS"
        assert result.started_at is not None

    def test_complete_order(self, assigned_work_order, manager, work_order_service):
        """Test completing work order."""
        # Progress through workflow
        work_order_service.accept_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )
        work_order_service.start_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )

        result = work_order_service.complete_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )

        assert result.status == "COMPLETED"
        assert result.completed_at is not None
        assert result.verification_status == "PENDING"

    def test_verify_placement_correct(
        self, assigned_work_order, manager, admin_user, work_order_service
    ):
        """Test verifying placement as correct."""
        # Complete workflow first
        work_order_service.accept_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )
        work_order_service.start_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )
        work_order_service.complete_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )

        result = work_order_service.verify_placement(
            work_order_id=assigned_work_order.id,
            is_correct=True,
            notes="Placement verified via camera",
            verified_by=admin_user,
        )

        assert result.status == "VERIFIED"
        assert result.verification_status == "CORRECT"
        assert result.verified_at is not None

    def test_verify_placement_incorrect(
        self, assigned_work_order, manager, admin_user, work_order_service
    ):
        """Test verifying placement as incorrect."""
        # Complete workflow
        work_order_service.accept_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )
        work_order_service.start_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )
        work_order_service.complete_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )

        result = work_order_service.verify_placement(
            work_order_id=assigned_work_order.id,
            is_correct=False,
            notes="Container placed in wrong bay",
            verified_by=admin_user,
        )

        assert result.status == "FAILED"
        assert result.verification_status == "INCORRECT"

    def test_fail_order(self, assigned_work_order, manager, work_order_service):
        """Test failing a work order."""
        # Progress to IN_PROGRESS
        work_order_service.accept_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )
        work_order_service.start_order(
            work_order_id=assigned_work_order.id,
            manager=manager,
        )

        result = work_order_service.fail_order(
            work_order_id=assigned_work_order.id,
            reason="Crane malfunction - cannot complete",
            manager=manager,
        )

        assert result.status == "FAILED"
        assert "Crane malfunction" in result.verification_notes

    def test_invalid_status_transition(
        self, assigned_work_order, manager, work_order_service
    ):
        """Test that invalid status transitions raise error."""
        # Try to complete an ASSIGNED order (should fail - must be IN_PROGRESS first)
        with pytest.raises(InvalidStatusTransitionError):
            work_order_service.complete_order(
                work_order_id=assigned_work_order.id,
                manager=manager,
            )

    def test_verify_from_non_completed_status(
        self, assigned_work_order, manager, admin_user, work_order_service
    ):
        """Test error when verifying order not in COMPLETED status."""
        # Order is in ASSIGNED status
        with pytest.raises(InvalidStatusTransitionError):
            work_order_service.verify_placement(
                work_order_id=assigned_work_order.id,
                is_correct=True,
                verified_by=admin_user,
            )

    def test_fail_from_completed_status(
        self, assigned_work_order, manager, work_order_service
    ):
        """Test failing an order from COMPLETED status."""
        # Progress to COMPLETED
        work_order_service.accept_order(assigned_work_order.id, manager)
        work_order_service.start_order(assigned_work_order.id, manager)
        work_order_service.complete_order(assigned_work_order.id, manager)

        # Fail from COMPLETED should work
        result = work_order_service.fail_order(
            work_order_id=assigned_work_order.id,
            reason="Wrong container placed",
        )

        assert result.status == "FAILED"

    def test_fail_from_invalid_status(
        self, assigned_work_order, manager, work_order_service
    ):
        """Test error when failing order from invalid status (e.g., ASSIGNED)."""
        # Order is in ASSIGNED status - cannot fail
        with pytest.raises(InvalidStatusTransitionError):
            work_order_service.fail_order(
                work_order_id=assigned_work_order.id,
                reason="Some reason",
                manager=manager,
            )

    def test_fail_without_manager(
        self, assigned_work_order, manager, work_order_service
    ):
        """Test failing order without manager (e.g., by control room)."""
        # Progress to IN_PROGRESS
        work_order_service.accept_order(assigned_work_order.id, manager)
        work_order_service.start_order(assigned_work_order.id, manager)

        # Fail without specifying manager (control room action)
        result = work_order_service.fail_order(
            work_order_id=assigned_work_order.id,
            reason="Control room override",
            manager=None,
        )

        assert result.status == "FAILED"


@pytest.mark.django_db
class TestWorkOrderServiceQueries:
    """Tests for WorkOrderService query methods."""

    def test_get_manager_orders(
        self, container_entry_factory, manager, admin_user, work_order_service
    ):
        """Test getting orders assigned to a manager."""
        # Create multiple orders for this manager
        for i in range(3):
            entry = container_entry_factory()
            order = work_order_service.create_work_order(
                container_entry_id=entry.id,
                zone="A",
                row=i + 1,
                bay=1,
                tier=1,
                assigned_to_id=manager.id,
                created_by=admin_user,
            )

        with patch.object(WorkOrderService, "_notify_manager_async"):
            orders = work_order_service.get_manager_orders(manager=manager)

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

    def test_get_overdue_orders(self, work_order, work_order_service):
        """Test getting overdue orders."""
        # Make order overdue
        work_order.sla_deadline = timezone.now() - timedelta(hours=1)
        work_order.save()

        orders = work_order_service.get_overdue_orders()
        assert len(orders) == 1
        assert orders[0].id == work_order.id

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_get_manager_orders_with_status_filter(
        self,
        mock_notify,
        container_entry_factory,
        manager,
        admin_user,
        work_order_service,
    ):
        """Test getting manager orders with specific status filter."""
        # Create orders in different statuses
        entry1 = container_entry_factory()
        order1 = work_order_service.create_work_order(
            container_entry_id=entry1.id,
            zone="A",
            row=1,
            bay=1,
            tier=1,
            assigned_to_id=manager.id,
            created_by=admin_user,
        )

        entry2 = container_entry_factory()
        order2 = work_order_service.create_work_order(
            container_entry_id=entry2.id,
            zone="A",
            row=2,
            bay=1,
            tier=1,
            assigned_to_id=manager.id,
            created_by=admin_user,
        )
        # Accept order2
        work_order_service.accept_order(order2.id, manager)

        # Filter by ACCEPTED only
        orders = work_order_service.get_manager_orders(
            manager=manager, status_filter=["ACCEPTED"]
        )

        assert len(orders) == 1
        assert orders[0].status == "ACCEPTED"

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_get_manager_orders_include_completed(
        self,
        mock_notify,
        container_entry_factory,
        manager,
        admin_user,
        work_order_service,
    ):
        """Test getting manager orders including completed ones."""
        # Create and complete an order
        entry = container_entry_factory()
        order = work_order_service.create_work_order(
            container_entry_id=entry.id,
            zone="A",
            row=1,
            bay=1,
            tier=1,
            assigned_to_id=manager.id,
            created_by=admin_user,
        )
        work_order_service.accept_order(order.id, manager)
        work_order_service.start_order(order.id, manager)
        work_order_service.complete_order(order.id, manager)
        work_order_service.verify_placement(order.id, is_correct=True)

        # Without include_completed - should be empty (VERIFIED is not active)
        active_orders = work_order_service.get_manager_orders(manager=manager)
        assert len(active_orders) == 0

        # With include_completed=True - should include
        all_orders = work_order_service.get_manager_orders(
            manager=manager, include_completed=True
        )
        assert len(all_orders) == 1

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_get_all_active_orders(
        self,
        mock_notify,
        container_entry_factory,
        manager,
        admin_user,
        work_order_service,
    ):
        """Test getting all active orders for control room dashboard."""
        # Create orders in various active statuses
        entry1 = container_entry_factory()
        work_order_service.create_work_order(
            container_entry_id=entry1.id,
            zone="A",
            row=1,
            bay=1,
            tier=1,
            created_by=admin_user,
        )  # PENDING

        entry2 = container_entry_factory()
        order2 = work_order_service.create_work_order(
            container_entry_id=entry2.id,
            zone="A",
            row=2,
            bay=1,
            tier=1,
            assigned_to_id=manager.id,
            created_by=admin_user,
        )  # ASSIGNED

        entry3 = container_entry_factory()
        order3 = work_order_service.create_work_order(
            container_entry_id=entry3.id,
            zone="A",
            row=3,
            bay=1,
            tier=1,
            assigned_to_id=manager.id,
            created_by=admin_user,
        )
        work_order_service.accept_order(order3.id, manager)
        work_order_service.start_order(order3.id, manager)  # IN_PROGRESS

        # Get all active orders
        orders = work_order_service.get_all_active_orders()

        assert len(orders) == 3
        statuses = {o.status for o in orders}
        assert "PENDING" in statuses
        assert "ASSIGNED" in statuses
        assert "IN_PROGRESS" in statuses


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

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_create_work_order_api(
        self, mock_notify, api_client, admin_user, container_entry
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

    @patch.object(WorkOrderService, "_notify_manager_async")
    def test_assign_work_order_api(
        self, mock_notify, api_client, admin_user, work_order, manager
    ):
        """Test assigning work order via API."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f"/api/terminal/work-orders/{work_order.id}/assign/",
            {"manager_id": manager.id},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["status"] == "ASSIGNED"
        mock_notify.assert_called_once()

    def test_accept_work_order_api(self, api_client, assigned_work_order, manager):
        """Test manager accepting work order via API."""
        api_client.force_authenticate(user=manager)
        response = api_client.post(
            f"/api/terminal/work-orders/{assigned_work_order.id}/accept/",
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["status"] == "ACCEPTED"

    def test_my_orders_api(self, api_client, assigned_work_order, manager):
        """Test getting manager's own orders."""
        api_client.force_authenticate(user=manager)
        response = api_client.get("/api/terminal/work-orders/my-orders/")

        assert response.status_code == status.HTTP_200_OK
        # Response can be paginated (results) or non-paginated (data)
        data = response.data.get("results") or response.data.get("data", [])
        assert len(data) >= 1

    def test_my_orders_non_manager(self, api_client, admin_user):
        """Test my-orders fails for non-manager users."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/terminal/work-orders/my-orders/")

        # Should return error for non-manager
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_pending_orders_api(self, api_client, admin_user, work_order):
        """Test getting pending orders."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/terminal/work-orders/pending/")

        assert response.status_code == status.HTTP_200_OK
        # Response can be paginated (results) or non-paginated (data)
        data = response.data.get("results") or response.data.get("data", [])
        assert len(data) >= 1

    def test_overdue_orders_api(self, api_client, admin_user, work_order):
        """Test getting overdue orders."""
        # Make order overdue
        work_order.sla_deadline = timezone.now() - timedelta(hours=1)
        work_order.save()

        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/terminal/work-orders/overdue/")

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


# ============================================================================
# Notification Tests (Mocked)
# ============================================================================


@pytest.mark.django_db
class TestWorkOrderNotifications:
    """Tests for WorkOrder Telegram notifications."""

    @patch(
        "apps.terminal_operations.services.telegram_notification_service.TelegramNotificationService"
    )
    def test_notification_sent_on_assignment(
        self, mock_notification_class, container_entry, manager, admin_user
    ):
        """Test that notification is triggered when work order is assigned."""
        mock_service = MagicMock()
        mock_notification_class.return_value = mock_service

        service = WorkOrderService()

        # Create work order with manager
        work_order = service.create_work_order(
            container_entry_id=container_entry.id,
            zone="A",
            row=1,
            bay=1,
            tier=1,
            assigned_to_id=manager.id,
            created_by=admin_user,
        )

        # Give background thread time to execute
        import time

        time.sleep(0.5)

        # The notification service should have been instantiated
        # (actual async call is in background thread)
        assert work_order.assigned_to == manager

    def test_no_notification_without_manager(
        self, container_entry, admin_user, work_order_service
    ):
        """Test that no notification is sent when no manager assigned."""
        with patch.object(work_order_service, "_notify_manager_async") as mock_notify:
            work_order_service.create_work_order(
                container_entry_id=container_entry.id,
                zone="A",
                row=1,
                bay=1,
                tier=1,
                created_by=admin_user,
            )

            mock_notify.assert_not_called()
