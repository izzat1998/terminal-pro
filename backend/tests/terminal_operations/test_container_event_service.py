"""
Tests for ContainerEventService.
"""

import pytest
from django.utils import timezone

from apps.terminal_operations.models import ContainerEvent
from apps.terminal_operations.services import ContainerEventService


@pytest.mark.django_db
class TestContainerEventService:
    """Tests for ContainerEventService."""

    @pytest.fixture
    def event_service(self):
        return ContainerEventService()

    def test_create_event_basic(self, event_service, container_entry):
        """Test basic event creation."""
        event = event_service.create_event(
            container_entry=container_entry,
            event_type="ENTRY_CREATED",
            details={"status": "LADEN"},
        )

        assert event.id is not None
        assert event.container_entry == container_entry
        assert event.event_type == "ENTRY_CREATED"
        assert event.details == {"status": "LADEN"}
        assert event.source == "API"

    def test_create_event_with_user(self, event_service, container_entry, admin_user):
        """Test event creation with performed_by user."""
        event = event_service.create_event(
            container_entry=container_entry,
            event_type="STATUS_CHANGED",
            details={"old_status": "EMPTY", "new_status": "LADEN"},
            performed_by=admin_user,
            source="TELEGRAM_BOT",
        )

        assert event.performed_by == admin_user
        assert event.source == "TELEGRAM_BOT"

    def test_create_event_invalid_type(self, event_service, container_entry):
        """Test that invalid event type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid event_type"):
            event_service.create_event(
                container_entry=container_entry,
                event_type="INVALID_TYPE",
                details={},
            )

    def test_create_event_invalid_source(self, event_service, container_entry):
        """Test that invalid source raises ValueError."""
        with pytest.raises(ValueError, match="Invalid source"):
            event_service.create_event(
                container_entry=container_entry,
                event_type="ENTRY_CREATED",
                details={},
                source="INVALID_SOURCE",
            )

    def test_get_container_timeline(self, event_service, container_entry):
        """Test timeline query returns events in chronological order."""
        # Create events with different times
        event1 = event_service.create_event(
            container_entry=container_entry,
            event_type="ENTRY_CREATED",
            details={},
            event_time=timezone.now() - timezone.timedelta(hours=2),
        )
        event2 = event_service.create_event(
            container_entry=container_entry,
            event_type="POSITION_ASSIGNED",
            details={},
            event_time=timezone.now() - timezone.timedelta(hours=1),
        )
        event3 = event_service.create_event(
            container_entry=container_entry,
            event_type="EXIT_RECORDED",
            details={},
            event_time=timezone.now(),
        )

        timeline = event_service.get_container_timeline(container_entry)
        timeline_list = list(timeline)

        assert len(timeline_list) == 3
        assert timeline_list[0].id == event1.id
        assert timeline_list[1].id == event2.id
        assert timeline_list[2].id == event3.id

    def test_create_entry_created_event_helper(self, event_service, container_entry):
        """Test ENTRY_CREATED helper creates correct details."""
        event = event_service.create_entry_created_event(
            container_entry=container_entry,
            source="API",
        )

        assert event.event_type == "ENTRY_CREATED"
        assert event.details["status"] == container_entry.status
        assert event.details["transport_type"] == container_entry.transport_type
        assert event.event_time == container_entry.entry_time

    def test_create_status_changed_event_helper(self, event_service, container_entry):
        """Test STATUS_CHANGED helper creates correct details."""
        event = event_service.create_status_changed_event(
            container_entry=container_entry,
            old_status="EMPTY",
            new_status="LADEN",
            reason="Loaded with cargo",
        )

        assert event.event_type == "STATUS_CHANGED"
        assert event.details["old_status"] == "EMPTY"
        assert event.details["new_status"] == "LADEN"
        assert event.details["reason"] == "Loaded with cargo"

    def test_create_position_assigned_event_helper(self, event_service, container_entry):
        """Test POSITION_ASSIGNED helper creates correct details."""
        event = event_service.create_position_assigned_event(
            container_entry=container_entry,
            zone="A",
            row=3,
            bay=15,
            tier=2,
            sub_slot="A",
            auto_assigned=True,
        )

        assert event.event_type == "POSITION_ASSIGNED"
        assert event.details["zone"] == "A"
        assert event.details["row"] == 3
        assert event.details["coordinate"] == "A-R03-B15-T2-A"
        assert event.details["auto_assigned"] is True

    def test_create_exit_recorded_event_helper(self, event_service, container_entry):
        """Test EXIT_RECORDED helper creates correct details."""
        # Set exit data
        container_entry.exit_date = timezone.now()
        container_entry.exit_transport_type = "WAGON"
        container_entry.destination_station = "Tashkent"
        container_entry.save()

        event = event_service.create_exit_recorded_event(
            container_entry=container_entry,
        )

        assert event.event_type == "EXIT_RECORDED"
        assert event.details["exit_transport_type"] == "WAGON"
        assert event.details["destination_station"] == "Tashkent"
        assert "dwell_time_days" in event.details
