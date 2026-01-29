# Unified 3D Yard View — Design Document

**Date:** 2026-01-27
**Status:** Draft
**Scope:** Replace existing 3D yard placement with unified yard view backed by real API data

---

## 1. Goal

Replace the current fragmented yard views (ContainerPlacement, YardTestView, yard-test-dev) with a **single unified 3D yard view** at `/yard` that:

- Renders all containers using **real backend data** (not mock/JSON)
- Uses the backend as the **single source of truth** for both logical positions (zone/row/bay/tier) and physical positions (DXF x, y, rotation)
- Carries forward **all** YardTestView features: 3D rendering, settings drawer, debug mode, draw mode, gate cameras, vehicle animation, tooltips, stats overlays

---

## 2. Architecture

```
Route: /yard (auth required, admin role)
│
├─ UnifiedYardView.vue
│  ├─ Fetches GET /api/terminal/yard/slots/
│  ├─ Maps API data → ContainerPosition[] + ContainerData[]
│  ├─ Passes to YardView3D.vue (existing 3D engine)
│  └─ All overlay components (settings, debug, draw, gate cameras, stats, tooltips)
│
Backend:
├─ YardSlot model (zone/row/bay/tier + dxf_x/dxf_y/rotation)
├─ GET /api/terminal/yard/slots/ endpoint
├─ Management command: import_yard_slots (seed from containers.json)
│
Removed:
├─ ContainerPlacement.vue
├─ /placement route
├─ /yard-test-dev route
├─ /yard-test route
```

---

## 3. Backend Changes

### 3.1 New Model: `YardSlot`

Location: `backend/apps/terminal_operations/models.py`

```python
class YardSlot(TimestampedModel):
    """Physical container slot with logical + physical coordinates."""

    # Logical position
    zone = models.CharField(max_length=10)
    row = models.PositiveSmallIntegerField()
    bay = models.PositiveSmallIntegerField()
    tier = models.PositiveSmallIntegerField(default=1)

    # Physical position (DXF coordinates for 3D rendering)
    dxf_x = models.FloatField(help_text="Original DXF X coordinate")
    dxf_y = models.FloatField(help_text="Original DXF Y coordinate")
    rotation = models.FloatField(default=0, help_text="Rotation in degrees")
    container_size = models.CharField(
        max_length=10,
        choices=[('20ft', '20ft'), ('40ft', '40ft'), ('45ft', '45ft')],
        default='40ft'
    )

    # Occupant (null = empty slot)
    container_entry = models.OneToOneField(
        'ContainerEntry',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='yard_slot'
    )

    class Meta:
        unique_together = ['zone', 'row', 'bay', 'tier']
        ordering = ['zone', 'row', 'bay', 'tier']

    def __str__(self):
        return f"{self.zone}-R{self.row:02d}-B{self.bay:02d}-T{self.tier}"
```

### 3.2 Serializer

```python
class YardSlotSerializer(serializers.ModelSerializer):
    container_entry = ContainerEntryBriefSerializer(read_only=True)

    class Meta:
        model = YardSlot
        fields = [
            'id', 'zone', 'row', 'bay', 'tier',
            'dxf_x', 'dxf_y', 'rotation', 'container_size',
            'container_entry'
        ]

class ContainerEntryBriefSerializer(serializers.ModelSerializer):
    """Lightweight serializer for yard slot occupant data."""
    company_name = serializers.CharField(source='company.name', default=None)
    container_number = serializers.CharField(source='container.container_number')
    iso_type = serializers.CharField(source='container.iso_type')

    class Meta:
        model = ContainerEntry
        fields = [
            'id', 'container_number', 'iso_type', 'status',
            'is_hazmat', 'imo_class', 'priority',
            'company_name', 'dwell_time_days',
            'entry_time', 'cargo_name'
        ]
```

### 3.3 API Endpoint

```
GET /api/terminal/yard/slots/
```

Returns all yard slots with occupant data. Supports query params:
- `?zone=A` — filter by zone
- `?occupied=true` — only slots with containers
- `?container_size=40ft` — filter by slot size

Response: standard `{ success: true, data: [...] }` format.

### 3.4 Management Command: `import_yard_slots`

Location: `backend/apps/terminal_operations/management/commands/import_yard_slots.py`

Reads `frontend/src/data/containers.json` and creates `YardSlot` records:
- Uses `_original.x` and `_original.y` for DXF coordinates
- Uses `rotation` for rotation
- Derives `container_size` from `blockName` (40ft, 20ft)
- Assigns `zone`, `row`, `bay` based on spatial grouping:
  - Group containers by proximity into zones
  - Within each zone, assign row/bay by sorted x/y position
- Tier defaults to 1 (ground level); tiers 2-4 created as empty slots above occupied ones

---

## 4. Frontend Changes

### 4.1 New View: `UnifiedYardView.vue`

Based on the existing `YardTestView.vue` with these changes:

**Data loading:**
- Remove `import containersJson from '@/data/containers.json'`
- Remove `generateMockContainerData()` function
- Add `fetchYardSlots()` that calls `GET /api/terminal/yard/slots/`
- Map API response to `ContainerPosition[]` and `ContainerData[]`
- Auto-refresh every 30 seconds

**Data mapping:**
```typescript
interface YardSlotResponse {
  id: number
  zone: string
  row: number
  bay: number
  tier: number
  dxf_x: number
  dxf_y: number
  rotation: number
  container_size: string
  container_entry: {
    id: number
    container_number: string
    iso_type: string
    status: 'LADEN' | 'EMPTY'
    is_hazmat: boolean
    imo_class?: string
    priority: string
    company_name?: string
    dwell_time_days: number
    entry_time: string
    cargo_name?: string
  } | null
}
```

**Features carried forward (all from YardTestView):**
- YardView3D core rendering
- YardSettingsDrawer (layer visibility, color modes, label toggles)
- ContainerTooltip (hover/click with real data)
- GateCamera3D + GateCameraWidget
- VehicleStatsOverlay + GateStatsHeader
- YardDebugTooltip (press D)
- YardDrawOverlay + YardGridOverlay

### 4.2 Modify `useContainers3D.ts`

- Remove static `import containersJson`
- Accept container positions as a reactive parameter
- Keep all rendering logic (InstancedMesh, color modes, selection, hover) unchanged

### 4.3 New Service: `yardService.ts`

```typescript
export async function getYardSlots(params?: {
  zone?: string
  occupied?: boolean
}): Promise<YardSlotResponse[]> {
  const { data } = await api.get('/terminal/yard/slots/', { params })
  return data.data
}
```

### 4.4 Router Changes

```typescript
// Remove
{ path: '/placement', component: ContainerPlacement }
{ path: '/yard-test', component: YardTestView }
{ path: '/yard-test-dev', component: YardTestView }

// Add
{ path: '/yard', component: UnifiedYardView, meta: { requiresAuth: true } }
```

### 4.5 Files to Delete

- `frontend/src/views/ContainerPlacement.vue`
- `frontend/src/views/YardTestView.vue` (replaced by UnifiedYardView)
- Route entries for `/placement`, `/yard-test`, `/yard-test-dev`
- `frontend/src/services/placementService.ts` (if only used by ContainerPlacement)
- `frontend/src/types/placement.ts` (if only used by ContainerPlacement)

---

## 5. Migration Strategy

### Phase 1: Backend (no frontend breakage)
1. Create `YardSlot` model + migration
2. Create serializer + viewset + URL
3. Create `import_yard_slots` management command
4. Run import to seed database with containers.json positions

### Phase 2: Frontend
5. Create `yardService.ts`
6. Create `UnifiedYardView.vue` (copy YardTestView, replace mock data with API)
7. Modify `useContainers3D.ts` to accept reactive positions
8. Update router: add `/yard`, remove old routes

### Phase 3: Cleanup
9. Delete old views (ContainerPlacement, YardTestView)
10. Delete unused services/types (placementService, placement types)
11. Update sidebar/navigation links to point to `/yard`

---

## 6. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Zone/row/bay assignment during import is subjective | Semi-automated: script groups by proximity, human reviews |
| API latency on ~1000 slots | Single query with select_related, lightweight serializer |
| 30s polling could be heavy | Use `If-Modified-Since` header or switch to WebSocket later |
| Existing placement features lost | ContainerPlacement's placement workflow (suggest/assign) can be added to unified view later if needed |

---

## 7. Out of Scope

- Placement workflow (suggest position, assign container) — can be added as a feature of the unified view later
- WebSocket real-time updates — polling is sufficient for now
- Admin UI for editing YardSlot positions — manage via Django admin initially
