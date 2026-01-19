# 3D Container Placement Business Flow

## Executive Summary

This document defines the complete business flow for container placement in the MTT Terminal, from gate entry to verified yard placement. The design follows **TOS (Terminal Operating System) best practices** used by major terminals worldwide (NAVIS N4, Tideworks, COSMOS).

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Business Flow Overview](#2-business-flow-overview)
3. [Detailed Process Stages](#3-detailed-process-stages)
4. [Work Order System](#4-work-order-system)
5. [Notification Architecture](#5-notification-architecture)
6. [Tablet Interface Design](#6-tablet-interface-design)
7. [Verification System](#7-verification-system)
8. [Technical Architecture](#8-technical-architecture)
9. [Data Models](#9-data-models)
10. [API Specifications](#10-api-specifications)
11. [Implementation Phases](#11-implementation-phases)
12. [Best Practices & Standards](#12-best-practices--standards)

---

## 1. Current State Analysis

### What We Have

| Component | Status | Description |
|-----------|--------|-------------|
| 3D Visualization | ✅ Complete | Three.js-based terminal view with InstancedMesh rendering |
| Container Position Model | ✅ Complete | Zone-Row-Bay-Tier-SubSlot coordinate system |
| Placement Service | ✅ Complete | Auto-suggestion algorithm with TOS validation rules |
| Validation Rules | ✅ Complete | Row segregation, size compatibility, weight distribution |
| REST API | ✅ Complete | Layout, suggest, assign, move, remove endpoints |
| Manual Placement UI | ✅ Complete | Admin can assign positions via web interface |

### What's Missing (This Document Addresses)

| Component | Status | Description |
|-----------|--------|-------------|
| Work Order System | ❌ Missing | Trackable placement tasks with lifecycle |
| Real-time Notifications | ❌ Missing | Push updates to mobile devices |
| Tablet Interface | ❌ Missing | Manager's mobile view for placement instructions |
| Placement Verification | ❌ Missing | System confirms container is in correct position |
| Operator Workflow | ❌ Missing | Complete gate-to-yard process automation |

---

## 2. Business Flow Overview

### High-Level Process Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONTAINER PLACEMENT WORKFLOW                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   GATE       │    │   OPERATOR   │    │   MANAGER    │    │   SYSTEM     │
│   ENTRY      │───▶│   ASSIGNS    │───▶│   EXECUTES   │───▶│   VERIFIES   │
│              │    │   POSITION   │    │   PLACEMENT  │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
      │                   │                   │                    │
      ▼                   ▼                   ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Container    │    │ Work Order   │    │ Tablet shows │    │ Position     │
│ registered   │    │ created with │    │ 3D location  │    │ confirmed or │
│ in system    │    │ target pos.  │    │ & directions │    │ flagged      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### Actor Roles

| Actor | Location | Device | Responsibilities |
|-------|----------|--------|------------------|
| **Gate Operator** | Gate booth | Desktop/Tablet | Register container entry, capture data |
| **Control Room Operator** | Control room | Desktop (3D view) | Choose optimal position, create work orders |
| **Yard Manager (CHE Operator)** | Yard (in equipment) | Tablet | Execute placement, confirm completion |
| **System** | Server | - | Validate, notify, verify, audit |

---

## 3. Detailed Process Stages

### Stage 1: Gate Entry (Время: ~2-3 мин)

**Trigger:** Truck arrives at gate with container

**Process:**
```
1.1 Gate operator scans/enters container number
    ├── System checks pre-order (if exists)
    ├── Captures license plate (ANPR or manual)
    └── Validates container format (ISO 6346)

1.2 Container data captured
    ├── Container Number: MSCU1234567
    ├── Size/Type: 40HC (from prefix or manual)
    ├── Status: LADEN or EMPTY
    ├── Weight: 28,500 kg (from docs or weighbridge)
    ├── Customer: ACME Shipping Co
    └── Seal Number: ABC123456

1.3 Container Entry created
    ├── Status: ENTERED
    ├── entry_time: NOW
    └── position: NULL (unplaced)

1.4 Automatic notification sent
    └── → Control Room: "New container awaiting placement"
```

**Output:** `ContainerEntry` record with status ENTERED, triggers Stage 2

---

### Stage 2: Position Assignment (Время: ~30 сек - 2 мин)

**Trigger:** Container entry created OR operator manually initiates

**Process:**
```
2.1 Control room operator sees unplaced container
    ├── 3D view highlights unplaced containers
    ├── List shows container details
    └── System auto-suggests optimal position

2.2 Auto-suggestion algorithm runs
    ├── Input: container size, status, weight, customer
    ├── Algorithm: Consolidation-first
    │   ├── Prefer same-customer stacking
    │   ├── Fill existing stacks before spreading
    │   ├── Minimize moves for future pickup
    │   └── Balance zone utilization
    └── Output: Primary + 3 alternative positions

2.3 Operator reviews and selects position
    ├── View suggestion in 3D (ghost preview)
    ├── Check alternatives if preferred
    ├── Override manually if needed
    └── Confirm position selection

2.4 Work Order created
    ├── Type: PLACEMENT
    ├── Container: MSCU1234567
    ├── Target Position: A-R03-B15-T2-A
    ├── Priority: NORMAL / URGENT
    ├── Status: PENDING
    └── Assigned To: [Available Manager]

2.5 Notification sent to Manager's tablet
    └── → Manager Tablet: "New placement order"
```

**Output:** `PlacementWorkOrder` with status PENDING, assigned to manager

---

### Stage 3: Manager Receives Work Order (Время: ~10 сек)

**Trigger:** Work order created and assigned

**Process:**
```
3.1 Tablet receives push notification
    ├── Sound/vibration alert
    ├── Quick view: Container + Position
    └── Action buttons: Accept / Decline

3.2 Manager accepts work order
    ├── Status changes: PENDING → ACCEPTED
    ├── Timer starts (SLA tracking)
    └── Other managers see order as "In Progress"

3.3 Tablet shows placement instructions
    ├── 3D mini-view of target location
    ├── Path from current location
    ├── Position details:
    │   ├── Zone: A (highlighted on map)
    │   ├── Row: 03 (row marker)
    │   ├── Bay: 15 (bay number)
    │   ├── Tier: 2 (second level)
    │   └── Slot: A (left side)
    ├── Container below (if tier > 1):
    │   └── MSKU9876543 (for visual confirmation)
    └── Special instructions (if any)
```

**Output:** Manager has clear instructions, work order status ACCEPTED

---

### Stage 4: Physical Placement (Время: ~3-5 мин)

**Trigger:** Manager accepted work order

**Process:**
```
4.1 Manager drives to container pickup
    ├── Picks up container from truck/staging
    └── Tablet shows container ID for verification

4.2 Manager drives to target position
    ├── Tablet shows real-time location (optional GPS)
    ├── Audio guidance (optional)
    └── Zone/Row/Bay highlighted

4.3 Manager places container
    ├── Positions in designated spot
    ├── Verifies alignment (visual check)
    └── Notes any issues

4.4 Manager confirms placement on tablet
    ├── Button: "Placement Complete"
    ├── Optional: Take photo of placement
    ├── Optional: Note any discrepancies
    └── Status: ACCEPTED → COMPLETED
```

**Output:** Work order status COMPLETED, triggers verification

---

### Stage 5: System Verification (Время: ~5-30 сек)

**Trigger:** Manager marks placement complete

**Process:**
```
5.1 Automatic validation checks
    ├── Position rules validation:
    │   ├── ✓ Row segregation (40ft in rows 1-5)
    │   ├── ✓ Size compatibility (40ft on 40ft)
    │   ├── ✓ Weight distribution (laden below)
    │   └── ✓ Stacking support (container below exists)
    ├── Conflict detection:
    │   ├── ✓ Position not double-booked
    │   └── ✓ No concurrent placement to same slot
    └── Business rules:
        └── ✓ Container not already placed elsewhere

5.2 Position record created/updated
    ├── ContainerPosition created
    ├── ContainerEntry.position linked
    └── ContainerEntry.location string updated

5.3 Verification methods (configurable)
    ├── Method A: Manager Confirmation Only (current)
    │   └── Trust manager's placement button
    ├── Method B: Photo Verification
    │   ├── Manager uploads placement photo
    │   ├── AI/Operator validates container ID visible
    │   └── Position confirmed or flagged
    ├── Method C: RFID/GPS Verification
    │   ├── RFID reader at each bay (hardware)
    │   ├── Container RFID tag scanned automatically
    │   └── Position confirmed by sensor
    └── Method D: Camera Verification
        ├── Fixed cameras at each zone
        ├── OCR reads container ID
        └── System confirms correct position

5.4 Verification result
    ├── SUCCESS: Work order → VERIFIED
    │   ├── All parties notified
    │   ├── 3D view updated in real-time
    │   └── Audit log created
    └── FAILURE: Work order → FLAGGED
        ├── Alert to control room
        ├── Manager notified of issue
        └── Manual review required
```

**Output:** Final placement confirmed, system updated

---

### Stage 6: Completion & Audit (Время: Immediate)

**Trigger:** Verification complete

**Process:**
```
6.1 Work order finalized
    ├── Status: VERIFIED or FLAGGED
    ├── Completion time recorded
    ├── SLA compliance calculated
    └── Manager performance tracked

6.2 System updates
    ├── 3D visualization updated (WebSocket push)
    ├── Terminal statistics recalculated
    ├── Zone occupancy updated
    └── Customer portal shows container location

6.3 Notifications sent
    ├── → Gate: "Container placed successfully"
    ├── → Customer Portal: Location updated
    └── → Control Room: Statistics refresh

6.4 Audit trail created
    ├── Who: Manager ID
    ├── What: Placed MSCU1234567
    ├── Where: A-R03-B15-T2-A
    ├── When: 2024-01-15 14:32:45
    └── Duration: 4m 23s (accept to complete)
```

**Output:** Complete audit trail, all systems synchronized

---

## 4. Work Order System

### Work Order Model

```python
class PlacementWorkOrder(models.Model):
    """Tracks container placement tasks from creation to verification."""

    # Identity
    id = UUIDField(primary_key=True)
    order_number = CharField(unique=True)  # WO-20240115-0001

    # What
    container_entry = ForeignKey(ContainerEntry)
    order_type = CharField(choices=[
        ('PLACEMENT', 'New Container Placement'),
        ('RELOCATION', 'Container Move/Shuffle'),
        ('RETRIEVAL', 'Container Retrieval for Exit'),
    ])

    # Where
    target_zone = CharField(max_length=1)
    target_row = IntegerField()
    target_bay = IntegerField()
    target_tier = IntegerField()
    target_sub_slot = CharField(max_length=1)

    # Who
    created_by = ForeignKey(User)  # Control room operator
    assigned_to = ForeignKey(User, null=True)  # Yard manager

    # When
    created_at = DateTimeField(auto_now_add=True)
    accepted_at = DateTimeField(null=True)
    started_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)
    verified_at = DateTimeField(null=True)

    # Status
    status = CharField(choices=[
        ('PENDING', 'Awaiting Assignment'),
        ('ASSIGNED', 'Assigned to Manager'),
        ('ACCEPTED', 'Manager Accepted'),
        ('IN_PROGRESS', 'Placement in Progress'),
        ('COMPLETED', 'Placement Done, Awaiting Verification'),
        ('VERIFIED', 'Position Verified'),
        ('FLAGGED', 'Verification Failed'),
        ('CANCELLED', 'Order Cancelled'),
    ])

    # Priority
    priority = CharField(choices=[
        ('LOW', 'Low - Can wait'),
        ('NORMAL', 'Normal - Standard SLA'),
        ('HIGH', 'High - Priority customer'),
        ('URGENT', 'Urgent - Immediate action'),
    ])

    # Verification
    verification_method = CharField(choices=[
        ('MANUAL', 'Manager Confirmation'),
        ('PHOTO', 'Photo Verification'),
        ('RFID', 'RFID Sensor'),
        ('CAMERA', 'OCR Camera'),
    ])
    verification_photo = ImageField(null=True)
    verification_notes = TextField(blank=True)

    # Performance
    sla_deadline = DateTimeField()
    sla_met = BooleanField(null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['status', 'assigned_to']),
            Index(fields=['created_at']),
        ]
```

### Work Order Lifecycle

```
                    ┌─────────────────────────────────────────────────────────┐
                    │              WORK ORDER STATE MACHINE                    │
                    └─────────────────────────────────────────────────────────┘

                                    ┌──────────┐
                      create()      │ PENDING  │
                    ───────────────▶│          │
                                    └────┬─────┘
                                         │ assign(manager)
                                         ▼
                                    ┌──────────┐
                                    │ ASSIGNED │◀─────────────────┐
                                    │          │                  │
                                    └────┬─────┘                  │
                                         │ accept()               │ reassign()
                                         ▼                        │
                                    ┌──────────┐                  │
                                    │ ACCEPTED │──────────────────┘
                                    │          │     decline()
                                    └────┬─────┘
                                         │ start()
                                         ▼
                                    ┌──────────┐
                                    │IN_PROGRESS│
                                    │          │
                                    └────┬─────┘
                                         │ complete()
                                         ▼
                                    ┌──────────┐
                                    │COMPLETED │
                                    │          │
                                    └────┬─────┘
                                         │ verify()
                               ┌─────────┴─────────┐
                               ▼                   ▼
                          ┌──────────┐        ┌──────────┐
                          │ VERIFIED │        │ FLAGGED  │
                          │    ✓     │        │    ⚠     │
                          └──────────┘        └────┬─────┘
                                                   │ resolve()
                                                   ▼
                                              ┌──────────┐
                                              │ VERIFIED │
                                              │    ✓     │
                                              └──────────┘

    At any state (except VERIFIED/CANCELLED):
    ──────────────────────────────────────────
                    cancel() ───▶ CANCELLED
```

### SLA Configuration

| Priority | Placement SLA | Retrieval SLA | Escalation |
|----------|---------------|---------------|------------|
| LOW | 60 min | 45 min | After deadline |
| NORMAL | 30 min | 20 min | 80% of deadline |
| HIGH | 15 min | 10 min | 50% of deadline |
| URGENT | 5 min | 5 min | Immediate if not accepted |

---

## 5. Notification Architecture

### Notification Channels

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NOTIFICATION SYSTEM                                   │
└─────────────────────────────────────────────────────────────────────────────┘

                         ┌────────────────────┐
                         │   Event Trigger    │
                         │ (Work Order Change)│
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Notification       │
                         │ Service            │
                         └─────────┬──────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      ▼                      ▼
    ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
    │   WebSocket   │      │     Push      │      │   Telegram    │
    │   (Real-time) │      │ Notification  │      │     Bot       │
    └───────┬───────┘      └───────┬───────┘      └───────┬───────┘
            │                      │                      │
            ▼                      ▼                      ▼
    ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
    │  3D View      │      │   Manager     │      │   Manager     │
    │  Control Room │      │   Tablet App  │      │   Telegram    │
    │  Web Dashboard│      │   (PWA)       │      │   Mini App    │
    └───────────────┘      └───────────────┘      └───────────────┘
```

### Notification Events

| Event | Recipients | Channels | Content |
|-------|------------|----------|---------|
| Container Entered | Control Room | WebSocket | New container awaiting placement |
| Work Order Created | Assigned Manager | Push, Telegram | New placement order details |
| Work Order Accepted | Control Room | WebSocket | Manager {name} accepted |
| Placement Started | Control Room | WebSocket | Manager en route |
| Placement Completed | Control Room, Gate | WebSocket, Push | Awaiting verification |
| Placement Verified | All | WebSocket, Push | Container placed at {position} |
| Placement Flagged | Control Room, Manager | WebSocket, Push, Telegram | Verification failed |
| SLA Warning | Control Room, Manager | WebSocket, Push | Order approaching deadline |
| SLA Breach | Control Room, Supervisor | WebSocket, Push, Telegram | SLA missed |

### WebSocket Implementation

```python
# Channel groups
CHANNEL_GROUPS = {
    'placement_updates': 'placement.updates.all',
    'zone_updates': 'placement.updates.zone.{zone}',
    'manager_orders': 'placement.orders.manager.{manager_id}',
    'control_room': 'placement.control_room',
}

# Message format
{
    "type": "placement.update",
    "event": "WORK_ORDER_CREATED",
    "data": {
        "work_order_id": "WO-20240115-0001",
        "container_number": "MSCU1234567",
        "target_position": "A-R03-B15-T2-A",
        "priority": "NORMAL",
        "assigned_to": "Manager Ivan",
    },
    "timestamp": "2024-01-15T14:32:45Z"
}
```

---

## 6. Tablet Interface Design

### Manager App: Telegram Mini App (Extended)

**Technology:** React 18 + TypeScript (extends existing `telegram-miniapp/`)
**Platform:** Telegram app on Android/iOS tablets and phones
**Offline Support:** Basic localStorage + Service Worker (WiFi coverage assumed)
**Push Notifications:** Telegram native notifications
**Visualization:** 2D Canvas/SVG grid (simple, worker-friendly)

### Why Telegram Mini App (Not Flutter)

| Factor | Flutter | Telegram Mini App ✅ |
|--------|---------|---------------------|
| Tech Stack | New (Dart) | Existing (React/TS) |
| Team Expertise | Must learn | Already know |
| Deployment | App Store process | Instant (web deploy) |
| Updates | Version fragmentation | Always latest |
| User Adoption | Must download app | Already in Telegram |
| Maintenance | Separate codebase | Same team |
| Development Time | 10-12 weeks | 5-8 weeks |
| Offline (with WiFi) | Overkill | Sufficient |
| Workers Familiar | No | Yes (use Telegram daily) |

**Key Decision Factor:** Terminal has full WiFi coverage, eliminating need for Flutter's offline capabilities.

### Screen Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TELEGRAM MINI APP SCREENS                                 │
└─────────────────────────────────────────────────────────────────────────────┘

  User opens Telegram → Bot chat → "Открыть приложение" button
                                           │
                                           ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  DASHBOARD   │───▶│  WORK ORDER  │───▶│   ORDER      │───▶│   CONFIRM    │
│  (existing)  │    │    LIST      │    │  + 2D MAP    │    │  + PHOTO     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                   │
       │                   ▼                   ▼                   ▼
       │            ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
       │            │  PENDING     │    │  GRID +      │    │  SUCCESS     │
       │            │  ORDERS      │    │  SIDE VIEW   │    │  FEEDBACK    │
       │            │  BADGE       │    │              │    │              │
       │            └──────────────┘    └──────────────┘    └──────────────┘
       │
       └───▶ Existing: Vehicles, Camera, Exit (unchanged)
```

**Key UX Principle:** Auto-login via Telegram (no password), workers already familiar with Telegram.

### Key Screens

#### 1. Work Order List

```
┌─────────────────────────────────────┐
│  📋 Мои наряды              [🔄]   │
├─────────────────────────────────────┤
│  ┌─────────────────────────────────┐│
│  │ 🔴 WO-0015 | СРОЧНО            ││
│  │ MSCU1234567 → A-R03-B15-T2     ││
│  │ 40HC ГРУЖ | ACME Shipping      ││
│  │ ⏱️ Осталось 3:45               ││
│  │ [Принять]  [Отклонить]         ││
│  └─────────────────────────────────┘│
│  ┌─────────────────────────────────┐│
│  │ 🟡 WO-0014 | ОБЫЧНЫЙ           ││
│  │ TCKU9876543 → A-R05-B08-T1     ││
│  │ 20ft ПОРОЖ | Global Trade      ││
│  │ ⏱️ Осталось 18:30              ││
│  │ [Принять]  [Отклонить]         ││
│  └─────────────────────────────────┘│
│                                     │
│  ═══════════════════════════════════│
│  ✅ Выполнено сегодня: 12           │
│  ⏱️ Среднее время: 4м 15с          │
└─────────────────────────────────────┘
```

#### 2. Order Details + 2D Grid View

```
┌─────────────────────────────────────┐
│  ← Назад        WO-0015      [📍]  │
├─────────────────────────────────────┤
│                                     │
│   ЗОНА A - ВИД СВЕРХУ               │
│   ═══════════════════════════════   │
│                                     │
│      B13   B14   B15   B16   B17    │
│     ┌────┬────┬────┬────┬────┐     │
│  R01│ 2  │ 3  │ 2  │ 1  │    │     │
│     ├────┼────┼────┼────┼────┤     │
│  R02│ 1  │ 2  │ 3  │ 2  │ 1  │     │
│     ├────┼────┼────╋════╋────┤     │
│  R03│ 2  │ 1  │ 1 ║🎯T2║    │     │  ← ЦЕЛЬ
│     ├────┼────┼────╋════╋────┤     │
│  R04│ 3  │ 2  │ 2  │ 1  │ 1  │     │
│     └────┴────┴────┴────┴────┘     │
│                                     │
│  ┌─────────────────────────────────┐│
│  │  ВИД СБОКУ (Ряд 03)             ││
│  │  T4 │    │    │    │    │    │ ││
│  │  T3 │    │    │    │    │    │ ││
│  │  T2 │    │    │ 🎯 │    │    │ ││
│  │  T1 │ ██ │ ██ │ ██ │    │    │ ││
│  │     │B13 │B14 │B15 │B16 │B17 │ ││
│  └─────────────────────────────────┘│
│                                     │
│  📦 MSCU1234567                     │
│  ├─ Размер: 40ft High Cube         │
│  ├─ Статус: ГРУЖЁНЫЙ (28,500 кг)   │
│  ├─ Клиент: ACME Shipping          │
│  └─ Пломба: ABC123456              │
│                                     │
│  📍 Целевая позиция: A-R03-B15-T2  │
│  ⚠️ Под ним: MSKU9876543           │
│                                     │
│  ┌─────────────────────────────────┐│
│  │   [▶️ НАЧАТЬ РАЗМЕЩЕНИЕ]        ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

#### 3. Placement Confirmation

```
┌─────────────────────────────────────┐
│  ← Назад    Подтверждение          │
├─────────────────────────────────────┤
│                                     │
│  📦 MSCU1234567                     │
│  📍 A-R03-B15-T2-A                  │
│                                     │
│  ┌─────────────────────────────────┐│
│  │                                 ││
│  │      [Камера - Видоискатель]    ││
│  │                                 ││
│  │   📸 Сфотографируйте контейнер  ││
│  │      (опционально)              ││
│  │                                 ││
│  └─────────────────────────────────┘│
│                                     │
│  ☑️ Контейнер размещён правильно    │
│  ☑️ Выровнен по разметке            │
│  ☐ Есть проблема (опционально)      │
│                                     │
│  Примечания:                        │
│  ┌─────────────────────────────────┐│
│  │                                 ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  [✅ ПОДТВЕРДИТЬ РАЗМЕЩЕНИЕ]    ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  [⚠️ Сообщить о проблеме]       ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

### 2D Visualization Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         2D VISUALIZATION COMPONENTS                          │
└─────────────────────────────────────────────────────────────────────────────┘

TOP-DOWN GRID VIEW (Primary):
─────────────────────────────
  ┌────┬────┬────┬────┬────┐
  │ 2  │ 3  │ 🎯 │ 1  │    │   • Numbers = tier count (stack height)
  ├────┼────┼────┼────┼────┤   • Colors = occupancy level
  │ 1  │ 2  │ 2  │    │    │   • 🎯 = Target position (gold)
  └────┴────┴────┴────┴────┘   • Empty = available ground slot

COLOR CODING:
─────────────
  ┌──────┐ Empty (available)     - Grey 200
  │      │
  └──────┘
  ┌──────┐ 1 tier (can stack 3)  - Green 300
  │  1   │
  └──────┘
  ┌──────┐ 2 tiers (can stack 2) - Green 500
  │  2   │
  └──────┘
  ┌──────┐ 3 tiers (can stack 1) - Orange 400
  │  3   │
  └──────┘
  ┌──────┐ 4 tiers (FULL)        - Red 400
  │  4   │
  └──────┘
  ╔══════╗ Target position       - Amber 600
  ║ 🎯T2 ║
  ╚══════╝

SIDE VIEW (Cross-section):
──────────────────────────
  Shows stacking at target row

  T4 │    │    │    │    │
  T3 │    │    │    │    │
  T2 │    │ 🎯 │    │    │  ← Your container placement
  T1 │ ██ │ ██ │ ██ │    │  ← Container below (support)
     │B14 │B15 │B16 │B17 │

  • Helps visualize vertical stacking
  • Shows container below for confirmation
  • Gold highlight for target tier
```

### Offline Support (Flutter)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FLUTTER OFFLINE ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Online Mode:
────────────
  Flutter App ←──WebSocket──→ Server ←──→ Database
              ←──REST API───→
              ←──FCM Push────→

Offline Mode (yard has poor signal):
────────────────────────────────────
  ┌────────────────────────────┐
  │   Flutter App              │
  │  ┌──────────────────────┐  │
  │  │ Hive (Fast NoSQL)    │  │     Syncs when online:
  │  │ ├─ Work Orders       │  │    ────────────────────
  │  │ ├─ Terminal Layout   │  │     Queue → Server
  │  │ └─ User Session      │  │     Pull latest data
  │  └──────────────────────┘  │     Resolve conflicts
  │  ┌──────────────────────┐  │
  │  │ SQLite (Structured)  │  │
  │  │ ├─ Container History │  │
  │  │ └─ Audit Logs        │  │
  │  └──────────────────────┘  │
  │  ┌──────────────────────┐  │
  │  │ Action Queue         │  │
  │  │ ├─ Accept Order      │  │
  │  │ ├─ Complete Order    │  │
  │  │ └─ Photos (Base64)   │  │
  │  └──────────────────────┘  │
  └────────────────────────────┘

Conflict Resolution:
───────────────────
  - Server timestamp wins for concurrent edits
  - Queue cleared after successful sync
  - User notified of any conflicts
  - Retry with exponential backoff
```

### Telegram Mini App Extension Structure

Extends existing `telegram-miniapp/` project:

```
telegram-miniapp/src/
├── pages/
│   ├── IndexPage/                 # ✅ EXISTS - Dashboard (extend with placement stats)
│   ├── VehiclesPage/              # ✅ EXISTS - Vehicle list
│   ├── CameraPage/                # ✅ EXISTS - Vehicle entry with plate recognition
│   ├── ExitEntryPage/             # ✅ EXISTS - Vehicle exit workflow
│   │
│   ├── WorkOrdersPage/            # 🆕 NEW - List of placement work orders
│   │   ├── index.tsx
│   │   └── WorkOrdersPage.css
│   ├── PlacementDetailPage/       # 🆕 NEW - 2D grid + side view + order details
│   │   ├── index.tsx
│   │   └── PlacementDetailPage.css
│   └── PlacementConfirmPage/      # 🆕 NEW - Photo + checklist + confirm
│       ├── index.tsx
│       └── PlacementConfirmPage.css
│
├── components/
│   ├── CameraCapture/             # ✅ EXISTS - Reuse for placement photo
│   ├── CameraOverlay/             # ✅ EXISTS
│   │
│   └── placement/                 # 🆕 NEW - All placement components
│       ├── YardGrid.tsx           # 2D top-down grid (Canvas or SVG)
│       ├── YardGrid.css
│       ├── RowSideView.tsx        # Cross-section tier visualization
│       ├── PositionCell.tsx       # Single grid cell component
│       ├── WorkOrderCard.tsx      # Order card for list
│       ├── CountdownTimer.tsx     # SLA countdown
│       ├── PriorityBadge.tsx      # Priority indicator
│       └── StackingWarning.tsx    # Tier warning message
│
├── hooks/
│   ├── useCameraCapture.ts        # ✅ EXISTS - Reuse
│   ├── usePlateRecognition.ts     # ✅ EXISTS
│   │
│   ├── useWorkOrders.ts           # 🆕 NEW - Fetch/accept/complete orders
│   ├── useYardLayout.ts           # 🆕 NEW - Fetch grid data
│   └── usePlacement.ts            # 🆕 NEW - Placement workflow state
│
├── contexts/
│   ├── CameraContext.tsx          # ✅ EXISTS
│   ├── PageContext.tsx            # ✅ EXISTS
│   │
│   └── PlacementContext.tsx       # 🆕 NEW - Current placement state
│
├── types/
│   ├── api.ts                     # ✅ EXISTS - Extend with placement types
│   └── placement.ts               # 🆕 NEW - WorkOrder, Position, YardLayout
│
└── config/
    └── api.ts                     # ✅ EXISTS - Add placement endpoints
```

**Reuse Summary:**
- Camera system: 100% reuse
- API patterns: 100% reuse
- Form dialogs: Pattern reuse
- Access control: 100% reuse
- Theme/styling: 100% reuse

---

## 7. Verification System

### Verification Methods

#### Method A: Manager Confirmation (Simple)

```
Manager clicks "Confirm Placement"
         │
         ▼
┌─────────────────────────────┐
│ Validation checks           │
│ ├─ Position rules valid     │
│ ├─ No conflicts             │
│ └─ Container not moved      │
└─────────────────────────────┘
         │
         ▼
    ✅ VERIFIED
```

**Pros:** Simple, no additional hardware
**Cons:** Relies on human accuracy, no independent verification

---

#### Method B: Photo Verification (Recommended)

```
Manager takes placement photo
         │
         ▼
┌─────────────────────────────┐
│ Photo uploaded              │
│ ├─ Stored in S3/MinIO       │
│ └─ Linked to work order     │
└─────────────────────────────┘
         │
         ├──────────────────────┐
         ▼                      ▼
┌─────────────────────┐  ┌─────────────────────┐
│ AI Verification     │  │ Manual Verification │
│ (Optional)          │  │ (Fallback)          │
│ ├─ OCR container ID │  │ ├─ Control room     │
│ ├─ Position markers │  │ │   reviews photo   │
│ └─ Confidence score │  │ └─ Approves/rejects │
└─────────────────────┘  └─────────────────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
              ✅ VERIFIED or ⚠️ FLAGGED
```

**Pros:** Visual record, can be audited, AI-assistable
**Cons:** Requires camera, network bandwidth for photos

---

#### Method C: RFID Verification (Advanced)

```
Container has RFID tag
         │
         ▼
┌─────────────────────────────┐
│ RFID Reader at each bay     │
│ ├─ Detects container tag    │
│ ├─ Reports to server        │
│ └─ Matches expected ID      │
└─────────────────────────────┘
         │
         ▼
    ✅ VERIFIED (automatic)
```

**Pros:** Fully automatic, highly accurate
**Cons:** Expensive hardware, RFID tags on containers

---

#### Method D: Camera OCR Verification (Enterprise)

```
Fixed cameras on gantries/posts
         │
         ▼
┌─────────────────────────────┐
│ Camera System               │
│ ├─ Captures zone images     │
│ ├─ OCR reads container IDs  │
│ └─ Compares to expected     │
└─────────────────────────────┘
         │
         ▼
    ✅ VERIFIED (automatic)
```

**Pros:** Automatic, covers entire yard
**Cons:** Expensive infrastructure, requires good lighting

---

### Recommended Approach: Hybrid

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RECOMMENDED VERIFICATION FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

Phase 1 (MVP):
──────────────
  Manager Confirmation + Optional Photo

Phase 2 (Enhancement):
─────────────────────
  Required Photo + AI OCR Validation

Phase 3 (Enterprise):
────────────────────
  RFID/Camera integration (if ROI justified)
```

---

## 8. Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TECHNICAL ARCHITECTURE                               │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────────┐
                    │           FRONTEND LAYER              │
                    ├──────────────────────────────────────┤
                    │  ┌────────────┐  ┌─────────────────┐ │
                    │  │ Control    │  │ Manager Tablet  │ │
                    │  │ Room       │  │ (FLUTTER)       │ │
                    │  │ Dashboard  │  │                 │ │
                    │  │ (Vue 3)    │  │ ├─ Work Orders  │ │
                    │  │            │  │ ├─ 2D Grid View │ │
                    │  │ ├─ 3D View │  │ ├─ Native Camera│ │
                    │  │ ├─ Orders  │  │ ├─ Hive/SQLite  │ │
                    │  │ └─ Stats   │  │ └─ FCM Push     │ │
                    │  └──────┬─────┘  └────────┬────────┘ │
                    └─────────┼─────────────────┼──────────┘
                              │                 │
                    ┌─────────▼─────────────────▼──────────┐
                    │          API GATEWAY                  │
                    │  ├─ REST API (DRF)                   │
                    │  ├─ WebSocket (Django Channels)      │
                    │  └─ Push Notifications (FCM)         │
                    └─────────────────┬────────────────────┘
                                      │
┌─────────────────────────────────────┼─────────────────────────────────────┐
│                         BACKEND LAYER                                      │
├─────────────────────────────────────┼─────────────────────────────────────┤
│  ┌──────────────────────┐  ┌────────▼────────┐  ┌──────────────────────┐  │
│  │  Work Order Service  │  │ Placement       │  │ Notification         │  │
│  │                      │  │ Service         │  │ Service              │  │
│  │  ├─ Create/Assign    │  │                 │  │                      │  │
│  │  ├─ State Machine    │  │ ├─ Suggest      │  │ ├─ WebSocket Push    │  │
│  │  ├─ SLA Tracking     │  │ ├─ Validate     │  │ ├─ FCM Push          │  │
│  │  └─ Performance      │  │ ├─ Assign       │  │ └─ Telegram Bot      │  │
│  │     Metrics          │  │ └─ Verify       │  │                      │  │
│  └──────────────────────┘  └─────────────────┘  └──────────────────────┘  │
│                                                                            │
│  ┌──────────────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │
│  │  Verification        │  │ Audit           │  │ Analytics            │  │
│  │  Service             │  │ Service         │  │ Service              │  │
│  │                      │  │                 │  │                      │  │
│  │  ├─ Photo Upload     │  │ ├─ Action Log   │  │ ├─ SLA Reports       │  │
│  │  ├─ OCR Validation   │  │ ├─ Change Track │  │ ├─ Manager Perf      │  │
│  │  └─ Manual Review    │  │ └─ Compliance   │  │ └─ Zone Utilization  │  │
│  └──────────────────────┘  └─────────────────┘  └──────────────────────┘  │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │          DATA LAYER              │
                    ├─────────────────────────────────┤
                    │  ┌───────────┐  ┌────────────┐  │
                    │  │PostgreSQL │  │ Redis      │  │
                    │  │           │  │            │  │
                    │  │├─ Models  │  │├─ Channels │  │
                    │  │├─ Orders  │  │├─ Cache    │  │
                    │  │└─ Audit   │  │└─ Sessions │  │
                    │  └───────────┘  └────────────┘  │
                    │  ┌───────────┐  ┌────────────┐  │
                    │  │ S3/MinIO  │  │ Celery     │  │
                    │  │           │  │            │  │
                    │  │├─ Photos  │  │├─ Async    │  │
                    │  │└─ Docs    │  │└─ Scheduled│  │
                    │  └───────────┘  └────────────┘  │
                    └─────────────────────────────────┘
```

### Django Channels Setup (WebSocket)

```python
# routing.py
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/placement/", PlacementConsumer.as_asgi()),
            path("ws/orders/", WorkOrderConsumer.as_asgi()),
        ])
    ),
})

# consumers.py
class PlacementConsumer(WebsocketConsumer):
    """Real-time placement updates."""

    async def connect(self):
        await self.channel_layer.group_add(
            "placement_updates",
            self.channel_name
        )
        await self.accept()

    async def placement_update(self, event):
        await self.send(json.dumps(event['data']))
```

---

## 9. Data Models

### Complete Model Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA MODEL                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐       ┌──────────────────────┐
│   ContainerEntry     │       │   ContainerPosition  │
├──────────────────────┤       ├──────────────────────┤
│ id                   │       │ id                   │
│ container_number     │       │ zone                 │
│ size                 │       │ row                  │
│ status (laden/empty) │       │ bay                  │
│ weight               │       │ tier                 │
│ customer             │       │ sub_slot             │
│ entry_time           │1     1│ coordinate (computed)│
│ exit_time            │───────│ container_entry (FK) │
│ seal_number          │       │ created_at           │
│ location (legacy)    │       │ updated_at           │
└──────────────────────┘       └──────────────────────┘
          │
          │ 1
          │
          │ *
┌─────────▼────────────┐       ┌──────────────────────┐
│ PlacementWorkOrder   │       │   User               │
├──────────────────────┤       ├──────────────────────┤
│ id                   │       │ id                   │
│ order_number         │       │ username             │
│ container_entry (FK) │       │ role                 │
│ order_type           │       │ device_token (FCM)   │
│ target_zone          │     * │ telegram_id          │
│ target_row           │◀──────│ is_yard_manager      │
│ target_bay           │       └──────────────────────┘
│ target_tier          │ assigned_to
│ target_sub_slot      │
│ status               │       ┌──────────────────────┐
│ priority             │       │  WorkOrderAudit      │
│ created_by (FK)      │       ├──────────────────────┤
│ assigned_to (FK)     │1     *│ id                   │
│ created_at           │───────│ work_order (FK)      │
│ accepted_at          │       │ action               │
│ started_at           │       │ old_status           │
│ completed_at         │       │ new_status           │
│ verified_at          │       │ performed_by (FK)    │
│ verification_method  │       │ timestamp            │
│ verification_photo   │       │ metadata (JSON)      │
│ verification_notes   │       └──────────────────────┘
│ sla_deadline         │
│ sla_met              │
└──────────────────────┘

┌──────────────────────┐       ┌──────────────────────┐
│   Notification       │       │   ManagerDevice      │
├──────────────────────┤       ├──────────────────────┤
│ id                   │       │ id                   │
│ recipient (FK)       │       │ user (FK)            │
│ event_type           │       │ device_token         │
│ title                │       │ platform (ios/and)   │
│ message              │       │ last_active          │
│ data (JSON)          │       │ is_active            │
│ sent_at              │       └──────────────────────┘
│ read_at              │
│ channel              │
└──────────────────────┘
```

---

## 10. API Specifications

### New Endpoints

#### Work Orders

```yaml
# Create work order (auto-assigns position)
POST /api/terminal/work-orders/
Request:
  container_entry_id: uuid
  priority: string (NORMAL)
  zone_preference: string? (optional)
Response:
  success: true
  data:
    id: uuid
    order_number: "WO-20240115-0001"
    container_number: "MSCU1234567"
    target_position: "A-R03-B15-T2-A"
    status: "PENDING"
    assigned_to: null
    sla_deadline: "2024-01-15T15:00:00Z"

# List work orders (for managers)
GET /api/terminal/work-orders/
Query params:
  status: string (PENDING,ASSIGNED,ACCEPTED,IN_PROGRESS)
  assigned_to: uuid (filter by manager)
  priority: string
Response:
  success: true
  data: [WorkOrder, ...]
  meta:
    count: 5
    pending: 2
    in_progress: 3

# Accept work order
POST /api/terminal/work-orders/{id}/accept/
Response:
  success: true
  data: WorkOrder (status: ACCEPTED)

# Decline work order
POST /api/terminal/work-orders/{id}/decline/
Request:
  reason: string
Response:
  success: true
  data: WorkOrder (status: PENDING, assigned_to: null)

# Start placement
POST /api/terminal/work-orders/{id}/start/
Response:
  success: true
  data: WorkOrder (status: IN_PROGRESS)

# Complete placement
POST /api/terminal/work-orders/{id}/complete/
Request:
  photo: file? (optional)
  notes: string?
  checklist:
    placed_correctly: boolean
    aligned: boolean
    issue_reported: boolean
Response:
  success: true
  data: WorkOrder (status: COMPLETED or VERIFIED)

# Verify placement (control room)
POST /api/terminal/work-orders/{id}/verify/
Request:
  verified: boolean
  notes: string?
Response:
  success: true
  data: WorkOrder (status: VERIFIED or FLAGGED)
```

#### WebSocket Events

```yaml
# Connect to work order stream
ws://api/ws/orders/?token={jwt}

# Events received:
{
  type: "work_order.created",
  data: {
    id: uuid,
    order_number: string,
    container_number: string,
    target_position: string,
    priority: string,
    assigned_to: uuid | null
  }
}

{
  type: "work_order.updated",
  data: {
    id: uuid,
    status: string,
    updated_fields: string[]
  }
}

{
  type: "work_order.assigned",
  data: {
    id: uuid,
    assigned_to: uuid,
    manager_name: string
  }
}

{
  type: "placement.verified",
  data: {
    container_number: string,
    position: string,
    work_order_id: uuid
  }
}
```

---

## 11. Implementation Phases

### Phase 1: Foundation (2-3 weeks)

**Goal:** Work order system with basic flow

| Task | Effort | Dependencies |
|------|--------|--------------|
| PlacementWorkOrder model | 2d | - |
| WorkOrderService (CRUD + state machine) | 3d | Model |
| Work order API endpoints | 2d | Service |
| Control room: Work order list | 2d | API |
| Control room: Create order from unplaced | 1d | API |
| Integration tests | 2d | All above |

**Deliverable:** Control room can create and track work orders

---

### Phase 2: Telegram Mini App Extension (2-3 weeks)

**Goal:** Extend existing Mini App with placement workflow (React + TypeScript)

| Task | Effort | Dependencies |
|------|--------|--------------|
| TypeScript types for placement | 0.5d | - |
| API endpoints in config | 0.5d | Phase 1 |
| WorkOrderCard component | 1d | Types |
| WorkOrdersPage (list) | 1.5d | Card component |
| YardGrid component (2D Canvas/SVG) | 2d | - |
| RowSideView component | 1d | Grid |
| PlacementDetailPage | 1.5d | Grid + Side |
| Accept/decline API integration | 1d | Phase 1 |
| PlacementConfirmPage | 1.5d | Existing camera |
| CountdownTimer + PriorityBadge | 0.5d | - |
| Integration testing | 1d | All above |
| Worker UX polish (large buttons) | 1d | All above |

**Deliverable:** Extended Telegram Mini App with placement workflow

**Advantages over Flutter:**
- Uses existing camera system (already works)
- Uses existing API patterns (already works)
- Same tech stack as team knows
- No app store deployment needed
- Instant updates

---

### Phase 3: Real-time Updates (1-2 weeks)

**Goal:** WebSocket updates across all clients

| Task | Effort | Dependencies |
|------|--------|--------------|
| Django Channels setup | 1d | - |
| PlacementConsumer (WebSocket) | 2d | Channels |
| Frontend WebSocket client | 2d | Consumer |
| 3D view real-time refresh | 1d | WebSocket |
| Push notification service (FCM) | 2d | - |
| Tablet push integration | 1d | FCM |

**Deliverable:** All clients update in real-time

---

### Phase 4: Verification System (1-2 weeks)

**Goal:** Photo verification with optional AI

| Task | Effort | Dependencies |
|------|--------|--------------|
| Photo upload API | 1d | Phase 2 |
| S3/MinIO integration | 1d | - |
| Manual verification UI | 2d | Photo API |
| AI OCR integration (optional) | 3d | Photo API |
| Verification dashboard | 2d | All above |

**Deliverable:** Photos captured and reviewed for verification

---

### Phase 5: Analytics & Polish (1-2 weeks)

**Goal:** Performance tracking and UX improvements

| Task | Effort | Dependencies |
|------|--------|--------------|
| SLA tracking service | 2d | Phase 1 |
| Manager performance dashboard | 2d | SLA service |
| Zone utilization reports | 2d | - |
| Audit log viewer | 1d | - |
| UX refinements | 2d | All phases |
| Documentation | 1d | - |

**Deliverable:** Complete system with analytics

---

### Timeline Summary

```
Week 1-2:   [████████████████] Phase 1: Foundation (Backend)
Week 3-4:   [████████████████] Phase 2: Telegram Mini App Extension
Week 5:     [████████]         Phase 3: Real-time Updates
Week 6:     [████████]         Phase 4: Verification
Week 7:     [████████]         Phase 5: Analytics & Polish

Total: 6-8 weeks for full implementation
MVP (Phases 1-2): 3-4 weeks
```

### Technology Stack Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TECHNOLOGY DECISIONS (FINAL)                         │
└─────────────────────────────────────────────────────────────────────────────┘

  CONTROL ROOM (Desktop)              YARD MANAGER (Tablet/Phone)
  ══════════════════════              ══════════════════════════

  ┌─────────────────────┐             ┌─────────────────────┐
  │  Vue 3 + TypeScript │             │  TELEGRAM MINI APP  │
  │  + Three.js         │             │  (React + TypeScript)│
  ├─────────────────────┤             ├─────────────────────┤
  │  3D Visualization   │             │  2D Grid + Side View│
  │  Full terminal view │             │  Simple, worker-UX  │
  │  Complex interaction│             │  Large touch targets│
  ├─────────────────────┤             ├─────────────────────┤
  │  Desktop browser    │             │  Telegram app       │
  │  Air-conditioned    │             │  (already installed)│
  │  Multi-monitor      │             │  Auto-login, no pwd │
  └─────────────────────┘             └─────────────────────┘

  WHY TELEGRAM MINI APP:
  ──────────────────────
  ✅ Full WiFi coverage → no offline complexity needed
  ✅ Extends existing telegram-miniapp/ (React + TypeScript)
  ✅ Same tech stack → same team maintains
  ✅ Workers already use Telegram daily
  ✅ No app store deployment → instant updates
  ✅ Auto-login via Telegram → no passwords
  ✅ Push notifications → Telegram handles it
  ✅ Camera already works → reuse existing code
```

---

## 12. Best Practices & Standards

### TOS Industry Standards Applied

| Standard | Implementation |
|----------|----------------|
| **ISO 6346** | Container number validation, size prefixes |
| **ISO 668** | Container dimensions for 3D rendering |
| **BAPLIE/COPARN** | Data format compatible with shipping lines |
| **Work Order Flow** | NAVIS N4-style state machine |
| **Position Coding** | Zone-Row-Bay-Tier format (industry standard) |
| **Segregation Rules** | 40ft/20ft row separation |
| **Stacking Rules** | Weight distribution, support requirements |

### Security Considerations

| Concern | Mitigation |
|---------|------------|
| Work order tampering | Audit log, immutable history |
| Photo spoofing | GPS metadata, timestamp verification |
| Unauthorized access | JWT auth, role-based permissions |
| Offline conflicts | Server timestamp wins, user notified |
| Data loss | Transaction-safe operations |

### Performance Requirements

| Metric | Target |
|--------|--------|
| API response time | < 200ms (p95) |
| WebSocket latency | < 100ms |
| Photo upload | < 5 seconds |
| 3D view FPS | 60 FPS |
| Offline queue size | 100 orders |
| Concurrent managers | 50 |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Bay** | Column position in yard (X direction) |
| **Row** | Row position in yard (Z direction) |
| **Tier** | Stacking level (Y direction, 1=ground) |
| **Sub-slot** | A or B for 20ft containers in 40ft bay |
| **Work Order** | Task to place/move/retrieve container |
| **SLA** | Service Level Agreement (time target) |
| **CHE** | Container Handling Equipment (crane, reach stacker) |
| **OCR** | Optical Character Recognition |
| **PWA** | Progressive Web App |
| **FCM** | Firebase Cloud Messaging |

---

## Appendix B: Reference Links

- [NAVIS N4 TOS](https://www.navis.com/en/products/n4)
- [Tideworks TOS](https://www.tideworks.com/)
- [ISO 6346 Container Codes](https://en.wikipedia.org/wiki/ISO_6346)
- [Django Channels](https://channels.readthedocs.io/)
- [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)

---

*Document Version: 1.0*
*Last Updated: January 2024*
*Author: MTT Development Team*
