# 3D Terminal Placement Feature - Implementation Plan

## Overview

This document outlines the implementation plan for adding a 3D terminal yard visualization feature to the MTT Container Terminal Management System.

### Feature Summary
- **Visual yard overview**: See all containers in their physical 3D positions
- **Container placement planning**: Auto-suggest optimal positions for incoming containers
- **Container search/locate**: Click containers in 3D to view details
- **Bi-directional integration**: Table ↔ 3D view synchronization

### Technical Decisions
- **Architecture**: Pragmatic Balance (structured but not over-engineered)
- **Database**: New `ContainerPosition` model (1-to-1 with ContainerEntry)
- **3D Library**: Three.js direct usage (no wrapper framework)
- **Rendering**: InstancedMesh for performance (handles 2000+ containers)

---

## Terminal Configuration

| Setting | Value |
|---------|-------|
| Zones | 5 (A, B, C, D, E) |
| Rows per zone | 10 |
| Bays per zone | 10 |
| Max tiers | 4 |
| Capacity per zone | ~400 TEU |
| Total capacity | ~2000 TEU |
| Position format | `A-R03-B15-T2` (Zone-Row-Bay-Tier) |

### Color Coding
- **Laden containers**: Green (`#52c41a`)
- **Empty containers**: Blue (`#1677ff`)
- **Hovered container**: Orange (`#fa8c16`)
- **Selected container**: Gold (`#faad14`)

---

## Database Schema

### New Model: ContainerPosition

```python
# backend/apps/terminal_operations/models.py

class ContainerPosition(TimestampedModel):
    """
    3D position for container placement in terminal yard.
    One-to-one relationship with ContainerEntry.
    """

    container_entry = models.OneToOneField(
        ContainerEntry,
        on_delete=models.CASCADE,
        related_name="position",
        help_text="Связанная запись въезда контейнера"
    )

    # Zone (A-E)
    zone = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E')],
        db_index=True,
        help_text="Зона терминала"
    )

    # Row (1-10)
    row = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Номер ряда (1-10)"
    )

    # Bay (1-10)
    bay = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Номер отсека (1-10)"
    )

    # Tier (1-4)
    tier = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Ярус (1-4)"
    )

    # Metadata
    auto_assigned = models.BooleanField(
        default=False,
        help_text="Была ли позиция назначена автоматически"
    )

    class Meta:
        ordering = ['zone', 'row', 'bay', 'tier']
        verbose_name = "Позиция контейнера"
        verbose_name_plural = "Позиции контейнеров"
        indexes = [
            models.Index(fields=['zone', 'row', 'bay', 'tier'], name='position_coords_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['zone', 'row', 'bay', 'tier'],
                name='unique_position',
                violation_error_message="Эта позиция уже занята другим контейнером"
            )
        ]

    @property
    def coordinate_string(self):
        """Return formatted coordinate: A-R03-B15-T2"""
        return f"{self.zone}-R{self.row:02d}-B{self.bay:02d}-T{self.tier}"
```

### Migration Strategy
1. Create new `ContainerPosition` model
2. Keep existing `ContainerEntry.location` field (backward compatible)
3. Auto-sync `location` text when position is assigned
4. Existing containers without positions will show as "unplaced"

---

## API Endpoints

### 1. Get 3D Layout
```
GET /api/terminal/placement/layout/

Response:
{
  "zones": ["A", "B", "C", "D", "E"],
  "dimensions": {
    "max_rows": 10,
    "max_bays": 10,
    "max_tiers": 4
  },
  "containers": [
    {
      "id": 123,
      "container_number": "HDMU6565958",
      "iso_type": "42G1",
      "status": "LADEN",
      "position": {
        "zone": "A",
        "row": 3,
        "bay": 15,
        "tier": 2,
        "coordinate": "A-R03-B15-T2"
      },
      "entry_time": "2025-01-10T10:00:00Z",
      "dwell_time_days": 5,
      "company_name": "Company ABC"
    }
  ],
  "stats": {
    "total_capacity": 2000,
    "occupied": 450,
    "available": 1550,
    "by_zone": {
      "A": {"occupied": 120, "available": 280},
      "B": {"occupied": 100, "available": 300}
    }
  }
}
```

### 2. Auto-Suggest Position
```
POST /api/terminal/placement/suggest/

Request:
{
  "container_entry_id": 123,
  "zone_preference": "A"  // Optional
}

Response:
{
  "success": true,
  "suggested_position": {
    "zone": "A",
    "row": 3,
    "bay": 15,
    "tier": 1,
    "coordinate": "A-R03-B15-T1"
  },
  "reason": "Nearest available ground-level slot in zone A",
  "alternatives": [
    {"zone": "A", "row": 3, "bay": 16, "tier": 1},
    {"zone": "B", "row": 1, "bay": 1, "tier": 1}
  ]
}
```

### 3. Assign Position
```
POST /api/terminal/placement/assign/

Request:
{
  "container_entry_id": 123,
  "position": {
    "zone": "A",
    "row": 3,
    "bay": 15,
    "tier": 2
  }
}

Response:
{
  "success": true,
  "data": {
    "id": 456,
    "container_entry": 123,
    "zone": "A",
    "row": 3,
    "bay": 15,
    "tier": 2,
    "coordinate": "A-R03-B15-T2",
    "auto_assigned": false
  },
  "message": "Позиция успешно назначена"
}
```

### 4. Move Container
```
PATCH /api/terminal/placement/{position_id}/move/

Request:
{
  "new_position": {
    "zone": "B",
    "row": 5,
    "bay": 8,
    "tier": 1
  }
}

Response:
{
  "success": true,
  "data": {...},
  "message": "Контейнер перемещён"
}
```

### 5. Get Available Positions
```
GET /api/terminal/placement/available/?zone=A&tier=1

Response:
{
  "available": [
    {"zone": "A", "row": 3, "bay": 15, "tier": 1},
    {"zone": "A", "row": 3, "bay": 16, "tier": 1}
  ],
  "count": 280,
  "zone_stats": {
    "total": 400,
    "occupied": 120
  }
}
```

### 6. Remove Position (on container exit)
```
DELETE /api/terminal/placement/{position_id}/

Response:
{
  "success": true,
  "message": "Позиция освобождена"
}
```

---

## Backend Service Layer

### PlacementService

```python
# backend/apps/terminal_operations/services/placement_service.py

class PlacementService(BaseService):
    """
    Business logic for container placement operations.
    Handles auto-suggestion, validation, and position management.
    """

    def get_layout(self) -> dict:
        """Get complete 3D layout data for visualization."""

    def suggest_position(
        self,
        container_entry_id: int,
        zone_preference: str = None
    ) -> dict:
        """
        Auto-suggest optimal position for a container.

        Algorithm:
        1. Prefer specified zone, otherwise find least occupied
        2. Prefer tier 1 (ground level) for stability
        3. Fill rows/bays sequentially for compactness
        4. Validate stacking rules (support below)
        """

    def assign_position(
        self,
        container_entry_id: int,
        zone: str,
        row: int,
        bay: int,
        tier: int,
        auto_assigned: bool = False
    ) -> ContainerPosition:
        """
        Assign container to specific position.

        Validations:
        - Position not already occupied
        - Tier > 1 requires support below
        - Max tier = 4
        - Container not already placed
        """

    def move_container(
        self,
        position_id: int,
        new_zone: str,
        new_row: int,
        new_bay: int,
        new_tier: int
    ) -> ContainerPosition:
        """Move container to new position."""

    def remove_position(self, position_id: int) -> None:
        """Remove container from position (e.g., on exit)."""

    def get_available_positions(
        self,
        zone: str = None,
        tier: int = None
    ) -> list:
        """Get list of available positions with optional filters."""

    def validate_stacking(
        self,
        zone: str,
        row: int,
        bay: int,
        tier: int
    ) -> bool:
        """
        Validate stacking rules:
        - Max 4 tiers
        - Tier > 1 requires container below
        """
```

### Auto-Suggest Algorithm (Simple Greedy)

```python
def _find_optimal_position(
    self,
    zone_preference: str = None
) -> tuple[str, int, int, int]:
    """
    Simple greedy algorithm for position selection.

    Priority:
    1. Specified zone preference (if any)
    2. Zone with most available ground-level slots
    3. Sequential row/bay filling
    4. Lowest available tier
    """
    zones = [zone_preference] if zone_preference else ['A', 'B', 'C', 'D', 'E']

    for zone in zones:
        for row in range(1, 11):
            for bay in range(1, 11):
                for tier in range(1, 5):
                    if self._is_position_available(zone, row, bay, tier):
                        if tier == 1 or self._has_support_below(zone, row, bay, tier):
                            return zone, row, bay, tier

    raise BusinessLogicError("Нет свободных позиций на терминале")
```

---

## Frontend Architecture

### Component Hierarchy

```
ContainerPlacement.vue (Page)
├── PlacementPanel.vue (Controls)
│   ├── Zone filter dropdown
│   ├── Auto-suggest button
│   ├── Position form (manual entry)
│   └── Stats display
│
├── ContainerTable.vue (Existing, modified)
│   ├── Added: Position column
│   ├── Added: "Place" action button
│   └── Added: Row highlighting sync
│
└── TerminalLayout3D.vue (3D View)
    ├── Three.js Scene
    ├── Zone grid rendering
    ├── Container meshes (InstancedMesh)
    ├── Camera controls (OrbitControls)
    └── Click/hover interactions
```

### TypeScript Types

```typescript
// frontend/src/types/placement.ts

export interface Position {
  zone: 'A' | 'B' | 'C' | 'D' | 'E';
  row: number;  // 1-10
  bay: number;  // 1-10
  tier: number; // 1-4
  coordinate?: string; // "A-R03-B15-T2"
}

export interface ContainerPlacement {
  id: number;
  container_entry: number;
  container_number: string;
  iso_type: string;
  status: 'LADEN' | 'EMPTY';
  position: Position;
  entry_time: string;
  dwell_time_days: number;
  company_name: string;
}

export interface PlacementLayout {
  zones: string[];
  dimensions: {
    max_rows: number;
    max_bays: number;
    max_tiers: number;
  };
  containers: ContainerPlacement[];
  stats: {
    total_capacity: number;
    occupied: number;
    available: number;
    by_zone: Record<string, { occupied: number; available: number }>;
  };
}

export interface SuggestionResponse {
  success: boolean;
  suggested_position: Position;
  reason: string;
  alternatives: Position[];
}
```

### Composables

#### use3DScene.ts
```typescript
// Three.js scene setup, camera, renderer, lighting
export function use3DScene(canvasRef: Ref<HTMLCanvasElement | undefined>) {
  const scene = shallowRef<THREE.Scene>();
  const camera = shallowRef<THREE.OrthographicCamera>();
  const renderer = shallowRef<THREE.WebGLRenderer>();

  function initScene() { /* Setup scene, camera, lights, grid */ }
  function animate() { /* Render loop */ }
  function dispose() { /* Cleanup */ }

  return { scene, camera, renderer, initScene, animate, dispose };
}
```

#### useContainerMesh.ts
```typescript
// Container rendering with InstancedMesh for performance
export function useContainerMesh(scene: Ref<THREE.Scene | undefined>) {
  const ladenMesh = shallowRef<THREE.InstancedMesh>();
  const emptyMesh = shallowRef<THREE.InstancedMesh>();

  function updateContainers(containers: ContainerPlacement[]) {
    // Update instance matrices based on positions
  }

  function highlightContainer(id: number) {
    // Change color for selected container
  }

  return { updateContainers, highlightContainer };
}
```

#### usePlacementState.ts
```typescript
// Shared state for table ↔ 3D synchronization
export function usePlacementState() {
  const selectedContainerId = ref<number | null>(null);
  const hoveredContainerId = ref<number | null>(null);
  const layout = ref<PlacementLayout | null>(null);
  const loading = ref(false);

  async function fetchLayout() { /* API call */ }
  async function suggestPosition(entryId: number) { /* API call */ }
  async function assignPosition(entryId: number, pos: Position) { /* API call */ }

  return {
    selectedContainerId,
    hoveredContainerId,
    layout,
    loading,
    fetchLayout,
    suggestPosition,
    assignPosition
  };
}
```

---

## 3D Rendering Details

### Scene Setup
- **Camera**: OrthographicCamera (bird's-eye view, looking down)
- **Controls**: OrbitControls (pan, zoom, limited rotation)
- **Lighting**: AmbientLight + DirectionalLight for shadows
- **Ground**: GridHelper + Plane for reference

### Container Rendering (InstancedMesh)
```typescript
// Efficient rendering for 2000+ containers
const geometry = new THREE.BoxGeometry(2.4, 2.6, 6.1); // Container dimensions
const ladenMaterial = new THREE.MeshLambertMaterial({ color: 0x52c41a });
const emptyMaterial = new THREE.MeshLambertMaterial({ color: 0x1677ff });

const ladenMesh = new THREE.InstancedMesh(geometry, ladenMaterial, 1000);
const emptyMesh = new THREE.InstancedMesh(geometry, emptyMaterial, 1000);

// Update positions via Matrix4
containers.forEach((container, index) => {
  const matrix = new THREE.Matrix4();
  matrix.setPosition(
    container.position.bay * 6.5,      // X: bay spacing
    container.position.tier * 2.7,     // Y: tier height
    container.position.row * 3.0       // Z: row spacing
  );
  mesh.setMatrixAt(index, matrix);
});
```

### Zone Layout (Spatial)
```
Zone Layout (Top View):
┌─────────────────────────────────────────────────────────┐
│                                                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                    │
│  │ Zone A  │ │ Zone B  │ │ Zone C  │                    │
│  │ 10×10×4 │ │ 10×10×4 │ │ 10×10×4 │                    │
│  └─────────┘ └─────────┘ └─────────┘                    │
│                                                          │
│  ┌─────────┐ ┌─────────┐                                │
│  │ Zone D  │ │ Zone E  │                                │
│  │ 10×10×4 │ │ 10×10×4 │                                │
│  └─────────┘ └─────────┘                                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Click Detection (Raycasting)
```typescript
function onCanvasClick(event: MouseEvent) {
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();

  // Convert screen to normalized device coordinates
  mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects([ladenMesh, emptyMesh]);

  if (intersects.length > 0) {
    const instanceId = intersects[0].instanceId;
    const container = containers[instanceId];
    emit('container-clicked', container);
  }
}
```

---

## File List

### Backend Files

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `backend/apps/terminal_operations/models.py` | MODIFY | Add ContainerPosition model (~60 lines) |
| 2 | `backend/apps/terminal_operations/migrations/XXXX_add_container_position.py` | CREATE | Database migration |
| 3 | `backend/apps/terminal_operations/services/placement_service.py` | CREATE | Placement business logic (~250 lines) |
| 4 | `backend/apps/terminal_operations/serializers.py` | MODIFY | Add position serializers (~50 lines) |
| 5 | `backend/apps/terminal_operations/views.py` | MODIFY | Add PlacementViewSet (~150 lines) |
| 6 | `backend/apps/terminal_operations/urls.py` | MODIFY | Register placement routes (~10 lines) |
| 7 | `backend/tests/terminal_operations/test_placement_service.py` | CREATE | Unit tests (~100 lines) |

### Frontend Files

| # | File | Action | Description |
|---|------|--------|-------------|
| 8 | `frontend/package.json` | MODIFY | Add `three` and `@types/three` dependencies |
| 9 | `frontend/src/types/placement.ts` | CREATE | TypeScript interfaces (~60 lines) |
| 10 | `frontend/src/services/placementService.ts` | CREATE | API client (~80 lines) |
| 11 | `frontend/src/composables/use3DScene.ts` | CREATE | Three.js scene setup (~120 lines) |
| 12 | `frontend/src/composables/useContainerMesh.ts` | CREATE | Container rendering (~100 lines) |
| 13 | `frontend/src/composables/usePlacementState.ts` | CREATE | Shared state (~80 lines) |
| 14 | `frontend/src/components/TerminalLayout3D.vue` | CREATE | 3D view component (~300 lines) |
| 15 | `frontend/src/components/PlacementPanel.vue` | CREATE | Control panel (~150 lines) |
| 16 | `frontend/src/views/ContainerPlacement.vue` | CREATE | Page component (~200 lines) |
| 17 | `frontend/src/router/index.ts` | MODIFY | Add `/placement` route |
| 18 | `frontend/src/components/AppLayout.vue` | MODIFY | Add menu item |

**Total: 18 files (7 backend, 11 frontend)**

---

## Implementation Phases

### Phase 1: Backend Foundation (2-3 hours)
1. Add ContainerPosition model
2. Create and run migration
3. Create PlacementService with core methods
4. Add serializers
5. Test model/service in Django shell

### Phase 2: Backend API (2-3 hours)
6. Create PlacementViewSet
7. Register URL routes
8. Test endpoints via `/api/docs/`
9. Write unit tests

### Phase 3: Frontend Foundation (1-2 hours)
10. Install Three.js dependency
11. Create TypeScript types
12. Create placementService API client
13. Create usePlacementState composable

### Phase 4: 3D Rendering (3-4 hours)
14. Create use3DScene composable
15. Create useContainerMesh composable
16. Create TerminalLayout3D.vue component
17. Implement zone grid rendering
18. Implement container rendering
19. Add camera controls
20. Add click/hover interactions

### Phase 5: Integration (2-3 hours)
21. Create PlacementPanel.vue
22. Create ContainerPlacement.vue page
23. Add route and menu item
24. Wire up table ↔ 3D synchronization
25. Add position column to existing table

### Phase 6: Testing & Polish (1-2 hours)
26. Test with sample data
27. Test auto-suggest workflow
28. Test manual placement
29. Performance check with many containers
30. Error handling and loading states

---

## Stacking Rules

### Basic Rules (Implemented)
1. **Max height**: 4 tiers maximum
2. **Support required**: Tier > 1 must have container directly below
3. **No overhangs**: Container must be fully supported

### Advanced Rules (Future Enhancement)
- Heavy (laden) below light (empty)
- Same-company containers grouped
- Reefer containers in specific zones
- Hazmat separation

---

## Error Handling

### Backend Errors
| Error | Code | Message |
|-------|------|---------|
| Position occupied | `POSITION_OCCUPIED` | "Эта позиция уже занята" |
| No support below | `NO_SUPPORT` | "Нет контейнера ниже для поддержки" |
| Max tier exceeded | `MAX_TIER` | "Максимум 4 яруса" |
| Container already placed | `ALREADY_PLACED` | "Контейнер уже размещён" |
| No available positions | `NO_POSITIONS` | "Нет свободных позиций" |

### Frontend Error Display
- Toast messages via `message.error()`
- Inline form validation
- 3D highlight for conflicts

---

## Performance Considerations

### Backend
- Index on `(zone, row, bay, tier)` for fast lookups
- `select_related('container_entry')` for efficient queries
- Bulk operations for stats calculations

### Frontend
- InstancedMesh for rendering (1 draw call for all containers)
- Throttled raycasting on mouse move
- Lazy loading of 3D view (code-split)
- WebGL context management (dispose on unmount)

---

## Testing Checklist

### Backend Tests
- [ ] Create position - success
- [ ] Create position - duplicate fails
- [ ] Create position - no support fails (tier > 1)
- [ ] Suggest position - finds available
- [ ] Suggest position - no positions error
- [ ] Move position - success
- [ ] Remove position - success
- [ ] Layout endpoint - returns all zones
- [ ] Available endpoint - filters correctly

### Frontend Tests
- [ ] 3D scene initializes
- [ ] Containers render in correct positions
- [ ] Camera controls work (zoom, pan)
- [ ] Click selects container
- [ ] Hover shows tooltip
- [ ] Table ↔ 3D sync works
- [ ] Auto-suggest workflow
- [ ] Manual placement workflow

### E2E Tests
- [ ] Full placement flow: suggest → confirm
- [ ] Container exit removes position
- [ ] Refresh maintains state

---

## Approval Required

Please review this plan and confirm:

1. **Database schema** - ContainerPosition model structure
2. **API endpoints** - Routes and response formats
3. **3D rendering** - Zone layout and colors
4. **Implementation phases** - Order of development

Once approved, I will begin implementation starting with Phase 1 (Backend Foundation).

---

## Questions for Clarification

If any of the following need adjustment, please let me know:

1. **Zone arrangement**: Are A-B-C in one row and D-E in another row acceptable?
2. **Container dimensions**: Standard 20ft (6.1m × 2.4m × 2.6m) for all?
3. **Initial camera position**: Bird's-eye directly above center?
4. **Auto-suggest zone preference**: Should it prefer alphabetically (A first) or by occupancy?
