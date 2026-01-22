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
            v-for="img in images.slice(0, 4)"
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
