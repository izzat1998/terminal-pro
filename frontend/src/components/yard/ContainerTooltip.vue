<script setup lang="ts">
/**
 * ContainerTooltip - Rich hover tooltip for 3D container visualization
 *
 * Displays detailed container information on hover:
 * - Container number (large, bold)
 * - Status badge (Laden/Empty)
 * - Dwell time with color indicator
 * - Company name
 * - Hazmat warning badge (if applicable)
 * - Priority badge (if HIGH/URGENT)
 * - Position (Zone-Row-Bay-Tier)
 * - Entry date
 * - Vessel/booking (if set)
 */

import { computed } from 'vue'
import type { ContainerData, ImoClass } from '@/composables/useContainers3D'

interface Props {
  /** Container data to display */
  container: ContainerData | null
  /** Position coordinates on screen (pixels) */
  x: number
  y: number
  /** Whether the tooltip is visible */
  visible: boolean
}

const props = withDefaults(defineProps<Props>(), {
  container: null,
  x: 0,
  y: 0,
  visible: false,
})

// Dwell tier calculation (matches useContainers3D logic)
const dwellTier = computed(() => {
  if (!props.container?.dwell_days) return null
  const days = props.container.dwell_days

  if (days <= 3) return { color: '#22C55E', label: 'Свежий', bgColor: '#DCFCE7' }
  if (days <= 7) return { color: '#3B82F6', label: 'Нормальный', bgColor: '#DBEAFE' }
  if (days <= 14) return { color: '#F59E0B', label: 'Стареющий', bgColor: '#FEF3C7' }
  if (days <= 21) return { color: '#F97316', label: 'Просроченный', bgColor: '#FED7AA' }
  return { color: '#EF4444', label: 'Критический', bgColor: '#FEE2E2' }
})

// IMO class label
const imoLabel = computed(() => {
  if (!props.container?.imo_class) return null

  const labels: Record<ImoClass, string> = {
    '1': 'Взрывчатые',
    '2': 'Газы',
    '3': 'Горючие жидкости',
    '4': 'Горючие твёрдые',
    '5': 'Окислители',
    '6': 'Токсичные',
    '7': 'Радиоактивные',
    '8': 'Коррозионные',
    '9': 'Прочие опасные',
  }

  return labels[props.container.imo_class] ?? null
})

// Format entry date
const formattedEntryDate = computed(() => {
  if (!props.container?.entry_time) return null
  const date = new Date(props.container.entry_time)
  return date.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

// Priority badge config
const priorityConfig = computed(() => {
  if (!props.container?.priority || props.container.priority === 'NORMAL') return null

  if (props.container.priority === 'HIGH') {
    return { label: 'Высокий', color: '#F59E0B', bgColor: '#FEF3C7' }
  }
  if (props.container.priority === 'URGENT') {
    return { label: 'Срочный', color: '#EF4444', bgColor: '#FEE2E2' }
  }
  return null
})

// Status badge config
const statusConfig = computed(() => {
  if (!props.container) return null

  if (props.container.status === 'LADEN') {
    return { label: 'Груженый', color: '#0077B6', bgColor: '#DBEAFE' }
  }
  return { label: 'Порожний', color: '#F97316', bgColor: '#FED7AA' }
})

// Tooltip positioning style with viewport bounds checking
const positionStyle = computed(() => {
  // Offset from cursor
  const offsetX = 12
  const offsetY = 12

  return {
    left: `${props.x + offsetX}px`,
    top: `${props.y + offsetY}px`,
  }
})
</script>

<template>
  <Teleport to="body">
    <Transition name="tooltip-fade">
      <div
        v-if="visible && container"
        class="container-tooltip"
        :style="positionStyle"
      >
        <!-- Header: Container Number -->
        <div class="tooltip-header">
          <span class="container-number">{{ container.container_number }}</span>
          <span v-if="statusConfig" class="status-badge" :style="{ color: statusConfig.color, backgroundColor: statusConfig.bgColor }">
            {{ statusConfig.label }}
          </span>
        </div>

        <!-- Badges Row: Priority, Hazmat -->
        <div v-if="priorityConfig || container.is_hazmat" class="badges-row">
          <span v-if="priorityConfig" class="badge priority-badge" :style="{ color: priorityConfig.color, backgroundColor: priorityConfig.bgColor }">
            ⚡ {{ priorityConfig.label }}
          </span>
          <span v-if="container.is_hazmat && imoLabel" class="badge hazmat-badge">
            ⚠️ IMO {{ container.imo_class }}: {{ imoLabel }}
          </span>
        </div>

        <!-- Info Grid -->
        <div class="info-grid">
          <!-- Company -->
          <template v-if="container.company_name">
            <span class="info-label">Компания</span>
            <span class="info-value">{{ container.company_name }}</span>
          </template>

          <!-- Dwell Time -->
          <template v-if="container.dwell_days !== undefined">
            <span class="info-label">На терминале</span>
            <span class="info-value dwell-value">
              <span
                class="dwell-indicator"
                :style="{ backgroundColor: dwellTier?.color }"
              />
              {{ container.dwell_days }} дн. <span class="dwell-tier">({{ dwellTier?.label }})</span>
            </span>
          </template>

          <!-- Container Type -->
          <span class="info-label">Тип</span>
          <span class="info-value">{{ container.container_type }}</span>

          <!-- Entry Date -->
          <template v-if="formattedEntryDate">
            <span class="info-label">Въезд</span>
            <span class="info-value">{{ formattedEntryDate }}</span>
          </template>

          <!-- Vessel -->
          <template v-if="container.vessel_name">
            <span class="info-label">Судно</span>
            <span class="info-value">{{ container.vessel_name }}</span>
          </template>

          <!-- Booking -->
          <template v-if="container.booking_number">
            <span class="info-label">Букинг</span>
            <span class="info-value">{{ container.booking_number }}</span>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.container-tooltip {
  position: fixed;
  z-index: 9999;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  padding: 12px;
  min-width: 220px;
  max-width: 300px;
  pointer-events: none;
  font-size: 13px;
}

.tooltip-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.container-number {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  letter-spacing: 0.5px;
}

.status-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
}

.badges-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.badge {
  font-size: 11px;
  font-weight: 500;
  padding: 3px 8px;
  border-radius: 4px;
}

.priority-badge {
  /* Color set dynamically */
}

.hazmat-badge {
  color: #B45309;
  background-color: #FEF3C7;
}

.info-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  align-items: baseline;
}

.info-label {
  color: #6b7280;
  font-size: 12px;
}

.info-value {
  color: #1f2937;
  font-weight: 500;
}

.dwell-value {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dwell-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dwell-tier {
  color: #6b7280;
  font-weight: 400;
  font-size: 12px;
}

/* Fade transition */
.tooltip-fade-enter-active,
.tooltip-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.tooltip-fade-enter-from,
.tooltip-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
</style>
