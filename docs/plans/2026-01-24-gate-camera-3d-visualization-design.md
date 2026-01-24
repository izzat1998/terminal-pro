# Gate Camera System with 3D Vehicle Visualization

**Date:** 2026-01-24
**Status:** Approved
**Author:** Brainstorming session with Claude

## Overview

Real-time gate camera system that detects vehicles (plate number + type) and visualizes them as animated 3D models in the terminal yard view.

## Requirements Summary

| Aspect | Decision |
|--------|----------|
| **Camera (Production)** | IP Camera with RTSP stream |
| **Camera (Testing)** | MacBook webcam or video file |
| **3D Visualization** | Animated low-poly 3D vehicle models |
| **Vehicle Types** | Trucks, light vehicles, rail wagons |
| **Detection** | Plate number + vehicle type classification |
| **Vehicle Behavior** | Animate from gate to parking/waiting zone |
| **Architecture** | Hybrid (frontend local cam, backend RTSP) |
| **Real-time** | WebSocket (Django Channels) |

## System Architecture

### Development Mode

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────────┐
│ MacBook Cam  │────▶│ Vue Frontend     │────▶│ PlateRecognizer    │
│ or Video     │     │ (WebRTC capture) │     │ API (cloud)        │
└──────────────┘     └────────┬─────────┘     └─────────┬──────────┘
                              │                         │
                              ▼                         ▼
                     ┌────────────────────────────────────┐
                     │     3D Yard Visualization          │
                     │     (Vehicle spawns + animates)    │
                     └────────────────────────────────────┘
```

### Production Mode

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────────┐
│ IP Camera    │────▶│ Django Backend   │────▶│ PlateRecognizer    │
│ (RTSP)       │     │ (Stream handler) │     │ + Vehicle Type AI  │
└──────────────┘     └────────┬─────────┘     └─────────┬──────────┘
                              │                         │
                              ▼                         ▼
                     ┌─────────────────┐      ┌────────────────────┐
                     │ WebSocket Event │─────▶│ 3D Visualization   │
                     │ (Django Channels)│      │ (same component)   │
                     └─────────────────┘      └────────────────────┘
```

## 3D Vehicle Models

### Specifications (Real-World Dimensions)

| Vehicle Type | Length | Width | Height | Polygon Target |
|--------------|--------|-------|--------|----------------|
| **Truck Tractor (Head)** | 6.0 m | 2.55 m | 3.8 m | 500-800 |
| **Container Chassis (40ft)** | 12.5 m | 2.5 m | 1.55 m | 200-400 |
| **Container Chassis (20ft)** | 6.1 m | 2.5 m | 1.55 m | 200-400 |
| **Full Truck + 40ft** | 16.5 m | 2.55 m | 4.0 m | 700-1200 |
| **Light Vehicle** | 4.5 m | 1.8 m | 1.6 m | 300-500 |
| **Railway Wagon (NX70)** | 16.4 m | 3.0 m | 1.4 m | 400-600 |

### Model Approach

Low-poly procedural models built with Three.js primitives (BoxGeometry, CylinderGeometry). Start with geometric shapes, upgrade to proper models later if needed.

## Detection System

### Data Flow

```
Camera Frame → Vehicle Detector → Plate Recognizer → Detection Result
                (classify type)    (existing API)
```

### Detection Result Model

```python
@dataclass
class VehicleDetectionResult:
    success: bool
    plate_number: str
    plate_confidence: float
    vehicle_type: str          # "TRUCK" | "CAR" | "WAGON" | "UNKNOWN"
    vehicle_type_confidence: float
    vehicle_make: Optional[str] = None
    vehicle_color: Optional[str] = None
    error_message: Optional[str] = None
```

### Vehicle Type Mapping

PlateRecognizer API already returns vehicle type data - just need to extract and map it:

```python
VEHICLE_TYPE_MAP = {
    "Truck": "TRUCK",
    "Big Truck": "TRUCK",
    "Bus": "TRUCK",
    "Van": "TRUCK",
    "Sedan": "CAR",
    "SUV": "CAR",
    "Pickup": "CAR",
    "Motorcycle": "CAR",
}
```

## WebSocket Events

### Event Types

```typescript
interface GateEvent {
  type: 'vehicle_detected' | 'vehicle_entered' | 'vehicle_exited'
  timestamp: string
  data: VehicleDetection
}

interface VehicleDetection {
  id: string
  plate_number: string
  plate_confidence: number
  vehicle_type: 'TRUCK' | 'CAR' | 'WAGON'
  vehicle_confidence: number
  vehicle_make?: string
  vehicle_color?: string
  gate_id: string
  image_url?: string
}
```

### WebSocket URL

```
ws://localhost:8000/ws/gate/{gate_id}/
```

## Animation System

### Vehicle States

```
DETECTED → ENTERING → PARKED → (later) EXITING → GONE
```

### Path System

Vehicles follow predefined waypoint paths from gate to waiting zone.

```typescript
interface VehiclePath {
  name: string
  waypoints: { x: number; z: number }[]
  duration: number  // seconds
}
```

## File Structure

### Backend (New)

```
backend/apps/gate/
├── __init__.py
├── admin.py
├── apps.py
├── models.py              # GateCamera, VehicleDetection
├── consumers.py           # WebSocket consumers
├── routing.py             # WebSocket URL routing
├── events.py              # Event broadcasting
├── serializers.py
├── views.py
├── urls.py
└── services/
    ├── detection_service.py
    ├── rtsp_service.py
    └── vehicle_classifier.py
```

### Frontend (New)

```
frontend/src/
├── components/
│   ├── GateCameraPanel.vue
│   └── VehicleInfoCard.vue
├── composables/
│   ├── useGateWebSocket.ts
│   ├── useGateDetection.ts
│   ├── useVehicles3D.ts
│   └── useVehicleModels.ts
├── data/
│   └── vehiclePaths.json
└── views/dev/
    └── GateCameraTestView.vue
```

## Implementation Phases

### Phase 1: Enhanced Detection (1-2 days)
- Update PlateRecognizerService to extract vehicle type
- Create VehicleDetectionResult dataclass
- Add vehicle type mapping
- Update API endpoint to return vehicle data
- Test with existing Telegram Mini App

### Phase 2: 3D Vehicle Models (2-3 days)
- Create useVehicleModels.ts composable
- Build procedural truck model (cab + chassis)
- Build procedural car model
- Build procedural rail wagon model
- Add to YardView3D scene
- Test spawning at gate position

### Phase 3: Animation System (1-2 days)
- Define gate position in 3D scene
- Define waiting zone position
- Create path waypoints (vehiclePaths.json)
- Implement useVehicles3D with animation
- Add vehicle state machine
- Add info labels floating above vehicles

### Phase 4: WebSocket Integration (2-3 days)
- Install Django Channels + Redis
- Create gate app with consumers
- Implement event broadcasting
- Create useGateWebSocket.ts composable
- Connect WebSocket events to 3D vehicle spawning
- Test end-to-end flow

### Phase 5: Dev Testing Mode (1 day)
- Create GateCameraTestView.vue
- Implement webcam capture
- Implement video file loading
- Add mock detection mode
- Add dev route

### Phase 6: Production RTSP (Future)
- Implement RTSP stream handler
- Add camera configuration API
- Motion detection / frame sampling
- Deploy and connect to real IP cameras

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | 1-2 days | None |
| Phase 2 | 2-3 days | None (parallel) |
| Phase 3 | 1-2 days | Phase 2 |
| Phase 4 | 2-3 days | Phase 1 |
| Phase 5 | 1 day | Phases 1-4 |
| Phase 6 | Future | Phase 5 |

**Total MVP (Phases 1-5): ~7-10 days**

## Dependencies

### Backend
```
channels>=4.0.0
channels-redis>=4.1.0
```

### Frontend
No additional dependencies (WebSocket is native browser API)

## References

- [BAS World - Truck Dimensions](https://www.basworld.com/en/content/what-are-the-standard-dimensions-of-a-truck)
- [Panda Mech - Container Chassis](https://www.pandamech.com/product/40-shipping-container-chassis-trailers/)
- [AGICO - Railway Flat Wagons](https://railwaywagons.com/rail-freight-wagons/flat-wagons/)
- [PlateRecognizer API Docs](https://docs.platerecognizer.com/)
- [Django Channels Docs](https://channels.readthedocs.io/)
