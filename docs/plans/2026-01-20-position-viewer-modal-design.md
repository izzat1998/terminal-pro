# Position Viewer Modal - Design Document

**Date:** 2026-01-20
**Feature:** Reusable Position Viewer with 2D/3D Toggle

## Overview

A reusable modal component that shows container positions with two viewing modes:
- **2D View**: Existing grid diagram (ContainerLocationView)
- **3D View**: New focused 3D scene showing only nearby containers

### Problem
Currently, clicking a position in Work Orders navigates to the full placement page, which:
- Loads the entire yard (100-500+ containers)
- Takes user away from their current context
- Is overkill for a quick "where is this?" check

### Solution
A modal with a focused 3D view showing only containers within ±2 rows/bays of the target position.

## User Flow

1. User views Work Orders table (or any page with position links)
2. Clicks the location button (📍) on a row
3. Modal opens with tabs: `[2D]` `[3D]`
4. **2D Tab**: Shows existing grid diagram
5. **3D Tab**: Shows focused 3D view with:
   - 5×5 grid around target (±2 rows, ±2 bays)
   - All 4 tiers visible
   - Target highlighted in **pulsing orange**
   - Camera controls (rotate, zoom, pan)
6. User inspects, then closes modal

## Design Decisions

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Nearby range | 5×5 (±2 rows/bays) | Balanced context without overwhelming |
| Tiers | All 4 | Full vertical context for stacking |
| Interactions | View + camera controls | Allows inspection from any angle |
| Target highlight | Pulsing orange | Draws attention without being distracting |
| Data fetching | Client-side filtering | Data already available, no backend changes |
| Reusability | Universal component | Can replace all position viewers in app |

## Component Architecture

```
frontend/src/components/
├── PositionViewerModal.vue      # Modal wrapper with 2D/3D tabs
├── PositionViewer3D.vue         # New focused 3D view
└── ContainerLocationView.vue    # Existing 2D view (no changes)

frontend/src/composables/
└── useMini3DScene.ts            # Simplified Three.js setup for modal
```

### Component Hierarchy

```
PositionViewerModal
├── Tab: "2D"
│   └── ContainerLocationView (existing)
└── Tab: "3D"
    └── PositionViewer3D (new)
```

### Props Interface

```typescript
interface PositionViewerModalProps {
  open: boolean;
  coordinate: string;        // "A-R03-B05-T2-A"
  containerNumber?: string;  // "HDMU6565958" (optional)
  isoType?: string;          // "45G1" (optional)
  status?: 'LADEN' | 'EMPTY';
  defaultMode?: '2d' | '3d'; // Default: '2d'
}
```

## 3D Scene Configuration

### Differences from Full TerminalLayout3D

| Aspect | Full View | Focused View |
|--------|-----------|--------------|
| Containers | All (100-500+) | Nearby only (~25-50) |
| Grid size | 10×10 | 5×5 centered on target |
| Ground labels | All R1-R10, B1-B10 | Only visible range |
| Legend | Full | None |
| Controls overlay | Labels, heatmap, presets | None |
| Canvas size | Large (fills page) | Medium (~600×400px) |

### Camera Setup

- **Default**: Isometric view, auto-centered on target
- **Zoom**: Closer than full view (containers appear larger)
- **Controls**: OrbitControls (rotate, zoom, pan)

### Target Highlighting

```
Color: Orange (#fa8c16)
Effect: Pulsing emissive glow
Animation: 0.3 → 0.8 → 0.3 intensity over ~1.5s (sine wave)
```

Other containers use normal status colors (green=laden, blue=empty).

## Data Flow

```
PositionViewerModal (receives coordinate)
       │
       ▼
PositionViewer3D
       │
       ├── Parse coordinate → extract zone, row, bay, tier
       │
       ├── Fetch containers via placementService
       │
       ├── Filter: |container.row - targetRow| <= 2
       │          |container.bay - targetBay| <= 2
       │
       └── Render filtered containers in mini 3D scene
```

### Coordinate Parsing

```typescript
// Input: "A-R03-B05-T2-A"
// Output: { zone: 'A', row: 3, bay: 5, tier: 2, subSlot: 'A' }
const match = coordinate.match(/^([A-E])-R(\d{2})-B(\d{2})-T(\d)-([AB])$/);
```

### Filtering Logic

```typescript
function filterNearbyContainers(
  containers: ContainerPlacement[],
  targetRow: number,
  targetBay: number,
  range: number = 2
): ContainerPlacement[] {
  return containers.filter(c =>
    Math.abs(c.position.row - targetRow) <= range &&
    Math.abs(c.position.bay - targetBay) <= range
  );
}
```

## Files to Create

| File | Lines (est.) | Purpose |
|------|--------------|---------|
| `components/PositionViewerModal.vue` | ~100 | Modal with tabs |
| `components/PositionViewer3D.vue` | ~200 | Mini 3D canvas |
| `composables/useMini3DScene.ts` | ~150 | Simplified Three.js |

## Files to Modify

| File | Change |
|------|--------|
| `views/WorkOrdersPage.vue` | Replace navigation with modal |
| `components/Container3DModal.vue` | Deprecate (replaced by new modal) |

## Implementation Order

1. `useMini3DScene.ts` - Simplified Three.js setup
2. `PositionViewer3D.vue` - Mini 3D canvas with filtering + pulsing highlight
3. `PositionViewerModal.vue` - Tabs wrapper combining 2D and 3D
4. Update `WorkOrdersPage.vue` - Use new modal instead of navigation
5. Replace other `Container3DModal` usages across the app

## Usage Example

```vue
<template>
  <PositionViewerModal
    v-model:open="showPositionModal"
    :coordinate="selectedPosition"
    :container-number="selectedContainer"
    default-mode="3d"
  />
</template>

<script setup lang="ts">
const showPositionModal = ref(false);
const selectedPosition = ref('A-R03-B05-T2-A');
const selectedContainer = ref('HDMU6565958');

function handlePositionClick(coordinate: string, containerNumber: string) {
  selectedPosition.value = coordinate;
  selectedContainer.value = containerNumber;
  showPositionModal.value = true;
}
</script>
```

## Future Enhancements (Out of Scope)

- Add "Open full view" button for edge cases
- Remember user's preferred mode (2D/3D) in localStorage
- Show empty positions as ghost outlines
- Add mini-legend for status colors
