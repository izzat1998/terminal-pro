<script setup lang="ts">
/**
 * PlacementPanel - Orchestrator for placement workflow
 *
 * Step-based workflow for container placement:
 * Step 0: Container selection (shows ContainerInfoCard)
 * Step 1: Position selection (recommendation + alternatives)
 * Step 2: Work order creation (options + submit)
 */

import { ref, computed, onMounted, watch } from 'vue';
import { message } from 'ant-design-vue';
import { CheckCircleOutlined } from '@ant-design/icons-vue';
import { usePlacementState } from '../composables/usePlacementState';
import { workOrderService, type TerminalVehicle } from '../services/workOrderService';
import type { Position, UnplacedContainer, WorkOrderPriority } from '../types/placement';

// Sub-components
import PlacementSteps from './placement/PlacementSteps.vue';
import ContainerInfoCard from './placement/ContainerInfoCard.vue';
import PositionSuggestionCard from './placement/PositionSuggestionCard.vue';
import PositionAlternativeGrid from './placement/PositionAlternativeGrid.vue';
import ManualPositionForm from './placement/ManualPositionForm.vue';
import WorkOrderOptions from './placement/WorkOrderOptions.vue';
import PlacementActions from './placement/PlacementActions.vue';

const props = defineProps<{
  selectedContainer?: UnplacedContainer | null;
  /** When true, recommendation was already fetched - skip step 0 */
  autoLoaded?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  placed: [];
  focusPosition: [position: Position, isoType: string];
}>();

// Placement state composable
const {
  currentSuggestion,
  startPlacement,
  cancelPlacement,
  refreshAll,
  selectedAlternativeIndex,
  selectAlternative,
  effectivePosition,
} = usePlacementState();

// Loading states
const loadingSuggest = ref(false);
const loadingConfirm = ref(false);
const showSuccess = ref(false);

// Manual position form state
const manualPosition = ref<Position>({
  zone: 'A',
  row: 1,
  bay: 1,
  tier: 1,
  sub_slot: 'A',
});
const useManualPosition = ref(false);

// Work order options state
const selectedPriority = ref<WorkOrderPriority>('MEDIUM');
const vehicles = ref<TerminalVehicle[]>([]);
const selectedVehicleId = ref<number | undefined>(undefined);
const loadingVehicles = ref(false);

// Computed: Current workflow step
// 0 = Container selected, waiting for recommendation
// 1 = Suggestion received, selecting position
// 2 = Position selected, creating work order
const currentStep = computed((): number => {
  if (!props.selectedContainer) return -1;
  if (!currentSuggestion.value && !useManualPosition.value) return 0;
  if (currentSuggestion.value || useManualPosition.value) {
    // If we have a suggestion or manual mode, we're at least at step 1
    // Move to step 2 when ready to create order (position is selected)
    if (effectivePosition.value || useManualPosition.value) return 2;
    return 1;
  }
  return 0;
});

// Computed: Position for work order
const finalPosition = computed((): Position | null => {
  if (useManualPosition.value) return manualPosition.value;
  return effectivePosition.value;
});


// Fetch terminal vehicles on mount
async function fetchVehicles(): Promise<void> {
  loadingVehicles.value = true;
  try {
    vehicles.value = await workOrderService.getTerminalVehicles();
  } catch {
    message.warning('Не удалось загрузить список техники');
  } finally {
    loadingVehicles.value = false;
  }
}

onMounted(() => {
  fetchVehicles();
});

// Watch for container changes to reset state
watch(() => props.selectedContainer, () => {
  // Reset state when container changes
  useManualPosition.value = false;
  selectedAlternativeIndex.value = -1;
  showSuccess.value = false;
});

// Request suggestion
async function handleSuggest(): Promise<void> {
  if (!props.selectedContainer || loadingSuggest.value) return;

  loadingSuggest.value = true;
  try {
    await startPlacement(props.selectedContainer.id);
  } finally {
    loadingSuggest.value = false;
  }
}

// Create work order
async function handleCreateWorkOrder(): Promise<void> {
  if (!props.selectedContainer || loadingConfirm.value || !finalPosition.value) return;

  loadingConfirm.value = true;
  try {
    const workOrder = await workOrderService.createWorkOrderFromPosition(
      props.selectedContainer.id,
      finalPosition.value,
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
      cancelPlacement();
      selectedVehicleId.value = undefined;
      showSuccess.value = false;
      refreshAll();
      emit('placed');
    }, 1500);

  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : 'Не удалось создать задачу';
    message.error(errorMsg);
  } finally {
    loadingConfirm.value = false;
  }
}

// Handle cancel
function handleCancel(): void {
  cancelPlacement();
  emit('close');
}

// Handle position selection from primary card
function handleSelectPrimary(): void {
  selectAlternative(-1);
  useManualPosition.value = false;
}

// Handle alternative selection
function handleSelectAlternative(index: number): void {
  selectAlternative(index);
  useManualPosition.value = false;
}

// Handle "Show in 3D" button click
function handleShowIn3D(position: Position): void {
  if (props.selectedContainer) {
    emit('focusPosition', position, props.selectedContainer.iso_type);
  }
}

// Handle manual position toggle
function handleManualToggle(enabled: boolean): void {
  useManualPosition.value = enabled;
  if (enabled) {
    selectAlternative(-1); // Deselect alternatives when manual is enabled
  }
}
</script>

<template>
  <!-- Wrapper: Card when standalone, div when in drawer (autoLoaded) -->
  <component :is="autoLoaded ? 'div' : 'a-card'" :class="['placement-panel', { 'in-drawer': autoLoaded }]" size="small">
    <template v-if="!autoLoaded" #title>
      <div class="panel-title">
        <span>Размещение контейнера</span>
      </div>
    </template>

    <!-- Success Animation Overlay -->
    <div v-if="showSuccess" class="success-overlay">
      <div class="success-content">
        <CheckCircleOutlined class="success-icon" />
        <span class="success-text">Задача создана!</span>
      </div>
    </div>

    <!-- Main Content -->
    <template v-if="selectedContainer && !showSuccess">
      <!-- Step Indicator -->
      <PlacementSteps :current-step="Math.max(0, currentStep)" />

      <!-- Container Info -->
      <ContainerInfoCard :container="selectedContainer" />

      <!-- Loading state when auto-loading recommendation -->
      <div v-if="autoLoaded && !currentSuggestion" class="loading-recommendation">
        <a-spin tip="Получение рекомендации..." />
      </div>

      <!-- Step 0: Get Recommendation Button (only when NOT auto-loaded) -->
      <a-button
        v-else-if="currentStep === 0 && !autoLoaded"
        type="primary"
        block
        :loading="loadingSuggest"
        class="suggest-btn"
        @click="handleSuggest"
      >
        Получить рекомендацию
      </a-button>

      <!-- Position Selection (when suggestion is available) -->
      <template v-if="currentSuggestion">
        <!-- Primary Recommendation Card -->
        <PositionSuggestionCard
          :position="currentSuggestion.suggested_position"
          :reason="currentSuggestion.reason"
          :selected="selectedAlternativeIndex === -1 && !useManualPosition"
          @select="handleSelectPrimary"
          @preview="handleShowIn3D"
        />

        <!-- Alternative Positions -->
        <PositionAlternativeGrid
          v-if="currentSuggestion.alternatives.length > 0"
          :alternatives="currentSuggestion.alternatives"
          :selected-index="useManualPosition ? -1 : selectedAlternativeIndex"
          @select="handleSelectAlternative"
          @preview="handleShowIn3D"
        />

        <!-- Manual Position Override -->
        <ManualPositionForm
          :enabled="useManualPosition"
          :position="manualPosition"
          @update:enabled="handleManualToggle"
          @update:position="(p) => manualPosition = p"
        />

        <!-- Work Order Options -->
        <WorkOrderOptions
          :vehicles="vehicles"
          :loading-vehicles="loadingVehicles"
          :selected-vehicle-id="selectedVehicleId"
          @update:selected-vehicle-id="(id) => selectedVehicleId = id"
        />

        <!-- Actions -->
        <PlacementActions
          :loading="loadingConfirm"
          :disabled="!finalPosition"
          primary-text="Создать задачу"
          :show-back="false"
          @cancel="handleCancel"
          @primary="handleCreateWorkOrder"
        />
      </template>
    </template>

    <!-- Empty State -->
    <template v-else-if="!showSuccess">
      <a-empty description="Выберите контейнер для размещения" />
    </template>
  </component>
</template>

<style scoped>
.placement-panel {
  width: var(--panel-width, 380px);
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  position: relative;

  /* CSS Custom Properties from design system */
  --placement-primary: #52c41a;
  --placement-alternative: #1677ff;
  --placement-selected: #722ed1;
}

/* When in drawer, expand to full width */
.placement-panel.in-drawer {
  width: 100%;
  max-height: none;
  padding: 16px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.suggest-btn {
  margin-bottom: 12px;
}

/* Loading recommendation state */
.loading-recommendation {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  text-align: center;
}

/* Success Overlay Animation */
.success-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  animation: fadeIn 0.3s ease;
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

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
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

/* Loading skeleton styles */
.placement-panel :deep(.ant-skeleton) {
  margin-bottom: 12px;
}
</style>
