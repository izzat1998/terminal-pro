# 3D Yard Reference System Design

**Date:** 2026-01-24
**Status:** Approved
**Target:** `frontend/src/views/YardTestView.vue` and related composables

## Problem Statement

When working on the 3D yard visualization, it's difficult to communicate about specific elements:
- Cannot point at objects in the 3D scene
- Cannot always share screenshots
- No shared language to reference buildings, walls, gates, or locations
- Trial-and-error positioning without coordinate feedback

## Solution: Unified Reference System

Three integrated layers that provide a shared language for discussing the 3D yard:

```
┌─────────────────────────────────────────────────────────────────┐
│                 3D YARD REFERENCE SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: GRID OVERLAY                                           │
│  • 20m × 20m real-world cells                                    │
│  • Origin: Top-left (NW corner)                                  │
│  • Labels: A1, B1, C1... (columns A-Z), rows 1-N                │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: NAMED ELEMENTS                                         │
│  • Pattern: {TYPE}-{NAME}-{GRID}                                 │
│  • Examples: BLD-OFFICE-C4, WALL-FENCE-A2-A8, GATE-MAIN-H12     │
│  • Stored in: yardElements.json                                  │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: DEBUG MODE                                             │
│  • Toggle: Press D key or URL ?debug=true                        │
│  • Shows: Grid, element labels, click-to-inspect                 │
│  • Inspector: Expandable panel with coordinates                  │
└─────────────────────────────────────────────────────────────────┘
```

## Design Decisions

### 1. Grid System

| Property | Value | Rationale |
|----------|-------|-----------|
| Cell size | 20m × 20m | Fits ~1.5 containers (40ft=12m), readable labels, ~150 cells total |
| Origin | Top-left (NW) | Map convention: read left→right, top→bottom |
| Columns | A, B, C... Z | Letters for X-axis (left to right) |
| Rows | 1, 2, 3... N | Numbers for Y-axis (top to bottom) |
| Coordinate system | DXF-based | Same as existing containers, buildings |

**Grid Calculation:**
```typescript
// DXF bounds (approximate)
const bounds = { minX: 12900, maxX: 13100, minY: 73250, maxY: 73550 }

// Grid dimensions
const cellSize = 20 // meters
const columns = Math.ceil((bounds.maxX - bounds.minX) / cellSize) // ~10 columns
const rows = Math.ceil((bounds.maxY - bounds.minY) / cellSize)    // ~15 rows

// Convert DXF position to grid cell
function dxfToGrid(x: number, y: number): string {
  const col = Math.floor((x - bounds.minX) / cellSize)
  const row = Math.floor((bounds.maxY - y) / cellSize) // Inverted: top = row 1
  const colLetter = String.fromCharCode(65 + col) // A, B, C...
  return `${colLetter}${row + 1}` // e.g., "C4"
}
```

### 2. Element Naming Convention

**Pattern:** `{TYPE}-{NAME}-{GRID}`

| Type | Prefix | Examples |
|------|--------|----------|
| Buildings | `BLD-` | `BLD-OFFICE-C4`, `BLD-WAREHOUSE-E6` |
| Walls/Fences | `WALL-` | `WALL-FENCE-A2-A8`, `WALL-BOUNDARY-B1` |
| Gates | `GATE-` | `GATE-MAIN-H12`, `GATE-SECONDARY-A5` |
| Zones | `ZONE-` | `ZONE-PARKING-D4`, `ZONE-CONTAINER-E5` |
| Container stacks | `CNTR-` | `CNTR-STACK-F3` |
| Roads/Paths | `ROAD-` | `ROAD-MAIN-C4-H4` |

**Multi-cell elements:** Use range notation for elements spanning cells:
- `WALL-FENCE-A2-A8` (wall from A2 to A8)
- `ROAD-MAIN-C4-H4` (road from C4 to H4)

### 3. Debug Mode

**Activation Methods:**
- Keyboard: Press `D` to toggle
- URL parameter: `/yard-test-dev?debug=true`
- Console: `window.toggleYardDebug()`

**Features when enabled:**
1. Grid overlay on ground plane with cell labels
2. Element ID labels floating above objects
3. Click any element → Inspector panel appears
4. Mouse coordinates shown (grid cell + DXF coords)

**Features when disabled:**
- Clean view for demos, screenshots, production

### 4. Inspector Panel

**Collapsed view (default):**
```
┌─────────────────────────────────────────┐
│  📍 BLD-OFFICE-C4              [×]     │
│  Grid: C4  │  Type: building           │
│  ▼ More details                         │
└─────────────────────────────────────────┘
```

**Expanded view:**
```
┌─────────────────────────────────────────┐
│  📍 BLD-OFFICE-C4              [×]     │
│  Grid: C4  │  Type: building           │
├─────────────────────────────────────────┤
│  ▲ Less details                         │
├─────────────────────────────────────────┤
│  Dimensions: 20m × 15m × 8m            │
│  DXF: (13024, 73400)                   │
│  Three.js: (15.2, 0, -42.3)            │
│  Rotation: 45°                          │
│  Layer: BUILDINGS                       │
│                                         │
│  [📋 Copy ID]  [🎯 Focus Camera]       │
└─────────────────────────────────────────┘
```

### 5. Data Storage

**File:** `frontend/src/data/yardElements.json`

**Schema:**
```json
{
  "meta": {
    "version": "1.0",
    "gridSize": 20,
    "origin": "top-left",
    "bounds": {
      "dxf": { "minX": 12900, "maxX": 13100, "minY": 73250, "maxY": 73550 },
      "grid": { "columns": 10, "rows": 15 }
    },
    "updatedAt": "2026-01-24"
  },
  "elements": {
    "BLD-OFFICE-C4": {
      "type": "building",
      "name": "Office",
      "grid": "C4",
      "dxf": { "x": 13024, "y": 73400 },
      "dimensions": { "width": 20, "depth": 15, "height": 8 },
      "rotation": 0,
      "layer": "BUILDINGS"
    },
    "WALL-FENCE-A2-A8": {
      "type": "wall",
      "name": "Fence",
      "grid": ["A2", "A3", "A4", "A5", "A6", "A7", "A8"],
      "dxf": {
        "start": { "x": 12900, "y": 73450 },
        "end": { "x": 12900, "y": 73310 }
      },
      "height": 3,
      "layer": "WALLS"
    },
    "GATE-MAIN-H12": {
      "type": "gate",
      "name": "Main",
      "grid": "H12",
      "dxf": { "x": 13024, "y": 73274 },
      "direction": "inbound",
      "rotation": 65
    }
  }
}
```

## File Structure

```
frontend/src/
├── data/
│   └── yardElements.json          # Element registry (NEW)
├── composables/
│   ├── useYardGrid.ts             # Grid overlay rendering (NEW)
│   ├── useYardDebug.ts            # Debug mode state & controls (NEW)
│   ├── useYardInspector.ts        # Click-to-inspect logic (NEW)
│   └── useYardRegistry.ts         # Element registry access (NEW)
├── components/
│   ├── yard/
│   │   ├── YardGridOverlay.vue    # Grid lines + labels (NEW)
│   │   ├── YardElementLabel.vue   # Floating ID labels (NEW)
│   │   ├── YardInspector.vue      # Inspector panel (NEW)
│   │   └── YardDebugControls.vue  # Debug toggle UI (NEW)
└── views/
    └── YardTestView.vue           # Integrate debug mode (MODIFY)
```

## Implementation Tasks

### Task 1: Create Element Registry
- Create `yardElements.json` with initial structure
- Create `useYardRegistry.ts` composable to load and query elements
- Populate with existing buildings, gates from current JSON files

### Task 2: Implement Grid System
- Create `useYardGrid.ts` composable
- Implement DXF-to-grid conversion functions
- Create `YardGridOverlay.vue` component (Three.js grid plane + labels)

### Task 3: Implement Debug Mode
- Create `useYardDebug.ts` composable (state, keyboard handler, URL param)
- Create `YardDebugControls.vue` (optional visual toggle)
- Add debug mode integration to `YardTestView.vue`

### Task 4: Implement Inspector
- Create `useYardInspector.ts` (raycasting, element selection)
- Create `YardInspector.vue` (panel UI)
- Create `YardElementLabel.vue` (floating labels)

### Task 5: Integration & Testing
- Integrate all components into `YardTestView.vue`
- Test grid accuracy with known container positions
- Verify element IDs match between registry and scene

## Usage Examples

After implementation, conversations will work like this:

**Example 1: Remove a building**
> User: "Remove BLD-OFFICE-C4"
> Claude: *Reads yardElements.json, finds element at DXF (13024, 73400), removes from buildings.json*

**Example 2: Add a wall**
> User: "Add a wall from D3 to D8, height 4m"
> Claude: *Calculates DXF coords from grid, creates WALL-NEW-D3-D8, adds to registry*

**Example 3: Report issue**
> User: "The building in E5 looks wrong"
> Claude: *Knows exactly which building, can inspect and fix*

## Success Criteria

- [ ] Grid is visible in debug mode with correct 20m cells
- [ ] All elements have IDs following naming convention
- [ ] Clicking any element shows inspector with correct coordinates
- [ ] Grid cell labels match DXF coordinate calculations
- [ ] Debug mode can be toggled via D key and URL param
- [ ] Element registry contains all buildings, gates, walls, zones
