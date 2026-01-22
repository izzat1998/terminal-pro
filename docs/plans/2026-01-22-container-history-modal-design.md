# Container Event History Modal - Design Document

**Date**: 2026-01-22
**Status**: Approved

## Overview

Add a modal to display the complete lifecycle history of a container as a visual timeline, accessible from the container tables in both Customer and Company views.

## User Flow

1. User views container list (Customer or Company portal)
2. User clicks history icon (`<HistoryOutlined />`) in the Actions column
3. Modal opens showing chronological timeline of all container events
4. User can view photos by clicking thumbnails to open gallery
5. User closes modal via X button or clicking outside

## Modal Specifications

| Property | Value |
|----------|-------|
| Width | 700px |
| Position | Centered |
| Footer | None |
| Title | `История контейнера: {CONTAINER_NUMBER}` |

## Timeline Display

### Visual Structure

```
┌─────────────────────────────────────────────────────────────┐
│  История контейнера: HDMU6565958                        ✕   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ● 23.12.2025, 10:00                          ┌─────────┐  │
│   │ Контейнер принят                           │  [img]  │  │
│   │                                            │   +2    │  │
│   │ Статус: LADEN                              └─────────┘  │
│   │ Транспорт: Авто 01A123BC                                │
│   │ Источник: API • Иван Петров                             │
│   │                                                         │
│   ● 23.12.2025, 10:15                                       │
│   │ Позиция назначена                                       │
│   │ Координата: A-R03-B15-T2-A                              │
│   │ Зона: A, Ряд: 3, Бей: 15, Ярус: 2                       │
│   │ Источник: Telegram • Мария Сидорова                     │
│   │                                                         │
│   ● 25.12.2025, 14:30                          ┌─────────┐  │
│   │ Выезд зарегистрирован                      │  [img]  │  │
│   │                                            └─────────┘  │
│   │ Транспорт: Ж/Д WAG-001                                  │
│   │ Станция назначения: Ташкент                             │
│   │ Время на терминале: 3 дня                               │
│   │ Источник: Система                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Event Types & Colors

| Event Type | Russian Title | Color | Details Shown |
|------------|---------------|-------|---------------|
| `ENTRY_CREATED` | Контейнер принят | 🟢 Green | Статус, Тип транспорта, Номер транспорта, Номер поезда |
| `STATUS_CHANGED` | Статус изменён | 🟣 Purple | Было → Стало, Причина |
| `POSITION_ASSIGNED` | Позиция назначена | 🔵 Blue | Координата, Зона, Ряд, Бей, Ярус, Авто-назначение |
| `POSITION_REMOVED` | Позиция удалена | 🔵 Blue | Предыдущая координата |
| `WORK_ORDER_CREATED` | Наряд-задание создано | 🟠 Orange | Номер наряда, Целевая координата, Приоритет |
| `WORK_ORDER_COMPLETED` | Наряд-задание выполнено | 🟠 Orange | Номер наряда, Время выполнения |
| `CRANE_OPERATION` | Крановая операция | 🔵 Blue | Дата операции |
| `EXIT_RECORDED` | Выезд зарегистрирован | 🔴 Red | Тип транспорта, Номер, Станция назначения, Время на терминале |

### Image Display

- **Thumbnail**: 80x80px, positioned to the right of event content
- **Badge**: Shows `+N` if more than one photo exists
- **Gallery**: Click thumbnail to open `<a-image-preview-group>` with full-screen viewer

## File Structure

### New Files

```
frontend/src/
├── components/
│   └── ContainerHistoryModal.vue    # Main modal component
└── services/
    └── containerEventService.ts     # API calls for events
```

### Modified Files

```
frontend/src/
├── views/customer/Containers.vue       # Add history button to actions
├── views/company/CompanyContainers.vue # Add history button to actions
└── types/api.ts                        # Add ContainerEvent interface
```

## API Integration

### Endpoint

```
GET /api/terminal/entries/{container_entry_id}/events/
```

### Response Structure

```typescript
interface ContainerTimeline {
  container_number: string
  container_entry_id: number
  events: ContainerEvent[]
}

interface ContainerEvent {
  id: number
  event_type: string
  event_type_display: string  // Russian label
  event_time: string          // ISO datetime
  performed_by: {
    id: number
    full_name: string
    user_type: string
  } | null
  source: string              // API, TELEGRAM_BOT, EXCEL_IMPORT, SYSTEM
  source_display: string      // Russian label
  details: Record<string, unknown>  // Event-specific data
  created_at: string
}
```

### Service Function

```typescript
// containerEventService.ts
import http from '@/utils/httpClient'

export interface ContainerEvent {
  id: number
  event_type: string
  event_type_display: string
  event_time: string
  performed_by: {
    id: number
    full_name: string
    user_type: string
  } | null
  source: string
  source_display: string
  details: Record<string, unknown>
  created_at: string
}

export interface ContainerTimeline {
  container_number: string
  container_entry_id: number
  events: ContainerEvent[]
}

export async function getContainerEvents(entryId: number): Promise<ContainerTimeline> {
  const response = await http.get(`/terminal/entries/${entryId}/events/`)
  return response.data.data
}
```

## Component Implementation

### ContainerHistoryModal.vue

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'
import { HistoryOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { getContainerEvents, type ContainerEvent, type ContainerTimeline } from '@/services/containerEventService'

interface Props {
  open: boolean
  entryId: number | null
  containerNumber: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const loading = ref(false)
const events = ref<ContainerEvent[]>([])

const eventColors: Record<string, string> = {
  ENTRY_CREATED: 'green',
  STATUS_CHANGED: 'purple',
  POSITION_ASSIGNED: 'blue',
  POSITION_REMOVED: 'blue',
  CRANE_OPERATION: 'blue',
  WORK_ORDER_CREATED: 'orange',
  WORK_ORDER_COMPLETED: 'orange',
  EXIT_RECORDED: 'red'
}

function getEventColor(eventType: string): string {
  return eventColors[eventType] || 'gray'
}

async function fetchEvents() {
  if (!props.entryId) return

  loading.value = true
  try {
    const data = await getContainerEvents(props.entryId)
    events.value = data.events
  } catch (error) {
    message.error('Не удалось загрузить историю')
    console.error('Failed to fetch container events:', error)
  } finally {
    loading.value = false
  }
}

watch(() => props.open, (isOpen) => {
  if (isOpen && props.entryId) {
    fetchEvents()
  } else {
    events.value = []
  }
})
</script>
```

### Integration in Container Tables

```vue
<!-- In columns definition -->
{
  title: 'Действия',
  key: 'actions',
  fixed: 'right',
  width: 120,
}

<!-- In template -->
<template #bodyCell="{ column, record }">
  <template v-if="column.key === 'actions'">
    <a-space>
      <!-- Existing buttons... -->
      <a-tooltip title="История контейнера">
        <a-button type="text" size="small" @click="openHistory(record)">
          <template #icon><HistoryOutlined /></template>
        </a-button>
      </a-tooltip>
    </a-space>
  </template>
</template>

<!-- Modal -->
<ContainerHistoryModal
  v-model:open="historyModalVisible"
  :entry-id="selectedEntryId"
  :container-number="selectedContainerNumber"
/>
```

## States

### Loading State
- Show `<a-spin>` spinner centered in modal body

### Empty State
- Show `<a-empty description="Нет событий" />` if no events exist

### Error State
- Show toast message: "Не удалось загрузить историю"
- Log error to console for debugging

## Future Considerations

- Add filtering by event type (if timeline becomes long)
- Add date range filter for containers with many events
- Export timeline to PDF for documentation purposes
