# Container Type Segregation Design

**Date:** 2026-01-19
**Status:** Approved for Implementation
**Target:** `backend/apps/core/management/commands/generate_realistic_data_v2.py`

## Executive Summary

Enhance realistic data generation to enforce terminal industry best practices:
- **Row-level homogeneity**: Each row dedicated to specific size/status combination
- **Stacking physics**: 40ft containers cannot rest on single 20ft containers
- **Balanced terminal**: Proportional row allocation matching typical container volumes

## Business Requirements

### Current Constraints (Already Implemented)
1. ✅ Tier-major stacking (ground-first physics)
2. ✅ No floating containers (vertical support required)
3. ✅ Terminal boundaries (rows 1-10 only)
4. ✅ Exit validation (can't remove if containers above)

### New Constraints (This Design)
1. **Row-level type segregation**: Each row contains only one size/status combination
2. **40ft-above-20ft prevention**: 40ft containers require full bay support below
3. **Proportional allocation**: Rows distributed to match realistic container mix

## Container Type Classification

### Size Extraction from ISO Type

ISO 6346 container codes encode size in the first character:
- `2` = 20ft containers (`22G1`, `25G1`, `22R1`, `22K2`, etc.)
- `4` = 40ft containers (`42G1`, `42R1`, `42U1`, `42P1`, etc.)
- `L` = 45ft containers (`L5G1`, `L5R1`) → treated as 40ft for bay purposes

```python
def get_container_size(iso_type: str) -> str:
    """
    Extract container size from ISO 6346 type code.

    Args:
        iso_type: ISO container type (e.g., '22G1', '42G1', 'L5G1')

    Returns:
        '20ft' or '40ft'

    Raises:
        ValueError: If ISO type is unrecognized
    """
    first_char = iso_type[0].upper()
    if first_char == '2':
        return '20ft'
    elif first_char in ('4', 'L'):  # 45ft uses 40ft bay space
        return '40ft'
    else:
        raise ValueError(f"Unknown ISO type: {iso_type}")
```

### Container Status

From `ContainerEntry.status` field:
- `LADEN` - Full container with cargo
- `EMPTY` - Empty container awaiting repositioning

### Four Container Types

Combining size × status creates 4 distinct types:
1. **40ft laden** - Most common in international trade
2. **20ft laden** - Regional shipments, smaller cargo
3. **40ft empty** - Repositioning inventory
4. **20ft empty** - Less common, quick turnover

## Row Allocation Strategy

### Balanced Terminal Distribution (Option B - Selected)

10 rows allocated proportionally to match typical terminal operations:

| Container Type | Target % | Rows Allocated | Row Numbers |
|---------------|----------|----------------|-------------|
| 40ft laden    | 35%      | 3 rows (30%)   | 1, 2, 3     |
| 20ft laden    | 25%      | 3 rows (30%)   | 4, 5, 6     |
| 40ft empty    | 25%      | 2 rows (20%)   | 7, 8        |
| 20ft empty    | 15%      | 2 rows (20%)   | 9, 10       |

**Row allocation constant:**
```python
ROW_ALLOCATION = {
    ('40ft', 'LADEN'): [1, 2, 3],
    ('20ft', 'LADEN'): [4, 5, 6],
    ('40ft', 'EMPTY'): [7, 8],
    ('20ft', 'EMPTY'): [9, 10],
}
```

**Rationale:**
- Discrete rows prevent perfect percentage matching (3-3-2-2 split is optimal)
- Slight bias toward laden containers (60% vs 60% target) matches working terminals
- Each type gets contiguous rows for operational efficiency

## Multi-Type Cursor System

### Previous Architecture (Single Cursor)

Each company had ONE cursor moving through assigned rows:
```python
state["company_cursors"][company_id] = {
    "rows": [1, 2, 3, 4],  # Company's assigned rows
    "current_row_idx": 0,
    "current_bay": 1,
    "current_tier": 1,
    # ...
}
```

### New Architecture (Four Cursors)

Each company has FOUR cursors - one per container type:
```python
state["company_cursors"][company_id] = {
    # Cursor for 40ft laden
    ('40ft', 'LADEN'): {
        "rows": [1, 2, 3],           # Only 40ft laden rows
        "current_row_idx": 0,
        "current_bay": 1,
        "current_tier": 1,
        "positions_filled": 0,
        "positions_skipped": 0,
    },

    # Cursor for 20ft laden
    ('20ft', 'LADEN'): {
        "rows": [4, 5, 6],           # Only 20ft laden rows
        "current_row_idx": 0,
        "current_bay": 1,
        "current_tier": 1,
        "positions_filled": 0,
        "positions_skipped": 0,
    },

    # Cursor for 40ft empty
    ('40ft', 'EMPTY'): {
        "rows": [7, 8],              # Only 40ft empty rows
        "current_row_idx": 0,
        "current_bay": 1,
        "current_tier": 1,
        "positions_filled": 0,
        "positions_skipped": 0,
    },

    # Cursor for 20ft empty
    ('20ft', 'EMPTY'): {
        "rows": [9, 10],             # Only 20ft empty rows
        "current_row_idx": 0,
        "current_bay": 1,
        "current_tier": 1,
        "positions_filled": 0,
        "positions_skipped": 0,
    },
}
```

**Overflow cursors (shared across all companies):**
```python
state["overflow_cursors"] = {
    ('40ft', 'LADEN'): create_cursor([1, 2, 3]),
    ('20ft', 'LADEN'): create_cursor([4, 5, 6]),
    ('40ft', 'EMPTY'): create_cursor([7, 8]),
    ('20ft', 'EMPTY'): create_cursor([9, 10]),
}
```

### Cursor Selection Logic

```python
def place_container(entry, container, state):
    # 1. Classify container
    size = get_container_size(container.iso_type)
    status = entry.status
    container_type = (size, status)

    # 2. Get company-specific cursor for this type
    company = entry.company
    cursor = state["company_cursors"][company.id][container_type]

    # 3. Try company cursor first
    position = get_position_from_cursor(cursor, size == '40ft', container_type, state)

    # 4. Fall back to overflow cursor if needed
    if not position:
        overflow_cursor = state["overflow_cursors"][container_type]
        position = get_position_from_cursor(overflow_cursor, size == '40ft', container_type, state)

    return position
```

**Key insight:** Row segregation is enforced by cursor row lists. A 40ft laden cursor can NEVER access rows 4-10 because its row list only contains `[1, 2, 3]`. No additional validation needed.

## Stacking Physics Constraints

### Constraint 1: Vertical Support (Already Implemented)

Containers at tier > 1 must have support directly below:
```python
if tier > 1:
    below_key = (zone, row, bay, tier - 1, slot)
    if below_key not in state["occupancy_grid"]:
        return False, "No support below"
```

### Constraint 2: 40ft-Above-20ft Prevention (New)

**Physical problem:** A 40ft container (12.2m wide) cannot rest on a single 20ft container (6.1m wide) - structurally unstable.

**When does this occur?**
- Row homogeneity prevents 40ft containers from entering 20ft rows (rows 4-6, 9-10)
- But within 40ft rows, a bay might have:
  - Tier 1, Slot A: 40ft container (occupies both A and B)
  - Later, that container exits
  - Tier 1, Slot B still empty
  - Can we place 40ft at tier 2? NO - only slot B has support

**Validation logic:**
```python
def can_place_40ft_container(zone, row, bay, tier, state):
    """
    Check if 40ft container can be placed at this position.
    40ft containers need full bay support (both slots A and B occupied below).
    """
    if tier == 1:
        return True  # Ground level always OK

    # Check tier-1 for both slots
    below_a_key = (zone, row, bay, tier - 1, 'A')
    below_b_key = (zone, row, bay, tier - 1, 'B')

    a_exists = below_a_key in state["occupancy_grid"]
    b_exists = below_b_key in state["occupancy_grid"]

    # Both must exist OR both must be empty
    if a_exists != b_exists:
        return False, "Cannot place 40ft above single 20ft container"

    # Both occupied (full bay below) OR both empty (ground level equivalent)
    return True, "OK"
```

**When applied:**
- Only for 40ft containers at tier > 1
- 20ft containers don't need this check (they occupy single slots)
- Integrated into `get_position_from_cursor()` placement loop

## Exit Validation Updates

### Existing Logic (Preserved)

Containers cannot exit if others are stacked above:
```python
def can_exit_container(position, state):
    if position.tier < 4:
        for tier_above in range(position.tier + 1, 5):
            above_key = (position.zone, position.row, position.bay,
                        tier_above, position.sub_slot)
            if above_key in state["occupancy_grid"]:
                return False, "Containers stacked above"
    return True, "OK"
```

### New Considerations

**Q:** When a 40ft container exits from tier 1, does it affect tier 2 40ft containers?

**A:** YES - the tier 2 40ft container would lose support. The existing "containers stacked above" check handles this:
- Tier 1 40ft occupies slots A and B
- Tier 2 40ft occupies slots A and B
- When tier 1 exits, check for tier 2 slot A → FOUND → exit blocked ✓

**No changes needed to exit validation** - the existing slot-by-slot check is sufficient.

### State Tracking Updates

Exit removes container from:
1. `occupancy_grid` - frees the physical position
2. `active_entries` - marks container as departed

**No cursor updates needed** - cursors only move forward during placement. Freed positions remain empty (contributing to realistic density).

## Complete Implementation Flow

### Initialization (Day 1)

```python
def initialize_state():
    state = {
        "occupancy_grid": {},        # (zone, row, bay, tier, slot) → entry_id
        "active_entries": {},        # container_id → entry
        "company_cursors": {},       # company_id → {container_type → cursor}
        "overflow_cursors": {},      # container_type → cursor
        "stats_by_type": defaultdict(lambda: {
            "entries": 0,
            "exits": 0,
            "failed_placements": 0
        }),
    }

    # Initialize overflow cursors (shared)
    for container_type, rows in ROW_ALLOCATION.items():
        state["overflow_cursors"][container_type] = {
            "rows": rows,
            "current_row_idx": 0,
            "current_bay": 1,
            "current_tier": 1,
            "positions_filled": 0,
            "positions_skipped": 0,
        }

    # Initialize company cursors (per company, per type)
    for company in Company.objects.all():
        state["company_cursors"][company.id] = {}
        for container_type, rows in ROW_ALLOCATION.items():
            state["company_cursors"][company.id][container_type] = {
                "rows": rows.copy(),  # Each company gets same row allocation
                "current_row_idx": 0,
                "current_bay": 1,
                "current_tier": 1,
                "positions_filled": 0,
                "positions_skipped": 0,
            }

    return state
```

### Daily Operations Loop

```python
def generate_day_operations(day_date, state):
    # PHASE 1: Process exits (containers leaving terminal)
    process_exits_for_day(day_date, state)

    # PHASE 2: Generate new entries
    num_entries = random.randint(10, 30)

    for _ in range(num_entries):
        # 2a. Select container from foundation data
        container = random.choice(available_containers)

        # 2b. Classify container
        size = get_container_size(container.iso_type)
        status = random.choice(['LADEN', 'EMPTY'])
        container_type = (size, status)

        # 2c. Select company
        company = random.choice(companies)

        # 2d. Create entry
        entry = ContainerEntry.objects.create(
            container=container,
            status=status,
            entry_time=day_date + random_time_offset(),
            company=company,
            transport_type=random.choice(['TRUCK', 'WAGON', 'TRAIN']),
            # ... other fields
        )

        # 2e. Try to place
        position = try_place_container(entry, container_type, state)

        if position:
            create_position_and_work_order(entry, position, state)
            state["stats_by_type"][container_type]["entries"] += 1
        else:
            entry.delete()  # No space, cancel entry
            state["stats_by_type"][container_type]["failed_placements"] += 1
```

### Container Placement with All Constraints

```python
def get_position_from_cursor(cursor, is_40ft, container_type, state):
    """
    Find next available position enforcing all constraints:
    1. Row allocation (via cursor row list)
    2. Vertical support (tier-1 exists)
    3. 40ft-above-20ft prevention
    4. Occupancy (position not already taken)
    5. 80% density (skip 20% at tier 1)
    """
    max_attempts = 400  # 10 rows × 10 bays × 4 tiers

    for attempt in range(max_attempts):
        # Get current cursor position
        if cursor["current_row_idx"] >= len(cursor["rows"]):
            return None  # Exhausted all allocated rows

        row = cursor["rows"][cursor["current_row_idx"]]
        bay = cursor["current_bay"]
        tier = cursor["current_tier"]

        # CONSTRAINT 1: 80% density (skip 20% at ground level)
        if tier == 1 and random.random() < 0.2:
            cursor["positions_skipped"] += 1
            advance_cursor(cursor)
            continue

        # CONSTRAINT 2: Vertical support (tier > 1 must have tier-1)
        if tier > 1:
            below_key = ("A", row, bay, tier - 1, "A")
            if below_key not in state["occupancy_grid"]:
                # No support, skip to next bay at tier 1
                cursor["current_bay"] += 1
                cursor["current_tier"] = 1
                if cursor["current_bay"] > 10:
                    cursor["current_row_idx"] += 1
                    cursor["current_bay"] = 1
                continue

        # CONSTRAINT 3: 40ft-above-20ft prevention
        if is_40ft and tier > 1:
            below_a = ("A", row, bay, tier - 1, "A")
            below_b = ("A", row, bay, tier - 1, "B")

            a_exists = below_a in state["occupancy_grid"]
            b_exists = below_b in state["occupancy_grid"]

            # If exactly one slot occupied, can't place 40ft
            if a_exists != b_exists:
                advance_cursor(cursor)
                continue

        # CONSTRAINT 4: Occupancy check
        position_key_a = ("A", row, bay, tier, "A")
        position_key_b = ("A", row, bay, tier, "B")

        if is_40ft:
            # 40ft needs full bay (slot A marks occupation)
            if position_key_a not in state["occupancy_grid"]:
                cursor["positions_filled"] += 1
                advance_cursor(cursor)
                return (row, bay, tier, "A")
        else:
            # 20ft tries slot A, then B
            if position_key_a not in state["occupancy_grid"]:
                cursor["positions_filled"] += 1
                advance_cursor(cursor)
                return (row, bay, tier, "A")
            elif position_key_b not in state["occupancy_grid"]:
                cursor["positions_filled"] += 1
                advance_cursor(cursor)
                return (row, bay, tier, "B")

        # Position occupied, try next
        advance_cursor(cursor)

    return None  # No position found after max attempts
```

## Verification and Testing

### Post-Generation Verification Checks

Extend existing `_verify_placements()` method:

```python
def _verify_placements(self):
    """Verify all placement constraints after generation"""
    positions = ContainerPosition.objects.all()
    position_dict = {
        (p.zone, p.row, p.bay, p.tier, p.sub_slot): p
        for p in positions
    }

    # Existing checks
    floating_count = 0
    boundary_violations = 0

    # NEW: Row homogeneity check
    row_violations = 0
    row_type_map = {}  # row → set of container types seen

    for (zone, row, bay, tier, slot), pos in position_dict.items():
        entry = pos.container_entry
        container = entry.container

        size = get_container_size(container.iso_type)
        status = entry.status
        container_type = (size, status)

        # Track types per row
        if row not in row_type_map:
            row_type_map[row] = set()
        row_type_map[row].add(container_type)

    # Check each row has only one type
    for row, types in row_type_map.items():
        if len(types) > 1:
            row_violations += 1
            print(f"  ⚠️  Row {row} has mixed types: {types}")

    # NEW: 40ft-above-20ft check
    stacking_violations = 0

    for (zone, row, bay, tier, slot), pos in position_dict.items():
        if tier > 1:
            entry = pos.container_entry
            size = get_container_size(entry.container.iso_type)

            if size == '40ft':
                # Check full bay support below
                below_a = (zone, row, bay, tier - 1, 'A')
                below_b = (zone, row, bay, tier - 1, 'B')

                a_exists = below_a in position_dict
                b_exists = below_b in position_dict

                if a_exists != b_exists:
                    stacking_violations += 1
                    print(f"  ⚠️  40ft at tier {tier} above single 20ft "
                          f"at {zone}-R{row:02d}-B{bay:02d}")

    # Report
    print("\n📋 VERIFICATION RESULTS")
    print("=" * 70)

    if floating_count == 0:
        print("  ✓ No floating containers")
    else:
        print(f"  ✗ Floating containers: {floating_count}")

    if boundary_violations == 0:
        print("  ✓ All containers within boundaries (rows 1-10)")
    else:
        print(f"  ✗ Boundary violations: {boundary_violations}")

    if row_violations == 0:
        print("  ✓ Row homogeneity maintained (each row = one type)")
    else:
        print(f"  ✗ Row homogeneity violations: {row_violations}")

    if stacking_violations == 0:
        print("  ✓ No 40ft containers above single 20ft containers")
    else:
        print(f"  ✗ Stacking violations: {stacking_violations}")
```

### Test Scenarios

**Scenario 1: Balanced placement**
- Generate 30 days
- Expect ~30% entries in rows 1-3 (40ft laden)
- Expect ~30% entries in rows 4-6 (20ft laden)
- Verify no mixed types within any row

**Scenario 2: Type exhaustion**
- Fill rows 1-3 completely (40ft laden)
- Try to place more 40ft laden containers
- Expect graceful failure (entry deleted, stats incremented)

**Scenario 3: Exit with stacking**
- Place tier 1 and tier 2 40ft containers in same bay
- Try to exit tier 1 container
- Expect rejection (tier 2 container blocks exit)

**Scenario 4: Mixed bay scenario**
- Place 20ft container at tier 1 slot A
- Leave tier 1 slot B empty
- Try to place 40ft at tier 2
- Expect rejection (insufficient support)

## Success Criteria

✅ **Row homogeneity:** Every row contains only one container type (size/status combination)

✅ **Proportional distribution:** Containers distributed approximately 30/30/20/20 across the 4 types

✅ **No stacking violations:** Zero cases of 40ft containers resting on single 20ft containers

✅ **Existing constraints preserved:** All previous physics constraints still enforced (floating, boundaries, exit blocking)

✅ **Visual verification:** 3D frontend shows clearly segregated rows by type

## Implementation Checklist

### Phase 1: Helper Functions
- [ ] Add `get_container_size(iso_type)` function
- [ ] Add `ROW_ALLOCATION` constant
- [ ] Add `can_place_40ft_container()` validation function

### Phase 2: State Initialization
- [ ] Modify `_initialize_state()` to create multi-type cursors
- [ ] Initialize `overflow_cursors` with 4 type-specific cursors
- [ ] Initialize `company_cursors` with 4 cursors per company
- [ ] Add `stats_by_type` tracking dictionary

### Phase 3: Placement Logic
- [ ] Modify `_get_position_from_cursor()` to accept `container_type` parameter
- [ ] Add 40ft-above-20ft validation to placement loop
- [ ] Update cursor selection logic to use `container_type` key

### Phase 4: Entry Generation
- [ ] Modify entry creation to classify containers by type
- [ ] Select appropriate cursor based on container type
- [ ] Update stats tracking by type

### Phase 5: Verification
- [ ] Add row homogeneity verification
- [ ] Add 40ft-above-20ft stacking verification
- [ ] Update statistics output to show per-type metrics

### Phase 6: Testing
- [ ] Run 30-day generation test
- [ ] Verify row distribution matches allocation
- [ ] Check all constraints in verification output
- [ ] Visual inspection in 3D frontend

## Migration Notes

**Database:** No schema changes required - using existing models

**Foundation data:** Must already have containers with varied `iso_type` codes (confirmed by user)

**Backward compatibility:** This is a data generation script change only - does not affect API or frontend

## Risk Mitigation

**Risk 1:** Lower terminal utilization due to type segregation
- **Mitigation:** 80% density target per type maintains realistic fill
- **Fallback:** Adjust density percentage if utilization too low

**Risk 2:** Uneven type distribution in foundation data
- **Mitigation:** Verification will show actual vs target distribution
- **Fallback:** Adjust `ROW_ALLOCATION` percentages if needed

**Risk 3:** Complex multi-cursor state management
- **Mitigation:** Each cursor is independent - no cross-cursor dependencies
- **Fallback:** Extensive logging to debug cursor state issues

## Future Enhancements

**Post-MVP improvements:**
1. **Dynamic row allocation:** Adjust row assignments based on actual container mix
2. **Zone expansion:** Extend to zones B-E with per-zone type preferences
3. **Company preferences:** Some companies prefer certain container types
4. **Seasonal variation:** Change type proportions over time (summer/winter patterns)

---

**Approved by:** User (2026-01-19)
**Next step:** Implementation planning with step-by-step code changes
