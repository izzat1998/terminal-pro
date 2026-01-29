# 3D Yard Settings Drawer - Design Document

**Date:** 2026-01-26
**Status:** Approved
**Author:** Claude + User

## Overview

Consolidate all 3D canvas controls into a single settings drawer, replacing scattered toggle buttons for a cleaner UI.

## Goals

1. Remove cluttered individual toggle buttons from right-side controls
2. Hide DXF layer panel by default
3. Provide centralized settings drawer with organized sections
4. Set sensible default visibility for layers

## Component Structure

### New Files

| File | Purpose |
|------|---------|
| `components/yard/YardSettingsDrawer.vue` | Settings drawer UI component |
| `composables/useYardSettings.ts` | Centralized settings state management |

### Modified Files

| File | Changes |
|------|---------|
| `components/YardView3D.vue` | Remove toggle buttons, add settings button, integrate drawer |
| `views/YardTestView.vue` | Wire up settings to debug overlays |

## Settings Drawer UI

### Layout (280px width, slides from right)

```
┌─────────────────────────────────────┐
│  ⚙️ Настройки                   [✕] │
├─────────────────────────────────────┤
│                                     │
│  ▼ Слои                             │
│  ┌─────────────────────────────┐   │
│  │  ☑ Контейнеры               │   │
│  │  ☑ Здания                   │   │
│  │  ☑ Дороги                   │   │
│  │  ☑ Ограждения               │   │
│  │  ☐ Ж/Д пути                 │   │
│  │  ☐ Площадки                 │   │
│  │  ☐ Тестовые ТС              │   │
│  └─────────────────────────────┘   │
│                                     │
│  ▼ Подписи                          │
│  ┌─────────────────────────────┐   │
│  │  ☐ Названия зданий          │   │
│  │  ☐ Номера контейнеров       │   │
│  │  ☐ Номера ТС                │   │
│  └─────────────────────────────┘   │
│                                     │
│  ▼ Отображение                      │
│  ┌─────────────────────────────┐   │
│  │  Цветовой режим:            │   │
│  │  [Визуал | Статус | Срок]   │   │
│  │                             │   │
│  │  ☐ Сетка                    │   │
│  │  ☑ Статистика               │   │
│  └─────────────────────────────┘   │
│                                     │
│  ▼ Камера                           │
│  ┌─────────────────────────────┐   │
│  │  [⬆ Сверху] [◇ Изо] [⊞ Всё] │   │
│  └─────────────────────────────┘   │
│                                     │
│  ▸ Расширенные (DXF слои)           │
│                                     │
└─────────────────────────────────────┘
```

### Drawer Behavior

- Slides from RIGHT edge
- Width: 280px
- Semi-transparent backdrop (click to close)
- Uses Ant Design `<a-drawer>` component

## TypeScript Interfaces

```typescript
// composables/useYardSettings.ts

interface YardLayerSettings {
  containers: boolean
  buildings: boolean
  roads: boolean
  fences: boolean
  railway: boolean
  platforms: boolean
  testVehicles: boolean
}

interface YardLabelSettings {
  buildings: boolean
  containers: boolean
  vehicles: boolean
}

interface YardDisplaySettings {
  colorMode: 'visual' | 'status' | 'dwell'
  showGrid: boolean
  showStats: boolean
}

interface YardSettings {
  layers: YardLayerSettings
  labels: YardLabelSettings
  display: YardDisplaySettings
}
```

## Default Values

| Setting | Default | Rationale |
|---------|---------|-----------|
| **Layers** | | |
| Containers | ✅ ON | Core content |
| Buildings | ✅ ON | Important landmarks |
| Roads | ✅ ON | Navigation context |
| Fences | ✅ ON | Terminal boundary |
| Railway | ❌ OFF | Optional detail |
| Platforms | ❌ OFF | Optional detail |
| Test Vehicles | ❌ OFF | Dev/demo only |
| **Labels** | | |
| Building Names | ❌ OFF | Reduces clutter |
| Container Numbers | ❌ OFF | Too dense |
| Vehicle Plates | ❌ OFF | Dynamic, on-demand |
| **Display** | | |
| Color Mode | Visual | Most attractive default |
| Grid | ❌ OFF | Debug feature |
| Stats | ✅ ON | Useful info |

## Right-Side Controls (After)

```
Before (8 buttons):     After (4 buttons):
[⬆] Top View            [⚙️] Settings
[◇] Isometric           ─────────────
[⊞] Fit to View         [⬆] Top View
[🏷] Building Labels    [◇] Isometric
[🚧] Fences             [⊞] Fit to View
[🚂] Railway
[📦] Platforms
[🛣️] Roads
```

## State Flow

```
useYardSettings()
     │
     ├──► YardSettingsDrawer (UI controls)
     │         │
     │         └──► User toggles checkbox
     │                    │
     │                    ▼
     │              settings.layers.fences = false
     │                    │
     ▼                    ▼
YardView3D ◄───── watches settings ─────►  Composables
     │                                      useFences3D()
     │                                      useRailway3D()
     ▼                                      etc.
Scene updates
```

## Implementation Tasks

1. Create `useYardSettings.ts` composable
2. Create `YardSettingsDrawer.vue` component
3. Modify `YardView3D.vue` - remove toggles, add settings button
4. Modify `YardView3D.vue` - integrate drawer and wire up settings
5. Update default visibility values
6. Test all toggles work correctly

## Notes

- DXF layer panel hidden by default, accessible in "Advanced" section
- Settings persist in component state (not localStorage for now)
- Future: Could add localStorage persistence for user preferences
