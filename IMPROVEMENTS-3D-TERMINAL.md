# 3D Terminal Placement - Professional Improvements Plan

## Executive Summary

This document outlines essential improvements to elevate the current 3D container placement visualization to **professional terminal operating system (TOS) standards**. The recommendations are based on industry best practices from systems like NAVIS N4, Tideworks Spinnaker, and Cosmos TOS.

**Current State**: Functional MVP with basic 3D visualization, placement workflow, and bi-directional sync.

**Target State**: Professional-grade yard management system with real-time operations, advanced algorithms, and enterprise features.

---

## Priority Matrix

| Priority | Category | Impact | Effort |
|----------|----------|--------|--------|
| 🔴 Critical | Performance & Stability | High | Medium |
| 🟠 High | Visual Enhancements | High | Medium |
| 🟡 Medium | Business Logic | Medium | High |
| 🟢 Low | Nice-to-Have | Low | Low |

---

## 🔴 CRITICAL IMPROVEMENTS

### 1. Performance Optimization for Scale

**Current Issue**: InstancedMesh limited to 300 instances, but terminal capacity is 2000.

```typescript
// CURRENT (use3DScene.ts)
const ladenMesh = new THREE.InstancedMesh(geometry, material, 300);

// IMPROVED
const MAX_CONTAINERS = 2500; // Buffer for peak capacity
const ladenMesh = new THREE.InstancedMesh(geometry, material, MAX_CONTAINERS);
```

**Improvements Required**:

| # | Improvement | File | Description |
|---|------------|------|-------------|
| 1.1 | Increase instance count | `useContainerMesh.ts` | Set to 2500 per mesh type (8 meshes × 2500 = 20K instances) |
| 1.2 | Frustum culling | `use3DScene.ts` | Only render visible containers |
| 1.3 | Level of Detail (LOD) | `useContainerMesh.ts` | Simplified geometry at distance |
| 1.4 | Spatial indexing | `usePlacementState.ts` | Octree for fast spatial queries |
| 1.5 | WebWorker for matrix calc | New file | Offload heavy computation |

**Code Example - LOD Implementation**:
```typescript
// useContainerMesh.ts - Add LOD support
function createContainerLOD(): THREE.LOD {
  const lod = new THREE.LOD();

  // High detail (close)
  const highDetail = new THREE.Mesh(
    new THREE.BoxGeometry(2.4, 2.6, 6.1),
    new THREE.MeshStandardMaterial({ color: 0x52c41a })
  );
  lod.addLevel(highDetail, 0);

  // Medium detail (mid distance)
  const midDetail = new THREE.Mesh(
    new THREE.BoxGeometry(2.4, 2.6, 6.1),
    new THREE.MeshLambertMaterial({ color: 0x52c41a })
  );
  lod.addLevel(midDetail, 50);

  // Low detail (far) - simple box
  const lowDetail = new THREE.Mesh(
    new THREE.BoxGeometry(2.4, 2.6, 6.1),
    new THREE.MeshBasicMaterial({ color: 0x52c41a })
  );
  lod.addLevel(lowDetail, 100);

  return lod;
}
```

---

### 2. Real-Time Data Synchronization

**Current Issue**: Manual refresh required; no live updates.

**Solution**: WebSocket integration for real-time yard state.

```
┌─────────────┐     WebSocket      ┌──────────────┐
│  Frontend   │◄──────────────────►│   Backend    │
│  3D View    │   /ws/placement/   │  Django Ch.  │
└─────────────┘                    └──────────────┘
```

**Implementation**:

| # | Task | File | Description |
|---|------|------|-------------|
| 2.1 | WebSocket consumer | `backend/consumers.py` | Django Channels consumer |
| 2.2 | WebSocket service | `frontend/services/wsService.ts` | Connection manager |
| 2.3 | Real-time hooks | `usePlacementState.ts` | Auto-update on events |
| 2.4 | Optimistic UI | `usePlacementState.ts` | Immediate visual feedback |
| 2.5 | Conflict resolution | Backend + Frontend | Handle concurrent edits |

**Events to Broadcast**:
```typescript
type PlacementEvent =
  | { type: 'CONTAINER_PLACED'; data: ContainerPlacement }
  | { type: 'CONTAINER_MOVED'; data: { from: Position; to: Position; container_id: number } }
  | { type: 'CONTAINER_REMOVED'; data: { position: Position; container_id: number } }
  | { type: 'CONTAINER_ENTERED'; data: UnplacedContainer }
  | { type: 'CONTAINER_EXITED'; data: { container_id: number } };
```

---

### 3. Stacking Rule Engine

**Current Issue**: Only basic tier support validation (container below required).

**Professional Requirements**:

| Rule | Description | Priority |
|------|-------------|----------|
| Weight Distribution | Heavy containers (Laden) below light (Empty) | 🔴 Critical |
| Size Compatibility | Same or smaller container on top | 🔴 Critical |
| Hazmat Segregation | Dangerous goods in dedicated zones | 🟠 High |
| Reefer Proximity | Reefer containers near power points | 🟠 High |
| Departure Time | LIFO - Later departures below | 🟡 Medium |
| Company Grouping | Same owner containers together | 🟢 Low |

**Backend Enhancement**:
```python
# placement_service.py - Enhanced stacking rules

class StackingRuleEngine:
    """Professional stacking rule validation."""

    def validate_placement(
        self,
        container: ContainerEntry,
        position: Position,
        containers_below: list[ContainerEntry]
    ) -> tuple[bool, list[str]]:
        """
        Validate all stacking rules.
        Returns (is_valid, list_of_violations).
        """
        violations = []

        # Rule 1: Support required
        if position.tier > 1 and not containers_below:
            violations.append("NO_SUPPORT: Tier > 1 requires container below")

        # Rule 2: Weight distribution (Laden below Empty)
        if containers_below:
            top_is_laden = container.status == 'LADEN'
            bottom_is_empty = any(c.status == 'EMPTY' for c in containers_below)
            if top_is_laden and bottom_is_empty:
                violations.append("WEIGHT_VIOLATION: Laden container cannot stack on empty")

        # Rule 3: Size compatibility
        if containers_below:
            container_size = self._get_container_size(container.container.iso_type)
            for below in containers_below:
                below_size = self._get_container_size(below.container.iso_type)
                if container_size > below_size:
                    violations.append(f"SIZE_VIOLATION: {container_size}ft cannot stack on {below_size}ft")

        # Rule 4: Hazmat segregation
        if self._is_hazmat(container) and not self._is_hazmat_zone(position.zone):
            violations.append("HAZMAT_VIOLATION: Dangerous goods must be in zone E")

        return len(violations) == 0, violations

    def _get_container_size(self, iso_type: str) -> int:
        """Extract size from ISO type (20, 40, or 45)."""
        if iso_type.startswith('2'):
            return 20
        elif iso_type.startswith('4'):
            return 40 if iso_type[1] != '5' else 45
        return 20
```

---

### 4. Error Handling & Recovery

**Current Issue**: Basic error toasts; no recovery mechanisms.

**Improvements**:

| # | Feature | Description |
|---|---------|-------------|
| 4.1 | Retry logic | Auto-retry failed API calls with exponential backoff |
| 4.2 | Offline queue | Queue operations when offline, sync on reconnect |
| 4.3 | Conflict resolution UI | Modal showing conflicting changes with merge options |
| 4.4 | Undo/Redo | Transaction history with undo capability |
| 4.5 | Audit log | Track all placement operations with user/timestamp |

**Frontend Error Handling**:
```typescript
// services/placementService.ts - Enhanced error handling

class PlacementServiceError extends Error {
  constructor(
    public code: string,
    public message: string,
    public details?: unknown,
    public recoverable: boolean = false
  ) {
    super(message);
  }
}

async function assignPositionWithRetry(
  entryId: number,
  position: Position,
  maxRetries = 3
): Promise<ContainerPositionRecord> {
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await assignPosition(entryId, position);
    } catch (error) {
      lastError = error as Error;

      if (error instanceof PlacementServiceError) {
        // Don't retry business logic errors
        if (!error.recoverable) throw error;
      }

      // Exponential backoff
      await new Promise(resolve =>
        setTimeout(resolve, Math.pow(2, attempt) * 1000)
      );
    }
  }

  throw lastError;
}
```

---

## 🟠 HIGH PRIORITY IMPROVEMENTS

### 5. Enhanced Visual Representation

**Current State**: Basic colored boxes with status differentiation.

**Professional Enhancements**:

| # | Feature | Description | Visual |
|---|---------|-------------|--------|
| 5.1 | Container labels | Show container number on mesh | Text sprite |
| 5.2 | Size differentiation | Accurate 20ft/40ft/45ft dimensions | Geometry |
| 5.3 | Status indicators | Icons for Reefer, Hazmat, OOG | Decals |
| 5.4 | Dwell time heatmap | Color gradient by days in yard | Heat colors |
| 5.5 | Zone boundaries | Clear visual zone separators | Lines/fences |
| 5.6 | Truck lanes | Animated paths for traffic | Dashed lines |
| 5.7 | Equipment | RTG cranes, reach stackers | 3D models |

**Dwell Time Heatmap Implementation**:
```typescript
// useContainerMesh.ts - Dwell time color coding

function getDwellTimeColor(days: number): THREE.Color {
  // Professional terminal color scheme
  if (days <= 3) return new THREE.Color(0x52c41a);  // Green - Fresh
  if (days <= 7) return new THREE.Color(0xfaad14);  // Yellow - Normal
  if (days <= 14) return new THREE.Color(0xfa8c16); // Orange - Aging
  if (days <= 21) return new THREE.Color(0xf5222d); // Red - Overdue
  return new THREE.Color(0x722ed1);                  // Purple - Critical
}

function updateContainerColors(
  containers: ContainerPlacement[],
  colorMode: 'status' | 'dwell_time' | 'company'
) {
  containers.forEach((container, index) => {
    let color: THREE.Color;

    switch (colorMode) {
      case 'status':
        color = container.status === 'LADEN'
          ? new THREE.Color(0x52c41a)
          : new THREE.Color(0x1677ff);
        break;
      case 'dwell_time':
        color = getDwellTimeColor(container.dwell_time_days);
        break;
      case 'company':
        color = getCompanyColor(container.company_name);
        break;
    }

    mesh.setColorAt(index, color);
  });
  mesh.instanceColor!.needsUpdate = true;
}
```

**Container Label Sprites**:
```typescript
// useContainerMesh.ts - Add container number labels

function createContainerLabel(containerNumber: string): THREE.Sprite {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext('2d')!;

  // Background
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  ctx.roundRect(0, 0, 256, 64, 8);
  ctx.fill();

  // Text
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 24px JetBrains Mono';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(containerNumber, 128, 32);

  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(4, 1, 1);

  return sprite;
}
```

---

### 6. Advanced Auto-Suggest Algorithm

**Current State**: Simple greedy algorithm (sequential fill).

**Professional Algorithm Requirements**:

| Factor | Weight | Description |
|--------|--------|-------------|
| Zone preference | 30% | Match requested zone |
| Departure time | 25% | LIFO stacking (later departures below) |
| Company grouping | 15% | Keep same-owner containers together |
| Equipment path | 15% | Minimize crane/stacker travel |
| Weight balance | 10% | Distribute weight across tiers |
| Reefer proximity | 5% | Near power points |

**Weighted Scoring Algorithm**:
```python
# placement_service.py - Professional suggestion algorithm

class PlacementSuggestionEngine:
    """Multi-factor weighted position suggestion."""

    WEIGHTS = {
        'zone_preference': 0.30,
        'departure_optimization': 0.25,
        'company_grouping': 0.15,
        'equipment_path': 0.15,
        'weight_balance': 0.10,
        'reefer_proximity': 0.05,
    }

    def suggest_position(
        self,
        container: ContainerEntry,
        zone_preference: str | None = None,
        optimization_mode: str = 'balanced'
    ) -> SuggestionResult:
        """
        Score all available positions and return the best one.
        """
        available = self._get_available_positions()
        scored_positions = []

        for position in available:
            score = self._calculate_position_score(
                container, position, zone_preference
            )
            scored_positions.append((position, score))

        # Sort by score (descending)
        scored_positions.sort(key=lambda x: x[1], reverse=True)

        best = scored_positions[0]
        alternatives = [p for p, _ in scored_positions[1:4]]

        return SuggestionResult(
            position=best[0],
            score=best[1],
            reason=self._build_reason(container, best[0]),
            alternatives=alternatives
        )

    def _calculate_position_score(
        self,
        container: ContainerEntry,
        position: Position,
        zone_preference: str | None
    ) -> float:
        """Calculate weighted score for a position."""
        scores = {}

        # Zone preference (1.0 if matches, 0.5 if adjacent, 0.0 otherwise)
        if zone_preference:
            if position.zone == zone_preference:
                scores['zone_preference'] = 1.0
            elif self._zones_adjacent(position.zone, zone_preference):
                scores['zone_preference'] = 0.5
            else:
                scores['zone_preference'] = 0.0
        else:
            scores['zone_preference'] = 0.5  # Neutral

        # Departure optimization (LIFO)
        scores['departure_optimization'] = self._score_departure(
            container, position
        )

        # Company grouping
        scores['company_grouping'] = self._score_company_proximity(
            container.company_id, position
        )

        # Equipment path (prefer sequential fills)
        scores['equipment_path'] = self._score_equipment_path(position)

        # Weight balance
        scores['weight_balance'] = self._score_weight_balance(
            container.status, position
        )

        # Reefer proximity
        if self._is_reefer(container):
            scores['reefer_proximity'] = self._score_reefer_proximity(position)
        else:
            scores['reefer_proximity'] = 0.5  # Neutral

        # Calculate weighted sum
        total = sum(
            scores[factor] * weight
            for factor, weight in self.WEIGHTS.items()
        )

        return total
```

---

### 7. Interactive Placement Mode

**Current State**: Click to select, then use panel to place.

**Professional UX**:

| Feature | Description |
|---------|-------------|
| Drag & Drop | Drag container from list to 3D position |
| Ghost preview | Show semi-transparent container at cursor |
| Valid/invalid feedback | Green glow for valid, red for invalid positions |
| Snap to grid | Auto-snap to nearest valid position |
| Multi-select | Select and move multiple containers |
| Quick actions | Right-click context menu |

**Implementation**:
```typescript
// usePlacementDragDrop.ts - Drag and drop placement

export function usePlacementDragDrop(
  scene: Ref<THREE.Scene | undefined>,
  camera: Ref<THREE.Camera | undefined>,
  canvas: Ref<HTMLCanvasElement | undefined>
) {
  const isDragging = ref(false);
  const draggedContainer = ref<UnplacedContainer | null>(null);
  const ghostMesh = shallowRef<THREE.Mesh | null>(null);
  const previewPosition = ref<Position | null>(null);
  const isValidPosition = ref(false);

  function startDrag(container: UnplacedContainer) {
    isDragging.value = true;
    draggedContainer.value = container;

    // Create ghost mesh
    const size = getContainerSize(container.iso_type);
    const geometry = new THREE.BoxGeometry(size.width, size.height, size.length);
    const material = new THREE.MeshBasicMaterial({
      color: 0x52c41a,
      transparent: true,
      opacity: 0.5,
    });
    ghostMesh.value = new THREE.Mesh(geometry, material);
    scene.value?.add(ghostMesh.value);
  }

  function onMouseMove(event: MouseEvent) {
    if (!isDragging.value || !ghostMesh.value) return;

    const position = screenToYardPosition(event, camera.value!, canvas.value!);
    if (!position) return;

    // Snap to grid
    const snapped = snapToGrid(position);
    previewPosition.value = snapped;

    // Update ghost position
    const worldPos = positionToWorld(snapped);
    ghostMesh.value.position.copy(worldPos);

    // Validate and update color
    isValidPosition.value = validatePosition(snapped, draggedContainer.value!);
    ghostMesh.value.material.color.setHex(
      isValidPosition.value ? 0x52c41a : 0xf5222d
    );
  }

  function endDrag() {
    if (isValidPosition.value && previewPosition.value && draggedContainer.value) {
      confirmPlacement(draggedContainer.value.id, previewPosition.value);
    }

    // Cleanup
    if (ghostMesh.value) {
      scene.value?.remove(ghostMesh.value);
      ghostMesh.value.geometry.dispose();
      (ghostMesh.value.material as THREE.Material).dispose();
      ghostMesh.value = null;
    }

    isDragging.value = false;
    draggedContainer.value = null;
    previewPosition.value = null;
  }

  return {
    isDragging,
    previewPosition,
    isValidPosition,
    startDrag,
    endDrag,
  };
}
```

---

### 8. Camera Presets & Navigation

**Current State**: Free orbit controls only.

**Professional Features**:

| Preset | View | Use Case |
|--------|------|----------|
| Bird's Eye | Top-down orthographic | Overview |
| Zone Focus | Zoom to specific zone | Zone operations |
| Container Focus | Zoom to specific container | Container details |
| 3D Perspective | Angled view | Depth perception |
| Section View | Cross-section slice | Tier inspection |

**Implementation**:
```typescript
// use3DScene.ts - Camera presets

interface CameraPreset {
  position: THREE.Vector3;
  target: THREE.Vector3;
  zoom?: number;
  fov?: number;
}

const CAMERA_PRESETS: Record<string, CameraPreset> = {
  overview: {
    position: new THREE.Vector3(0, 200, 0),
    target: new THREE.Vector3(0, 0, 0),
    zoom: 1,
  },
  zoneA: {
    position: new THREE.Vector3(-50, 80, 50),
    target: new THREE.Vector3(-50, 0, 50),
    zoom: 2,
  },
  zoneB: {
    position: new THREE.Vector3(0, 80, 50),
    target: new THREE.Vector3(0, 0, 50),
    zoom: 2,
  },
  perspective3D: {
    position: new THREE.Vector3(100, 80, 100),
    target: new THREE.Vector3(0, 0, 0),
    fov: 50,
  },
};

function animateCameraToPreset(preset: keyof typeof CAMERA_PRESETS) {
  const { position, target, zoom } = CAMERA_PRESETS[preset];

  // Smooth animation using GSAP or manual interpolation
  gsap.to(camera.value!.position, {
    x: position.x,
    y: position.y,
    z: position.z,
    duration: 1,
    ease: 'power2.inOut',
  });

  gsap.to(controls.value!.target, {
    x: target.x,
    y: target.y,
    z: target.z,
    duration: 1,
    ease: 'power2.inOut',
  });

  if (zoom && camera.value instanceof THREE.OrthographicCamera) {
    gsap.to(camera.value, {
      zoom,
      duration: 1,
      onUpdate: () => camera.value!.updateProjectionMatrix(),
    });
  }
}

function focusOnContainer(containerId: number) {
  const container = layout.value?.containers.find(c => c.id === containerId);
  if (!container) return;

  const worldPos = positionToWorld(container.position);
  animateCameraToPreset({
    position: new THREE.Vector3(worldPos.x + 20, 40, worldPos.z + 20),
    target: worldPos,
    zoom: 3,
  });
}
```

---

## 🟡 MEDIUM PRIORITY IMPROVEMENTS

### 9. Search & Filter System

**Features**:

| Filter | Description |
|--------|-------------|
| Container number | Partial match search |
| Company | Filter by owner |
| Status | Laden/Empty toggle |
| Dwell time | Range filter (>7 days) |
| Zone | Zone selection |
| ISO type | Size/type filter |
| Entry date | Date range |

**Visual Feedback**:
```typescript
// usePlacementState.ts - Filter system

interface PlacementFilters {
  search: string;
  companies: string[];
  statuses: ('LADEN' | 'EMPTY')[];
  dwellTimeMin?: number;
  dwellTimeMax?: number;
  zones: ZoneCode[];
  isoTypes: string[];
  entryDateFrom?: Date;
  entryDateTo?: Date;
}

const filters = ref<PlacementFilters>({
  search: '',
  companies: [],
  statuses: [],
  zones: [],
  isoTypes: [],
});

const filteredContainers = computed(() => {
  if (!layout.value) return [];

  return layout.value.containers.filter(container => {
    // Search filter
    if (filters.value.search) {
      const search = filters.value.search.toLowerCase();
      if (!container.container_number.toLowerCase().includes(search)) {
        return false;
      }
    }

    // Company filter
    if (filters.value.companies.length > 0) {
      if (!filters.value.companies.includes(container.company_name)) {
        return false;
      }
    }

    // Status filter
    if (filters.value.statuses.length > 0) {
      if (!filters.value.statuses.includes(container.status)) {
        return false;
      }
    }

    // Dwell time filter
    if (filters.value.dwellTimeMin !== undefined) {
      if (container.dwell_time_days < filters.value.dwellTimeMin) {
        return false;
      }
    }

    // Zone filter
    if (filters.value.zones.length > 0) {
      if (!filters.value.zones.includes(container.position.zone)) {
        return false;
      }
    }

    return true;
  });
});

// Dim non-matching containers in 3D view
watch(filteredContainers, (filtered) => {
  const filteredIds = new Set(filtered.map(c => c.id));

  layout.value?.containers.forEach((container, index) => {
    const opacity = filteredIds.has(container.id) ? 1.0 : 0.2;
    updateContainerOpacity(index, opacity);
  });
});
```

---

### 10. Reporting & Analytics Dashboard

**Reports**:

| Report | Description | Format |
|--------|-------------|--------|
| Zone Utilization | Occupancy by zone over time | Chart |
| Dwell Time Analysis | Average dwell by company/type | Chart |
| Placement History | All movements with timestamps | Table |
| Capacity Forecast | Predicted utilization | Chart |
| Stacking Efficiency | Tier distribution analysis | Chart |

**Dashboard Components**:
```vue
<!-- PlacementDashboard.vue -->
<template>
  <div class="placement-dashboard">
    <a-row :gutter="16">
      <!-- Zone Utilization Chart -->
      <a-col :span="12">
        <a-card title="Zone Utilization">
          <ZoneUtilizationChart :data="zoneStats" />
        </a-card>
      </a-col>

      <!-- Dwell Time Distribution -->
      <a-col :span="12">
        <a-card title="Dwell Time Distribution">
          <DwellTimeChart :data="dwellStats" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16" style="margin-top: 16px">
      <!-- Tier Stacking Analysis -->
      <a-col :span="8">
        <a-card title="Tier Distribution">
          <TierDistributionChart :data="tierStats" />
        </a-card>
      </a-col>

      <!-- Company Breakdown -->
      <a-col :span="8">
        <a-card title="By Company">
          <CompanyBreakdownChart :data="companyStats" />
        </a-card>
      </a-col>

      <!-- Daily Movements -->
      <a-col :span="8">
        <a-card title="Daily Movements">
          <MovementsChart :data="movementStats" />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>
```

---

### 11. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Toggle selection mode |
| `Enter` | Confirm placement |
| `Escape` | Cancel operation |
| `1-5` | Focus zone A-E |
| `R` | Reset camera |
| `F` | Focus selected container |
| `G` | Toggle grid |
| `L` | Toggle labels |
| `H` | Toggle heatmap |
| `Ctrl+Z` | Undo last action |
| `Ctrl+F` | Open search |

```typescript
// useKeyboardShortcuts.ts

export function useKeyboardShortcuts() {
  const shortcuts: Record<string, () => void> = {
    'Space': () => toggleSelectionMode(),
    'Enter': () => confirmPlacement(),
    'Escape': () => cancelOperation(),
    'Digit1': () => focusZone('A'),
    'Digit2': () => focusZone('B'),
    'Digit3': () => focusZone('C'),
    'Digit4': () => focusZone('D'),
    'Digit5': () => focusZone('E'),
    'KeyR': () => resetCamera(),
    'KeyF': () => focusSelectedContainer(),
    'KeyG': () => toggleGrid(),
    'KeyL': () => toggleLabels(),
    'KeyH': () => toggleHeatmap(),
  };

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown);
  });

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown);
  });

  function handleKeydown(event: KeyboardEvent) {
    // Ignore if typing in input
    if (event.target instanceof HTMLInputElement) return;

    const handler = shortcuts[event.code];
    if (handler) {
      event.preventDefault();
      handler();
    }

    // Ctrl+Z for undo
    if (event.ctrlKey && event.code === 'KeyZ') {
      event.preventDefault();
      undoLastAction();
    }

    // Ctrl+F for search
    if (event.ctrlKey && event.code === 'KeyF') {
      event.preventDefault();
      openSearch();
    }
  }
}
```

---

### 12. Export & Import

**Export Formats**:

| Format | Use Case |
|--------|----------|
| PNG/JPG | Screenshot of current view |
| PDF | Printable yard plan |
| CSV | Position data for analysis |
| JSON | Full state backup |

**Import Capabilities**:
- Bulk position import from CSV
- Layout templates (predefined arrangements)

```typescript
// useExport.ts

export function useExport(
  renderer: Ref<THREE.WebGLRenderer | undefined>,
  scene: Ref<THREE.Scene | undefined>,
  camera: Ref<THREE.Camera | undefined>
) {
  async function exportScreenshot(format: 'png' | 'jpg' = 'png'): Promise<Blob> {
    if (!renderer.value || !scene.value || !camera.value) {
      throw new Error('Scene not initialized');
    }

    // Render at high resolution
    const originalSize = renderer.value.getSize(new THREE.Vector2());
    renderer.value.setSize(originalSize.x * 2, originalSize.y * 2);
    renderer.value.render(scene.value, camera.value);

    const dataUrl = renderer.value.domElement.toDataURL(`image/${format}`);

    // Restore original size
    renderer.value.setSize(originalSize.x, originalSize.y);

    // Convert to blob
    const response = await fetch(dataUrl);
    return response.blob();
  }

  function exportPositionData(): string {
    const data = layout.value?.containers.map(c => ({
      container_number: c.container_number,
      iso_type: c.iso_type,
      status: c.status,
      zone: c.position.zone,
      row: c.position.row,
      bay: c.position.bay,
      tier: c.position.tier,
      coordinate: c.position.coordinate,
      company: c.company_name,
      dwell_days: c.dwell_time_days,
    }));

    return convertToCSV(data);
  }

  async function exportPDF(): Promise<Blob> {
    // Use jspdf + html2canvas
    const screenshot = await exportScreenshot('png');
    const pdf = new jsPDF('landscape', 'mm', 'a4');

    // Add header
    pdf.setFontSize(18);
    pdf.text('Terminal Yard Layout', 14, 15);
    pdf.setFontSize(10);
    pdf.text(`Generated: ${new Date().toLocaleString()}`, 14, 22);

    // Add screenshot
    const imgData = await blobToBase64(screenshot);
    pdf.addImage(imgData, 'PNG', 14, 30, 270, 150);

    // Add stats
    pdf.setFontSize(12);
    pdf.text(`Total: ${layout.value?.stats.occupied} / ${layout.value?.stats.total_capacity}`, 14, 190);

    return pdf.output('blob');
  }

  return { exportScreenshot, exportPositionData, exportPDF };
}
```

---

## 🟢 LOW PRIORITY (NICE-TO-HAVE)

### 13. Mobile/Tablet Support

- Touch gestures (pinch zoom, pan)
- Simplified UI for smaller screens
- Portrait/landscape layouts
- Progressive Web App (PWA)

### 14. Equipment Visualization

- RTG cranes with movement animation
- Reach stackers
- Trucks in lanes
- Equipment scheduling overlay

### 15. Historical Playback

- Time slider to view past states
- Movement animation replay
- Audit trail visualization

### 16. AR/VR Integration

- WebXR support for VR headsets
- AR overlay on physical terminal (future)

### 17. AI-Powered Predictions

- Demand forecasting
- Optimal stacking predictions
- Anomaly detection

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1)
- [ ] 1.1 Increase InstancedMesh capacity to 2500
- [ ] 1.2 Add frustum culling
- [ ] 3.1 Implement weight distribution rule
- [ ] 3.2 Implement size compatibility rule
- [ ] 4.1 Add retry logic with exponential backoff

### Phase 2: Core Enhancements (Week 2)
- [ ] 2.1-2.3 WebSocket real-time sync
- [ ] 5.1 Container number labels
- [ ] 5.4 Dwell time heatmap
- [ ] 8.1 Camera presets

### Phase 3: Professional UX (Week 3)
- [ ] 6.1 Weighted suggestion algorithm
- [ ] 7.1 Drag & drop placement
- [ ] 7.2 Ghost preview with validation
- [ ] 9.1 Search & filter system
- [ ] 11.1 Keyboard shortcuts

### Phase 4: Analytics & Export (Week 4)
- [ ] 10.1 Zone utilization chart
- [ ] 10.2 Dwell time analysis
- [ ] 12.1 Screenshot export
- [ ] 12.2 PDF export
- [ ] 12.3 CSV export

### Phase 5: Polish & Optimization (Week 5)
- [ ] 1.3 Level of Detail (LOD)
- [ ] 1.5 WebWorker for matrix calculations
- [ ] 4.4 Undo/Redo functionality
- [ ] Testing & bug fixes

---

## Technical Dependencies

### New npm Packages
```json
{
  "gsap": "^3.12.0",        // Camera animations
  "jspdf": "^2.5.1",        // PDF export
  "html2canvas": "^1.4.1",  // Screenshot
  "chart.js": "^4.4.0",     // Analytics charts
  "vue-chartjs": "^5.2.0"   // Vue wrapper for charts
}
```

### Backend Additions
```python
# requirements.txt
channels>=4.0.0           # WebSocket support
channels-redis>=4.1.0     # Redis channel layer
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Max containers rendered | 300 | 2500 |
| Frame rate (60fps target) | ~45fps | 60fps |
| Time to first render | ~2s | <1s |
| Auto-suggest accuracy | Basic | 85%+ |
| User actions per placement | 5+ clicks | 2-3 clicks |
| Real-time sync latency | N/A | <500ms |

---

## Conclusion

This improvement plan transforms the current MVP into a **professional-grade terminal yard management system** comparable to industry leaders. The phased approach ensures:

1. **Immediate stability** with critical performance fixes
2. **Core functionality** with real-time sync and better algorithms
3. **Professional UX** with drag-drop and keyboard shortcuts
4. **Business value** with analytics and export capabilities

Total estimated effort: **5 weeks** for full implementation.

---

*Document Version: 1.0*
*Created: 2026-01-13*
*Author: Claude Code Analysis*
