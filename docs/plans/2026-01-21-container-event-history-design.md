# Container Event History Design

**Date:** 2026-01-21
**Status:** Approved
**Author:** Claude + User

## Overview

Add comprehensive event tracking for container lifecycle to provide full operational visibility. This creates an audit trail of all significant container events from entry to exit.

## Goals

- Track all operationally meaningful container events
- Provide timeline view for any container ("what happened to MSKU1234567?")
- Know who performed each action and how (API, Telegram, Excel import)
- Generate baseline events for existing containers

## Non-Goals

- Track every field change (only significant operational events)
- Allow manual event creation via API (events are system-generated)
- Cross-container event queries (focus on per-container timeline)

---

## Data Model

### ContainerEvent

Single table design with event_type discriminator and JSON details.

```python
# apps/terminal_operations/models.py

class ContainerEvent(TimestampedModel):
    """
    Tracks all significant events in a container's lifecycle on the terminal.
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

    # Which container this event belongs to
    container_entry = models.ForeignKey(
        ContainerEntry,
        on_delete=models.CASCADE,
        related_name="events",
        help_text="Запись въезда контейнера",
    )

    # Event classification
    event_type = models.CharField(
        max_length=30,
        choices=EVENT_TYPE_CHOICES,
        db_index=True,
        help_text="Тип события",
    )

    # When the event occurred (may differ from created_at for imports)
    event_time = models.DateTimeField(
        db_index=True,
        help_text="Время события",
    )

    # Who triggered this event
    performed_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="container_events",
        help_text="Пользователь, выполнивший действие",
    )

    # How the event was triggered
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="API",
        help_text="Источник события",
    )

    # Type-specific data stored as JSON
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

---

## Event Details Structure

Each event type stores specific data in the `details` JSON field:

### ENTRY_CREATED
```json
{
    "status": "LADEN",
    "transport_type": "TRUCK",
    "transport_number": "01A123BC",
    "entry_train_number": ""
}
```

### STATUS_CHANGED
```json
{
    "old_status": "EMPTY",
    "new_status": "LADEN",
    "reason": "Loaded with cargo"
}
```

### POSITION_ASSIGNED
```json
{
    "zone": "A",
    "row": 3,
    "bay": 15,
    "tier": 2,
    "sub_slot": "A",
    "coordinate": "A-R03-B15-T2-A",
    "auto_assigned": true
}
```

### POSITION_REMOVED
```json
{
    "previous_zone": "A",
    "previous_row": 3,
    "previous_bay": 15,
    "previous_tier": 2,
    "previous_sub_slot": "A",
    "previous_coordinate": "A-R03-B15-T2-A"
}
```

### CRANE_OPERATION
```json
{
    "operation_date": "2026-01-21T10:30:00+05:00",
    "crane_operation_id": 123
}
```

### WORK_ORDER_CREATED
```json
{
    "order_number": "WO-20260121-0001",
    "target_coordinate": "A-R03-B15-T2-A",
    "priority": "HIGH",
    "work_order_id": 456
}
```

### WORK_ORDER_COMPLETED
```json
{
    "order_number": "WO-20260121-0001",
    "completed_at": "2026-01-21T11:45:00+05:00",
    "work_order_id": 456
}
```

### EXIT_RECORDED
```json
{
    "exit_transport_type": "WAGON",
    "exit_transport_number": "12345678",
    "exit_train_number": "T-2501",
    "destination_station": "Tashkent-Tovarniy",
    "dwell_time_days": 5
}
```

---

## Service Layer

### ContainerEventService

New service for event creation and queries:

```python
# apps/terminal_operations/services/container_event_service.py

class ContainerEventService(BaseService):
    """Creates and queries container lifecycle events."""

    def create_event(
        self,
        container_entry: ContainerEntry,
        event_type: str,
        details: dict,
        performed_by: CustomUser = None,
        source: str = "API",
        event_time: datetime = None,
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
        """

    def get_container_timeline(
        self,
        container_entry: ContainerEntry,
    ) -> QuerySet[ContainerEvent]:
        """
        Get all events for a container, ordered chronologically.

        Args:
            container_entry: The container to get events for

        Returns:
            QuerySet of ContainerEvent ordered by event_time
        """

    def generate_initial_events(self, dry_run: bool = False) -> dict:
        """
        One-time migration: create events for existing containers.

        Args:
            dry_run: If True, only report what would be created

        Returns:
            Dictionary with counts of events created by type
        """
```

### Integration Points

Existing services will be updated to emit events:

| Service | Method | Event Emitted |
|---------|--------|---------------|
| `ContainerEntryService` | `create_entry()` | `ENTRY_CREATED` |
| `ContainerEntryService` | `update_entry()` | `STATUS_CHANGED` (if status changed) |
| `ContainerEntryService` | `update_entry()` | `EXIT_RECORDED` (if exit_date set) |
| `PlacementService` | `assign_position()` | `POSITION_ASSIGNED` |
| `PlacementService` | `remove_position()` | `POSITION_REMOVED` |
| `ContainerEntryService` | `add_crane_operation()` | `CRANE_OPERATION` |
| `WorkOrderService` | `create_work_order()` | `WORK_ORDER_CREATED` |
| `WorkOrderService` | `complete_order()` | `WORK_ORDER_COMPLETED` |

### Source Determination

| Context | Source Value |
|---------|--------------|
| API views | `"API"` |
| Telegram bot handlers | `"TELEGRAM_BOT"` |
| Excel import service | `"EXCEL_IMPORT"` |
| Auto-assignment, migrations | `"SYSTEM"` |

---

## API Endpoint

### GET /api/terminal/entries/{id}/events/

Read-only endpoint to get container timeline.

**Response:**
```json
{
    "success": true,
    "data": {
        "container_number": "MSKU1234567",
        "container_entry_id": 123,
        "events": [
            {
                "id": 1,
                "event_type": "ENTRY_CREATED",
                "event_type_display": "Контейнер принят",
                "event_time": "2026-01-15T09:30:00+05:00",
                "performed_by": {
                    "id": 5,
                    "full_name": "Иванов Иван",
                    "user_type": "manager"
                },
                "source": "TELEGRAM_BOT",
                "source_display": "Telegram бот",
                "details": {
                    "status": "LADEN",
                    "transport_type": "TRUCK",
                    "transport_number": "01A123BC"
                },
                "created_at": "2026-01-15T09:30:15+05:00"
            }
        ]
    }
}
```

**Implementation:**
```python
# apps/terminal_operations/views.py

class ContainerEntryViewSet(viewsets.ModelViewSet):
    # ... existing code ...

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        """Get event timeline for a container."""
        entry = self.get_object()
        event_service = ContainerEventService()
        events = event_service.get_container_timeline(entry)
        serializer = ContainerEventSerializer(events, many=True)
        return Response({
            "success": True,
            "data": {
                "container_number": entry.container.container_number,
                "container_entry_id": entry.id,
                "events": serializer.data,
            }
        })
```

---

## Data Migration

### Management Command

```bash
python manage.py generate_initial_container_events [--dry-run]
```

**Behavior:**
1. Query all ContainerEntry records without events
2. For each container, create:
   - `ENTRY_CREATED` event from entry data
   - `POSITION_ASSIGNED` event if ContainerPosition exists
   - `EXIT_RECORDED` event if exit_date is set
   - `CRANE_OPERATION` events for each CraneOperation
3. Use `source="SYSTEM"` to indicate retroactive creation
4. Set `event_time` from original timestamps (entry_time, exit_date, etc.)

**Safety Features:**
- Idempotent: skips containers that already have events
- Batched: processes 100 containers at a time
- Transaction-wrapped per batch
- Dry-run mode available

**Expected Output:**
```
Created 1,247 ENTRY_CREATED events
Created 892 POSITION_ASSIGNED events
Created 156 EXIT_RECORDED events
Created 423 CRANE_OPERATION events
Total: 2,718 events generated for 1,247 containers
```

---

## Implementation Checklist

### Phase 1: Model & Service
- [ ] Add `ContainerEvent` model to `apps/terminal_operations/models.py`
- [ ] Create migration
- [ ] Create `ContainerEventService` in `apps/terminal_operations/services/`
- [ ] Add `ContainerEventSerializer` to serializers

### Phase 2: Integration
- [ ] Update `ContainerEntryService.create_entry()` to emit `ENTRY_CREATED`
- [ ] Update `ContainerEntryService.update_entry()` to emit `STATUS_CHANGED`, `EXIT_RECORDED`
- [ ] Update `PlacementService.assign_position()` to emit `POSITION_ASSIGNED`
- [ ] Update `PlacementService.remove_position()` to emit `POSITION_REMOVED`
- [ ] Update `ContainerEntryService.add_crane_operation()` to emit `CRANE_OPERATION`
- [ ] Update `WorkOrderService.create_work_order()` to emit `WORK_ORDER_CREATED`
- [ ] Update `WorkOrderService.complete_order()` to emit `WORK_ORDER_COMPLETED`

### Phase 3: API
- [ ] Add `events` action to `ContainerEntryViewSet`
- [ ] Register in URL patterns (automatic with viewset)

### Phase 4: Migration
- [ ] Create `generate_initial_container_events` management command
- [ ] Run migration on production data

### Phase 5: Testing
- [ ] Unit tests for `ContainerEventService`
- [ ] Integration tests for event emission from services
- [ ] API tests for events endpoint

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `apps/terminal_operations/models.py` | Modify | Add `ContainerEvent` model |
| `apps/terminal_operations/services/container_event_service.py` | Create | New service |
| `apps/terminal_operations/services/container_entry_service.py` | Modify | Emit events |
| `apps/terminal_operations/services/placement_service.py` | Modify | Emit events |
| `apps/terminal_operations/services/work_order_service.py` | Modify | Emit events |
| `apps/terminal_operations/serializers.py` | Modify | Add event serializer |
| `apps/terminal_operations/views.py` | Modify | Add events action |
| `apps/terminal_operations/management/commands/generate_initial_container_events.py` | Create | Migration command |
| `tests/terminal_operations/test_container_event_service.py` | Create | Tests |
