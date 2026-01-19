<script setup lang="ts">
/**
 * Container Placement Page - 3D-First Terminal View
 *
 * Canvas-first UX: Toggleable stats bar and company cards for maximum 3D space.
 * Click "Разместить" → markers appear in 3D → click marker → confirmation modal.
 *
 * Toggle States:
 * - Stats OFF + Companies OFF = Operator Mode (default, max canvas)
 * - Stats ON + Companies OFF = Quick Overview
 * - Stats ON + Companies ON = Presentation Mode (CEO demos)
 *
 * Auto-fullscreen: When entering placement mode, the view expands to fullscreen
 * for an immersive, distraction-free placement experience.
 */

import { ref, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { FullscreenExitOutlined } from '@ant-design/icons-vue';
import { usePlacementState } from '../composables/usePlacementState';
import { useFullscreen } from '../composables/useFullscreen';
import { useYardPreferences } from '../composables/useYardPreferences';
import TerminalLayout3D from '../components/TerminalLayout3D.vue';
import CompanyCards from '../components/CompanyCards.vue';
import YardStatsBar from '../components/YardStatsBar.vue';
import YardControls from '../components/YardControls.vue';
import UnplacedContainersList from '../components/UnplacedContainersList.vue';
import PlacementConfirmModal from '../components/placement/PlacementConfirmModal.vue';
import type { ContainerPlacement, UnplacedContainer, Position, PositionMarkerData } from '../types/placement';
import { parseCoordinate } from '../utils/coordinateParser';

// Route for query params (focus navigation)
const route = useRoute();

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

// Yard preferences (toggleable UI elements)
const {
  showStatsBar,
  showCompanyCards,
  toggleStatsBar,
  toggleCompanyCards,
} = useYardPreferences();

// Calculate company-filtered stats for stats bar
const filteredStats = computed(() => {
  if (!selectedCompanyName.value) {
    // All containers - use global stats
    const ladenCount = positionedContainers.value.filter(c => c.status === 'LADEN').length;
    const emptyCount = positionedContainers.value.filter(c => c.status === 'EMPTY').length;
    return {
      occupied: stats.value?.occupied ?? 0,
      available: stats.value?.available ?? 0,
      ladenCount,
      emptyCount,
    };
  }

  // Filtered by company
  const companyContainers = positionedContainers.value.filter(
    c => c.company_name === selectedCompanyName.value
  );
  return {
    occupied: companyContainers.length,
    available: stats.value?.available ?? 0, // Available stays global
    ladenCount: companyContainers.filter(c => c.status === 'LADEN').length,
    emptyCount: companyContainers.filter(c => c.status === 'EMPTY').length,
  };
});

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

// Handle focus query parameter for navigation from Tasks page
function handleFocusFromQuery(): void {
  const focusCoordinate = route.query.focus as string | undefined;
  if (focusCoordinate && terminalLayout3DRef.value) {
    const position = parseCoordinate(focusCoordinate);
    if (position) {
      // Small delay to ensure 3D scene is ready
      // Use default 40ft container size for focusing (most common)
      setTimeout(() => {
        terminalLayout3DRef.value?.focusOnPosition(position, '45G1');
      }, 500);
    }
  }
}

// Initialize data
onMounted(async () => {
  await refreshAll();
  handleFocusFromQuery();
});

// Watch for route changes to handle focus navigation
watch(() => route.query.focus, () => {
  handleFocusFromQuery();
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
</script>

<template>
  <div :class="['container-placement-page', { 'is-fullscreen': isFullscreen }]">
    <!-- Toggleable Stats Bar (hidden in fullscreen and when toggled off) -->
    <YardStatsBar
      v-if="showStatsBar && !isFullscreen"
      :occupied="filteredStats.occupied"
      :available="filteredStats.available"
      :laden-count="filteredStats.ladenCount"
      :empty-count="filteredStats.emptyCount"
      :selected-company="selectedCompanyName"
    />

    <!-- Toggleable Company filter cards (hidden in fullscreen and when toggled off) -->
    <CompanyCards
      v-if="showCompanyCards && !isFullscreen"
      :companies="companyStats"
      :selected-company="selectedCompanyName"
      :total-count="positionedContainers.length"
      @select="selectCompany"
    />

    <!-- Main 3D content with floating panels -->
    <a-card :bordered="false" :class="['main-content-card', { 'fullscreen-card': isFullscreen }]">
      <div class="terminal-container">
        <!-- Floating Controls (always visible, top-left) -->
        <YardControls
          v-if="!isFullscreen"
          :show-stats="showStatsBar"
          :show-companies="showCompanyCards"
          :loading="loading"
          @toggle-stats="toggleStatsBar"
          @toggle-companies="toggleCompanyCards"
          @refresh="refreshAll"
        />

        <!-- 3D View (always visible) -->
        <TerminalLayout3D
          ref="terminalLayout3DRef"
          :is-fullscreen="isFullscreen"
          @container-click="handle3DContainerClick"
          @marker-select="handleMarkerSelect"
        />

        <!-- Floating Unplaced Containers List (top-left, below controls) -->
        <UnplacedContainersList />

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
