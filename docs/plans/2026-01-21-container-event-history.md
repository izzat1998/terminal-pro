# Container Event History Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive event tracking for container lifecycle to provide full operational visibility and audit trail.

**Architecture:** Single `ContainerEvent` model with event_type discriminator and JSON details. Services emit events at key lifecycle points. Read-only API endpoint for per-container timeline.

**Tech Stack:** Django 5.2, DRF, PostgreSQL/SQLite, pytest

---

## Task 1: Create ContainerEvent Model

**Files:**
- Modify: `backend/apps/terminal_operations/models.py` (append after WorkOrder class ~line 773)

**Step 1: Write the model code**

Add this to `backend/apps/terminal_operations/models.py` after the `WorkOrder` class:

```python
class ContainerEvent(TimestampedModel):
    """
    Tracks all significant events in a container's lifecycle on the terminal.
    Single table design with event_type discriminator and JSON details.
    """

    EVENT_TYPE_CHOICES = [
        ("ENTRY_CREATED", "Контейнер принят"),
        ("STATUS_CHANGED", "Статус изменён"),
        ("POSITION_ASSIGNED", "Позиция назначена"),
        ("POSITION_REMOVED", "Позиция освобождена"),
        ("CRANE_OPERATION", "Крановая операция"),
        ("WORK_ORDER_CREATED", "Наряд создан"),
        ("WORK_ORDER_COMPLETED", "Наряд завершён"),
        ("EXIT_RECORDED", "Выезд зарегистрирован"),
    ]

    SOURCE_CHOICES = [
        ("API", "API"),
        ("TELEGRAM_BOT", "Telegram бот"),
        ("EXCEL_IMPORT", "Импорт Excel"),
        ("SYSTEM", "Система"),
    ]

    container_entry = models.ForeignKey(
        ContainerEntry,
        on_delete=models.CASCADE,
        related_name="events",
        help_text="Запись въезда контейнера",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EVENT_TYPE_CHOICES,
        db_index=True,
        help_text="Тип события",
    )

    event_time = models.DateTimeField(
        db_index=True,
        help_text="Время события",
    )

    performed_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="container_events",
        help_text="Пользователь, выполнивший действие",
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="API",
        help_text="Источник события",
    )

    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Детали события в формате JSON",
    )

    class Meta:
        ordering = ["event_time", "created_at"]
        verbose_name = "Событие контейнера"
        verbose_name_plural = "События контейнеров"
        indexes = [
            models.Index(
                fields=["container_entry", "event_time"],
                name="event_entry_time_idx",
            ),
            models.Index(
                fields=["event_type", "-event_time"],
                name="event_type_time_idx",
            ),
            models.Index(
                fields=["-event_time"],
                name="event_time_desc_idx",
            ),
        ]

    def __str__(self):
        return f"{self.container_entry.container.container_number}: {self.get_event_type_display()} ({self.event_time})"
```

**Step 2: Create and apply migration**

Run:
```bash
cd backend && python manage.py makemigrations terminal_operations --name add_container_event_model
```
Expected: Migration file created

Run:
```bash
cd backend && python manage.py migrate
```
Expected: Migration applied successfully

**Step 3: Verify model works**

Run:
```bash
cd backend && python manage.py shell -c "from apps.terminal_operations.models import ContainerEvent; print(ContainerEvent._meta.get_fields())"
```
Expected: Lists all fields including container_entry, event_type, event_time, performed_by, source, details

**Step 4: Commit**

```bash
git add backend/apps/terminal_operations/models.py backend/apps/terminal_operations/migrations/
git commit -m "feat: add ContainerEvent model for lifecycle tracking"
```

---

## Task 2: Create ContainerEventService

**Files:**
- Create: `backend/apps/terminal_operations/services/container_event_service.py`
- Modify: `backend/apps/terminal_operations/services/__init__.py`

**Step 1: Create the service file**

Create `backend/apps/terminal_operations/services/container_event_service.py`:

```python
"""
Container Event Service - Business logic for container lifecycle event tracking.

Provides event creation, timeline queries, and initial event generation for existing data.
"""

from datetime import datetime
from typing import Optional

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.core.services.base_service import BaseService

from ..models import ContainerEntry, ContainerEvent


class ContainerEventService(BaseService):
    """
    Service for managing container lifecycle events.

    Handles:
    - Event creation with validation
    - Timeline queries for containers
    - Initial event generation for existing data
    """

    # Valid event types
    VALID_EVENT_TYPES = [
        "ENTRY_CREATED",
        "STATUS_CHANGED",
        "POSITION_ASSIGNED",
        "POSITION_REMOVED",
        "CRANE_OPERATION",
        "WORK_ORDER_CREATED",
        "WORK_ORDER_COMPLETED",
        "EXIT_RECORDED",
    ]

    # Valid sources
    VALID_SOURCES = ["API", "TELEGRAM_BOT", "EXCEL_IMPORT", "SYSTEM"]

    def create_event(
        self,
        container_entry: ContainerEntry,
        event_type: str,
        details: dict,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
        event_time: Optional[datetime] = None,
    ) -> ContainerEvent:
        """
        Create a new event for a container.

        Args:
            container_entry: The container this event belongs to
            event_type: One of EVENT_TYPE_CHOICES
            details: Event-specific data dictionary
            performed_by: User who triggered the event (optional)
            source: How the event was triggered (API, TELEGRAM_BOT, etc.)
            event_time: When the event occurred (defaults to now)

        Returns:
            Created ContainerEvent instance

        Raises:
            ValueError: If event_type or source is invalid
        """
        if event_type not in self.VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type: {event_type}")

        if source not in self.VALID_SOURCES:
            raise ValueError(f"Invalid source: {source}")

        if event_time is None:
            event_time = timezone.now()

        event = ContainerEvent.objects.create(
            container_entry=container_entry,
            event_type=event_type,
            event_time=event_time,
            performed_by=performed_by,
            source=source,
            details=details or {},
        )

        self.logger.info(
            f"Created {event_type} event for container "
            f"{container_entry.container.container_number} (entry_id={container_entry.id})"
        )

        return event

    def get_container_timeline(
        self,
        container_entry: ContainerEntry,
    ) -> QuerySet[ContainerEvent]:
        """
        Get all events for a container, ordered chronologically.

        Args:
            container_entry: The container to get events for

        Returns:
            QuerySet of ContainerEvent ordered by event_time (oldest first)
        """
        return (
            ContainerEvent.objects.filter(container_entry=container_entry)
            .select_related("performed_by")
            .order_by("event_time", "created_at")
        )

    def create_entry_created_event(
        self,
        container_entry: ContainerEntry,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create ENTRY_CREATED event with standard details."""
        details = {
            "status": container_entry.status,
            "transport_type": container_entry.transport_type,
            "transport_number": container_entry.transport_number or "",
            "entry_train_number": container_entry.entry_train_number or "",
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="ENTRY_CREATED",
            details=details,
            performed_by=performed_by,
            source=source,
            event_time=container_entry.entry_time,
        )

    def create_status_changed_event(
        self,
        container_entry: ContainerEntry,
        old_status: str,
        new_status: str,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
        reason: str = "",
    ) -> ContainerEvent:
        """Helper to create STATUS_CHANGED event."""
        details = {
            "old_status": old_status,
            "new_status": new_status,
        }
        if reason:
            details["reason"] = reason
        return self.create_event(
            container_entry=container_entry,
            event_type="STATUS_CHANGED",
            details=details,
            performed_by=performed_by,
            source=source,
        )

    def create_position_assigned_event(
        self,
        container_entry: ContainerEntry,
        zone: str,
        row: int,
        bay: int,
        tier: int,
        sub_slot: str,
        auto_assigned: bool = False,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create POSITION_ASSIGNED event."""
        coordinate = f"{zone}-R{row:02d}-B{bay:02d}-T{tier}-{sub_slot}"
        details = {
            "zone": zone,
            "row": row,
            "bay": bay,
            "tier": tier,
            "sub_slot": sub_slot,
            "coordinate": coordinate,
            "auto_assigned": auto_assigned,
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="POSITION_ASSIGNED",
            details=details,
            performed_by=performed_by,
            source=source,
        )

    def create_position_removed_event(
        self,
        container_entry: ContainerEntry,
        previous_zone: str,
        previous_row: int,
        previous_bay: int,
        previous_tier: int,
        previous_sub_slot: str,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create POSITION_REMOVED event."""
        coordinate = f"{previous_zone}-R{previous_row:02d}-B{previous_bay:02d}-T{previous_tier}-{previous_sub_slot}"
        details = {
            "previous_zone": previous_zone,
            "previous_row": previous_row,
            "previous_bay": previous_bay,
            "previous_tier": previous_tier,
            "previous_sub_slot": previous_sub_slot,
            "previous_coordinate": coordinate,
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="POSITION_REMOVED",
            details=details,
            performed_by=performed_by,
            source=source,
        )

    def create_crane_operation_event(
        self,
        container_entry: ContainerEntry,
        operation_date: datetime,
        crane_operation_id: int,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create CRANE_OPERATION event."""
        details = {
            "operation_date": operation_date.isoformat(),
            "crane_operation_id": crane_operation_id,
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="CRANE_OPERATION",
            details=details,
            performed_by=performed_by,
            source=source,
            event_time=operation_date,
        )

    def create_work_order_created_event(
        self,
        container_entry: ContainerEntry,
        order_number: str,
        target_coordinate: str,
        priority: str,
        work_order_id: int,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create WORK_ORDER_CREATED event."""
        details = {
            "order_number": order_number,
            "target_coordinate": target_coordinate,
            "priority": priority,
            "work_order_id": work_order_id,
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="WORK_ORDER_CREATED",
            details=details,
            performed_by=performed_by,
            source=source,
        )

    def create_work_order_completed_event(
        self,
        container_entry: ContainerEntry,
        order_number: str,
        work_order_id: int,
        completed_at: datetime,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create WORK_ORDER_COMPLETED event."""
        details = {
            "order_number": order_number,
            "work_order_id": work_order_id,
            "completed_at": completed_at.isoformat(),
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="WORK_ORDER_COMPLETED",
            details=details,
            performed_by=performed_by,
            source=source,
            event_time=completed_at,
        )

    def create_exit_recorded_event(
        self,
        container_entry: ContainerEntry,
        performed_by: Optional[CustomUser] = None,
        source: str = "API",
    ) -> ContainerEvent:
        """Helper to create EXIT_RECORDED event."""
        details = {
            "exit_transport_type": container_entry.exit_transport_type or "",
            "exit_transport_number": container_entry.exit_transport_number or "",
            "exit_train_number": container_entry.exit_train_number or "",
            "destination_station": container_entry.destination_station or "",
            "dwell_time_days": container_entry.dwell_time_days,
        }
        return self.create_event(
            container_entry=container_entry,
            event_type="EXIT_RECORDED",
            details=details,
            performed_by=performed_by,
            source=source,
            event_time=container_entry.exit_date,
        )
```

**Step 2: Update services __init__.py**

Add to `backend/apps/terminal_operations/services/__init__.py`:

```python
from .container_event_service import ContainerEventService
```

And add `"ContainerEventService"` to the `__all__` list.

**Step 3: Test in shell**

Run:
```bash
cd backend && python manage.py shell -c "
from apps.terminal_operations.services import ContainerEventService
service = ContainerEventService()
print('Service created:', service)
"
```
Expected: `Service created: <ContainerEventService object>`

**Step 4: Commit**

```bash
git add backend/apps/terminal_operations/services/
git commit -m "feat: add ContainerEventService for event creation and queries"
```

---

## Task 3: Create ContainerEventSerializer

**Files:**
- Create: `backend/apps/terminal_operations/serializers/events.py`
- Modify: `backend/apps/terminal_operations/serializers/__init__.py`

**Step 1: Create the serializer file**

Create `backend/apps/terminal_operations/serializers/events.py`:

```python
"""
Serializers for container event tracking.
"""

from rest_framework import serializers

from ..models import ContainerEvent


class EventPerformerSerializer(serializers.Serializer):
    """Nested serializer for the user who performed the action."""
    id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()
    user_type = serializers.CharField()

    def get_full_name(self, obj):
        return obj.full_name or obj.username


class ContainerEventSerializer(serializers.ModelSerializer):
    """
    Serializer for ContainerEvent model.
    Returns event data with display labels for UI rendering.
    """

    event_type_display = serializers.CharField(
        source="get_event_type_display",
        read_only=True,
    )
    source_display = serializers.CharField(
        source="get_source_display",
        read_only=True,
    )
    performed_by = EventPerformerSerializer(read_only=True)

    class Meta:
        model = ContainerEvent
        fields = [
            "id",
            "event_type",
            "event_type_display",
            "event_time",
            "performed_by",
            "source",
            "source_display",
            "details",
            "created_at",
        ]
        read_only_fields = fields


class ContainerTimelineSerializer(serializers.Serializer):
    """
    Serializer for container timeline response.
    Wraps events with container context.
    """

    container_number = serializers.CharField()
    container_entry_id = serializers.IntegerField()
    events = ContainerEventSerializer(many=True)
```

**Step 2: Update serializers __init__.py**

Add to `backend/apps/terminal_operations/serializers/__init__.py`:

After the existing imports, add:
```python
# Event serializers
from .events import (
    ContainerEventSerializer,
    ContainerTimelineSerializer,
    EventPerformerSerializer,
)
```

And add to `__all__`:
```python
    # Events
    "EventPerformerSerializer",
    "ContainerEventSerializer",
    "ContainerTimelineSerializer",
```

**Step 3: Commit**

```bash
git add backend/apps/terminal_operations/serializers/
git commit -m "feat: add ContainerEventSerializer for timeline API"
```

---

## Task 4: Add Events Endpoint to ContainerEntryViewSet

**Files:**
- Modify: `backend/apps/terminal_operations/views.py`

**Step 1: Add the events action**

In `backend/apps/terminal_operations/views.py`, find the `ContainerEntryViewSet` class and add this action after the existing actions (around line 425, after `check_container`):

```python
    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        """
        Get event timeline for a container.

        GET /api/terminal/entries/{id}/events/

        Returns chronological list of all events for this container entry.
        """
        from .serializers import ContainerEventSerializer, ContainerTimelineSerializer
        from .services import ContainerEventService

        entry = self.get_object()
        event_service = ContainerEventService()
        events = event_service.get_container_timeline(entry)

        return Response({
            "success": True,
            "data": {
                "container_number": entry.container.container_number,
                "container_entry_id": entry.id,
                "events": ContainerEventSerializer(events, many=True).data,
            }
        })
```

**Step 2: Test the endpoint**

Run:
```bash
cd backend && python manage.py runserver &
sleep 3
# Get a valid entry ID first, then test
curl -s http://localhost:8000/api/terminal/entries/ -H "Authorization: Bearer <token>" | head -100
```

**Step 3: Commit**

```bash
git add backend/apps/terminal_operations/views.py
git commit -m "feat: add events endpoint to ContainerEntryViewSet"
```

---

## Task 5: Write Unit Tests for ContainerEventService

**Files:**
- Create: `backend/tests/terminal_operations/__init__.py`
- Create: `backend/tests/terminal_operations/test_container_event_service.py`

**Step 1: Create test directory**

```bash
mkdir -p backend/tests/terminal_operations
touch backend/tests/terminal_operations/__init__.py
```

**Step 2: Write the tests**

Create `backend/tests/terminal_operations/test_container_event_service.py`:

```python
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
```

**Step 3: Run the tests**

Run:
```bash
cd backend && pytest tests/terminal_operations/test_container_event_service.py -v
```
Expected: All tests pass

**Step 4: Commit**

```bash
git add backend/tests/terminal_operations/
git commit -m "test: add unit tests for ContainerEventService"
```

---

## Task 6: Integrate Events into ContainerEntryService

**Files:**
- Modify: `backend/apps/terminal_operations/services/container_entry_service.py`

**Step 1: Add event service import and initialization**

At the top of `container_entry_service.py`, add the import:

```python
from .container_event_service import ContainerEventService
```

In the `ContainerEntryService` class, add initialization in `__init__` (or as property):

```python
    def __init__(self):
        super().__init__()
        self._event_service = None

    @property
    def event_service(self):
        if self._event_service is None:
            self._event_service = ContainerEventService()
        return self._event_service
```

**Step 2: Emit ENTRY_CREATED event in create_entry**

In the `create_entry` method, after `entry = ContainerEntry.objects.create(**create_kwargs)` and before the crane operations sync, add:

```python
        # Emit ENTRY_CREATED event
        self.event_service.create_entry_created_event(
            container_entry=entry,
            performed_by=final_recorded_by,
            source="API",  # Will be overridden by caller if needed
        )
```

**Step 3: Emit STATUS_CHANGED and EXIT_RECORDED events in update_entry**

In the `update_entry` method, track the old status at the beginning:

```python
        # Track old status for event emission
        old_status = entry.status
```

After saving the entry (after `entry.save()`), add event emission:

```python
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
```

**Step 4: Emit CRANE_OPERATION event in add_crane_operation**

In the `add_crane_operation` method, after creating the operation, add:

```python
        # Emit CRANE_OPERATION event
        self.event_service.create_crane_operation_event(
            container_entry=entry,
            operation_date=operation_date,
            crane_operation_id=operation.id,
        )
```

**Step 5: Run existing tests to ensure no regression**

Run:
```bash
cd backend && pytest tests/test_terminal_operations.py -v
```
Expected: All existing tests pass

**Step 6: Commit**

```bash
git add backend/apps/terminal_operations/services/container_entry_service.py
git commit -m "feat: emit events from ContainerEntryService"
```

---

## Task 7: Integrate Events into PlacementService

**Files:**
- Modify: `backend/apps/terminal_operations/services/placement_service.py`

**Step 1: Add event service import and property**

At the top, add import:

```python
from .container_event_service import ContainerEventService
```

In `PlacementService`, add property:

```python
    @property
    def event_service(self):
        if not hasattr(self, '_event_service'):
            self._event_service = ContainerEventService()
        return self._event_service
```

**Step 2: Emit POSITION_ASSIGNED event in assign_position**

In the `assign_position` method, after creating the `ContainerPosition` and before the return, add:

```python
        # Emit POSITION_ASSIGNED event
        self.event_service.create_position_assigned_event(
            container_entry=entry,
            zone=zone,
            row=row,
            bay=bay,
            tier=tier,
            sub_slot=sub_slot,
            auto_assigned=auto_assigned,
            source="SYSTEM" if auto_assigned else "API",
        )
```

**Step 3: Emit POSITION_REMOVED event in remove_position (if exists) or in move logic**

Find the position removal logic (might be in `move_container` or a separate method) and add:

```python
        # Emit POSITION_REMOVED event before removing
        self.event_service.create_position_removed_event(
            container_entry=position.container_entry,
            previous_zone=position.zone,
            previous_row=position.row,
            previous_bay=position.bay,
            previous_tier=position.tier,
            previous_sub_slot=position.sub_slot,
        )
```

**Step 4: Commit**

```bash
git add backend/apps/terminal_operations/services/placement_service.py
git commit -m "feat: emit events from PlacementService"
```

---

## Task 8: Integrate Events into WorkOrderService

**Files:**
- Modify: `backend/apps/terminal_operations/services/work_order_service.py`

**Step 1: Add event service import and property**

At the top, add import:

```python
from .container_event_service import ContainerEventService
```

In `WorkOrderService`, add property:

```python
    @property
    def event_service(self):
        if not hasattr(self, '_event_service'):
            self._event_service = ContainerEventService()
        return self._event_service
```

**Step 2: Emit WORK_ORDER_CREATED event in create_work_order**

After saving the work order, add:

```python
        # Emit WORK_ORDER_CREATED event
        self.event_service.create_work_order_created_event(
            container_entry=entry,
            order_number=work_order.order_number,
            target_coordinate=work_order.target_coordinate_string,
            priority=priority,
            work_order_id=work_order.id,
            performed_by=created_by,
        )
```

**Step 3: Emit WORK_ORDER_COMPLETED event in complete_order**

After completing the work order, add:

```python
        # Emit WORK_ORDER_COMPLETED event
        self.event_service.create_work_order_completed_event(
            container_entry=work_order.container_entry,
            order_number=work_order.order_number,
            work_order_id=work_order.id,
            completed_at=work_order.completed_at,
        )
```

**Step 4: Commit**

```bash
git add backend/apps/terminal_operations/services/work_order_service.py
git commit -m "feat: emit events from WorkOrderService"
```

---

## Task 9: Create Management Command for Initial Events

**Files:**
- Create: `backend/apps/terminal_operations/management/__init__.py`
- Create: `backend/apps/terminal_operations/management/commands/__init__.py`
- Create: `backend/apps/terminal_operations/management/commands/generate_initial_container_events.py`

**Step 1: Create directory structure**

```bash
mkdir -p backend/apps/terminal_operations/management/commands
touch backend/apps/terminal_operations/management/__init__.py
touch backend/apps/terminal_operations/management/commands/__init__.py
```

**Step 2: Create the management command**

Create `backend/apps/terminal_operations/management/commands/generate_initial_container_events.py`:

```python
"""
Management command to generate initial events for existing containers.

This is a one-time migration to backfill event history for containers
that existed before the event tracking system was implemented.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.terminal_operations.models import ContainerEntry, ContainerEvent, CraneOperation
from apps.terminal_operations.services import ContainerEventService


class Command(BaseCommand):
    help = "Generate initial events for existing container entries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be created, don't actually create events",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of containers to process per batch (default: 100)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No events will be created"))

        event_service = ContainerEventService()

        # Get entries without any events
        entries_without_events = ContainerEntry.objects.exclude(
            id__in=ContainerEvent.objects.values_list("container_entry_id", flat=True)
        ).select_related("container", "recorded_by").prefetch_related("crane_operations")

        total_entries = entries_without_events.count()
        self.stdout.write(f"Found {total_entries} container entries without events")

        if total_entries == 0:
            self.stdout.write(self.style.SUCCESS("No entries to process"))
            return

        # Counters
        entry_created_count = 0
        position_assigned_count = 0
        exit_recorded_count = 0
        crane_operation_count = 0

        # Process in batches
        processed = 0
        for entry in entries_without_events.iterator(chunk_size=batch_size):
            if not dry_run:
                with transaction.atomic():
                    # 1. Create ENTRY_CREATED event
                    event_service.create_entry_created_event(
                        container_entry=entry,
                        performed_by=entry.recorded_by,
                        source="SYSTEM",
                    )
                    entry_created_count += 1

                    # 2. Create POSITION_ASSIGNED event if has position
                    if hasattr(entry, "position") and entry.position:
                        pos = entry.position
                        event_service.create_position_assigned_event(
                            container_entry=entry,
                            zone=pos.zone,
                            row=pos.row,
                            bay=pos.bay,
                            tier=pos.tier,
                            sub_slot=pos.sub_slot,
                            auto_assigned=pos.auto_assigned,
                            source="SYSTEM",
                        )
                        position_assigned_count += 1

                    # 3. Create EXIT_RECORDED event if has exit_date
                    if entry.exit_date:
                        event_service.create_exit_recorded_event(
                            container_entry=entry,
                            source="SYSTEM",
                        )
                        exit_recorded_count += 1

                    # 4. Create CRANE_OPERATION events for each crane operation
                    for crane_op in entry.crane_operations.all():
                        event_service.create_crane_operation_event(
                            container_entry=entry,
                            operation_date=crane_op.operation_date,
                            crane_operation_id=crane_op.id,
                            source="SYSTEM",
                        )
                        crane_operation_count += 1
            else:
                # Dry run - just count
                entry_created_count += 1
                if hasattr(entry, "position") and entry.position:
                    position_assigned_count += 1
                if entry.exit_date:
                    exit_recorded_count += 1
                crane_operation_count += entry.crane_operations.count()

            processed += 1
            if processed % batch_size == 0:
                self.stdout.write(f"Processed {processed}/{total_entries} entries...")

        # Summary
        total_events = entry_created_count + position_assigned_count + exit_recorded_count + crane_operation_count

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"{'Would create' if dry_run else 'Created'} {entry_created_count} ENTRY_CREATED events")
        self.stdout.write(f"{'Would create' if dry_run else 'Created'} {position_assigned_count} POSITION_ASSIGNED events")
        self.stdout.write(f"{'Would create' if dry_run else 'Created'} {exit_recorded_count} EXIT_RECORDED events")
        self.stdout.write(f"{'Would create' if dry_run else 'Created'} {crane_operation_count} CRANE_OPERATION events")
        self.stdout.write(self.style.SUCCESS(f"Total: {total_events} events for {total_entries} containers"))
```

**Step 3: Test dry run**

Run:
```bash
cd backend && python manage.py generate_initial_container_events --dry-run
```
Expected: Shows counts of events that would be created

**Step 4: Commit**

```bash
git add backend/apps/terminal_operations/management/
git commit -m "feat: add management command for initial event generation"
```

---

## Task 10: Write API Integration Tests

**Files:**
- Create: `backend/tests/terminal_operations/test_container_events_api.py`

**Step 1: Write API tests**

Create `backend/tests/terminal_operations/test_container_events_api.py`:

```python
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

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

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
```

**Step 2: Run API tests**

Run:
```bash
cd backend && pytest tests/terminal_operations/test_container_events_api.py -v
```
Expected: All tests pass

**Step 3: Commit**

```bash
git add backend/tests/terminal_operations/test_container_events_api.py
git commit -m "test: add API tests for container events endpoint"
```

---

## Task 11: Run Full Test Suite and Generate Initial Events

**Step 1: Run full test suite**

Run:
```bash
cd backend && pytest -v
```
Expected: All tests pass

**Step 2: Generate initial events (production)**

Run:
```bash
cd backend && python manage.py generate_initial_container_events
```
Expected: Events created for all existing containers

**Step 3: Verify events created**

Run:
```bash
cd backend && python manage.py shell -c "
from apps.terminal_operations.models import ContainerEvent
print(f'Total events: {ContainerEvent.objects.count()}')
for event_type, label in ContainerEvent.EVENT_TYPE_CHOICES:
    count = ContainerEvent.objects.filter(event_type=event_type).count()
    print(f'  {label}: {count}')
"
```

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: container event history feature complete

- ContainerEvent model with 8 event types
- ContainerEventService for event creation and queries
- Events endpoint at /api/terminal/entries/{id}/events/
- Integration with ContainerEntryService, PlacementService, WorkOrderService
- Management command for initial event generation
- Comprehensive test coverage"
```

---

## Summary

| Task | Description | Estimated Steps |
|------|-------------|-----------------|
| 1 | Create ContainerEvent model | 4 |
| 2 | Create ContainerEventService | 4 |
| 3 | Create ContainerEventSerializer | 3 |
| 4 | Add events endpoint | 3 |
| 5 | Write unit tests for service | 4 |
| 6 | Integrate into ContainerEntryService | 6 |
| 7 | Integrate into PlacementService | 4 |
| 8 | Integrate into WorkOrderService | 4 |
| 9 | Create management command | 4 |
| 10 | Write API integration tests | 3 |
| 11 | Final verification | 4 |

**Total: 11 tasks, ~43 steps**
