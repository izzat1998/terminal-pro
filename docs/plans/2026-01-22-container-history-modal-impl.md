# Container Event History Modal - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a modal to display container event history timeline with images in the Customer and Company container views.

**Architecture:** Create a reusable `ContainerHistoryModal.vue` component that fetches events from `/terminal/entries/{id}/events/` and displays them as a colored timeline with Ant Design's `<a-timeline>`. Images are shown as thumbnails with gallery preview.

**Tech Stack:** Vue 3 + TypeScript, Ant Design Vue (`a-timeline`, `a-modal`, `a-image`), existing `http` client

---

## Task 1: Create Container Event Service

**Files:**
- Create: `frontend/src/services/containerEventService.ts`

**Step 1: Create the service file with types and API function**

```typescript
// frontend/src/services/containerEventService.ts
import { http } from '../utils/httpClient'

export interface EventPerformer {
  id: number
  full_name: string
  user_type: string
}

export interface ContainerEvent {
  id: number
  event_type: string
  event_type_display: string
  event_time: string
  performed_by: EventPerformer | null
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

interface ApiResponse {
  success: boolean
  data: ContainerTimeline
}

export async function getContainerEvents(entryId: number): Promise<ContainerTimeline> {
  const response = await http.get<ApiResponse>(`/terminal/entries/${entryId}/events/`)
  return response.data
}
```

**Step 2: Verify file created correctly**

Run: `cat frontend/src/services/containerEventService.ts`
Expected: File contents shown

**Step 3: Commit**

```bash
git add frontend/src/services/containerEventService.ts
git commit -m "feat(frontend): add container event service"
```

---

## Task 2: Create ContainerHistoryModal Component

**Files:**
- Create: `frontend/src/components/ContainerHistoryModal.vue`

**Step 1: Create the modal component**

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'
import { CloseOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { getContainerEvents, type ContainerEvent } from '../services/containerEventService'

interface ContainerImage {
  id: string
  file_url: string
}

interface Props {
  open: boolean
  entryId: number | null
  containerNumber: string
  images?: ContainerImage[]
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
  EXIT_RECORDED: 'red',
}

function getEventColor(eventType: string): string {
  return eventColors[eventType] || 'gray'
}

function formatEventTime(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatEventDetails(event: ContainerEvent): string[] {
  const details: string[] = []
  const d = event.details

  switch (event.event_type) {
    case 'ENTRY_CREATED':
      if (d.status) details.push(`Статус: ${d.status === 'LADEN' ? 'Гружёный' : 'Порожний'}`)
      if (d.transport_type) details.push(`Транспорт: ${d.transport_type === 'TRUCK' ? 'Авто' : 'Ж/Д'} ${d.transport_number || ''}`)
      if (d.entry_train_number) details.push(`Поезд: ${d.entry_train_number}`)
      break
    case 'STATUS_CHANGED':
      if (d.old_status && d.new_status) {
        const oldLabel = d.old_status === 'LADEN' ? 'Гружёный' : 'Порожний'
        const newLabel = d.new_status === 'LADEN' ? 'Гружёный' : 'Порожний'
        details.push(`${oldLabel} → ${newLabel}`)
      }
      if (d.reason) details.push(`Причина: ${d.reason}`)
      break
    case 'POSITION_ASSIGNED':
      if (d.coordinate) details.push(`Координата: ${d.coordinate}`)
      if (d.zone) details.push(`Зона: ${d.zone}, Ряд: ${d.row}, Бей: ${d.bay}, Ярус: ${d.tier}`)
      if (d.auto_assigned) details.push('Авто-назначение: да')
      break
    case 'POSITION_REMOVED':
      if (d.previous_coordinate) details.push(`Предыдущая: ${d.previous_coordinate}`)
      break
    case 'WORK_ORDER_CREATED':
      if (d.order_number) details.push(`Наряд: ${d.order_number}`)
      if (d.target_coordinate) details.push(`Цель: ${d.target_coordinate}`)
      if (d.priority) details.push(`Приоритет: ${d.priority}`)
      break
    case 'WORK_ORDER_COMPLETED':
      if (d.order_number) details.push(`Наряд: ${d.order_number}`)
      break
    case 'CRANE_OPERATION':
      if (d.operation_date) details.push(`Дата: ${d.operation_date}`)
      break
    case 'EXIT_RECORDED':
      if (d.exit_transport_type) details.push(`Транспорт: ${d.exit_transport_type === 'TRUCK' ? 'Авто' : 'Ж/Д'} ${d.exit_transport_number || ''}`)
      if (d.exit_train_number) details.push(`Поезд: ${d.exit_train_number}`)
      if (d.destination_station) details.push(`Станция: ${d.destination_station}`)
      if (d.dwell_time_days !== undefined) details.push(`Время на терминале: ${d.dwell_time_days} дн.`)
      break
  }

  return details
}

function getSourceLabel(event: ContainerEvent): string {
  const parts: string[] = []
  if (event.source_display) parts.push(event.source_display)
  if (event.performed_by?.full_name) parts.push(event.performed_by.full_name)
  return parts.join(' • ') || '—'
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

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen && props.entryId) {
      fetchEvents()
    } else {
      events.value = []
    }
  }
)
</script>

<template>
  <a-modal
    :open="open"
    :title="`История контейнера: ${containerNumber}`"
    :width="700"
    :footer="null"
    centered
    @update:open="emit('update:open', $event)"
  >
    <template #closeIcon>
      <CloseOutlined />
    </template>

    <a-spin :spinning="loading">
      <!-- Images section if provided -->
      <div v-if="images && images.length > 0" class="images-section">
        <a-image-preview-group>
          <a-image
            v-for="(img, index) in images.slice(0, 4)"
            :key="img.id"
            :src="img.file_url"
            :width="80"
            :height="80"
            class="entry-thumbnail"
          />
          <template v-for="img in images.slice(4)" :key="img.id">
            <a-image :src="img.file_url" :style="{ display: 'none' }" />
          </template>
        </a-image-preview-group>
        <span v-if="images.length > 4" class="more-images">+{{ images.length - 4 }}</span>
      </div>

      <!-- Timeline -->
      <a-timeline v-if="events.length > 0" class="event-timeline">
        <a-timeline-item
          v-for="event in events"
          :key="event.id"
          :color="getEventColor(event.event_type)"
        >
          <div class="event-item">
            <div class="event-header">
              <span class="event-time">{{ formatEventTime(event.event_time) }}</span>
              <span class="event-title">{{ event.event_type_display }}</span>
            </div>
            <div class="event-details">
              <div v-for="(detail, idx) in formatEventDetails(event)" :key="idx" class="detail-line">
                {{ detail }}
              </div>
            </div>
            <div class="event-source">
              {{ getSourceLabel(event) }}
            </div>
          </div>
        </a-timeline-item>
      </a-timeline>

      <a-empty v-else-if="!loading" description="Нет событий" />
    </a-spin>
  </a-modal>
</template>

<style scoped>
.images-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.entry-thumbnail {
  border-radius: 4px;
  object-fit: cover;
  border: 1px solid #d9d9d9;
  cursor: pointer;
}

.more-images {
  color: #1890ff;
  font-size: 14px;
  margin-left: 4px;
}

.event-timeline {
  margin-top: 16px;
}

.event-item {
  padding-bottom: 8px;
}

.event-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 4px;
}

.event-time {
  font-size: 12px;
  color: #8c8c8c;
  min-width: 120px;
}

.event-title {
  font-weight: 600;
  color: #262626;
}

.event-details {
  margin-left: 132px;
  font-size: 13px;
  color: #595959;
}

.detail-line {
  margin-bottom: 2px;
}

.event-source {
  margin-left: 132px;
  margin-top: 4px;
  font-size: 12px;
  color: #8c8c8c;
}
</style>
```

**Step 2: Verify file created correctly**

Run: `head -50 frontend/src/components/ContainerHistoryModal.vue`
Expected: Vue component with script setup shown

**Step 3: Commit**

```bash
git add frontend/src/components/ContainerHistoryModal.vue
git commit -m "feat(frontend): add ContainerHistoryModal component"
```

---

## Task 3: Integrate into Customer Containers View

**Files:**
- Modify: `frontend/src/views/customer/Containers.vue`

**Step 1: Add imports and state for history modal**

In the `<script setup>` section, after existing imports (around line 157), add:

```typescript
import { HistoryOutlined } from '@ant-design/icons-vue';
import ContainerHistoryModal from '../../components/ContainerHistoryModal.vue';
```

After the 3D modal state (around line 232), add:

```typescript
// History modal state
const historyModalVisible = ref(false);
const selectedHistoryEntry = ref<{
  id: number;
  containerNumber: string;
  images: ContainerImage[];
} | null>(null);

function openHistory(record: ContainerEntry) {
  selectedHistoryEntry.value = {
    id: record.id,
    containerNumber: record.container.container_number,
    images: record.images || [],
  };
  historyModalVisible.value = true;
}
```

**Step 2: Add Actions column to columns array**

After the `exit` column definition (around line 360), add:

```typescript
{
  title: '',
  key: 'actions',
  width: 50,
  fixed: 'right' as const,
},
```

**Step 3: Add template for actions column**

In the `<template #bodyCell>` section, after the exit template (around line 135), add:

```vue
<template v-if="column.key === 'actions'">
  <a-tooltip title="История контейнера">
    <a-button type="text" size="small" @click="openHistory(record)">
      <template #icon><HistoryOutlined /></template>
    </a-button>
  </a-tooltip>
</template>
```

**Step 4: Add modal component before closing </a-card>**

After the Container3DModal (around line 144), add:

```vue
<!-- History Modal -->
<ContainerHistoryModal
  v-model:open="historyModalVisible"
  :entry-id="selectedHistoryEntry?.id ?? null"
  :container-number="selectedHistoryEntry?.containerNumber ?? ''"
  :images="selectedHistoryEntry?.images"
/>
```

**Step 5: Verify changes compile**

Run: `cd frontend && npm run build`
Expected: Build succeeds without TypeScript errors

**Step 6: Commit**

```bash
git add frontend/src/views/customer/Containers.vue
git commit -m "feat(frontend): integrate history modal in customer containers"
```

---

## Task 4: Integrate into Company Containers View

**Files:**
- Modify: `frontend/src/views/company/CompanyContainers.vue`

**Step 1: Add imports**

After existing imports (around line 89), add:

```typescript
import { HistoryOutlined } from '@ant-design/icons-vue';
import ContainerHistoryModal from '../../components/ContainerHistoryModal.vue';
```

**Step 2: Add state for history modal**

After `const loading = ref(false);` (around line 166), add:

```typescript
// History modal state
const historyModalVisible = ref(false);
const selectedHistoryEntry = ref<{
  id: number;
  containerNumber: string;
} | null>(null);

function openHistory(record: ContainerEntry) {
  selectedHistoryEntry.value = {
    id: record.id,
    containerNumber: record.container.container_number,
  };
  historyModalVisible.value = true;
}
```

**Step 3: Add Actions column**

After the `recorded_by` column (around line 224), add:

```typescript
{
  title: '',
  key: 'actions',
  width: 50,
  fixed: 'right' as const,
},
```

**Step 4: Add template for actions**

In the `<template #bodyCell>` section, after the recorded_by template (around line 80), add:

```vue
<template v-if="column.key === 'actions'">
  <a-tooltip title="История контейнера">
    <a-button type="text" size="small" @click="openHistory(record)">
      <template #icon><HistoryOutlined /></template>
    </a-button>
  </a-tooltip>
</template>
```

**Step 5: Add modal component before closing </a-card>**

After the `</a-table>` (around line 82), add:

```vue
<!-- History Modal -->
<ContainerHistoryModal
  v-model:open="historyModalVisible"
  :entry-id="selectedHistoryEntry?.id ?? null"
  :container-number="selectedHistoryEntry?.containerNumber ?? ''"
/>
```

**Step 6: Verify changes compile**

Run: `cd frontend && npm run build`
Expected: Build succeeds without TypeScript errors

**Step 7: Commit**

```bash
git add frontend/src/views/company/CompanyContainers.vue
git commit -m "feat(frontend): integrate history modal in company containers"
```

---

## Task 5: Manual Testing

**Step 1: Start backend and frontend**

Run: `make dev` (or in separate terminals: `make backend` and `make frontend`)

**Step 2: Test Customer Containers view**

1. Navigate to customer containers page
2. Click history icon on any container row
3. Verify modal opens with container number in title
4. Verify timeline shows events with correct colors
5. Verify event details display correctly
6. Verify images show if container has photos
7. Close modal and verify it closes cleanly

**Step 3: Test Company Containers view**

1. Navigate to company containers page
2. Click history icon on any container row
3. Verify same functionality as customer view

**Step 4: Test edge cases**

1. Test container with no events - should show "Нет событий"
2. Test error handling - disconnect network and click history icon
3. Verify loading spinner shows while fetching

---

## Task 6: Final Commit

**Step 1: Verify all changes**

Run: `git status`
Expected: All changes committed, working tree clean

**Step 2: Create summary commit if needed**

If there are any uncommitted changes:
```bash
git add -A
git commit -m "feat(frontend): complete container history modal implementation"
```

---

## Summary

Files created:
- `frontend/src/services/containerEventService.ts` - API service
- `frontend/src/components/ContainerHistoryModal.vue` - Modal component

Files modified:
- `frontend/src/views/customer/Containers.vue` - Added history button
- `frontend/src/views/company/CompanyContainers.vue` - Added history button

Total commits: 4-5 small commits
