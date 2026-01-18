<script setup lang="ts">
/**
 * Container Placement Page - 3D-First Terminal View
 *
 * Streamlined UX: 3D view with floating unplaced containers list.
 * Click "Разместить" → markers appear in 3D → click marker → confirmation modal.
 *
 * Auto-fullscreen: When entering placement mode, the view expands to fullscreen
 * for an immersive, distraction-free placement experience.
 */

import { ref, computed, onMounted, watch } from 'vue';
import { ReloadOutlined, FullscreenExitOutlined } from '@ant-design/icons-vue';
import { usePlacementState } from '../composables/usePlacementState';
import { useFullscreen } from '../composables/useFullscreen';
import TerminalLayout3D from '../components/TerminalLayout3D.vue';
import CompanyCards from '../components/CompanyCards.vue';
import UnplacedContainersList from '../components/UnplacedContainersList.vue';
import PlacementConfirmModal from '../components/placement/PlacementConfirmModal.vue';
import WorkOrderTaskPanel from '../components/placement/WorkOrderTaskPanel.vue';
import type { ContainerPlacement, UnplacedContainer, Position, PositionMarkerData, WorkOrder } from '../types/placement';

// State from composable
const {
  positionedContainers,
  unplacedContainers,
  stats,
  loading,
  selectContainer,
  refreshAll,
  // Company filtering
  companyStats,
  selectedCompanyName,
  selectCompany,
  // Placement mode
  placingContainerId,
  effectivePosition,
  exitPlacementMode,
  isPlacementMode,
} = usePlacementState();

// Fullscreen state for immersive placement experience
const { isFullscreen, enterFullscreen, exitFullscreen } = useFullscreen();

// Auto-enter fullscreen when placement mode starts
watch(isPlacementMode, (active) => {
  if (active) {
    enterFullscreen();
  } else {
    exitFullscreen();
  }
});

// Sync: if user manually exits fullscreen (ESC), also exit placement mode
watch(isFullscreen, (active) => {
  if (!active && isPlacementMode.value) {
    exitPlacementMode();
  }
});

// Confirmation modal state
const showConfirmModal = ref(false);
const selectedMarkerData = ref<PositionMarkerData | null>(null);

// Ref to TerminalLayout3D for camera control
const terminalLayout3DRef = ref<InstanceType<typeof TerminalLayout3D> | null>(null);

// Find the container being placed
const placingContainer = computed((): UnplacedContainer | null => {
  if (!placingContainerId.value) return null;
  return unplacedContainers.value.find(c => c.id === placingContainerId.value) ?? null;
});

// Get selected position from marker data or effective position
const selectedPosition = computed((): Position | null => {
  if (!selectedMarkerData.value) return effectivePosition.value;
  return selectedMarkerData.value.position;
});

// Get coordinate string for modal display
const selectedCoordinate = computed((): string => {
  if (selectedMarkerData.value) return selectedMarkerData.value.coordinate;
  return effectivePosition.value?.coordinate ?? '';
});

// Check if selected position is recommended (primary or alternative) vs just available
const isSelectedRecommended = computed((): boolean => {
  if (!selectedMarkerData.value) return true;
  return selectedMarkerData.value.type !== 'available';
});

// Initialize data
onMounted(async () => {
  await refreshAll();
});

// Handle 3D container click
function handle3DContainerClick(container: ContainerPlacement): void {
  selectContainer(container.id);
}

// Handle marker selection in 3D view
function handleMarkerSelect(marker: PositionMarkerData): void {
  selectedMarkerData.value = marker;
  showConfirmModal.value = true;
}

// Handle modal confirmation (work order created)
async function handleModalConfirm(): Promise<void> {
  showConfirmModal.value = false;
  selectedMarkerData.value = null;
  exitPlacementMode();
  await refreshAll();
}

// Handle modal cancel
function handleModalCancel(): void {
  showConfirmModal.value = false;
  selectedMarkerData.value = null;
  // Don't exit placement mode - user might want to select a different marker
}

// Handle focus request from task panel
function handleFocusTask(task: WorkOrder): void {
  const position: Position = {
    zone: task.target_zone,
    row: task.target_row,
    bay: task.target_bay,
    tier: task.target_tier,
    sub_slot: task.target_sub_slot,
    coordinate: task.target_coordinate,
  };
  terminalLayout3DRef.value?.focusOnPosition(position, task.iso_type);
}
</script>

<template>
  <div :class="['container-placement-page', { 'is-fullscreen': isFullscreen }]">
    <!-- Header with stats (hidden in fullscreen) -->
    <a-card v-show="!isFullscreen" class="header-card" :bordered="false">
      <a-row :gutter="16" align="middle">
        <a-col :span="18">
          <a-space size="large">
            <a-statistic
              title="На терминале"
              :value="stats?.occupied ?? 0"
              :value-style="{ color: '#1677ff' }"
            />
            <a-statistic
              title="Свободных позиций"
              :value="stats?.available ?? 0"
              :value-style="{ color: '#52c41a' }"
            />
            <a-statistic
              title="Без позиции"
              :value="unplacedContainers.length"
              :value-style="{ color: unplacedContainers.length > 0 ? '#fa8c16' : '#52c41a' }"
            />
          </a-space>
        </a-col>
        <a-col :span="6" style="text-align: right">
          <a-button @click="refreshAll" :loading="loading">
            <template #icon><ReloadOutlined /></template>
            Обновить
          </a-button>
        </a-col>
      </a-row>
    </a-card>

    <!-- Company filter cards (hidden in fullscreen) -->
    <CompanyCards
      v-show="!isFullscreen"
      :companies="companyStats"
      :selected-company="selectedCompanyName"
      :total-count="positionedContainers.length"
      @select="selectCompany"
    />

    <!-- Main 3D content with floating panel -->
    <a-card :bordered="false" :class="['main-content-card', { 'fullscreen-card': isFullscreen }]">
      <div class="terminal-container">
        <!-- 3D View (always visible) -->
        <TerminalLayout3D
          ref="terminalLayout3DRef"
          :is-fullscreen="isFullscreen"
          @container-click="handle3DContainerClick"
          @marker-select="handleMarkerSelect"
        />

        <!-- Floating Unplaced Containers List (top-left) -->
        <UnplacedContainersList />

        <!-- Floating Work Order Task Panel (top-right) -->
        <WorkOrderTaskPanel @focus-task="handleFocusTask" />

        <!-- Fullscreen Exit Hint -->
        <div v-if="isFullscreen" class="fullscreen-exit-hint">
          <a-button
            type="text"
            class="exit-btn"
            @click="exitPlacementMode"
          >
            <template #icon><FullscreenExitOutlined /></template>
            ESC для выхода
          </a-button>
        </div>
      </div>
    </a-card>

    <!-- Placement Confirmation Modal -->
    <PlacementConfirmModal
      :open="showConfirmModal"
      :container="placingContainer"
      :position="selectedPosition"
      :coordinate="selectedCoordinate"
      :is-recommended="isSelectedRecommended"
      @confirm="handleModalConfirm"
      @cancel="handleModalCancel"
    />
  </div>
</template>

<style scoped>
.container-placement-page {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header-card {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.main-content-card {
  flex: 1;
  min-height: 0;
}

.main-content-card :deep(.ant-card-body) {
  height: 100%;
  padding: 0;
}

/* Container for 3D view with floating panels */
.terminal-container {
  position: relative;
  height: 100%;
  min-height: 600px;
}

/* ═══════════════════════════════════════════════════════════════════
   FULLSCREEN MODE STYLES
   Immersive experience when placing containers - covers entire viewport
   ═══════════════════════════════════════════════════════════════════ */

.container-placement-page.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 1000;
  padding: 0;
  background: #d4d4d4; /* Matches ground color for seamless look */
}

.container-placement-page.is-fullscreen .fullscreen-card {
  position: absolute;
  inset: 0;
  margin: 0;
  border-radius: 0;
  border: none;
}

.container-placement-page.is-fullscreen .fullscreen-card :deep(.ant-card-body) {
  height: 100%;
  padding: 0;
}

.container-placement-page.is-fullscreen .terminal-container {
  min-height: 100%;
  height: 100%;
}

/* Fullscreen exit hint - positioned at top right */
.fullscreen-exit-hint {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 20;
}

.fullscreen-exit-hint .exit-btn {
  background: rgba(255, 255, 255, 0.9);
  color: #595959;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 12px;
  height: auto;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

.fullscreen-exit-hint .exit-btn:hover {
  background: #fff;
  color: #262626;
  border-color: #1677ff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}
</style>
