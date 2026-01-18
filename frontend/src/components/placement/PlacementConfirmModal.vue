<script setup lang="ts">
/**
 * PlacementConfirmModal - Confirmation modal for 3D-first placement workflow
 *
 * Shows when user clicks a position marker in 3D view.
 * Allows vehicle selection, priority selection, and work order creation.
 */

import { ref, computed, onMounted, watch } from 'vue';
import { message } from 'ant-design-vue';
import { EnvironmentOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons-vue';
import { workOrderService, type TerminalVehicle } from '../../services/workOrderService';
import type { Position, UnplacedContainer, WorkOrderPriority } from '../../types/placement';

const props = defineProps<{
  open: boolean;
  container: UnplacedContainer | null;
  position: Position | null;
  coordinate: string;
  isRecommended?: boolean; // True if primary or alternative, false if just "available" slot
}>();

const emit = defineEmits<{
  'update:open': [value: boolean];
  confirm: [];
  cancel: [];
}>();

// Work order options state
const selectedPriority = ref<WorkOrderPriority>('MEDIUM');
const vehicles = ref<TerminalVehicle[]>([]);
const selectedVehicleId = ref<number | undefined>(undefined);
const loadingVehicles = ref(false);
const loadingConfirm = ref(false);
const showSuccess = ref(false);

// SLA time estimates by priority
const slaEstimates: Record<WorkOrderPriority, string> = {
  LOW: '4 часа',
  MEDIUM: '2 часа',
  HIGH: '1 час',
  URGENT: '30 минут',
};

// Computed SLA text
const currentSLA = computed(() => slaEstimates[selectedPriority.value]);

// Priority options for segmented control
const priorityOptions = [
  { value: 'LOW', label: 'Низкий' },
  { value: 'MEDIUM', label: 'Средний' },
  { value: 'HIGH', label: 'Высокий' },
  { value: 'URGENT', label: 'Срочно' },
];

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

// Fetch terminal vehicles on mount
async function fetchVehicles(): Promise<void> {
  loadingVehicles.value = true;
  try {
    vehicles.value = await workOrderService.getTerminalVehicles();
  } catch (e) {
    console.warn('Failed to fetch vehicles:', e);
    message.warning('Не удалось загрузить список техники');
  } finally {
    loadingVehicles.value = false;
  }
}

onMounted(() => {
  fetchVehicles();
});

// Reset state when modal opens
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    selectedPriority.value = 'MEDIUM';
    selectedVehicleId.value = undefined;
    showSuccess.value = false;
  }
});

// Handle confirm click
async function handleConfirm(): Promise<void> {
  if (!props.container || !props.position || loadingConfirm.value) return;

  loadingConfirm.value = true;
  try {
    const workOrder = await workOrderService.createWorkOrderFromPosition(
      props.container.id,
      props.position,
      selectedPriority.value,
      selectedVehicleId.value,
    );

    // Show success animation
    showSuccess.value = true;

    // Show success message
    const vehicleName = selectedVehicleId.value
      ? vehicles.value.find(v => v.id === selectedVehicleId.value)?.name
      : null;
    const assignedText = vehicleName ? ` Назначено: ${vehicleName}` : ' Не назначено';
    message.success(`Задача ${workOrder.order_number} создана.${assignedText}`);

    // Cleanup after animation
    setTimeout(() => {
      emit('confirm');
    }, 1200);

  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : 'Не удалось создать задачу';
    message.error(errorMsg);
  } finally {
    loadingConfirm.value = false;
  }
}

// Handle cancel
function handleCancel(): void {
  emit('cancel');
}
</script>

<template>
  <a-modal
    :open="open"
    title="Подтверждение размещения"
    :width="420"
    :closable="!showSuccess"
    :mask-closable="!showSuccess && !loadingConfirm"
    :footer="null"
    @cancel="handleCancel"
  >
    <!-- Success Animation -->
    <div v-if="showSuccess" class="success-overlay">
      <div class="success-content">
        <CheckCircleOutlined class="success-icon" />
        <span class="success-text">Задача создана!</span>
      </div>
    </div>

    <!-- Main Content -->
    <div v-else class="modal-content">
      <!-- Position Info -->
      <div class="position-info" :class="{ 'not-recommended': !isRecommended }">
        <div class="position-header">
          <EnvironmentOutlined class="position-icon" />
          <span class="position-label">Выбранная позиция</span>
        </div>
        <div class="position-coordinate">{{ coordinate }}</div>
      </div>

      <!-- Warning for non-recommended position -->
      <a-alert
        v-if="isRecommended === false"
        type="warning"
        show-icon
        class="not-recommended-warning"
      >
        <template #icon><WarningOutlined /></template>
        <template #message>Не рекомендуемая позиция</template>
        <template #description>
          Эта позиция не была рекомендована алгоритмом оптимизации. Продолжить?
        </template>
      </a-alert>

      <!-- Container Info (brief) -->
      <div v-if="container" class="container-info">
        <span class="container-number">{{ container.container_number }}</span>
        <a-tag :color="container.status === 'LADEN' ? 'green' : 'blue'" size="small">
          {{ container.status === 'LADEN' ? 'Груж.' : 'Пор.' }}
        </a-tag>
        <span class="iso-type">{{ container.iso_type }}</span>
      </div>

      <a-divider />

      <!-- Vehicle Assignment -->
      <div class="option-section">
        <div class="option-header">
          <span class="option-label">Назначить технику</span>
          <span class="option-hint">(необязательно)</span>
        </div>
        <a-select
          v-model:value="selectedVehicleId"
          placeholder="Выберите технику"
          style="width: 100%"
          allow-clear
          :loading="loadingVehicles"
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

      <!-- Priority Selection -->
      <div class="option-section">
        <div class="option-header">
          <span class="option-label">Приоритет</span>
          <span class="sla-badge">SLA: {{ currentSLA }}</span>
        </div>
        <a-segmented
          v-model:value="selectedPriority"
          :options="priorityOptions"
          block
        />
      </div>

      <!-- Actions -->
      <div class="modal-actions">
        <a-button @click="handleCancel" :disabled="loadingConfirm">
          Отмена
        </a-button>
        <a-button
          type="primary"
          :loading="loadingConfirm"
          @click="handleConfirm"
        >
          Создать задачу
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<style scoped>
.modal-content {
  position: relative;
}

/* Position display */
.position-info {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
}

.position-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.position-icon {
  font-size: 16px;
  color: #52c41a;
}

.position-label {
  font-size: 12px;
  color: #52c41a;
  font-weight: 500;
}

.position-coordinate {
  font-family: monospace;
  font-size: 18px;
  font-weight: 600;
  color: #237804;
  letter-spacing: 0.5px;
}

/* Not recommended position styling (gray/orange instead of green) */
.position-info.not-recommended {
  background: #fffbe6;
  border-color: #ffe58f;
}

.position-info.not-recommended .position-icon {
  color: #faad14;
}

.position-info.not-recommended .position-label {
  color: #d48806;
}

.position-info.not-recommended .position-coordinate {
  color: #ad6800;
}

/* Warning alert for non-recommended positions */
.not-recommended-warning {
  margin-bottom: 12px;
}

.not-recommended-warning :deep(.ant-alert-description) {
  font-size: 12px;
}

/* Container info */
.container-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.container-number {
  font-family: monospace;
  font-weight: 600;
  color: #262626;
}

.iso-type {
  font-size: 12px;
  color: #8c8c8c;
}

/* Option sections */
.option-section {
  margin-bottom: 16px;
}

.option-section:last-of-type {
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

/* Actions */
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

/* Success animation */
.success-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.success-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  animation: scaleIn 0.4s ease;
}

.success-icon {
  font-size: 48px;
  color: #52c41a;
}

.success-text {
  font-size: 18px;
  font-weight: 600;
  color: #262626;
}

@keyframes scaleIn {
  from {
    transform: scale(0.5);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
