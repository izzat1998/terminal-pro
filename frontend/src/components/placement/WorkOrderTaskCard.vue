<script setup lang="ts">
/**
 * WorkOrderTaskCard - Individual task card showing work order details
 *
 * Displays container number, target position, priority, time remaining,
 * and vehicle assignment dropdown.
 */

import { computed, ref } from 'vue';
import { ClockCircleOutlined, EnvironmentOutlined } from '@ant-design/icons-vue';
import dayjs from '@/config/dayjs';
import type { WorkOrder } from '../../types/placement';
import type { TerminalVehicle } from '../../services/workOrderService';

interface Props {
  task: WorkOrder;
  vehicles: TerminalVehicle[];
  isSelected?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isSelected: false,
});

const emit = defineEmits<{
  click: [task: WorkOrder];
  assign: [taskId: number, vehicleId: number];
}>();

const assigning = ref(false);

// Priority color and label
const priorityConfig = computed((): { color: string; label: string } => {
  const config: Record<string, { color: string; label: string }> = {
    LOW: { color: '#8c8c8c', label: 'Низкий' },
    MEDIUM: { color: '#1677ff', label: 'Средний' },
    HIGH: { color: '#fa8c16', label: 'Высокий' },
    URGENT: { color: '#f5222d', label: 'Срочный' },
  };
  const defaultConfig = { color: '#1677ff', label: 'Средний' };
  return config[props.task.priority] ?? defaultConfig;
});

// Time since creation (for display)
const timeElapsed = computed(() => {
  const created = dayjs(props.task.created_at);
  const now = dayjs();
  const diffMins = now.diff(created, 'minute');

  if (diffMins < 60) {
    return { text: `${diffMins} мин назад`, isOld: diffMins > 30 };
  }

  const hours = Math.floor(diffMins / 60);
  const mins = diffMins % 60;
  return { text: `${hours}ч ${mins}м назад`, isOld: hours > 2 };
});

// Vehicle type icon
function getVehicleIcon(type: string): string {
  const icons: Record<string, string> = {
    REACH_STACKER: '🚜',
    FORKLIFT: '🏗️',
    YARD_TRUCK: '🚛',
    RTG_CRANE: '🏗️',
  };
  return icons[type] ?? '🚛';
}

// Handle vehicle selection
async function handleAssign(vehicleId: number): Promise<void> {
  assigning.value = true;
  try {
    emit('assign', props.task.id, vehicleId);
  } finally {
    assigning.value = false;
  }
}
</script>

<template>
  <div
    :class="['task-card', { 'is-selected': isSelected }]"
    @click="emit('click', task)"
  >
    <!-- Header: Priority & Order Number & Time -->
    <div class="task-header">
      <div class="header-left">
        <span
          class="priority-dot"
          :style="{ backgroundColor: priorityConfig.color }"
        />
        <span class="priority-label">{{ priorityConfig.label }}</span>
        <span class="order-number">#{{ task.order_number }}</span>
      </div>
      <div class="time-elapsed" :class="{ 'is-old': timeElapsed.isOld }">
        <ClockCircleOutlined class="time-icon" />
        <span>{{ timeElapsed.text }}</span>
      </div>
    </div>

    <!-- Container Info -->
    <div class="container-info">
      <div class="container-number">{{ task.container_number }}</div>
      <div class="target-position">
        <EnvironmentOutlined class="position-icon" />
        <span>{{ task.target_coordinate }}</span>
      </div>
    </div>

    <!-- Vehicle Assignment -->
    <div class="assignment-row">
      <div v-if="task.assigned_to_vehicle" class="assigned-vehicle">
        <span class="vehicle-icon">{{ getVehicleIcon(task.assigned_to_vehicle.vehicle_type) }}</span>
        <span class="vehicle-name">{{ task.assigned_to_vehicle.name }}</span>
        <a-tag size="small" color="processing">Назначено</a-tag>
      </div>
      <a-select
        v-else
        placeholder="Назначить технику"
        size="small"
        class="vehicle-select"
        :loading="assigning"
        @change="handleAssign"
        @click.stop
      >
        <a-select-option v-for="v in vehicles" :key="v.id" :value="v.id">
          {{ getVehicleIcon(v.vehicle_type) }} {{ v.name }}
        </a-select-option>
      </a-select>
    </div>
  </div>
</template>

<style scoped>
.task-card {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.2s ease;
}

.task-card:hover {
  background: #f5f5f5;
}

.task-card.is-selected {
  background: #e6f4ff;
  border-left: 3px solid #1677ff;
  padding-left: 9px;
}

.task-card:last-child {
  border-bottom: none;
}

/* Header */
.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.priority-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.priority-label {
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
}

.order-number {
  font-size: 11px;
  color: #8c8c8c;
  font-family: monospace;
}

/* Time elapsed */
.time-elapsed {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #595959;
}

.time-elapsed.is-old {
  color: #fa8c16;
  font-weight: 600;
}

.time-icon {
  font-size: 12px;
}

/* Container info */
.container-info {
  margin-bottom: 10px;
}

.container-number {
  font-family: monospace;
  font-size: 14px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 4px;
}

.target-position {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #595959;
}

.position-icon {
  font-size: 12px;
  color: #1677ff;
}

/* Assignment row */
.assignment-row {
  display: flex;
  align-items: center;
}

.assigned-vehicle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.vehicle-icon {
  font-size: 14px;
}

.vehicle-name {
  color: #262626;
  font-weight: 500;
}

.vehicle-select {
  width: 100%;
}
</style>
