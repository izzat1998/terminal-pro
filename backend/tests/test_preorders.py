"""
Tests for PreOrder model and workflow.
"""
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry, PreOrder
from apps.vehicles.models import Destination, VehicleEntry


User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def manager():
    """Create a manager user."""
    return CustomUser.objects.create(
        username="mgr_test",
        first_name="Test Manager",
        phone_number="+998901111111",
        user_type="manager",
        bot_access=True,
    )


@pytest.fixture
def customer():
    """Create a customer user."""
    return CustomUser.objects.create(
        username="customer_test",
        first_name="Test Customer",
        phone_number="+998902222222",
        user_type="customer",
        bot_access=True,
    )


@pytest.fixture
def destination():
    """Create a test destination."""
    return Destination.objects.create(
        name="Container Yard",
        zone="K1",
    )


@pytest.fixture
def preorder(customer):
    """Create a test pre-order."""
    return PreOrder.objects.create(
        customer=customer,
        plate_number="01A123BC",
        operation_type="LOAD",
        status="PENDING",
    )


@pytest.mark.django_db
class TestPreOrderModel:
    """Tests for PreOrder model."""

    def test_preorder_creation(self, customer):
        """Test creating a pre-order with valid data."""
        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number="01A456BC",
            operation_type="UNLOAD",
        )

        assert preorder.customer == customer
        assert preorder.plate_number == "01A456BC"
        assert preorder.operation_type == "UNLOAD"
        assert preorder.status == "PENDING"  # Default status
        assert preorder.created_at is not None

    def test_preorder_str_representation(self, preorder):
        """Test string representation."""
        expected = f"PreOrder {preorder.id}: {preorder.plate_number} (Погрузка) - Ожидает"
        assert str(preorder) == expected

    def test_preorder_status_choices(self, customer):
        """Test all valid status choices."""
        statuses = ["PENDING", "MATCHED", "COMPLETED", "CANCELLED"]

        for preorder_status in statuses:
            preorder = PreOrder.objects.create(
                customer=customer,
                plate_number=f"TEST{statuses.index(preorder_status)}",
                operation_type="LOAD",
                status=preorder_status,
            )
            assert preorder.status == preorder_status

    def test_preorder_operation_choices(self, customer):
        """Test operation type choices."""
        # LOAD (Погрузка)
        load_order = PreOrder.objects.create(
            customer=customer,
            plate_number="LOAD001",
            operation_type="LOAD",
        )
        assert load_order.get_operation_type_display() == "Погрузка"

        # UNLOAD (Разгрузка)
        unload_order = PreOrder.objects.create(
            customer=customer,
            plate_number="UNLOAD001",
            operation_type="UNLOAD",
        )
        assert unload_order.get_operation_type_display() == "Разгрузка"

    def test_preorder_batch_id(self, customer):
        """Test batch ID for grouped orders."""
        batch_id = uuid.uuid4()

        order1 = PreOrder.objects.create(
            customer=customer,
            plate_number="BATCH001",
            operation_type="LOAD",
            batch_id=batch_id,
        )
        order2 = PreOrder.objects.create(
            customer=customer,
            plate_number="BATCH002",
            operation_type="LOAD",
            batch_id=batch_id,
        )

        assert order1.batch_id == order2.batch_id
        assert PreOrder.objects.filter(batch_id=batch_id).count() == 2

    def test_preorder_ordering(self, customer):
        """Test pre-orders are ordered by created_at descending."""
        order1 = PreOrder.objects.create(
            customer=customer,
            plate_number="ORDER001",
            operation_type="LOAD",
        )
        order2 = PreOrder.objects.create(
            customer=customer,
            plate_number="ORDER002",
            operation_type="LOAD",
        )

        preorders = list(PreOrder.objects.all())
        assert preorders[0] == order2  # Most recent first
        assert preorders[1] == order1


@pytest.mark.django_db
class TestPreOrderWorkflow:
    """Tests for PreOrder workflow transitions."""

    def test_pending_to_matched_workflow(self, customer, manager, destination):
        """Test PENDING -> MATCHED transition when vehicle arrives."""
        # Step 1: Customer creates pre-order
        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number="MATCH001",
            operation_type="LOAD",
            status="PENDING",
        )

        # Step 2: Vehicle arrives, manager matches pre-order
        vehicle_entry = VehicleEntry.objects.create(
            license_plate="MATCH001",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="ON_TERMINAL",
            entry_time=timezone.now(),
            recorded_by=manager,
            destination=destination,
        )

        # Link and update status
        preorder.vehicle_entry = vehicle_entry
        preorder.status = "MATCHED"
        preorder.matched_at = timezone.now()
        preorder.save()

        assert preorder.status == "MATCHED"
        assert preorder.vehicle_entry == vehicle_entry
        assert preorder.matched_at is not None

    def test_matched_to_completed_workflow(self, customer, manager, destination):
        """Test MATCHED -> COMPLETED transition when operation finishes."""
        # Setup: Create matched pre-order
        vehicle_entry = VehicleEntry.objects.create(
            license_plate="COMP001",
            vehicle_type="CARGO",
            transport_type="TRUCK",
            status="ON_TERMINAL",
            entry_time=timezone.now(),
            recorded_by=manager,
            destination=destination,
        )

        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number="COMP001",
            operation_type="LOAD",
            status="MATCHED",
            vehicle_entry=vehicle_entry,
            matched_at=timezone.now(),
        )

        # Complete the operation
        vehicle_entry.status = "EXITED"
        vehicle_entry.exit_time = timezone.now()
        vehicle_entry.save()

        preorder.status = "COMPLETED"
        preorder.save()

        assert preorder.status == "COMPLETED"
        assert vehicle_entry.status == "EXITED"

    def test_pending_to_cancelled_workflow(self, customer):
        """Test PENDING -> CANCELLED transition when customer cancels."""
        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number="CANCEL001",
            operation_type="LOAD",
            status="PENDING",
        )

        # Customer cancels
        preorder.status = "CANCELLED"
        preorder.cancelled_at = timezone.now()
        preorder.save()

        assert preorder.status == "CANCELLED"
        assert preorder.cancelled_at is not None

    def test_preorder_with_container_entry(self, customer, manager):
        """Test linking pre-order to container entry."""
        # Create container
        container = Container.objects.create(
            container_number="MSKU1234567",
            iso_type="42G1",
        )

        # Create container entry
        container_entry = ContainerEntry.objects.create(
            container=container,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="PREORD001",
            recorded_by=manager,
        )

        # Create pre-order linked to container entry
        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number="PREORD001",
            operation_type="UNLOAD",
            status="MATCHED",
            matched_entry=container_entry,
            matched_at=timezone.now(),
        )

        assert preorder.matched_entry == container_entry
        assert container_entry.pre_orders.first() == preorder


@pytest.mark.django_db
class TestPreOrderGateMatching:
    """Tests for gate matching functionality."""

    def test_find_pending_preorder_by_plate(self, customer):
        """Test finding pending pre-order by plate number."""
        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number="FIND001",
            operation_type="LOAD",
            status="PENDING",
        )

        # Query as gate system would
        found = PreOrder.objects.filter(
            plate_number="FIND001",
            status="PENDING",
        ).first()

        assert found == preorder

    def test_no_match_for_completed_preorder(self, customer):
        """Test that completed pre-orders are not matched."""
        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number="NOMATCH001",
            operation_type="LOAD",
            status="COMPLETED",
        )

        # Query for pending only
        found = PreOrder.objects.filter(
            plate_number="NOMATCH001",
            status="PENDING",
        ).first()

        assert found is None

    def test_case_insensitive_plate_matching(self, customer):
        """Test plate matching is case-insensitive."""
        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number="CASE001",
            operation_type="LOAD",
            status="PENDING",
        )

        # Query with different case
        found = PreOrder.objects.filter(
            plate_number__iexact="case001",
            status="PENDING",
        ).first()

        assert found == preorder


@pytest.mark.django_db
class TestPreOrderNotes:
    """Tests for pre-order notes functionality."""

    def test_preorder_with_notes(self, customer):
        """Test pre-order with customer notes."""
        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number="NOTES001",
            operation_type="LOAD",
            notes="Please call driver on arrival: +998901234567",
        )

        assert preorder.notes == "Please call driver on arrival: +998901234567"

    def test_preorder_empty_notes(self, customer):
        """Test pre-order with empty notes."""
        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number="NONOTES001",
            operation_type="LOAD",
        )

        assert preorder.notes == ""
