# Gate Camera 3D Integration Design

**Date:** 2026-01-25
**Status:** Approved
**Author:** Claude + User collaboration

## Overview

Integrate gate camera vehicle detection into the 3D yard visualization. Users click a 3D security camera model at the main gate to open a detection widget. Detected vehicles spawn at the gate and animate along paths to parking zones.

## Goals

1. Add interactive 3D camera object at main gate location
2. Floating widget for camera feed and vehicle detection
3. Vehicle spawns at camera location when detected
4. Animated movement along predefined paths to parking zones
5. Visual feedback (camera pulse) on detection

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      YardTestView.vue                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    YardView3D                             │  │
│  │                                                           │  │
│  │   [Existing: Containers, Buildings, Fences, Roads]        │  │
│  │                                                           │  │
│  │                         📷 ← GateCamera3D                 │  │
│  │                      ══════                               │  │
│  │                       Gate                                │  │
│  │                                                           │  │
│  │   🚛 ← Vehicles (useVehicles3D)                          │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────┐                                            │
│  │ GateCameraWidget│ ← Floating widget (shown on click)        │
│  │ [Camera Feed]   │                                            │
│  │ [Capture Btn]   │                                            │
│  └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. GateCamera3D.vue

3D security camera model placed at main gate.

**Visual design:**
- Camera body: 0.4m × 0.25m × 0.2m (dark gray, slight metalness)
- Lens: Ø 0.08m cylinder (black with glass reflection)
- Bracket: 0.15m × 0.1m × 0.1m (metallic silver)
- Pole: Ø 0.08m, height 2.5m (metallic silver)
- Base: Ø 0.3m, height 0.05m (concrete gray)
- Camera tilted 15° downward

**Interactive states:**
| State | Visual Effect |
|-------|---------------|
| Normal | Standard materials, subtle shadow |
| Hover | Soft cyan outline glow (emissive boost) |
| Active | Brighter glow, widget opens |
| Detection pulse | Brief flash animation (0.3s) |

**Position:** Main Gate at DXF (13024, 73274), rotation 65°

### 2. GateCameraWidget.vue

Floating panel for camera interaction.

**Layout:**
```
┌──────────────────────────────────┐
│ 📷 Gate Camera           [✕]    │
├──────────────────────────────────┤
│ ┌────────────────────────────┐   │
│ │      [Camera Feed]         │   │
│ │         or                 │   │
│ │    📷 Test Mode            │   │
│ └────────────────────────────┘   │
├──────────────────────────────────┤
│ Source: [Webcam ▼] [Mock ○]      │
├──────────────────────────────────┤
│    ┌────────────────────┐        │
│    │     CAPTURE        │        │
│    └────────────────────┘        │
├──────────────────────────────────┤
│ Last: 01 A 123 BC  🚛 TRUCK     │
│       95% confidence             │
└──────────────────────────────────┘
```

**Behavior:**
- Size: ~320px × 400px
- Opens to right of camera (screen space), flips if near edge
- Draggable by header
- Closes on ✕ click or Escape key
- Stays open when clicking outside

### 3. useGateCamera3D.ts

Composable for camera mesh creation and effects.

**Exports:**
```typescript
interface UseGateCamera3DReturn {
  createCameraMesh(): THREE.Group
  setHovered(hovered: boolean): void
  setActive(active: boolean): void
  triggerPulse(): void
  dispose(): void
}
```

## Vehicle Flow

**Detection timeline:**
```
0s              0.3s              0.5s                    5-8s
│                │                 │                       │
▼                ▼                 ▼                       ▼
Capture      Camera           Vehicle              Vehicle
clicked      pulses           spawns               parked
             (glow)           at gate              in zone
```

**Spawn details:**
- Position: Main Gate (13024, 73274) in DXF coords
- Initial rotation: 65° (facing into yard)
- Vehicle type: Based on detection (TRUCK, CAR, WAGON)
- Label: Plate number floating above

**Animation:**
1. Pick random zone (waiting, parking_a, parking_b)
2. Get path waypoints from gatePositions.json
3. Animate along waypoints with smooth interpolation
4. Rotate to face movement direction
5. Stay parked 30s, then fade out

## File Structure

**New files:**
```
frontend/src/
├── components/yard/
│   ├── GateCamera3D.vue
│   └── GateCameraWidget.vue
├── composables/
│   └── useGateCamera3D.ts
```

**Modified files:**
```
frontend/src/views/YardTestView.vue
```

**Reused (no changes):**
- `useVehicles3D` - vehicle meshes and animation
- `useGateDetection` - plate recognition
- `scenePositions.ts` - gate position, paths
- `gatePositions.json` - waypoints data

## Implementation Steps

| Step | Task | Description |
|------|------|-------------|
| 1 | Create useGateCamera3D.ts | Camera mesh geometry, materials, effects |
| 2 | Create GateCamera3D.vue | 3D component with click/hover handling |
| 3 | Create GateCameraWidget.vue | Floating detection panel |
| 4 | Integrate into YardTestView | Add camera, widget, wire up events |
| 5 | Connect detection flow | Detection → spawn → animate |
| 6 | Add pulse effect | Visual feedback on detection |

## Technical Notes

### Coordinate Transformation
Camera position uses same DXF-to-Three.js transform as other yard elements:
```typescript
const x = (dxfX - center.x) * scale
const z = -(dxfY - center.y) * scale
```

### Click Detection
Use Three.js raycasting on the camera mesh group:
```typescript
raycaster.intersectObjects(cameraMesh.children, true)
```

### Widget Positioning
Convert 3D camera position to screen coordinates:
```typescript
const screenPos = camera3DPos.clone().project(threeCamera)
const x = (screenPos.x * 0.5 + 0.5) * containerWidth
const y = (-screenPos.y * 0.5 + 0.5) * containerHeight
```

## Success Criteria

- [ ] 3D camera visible at main gate in YardTestView
- [ ] Camera highlights on hover
- [ ] Click opens floating widget
- [ ] Widget shows camera feed (webcam or mock mode)
- [ ] Capture button triggers detection
- [ ] Camera pulses on detection
- [ ] Vehicle spawns at gate location
- [ ] Vehicle animates to parking zone
- [ ] Vehicle displays plate number label
- [ ] Widget closable via ✕ or Escape
