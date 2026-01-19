<script setup lang="ts">
/**
 * WorkOrderOptions - Vehicle select for work order configuration
 *
 * Work order configuration options for Step 3 of the placement workflow.
 * Priority is set to MEDIUM by default and hidden from UI.
 */

interface TerminalVehicle {
  id: number;
  name: string;
  vehicle_type: 'REACH_STACKER' | 'FORKLIFT' | 'YARD_TRUCK' | 'RTG_CRANE';
  vehicle_type_display: string;
  license_plate: string;
}

const props = defineProps<{
  vehicles: TerminalVehicle[];
  loadingVehicles: boolean;
  selectedVehicleId?: number;
}>();

const emit = defineEmits<{
  'update:selectedVehicleId': [id: number | undefined];
}>();

// Vehicle type icons (emoji)
const vehicleTypeIcons: Record<string, string> = {
  REACH_STACKER: '🏗️',
  FORKLIFT: '🚜',
  YARD_TRUCK: '🚛',
  RTG_CRANE: '🏭',
};

// Get icon for vehicle type
function getVehicleIcon(vehicleType: string): string {
  return vehicleTypeIcons[vehicleType] || '🚜';
}
</script>

<template>
  <div class="work-order-options">
    <!-- Vehicle Assignment -->
    <div class="option-section">
      <div class="option-header">
        <span class="option-label">Назначить технику</span>
        <span class="option-hint">(необязательно)</span>
      </div>
      <a-select
        :value="selectedVehicleId"
        placeholder="Выберите технику"
        style="width: 100%"
        allow-clear
        :loading="loadingVehicles"
        @change="(v: number | undefined) => emit('update:selectedVehicleId', v)"
      >
        <a-select-option v-for="vehicle in vehicles" :key="vehicle.id" :value="vehicle.id">
          <div class="vehicle-option">
            <span class="vehicle-icon">{{ getVehicleIcon(vehicle.vehicle_type) }}</span>
            <span class="vehicle-name">{{ vehicle.name }}</span>
            <span class="vehicle-type">{{ vehicle.vehicle_type_display }}</span>
          </div>
        </a-select-option>
      </a-select>

      <a-alert
        v-if="selectedVehicleId"
        type="success"
        class="assignment-info"
        show-icon
      >
        <template #message>
          Техника будет назначена на задачу
        </template>
      </a-alert>
      <div v-else class="unassigned-hint">
        Если не выбрано, задача будет в статусе "Ожидает назначения"
      </div>
    </div>
  </div>
</template>

<style scoped>
.work-order-options {
  /* Container styling */
}

.option-section {
  margin-bottom: 16px;
}

.option-section:last-child {
  margin-bottom: 0;
}

.option-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.option-label {
  font-size: 13px;
  font-weight: 500;
  color: #262626;
}

.option-hint {
  font-size: 11px;
  color: #8c8c8c;
}

.sla-badge {
  font-size: 11px;
  padding: 2px 8px;
  background: #e6f4ff;
  color: #1677ff;
  border-radius: 4px;
  font-weight: 500;
}

/* Vehicle dropdown option styling */
.vehicle-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.vehicle-icon {
  font-size: 16px;
}

.vehicle-name {
  font-weight: 500;
}

.vehicle-type {
  font-size: 12px;
  color: #8c8c8c;
  margin-left: auto;
}

/* Assignment info */
.assignment-info {
  margin-top: 8px;
}

.assignment-info :deep(.ant-alert-message) {
  font-size: 12px;
}

.unassigned-hint {
  margin-top: 6px;
  font-size: 11px;
  color: #8c8c8c;
}
</style>
