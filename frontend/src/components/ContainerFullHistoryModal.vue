<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { CloseOutlined, HistoryOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { terminalService, type TerminalEntry } from '../services/terminalService'
import ContainerHistoryModal from './ContainerHistoryModal.vue'

interface Props {
  open: boolean
  containerNumber: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const loading = ref(false)
const entries = ref<TerminalEntry[]>([])

// Entry timeline modal state
const entryTimelineVisible = ref(false)
const selectedEntryId = ref<number | null>(null)

const totalVisits = computed(() => entries.value.length)
const currentVisit = computed(() => entries.value.find(e => !e.exit_date))

function formatDateTime(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getStatusDisplay(status: string): string {
  return status === 'LADEN' ? 'Гружёный' : 'Порожний'
}

function getStatusColor(status: string): string {
  return status === 'LADEN' ? 'green' : 'orange'
}

function getTransportDisplay(transportType: string): string {
  const types: Record<string, string> = {
    'TRUCK': 'Авто',
    'WAGON': 'Вагон',
    'TRAIN': 'Поезд',
  }
  return types[transportType] || transportType
}

function openEntryTimeline(entry: TerminalEntry) {
  selectedEntryId.value = entry.id
  entryTimelineVisible.value = true
}

async function fetchHistory() {
  if (!props.containerNumber) return

  loading.value = true
  try {
    entries.value = await terminalService.getContainerHistory(props.containerNumber)
  } catch (error) {
    message.error('Не удалось загрузить историю контейнера')
    console.error('Failed to fetch container history:', error)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen && props.containerNumber) {
      fetchHistory()
    } else {
      entries.value = []
    }
  }
)
</script>

<template>
  <a-modal
    :open="open"
    :title="`История контейнера: ${containerNumber}`"
    :width="750"
    :footer="null"
    centered
    @update:open="emit('update:open', $event)"
  >
    <template #closeIcon>
      <CloseOutlined />
    </template>

    <a-spin :spinning="loading">
      <!-- Summary stats -->
      <div v-if="entries.length > 0" class="summary-section">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-statistic title="Всего визитов" :value="totalVisits" />
          </a-col>
          <a-col :span="8">
            <a-statistic
              title="Текущий статус"
              :value="currentVisit ? 'На терминале' : 'Нет на терминале'"
              :value-style="{ color: currentVisit ? '#52c41a' : '#8c8c8c', fontSize: '16px' }"
            />
          </a-col>
          <a-col :span="8">
            <a-statistic
              v-if="currentVisit"
              title="Текущий простой"
              :value="`${currentVisit.dwell_time_days || 0} дн.`"
            />
          </a-col>
        </a-row>
      </div>

      <!-- Visits list -->
      <div v-if="entries.length > 0" class="visits-list">
        <div
          v-for="(entry, index) in entries"
          :key="entry.id"
          class="visit-card"
          :class="{ 'visit-current': !entry.exit_date }"
        >
          <div class="visit-header">
            <div class="visit-number">
              <a-tag :color="!entry.exit_date ? 'blue' : 'default'">
                <template v-if="!entry.exit_date">
                  <ClockCircleOutlined /> Текущий визит
                </template>
                <template v-else>
                  <CheckCircleOutlined /> Визит #{{ totalVisits - index }}
                </template>
              </a-tag>
            </div>
            <a-button
              type="link"
              size="small"
              @click="openEntryTimeline(entry)"
            >
              <template #icon><HistoryOutlined /></template>
              События
            </a-button>
          </div>

          <a-descriptions :column="2" size="small" bordered>
            <a-descriptions-item label="Въезд">
              {{ formatDateTime(entry.entry_time) }}
            </a-descriptions-item>
            <a-descriptions-item label="Выезд">
              <template v-if="entry.exit_date">
                {{ formatDateTime(entry.exit_date) }}
              </template>
              <span v-else class="text-muted">На терминале</span>
            </a-descriptions-item>
            <a-descriptions-item label="Статус">
              <a-tag :color="getStatusColor(entry.status)">
                {{ getStatusDisplay(entry.status) }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="Простой">
              <a-tag :color="(entry.dwell_time_days || 0) > 7 ? 'red' : (entry.dwell_time_days || 0) > 3 ? 'orange' : 'green'">
                {{ entry.dwell_time_days || 0 }} дн.
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="Транспорт (въезд)">
              {{ getTransportDisplay(entry.transport_type) }}
              <span v-if="entry.transport_number" class="transport-number">
                {{ entry.transport_number }}
              </span>
            </a-descriptions-item>
            <a-descriptions-item label="Транспорт (выезд)">
              <template v-if="entry.exit_transport_type">
                {{ getTransportDisplay(entry.exit_transport_type) }}
                <span v-if="entry.exit_transport_number" class="transport-number">
                  {{ entry.exit_transport_number }}
                </span>
              </template>
              <span v-else class="text-muted">—</span>
            </a-descriptions-item>
            <a-descriptions-item v-if="entry.company" label="Клиент" :span="2">
              {{ entry.company.name }}
            </a-descriptions-item>
            <a-descriptions-item v-if="entry.cargo_name" label="Груз" :span="2">
              {{ entry.cargo_name }}
              <span v-if="entry.cargo_weight" class="cargo-weight">
                ({{ entry.cargo_weight }} кг)
              </span>
            </a-descriptions-item>
            <a-descriptions-item v-if="entry.location" label="Локация">
              <a-tag color="purple">{{ entry.location }}</a-tag>
            </a-descriptions-item>
          </a-descriptions>
        </div>
      </div>

      <a-empty v-else-if="!loading" description="Контейнер не найден в системе" />
    </a-spin>

    <!-- Entry timeline modal (nested) -->
    <ContainerHistoryModal
      v-model:open="entryTimelineVisible"
      :entry-id="selectedEntryId"
      :container-number="containerNumber"
    />
  </a-modal>
</template>

<style scoped>
.summary-section {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.visits-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.visit-card {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
  transition: all 0.2s;
}

.visit-card:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
}

.visit-current {
  border-color: #1890ff;
  background: linear-gradient(135deg, #f0f7ff 0%, #fff 100%);
}

.visit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.visit-number {
  font-weight: 600;
}

.text-muted {
  color: #8c8c8c;
}

.transport-number {
  margin-left: 8px;
  color: #1890ff;
  font-weight: 500;
}

.cargo-weight {
  color: #8c8c8c;
  margin-left: 4px;
}
</style>
