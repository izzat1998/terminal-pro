# Simplify WorkOrder Status Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify WorkOrder status from 7 states to 2 states (PENDING → COMPLETED)

**Architecture:** Remove intermediate workflow states (ASSIGNED, ACCEPTED, IN_PROGRESS, VERIFIED, FAILED) and associated timestamp fields. Keep vehicle assignment as a field, not a status. Container is either waiting for placement (PENDING) or placed (COMPLETED).

**Tech Stack:** Django 5.2, Django REST Framework, Vue 3 + TypeScript, PostgreSQL

---

## Task 1: Update WorkOrder Model

**Files:**
- Modify: `backend/apps/terminal_operations/models.py:544-836`

**Step 1: Update STATUS_CHOICES and remove fields**

```python
# Replace lines 570-579 with:
    # Status workflow (simplified)
    STATUS_CHOICES = [
        ("PENDING", "Ожидает"),
        ("COMPLETED", "Завершён"),
    ]
```

**Step 2: Remove timestamp fields and verification fields**

Remove these fields from the WorkOrder model (lines 696-756):
- `sla_deadline` (line 697-699)
- `assigned_at` (line 702-706)
- `accepted_at` (line 708-712)
- `started_at` (line 714-718)
- `verified_at` (line 726-730)
- `placement_photo` (line 733-738)
- `verification_status` (line 740-750)
- `verification_notes` (line 752-756)

**Step 3: Update docstring**

```python
class WorkOrder(TimestampedModel):
    """
    Work order for container operations (placement or retrieval).

    Simplified workflow:
    PENDING → COMPLETED

    - PENDING: Created, container waiting for placement
    - COMPLETED: Container physically placed at target position
    """
```

**Step 4: Remove is_overdue and time_remaining_minutes properties**

Remove lines 793-803 (the `is_overdue` and `time_remaining_minutes` properties).

**Step 5: Run test to verify model compiles**

Run: `cd backend && python manage.py check`
Expected: System check identified no issues

**Step 6: Commit**

```bash
git add backend/apps/terminal_operations/models.py
git commit -m "refactor: simplify WorkOrder model to 2 statuses (PENDING/COMPLETED)"
```

---

## Task 2: Create Database Migration

**Files:**
- Create: `backend/apps/terminal_operations/migrations/XXXX_simplify_workorder_status.py`

**Step 1: Generate migration**

Run: `cd backend && python manage.py makemigrations terminal_operations --name simplify_workorder_status`

**Step 2: Review migration**

The migration should:
- Remove fields: `sla_deadline`, `assigned_at`, `accepted_at`, `started_at`, `verified_at`, `placement_photo`, `verification_status`, `verification_notes`
- Update `status` choices

**Step 3: Apply migration**

Run: `cd backend && python manage.py migrate`
Expected: Operations to perform: Apply all migrations: terminal_operations

**Step 4: Commit**

```bash
git add backend/apps/terminal_operations/migrations/
git commit -m "chore: add migration for simplified WorkOrder status"
```

---

## Task 3: Simplify WorkOrderService

**Files:**
- Modify: `backend/apps/terminal_operations/services/work_order_service.py`

**Step 1: Remove SLA and transition constants**

Remove lines 74-91:
```python
# Remove SLA_BY_PRIORITY dict
# Remove VALID_TRANSITIONS dict
```

**Step 2: Simplify create_work_order method**

Update `create_work_order` (lines 109-230) to:
- Remove `sla_deadline` calculation
- Always set `status = "PENDING"` regardless of vehicle assignment
- Remove `assigned_at` timestamp setting

```python
def create_work_order(
    self,
    container_entry_id: int,
    zone: Optional[str] = None,
    row: Optional[int] = None,
    bay: Optional[int] = None,
    tier: Optional[int] = None,
    sub_slot: str = "A",
    priority: str = "MEDIUM",
    assigned_to_vehicle_id: Optional[int] = None,
    created_by: Optional[CustomUser] = None,
    notes: str = "",
) -> WorkOrder:
    """Create a new work order for container placement."""
    # Get container entry
    try:
        entry = ContainerEntry.objects.select_related("container").get(
            id=container_entry_id
        )
    except ContainerEntry.DoesNotExist:
        raise BusinessLogicError(
            message=f"Запись контейнера #{container_entry_id} не найдена",
            error_code="CONTAINER_ENTRY_NOT_FOUND",
        )

    # Check for existing active work order
    existing_order = WorkOrder.objects.filter(
        container_entry=entry,
        status="PENDING",
    ).first()

    if existing_order:
        raise WorkOrderAlreadyExistsError(
            entry.container.container_number,
            existing_order.order_number,
        )

    # If position not specified, auto-suggest
    if zone is None:
        suggestion = self.placement_service.suggest_position(
            container_entry_id=container_entry_id,
            zone_preference=None,
        )
        pos = suggestion["suggested_position"]
        zone = pos["zone"]
        row = pos["row"]
        bay = pos["bay"]
        tier = pos["tier"]
        sub_slot = pos["sub_slot"]

    # Create work order
    work_order = WorkOrder(
        container_entry=entry,
        status="PENDING",
        priority=priority,
        target_zone=zone,
        target_row=row,
        target_bay=bay,
        target_tier=tier,
        target_sub_slot=sub_slot,
        created_by=created_by,
        notes=notes,
    )

    # Assign to vehicle if specified
    if assigned_to_vehicle_id:
        try:
            vehicle = TerminalVehicle.objects.get(
                id=assigned_to_vehicle_id,
                is_active=True,
            )
            work_order.assigned_to_vehicle = vehicle
        except TerminalVehicle.DoesNotExist:
            raise BusinessLogicError(
                message=f"Техника #{assigned_to_vehicle_id} не найдена",
                error_code="VEHICLE_NOT_FOUND",
            )

    work_order.save()

    self.logger.info(
        f"Created work order {work_order.order_number} for container "
        f"{entry.container.container_number} → {work_order.target_coordinate_string}"
    )

    return work_order
```

**Step 3: Simplify assign_to_vehicle method**

```python
def assign_to_vehicle(
    self,
    work_order_id: int,
    vehicle_id: int,
) -> WorkOrder:
    """Assign a work order to a terminal vehicle."""
    work_order = self._get_work_order(work_order_id)

    if work_order.status != "PENDING":
        raise BusinessLogicError(
            message="Только ожидающие наряды можно назначить",
            error_code="INVALID_STATUS",
        )

    try:
        vehicle = TerminalVehicle.objects.get(
            id=vehicle_id,
            is_active=True,
        )
    except TerminalVehicle.DoesNotExist:
        raise BusinessLogicError(
            message=f"Техника #{vehicle_id} не найдена или неактивна",
            error_code="VEHICLE_NOT_FOUND",
        )

    work_order.assigned_to_vehicle = vehicle
    work_order.save(update_fields=["assigned_to_vehicle", "updated_at"])

    self.logger.info(
        f"Assigned work order {work_order.order_number} to vehicle {vehicle.name}"
    )

    return work_order
```

**Step 4: Replace accept_order, start_order, verify_placement, fail_order with single complete_order**

Remove methods: `accept_order`, `start_order`, `verify_placement`, `fail_order`

Simplify `complete_order`:

```python
@transaction.atomic
def complete_order(
    self,
    work_order_id: int,
    vehicle_id: Optional[int] = None,
    operator: Optional[CustomUser] = None,
) -> WorkOrder:
    """
    Complete a work order - container is physically placed.

    Creates the actual ContainerPosition via PlacementService.
    """
    work_order = self._get_work_order(work_order_id)

    if work_order.status != "PENDING":
        raise BusinessLogicError(
            message="Только ожидающие наряды можно завершить",
            error_code="INVALID_STATUS",
        )

    # If vehicle_id provided, validate assignment
    if vehicle_id and work_order.assigned_to_vehicle_id != vehicle_id:
        raise BusinessLogicError(
            message="Наряд не назначен этой технике",
            error_code="NOT_ASSIGNED_TO_VEHICLE",
        )

    # Create actual container position via PlacementService
    self.placement_service.assign_position(
        container_entry_id=work_order.container_entry_id,
        zone=work_order.target_zone,
        row=work_order.target_row,
        bay=work_order.target_bay,
        tier=work_order.target_tier,
        sub_slot=work_order.target_sub_slot,
        auto_assigned=False,
    )

    # Update work order
    work_order.status = "COMPLETED"
    work_order.completed_at = timezone.now()
    work_order.save(update_fields=["status", "completed_at", "updated_at"])

    operator_name = operator.get_full_name() if operator else "Operator"
    self.logger.info(
        f"Work order {work_order.order_number} completed by {operator_name}"
    )

    return work_order
```

**Step 5: Update helper methods**

Update `get_vehicle_orders`:
```python
def get_vehicle_orders(
    self,
    vehicle_id: int,
    include_completed: bool = False,
) -> list:
    """Get work orders assigned to a specific vehicle."""
    queryset = (
        WorkOrder.objects.filter(assigned_to_vehicle_id=vehicle_id)
        .select_related(
            "container_entry__container",
            "container_entry__company",
            "assigned_to_vehicle",
        )
        .order_by("-priority", "-created_at")
    )

    if not include_completed:
        queryset = queryset.filter(status="PENDING")

    return queryset
```

Update `get_pending_orders`:
```python
def get_pending_orders(self) -> list:
    """Get unassigned work orders."""
    return (
        WorkOrder.objects.filter(status="PENDING", assigned_to_vehicle__isnull=True)
        .select_related(
            "container_entry__container",
            "container_entry__company",
        )
        .order_by("-priority", "-created_at")
    )
```

Update `get_all_active_orders`:
```python
def get_all_active_orders(self) -> list:
    """Get all pending work orders."""
    return (
        WorkOrder.objects.filter(status="PENDING")
        .select_related(
            "container_entry__container",
            "container_entry__company",
            "assigned_to_vehicle",
        )
        .order_by("-priority", "-created_at")
    )
```

**Step 6: Remove get_overdue_orders method and _validate_transition helper**

Remove `get_overdue_orders` method and `_validate_transition` helper.

**Step 7: Remove unused exception classes**

Keep only: `WorkOrderNotFoundError`, `WorkOrderAlreadyExistsError`
Remove: `InvalidStatusTransitionError`, `NotAssignedToVehicleError`

**Step 8: Run tests**

Run: `cd backend && pytest apps/terminal_operations/ -v -k work_order`
Expected: Tests may fail (will fix in later task)

**Step 9: Commit**

```bash
git add backend/apps/terminal_operations/services/work_order_service.py
git commit -m "refactor: simplify WorkOrderService for 2-status workflow"
```

---

## Task 4: Update WorkOrder Serializers

**Files:**
- Modify: `backend/apps/terminal_operations/serializers/work_orders.py`

**Step 1: Simplify WorkOrderSerializer**

Update fields list (remove timestamp and verification fields):

```python
class Meta:
    from ..models import WorkOrder

    model = WorkOrder
    fields = [
        "id",
        "order_number",
        "status",
        "status_display",
        "priority",
        "priority_display",
        "container",
        "target_location",
        "assigned_to_vehicle",
        "created_at",
        "completed_at",
        "notes",
    ]
    read_only_fields = [
        "id",
        "order_number",
        "created_at",
        "completed_at",
    ]
```

Remove methods: `get_placement_photo_url`
Remove fields: `is_overdue`, `time_remaining_minutes`, `placement_photo_url`, `verification_status`, `verification_notes`, `sla_deadline`, `assigned_at`, `accepted_at`, `started_at`, `verified_at`

**Step 2: Simplify WorkOrderListSerializer**

```python
class Meta:
    from ..models import WorkOrder

    model = WorkOrder
    fields = [
        "id",
        "order_number",
        "status",
        "status_display",
        "priority",
        "priority_display",
        "container_number",
        "container_size",
        "target_coordinate",
        "assigned_vehicle_name",
        "assigned_to_vehicle",
        "created_at",
    ]
```

Remove: `is_overdue`, `sla_deadline`

**Step 3: Remove unused serializers**

Remove these serializer classes:
- `WorkOrderCompleteSerializer` (no longer needs photo)
- `WorkOrderVerifySerializer` (no verification step)
- `WorkOrderFailSerializer` (no fail status)

**Step 4: Update TerminalVehicleStatusSerializer**

Update `get_status` method:
```python
@extend_schema_field(OpenApiTypes.STR)
def get_status(self, obj):
    """
    Compute vehicle status:
    - offline: not active or no operator
    - working: has pending work order assigned
    - available: active with operator but no assigned work
    """
    if not obj.is_active or not obj.operator:
        return "offline"

    # Check for assigned pending work orders
    has_active_work = obj.work_orders.filter(status="PENDING").exists()

    if has_active_work:
        return "working"

    return "available"
```

Update `get_current_task` method:
```python
@extend_schema_field({"type": "object", "nullable": True})
def get_current_task(self, obj):
    """Return current task info if vehicle has assigned work."""
    active_order = (
        obj.work_orders.filter(status="PENDING")
        .select_related("container_entry__container")
        .order_by("-priority", "-created_at")
        .first()
    )

    if active_order:
        return {
            "container_number": active_order.container_entry.container.container_number,
            "target_coordinate": active_order.target_coordinate_string,
        }

    return None
```

**Step 5: Commit**

```bash
git add backend/apps/terminal_operations/serializers/work_orders.py
git commit -m "refactor: simplify WorkOrder serializers for 2-status workflow"
```

---

## Task 5: Update WorkOrderViewSet

**Files:**
- Modify: `backend/apps/terminal_operations/views.py:1334-1600+`

**Step 1: Update list filter**

In the `list` method, update the status filter documentation:
```python
@extend_schema(
    summary="List work orders",
    description="List all work orders. Filter by status (PENDING or COMPLETED).",
    parameters=[
        OpenApiParameter(
            name="status",
            type=str,
            required=False,
            description="Filter by status (PENDING, COMPLETED)",
        ),
        # ... keep other params
    ],
)
```

**Step 2: Remove action methods**

Remove these action methods:
- `accept` action
- `start` action
- `verify` action
- `fail` action

**Step 3: Simplify complete action**

```python
@extend_schema(
    summary="Complete work order",
    description="Mark work order as completed. Creates the container position.",
    tags=["Work Orders"],
)
@action(detail=True, methods=["post"])
def complete(self, request, pk=None):
    """Complete a work order - container is physically placed."""
    work_order_service = self.get_work_order_service()

    work_order = work_order_service.complete_order(
        work_order_id=pk,
        operator=request.user,
    )

    return self._work_order_response(
        work_order, request, "Наряд завершён"
    )
```

**Step 4: Commit**

```bash
git add backend/apps/terminal_operations/views.py
git commit -m "refactor: simplify WorkOrderViewSet for 2-status workflow"
```

---

## Task 6: Update Frontend Types

**Files:**
- Modify: `frontend/src/types/placement.ts`

**Step 1: Update WorkOrderStatus type**

```typescript
export type WorkOrderStatus =
  | 'PENDING'      // Created, waiting for placement
  | 'COMPLETED';   // Container physically placed
```

**Step 2: Update PendingWorkOrderInfo interface**

```typescript
export interface PendingWorkOrderInfo {
  id: number;
  order_number: string;
  status: 'PENDING' | 'COMPLETED';
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  assigned_to: string | null;
}
```

**Step 3: Update WorkOrder interface**

Remove `sla_deadline` field:

```typescript
export interface WorkOrder {
  id: number;
  order_number: string;
  container_entry_id: number;
  container_number: string;
  iso_type: string;
  status: WorkOrderStatus;
  priority: WorkOrderPriority;
  target_zone: ZoneCode;
  target_row: number;
  target_bay: number;
  target_tier: number;
  target_sub_slot: SubSlot;
  target_coordinate: string;
  assigned_to_vehicle: WorkOrderVehicle | null;
  created_at: string;
  completed_at?: string;
  company_name: string;
}
```

**Step 4: Commit**

```bash
git add frontend/src/types/placement.ts
git commit -m "refactor: simplify WorkOrder types for 2-status workflow"
```

---

## Task 7: Update Frontend Services

**Files:**
- Modify: `frontend/src/services/workOrderService.ts`

**Step 1: Update getActiveWorkOrdersCount**

```typescript
export async function getActiveWorkOrdersCount(): Promise<number> {
  // Get pending work orders only (simplified: PENDING is the only active status)
  const response = await http.get<PaginatedResponse<WorkOrder>>(
    `${BASE_URL}/?status=PENDING&page_size=1`
  );
  return response.count;
}
```

**Step 2: Commit**

```bash
git add frontend/src/services/workOrderService.ts
git commit -m "refactor: simplify workOrderService for 2-status workflow"
```

---

## Task 8: Update Frontend Composables

**Files:**
- Modify: `frontend/src/composables/useWorkOrderTasks.ts`

**Step 1: Update fetchTasks to only fetch PENDING**

```typescript
async function fetchTasks(): Promise<void> {
  loading.value = true;
  error.value = null;

  try {
    // Fetch only PENDING work orders (simplified workflow)
    const orders = await workOrderService.getWorkOrders({
      status: 'PENDING',
    });
    pendingTasks.value = orders;
  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : 'Не удалось загрузить задания';
    error.value = errorMsg;
    message.error(errorMsg);
  } finally {
    loading.value = false;
  }
}
```

**Step 2: Commit**

```bash
git add frontend/src/composables/useWorkOrderTasks.ts
git commit -m "refactor: simplify useWorkOrderTasks for 2-status workflow"
```

---

## Task 9: Update Data Generation Script

**Files:**
- Modify: `backend/apps/core/management/commands/generate_realistic_data_v2.py`

**Step 1: Update _create_test_entry_with_position**

Update work order creation (around line 447):

```python
work_order = WorkOrder.objects.create(
    container_entry=entry,
    operation_type="PLACEMENT",
    status="COMPLETED",  # Simplified: only PENDING or COMPLETED
    assigned_to_vehicle=vehicle,
    created_by=recorded_by,
    target_zone="A",
    target_row=row,
    target_bay=bay,
    target_tier=tier,
    target_sub_slot=sub_slot,
    priority="MEDIUM",
)
```

**Step 2: Update _set_work_order_timestamps**

Simplify to only set `completed_at`:

```python
def _set_work_order_timestamps(self, work_order: WorkOrder, entry_time: datetime, status: str):
    """Set realistic workflow timestamps."""
    if status == "COMPLETED":
        completed_at = entry_time + timedelta(minutes=random.randint(15, 45))
        WorkOrder.objects.filter(id=work_order.id).update(
            created_at=entry_time,
            completed_at=completed_at,
        )
```

**Step 3: Update _create_placement_work_order**

Update status logic (around line 948-960):

```python
# For placed containers, mark as COMPLETED
# For waiting containers, mark as PENDING
status = "COMPLETED"  # Default for entries with positions

# Create work order
work_order = WorkOrder.objects.create(
    operation_type="PLACEMENT",
    container_entry=entry,
    status=status,
    priority="MEDIUM",
    assigned_to_vehicle=random.choice(foundation["vehicles"]),
    created_by=foundation["controlroom_admin"],
    target_zone="A",
    target_row=row,
    target_bay=bay,
    target_tier=tier,
    target_sub_slot=slot,
)
```

**Step 4: Update retrieval work order creation**

In `_process_exit_with_retrieval`, update status:

```python
work_order = WorkOrder.objects.create(
    operation_type="RETRIEVAL",
    container_entry=entry,
    status="COMPLETED",  # Retrieval is done when container exits
    priority="MEDIUM",
    # ... rest of fields
)
```

**Step 5: Commit**

```bash
git add backend/apps/core/management/commands/generate_realistic_data_v2.py
git commit -m "refactor: update data generation for 2-status workflow"
```

---

## Task 10: Update Existing Data

**Files:**
- Create: `backend/apps/terminal_operations/migrations/XXXX_convert_workorder_statuses.py`

**Step 1: Create data migration**

```python
from django.db import migrations


def convert_statuses_forward(apps, schema_editor):
    """Convert all non-PENDING statuses to COMPLETED."""
    WorkOrder = apps.get_model('terminal_operations', 'WorkOrder')

    # All completed-like statuses become COMPLETED
    WorkOrder.objects.filter(
        status__in=['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS', 'COMPLETED', 'VERIFIED']
    ).update(status='COMPLETED')

    # FAILED becomes PENDING (needs to be redone)
    WorkOrder.objects.filter(status='FAILED').update(status='PENDING')


def convert_statuses_backward(apps, schema_editor):
    """Reverse migration - just mark everything as PENDING."""
    # Note: This is a lossy reverse - we can't restore original statuses
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('terminal_operations', 'XXXX_simplify_workorder_status'),  # Update with actual migration name
    ]

    operations = [
        migrations.RunPython(convert_statuses_forward, convert_statuses_backward),
    ]
```

**Step 2: Apply migration**

Run: `cd backend && python manage.py migrate`

**Step 3: Verify data**

Run: `cd backend && python manage.py shell -c "from apps.terminal_operations.models import WorkOrder; print(WorkOrder.objects.values('status').annotate(count=Count('id')))"`

Expected: Only PENDING and COMPLETED statuses

**Step 4: Commit**

```bash
git add backend/apps/terminal_operations/migrations/
git commit -m "chore: add data migration to convert WorkOrder statuses"
```

---

## Task 11: Run Full Test Suite

**Step 1: Run backend tests**

Run: `cd backend && pytest -v`

Fix any failing tests related to WorkOrder status changes.

**Step 2: Run frontend type check**

Run: `cd frontend && npm run build`

Fix any TypeScript errors.

**Step 3: Manual testing**

1. Start backend: `make backend`
2. Start frontend: `make frontend`
3. Open browser to http://localhost:5174
4. Verify Tasks panel shows only PENDING work orders
5. Verify completing a task changes status to COMPLETED

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete WorkOrder status simplification (PENDING → COMPLETED)"
```

---

## Summary of Changes

| Component | Before | After |
|-----------|--------|-------|
| Statuses | 7 (PENDING→ASSIGNED→ACCEPTED→IN_PROGRESS→COMPLETED→VERIFIED/FAILED) | 2 (PENDING→COMPLETED) |
| Timestamp fields | 6 (assigned_at, accepted_at, started_at, completed_at, verified_at, sla_deadline) | 1 (completed_at) |
| Verification | placement_photo, verification_status, verification_notes | Removed |
| Service methods | 8 (create, assign, accept, start, complete, verify, fail, get_*) | 4 (create, assign, complete, get_*) |
| View actions | 6 (assign, accept, start, complete, verify, fail) | 2 (assign, complete) |
