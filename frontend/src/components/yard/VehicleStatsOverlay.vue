<script setup lang="ts">
/**
 * VehicleStatsOverlay - Professional vehicle statistics panel
 *
 * Floating panel showing real-time vehicle detection statistics
 * with elegant typography and subtle animations.
 */

import { computed } from 'vue'
import type { VehicleType } from '@/composables/useVehicleModels'

interface VehicleEntry {
  id: string
  plateNumber: string
  vehicleType: VehicleType
  timestamp: number
}

interface Props {
  entries: VehicleEntry[]
  visible?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  visible: true,
})

// Computed stats
const totalEntries = computed(() => props.entries.length)

const truckCount = computed(() =>
  props.entries.filter(e => e.vehicleType === 'TRUCK').length
)

const carCount = computed(() =>
  props.entries.filter(e => e.vehicleType === 'CAR').length
)

const wagonCount = computed(() =>
  props.entries.filter(e => e.vehicleType === 'WAGON').length
)

const lastEntry = computed(() => {
  if (props.entries.length === 0) return null
  return [...props.entries].sort((a, b) => b.timestamp - a.timestamp)[0]
})

const lastEntryTime = computed(() => {
  if (!lastEntry.value) return ''
  const date = new Date(lastEntry.value.timestamp)
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
})

const vehicleTypeLabels: Record<VehicleType, string> = {
  TRUCK: 'Грузовик',
  CAR: 'Легковой',
  WAGON: 'Вагон',
  UNKNOWN: 'Неизвестно',
}
</script>

<template>
  <Transition name="panel-slide">
    <div v-if="visible && totalEntries > 0" class="stats-panel">
      <!-- Header -->
      <div class="panel-header">
        <svg class="header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="20" x2="18" y2="10"/>
          <line x1="12" y1="20" x2="12" y2="4"/>
          <line x1="6" y1="20" x2="6" y2="14"/>
        </svg>
        <span class="header-title">Въезды сегодня</span>
      </div>

      <!-- Total Counter -->
      <div class="total-section">
        <div class="total-ring">
          <span class="total-value">{{ totalEntries }}</span>
        </div>
        <span class="total-label">транспорта</span>
      </div>

      <!-- Breakdown by Type -->
      <div class="breakdown-section">
        <div v-if="truckCount > 0" class="type-row">
          <div class="type-info">
            <svg class="type-icon truck" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 3h15v13H1z"/>
              <path d="M16 8h4l3 3v5h-7V8z"/>
              <circle cx="5.5" cy="18.5" r="2.5"/>
              <circle cx="18.5" cy="18.5" r="2.5"/>
            </svg>
            <span class="type-label">Грузовики</span>
          </div>
          <span class="type-value">{{ truckCount }}</span>
        </div>

        <div v-if="carCount > 0" class="type-row">
          <div class="type-info">
            <svg class="type-icon car" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 17H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h1"/>
              <path d="M19 17h1a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2h-1"/>
              <path d="M5 9V7a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2"/>
              <rect x="5" y="9" width="14" height="8" rx="2"/>
              <circle cx="8" cy="17" r="2"/>
              <circle cx="16" cy="17" r="2"/>
            </svg>
            <span class="type-label">Легковые</span>
          </div>
          <span class="type-value">{{ carCount }}</span>
        </div>

        <div v-if="wagonCount > 0" class="type-row">
          <div class="type-info">
            <svg class="type-icon wagon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="5" width="22" height="14" rx="2"/>
              <line x1="1" y1="10" x2="23" y2="10"/>
              <circle cx="6" cy="19" r="2"/>
              <circle cx="18" cy="19" r="2"/>
            </svg>
            <span class="type-label">Вагоны</span>
          </div>
          <span class="type-value">{{ wagonCount }}</span>
        </div>
      </div>

      <!-- Last Entry -->
      <div v-if="lastEntry" class="last-entry-section">
        <div class="section-divider"></div>
        <div class="last-entry-header">
          <svg class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          <span class="last-entry-label">Последний въезд</span>
        </div>
        <div class="last-plate">{{ lastEntry.plateNumber }}</div>
        <div class="last-meta">
          <span class="last-type">{{ vehicleTypeLabels[lastEntry.vehicleType] }}</span>
          <span class="last-divider">•</span>
          <span class="last-time">{{ lastEntryTime }}</span>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.stats-panel {
  position: absolute;
  top: 16px;
  left: 240px;
  width: 200px;
  background: var(--color-bg-card, white);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-lg, 16px);
  box-shadow: var(--shadow-md, 0 4px 20px rgba(0, 0, 0, 0.08));
  z-index: 50;
  overflow: hidden;
  font-family: var(--font-body, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
}

/* Header */
.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: linear-gradient(to bottom, var(--color-bg-page, #f8fafc), var(--color-bg-card, #ffffff));
  border-bottom: 1px solid var(--color-border-light, #f1f5f9);
}

.header-icon {
  width: 18px;
  height: 18px;
  color: var(--color-primary, #3b82f6);
}

.header-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text, #0f172a);
}

/* Total Section */
.total-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 16px;
}

.total-ring {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, var(--color-primary-light, #dbeafe) 0%, var(--color-primary-lighter, #eff6ff) 100%);
  border: 3px solid var(--color-primary, #3b82f6);
  border-radius: 50%;
  margin-bottom: 8px;
}

.total-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-primary, #3b82f6);
  font-variant-numeric: tabular-nums;
}

.total-label {
  font-size: 12px;
  color: var(--color-text-secondary, #64748b);
}

/* Breakdown Section */
.breakdown-section {
  padding: 0 16px 16px;
}

.type-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
}

.type-row + .type-row {
  border-top: 1px solid var(--color-border-light, #f1f5f9);
}

.type-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-icon {
  width: 18px;
  height: 18px;
}

.type-icon.truck {
  color: var(--color-primary, #3b82f6);
}

.type-icon.car {
  color: var(--color-success, #10b981);
}

.type-icon.wagon {
  color: var(--color-warning, #d97706);
}

.type-label {
  font-size: 13px;
  color: var(--color-text-secondary, #475569);
}

.type-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text, #0f172a);
  font-variant-numeric: tabular-nums;
}

/* Last Entry Section */
.last-entry-section {
  padding: 0 16px 16px;
}

.section-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-border, #e2e8f0), transparent);
  margin-bottom: 14px;
}

.last-entry-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.check-icon {
  width: 14px;
  height: 14px;
  color: var(--color-success, #10b981);
}

.last-entry-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted, #94a3b8);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.last-plate {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-success, #10b981);
  text-align: center;
  padding: 8px;
  background: var(--color-entry-lighter, #f0fdf4);
  border: 1px solid var(--color-success-light, #bbf7d0);
  border-radius: var(--radius-md, 8px);
  margin-bottom: 8px;
}

.last-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-secondary, #64748b);
}

.last-divider {
  color: var(--color-bg-muted, #cbd5e1);
}

.last-time {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-variant-numeric: tabular-nums;
}

/* Transition */
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all 300ms ease;
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}
</style>
