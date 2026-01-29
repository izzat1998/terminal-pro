# Exit Camera Integration for 3D Yard View

**Date:** 2026-01-29
**Status:** Approved
**Author:** Claude Code + User

## Overview

Add a second camera to the 3D yard view facing the opposite direction to detect vehicles exiting the terminal in real-time.

## Requirements Summary

| Requirement | Decision |
|-------------|----------|
| Gate setup | Same Main Gate, bidirectional (entry + exit lanes) |
| Exit behavior | Match & animate out + update backend; fallback to logging if unknown |
| Camera source | Separate physical camera, independent stream URL |
| UI visualization | Mirrored widgets - Entry camera left, Exit camera right |
| Exit animation | Reverse entry paths (parking zone → gate → drive off-screen) |
| Unknown vehicles | Silent logging only (no 3D clutter) |
| Configuration | Environment variables (`VITE_EXIT_CAMERA_URL`) |
| Test mode | Mock detection + test vehicles for development |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    3D Yard View (YardView3D.vue)                │
├─────────────────────────────┬───────────────────────────────────┤
│   GateWidget (ENTRY)        │   GateWidget (EXIT)               │
│   - Video feed left side    │   - Video feed right side         │
│   - Detection overlay       │   - Detection overlay             │
│   - "ENTRY" label           │   - "EXIT" label                  │
└─────────────────────────────┴───────────────────────────────────┘
              │                              │
              ▼                              ▼
     useGateDetection()            useExitDetection()
     - Entry camera stream         - Exit camera stream
     - Spawns vehicles             - Matches & removes vehicles
     - Animates TO zones           - Animates FROM zones
              │                              │
              └──────────────┬───────────────┘
                             ▼
                    useVehicles3D()
                    - Vehicle registry (Map)
                    - Shared animation system
                    - State management
```

---

## Gate Configuration

### Physical Layout

```
          TERMINAL INTERIOR
                 ↑
    ┌────────────┬────────────┐
    │   EXIT     │   ENTRY    │
    │   LANE     │   LANE     │
    │     ↓      │     ↑      │
    │  [CAM 2]   │  [CAM 1]   │
    │  facing    │  facing    │
    │  outward   │  inward    │
    └────────────┴────────────┘
          OUTSIDE TERMINAL
                 ↓
```

### gatePositions.json Extension

```json
{
  "gates": {
    "main": {
      "name": "Main Gate",
      "dxfPosition": { "x": 12870, "y": 73391 },
      "rotation": 65,
      "lanes": {
        "entry": {
          "offset": { "x": -5, "y": 0 },
          "direction": "inbound",
          "cameraId": "main_entry"
        },
        "exit": {
          "offset": { "x": 5, "y": 0 },
          "direction": "outbound",
          "cameraId": "main_exit"
        }
      }
    }
  },
  "exitPaths": {
    "waiting_to_exit": {
      "waypoints": [
        { "x": 13000, "y": 73400 },
        { "x": 12950, "y": 73395 },
        { "x": 12875, "y": 73391 }
      ],
      "duration": 5
    },
    "parking_a_to_exit": {
      "waypoints": [
        { "x": 12950, "y": 73450 },
        { "x": 12920, "y": 73420 },
        { "x": 12875, "y": 73391 }
      ],
      "duration": 6
    },
    "parking_b_to_exit": {
      "waypoints": [
        { "x": 12960, "y": 73520 },
        { "x": 12930, "y": 73470 },
        { "x": 12900, "y": 73420 },
        { "x": 12875, "y": 73391 }
      ],
      "duration": 7
    }
  }
}
```

---

## Exit Detection Composable

### Interface

```typescript
// frontend/src/composables/3d/useExitDetection.ts

interface ExitDetectionOptions {
  vehicleRegistry: Map<string, ActiveVehicle>
  onVehicleMatched: (vehicle: ActiveVehicle) => void
  onUnknownVehicle: (plateNumber: string) => void
  mockMode?: boolean
}

interface ExitDetectionResult {
  plateNumber: string
  vehicleType: VehicleType
  confidence: number
  timestamp: string
  matchedVehicle: ActiveVehicle | null
}
```

### Core Functions

| Function | Purpose |
|----------|---------|
| `startDetection()` | Connect to exit camera stream, begin processing |
| `stopDetection()` | Disconnect, cleanup resources |
| `matchVehicle(plate)` | Search registry for vehicle by plate number |
| `triggerMockExit()` | Dev mode: simulate random vehicle exiting |
| `processDetection()` | Handle detection → match → animate → cleanup |

### Matching Logic

```typescript
function matchVehicle(plateNumber: string): ActiveVehicle | null {
  for (const [id, vehicle] of vehicleRegistry) {
    if (vehicle.plateNumber === plateNumber &&
        vehicle.state !== 'exiting' &&
        vehicle.state !== 'fading') {
      return vehicle
    }
  }
  return null
}
```

---

## Exit Animation Sequence

```
1. DETECTION
   └─ Exit camera detects plate "01A123BC"

2. MATCH
   └─ Find vehicle in registry → found in "parking_a" zone

3. STATE CHANGE
   └─ vehicle.state = 'exiting'
   └─ Label color → orange

4. ANIMATE TO GATE
   └─ Follow "parking_a_to_exit" path
   └─ Vehicle rotates to face movement direction
   └─ Duration: 6 seconds

5. DRIVE OFF-SCREEN
   └─ Continue 20m past gate (outward direction)
   └─ Duration: 2 seconds

6. FADE & REMOVE
   └─ vehicle.state = 'fading'
   └─ Opacity 1.0 → 0.0 over 1 second
   └─ Remove from scene & registry

7. BACKEND UPDATE
   └─ POST /api/vehicles/{id}/exit/
   └─ Updates database status
```

---

## GateWidget Component Extension

### Props

```typescript
interface GateWidgetProps {
  mode: 'entry' | 'exit'
  cameraUrl: string
  gateName: string
  position?: 'left' | 'right'
  mockMode?: boolean
  onDetection?: (result: DetectionResult) => void
}
```

### Visual Differences

| Aspect | Entry Mode | Exit Mode |
|--------|------------|-----------|
| Header badge | 🟢 "ENTRY" (green) | 🟠 "EXIT" (orange) |
| Position | Left side of screen | Right side of screen |
| Detection label | "Vehicle Entering" | "Vehicle Exiting" |

### Usage in YardView3D

```vue
<template>
  <div class="yard-view-3d">
    <canvas ref="canvas" />

    <GateWidget
      mode="entry"
      position="left"
      :cameraUrl="entryCameraUrl"
      gateName="Main Gate - Entry"
      :mockMode="useMockDetection"
      @detection="handleEntryDetection"
    />

    <GateWidget
      mode="exit"
      position="right"
      :cameraUrl="exitCameraUrl"
      gateName="Main Gate - Exit"
      :mockMode="useMockDetection"
      @detection="handleExitDetection"
    />
  </div>
</template>
```

---

## Test Mode

### Environment Variables

```env
VITE_ENTRY_CAMERA_URL=rtsp://camera1.local:554/stream
VITE_EXIT_CAMERA_URL=rtsp://camera2.local:554/stream
VITE_USE_MOCK_DETECTION=true
```

### Test Functions

```typescript
function createTestExitScenario() {
  const testVehicles = [
    { plate: '01A111AA', zone: 'waiting', type: 'TRUCK' },
    { plate: '01B222BB', zone: 'parking_a', type: 'CAR' },
    { plate: '01C333CC', zone: 'parking_b', type: 'TRUCK' },
  ]

  testVehicles.forEach(v => {
    spawnVehicleAtZone(v.plate, v.zone, v.type)
  })
}

function triggerMockExit() {
  const parkedVehicles = [...vehicleRegistry.values()]
    .filter(v => v.state === 'parked')

  if (parkedVehicles.length === 0) return

  const vehicle = parkedVehicles[Math.floor(Math.random() * parkedVehicles.length)]

  processExitDetection({
    plateNumber: vehicle.plateNumber,
    vehicleType: vehicle.vehicleType,
    confidence: 0.92 + Math.random() * 0.07,
    timestamp: new Date().toISOString(),
    source: 'mock'
  })
}
```

### UI Controls (Mock Mode)

| Control | Action |
|---------|--------|
| "Simulate Entry" button | Spawns random vehicle at entry gate |
| "Simulate Exit" button | Triggers random parked vehicle to exit |
| "Auto Demo" toggle | Automatic entry/exit every 10-15 seconds |

---

## Backend Integration

### API Endpoint

```
POST /api/vehicles/{id}/exit/
```

### Request

```json
{
  "exit_time": "2026-01-29T14:32:15Z",
  "exit_gate": "main",
  "detected_plate": "01A123BC",
  "confidence": 0.95,
  "source": "camera"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": 123,
    "license_plate": "01A123BC",
    "status": "EXITED",
    "entry_time": "2026-01-29T10:15:00Z",
    "exit_time": "2026-01-29T14:32:15Z",
    "duration_minutes": 257
  }
}
```

### Error Handling

- Backend failure does NOT block the 3D animation
- Errors are logged for debugging
- Optional: queue failed updates for retry

---

## Edge Cases

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Same plate detected twice (rapid fire) | Debounce: ignore detections within 5 seconds |
| Vehicle already in 'exiting' state | Skip - already being processed |
| Vehicle in 'fading' state | Skip - already removed |
| Unknown plate (no match) | Log to console + backend, no 3D visualization |
| Camera stream disconnected | Show "Camera Offline" overlay, auto-reconnect every 10s |
| Backend API unavailable | Continue 3D animation, queue notification for retry |
| Multiple vehicles exit simultaneously | Process independently, animations can overlap |
| Mock mode + real camera configured | Mock mode takes precedence |
| Entry and exit detect same plate simultaneously | Entry takes precedence |

### Debounce Implementation

```typescript
const recentDetections = new Map<string, number>()
const DEBOUNCE_MS = 5000

function shouldProcessDetection(plateNumber: string): boolean {
  const lastSeen = recentDetections.get(plateNumber)
  const now = Date.now()

  if (lastSeen && (now - lastSeen) < DEBOUNCE_MS) {
    return false
  }

  recentDetections.set(plateNumber, now)
  return true
}
```

---

## Implementation Files

### New Files

| File | Purpose |
|------|---------|
| `frontend/src/composables/3d/useExitDetection.ts` | Exit detection logic |

### Modified Files

| File | Changes |
|------|---------|
| `frontend/src/components/3d/GateWidget.vue` | Add mode/position props, theming |
| `frontend/src/components/YardView3D.vue` | Add exit GateWidget, handlers |
| `frontend/src/composables/3d/useVehicles3D.ts` | Add exit animation methods |
| `frontend/src/data/gatePositions.json` | Add exit paths, lane config |
| `frontend/.env.example` | Add `VITE_EXIT_CAMERA_URL` |
| `frontend/src/services/vehicleService.ts` | Add `registerExit()` if needed |

---

## Implementation Tasks

1. **Task 1:** Extend gatePositions.json with exit lane and paths
2. **Task 2:** Create useExitDetection.ts composable
3. **Task 3:** Add exit animation methods to useVehicles3D.ts
4. **Task 4:** Extend GateWidget.vue for entry/exit modes
5. **Task 5:** Integrate exit camera into YardView3D.vue
6. **Task 6:** Add environment variable configuration
7. **Task 7:** Implement mock mode and test scenarios
8. **Task 8:** Test full entry → park → exit flow
