# Telegram Mini App: Placement Feature Extension

> **Design Document** | Version 1.0 | January 2026
>
> Extends the existing `telegram-miniapp/` React application with container placement visualization and work order management for yard managers.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [New Files Structure](#3-new-files-structure)
4. [TypeScript Types](#4-typescript-types)
5. [Context & Hooks](#5-context--hooks)
6. [Page Components](#6-page-components)
7. [Reusable Components](#7-reusable-components)
8. [API Integration](#8-api-integration)
9. [Real-time Updates](#9-real-time-updates)
10. [Worker UX Guidelines](#10-worker-ux-guidelines)
11. [Implementation Phases](#11-implementation-phases)

---

## 1. Overview

### Purpose
Add container placement functionality to the existing Telegram Mini App, enabling yard managers to:
- Receive placement work orders
- View 2D visualization of target location
- Navigate to placement position
- Confirm placement with photo verification

### Technology Decision
| Aspect | Choice | Rationale |
|--------|--------|-----------|
| Platform | Telegram Mini App | Full WiFi in yard, same team maintains, workers use Telegram daily |
| Visualization | 2D Canvas | Glanceable, fast, no WebGL needed |
| State | React Context + Hooks | Matches existing architecture |
| Real-time | WebSocket | Django Channels on backend |

### Key Features
```
┌─────────────────────────────────────────────────────────────┐
│                   PLACEMENT WORKFLOW                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ① WORK ORDERS      ② DETAIL VIEW       ③ CONFIRMATION     │
│  ─────────────      ─────────────       ──────────────      │
│  ┌──────────┐      ┌──────────────┐     ┌────────────┐     │
│  │ 📦 ABC123│      │  ZONE A-03   │     │ 📷 Photo   │     │
│  │ Zone A-03│  →   │ ┌──────────┐ │  →  │ ☑ Checklist│     │
│  │ 15:30    │      │ │ 2D Grid  │ │     │ ✓ Confirm  │     │
│  │ ────────│      │ │ + Side   │ │     │            │     │
│  │ 📦 DEF456│      │ │   View   │ │     └────────────┘     │
│  │ Zone B-12│      │ └──────────┘ │                         │
│  └──────────┘      └──────────────┘                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture

### Component Hierarchy
```
App.tsx
├── CameraProvider (existing)
├── PageProvider (existing)
├── PlacementProvider (🆕 NEW)
│   └── WebSocket connection
│
└── Layout.tsx
    ├── IndexPage (existing)
    ├── VehiclesPage (existing)
    ├── CameraPage (existing)
    │
    └── 🆕 PLACEMENT PAGES
        ├── WorkOrdersPage
        │   └── WorkOrderCard[]
        │
        ├── PlacementDetailPage
        │   ├── YardGrid (2D top-down)
        │   ├── RowSideView (tier visualization)
        │   └── PlacementInfo
        │
        └── PlacementConfirmPage
            ├── CameraOverlay (existing, reused)
            ├── PlacementChecklist
            └── ConfirmButton
```

### State Flow
```
                    ┌─────────────────┐
                    │ PlacementContext│
                    │                 │
                    │ - workOrders[]  │
                    │ - activeOrder   │
                    │ - wsConnection  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ WorkOrdersPage  │ │PlacementDetail  │ │PlacementConfirm │
│                 │ │                 │ │                 │
│ Lists orders    │ │ Shows location  │ │ Photo + verify  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## 3. New Files Structure

```
telegram-miniapp/src/
├── contexts/
│   ├── CameraContext.tsx         # ✅ EXISTS
│   ├── PageContext.tsx           # ✅ EXISTS
│   └── PlacementContext.tsx      # 🆕 NEW - Work orders + WebSocket
│
├── hooks/
│   ├── useCameraCapture.ts       # ✅ EXISTS
│   ├── usePlateRecognition.ts    # ✅ EXISTS
│   ├── useWorkOrders.ts          # 🆕 NEW - Fetch/update work orders
│   ├── useYardLayout.ts          # 🆕 NEW - Yard grid data
│   └── usePlacementWebSocket.ts  # 🆕 NEW - Real-time updates
│
├── pages/
│   ├── IndexPage/                # ✅ EXISTS
│   ├── VehiclesPage/             # ✅ EXISTS
│   ├── CameraPage/               # ✅ EXISTS
│   │
│   ├── WorkOrdersPage/           # 🆕 NEW
│   │   ├── WorkOrdersPage.tsx
│   │   └── index.ts
│   │
│   ├── PlacementDetailPage/      # 🆕 NEW
│   │   ├── PlacementDetailPage.tsx
│   │   └── index.ts
│   │
│   └── PlacementConfirmPage/     # 🆕 NEW
│       ├── PlacementConfirmPage.tsx
│       └── index.ts
│
├── components/
│   ├── CameraOverlay/            # ✅ EXISTS (reuse for photo)
│   │
│   └── placement/                # 🆕 NEW - All placement components
│       ├── YardGrid.tsx          # 2D top-down grid (Canvas)
│       ├── RowSideView.tsx       # Side view for tier height
│       ├── WorkOrderCard.tsx     # Single work order display
│       ├── PlacementInfo.tsx     # Container + location details
│       ├── PlacementChecklist.tsx # Verification checklist
│       ├── CountdownTimer.tsx    # SLA countdown
│       └── index.ts              # Barrel export
│
├── types/
│   ├── api.ts                    # ✅ EXISTS
│   └── placement.ts              # 🆕 NEW - Placement types
│
├── config/
│   └── api.ts                    # ✅ EXISTS (add placement endpoints)
│
└── navigation/
    └── routes.tsx                # ✅ EXISTS (add placement routes)
```

---

## 4. TypeScript Types

### File: `src/types/placement.ts`

```typescript
// ============================================================
// WORK ORDER TYPES
// ============================================================

export type WorkOrderStatus =
  | 'PENDING'      // Created, not assigned
  | 'ASSIGNED'     // Assigned to manager
  | 'ACCEPTED'     // Manager accepted
  | 'IN_PROGRESS'  // Manager navigating/placing
  | 'COMPLETED'    // Placed, awaiting verification
  | 'VERIFIED'     // System confirmed placement
  | 'FAILED';      // Placement incorrect

export type WorkOrderPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

export interface WorkOrder {
  id: number;
  order_number: string;
  status: WorkOrderStatus;
  priority: WorkOrderPriority;

  // Container info
  container: {
    id: number;
    number: string;            // e.g., "MSCU1234567"
    size: '20' | '40' | '45';
    load_status: 'LADEN' | 'EMPTY';
    weight_kg: number | null;
  };

  // Target location
  target_location: PlacementLocation;

  // Timing
  created_at: string;
  assigned_at: string | null;
  accepted_at: string | null;
  completed_at: string | null;
  sla_deadline: string;        // ISO datetime

  // Assigned manager
  assigned_to: {
    id: number;
    name: string;
  } | null;

  // Verification
  placement_photo: string | null;
  verification_status: 'PENDING' | 'CORRECT' | 'INCORRECT' | null;
  verification_notes: string | null;
}

// ============================================================
// LOCATION TYPES
// ============================================================

export interface PlacementLocation {
  zone: string;           // e.g., "A"
  row: number;            // e.g., 3
  bay: number;            // e.g., 12
  tier: number;           // e.g., 2 (height level)
  sub_slot?: 'FORE' | 'AFT';  // For 20ft in 40ft slot

  // Computed display
  display_code: string;   // e.g., "A-03-12-2"
}

export interface YardZone {
  code: string;           // e.g., "A"
  name: string;           // e.g., "Зона А"
  rows: number;           // Total rows in zone
  bays_per_row: number;   // Bays per row
  max_tiers: number;      // Max stacking height

  // Grid position (for rendering)
  grid_x: number;
  grid_y: number;
  width: number;
  height: number;
}

export interface YardRow {
  zone: string;
  row_number: number;
  bays: YardBay[];
}

export interface YardBay {
  bay_number: number;
  slots: YardSlot[];
}

export interface YardSlot {
  tier: number;
  sub_slot: 'FORE' | 'AFT' | 'FULL';

  // Container in this slot (if any)
  container: {
    number: string;
    size: '20' | '40' | '45';
    load_status: 'LADEN' | 'EMPTY';
  } | null;

  // Visual state
  is_target: boolean;      // Highlight as placement target
  is_blocked: boolean;     // Cannot place here
}

// ============================================================
// YARD LAYOUT (FULL GRID)
// ============================================================

export interface YardLayout {
  zones: YardZone[];
  last_updated: string;
}

// ============================================================
// API RESPONSE TYPES
// ============================================================

export interface WorkOrdersResponse {
  success: boolean;
  data: {
    results: WorkOrder[];
    count: number;
    next: string | null;
    previous: string | null;
  };
}

export interface WorkOrderDetailResponse {
  success: boolean;
  data: WorkOrder;
}

export interface YardLayoutResponse {
  success: boolean;
  data: YardLayout;
}

export interface RowDetailResponse {
  success: boolean;
  data: YardRow;
}

// ============================================================
// WEBSOCKET MESSAGE TYPES
// ============================================================

export type WSMessageType =
  | 'work_order_assigned'
  | 'work_order_updated'
  | 'placement_verified'
  | 'slot_changed';

export interface WSMessage {
  type: WSMessageType;
  payload: WorkOrder | YardSlot;
  timestamp: string;
}
```

---

## 5. Context & Hooks

### PlacementContext

**File: `src/contexts/PlacementContext.tsx`**

```tsx
import type { FC, ReactNode } from 'react';
import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import type { WorkOrder, WSMessage } from '@/types/placement';
import { Toast } from 'antd-mobile';

interface PlacementContextType {
  // Work orders
  workOrders: WorkOrder[];
  activeOrder: WorkOrder | null;
  setActiveOrder: (order: WorkOrder | null) => void;

  // Actions
  acceptOrder: (orderId: number) => Promise<void>;
  startPlacement: (orderId: number) => Promise<void>;
  completePlacement: (orderId: number, photoBase64: string) => Promise<void>;

  // WebSocket
  isConnected: boolean;

  // Loading states
  isLoading: boolean;
  refreshOrders: () => Promise<void>;
}

const PlacementContext = createContext<PlacementContextType | null>(null);

export const usePlacement = (): PlacementContextType => {
  const context = useContext(PlacementContext);
  if (!context) {
    throw new Error('usePlacement must be used within PlacementProvider');
  }
  return context;
};

interface Props {
  children: ReactNode;
}

export const PlacementProvider: FC<Props> = ({ children }) => {
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [activeOrder, setActiveOrder] = useState<WorkOrder | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);

  // Fetch work orders
  const refreshOrders = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/placement/work-orders/?status=ASSIGNED,ACCEPTED,IN_PROGRESS');
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setWorkOrders(data.data.results);
    } catch (error) {
      console.error('Failed to fetch work orders:', error);
      Toast.show({ icon: 'fail', content: 'Буюртмаларни юклаб бўлмади' });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Accept work order
  const acceptOrder = useCallback(async (orderId: number): Promise<void> => {
    try {
      const response = await fetch(`/api/placement/work-orders/${orderId}/accept/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) throw new Error('Failed to accept');

      Toast.show({ icon: 'success', content: 'Буюртма қабул қилинди' });
      await refreshOrders();
    } catch (error) {
      console.error('Failed to accept order:', error);
      Toast.show({ icon: 'fail', content: 'Қабул қилиб бўлмади' });
      throw error;
    }
  }, [refreshOrders]);

  // Start placement (navigate to location)
  const startPlacement = useCallback(async (orderId: number): Promise<void> => {
    try {
      const response = await fetch(`/api/placement/work-orders/${orderId}/start/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) throw new Error('Failed to start');

      await refreshOrders();
    } catch (error) {
      console.error('Failed to start placement:', error);
      throw error;
    }
  }, [refreshOrders]);

  // Complete placement with photo
  const completePlacement = useCallback(async (
    orderId: number,
    photoBase64: string
  ): Promise<void> => {
    try {
      // Convert base64 to blob
      const blob = await fetch(photoBase64).then(r => r.blob());

      const formData = new FormData();
      formData.append('placement_photo', blob, 'placement.jpg');

      const response = await fetch(`/api/placement/work-orders/${orderId}/complete/`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Failed to complete');

      Toast.show({ icon: 'success', content: 'Жойлаш тасдиқланди' });
      setActiveOrder(null);
      await refreshOrders();
    } catch (error) {
      console.error('Failed to complete placement:', error);
      Toast.show({ icon: 'fail', content: 'Тасдиқлаб бўлмади' });
      throw error;
    }
  }, [refreshOrders]);

  // WebSocket connection
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/placement/`;

    const connect = (): void => {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        // Reconnect after 3 seconds
        setTimeout(connect, 3000);
      };

      wsRef.current.onmessage = (event) => {
        const message: WSMessage = JSON.parse(event.data);
        handleWSMessage(message);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    };

    const handleWSMessage = (message: WSMessage): void => {
      switch (message.type) {
        case 'work_order_assigned':
          // New order assigned - show notification and refresh
          Toast.show({
            icon: 'success',
            content: 'Янги буюртма!'
          });
          refreshOrders();
          break;

        case 'work_order_updated':
          // Order status changed - refresh
          refreshOrders();
          break;

        case 'placement_verified':
          // Placement was verified by system
          const order = message.payload as WorkOrder;
          if (order.verification_status === 'CORRECT') {
            Toast.show({ icon: 'success', content: 'Жойлаш тасдиқланди ✓' });
          } else {
            Toast.show({ icon: 'fail', content: 'Жойлаш нотўғри!' });
          }
          refreshOrders();
          break;
      }
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [refreshOrders]);

  // Initial fetch
  useEffect(() => {
    refreshOrders();
  }, [refreshOrders]);

  return (
    <PlacementContext.Provider
      value={{
        workOrders,
        activeOrder,
        setActiveOrder,
        acceptOrder,
        startPlacement,
        completePlacement,
        isConnected,
        isLoading,
        refreshOrders,
      }}
    >
      {children}
    </PlacementContext.Provider>
  );
};
```

### useYardLayout Hook

**File: `src/hooks/useYardLayout.ts`**

```tsx
import { useState, useEffect, useCallback } from 'react';
import type { YardLayout, YardRow } from '@/types/placement';
import { Toast } from 'antd-mobile';

interface UseYardLayoutReturn {
  layout: YardLayout | null;
  isLoading: boolean;
  error: string | null;

  // Fetch specific row with all tiers
  fetchRow: (zone: string, row: number) => Promise<YardRow | null>;

  // Refresh full layout
  refresh: () => Promise<void>;
}

export const useYardLayout = (): UseYardLayoutReturn => {
  const [layout, setLayout] = useState<YardLayout | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLayout = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/placement/yard-layout/');
      if (!response.ok) throw new Error('Failed to fetch layout');

      const data = await response.json();
      setLayout(data.data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      Toast.show({ icon: 'fail', content: 'Майдон схемасини юклаб бўлмади' });
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchRow = useCallback(async (
    zone: string,
    row: number
  ): Promise<YardRow | null> => {
    try {
      const response = await fetch(`/api/placement/yard-layout/${zone}/${row}/`);
      if (!response.ok) throw new Error('Failed to fetch row');

      const data = await response.json();
      return data.data;
    } catch (err) {
      console.error('Failed to fetch row:', err);
      return null;
    }
  }, []);

  useEffect(() => {
    fetchLayout();
  }, [fetchLayout]);

  return {
    layout,
    isLoading,
    error,
    fetchRow,
    refresh: fetchLayout,
  };
};
```

---

## 6. Page Components

### WorkOrdersPage

**File: `src/pages/WorkOrdersPage/WorkOrdersPage.tsx`**

```tsx
import type { FC } from 'react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Page } from '@/components/Page';
import { Space, PullToRefresh, Empty, DotLoading } from 'antd-mobile';
import { usePlacement } from '@/contexts/PlacementContext';
import { WorkOrderCard } from '@/components/placement';
import { Wifi, WifiOff } from 'lucide-react';

export const WorkOrdersPage: FC = () => {
  const navigate = useNavigate();
  const {
    workOrders,
    isLoading,
    isConnected,
    refreshOrders,
    acceptOrder,
    setActiveOrder,
  } = usePlacement();

  const handleCardClick = (order: WorkOrder): void => {
    setActiveOrder(order);
    navigate(`/placement/${order.id}`);
  };

  const handleAccept = async (orderId: number): Promise<void> => {
    await acceptOrder(orderId);
  };

  return (
    <Page back={false} title="Жойлаш буюртмалари">
      {/* Connection status indicator */}
      <div
        className="fixed top-16 right-4 z-10 flex items-center gap-1 px-2 py-1 rounded-full text-xs"
        style={{
          backgroundColor: isConnected ? '#e6f7e6' : '#fff0f0',
          color: isConnected ? '#00b578' : '#ff3b30',
        }}
      >
        {isConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
        {isConnected ? 'Онлайн' : 'Офлайн'}
      </div>

      <PullToRefresh onRefresh={refreshOrders}>
        <Space
          direction="vertical"
          block
          style={{ padding: '16px', paddingBottom: '100px' }}
        >
          {isLoading && workOrders.length === 0 ? (
            <div className="flex justify-center py-20">
              <DotLoading color="primary" />
            </div>
          ) : workOrders.length === 0 ? (
            <Empty
              description="Буюртмалар йўқ"
              style={{ padding: '60px 0' }}
            />
          ) : (
            workOrders.map((order) => (
              <WorkOrderCard
                key={order.id}
                order={order}
                onClick={() => handleCardClick(order)}
                onAccept={() => handleAccept(order.id)}
              />
            ))
          )}
        </Space>
      </PullToRefresh>
    </Page>
  );
};
```

### PlacementDetailPage

**File: `src/pages/PlacementDetailPage/PlacementDetailPage.tsx`**

```tsx
import type { FC } from 'react';
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Page } from '@/components/Page';
import { Card, Button, Space, DotLoading, Toast } from 'antd-mobile';
import { usePlacement } from '@/contexts/PlacementContext';
import { useYardLayout } from '@/hooks/useYardLayout';
import {
  YardGrid,
  RowSideView,
  PlacementInfo,
  CountdownTimer,
} from '@/components/placement';
import type { YardRow, WorkOrder } from '@/types/placement';
import { Navigation, Camera } from 'lucide-react';

export const PlacementDetailPage: FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { activeOrder, setActiveOrder, startPlacement, workOrders } = usePlacement();
  const { layout, fetchRow } = useYardLayout();

  const [rowDetail, setRowDetail] = useState<YardRow | null>(null);
  const [isStarting, setIsStarting] = useState(false);

  // Find order if not set (direct navigation)
  useEffect(() => {
    if (!activeOrder && id) {
      const order = workOrders.find(o => o.id === parseInt(id, 10));
      if (order) {
        setActiveOrder(order);
      } else {
        // Fetch from API if not in local state
        fetch(`/api/placement/work-orders/${id}/`)
          .then(r => r.json())
          .then(data => setActiveOrder(data.data))
          .catch(() => {
            Toast.show({ icon: 'fail', content: 'Буюртма топилмади' });
            navigate('/work-orders');
          });
      }
    }
  }, [id, activeOrder, workOrders, setActiveOrder, navigate]);

  // Fetch row detail for side view
  useEffect(() => {
    if (activeOrder) {
      const { zone, row } = activeOrder.target_location;
      fetchRow(zone, row).then(setRowDetail);
    }
  }, [activeOrder, fetchRow]);

  const handleStartNavigation = async (): Promise<void> => {
    if (!activeOrder) return;

    setIsStarting(true);
    try {
      await startPlacement(activeOrder.id);
      Toast.show({ icon: 'success', content: 'Жойга боринг' });
    } catch {
      // Error handled in context
    } finally {
      setIsStarting(false);
    }
  };

  const handleConfirm = (): void => {
    if (!activeOrder) return;
    navigate(`/placement/${activeOrder.id}/confirm`);
  };

  if (!activeOrder) {
    return (
      <Page back={true} title="Жойлаш">
        <div className="flex justify-center py-20">
          <DotLoading color="primary" />
        </div>
      </Page>
    );
  }

  const canStart = activeOrder.status === 'ACCEPTED';
  const canConfirm = activeOrder.status === 'IN_PROGRESS';

  return (
    <Page back={true} title={`Буюртма #${activeOrder.order_number}`}>
      <Space
        direction="vertical"
        block
        style={{ padding: '16px', paddingBottom: '120px' }}
      >
        {/* Countdown Timer */}
        <CountdownTimer deadline={activeOrder.sla_deadline} />

        {/* Container Info */}
        <PlacementInfo order={activeOrder} />

        {/* 2D Yard Grid - Top Down View */}
        <Card title="Майдон схемаси">
          {layout ? (
            <YardGrid
              layout={layout}
              targetLocation={activeOrder.target_location}
              height={200}
            />
          ) : (
            <div className="flex justify-center py-8">
              <DotLoading />
            </div>
          )}
        </Card>

        {/* Side View - Tier Heights */}
        <Card title="Қатор кўриниши (ён томондан)">
          {rowDetail ? (
            <RowSideView
              row={rowDetail}
              targetBay={activeOrder.target_location.bay}
              targetTier={activeOrder.target_location.tier}
              height={150}
            />
          ) : (
            <div className="flex justify-center py-8">
              <DotLoading />
            </div>
          )}
        </Card>

        {/* Action Buttons - Large for workers */}
        <Space direction="vertical" block style={{ marginTop: '16px' }}>
          {canStart && (
            <Button
              block
              color="primary"
              size="large"
              loading={isStarting}
              onClick={handleStartNavigation}
              style={{
                height: '64px',
                fontSize: '18px',
                borderRadius: '12px',
              }}
            >
              <Space align="center">
                <Navigation size={24} />
                <span>Жойга бориш</span>
              </Space>
            </Button>
          )}

          {canConfirm && (
            <Button
              block
              color="success"
              size="large"
              onClick={handleConfirm}
              style={{
                height: '64px',
                fontSize: '18px',
                borderRadius: '12px',
              }}
            >
              <Space align="center">
                <Camera size={24} />
                <span>Тасдиқлаш</span>
              </Space>
            </Button>
          )}
        </Space>
      </Space>
    </Page>
  );
};
```

### PlacementConfirmPage

**File: `src/pages/PlacementConfirmPage/PlacementConfirmPage.tsx`**

```tsx
import type { FC } from 'react';
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Page } from '@/components/Page';
import { Card, Button, Space, Image, Dialog, Toast } from 'antd-mobile';
import { usePlacement } from '@/contexts/PlacementContext';
import { useCameraCapture } from '@/hooks/useCameraCapture';
import { CameraOverlay } from '@/components/CameraOverlay';
import { PlacementChecklist } from '@/components/placement';
import { Camera, Check, RotateCcw } from 'lucide-react';

export const PlacementConfirmPage: FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { activeOrder, completePlacement } = usePlacement();
  const { videoRef, canvasRef, initializeCamera, capturePhoto, stopCamera } = useCameraCapture();

  const [showCamera, setShowCamera] = useState(false);
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null);
  const [checklistComplete, setChecklistComplete] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleOpenCamera = async (): Promise<void> => {
    const success = await initializeCamera();
    if (success) {
      setShowCamera(true);
    } else {
      Toast.show({ icon: 'fail', content: 'Камерани очиб бўлмади' });
    }
  };

  const handleCapture = (): void => {
    const photo = capturePhoto(0.8, 1280, 720);
    if (photo) {
      setCapturedPhoto(photo);
      setShowCamera(false);
      stopCamera();
    }
  };

  const handleRetake = (): void => {
    setCapturedPhoto(null);
    handleOpenCamera();
  };

  const handleSubmit = async (): Promise<void> => {
    if (!activeOrder || !capturedPhoto || !checklistComplete) return;

    // Confirmation dialog
    const confirmed = await Dialog.confirm({
      title: 'Тасдиқлаш',
      content: 'Контейнер тўғри жойлаштирилганини тасдиқлайсизми?',
      confirmText: 'Ҳа',
      cancelText: 'Йўқ',
    });

    if (!confirmed) return;

    setIsSubmitting(true);
    try {
      await completePlacement(activeOrder.id, capturedPhoto);
      navigate('/work-orders');
    } catch {
      // Error handled in context
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!activeOrder) {
    navigate('/work-orders');
    return null;
  }

  // Camera overlay (full screen)
  if (showCamera) {
    return (
      <CameraOverlay
        videoRef={videoRef}
        canvasRef={canvasRef}
        onCapture={handleCapture}
        onCancel={() => {
          setShowCamera(false);
          stopCamera();
        }}
      />
    );
  }

  const canSubmit = capturedPhoto && checklistComplete;

  return (
    <Page back={true} title="Жойлашни тасдиқлаш">
      <Space
        direction="vertical"
        block
        style={{ padding: '16px', paddingBottom: '120px' }}
      >
        {/* Location reminder */}
        <Card>
          <div className="text-center">
            <div className="text-lg font-bold text-primary">
              {activeOrder.target_location.display_code}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              {activeOrder.container.number}
            </div>
          </div>
        </Card>

        {/* Photo capture */}
        <Card title="Расм">
          {capturedPhoto ? (
            <Space direction="vertical" block>
              <Image
                src={capturedPhoto}
                fit="cover"
                style={{
                  width: '100%',
                  height: '200px',
                  borderRadius: '8px',
                }}
              />
              <Button
                block
                fill="outline"
                onClick={handleRetake}
                style={{ height: '48px' }}
              >
                <Space align="center">
                  <RotateCcw size={18} />
                  <span>Қайта олиш</span>
                </Space>
              </Button>
            </Space>
          ) : (
            <Button
              block
              color="primary"
              onClick={handleOpenCamera}
              style={{
                height: '80px',
                fontSize: '16px',
                borderRadius: '12px',
              }}
            >
              <Space direction="vertical" align="center">
                <Camera size={32} />
                <span>Расм олиш</span>
              </Space>
            </Button>
          )}
        </Card>

        {/* Checklist */}
        <Card title="Текшириш рўйхати">
          <PlacementChecklist
            onChange={setChecklistComplete}
            containerSize={activeOrder.container.size}
          />
        </Card>

        {/* Submit button */}
        <Button
          block
          color="success"
          size="large"
          disabled={!canSubmit}
          loading={isSubmitting}
          onClick={handleSubmit}
          style={{
            height: '64px',
            fontSize: '18px',
            borderRadius: '12px',
            marginTop: '16px',
          }}
        >
          <Space align="center">
            <Check size={24} />
            <span>Тасдиқлаш</span>
          </Space>
        </Button>
      </Space>
    </Page>
  );
};
```

---

## 7. Reusable Components

### YardGrid (2D Top-Down View)

**File: `src/components/placement/YardGrid.tsx`**

```tsx
import type { FC } from 'react';
import { useRef, useEffect } from 'react';
import type { YardLayout, PlacementLocation, YardZone } from '@/types/placement';

interface Props {
  layout: YardLayout;
  targetLocation: PlacementLocation;
  height?: number;
}

// Color scheme for worker visibility
const COLORS = {
  zone: '#f0f0f0',
  zoneBorder: '#d9d9d9',
  target: '#52c41a',       // Green - target zone
  targetGlow: '#95de64',
  row: '#1890ff',          // Blue - current row
  text: '#333333',
  highlight: '#ff4d4f',    // Red - attention
};

export const YardGrid: FC<Props> = ({ layout, targetLocation, height = 200 }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Get device pixel ratio for sharp rendering
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    // Clear canvas
    ctx.clearRect(0, 0, rect.width, rect.height);

    // Calculate grid dimensions
    const padding = 20;
    const gridWidth = rect.width - padding * 2;
    const gridHeight = rect.height - padding * 2;

    // Find bounds of all zones
    const maxX = Math.max(...layout.zones.map(z => z.grid_x + z.width));
    const maxY = Math.max(...layout.zones.map(z => z.grid_y + z.height));

    const scaleX = gridWidth / maxX;
    const scaleY = gridHeight / maxY;
    const scale = Math.min(scaleX, scaleY);

    // Draw zones
    layout.zones.forEach((zone) => {
      const x = padding + zone.grid_x * scale;
      const y = padding + zone.grid_y * scale;
      const w = zone.width * scale;
      const h = zone.height * scale;

      const isTarget = zone.code === targetLocation.zone;

      // Zone background
      ctx.fillStyle = isTarget ? COLORS.targetGlow : COLORS.zone;
      ctx.fillRect(x, y, w, h);

      // Zone border
      ctx.strokeStyle = isTarget ? COLORS.target : COLORS.zoneBorder;
      ctx.lineWidth = isTarget ? 3 : 1;
      ctx.strokeRect(x, y, w, h);

      // Zone label (large, centered)
      ctx.fillStyle = isTarget ? COLORS.target : COLORS.text;
      ctx.font = isTarget ? 'bold 24px sans-serif' : '18px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(zone.code, x + w / 2, y + h / 2);

      // If target zone, show row indicator
      if (isTarget) {
        const rowHeight = h / zone.rows;
        const rowY = y + (targetLocation.row - 1) * rowHeight;

        // Highlight target row
        ctx.fillStyle = 'rgba(24, 144, 255, 0.3)';
        ctx.fillRect(x + 2, rowY, w - 4, rowHeight);

        // Row number
        ctx.fillStyle = COLORS.row;
        ctx.font = 'bold 14px sans-serif';
        ctx.fillText(
          `Қатор ${targetLocation.row}`,
          x + w / 2,
          rowY + rowHeight / 2
        );
      }
    });

    // Draw location code at bottom
    ctx.fillStyle = COLORS.target;
    ctx.font = 'bold 16px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(
      targetLocation.display_code,
      rect.width / 2,
      rect.height - 5
    );

  }, [layout, targetLocation]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: '100%',
        height: `${height}px`,
        display: 'block',
      }}
    />
  );
};
```

### RowSideView (Tier Visualization)

**File: `src/components/placement/RowSideView.tsx`**

```tsx
import type { FC } from 'react';
import { useRef, useEffect } from 'react';
import type { YardRow } from '@/types/placement';

interface Props {
  row: YardRow;
  targetBay: number;
  targetTier: number;
  height?: number;
}

const COLORS = {
  container_laden: '#1890ff',   // Blue - loaded
  container_empty: '#91d5ff',   // Light blue - empty
  target: '#52c41a',            // Green - target slot
  targetBorder: '#237804',
  blocked: '#ff4d4f',           // Red - cannot place
  slot: '#f5f5f5',
  slotBorder: '#d9d9d9',
  ground: '#8c8c8c',
  text: '#333333',
};

export const RowSideView: FC<Props> = ({ row, targetBay, targetTier, height = 150 }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, rect.width, rect.height);

    const padding = { top: 20, bottom: 30, left: 40, right: 20 };
    const gridWidth = rect.width - padding.left - padding.right;
    const gridHeight = rect.height - padding.top - padding.bottom;

    const bays = row.bays;
    const maxTiers = Math.max(...bays.flatMap(b => b.slots.map(s => s.tier)), 5);

    const bayWidth = gridWidth / bays.length;
    const tierHeight = gridHeight / maxTiers;

    // Draw ground line
    ctx.strokeStyle = COLORS.ground;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding.left, rect.height - padding.bottom);
    ctx.lineTo(rect.width - padding.right, rect.height - padding.bottom);
    ctx.stroke();

    // Draw each bay
    bays.forEach((bay, bayIndex) => {
      const bayX = padding.left + bayIndex * bayWidth;

      // Bay number label
      ctx.fillStyle = bay.bay_number === targetBay ? COLORS.target : COLORS.text;
      ctx.font = bay.bay_number === targetBay ? 'bold 12px sans-serif' : '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(
        String(bay.bay_number),
        bayX + bayWidth / 2,
        rect.height - padding.bottom + 15
      );

      // Draw slots (tiers)
      bay.slots.forEach((slot) => {
        const slotX = bayX + 4;
        const slotY = rect.height - padding.bottom - slot.tier * tierHeight;
        const slotWidth = bayWidth - 8;
        const slotHeight = tierHeight - 4;

        const isTarget = bay.bay_number === targetBay && slot.tier === targetTier;

        // Slot background
        if (slot.container) {
          // Container present
          ctx.fillStyle = slot.container.load_status === 'LADEN'
            ? COLORS.container_laden
            : COLORS.container_empty;
        } else if (isTarget) {
          // Target slot (empty)
          ctx.fillStyle = COLORS.target;
        } else if (slot.is_blocked) {
          ctx.fillStyle = COLORS.blocked;
        } else {
          ctx.fillStyle = COLORS.slot;
        }

        // Draw slot rectangle
        ctx.fillRect(slotX, slotY, slotWidth, slotHeight);

        // Border
        ctx.strokeStyle = isTarget ? COLORS.targetBorder : COLORS.slotBorder;
        ctx.lineWidth = isTarget ? 3 : 1;
        ctx.strokeRect(slotX, slotY, slotWidth, slotHeight);

        // Container number (if present)
        if (slot.container) {
          ctx.fillStyle = '#ffffff';
          ctx.font = '9px sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          // Show last 4 digits
          const shortNum = slot.container.number.slice(-4);
          ctx.fillText(shortNum, slotX + slotWidth / 2, slotY + slotHeight / 2);
        }

        // Target indicator
        if (isTarget && !slot.container) {
          ctx.fillStyle = COLORS.targetBorder;
          ctx.font = 'bold 14px sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText('▼', slotX + slotWidth / 2, slotY + slotHeight / 2);
        }
      });
    });

    // Tier labels on left
    for (let tier = 1; tier <= maxTiers; tier++) {
      const y = rect.height - padding.bottom - tier * tierHeight + tierHeight / 2;
      ctx.fillStyle = tier === targetTier ? COLORS.target : COLORS.text;
      ctx.font = tier === targetTier ? 'bold 11px sans-serif' : '10px sans-serif';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(`T${tier}`, padding.left - 8, y);
    }

  }, [row, targetBay, targetTier]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: '100%',
        height: `${height}px`,
        display: 'block',
      }}
    />
  );
};
```

### WorkOrderCard

**File: `src/components/placement/WorkOrderCard.tsx`**

```tsx
import type { FC } from 'react';
import { Card, Tag, Button, Space } from 'antd-mobile';
import type { WorkOrder } from '@/types/placement';
import { Package, MapPin, Clock, AlertTriangle } from 'lucide-react';

interface Props {
  order: WorkOrder;
  onClick: () => void;
  onAccept?: () => void;
}

const STATUS_CONFIG: Record<string, { color: string; text: string }> = {
  PENDING: { color: '#faad14', text: 'Кутилмоқда' },
  ASSIGNED: { color: '#1890ff', text: 'Тайинланган' },
  ACCEPTED: { color: '#52c41a', text: 'Қабул қилинган' },
  IN_PROGRESS: { color: '#722ed1', text: 'Бажарилмоқда' },
  COMPLETED: { color: '#13c2c2', text: 'Тугалланган' },
  VERIFIED: { color: '#52c41a', text: 'Тасдиқланган' },
  FAILED: { color: '#ff4d4f', text: 'Хато' },
};

const PRIORITY_CONFIG: Record<string, { color: string; icon: boolean }> = {
  LOW: { color: '#8c8c8c', icon: false },
  MEDIUM: { color: '#1890ff', icon: false },
  HIGH: { color: '#faad14', icon: true },
  URGENT: { color: '#ff4d4f', icon: true },
};

export const WorkOrderCard: FC<Props> = ({ order, onClick, onAccept }) => {
  const statusConfig = STATUS_CONFIG[order.status];
  const priorityConfig = PRIORITY_CONFIG[order.priority];

  const isOverdue = new Date(order.sla_deadline) < new Date();
  const showAcceptButton = order.status === 'ASSIGNED' && onAccept;

  return (
    <Card
      onClick={onClick}
      style={{
        borderRadius: '12px',
        borderLeft: `4px solid ${statusConfig.color}`,
      }}
    >
      {/* Header: Container number + Status */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2">
          <Package size={20} color="#1890ff" />
          <span className="font-bold text-lg">{order.container.number}</span>
        </div>
        <Space>
          {priorityConfig.icon && (
            <AlertTriangle size={18} color={priorityConfig.color} />
          )}
          <Tag color={statusConfig.color} fill="outline">
            {statusConfig.text}
          </Tag>
        </Space>
      </div>

      {/* Location */}
      <div className="flex items-center gap-2 mb-2">
        <MapPin size={18} color="#52c41a" />
        <span className="text-base font-medium" style={{ color: '#52c41a' }}>
          {order.target_location.display_code}
        </span>
      </div>

      {/* Container details */}
      <div className="flex gap-2 mb-3">
        <Tag color="#1890ff" fill="outline">
          {order.container.size}ft
        </Tag>
        <Tag
          color={order.container.load_status === 'LADEN' ? '#722ed1' : '#13c2c2'}
          fill="outline"
        >
          {order.container.load_status === 'LADEN' ? 'Юкли' : 'Бўш'}
        </Tag>
      </div>

      {/* Deadline */}
      <div
        className="flex items-center gap-2"
        style={{ color: isOverdue ? '#ff4d4f' : '#8c8c8c' }}
      >
        <Clock size={16} />
        <span className="text-sm">
          {isOverdue ? 'Муддати ўтган!' : formatDeadline(order.sla_deadline)}
        </span>
      </div>

      {/* Accept button */}
      {showAcceptButton && (
        <Button
          block
          color="primary"
          size="large"
          onClick={(e) => {
            e.stopPropagation();
            onAccept();
          }}
          style={{
            marginTop: '12px',
            height: '56px',
            fontSize: '16px',
            borderRadius: '10px',
          }}
        >
          Қабул қилиш
        </Button>
      )}
    </Card>
  );
};

// Format deadline for display
function formatDeadline(deadline: string): string {
  const date = new Date(deadline);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 60) {
    return `${diffMins} дақиқа қолди`;
  }

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) {
    return `${diffHours} соат қолди`;
  }

  return date.toLocaleString('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}
```

### PlacementInfo

**File: `src/components/placement/PlacementInfo.tsx`**

```tsx
import type { FC } from 'react';
import { Card, List, Tag } from 'antd-mobile';
import type { WorkOrder } from '@/types/placement';
import { Package, MapPin, Scale, Box } from 'lucide-react';

interface Props {
  order: WorkOrder;
}

export const PlacementInfo: FC<Props> = ({ order }) => {
  return (
    <Card>
      <List mode="card" style={{ '--border-inner': 'none' } as React.CSSProperties}>
        {/* Container number */}
        <List.Item
          prefix={<Package size={24} color="#1890ff" />}
          description="Контейнер"
        >
          <span className="font-bold text-lg">{order.container.number}</span>
        </List.Item>

        {/* Target location - PROMINENT */}
        <List.Item
          prefix={<MapPin size={24} color="#52c41a" />}
          description="Жой"
        >
          <span
            className="font-bold text-xl"
            style={{ color: '#52c41a' }}
          >
            {order.target_location.display_code}
          </span>
        </List.Item>

        {/* Container size */}
        <List.Item
          prefix={<Box size={24} color="#722ed1" />}
          description="Ўлчами"
        >
          <Tag color="#722ed1" fill="solid" style={{ fontSize: '14px' }}>
            {order.container.size} фут
          </Tag>
        </List.Item>

        {/* Weight (if laden) */}
        {order.container.load_status === 'LADEN' && order.container.weight_kg && (
          <List.Item
            prefix={<Scale size={24} color="#faad14" />}
            description="Оғирлиги"
          >
            {(order.container.weight_kg / 1000).toFixed(1)} тонна
          </List.Item>
        )}
      </List>
    </Card>
  );
};
```

### PlacementChecklist

**File: `src/components/placement/PlacementChecklist.tsx`**

```tsx
import type { FC } from 'react';
import { useState, useEffect } from 'react';
import { Checkbox, Space } from 'antd-mobile';

interface Props {
  onChange: (complete: boolean) => void;
  containerSize: '20' | '40' | '45';
}

interface CheckItem {
  id: string;
  label: string;
  required: boolean;
}

export const PlacementChecklist: FC<Props> = ({ onChange, containerSize }) => {
  const [checked, setChecked] = useState<Set<string>>(new Set());

  const items: CheckItem[] = [
    { id: 'position', label: 'Контейнер тўғри жойда', required: true },
    { id: 'aligned', label: 'Текис туриши текширилган', required: true },
    { id: 'locks', label: 'Қулфлар берк', required: true },
    { id: 'clearance', label: 'Атрофи бўш', required: true },
    ...(containerSize === '20' ? [
      { id: 'subslot', label: '20фт - тўғри томонда (олд/орқа)', required: true },
    ] : []),
  ];

  const requiredItems = items.filter(i => i.required);

  useEffect(() => {
    const allRequiredChecked = requiredItems.every(item => checked.has(item.id));
    onChange(allRequiredChecked);
  }, [checked, requiredItems, onChange]);

  const handleCheck = (id: string, isChecked: boolean): void => {
    setChecked(prev => {
      const next = new Set(prev);
      if (isChecked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  };

  return (
    <Space direction="vertical" block>
      {items.map((item) => (
        <Checkbox
          key={item.id}
          checked={checked.has(item.id)}
          onChange={(val) => handleCheck(item.id, val)}
          style={{
            '--icon-size': '28px',
            '--font-size': '16px',
            padding: '12px 0',
          } as React.CSSProperties}
        >
          {item.label}
          {item.required && <span style={{ color: '#ff4d4f' }}> *</span>}
        </Checkbox>
      ))}
    </Space>
  );
};
```

### CountdownTimer

**File: `src/components/placement/CountdownTimer.tsx`**

```tsx
import type { FC } from 'react';
import { useState, useEffect } from 'react';
import { Tag } from 'antd-mobile';
import { Clock, AlertTriangle } from 'lucide-react';

interface Props {
  deadline: string;
}

export const CountdownTimer: FC<Props> = ({ deadline }) => {
  const [remaining, setRemaining] = useState<string>('');
  const [isUrgent, setIsUrgent] = useState(false);
  const [isOverdue, setIsOverdue] = useState(false);

  useEffect(() => {
    const update = (): void => {
      const now = new Date();
      const target = new Date(deadline);
      const diffMs = target.getTime() - now.getTime();

      if (diffMs <= 0) {
        setIsOverdue(true);
        setRemaining('Муддати ўтди!');
        return;
      }

      const diffMins = Math.floor(diffMs / 60000);
      const hours = Math.floor(diffMins / 60);
      const mins = diffMins % 60;

      setIsUrgent(diffMins < 15);

      if (hours > 0) {
        setRemaining(`${hours}:${mins.toString().padStart(2, '0')}`);
      } else {
        setRemaining(`${mins} дақ`);
      }
    };

    update();
    const interval = setInterval(update, 10000); // Update every 10s

    return () => clearInterval(interval);
  }, [deadline]);

  const bgColor = isOverdue ? '#ff4d4f' : isUrgent ? '#faad14' : '#52c41a';
  const Icon = isOverdue || isUrgent ? AlertTriangle : Clock;

  return (
    <div
      className="flex items-center justify-center gap-2 py-3 rounded-lg"
      style={{ backgroundColor: bgColor }}
    >
      <Icon size={24} color="#ffffff" />
      <span
        className="text-white font-bold"
        style={{ fontSize: isUrgent || isOverdue ? '24px' : '20px' }}
      >
        {remaining}
      </span>
    </div>
  );
};
```

### Barrel Export

**File: `src/components/placement/index.ts`**

```typescript
export { YardGrid } from './YardGrid';
export { RowSideView } from './RowSideView';
export { WorkOrderCard } from './WorkOrderCard';
export { PlacementInfo } from './PlacementInfo';
export { PlacementChecklist } from './PlacementChecklist';
export { CountdownTimer } from './CountdownTimer';
```

---

## 8. API Integration

### Updated API Config

**File: `src/config/api.ts` (additions)**

```typescript
// Add to existing API_ENDPOINTS
export const API_ENDPOINTS = {
  // ... existing endpoints ...

  placement: {
    // Work Orders
    workOrders: '/api/placement/work-orders/',
    workOrder: (id: number) => `/api/placement/work-orders/${id}/`,
    acceptOrder: (id: number) => `/api/placement/work-orders/${id}/accept/`,
    startOrder: (id: number) => `/api/placement/work-orders/${id}/start/`,
    completeOrder: (id: number) => `/api/placement/work-orders/${id}/complete/`,

    // Yard Layout
    yardLayout: '/api/placement/yard-layout/',
    rowDetail: (zone: string, row: number) => `/api/placement/yard-layout/${zone}/${row}/`,
  },
};

// Work order status colors
export const WORK_ORDER_COLORS = {
  PENDING: '#faad14',
  ASSIGNED: '#1890ff',
  ACCEPTED: '#52c41a',
  IN_PROGRESS: '#722ed1',
  COMPLETED: '#13c2c2',
  VERIFIED: '#52c41a',
  FAILED: '#ff4d4f',
};
```

### Updated Routes

**File: `src/navigation/routes.tsx` (additions)**

```tsx
import { WorkOrdersPage } from '@/pages/WorkOrdersPage';
import { PlacementDetailPage } from '@/pages/PlacementDetailPage';
import { PlacementConfirmPage } from '@/pages/PlacementConfirmPage';

export const routes: Route[] = [
  // ... existing routes ...

  // Placement routes
  { path: '/work-orders', Component: WorkOrdersPage },
  { path: '/placement/:id', Component: PlacementDetailPage },
  { path: '/placement/:id/confirm', Component: PlacementConfirmPage },
];
```

### Updated App.tsx

**File: `src/components/App.tsx` (wrap with PlacementProvider)**

```tsx
import { PlacementProvider } from '@/contexts/PlacementContext';

// In the component tree, add PlacementProvider:
<CameraProvider>
  <PageProvider>
    <PlacementProvider>  {/* Add this */}
      <HashRouter>
        <Routes>
          {/* ... */}
        </Routes>
      </HashRouter>
    </PlacementProvider>
  </PageProvider>
</CameraProvider>
```

---

## 9. Real-time Updates

### WebSocket Connection (Backend Django Channels)

The PlacementContext handles WebSocket connection with auto-reconnect:

```
Browser                          Django Channels
   │                                   │
   │──── WebSocket Connect ───────────▶│
   │◀─── Connection Accepted ──────────│
   │                                   │
   │◀─── work_order_assigned ──────────│  (New order)
   │──── Refresh order list            │
   │                                   │
   │◀─── work_order_updated ───────────│  (Status change)
   │──── Update UI                     │
   │                                   │
   │◀─── placement_verified ───────────│  (System verified)
   │──── Show success/failure          │
   │                                   │
```

### Telegram Push Notifications

For background notifications when app is closed:

```typescript
// Using Telegram Mini Apps SDK
import { postEvent } from '@tma.js/sdk-react';

// Request notification permission
postEvent('web_app_request_write_access');

// Send notification via backend
// Backend uses Telegram Bot API: sendMessage to user
```

---

## 10. Worker UX Guidelines

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Large Touch Targets** | Minimum 48px height, action buttons 64px |
| **Icons > Text** | Every action has prominent icon |
| **Color Coding** | Green = target, Blue = info, Red = warning |
| **One Action Per Screen** | Clear primary action button |
| **Glanceable Info** | Key data (location code) is largest text |
| **Forgiving Input** | Confirmation dialogs for destructive actions |

### Touch Target Sizes

```
┌─────────────────────────────────────────────────┐
│                    Button Sizes                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  Primary Actions:     64px height               │
│  ┌──────────────────────────────────────────┐   │
│  │  🚀  ЖОЙГА БОРИШ                         │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  Secondary Actions:   48px height               │
│  ┌──────────────────────────────────────────┐   │
│  │  📷  Қайта олиш                           │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  List Items:          60px minimum height        │
│  Checkboxes:          28px icon size            │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Color Scheme

```
┌─────────────────────────────────────────────────┐
│               Color Meanings                     │
├─────────────────────────────────────────────────┤
│                                                  │
│  🟢 #52c41a  GREEN    Target location           │
│                       Success states            │
│                       "Go" actions              │
│                                                  │
│  🔵 #1890ff  BLUE     Information               │
│                       Container data            │
│                       Navigation                │
│                                                  │
│  🟡 #faad14  YELLOW   Warning                   │
│                       Time running low          │
│                       High priority             │
│                                                  │
│  🔴 #ff4d4f  RED      Error/Overdue             │
│                       Urgent priority           │
│                       Cannot place here         │
│                                                  │
│  🟣 #722ed1  PURPLE   In progress               │
│                       Laden containers          │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## 11. Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Backend:**
- [ ] Work Order model and migrations
- [ ] Work Order API endpoints (CRUD + accept/start/complete)
- [ ] Yard Layout API (zones, rows, slots)
- [ ] Django Channels WebSocket consumer

**Frontend:**
- [ ] TypeScript types (`types/placement.ts`)
- [ ] PlacementContext with WebSocket
- [ ] API config updates

### Phase 2: Core Pages (Week 3-4)

**Pages:**
- [ ] WorkOrdersPage with WorkOrderCard
- [ ] PlacementDetailPage with info display
- [ ] PlacementConfirmPage with photo capture

**Components:**
- [ ] WorkOrderCard
- [ ] PlacementInfo
- [ ] PlacementChecklist
- [ ] CountdownTimer

### Phase 3: Visualization (Week 5)

**2D Components:**
- [ ] YardGrid (Canvas-based top-down view)
- [ ] RowSideView (Canvas-based side view)
- [ ] Touch interaction for zoom/pan

### Phase 4: Real-time & Polish (Week 6)

**Features:**
- [ ] WebSocket reconnection handling
- [ ] Push notifications via Telegram
- [ ] Offline detection and warning
- [ ] Loading states and error handling
- [ ] Haptic feedback for actions

### Phase 5: Testing & Optimization (Week 7-8)

**Testing:**
- [ ] Unit tests for hooks and utilities
- [ ] Integration tests for API calls
- [ ] E2E tests for critical flows
- [ ] Field testing with actual devices

**Optimization:**
- [ ] Canvas rendering performance
- [ ] Image compression for photos
- [ ] Bundle size optimization

---

## Appendix: File Checklist

### New Files to Create

```
telegram-miniapp/src/
├── types/placement.ts                    ☐
├── contexts/PlacementContext.tsx         ☐
├── hooks/useYardLayout.ts                ☐
├── pages/WorkOrdersPage/
│   ├── WorkOrdersPage.tsx                ☐
│   └── index.ts                          ☐
├── pages/PlacementDetailPage/
│   ├── PlacementDetailPage.tsx           ☐
│   └── index.ts                          ☐
├── pages/PlacementConfirmPage/
│   ├── PlacementConfirmPage.tsx          ☐
│   └── index.ts                          ☐
└── components/placement/
    ├── YardGrid.tsx                      ☐
    ├── RowSideView.tsx                   ☐
    ├── WorkOrderCard.tsx                 ☐
    ├── PlacementInfo.tsx                 ☐
    ├── PlacementChecklist.tsx            ☐
    ├── CountdownTimer.tsx                ☐
    └── index.ts                          ☐
```

### Files to Modify

```
telegram-miniapp/src/
├── config/api.ts                         ☐ Add placement endpoints
├── navigation/routes.tsx                 ☐ Add placement routes
└── components/App.tsx                    ☐ Add PlacementProvider
```

---

> **Document Version:** 1.0
> **Created:** January 2026
> **Related:** `docs/specs/3d-placement-business-flow.md`
