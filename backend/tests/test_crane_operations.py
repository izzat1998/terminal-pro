"""
Tests for CraneOperationService.

Tests cover:
- Creating crane operations
- Retrieving operations for entries
- Deleting operations
- Error handling (entry not found, operation not found)
- QuerySet filtering
"""

from datetime import datetime

import pytest
from django.utils import timezone

from apps.containers.models import Container
from apps.core.exceptions import BusinessLogicError
from apps.terminal_operations.models import ContainerEntry, CraneOperation
from apps.terminal_operations.services.crane_operation_service import (
    CraneOperationService,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crane_service():
    """Create CraneOperationService instance."""
    return CraneOperationService()


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


# ============================================================================
# Service Tests - Create Operation
# ============================================================================


@pytest.mark.django_db
class TestCraneOperationServiceCreate:
    """Tests for CraneOperationService.create_operation()."""

    def test_create_operation_success(self, container_entry, crane_service):
        """Test successfully creating a crane operation."""
        operation_date = timezone.now()

        operation = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=operation_date,
        )

        assert operation.container_entry == container_entry
        assert operation.operation_date == operation_date
        assert CraneOperation.objects.filter(container_entry=container_entry).exists()

    def test_create_operation_entry_not_found(self, crane_service):
        """Test error when container entry doesn't exist."""
        operation_date = timezone.now()

        with pytest.raises(BusinessLogicError) as exc_info:
            crane_service.create_operation(
                entry_id=99999,
                operation_date=operation_date,
            )

        assert "не найдена" in str(exc_info.value)
        assert exc_info.value.error_code == "CONTAINER_ENTRY_NOT_FOUND"

    def test_create_operation_missing_entry_id(self, crane_service):
        """Test error when entry_id is not provided."""
        operation_date = timezone.now()

        with pytest.raises(BusinessLogicError) as exc_info:
            crane_service.create_operation(
                entry_id=None,
                operation_date=operation_date,
            )

        assert "Необходимо указать ID" in str(exc_info.value)
        assert exc_info.value.error_code == "MISSING_PARAMETER"

    def test_create_operation_zero_entry_id(self, crane_service):
        """Test error when entry_id is 0 (falsy but not None)."""
        operation_date = timezone.now()

        with pytest.raises(BusinessLogicError) as exc_info:
            crane_service.create_operation(
                entry_id=0,
                operation_date=operation_date,
            )

        assert exc_info.value.error_code == "MISSING_PARAMETER"

    def test_create_multiple_operations_same_entry(
        self, container_entry, crane_service
    ):
        """Test creating multiple crane operations for same entry."""
        date1 = timezone.now()
        date2 = timezone.now()

        op1 = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=date1,
        )
        op2 = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=date2,
        )

        assert op1.id != op2.id
        assert CraneOperation.objects.filter(container_entry=container_entry).count() == 2


# ============================================================================
# Service Tests - Get Operations
# ============================================================================


@pytest.mark.django_db
class TestCraneOperationServiceGetOperations:
    """Tests for retrieving crane operations."""

    def test_get_operations_for_entry(self, container_entry, crane_service):
        """Test getting operations for a specific entry."""
        # Create multiple operations
        for i in range(3):
            crane_service.create_operation(
                entry_id=container_entry.id,
                operation_date=timezone.now(),
            )

        operations = crane_service.get_operations_for_entry(container_entry.id)

        assert operations.count() == 3
        # Should be ordered by -operation_date
        for op in operations:
            assert op.container_entry == container_entry

    def test_get_operations_for_entry_empty(self, container_entry, crane_service):
        """Test getting operations when none exist."""
        operations = crane_service.get_operations_for_entry(container_entry.id)

        assert operations.count() == 0

    def test_get_operations_queryset_all(
        self, container_entry_factory, crane_service
    ):
        """Test getting all crane operations."""
        # Create operations for multiple entries
        entry1 = container_entry_factory()
        entry2 = container_entry_factory()

        crane_service.create_operation(entry1.id, timezone.now())
        crane_service.create_operation(entry2.id, timezone.now())

        operations = crane_service.get_operations_queryset()

        assert operations.count() == 2

    def test_get_operations_queryset_filtered(
        self, container_entry_factory, crane_service
    ):
        """Test getting operations filtered by entry_id."""
        entry1 = container_entry_factory()
        entry2 = container_entry_factory()

        crane_service.create_operation(entry1.id, timezone.now())
        crane_service.create_operation(entry2.id, timezone.now())

        operations = crane_service.get_operations_queryset(entry_id=entry1.id)

        assert operations.count() == 1
        assert operations.first().container_entry == entry1

    def test_get_operations_includes_related_data(
        self, container_entry, crane_service
    ):
        """Test that operations include related container data."""
        crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=timezone.now(),
        )

        operations = crane_service.get_operations_for_entry(container_entry.id)
        operation = operations.first()

        # Should be able to access container without additional query (select_related)
        assert operation.container_entry.container.container_number == "MSKU1234567"


# ============================================================================
# Service Tests - Delete Operation
# ============================================================================


@pytest.mark.django_db
class TestCraneOperationServiceDelete:
    """Tests for CraneOperationService.delete_operation()."""

    def test_delete_operation_success(self, container_entry, crane_service):
        """Test successfully deleting a crane operation."""
        operation = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=timezone.now(),
        )

        result = crane_service.delete_operation(operation.id)

        assert result is True
        assert not CraneOperation.objects.filter(id=operation.id).exists()

    def test_delete_operation_not_found(self, crane_service):
        """Test error when operation doesn't exist."""
        with pytest.raises(BusinessLogicError) as exc_info:
            crane_service.delete_operation(99999)

        assert "не найдена" in str(exc_info.value)
        assert exc_info.value.error_code == "CRANE_OPERATION_NOT_FOUND"

    def test_delete_operation_does_not_affect_entry(
        self, container_entry, crane_service
    ):
        """Test that deleting operation doesn't delete the entry."""
        operation = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=timezone.now(),
        )

        crane_service.delete_operation(operation.id)

        # Entry should still exist
        assert ContainerEntry.objects.filter(id=container_entry.id).exists()

    def test_delete_multiple_operations(self, container_entry, crane_service):
        """Test deleting multiple operations independently."""
        op1 = crane_service.create_operation(container_entry.id, timezone.now())
        op2 = crane_service.create_operation(container_entry.id, timezone.now())

        crane_service.delete_operation(op1.id)

        # op1 deleted, op2 still exists
        assert not CraneOperation.objects.filter(id=op1.id).exists()
        assert CraneOperation.objects.filter(id=op2.id).exists()


# ============================================================================
# Service Tests - Private Helper Methods
# ============================================================================


@pytest.mark.django_db
class TestCraneOperationServiceHelpers:
    """Tests for private helper methods."""

    def test_get_container_entry_success(self, container_entry, crane_service):
        """Test _get_container_entry helper with valid ID."""
        entry = crane_service._get_container_entry(container_entry.id)

        assert entry == container_entry

    def test_get_container_entry_not_found(self, crane_service):
        """Test _get_container_entry helper with invalid ID."""
        with pytest.raises(BusinessLogicError) as exc_info:
            crane_service._get_container_entry(99999)

        assert exc_info.value.error_code == "CONTAINER_ENTRY_NOT_FOUND"


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestCraneOperationServiceIntegration:
    """Integration tests for full workflows."""

    def test_full_lifecycle(self, container_entry, crane_service):
        """Test complete lifecycle: create → retrieve → delete."""
        # Create
        operation = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=timezone.now(),
        )

        # Retrieve
        operations = crane_service.get_operations_for_entry(container_entry.id)
        assert operations.count() == 1

        # Delete
        crane_service.delete_operation(operation.id)
        operations = crane_service.get_operations_for_entry(container_entry.id)
        assert operations.count() == 0

    def test_multiple_entries_isolation(self, container_entry_factory, crane_service):
        """Test that operations for different entries are isolated."""
        entry1 = container_entry_factory()
        entry2 = container_entry_factory()

        # Create operations
        crane_service.create_operation(entry1.id, timezone.now())
        crane_service.create_operation(entry1.id, timezone.now())
        crane_service.create_operation(entry2.id, timezone.now())

        # Verify isolation
        ops_entry1 = crane_service.get_operations_for_entry(entry1.id)
        ops_entry2 = crane_service.get_operations_for_entry(entry2.id)

        assert ops_entry1.count() == 2
        assert ops_entry2.count() == 1

    def test_operation_ordering(self, container_entry, crane_service):
        """Test that operations are ordered by date descending."""
        from datetime import timedelta

        now = timezone.now()

        # Create operations with different dates
        op1 = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=now - timedelta(hours=2),
        )
        op2 = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=now,
        )
        op3 = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=now - timedelta(hours=1),
        )

        operations = crane_service.get_operations_for_entry(container_entry.id)
        operations_list = list(operations)

        # Should be ordered newest first
        assert operations_list[0].id == op2.id
        assert operations_list[1].id == op3.id
        assert operations_list[2].id == op1.id


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.django_db
class TestCraneOperationServiceEdgeCases:
    """Edge case tests."""

    def test_create_operation_with_past_date(self, container_entry, crane_service):
        """Test creating operation with past date."""
        from datetime import timedelta

        past_date = timezone.now() - timedelta(days=7)

        operation = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=past_date,
        )

        assert operation.operation_date == past_date

    def test_create_operation_with_future_date(self, container_entry, crane_service):
        """Test creating operation with future date."""
        from datetime import timedelta

        future_date = timezone.now() + timedelta(days=1)

        operation = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=future_date,
        )

        assert operation.operation_date == future_date

    def test_delete_already_deleted_operation(self, container_entry, crane_service):
        """Test deleting an already deleted operation raises error."""
        operation = crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=timezone.now(),
        )

        # First delete
        crane_service.delete_operation(operation.id)

        # Second delete should raise error
        with pytest.raises(BusinessLogicError):
            crane_service.delete_operation(operation.id)

    def test_queryset_does_not_execute_immediately(
        self, container_entry, crane_service
    ):
        """Test that get_operations_queryset returns lazy queryset."""
        crane_service.create_operation(
            entry_id=container_entry.id,
            operation_date=timezone.now(),
        )

        queryset = crane_service.get_operations_queryset()

        # Should be QuerySet, not list
        from django.db.models import QuerySet

        assert isinstance(queryset, QuerySet)

        # Can chain additional filters
        filtered = queryset.filter(container_entry_id=container_entry.id)
        assert filtered.count() == 1
