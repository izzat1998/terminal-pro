<script setup lang="ts">
/**
 * GateStatsHeader - Professional gate statistics bar
 *
 * Displays real-time gate activity: entries, exits, vehicles on site,
 * and last detection with elegant status indicators.
 */

import { computed } from 'vue'
import type { VehicleType } from '@/composables/useVehicleModels'

interface VehicleEntry {
  id: string
  plateNumber: string
  vehicleType: VehicleType
  timestamp: number
  direction?: 'entering' | 'exiting'
}

interface Props {
  entries: VehicleEntry[]
  isActive?: boolean
  inactiveTimeout?: number
}

const props = withDefaults(defineProps<Props>(), {
  isActive: false,
  inactiveTimeout: 5 * 60 * 1000,
})

// Computed statistics
const stats = computed(() => {
  const entries = props.entries
  const entering = entries.filter(e => e.direction !== 'exiting').length
  const exiting = entries.filter(e => e.direction === 'exiting').length
  const onSite = entering - exiting

  return {
    entering,
    exiting,
    onSite: Math.max(0, onSite),
    total: entries.length,
  }
})

// Last entry info
const lastEntry = computed(() => {
  if (props.entries.length === 0) return null
  const sorted = [...props.entries].sort((a, b) => b.timestamp - a.timestamp)
  return sorted[0]
})

// Time since last entry
const timeSinceLastEntry = computed(() => {
  if (!lastEntry.value) return null

  const now = Date.now()
  const diff = now - lastEntry.value.timestamp

  if (diff < 60 * 1000) {
    return 'только что'
  } else if (diff < 60 * 60 * 1000) {
    const minutes = Math.floor(diff / (60 * 1000))
    return `${minutes}м назад`
  } else {
    const hours = Math.floor(diff / (60 * 60 * 1000))
    return `${hours}ч назад`
  }
})

// Gate activity status
const gateStatus = computed(() => {
  if (props.isActive) {
    return { label: 'Активны', type: 'active' }
  }

  if (lastEntry.value) {
    const diff = Date.now() - lastEntry.value.timestamp
    if (diff < props.inactiveTimeout) {
      return { label: 'Активны', type: 'online' }
    }
  }

  return { label: 'Ожидание', type: 'idle' }
})
</script>

<template>
  <div class="stats-bar">
    <!-- Gate Status -->
    <div class="stat-group status-group">
      <div class="status-badge" :class="gateStatus.type">
        <span class="status-dot"></span>
        <span class="status-text">Ворота: {{ gateStatus.label }}</span>
      </div>
    </div>

    <span class="stat-divider"></span>

    <!-- Entry Stats -->
    <div class="stat-group">
      <div class="stat-item">
        <svg class="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14"/>
          <path d="M12 5l7 7-7 7"/>
        </svg>
        <span class="stat-label">Въезд</span>
        <span class="stat-value">{{ stats.entering }}</span>
      </div>

      <div class="stat-item">
        <svg class="stat-icon exit" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5"/>
          <path d="M12 19l-7-7 7-7"/>
        </svg>
        <span class="stat-label">Выезд</span>
        <span class="stat-value">{{ stats.exiting }}</span>
      </div>
    </div>

    <span class="stat-divider"></span>

    <!-- On Site Counter -->
    <div class="stat-group highlight-group">
      <div class="stat-item highlight">
        <svg class="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M3 9h18"/>
          <path d="M9 21V9"/>
        </svg>
        <span class="stat-label">На территории</span>
        <span class="stat-value highlight-value">{{ stats.onSite }}</span>
      </div>
    </div>

    <span class="stat-divider"></span>

    <!-- Last Detection -->
    <div class="stat-group last-entry-group">
      <div v-if="lastEntry" class="last-entry">
        <span class="last-label">Последний:</span>
        <span class="plate-badge">{{ lastEntry.plateNumber }}</span>
        <span class="last-time">{{ timeSinceLastEntry }}</span>
      </div>
      <div v-else class="last-entry empty">
        <span class="last-label">Нет данных</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 16px;
  background: var(--color-bg-card, white);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-lg, 12px);
  box-shadow: var(--shadow-sm, 0 2px 8px rgba(0, 0, 0, 0.06));
  font-family: var(--font-body, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
}

/* Status Badge */
.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
  transition: all 200ms ease;
}

.status-badge.active {
  background: linear-gradient(135deg, var(--color-entry-lighter, #dcfce7) 0%, var(--color-success-light, #d1fae5) 100%);
  color: var(--color-entry-hover, #059669);
}

.status-badge.online {
  background: var(--color-entry-lighter, #f0fdf4);
  color: var(--color-success, #16a34a);
}

.status-badge.idle {
  background: var(--color-warning-light, #fefce8);
  color: var(--color-warning, #ca8a04);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.status-badge.active .status-dot {
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.2);
  }
}

.status-text {
  white-space: nowrap;
}

/* Divider */
.stat-divider {
  width: 1px;
  height: 24px;
  background: #e2e8f0;
  flex-shrink: 0;
}

/* Stat Groups */
.stat-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-icon {
  width: 16px;
  height: 16px;
  color: var(--color-text-secondary, #64748b);
  flex-shrink: 0;
}

.stat-icon.exit {
  color: var(--color-text-muted, #94a3b8);
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-secondary, #64748b);
  white-space: nowrap;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text, #0f172a);
  font-variant-numeric: tabular-nums;
  min-width: 20px;
}

/* Highlight Stat */
.stat-item.highlight .stat-icon {
  color: var(--color-primary, #3b82f6);
}

.stat-item.highlight .stat-label {
  color: var(--color-primary, #3b82f6);
}

.highlight-value {
  color: var(--color-primary, #3b82f6) !important;
  font-size: 18px;
}

/* Last Entry */
.last-entry {
  display: flex;
  align-items: center;
  gap: 8px;
}

.last-label {
  font-size: 12px;
  color: #94a3b8;
}

.plate-badge {
  display: inline-flex;
  padding: 4px 10px;
  background: var(--color-slate-900, #0f172a);
  border-radius: var(--radius-md, 6px);
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 12px;
  font-weight: 600;
  color: white;
  letter-spacing: 0.5px;
}

.last-time {
  font-size: 11px;
  color: var(--color-text-muted, #94a3b8);
}

.last-entry.empty .last-label {
  font-style: italic;
  color: var(--color-bg-muted, #cbd5e1);
}

/* Responsive */
@media (max-width: 900px) {
  .stats-bar {
    gap: 12px;
    padding: 8px 12px;
  }

  .stat-group {
    gap: 8px;
  }

  .stat-label {
    display: none;
  }

  .last-label {
    display: none;
  }

  .last-time {
    display: none;
  }
}

@media (max-width: 600px) {
  .stat-divider {
    display: none;
  }

  .last-entry-group {
    display: none;
  }
}
</style>
