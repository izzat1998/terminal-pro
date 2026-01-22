"""
API tests for container event endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.terminal_operations.models import ContainerEvent
from apps.terminal_operations.services import ContainerEventService


@pytest.mark.django_db
class TestContainerEventsAPI:
    """Tests for the container events API endpoint."""

    def test_get_events_for_container(self, authenticated_client, container_entry):
        """Test GET /api/terminal/entries/{id}/events/ returns events."""
        # Create some events
        event_service = ContainerEventService()
        event_service.create_entry_created_event(container_entry=container_entry)
        event_service.create_status_changed_event(
            container_entry=container_entry,
            old_status="EMPTY",
            new_status="LADEN",
        )

        url = f"/api/terminal/entries/{container_entry.id}/events/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["container_entry_id"] == container_entry.id
        assert len(response.data["data"]["events"]) == 2

    def test_events_endpoint_requires_auth(self, api_client, container_entry):
        """Test that events endpoint requires authentication."""
        url = f"/api/terminal/entries/{container_entry.id}/events/"
        response = api_client.get(url)

        # DRF returns 403 for unauthenticated requests with custom exception handler
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_events_include_display_labels(self, authenticated_client, container_entry):
        """Test that events include display labels for UI."""
        event_service = ContainerEventService()
        event_service.create_entry_created_event(container_entry=container_entry)

        url = f"/api/terminal/entries/{container_entry.id}/events/"
        response = authenticated_client.get(url)

        event = response.data["data"]["events"][0]
        assert "event_type_display" in event
        assert "source_display" in event
        assert event["event_type_display"] == "Контейнер принят"

    def test_events_ordered_chronologically(self, authenticated_client, container_entry):
        """Test that events are returned in chronological order (oldest first)."""
        from django.utils import timezone

        event_service = ContainerEventService()

        # Create events in reverse order
        event_service.create_event(
            container_entry=container_entry,
            event_type="EXIT_RECORDED",
            details={},
            event_time=timezone.now(),
        )
        event_service.create_event(
            container_entry=container_entry,
            event_type="ENTRY_CREATED",
            details={},
            event_time=timezone.now() - timezone.timedelta(hours=2),
        )

        url = f"/api/terminal/entries/{container_entry.id}/events/"
        response = authenticated_client.get(url)

        events = response.data["data"]["events"]
        assert events[0]["event_type"] == "ENTRY_CREATED"
        assert events[1]["event_type"] == "EXIT_RECORDED"

    def test_container_not_found_returns_404(self, authenticated_client):
        """Test that non-existent container returns 404."""
        url = "/api/terminal/entries/99999/events/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
