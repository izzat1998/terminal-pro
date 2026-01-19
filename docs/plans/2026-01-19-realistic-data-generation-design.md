# Realistic Data Generation System - Design Document

**Date:** 2026-01-19
**Status:** Design Complete - Ready for Implementation
**Goal:** Generate 90 days of bulletproof realistic container terminal data with tight company clustering and 100% placement success

---

## Problem Statement

The existing `generate_realistic_data.py` script has two key issues:

1. **❌ Poor 3D Placement**: Containers scattered randomly across bays, breaking visual company clustering
2. **❌ Too Many Waiting Containers**: Excessive containers in PENDING/IN_PROGRESS state without positions

**Root Cause:** Random position selection within company rows causes scattering instead of tight clusters.

---

## Solution Overview

**Improved Placement System:**
- Sequential position allocation (fill like a bookshelf: bay-by-bay, tier-by-tier)
- Tight company clustering: Large companies get 4 rows, Medium 2 rows, Small 1 row
- 80% density target (operational gaps for realism)
- 100% placement success (no failed work orders)
- Complete lifecycle: Entry → PLACEMENT work order → RETRIEVAL work order → Exit

**Expected Results:**
- 98% containers with positions (2% recent entries still in-progress)
- Tight visual clusters per company in 3D yard
- Realistic work order distribution: 70% VERIFIED, 20% IN_PROGRESS, 10% ACCEPTED
- Both PLACEMENT and RETRIEVAL work orders for complete workflow

---

## Data Generation Layers

### Layer 1: Foundation (Independent Entities)

**Purpose:** Create all prerequisite data with no dependencies

```python
# 1.1 Users (4 types)
- system_admin (username: "system")
- controlroom_admin (username: "controlroom")
- managers × 4 (Aziz, Bobur, Sardor, Dilshod) with ManagerProfile
- customers × 3 (Jamshid, Kamol, Laziz) with CustomerProfile

# 1.2 Companies (7 with size classification)
- Large × 2: "O'zbekiston Temir Yo'llari", "Toshkent Logistika"
- Medium × 2: "Ipak Yo'li Transport", "Navoiy Yuk Tashish"
- Small × 3: "Buxoro Trans", "Samarqand Cargo", "Farg'ona Logistics"

# 1.3 Container Owners (5 shipping lines)
- Maersk Line (MSKU)
- MSC (MSCU)
- CMA CGM (CMAU)
- Hapag-Lloyd (HLCU)
- COSCO (COSU)

# 1.4 Container Pool (100 containers)
- 70% 40ft containers (ISO types: 42G1, 45G1, L5G1, etc.)
- 30% 20ft containers (ISO types: 22G1, 25G1, etc.)
- Realistic container numbers: PREFIX + 7 digits

# 1.5 Terminal Vehicles (3 reach stackers)
- RS-01 (operator: Aziz)
- RS-02 (operator: Bobur)
- RS-03 (operator: Sardor)

# 1.6 Tariffs (covering 90+ days)
- General tariff (applies to all companies)
- Special tariffs for 2 large companies (better rates)
```

---

### Layer 2: Space Allocation (Pre-Generation Setup)

**Purpose:** Assign 3D yard space to companies BEFORE generating entries

**Row Assignment Strategy:**
```
Rows 1-4:   Large Company #1 (O'zbekiston Temir Yo'llari)
Rows 5-8:   Large Company #2 (Toshkent Logistika)
Rows 9-10:  Medium Company #1 (Ipak Yo'li Transport)
Rows 11-12: Medium Company #2 (Navoiy Yuk Tashish)
Row 13:     Small Company #1 (Buxoro Trans)
Row 14:     Small Company #2 (Samarqand Cargo)
Row 15:     Small Company #3 (Farg'ona Logistics)
Rows 16-20: Overflow pool (for capacity spillover)
```

**State Management Structure:**
```python
state = {
    "company_cursors": {
        company_id: {
            "rows": [1, 2, 3, 4],         # Assigned rows
            "current_row_idx": 0,          # Current row being filled
            "current_bay": 1,              # Current bay (1-10)
            "current_tier": 1,             # Current tier (1-2)
            "bay_occupancy": {},           # {bay_num: "FULL" | "SLOT_A_USED" | "EMPTY"}
            "positions_filled": 0,         # Stats
            "positions_skipped": 0         # For 80% density
        }
    },
    "active_entries": {},                  # {container_id: entry_id} - prevents double-placement
    "exited_container_ids": set(),         # Containers available for reuse
    "occupancy_grid": {},                  # {(zone, row, bay, tier, slot): entry_id}
    "overflow_cursor": {                   # Same structure as company cursor
        "rows": [16, 17, 18, 19, 20],
        ...
    }
}
```

**Sequential Position Algorithm:**
```
Fill Order: Bay-major, tier-minor (tier 1 first for stability)

Example for Row 1:
  Bay 1, Tier 1 → Bay 2, Tier 1 → ... → Bay 10, Tier 1
  Bay 1, Tier 2 → Bay 2, Tier 2 → ... → Bay 10, Tier 2
  Then move to Row 2...

80% Density Implementation:
  - For every position attempt, 20% chance to skip
  - Creates operational gaps (containers recently moved, reserved spots)
```

**20ft/40ft Slot Logic:**
```
Each bay can hold:
  - One 40ft container (occupies slot A only, bay marked FULL)
  - Two 20ft containers (slot A + slot B, bay marked FULL after both)

Bay Occupancy States:
  EMPTY         → can place 40ft (slot A) OR 20ft (slot A)
  SLOT_A_USED   → can only place 20ft (slot B)
  FULL          → no space, advance to next bay
```

---

### Layer 3: Entry Generation (Chronological, Day-by-Day)

**Purpose:** Generate container entries with realistic patterns over 90 days

**Volume Distribution:**
```python
Daily volume: 10-30 containers per day
Transport mix: 70% truck, 30% train
Status mix: 70% empty, 30% laden
PreOrder rate: 70% of truck entries

Train batches: 5-15 containers arrive together (same train_number)
```

**Entry Creation Process:**
```python
for day in range(90):
    current_date = start_date + timedelta(days=day)

    # 1. Generate train batches (30% of volume)
    train_volume = random.randint(3, 9)  # 30% of 10-30
    for batch in create_train_batches(train_volume):
        for container in batch:
            create_entry(container, transport_type="TRAIN")

    # 2. Generate truck entries (70% of volume)
    truck_volume = random.randint(7, 21)  # 70% of 10-30
    for _ in range(truck_volume):
        create_entry(random_container(), transport_type="TRUCK")

    # 3. Process exits for this day (see Layer 5)
    process_exits_for_day(current_date)
```

**Container Selection Logic:**
```python
def select_container(container_pool, state):
    # 25% chance to reuse exited container (realistic return pattern)
    if state["exited_container_ids"] and random.random() < 0.25:
        container_id = random.choice(list(state["exited_container_ids"]))
        container = Container.objects.get(id=container_id)

        # Prevent double-placement (container already active on terminal)
        if container.id not in state["active_entries"]:
            return container

    # Otherwise pick from pool (ensure not active)
    for _ in range(100):  # Try 100 times
        container = random.choice(container_pool)
        if container.id not in state["active_entries"]:
            return container

    return None  # All containers busy (shouldn't happen with 100-container pool)
```

---

### Layer 4: Work Order & Placement (100% Success)

**Purpose:** Create PLACEMENT work orders and 3D positions with guaranteed success

**Work Order Status Distribution:**
```python
# Based on entry age:
if days_since_entry <= 2:
    # Recent entries: show active workflow
    status = random.choices(
        ["VERIFIED", "IN_PROGRESS", "ACCEPTED"],
        weights=[70, 20, 10]
    )[0]
else:
    # Historical: all completed
    status = "VERIFIED"
```

**Position Allocation (Guaranteed Success):**
```python
def get_next_position_guaranteed(company_id, container_size, state):
    """
    Returns position coordinates - ALWAYS succeeds via fallback chain:
    1. Try company's assigned rows
    2. Try overflow rows (16-20)
    3. Dynamically add more overflow rows if needed
    """

    # Determine 40ft or 20ft
    is_40ft = (container_size == "40")

    # Get company cursor
    cursor = state["company_cursors"][company_id]

    # Try to find position in company rows
    while cursor["current_row_idx"] < len(cursor["rows"]):
        row = cursor["rows"][cursor["current_row_idx"]]
        bay = cursor["current_bay"]
        tier = cursor["current_tier"]

        # 80% density: 20% chance to skip this position
        if random.random() < 0.2:
            cursor["positions_skipped"] += 1
            advance_cursor(cursor)
            continue

        # Check bay occupancy
        bay_status = cursor["bay_occupancy"].get(bay, "EMPTY")

        # Try to place 40ft container
        if is_40ft and bay_status == "EMPTY":
            cursor["bay_occupancy"][bay] = "FULL"
            cursor["positions_filled"] += 1
            advance_cursor(cursor)
            return (row, bay, tier, "A")

        # Try to place 20ft container
        if not is_40ft:
            if bay_status == "EMPTY":
                # Use slot A
                cursor["bay_occupancy"][bay] = "SLOT_A_USED"
                cursor["positions_filled"] += 1
                advance_cursor(cursor)
                return (row, bay, tier, "A")
            elif bay_status == "SLOT_A_USED":
                # Use slot B
                cursor["bay_occupancy"][bay] = "FULL"
                cursor["positions_filled"] += 1
                advance_cursor(cursor)
                return (row, bay, tier, "B")

        # Position not suitable, try next
        advance_cursor(cursor)

    # Company zone full → use overflow
    overflow_position = get_overflow_position(container_size, state)
    if overflow_position:
        return overflow_position

    # Overflow full → dynamically expand overflow rows
    new_row = max(state["overflow_cursor"]["rows"]) + 1
    state["overflow_cursor"]["rows"].append(new_row)
    return get_overflow_position(container_size, state)

def advance_cursor(cursor):
    """
    Move cursor to next position in sequential order.
    Fill order: Bay 1-10 (tier 1), then Bay 1-10 (tier 2), then next row.
    """
    cursor["current_bay"] += 1

    if cursor["current_bay"] > 10:
        if cursor["current_tier"] == 1:
            # Tier 1 done, move to tier 2
            cursor["current_tier"] = 2
            cursor["current_bay"] = 1
            cursor["bay_occupancy"] = {}  # Reset for tier 2
        else:
            # Tier 2 done, move to next row
            cursor["current_row_idx"] += 1
            cursor["current_tier"] = 1
            cursor["current_bay"] = 1
            cursor["bay_occupancy"] = {}
```

**Work Order Creation:**
```python
def create_placement_work_order(entry, entry_time, foundation, state):
    # Get position (guaranteed)
    iso_type = entry.container.iso_type
    size = "40" if iso_type[0] in ["4", "L"] else "20"
    row, bay, tier, slot = get_next_position_guaranteed(entry.company.id, size, state)

    # Determine status based on age
    status = determine_work_order_status(entry_time, "PLACEMENT")

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
        sla_deadline=entry_time + timedelta(hours=1),
    )

    # Set realistic workflow timestamps
    if status == "VERIFIED":
        # Complete workflow: entry → +5min created → +2min assigned → +1min accepted → +5min started → +10min completed → +2min verified
        WorkOrder.objects.filter(id=work_order.id).update(
            created_at=entry_time + timedelta(minutes=5),
            assigned_at=entry_time + timedelta(minutes=7),
            accepted_at=entry_time + timedelta(minutes=8),
            started_at=entry_time + timedelta(minutes=13),
            completed_at=entry_time + timedelta(minutes=23),
            verified_at=entry_time + timedelta(minutes=25),
        )
    elif status == "IN_PROGRESS":
        # Partial workflow (no completion yet)
        WorkOrder.objects.filter(id=work_order.id).update(
            created_at=entry_time + timedelta(minutes=5),
            assigned_at=entry_time + timedelta(minutes=7),
            accepted_at=entry_time + timedelta(minutes=8),
            started_at=entry_time + timedelta(minutes=13),
        )
    elif status == "ACCEPTED":
        # Early workflow (just accepted)
        WorkOrder.objects.filter(id=work_order.id).update(
            created_at=entry_time + timedelta(minutes=5),
            assigned_at=entry_time + timedelta(minutes=7),
            accepted_at=entry_time + timedelta(minutes=8),
        )

    # Create position (always, since 100% success)
    ContainerPosition.objects.create(
        container_entry=entry,
        zone="A",
        row=row,
        bay=bay,
        tier=tier,
        sub_slot=slot,
        auto_assigned=True
    )

    # Update entry location
    entry.location = f"A-R{row:02d}-B{bay:02d}-T{tier}-{slot}"
    entry.save(update_fields=["location"])

    # Mark in state
    state["occupancy_grid"][("A", row, bay, tier, slot)] = entry.id
    state["active_entries"][entry.container.id] = entry.id
```

---

### Layer 5: Exit Processing (With RETRIEVAL Work Orders)

**Purpose:** Process container exits with retrieval work orders for complete workflow

**Exit Strategy:**
```python
# Exit rate: 40-50% of containers exit during 90 days
# Dwell time distribution:
#   - 20% quick exit (1-3 days)
#   - 50% medium stay (4-10 days)
#   - 30% long stay (11-30 days)

def determine_exit(entry, current_date):
    days_on_terminal = (current_date - entry.entry_time.date()).days

    if 1 <= days_on_terminal <= 3:
        return random.random() < 0.35  # 35% chance
    elif 4 <= days_on_terminal <= 10:
        return random.random() < 0.20  # 20% chance
    elif days_on_terminal >= 11:
        return random.random() < 0.30  # 30% chance

    return False
```

**Retrieval Work Order Creation:**
```python
def process_exit_with_retrieval(entry, exit_date, foundation, state):
    """
    Create RETRIEVAL work order for container exit.
    ALL containers have positions (100% placement success).
    """

    position = entry.position  # Always exists

    # Retrieval work order created 2-6 hours before truck arrives
    wo_created = exit_date - timedelta(hours=random.randint(2, 6))
    wo_assigned = wo_created + timedelta(minutes=random.randint(5, 15))
    wo_accepted = wo_assigned + timedelta(minutes=random.randint(1, 5))
    wo_started = wo_accepted + timedelta(minutes=random.randint(5, 15))
    wo_completed = exit_date  # Truck leaves = work order complete

    # Create RETRIEVAL work order
    work_order = WorkOrder.objects.create(
        operation_type="RETRIEVAL",
        container_entry=entry,
        status="COMPLETED",  # All retrievals completed (exit already happened)
        priority="MEDIUM",
        assigned_to_vehicle=random.choice(foundation["vehicles"]),
        created_by=foundation["controlroom_admin"],
        target_zone=position.zone,
        target_row=position.row,
        target_bay=position.bay,
        target_tier=position.tier,
        target_sub_slot=position.sub_slot,
        sla_deadline=wo_created + timedelta(hours=1),
    )

    # Set timestamps
    WorkOrder.objects.filter(id=work_order.id).update(
        created_at=wo_created,
        assigned_at=wo_assigned,
        accepted_at=wo_accepted,
        started_at=wo_started,
        completed_at=wo_completed,
    )

    # Update entry with exit data
    entry.exit_date = exit_date
    entry.exit_transport_type = random.choice(["TRUCK", "TRAIN"])

    if entry.exit_transport_type == "TRUCK":
        region = random.choice(["01", "10", "20", "30"])
        entry.exit_transport_number = f"{region}{random.choice('ABCD')}{random.randint(100, 999)}{random.choice('EF')}{random.choice('GH')}"
    else:
        entry.exit_transport_number = f"W{random.randint(100000, 999999)}"
        entry.exit_train_number = f"T{random.randint(1000, 9999)}"

    entry.destination_station = random.choice([
        "Toshkent-Tovarniy", "Chukursay", "Sergeli", "Bekabad"
    ])
    entry.location = ""  # Clear location
    entry.save()

    # Delete position
    position.delete()

    # Free resources in state
    grid_key = ("A", position.row, position.bay, position.tier, position.sub_slot)
    if grid_key in state["occupancy_grid"]:
        del state["occupancy_grid"][grid_key]

    # Update cursor bay occupancy
    free_bay_in_cursor(entry.company.id, position, state)

    # Mark container available for reuse
    if entry.container.id in state["active_entries"]:
        del state["active_entries"][entry.container.id]
    state["exited_container_ids"].add(entry.container.id)

def free_bay_in_cursor(company_id, position, state):
    """Update bay occupancy when container exits"""
    cursor = state["company_cursors"].get(company_id)
    if not cursor:
        cursor = state["overflow_cursor"]

    bay = position.bay
    slot = position.sub_slot
    current_status = cursor["bay_occupancy"].get(bay, "EMPTY")

    if current_status == "FULL":
        if slot == "A":
            # Check if slot B still occupied
            other_exists = any(
                key for key in state["occupancy_grid"].keys()
                if key[1] == position.row and key[2] == bay and key[4] == "B"
            )
            cursor["bay_occupancy"][bay] = "SLOT_A_USED" if other_exists else "EMPTY"
        else:  # slot B
            cursor["bay_occupancy"][bay] = "SLOT_A_USED"
    elif current_status == "SLOT_A_USED":
        cursor["bay_occupancy"][bay] = "EMPTY"
```

---

## Model Changes Required

**Migration needed for WorkOrder model:**

```python
# File: backend/apps/terminal_operations/models.py

class WorkOrder(TimestampedModel):
    # ADD THESE FIELDS
    OPERATION_CHOICES = [
        ("PLACEMENT", "Размещение"),
        ("RETRIEVAL", "Извлечение"),
    ]
    operation_type = models.CharField(
        max_length=10,
        choices=OPERATION_CHOICES,
        default="PLACEMENT",
        db_index=True,
        help_text="Тип операции: размещение или извлечение контейнера"
    )

    # UPDATE THIS FIELD (increase max from 10 to 20 for overflow)
    target_row = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)],  # Was 10
        help_text="Целевой ряд (1-20)",  # Was (1-10)
    )

    # ... rest of model unchanged

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Наряд на операцию"  # Was "Наряд на размещение"
        verbose_name_plural = "Наряды на операции"  # Was "Наряды на размещение"
        indexes = [
            # ADD THIS INDEX
            models.Index(fields=["operation_type"], name="wo_operation_type_idx"),
            # ... existing indexes
        ]
```

**Migration command:**
```bash
cd backend
source .venv/bin/activate
python manage.py makemigrations terminal_operations --name add_retrieval_work_orders
python manage.py migrate
```

---

## Expected Statistics (90 days)

```
Containers created:        100
Container entries:         ~2000
PreOrders created:         ~1400 (70% of truck entries)
Work orders total:         ~2800
  ├─ PLACEMENT:            ~2000 (98% VERIFIED, 2% IN_PROGRESS/ACCEPTED)
  └─ RETRIEVAL:            ~800 (100% COMPLETED)
Positions created:         ~2000 (100% placement success)
Exits processed:           ~800 (40% of entries)
Containers on terminal:    ~1200
Positions occupied:        ~1200

Company Distribution (by entry volume):
  Large #1:   ~600 entries (30%)
  Large #2:   ~600 entries (30%)
  Medium #1:  ~300 entries (15%)
  Medium #2:  ~300 entries (15%)
  Small #1:   ~100 entries (5%)
  Small #2:   ~67 entries (3.3%)
  Small #3:   ~33 entries (1.7%)

3D Yard Occupancy:
  Company zones (rows 1-15):  ~960 positions (80% of capacity)
  Overflow (rows 16-20):      ~240 positions (overflow capacity)
  Total capacity used:        1200 / 2000 positions (60%)
```

---

## Implementation Steps

### Step 1: Create Migration
```bash
cd backend
source .venv/bin/activate

# Add operation_type field and update target_row validator in models.py
# (see "Model Changes Required" section above)

python manage.py makemigrations terminal_operations --name add_retrieval_work_orders
python manage.py migrate
```

### Step 2: Create Command
```bash
# File: backend/apps/core/management/commands/generate_realistic_data_v2.py

class Command(BaseCommand):
    help = "Generate 90 days of realistic data with company clustering (v2)"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90)
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        # Phase 1: Foundation
        foundation = self._create_foundation_data()

        # Phase 2: Container pool
        container_pool = self._create_container_pool(100)

        # Phase 3: Space allocation
        state = self._initialize_state(foundation)

        # Phase 4: Chronological generation
        self._generate_timeline(options["days"], foundation, container_pool, state)

        # Phase 5: Statistics
        self._print_statistics()
```

### Step 3: Implement Core Algorithms

Implement these key functions following the designs above:
1. `get_next_position_guaranteed()` - Sequential position allocator
2. `create_placement_work_order()` - PLACEMENT work orders
3. `process_exit_with_retrieval()` - RETRIEVAL work orders
4. `advance_cursor()` - Cursor movement logic
5. `free_bay_in_cursor()` - Bay occupancy updates

### Step 4: Test & Validate
```bash
# Dry run first (no data saved)
python manage.py generate_realistic_data_v2 --days 90 --dry-run

# Real run with clearing existing data
python manage.py generate_realistic_data_v2 --days 90 --clear

# Verify results
python manage.py shell
>>> from apps.terminal_operations.models import ContainerEntry, WorkOrder, ContainerPosition
>>> print(f"Entries: {ContainerEntry.objects.count()}")
>>> print(f"Positions: {ContainerPosition.objects.count()}")
>>> print(f"Work Orders: {WorkOrder.objects.count()}")
>>> print(f"  Placement: {WorkOrder.objects.filter(operation_type='PLACEMENT').count()}")
>>> print(f"  Retrieval: {WorkOrder.objects.filter(operation_type='RETRIEVAL').count()}")
```

### Step 5: Verify Company Clustering
```bash
# Check that companies are tightly clustered in their assigned rows
python manage.py shell

>>> from apps.terminal_operations.models import ContainerPosition, ContainerEntry
>>> from apps.accounts.models import Company

>>> company = Company.objects.first()
>>> positions = ContainerPosition.objects.filter(container_entry__company=company)
>>> rows = positions.values_list('row', flat=True).distinct()
>>> print(f"{company.name}: Rows {list(rows)}")  # Should be contiguous (e.g., [1, 2, 3, 4])

>>> # Check bay fill pattern for first row
>>> row_1_positions = positions.filter(row=1).order_by('bay', 'tier', 'sub_slot')
>>> for pos in row_1_positions[:20]:
...     print(f"Bay {pos.bay}, Tier {pos.tier}, Slot {pos.sub_slot}")
... # Should show sequential fill: Bay 1-10 tier 1, then Bay 1-N tier 2
```

---

## Success Criteria

✅ **Tight Company Clustering:** Companies occupy contiguous rows with sequential bay filling
✅ **100% Placement Success:** Every container has a position (no failed work orders)
✅ **Realistic Work Orders:** Both PLACEMENT and RETRIEVAL work orders for complete lifecycle
✅ **80% Density:** Operational gaps for realism (20% positions skipped)
✅ **Clean Data:** No constraint violations, no orphaned positions, no impossible states
✅ **Performance:** Script completes in <5 minutes for 90 days (~2000 entries)

---

## Future Enhancements

1. **Multi-zone support:** Currently uses only Zone A, could expand to zones B-E
2. **Dynamic company sizing:** Adjust row allocation based on actual volume patterns
3. **Seasonal patterns:** Higher volume in certain months (harvest season, etc.)
4. **Failed operations:** Add small percentage of FAILED work orders for realism
5. **Crane operation tracking:** Link work orders to CraneOperation model for billing

---

## Document History

- **2026-01-19:** Initial design document created after brainstorming session
- **Status:** Design validated, ready for implementation
