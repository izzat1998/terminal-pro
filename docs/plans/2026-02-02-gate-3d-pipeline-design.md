# Gate → 3D Animation Pipeline Design

**Date:** 2026-02-02
**Goal:** Connect real gate camera detection to 3D vehicle animations with API polling for Telegram bot events.

## Overview

Full entry→exit loop: gate camera detects plate → vehicle animates in 3D → API polling catches events from other channels (Telegram bot).

Both entry and exit are **brief visual notifications** — vehicle spawns, drives ~20m, fades out. No persistent vehicles in the scene.

## Architecture

```
┌─── CAMERA PATH (instant) ───┐    ┌─── API POLL PATH (5s) ──────┐
│                               │    │                               │
│  GateCameraWidget             │    │  useGateEventPoller           │
│    ↓ vehicleDetected          │    │    ↓ polls /api/entries/      │
│  onVehicleDetected()          │    │    ↓ detects new entry/exit   │
│    ↓ add to recentCameraPlates│    │    ↓ check recentCameraPlates │
│    ↓ spawnVehicle()           │    │    ↓ skip if camera handled   │
│    ↓ animateForward(20m)      │    │    ↓ else trigger animation   │
│    ↓ fadeOut(1s)              │    │                               │
│                               │    │                               │
└───────────────────────────────┘    └───────────────────────────────┘
```

## Changes

### 1. Fix Entry Animation (UnifiedYardView.vue)

Current: `animateVehicleForward(vehicle, 5, 3)` — too short, too fast.

New: `animateVehicleForward(vehicle, 20, 5)` — 20m distance, 5 m/s speed (~4s animation), then 1s fade.

### 2. Fix Exit Animation (UnifiedYardView.vue)

Same adjustment: 20m outward at 5 m/s, 1s fade. Vehicle faces exit direction (already has `rotation.y += Math.PI`).

### 3. Create useGateEventPoller Composable

New file: `src/composables/useGateEventPoller.ts`

Polls `GET /api/terminal/entries/?ordering=-entry_time&page_size=20` every 5 seconds.

Detects:
- **New entries:** `entry_time` newer than last poll, no `exit_date`
- **New exits:** `exit_date` newer than last poll

Callbacks: `onNewEntry(entry)` and `onNewExit(entry)` trigger same animation as camera.

Deduplication via `seenEntryIds`/`seenExitIds` Sets + `recentCameraPlates` Set (30s TTL).

### 4. Wire Poller to UnifiedYardView

In `UnifiedYardView.vue`:
- Initialize `useGateEventPoller` with callbacks
- `onNewEntry` → same animation as `onVehicleDetected`
- `onNewExit` → same animation as `onExitDetected`
- Maintain `recentCameraPlates` Set to prevent double-animation
- Camera handlers add plate to Set, poller checks against it

## Deduplication Strategy

```
Camera detects "01A123BC" → immediate animation → add to recentCameraPlates (30s TTL)
Poller sees entry "01A123BC" → found in recentCameraPlates → skip
Telegram creates "99X777YY" → not in recentCameraPlates → poller triggers animation
```

## API Data Required

```typescript
interface EntryEvent {
  id: number
  transport_number: string   // license plate
  transport_type: 'TRUCK' | 'WAGON'
  entry_time: string
  exit_date: string | null
}
```

Existing `/api/terminal/entries/` endpoint already returns all these fields.
