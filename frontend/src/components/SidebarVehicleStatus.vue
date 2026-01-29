<script setup lang="ts">
/**
 * Sidebar Vehicle Status Component
 *
 * Displays terminal vehicles with their operators and work status.
 * Adapts to collapsed/expanded sidebar states.
 */

import { computed } from 'vue'
import { useTerminalVehicleStatus } from '../composables/useTerminalVehicleStatus'
import { VEHICLE_STATUS_CONFIG } from '../types/terminalVehicles'
import type { TerminalVehicleWithStatus } from '../types/terminalVehicles'

defineProps<{
  collapsed: boolean
}>()

const { vehicles, workingCount, loading } = useTerminalVehicleStatus()

/**
 * Get status icon for a vehicle
 */
function getStatusIcon(vehicle: TerminalVehicleWithStatus): string {
  return VEHICLE_STATUS_CONFIG[vehicle.status].icon
}

/**
 * Active (non-offline) vehicles for display
 */
const activeVehicles = computed(() =>
  vehicles.value.filter((v) => v.status !== 'offline')
)

/**
 * Offline vehicle count
 */
const offlineCount = computed(() =>
  vehicles.value.filter((v) => v.status === 'offline').length
)
</script>

<template>
  <!-- Expanded View -->
  <div v-if="!collapsed" class="vehicle-status-panel">
    <div class="panel-header">
      <span class="panel-title">Техника</span>
      <a-badge
        v-if="workingCount > 0"
        :count="workingCount"
        :number-style="{ backgroundColor: '#fa8c16' }"
        :title="`${workingCount} работает`"
      />
    </div>

    <!-- Loading state -->
    <div v-if="loading && vehicles.length === 0" class="loading-state">
      <a-spin size="small" />
    </div>

    <!-- Vehicle list -->
    <div v-else class="vehicle-list">
      <a-empty v-if="activeVehicles.length === 0 && offlineCount === 0" :image="false" style="padding: 12px;">
        <template #description>
          <span style="color: rgba(255, 255, 255, 0.45); font-size: 12px;">Нет техники</span>
        </template>
      </a-empty>
      <div
        v-for="vehicle in activeVehicles"
        :key="vehicle.id"
        class="vehicle-item"
      >
        <div class="vehicle-header">
          <span class="status-icon">{{ getStatusIcon(vehicle) }}</span>
          <span class="vehicle-name">{{ vehicle.name }}</span>
        </div>

        <div class="vehicle-details">
          <span class="operator-name">
            {{ vehicle.operator_name || 'Нет оператора' }}
          </span>

          <!-- Current task info if working -->
          <div v-if="vehicle.current_task" class="task-info">
            <span class="container-number">
              {{ vehicle.current_task.container_number }}
            </span>
            <span class="target-arrow">→</span>
            <span class="target-coord">
              {{ vehicle.current_task.target_coordinate }}
            </span>
          </div>
        </div>
      </div>

      <!-- Offline count -->
      <div v-if="offlineCount > 0" class="offline-summary">
        <span class="status-icon">⚪</span>
        <span class="offline-text">{{ offlineCount }} оффлайн</span>
      </div>
    </div>
  </div>

  <!-- Collapsed View -->
  <div v-else class="vehicle-status-collapsed">
    <a-tooltip placement="right" :title="`Техника: ${workingCount} работает`">
      <div class="collapsed-indicator">
        <span class="collapsed-icon">🚜</span>
        <a-badge
          v-if="workingCount > 0"
          :count="workingCount"
          :number-style="{
            backgroundColor: '#fa8c16',
            fontSize: '10px',
            minWidth: '14px',
            height: '14px',
            lineHeight: '14px',
          }"
          :offset="[-2, 2]"
        />
      </div>
    </a-tooltip>
  </div>
</template>

<style scoped>
/* Panel styling */
.vehicle-status-panel {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin-top: auto;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 0 4px;
}

.panel-title {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.45);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Loading state */
.loading-state {
  display: flex;
  justify-content: center;
  padding: 16px;
}

/* Vehicle list */
.vehicle-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.vehicle-item {
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  transition: background 0.15s ease;
}

.vehicle-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.vehicle-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.status-icon {
  font-size: 12px;
  line-height: 1;
}

.vehicle-name {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
}

.vehicle-details {
  padding-left: 20px;
}

.operator-name {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  display: block;
}

/* Task info */
.task-info {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.65);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
}

.container-number {
  color: var(--ant-color-warning, #fa8c16);
}

.target-arrow {
  color: rgba(255, 255, 255, 0.35);
}

.target-coord {
  color: var(--ant-color-primary, #1890ff);
}

/* Offline summary */
.offline-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.45);
}

.offline-text {
  font-style: italic;
}

/* Collapsed view */
.vehicle-status-collapsed {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin-top: auto;
  display: flex;
  justify-content: center;
}

.collapsed-indicator {
  position: relative;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  cursor: default;
  transition: background 0.15s ease;
}

.collapsed-indicator:hover {
  background: rgba(255, 255, 255, 0.08);
}

.collapsed-icon {
  font-size: 16px;
}
</style>
