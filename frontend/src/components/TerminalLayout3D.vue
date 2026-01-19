<script setup lang="ts">
/**
 * 3D Terminal Visualization Component
 * Renders the terminal yard with positioned containers using Three.js
 * Features: Light theme, interactive tooltips, 20ft/40ft size distinction
 */

import { ref, watch, computed, onMounted, onUnmounted } from 'vue';
import * as THREE from 'three';
import {
  ReloadOutlined,
  TagOutlined,
  TagFilled,
  HeatMapOutlined,
  FontSizeOutlined,
  ExpandOutlined,
  QuestionCircleOutlined,
  CameraOutlined
} from '@ant-design/icons-vue';
import { use3DScene, type CameraPreset } from '../composables/use3DScene';
import { useContainerMesh } from '../composables/useContainerMesh';
import { usePlacementState } from '../composables/usePlacementState';
import type { ContainerPlacement, ZoneCode, PositionMarkerData } from '../types/placement';
import { ZONE_LAYOUT, SPACING, getContainerSize, isHighCube } from '../types/placement';

// Simple throttle function for performance
function throttle<T extends (...args: Parameters<T>) => ReturnType<T>>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false;
  return function (this: ThisParameterType<T>, ...args: Parameters<T>): void {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

// Zone colors (darker for light theme visibility)
// Currently only Zone A for simplified version
const ZONE_COLORS: Partial<Record<ZoneCode, number>> = {
  A: 0x2980b9,
};

const ZONES: ZoneCode[] = ['A'];

function getLegendColor(zone: ZoneCode): string {
  const color = ZONE_COLORS[zone] ?? 0x888888;
  return '#' + color.toString(16).padStart(6, '0');
}

// Props
interface Props {
  isFullscreen?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isFullscreen: false,
});

const emit = defineEmits<{
  containerClick: [container: ContainerPlacement];
  containerHover: [container: ContainerPlacement | null];
  markerSelect: [marker: PositionMarkerData];
}>();

// Canvas ref
const canvasRef = ref<HTMLCanvasElement>();

// Error state for Three.js initialization
const threeError = ref<string | null>(null);

// Composables
const { scene, camera, currentPreset, initScene, handleResize, resetCamera, setCameraPreset, fitToContainers, focusOnPosition } = use3DScene(canvasRef);

// Navigation help popover visibility
const showNavHelp = ref(false);

// Camera preset options for dropdown
const cameraPresets: { key: CameraPreset; label: string; icon: string }[] = [
  { key: 'isometric', label: 'Изометрия', icon: '📐' },
  { key: 'top', label: 'Сверху', icon: '⬇️' },
  { key: 'front', label: 'Спереди', icon: '➡️' },
  { key: 'side', label: 'Сбоку', icon: '⬆️' },
];
const {
  initMeshes,
  updateContainers,
  hoverContainer,
  selectContainer,
  getContainerAtPoint,
  toggleLabels,
  showLabels,
  toggleWallText,
  showWallText,
  colorMode,
  setColorMode,
  // Placement mode visual functions
  enterPlacementModeVisuals,
  exitPlacementModeVisuals,
  hidePlacementPreview,
  // Position marker functions
  showPositionMarkers,
  hidePositionMarkers,
  highlightMarker,
  selectMarker,
  getMarkerAtPoint,
  dispose: disposeMeshes
} = useContainerMesh(scene);
const {
  filteredPositionedContainers,
  selectedContainerId,
  loading,
  currentSuggestion,
  placingContainerId,
  unplacedContainers,
  selectedAlternativeIndex,
  selectAlternative,
  isPlacementMode,
  availablePositions, // All empty valid positions for hybrid placement mode
} = usePlacementState();

// Hovered container for tooltip
const hoveredContainer = ref<ContainerPlacement | null>(null);
const tooltipPosition = ref({ x: 0, y: 0 });

// Hovered position marker for marker tooltip
const hoveredMarker = ref<PositionMarkerData | null>(null);
const markerTooltipPosition = ref({ x: 0, y: 0 });


// Computed: container size display with HC indicator
const hoveredSize = computed(() => {
  if (!hoveredContainer.value) return '';
  const size = getContainerSize(hoveredContainer.value.iso_type);
  const hc = isHighCube(hoveredContainer.value.iso_type);
  return hc ? `${size} HC` : size;
});

// ResizeObserver for container resize (when layout changes)
let resizeObserver: ResizeObserver | null = null;

// Initialize scene and meshes with error handling
onMounted(() => {
  if (!canvasRef.value) {
    threeError.value = 'Canvas element not found';
    return;
  }

  try {
    initScene();
    initMeshes();
    createZoneWireframes();

    window.addEventListener('resize', handleResize);
    window.addEventListener('keydown', handleKeyDown);

    // Watch for container resize (when panel opens/closes)
    resizeObserver = new ResizeObserver(() => {
      handleResize();
    });
    resizeObserver.observe(canvasRef.value);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    threeError.value = `3D visualization unavailable: ${message}`;
    console.error('Three.js initialization failed:', error);
  }
});

// Track if we've done the initial fit
const hasInitialFit = ref(false);

// Update containers when data changes (uses filtered list for company filtering)
watch(filteredPositionedContainers, (containers) => {
  updateContainers(containers);

  // Auto-fit camera on first load with containers
  if (!hasInitialFit.value && containers.length > 0) {
    // Small delay to ensure meshes are rendered
    setTimeout(() => {
      fitToContainers();
      hasInitialFit.value = true;
    }, 100);
  }
}, { immediate: true });

// Highlight selected container (gold color)
watch(selectedContainerId, (id) => {
  selectContainer(id);
});

// Show position markers when suggestion is available (includes all empty slots)
watch([currentSuggestion, availablePositions], ([suggestion, available]) => {
  if (suggestion) {
    // Find the actual container being placed to get its ISO type
    const containerBeingPlaced = unplacedContainers.value.find(
      c => c.id === placingContainerId.value
    );
    // Use actual ISO type or fallback to 45G1 (standard 40ft)
    const isoType = containerBeingPlaced?.iso_type ?? '45G1';
    // Show position markers for primary, alternatives, AND all available slots
    showPositionMarkers(suggestion, isoType, available);
    // Hide the old single preview (replaced by markers)
    hidePlacementPreview();
  } else {
    // Hide markers when no suggestion
    hidePositionMarkers();
    hidePlacementPreview();
  }
});

// Sync marker selection with state
watch(selectedAlternativeIndex, (index) => {
  selectMarker(index);
});

// Adjust container visuals when entering/exiting placement mode
// Hides labels, wall text, and dims containers for better marker visibility
watch(isPlacementMode, (active) => {
  if (active) {
    enterPlacementModeVisuals();
  } else {
    exitPlacementModeVisuals();
  }
});

// Auto-fit and zoom when entering fullscreen mode
// Gives a small delay for the CSS/canvas to resize first
watch(() => props.isFullscreen, (isFullscreen) => {
  if (isFullscreen) {
    // Wait for canvas resize to complete, then fit to containers with better zoom
    setTimeout(() => {
      handleResize();
      fitToContainers();
    }, 100);
  }
});

// Note: Company filtering now handled by filteredPositionedContainers watcher above
// The 3D view completely re-renders with only matching containers when a company is selected

// Create zone labels, row labels, and bay labels
function createZoneWireframes(): void {
  if (!scene.value) return;

  for (const zone of ZONES) {
    const layout = ZONE_LAYOUT[zone];
    if (!layout) continue; // Skip undefined zones
    const width = 10 * SPACING.bay;  // 10 bays
    const depth = 10 * SPACING.row;  // 10 rows
    const height = 4 * SPACING.tier; // 4 tiers

    // Add zone label (floating "A" above the zone)
    addZoneLabel(zone, layout.xOffset + width / 2, height + 2, layout.zOffset + depth / 2);

    // Add Row labels (R1-R10) on the left side - painted on ground
    for (let row = 1; row <= 10; row++) {
      const z = layout.zOffset + (row - 1) * SPACING.row + SPACING.row / 2;
      addAxisLabel(`R${row}`, layout.xOffset - 6, 0, z, '#c0392b', true); // Dark red for rows
    }

    // Add Bay labels (B1-B10) at the front - painted on ground
    for (let bay = 1; bay <= 10; bay++) {
      const x = layout.xOffset + (bay - 1) * SPACING.bay + SPACING.bay / 2;
      addAxisLabel(`B${bay}`, x, 0, layout.zOffset - 4, '#2980b9', false); // Dark blue for bays
    }
  }
}

// Add ground label (Row or Bay) - painted on the floor like terminal markings
function addAxisLabel(text: string, x: number, _y: number, z: number, color: string, isRow: boolean = true): void {
  if (!scene.value) return;

  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  if (!context) return;

  canvas.width = 128;
  canvas.height = 64;

  // Semi-transparent background (like painted marking)
  context.fillStyle = 'rgba(255, 255, 255, 0.85)';
  context.fillRect(0, 0, 128, 64);

  // Border
  context.strokeStyle = color;
  context.lineWidth = 4;
  context.strokeRect(2, 2, 124, 60);

  // Text
  context.fillStyle = color;
  context.font = 'bold 36px Arial';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text, 64, 32);

  const texture = new THREE.CanvasTexture(canvas);

  // Create a plane geometry lying flat on the ground
  const geometry = new THREE.PlaneGeometry(6, 3);
  const material = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    side: THREE.DoubleSide,
    depthWrite: false, // Prevent z-fighting with ground
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(x, 0.05, z); // Slightly above ground to prevent z-fighting

  // Rotate to lie flat on the ground (face up)
  mesh.rotation.x = -Math.PI / 2;

  // For row labels, rotate to be readable from the default camera angle
  if (isRow) {
    mesh.rotation.z = Math.PI / 2; // Rotate text to face the bays
  }

  scene.value.add(mesh);
}

// Add floating zone label
function addZoneLabel(zone: ZoneCode, x: number, y: number, z: number): void {
  if (!scene.value) return;

  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  if (!context) return;

  canvas.width = 128;
  canvas.height = 64;

  context.fillStyle = getLegendColor(zone);
  context.font = 'bold 48px Arial';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(zone, 64, 32);

  const texture = new THREE.CanvasTexture(canvas);
  const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
  const sprite = new THREE.Sprite(spriteMaterial);
  sprite.position.set(x, y, z);
  sprite.scale.set(8, 4, 1);

  scene.value.add(sprite);
}

// Handle canvas click
function handleClick(event: MouseEvent): void {
  if (!canvasRef.value || !camera.value) return;

  // Check markers first (higher priority during placement)
  const marker = getMarkerAtPoint(
    event.clientX,
    event.clientY,
    canvasRef.value,
    camera.value
  );

  if (marker) {
    // Select the clicked marker visually
    selectAlternative(marker.data.index);
    // Emit event to open confirmation modal
    emit('markerSelect', marker.data);
    return;
  }

  // Then check containers
  const container = getContainerAtPoint(
    event.clientX,
    event.clientY,
    canvasRef.value,
    camera.value
  );

  if (container) {
    emit('containerClick', container);
  }
}

// Handle mouse move for hover tooltip (throttled for performance)
function handleMouseMove(event: MouseEvent): void {
  if (!canvasRef.value || !camera.value) return;

  // Throttled raycasting - only check every 50ms
  throttledRaycast(event);
}

// Throttled raycasting function (50ms interval)
const throttledRaycast = throttle((event: MouseEvent) => {
  const rect = canvasRef.value!.getBoundingClientRect();

  // Check markers first (higher priority during placement)
  const marker = getMarkerAtPoint(
    event.clientX,
    event.clientY,
    canvasRef.value!,
    camera.value!
  );

  if (marker) {
    // Hovering over a marker - extract data and group
    hoveredMarker.value = marker.data;
    hoveredContainer.value = null;
    hoverContainer(null);
    // Pass group reference for available markers (index -2) to enable hover highlight
    highlightMarker(marker.data.index, marker.group);

    // Position marker tooltip
    markerTooltipPosition.value = {
      x: event.clientX - rect.left + 15,
      y: event.clientY - rect.top + 15,
    };
    emit('containerHover', null);
    return;
  }

  // Not hovering over marker - clear marker state
  hoveredMarker.value = null;
  highlightMarker(null, null);

  // Check containers
  const container = getContainerAtPoint(
    event.clientX,
    event.clientY,
    canvasRef.value!,
    camera.value!
  );

  hoveredContainer.value = container;

  // Update hover highlight in 3D view
  hoverContainer(container?.id ?? null);

  if (container) {
    // Position tooltip near cursor
    tooltipPosition.value = {
      x: event.clientX - rect.left + 15,
      y: event.clientY - rect.top + 15,
    };
  }

  emit('containerHover', container);
}, 50);

// Handle mouse leave
function handleMouseLeave(): void {
  hoveredContainer.value = null;
  hoveredMarker.value = null;
  hoverContainer(null); // Clear hover highlight
  highlightMarker(null); // Clear marker highlight
}

// Toggle heatmap mode
function toggleHeatmap(): void {
  setColorMode(colorMode.value === 'status' ? 'dwell_time' : 'status');
}

// Keyboard shortcuts
function handleKeyDown(event: KeyboardEvent): void {
  // Ignore if typing in an input
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
    return;
  }

  // ESC: Hide tooltip
  if (event.key === 'Escape') {
    hoveredContainer.value = null;
    hoverContainer(null);
    return;
  }

  // R: Reset camera
  if (event.key === 'r' || event.key === 'R') {
    resetCamera();
    return;
  }

  // F: Fit to containers
  if (event.key === 'f' || event.key === 'F') {
    fitToContainers();
    return;
  }

  // T: Toggle labels
  if (event.key === 't' || event.key === 'T') {
    toggleLabels();
    return;
  }

  // H: Toggle heatmap
  if (event.key === 'h' || event.key === 'H') {
    toggleHeatmap();
    return;
  }

  // 1-4: Camera presets
  if (event.key === '1') {
    setCameraPreset('isometric');
    return;
  }
  if (event.key === '2') {
    setCameraPreset('top');
    return;
  }
  if (event.key === '3') {
    setCameraPreset('front');
    return;
  }
  if (event.key === '4') {
    setCameraPreset('side');
    return;
  }
}

// Cleanup
onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  window.removeEventListener('keydown', handleKeyDown);
  resizeObserver?.disconnect();
  resizeObserver = null;
  disposeMeshes();
});

// Expose camera controls for parent
defineExpose({
  resetCamera,
  fitToContainers,
  setCameraPreset,
  focusOnPosition,
});
</script>

<template>
  <div :class="['terminal-3d-container', { 'is-fullscreen': props.isFullscreen }]">
    <!-- Error display -->
    <div v-if="threeError" class="error-overlay">
      <a-alert
        type="error"
        :message="threeError"
        show-icon
      />
    </div>

    <!-- Loading overlay (separate from canvas to not block events) -->
    <div v-else-if="loading" class="loading-overlay">
      <a-spin tip="Загрузка..." />
    </div>

    <!-- Canvas with direct event handlers -->
    <canvas
      ref="canvasRef"
      class="terminal-canvas"
      @click="handleClick"
      @mousemove="handleMouseMove"
      @mouseleave="handleMouseLeave"
    />

    <!-- Container info tooltip -->
    <div
      v-if="hoveredContainer"
      class="container-tooltip"
      :style="{ left: tooltipPosition.x + 'px', top: tooltipPosition.y + 'px' }"
    >
      <div class="tooltip-header">
        <span class="container-number">{{ hoveredContainer.container_number }}</span>
        <a-tag :color="hoveredContainer.status === 'LADEN' ? 'green' : 'blue'" size="small">
          {{ hoveredContainer.status === 'LADEN' ? 'Груж.' : 'Пор.' }}
        </a-tag>
      </div>
      <div class="tooltip-body">
        <div class="tooltip-row">
          <span class="label">Компания:</span>
          <span class="value">{{ hoveredContainer.company_name || 'Не указана' }}</span>
        </div>
        <div class="tooltip-row">
          <span class="label">Тип:</span>
          <span class="value">{{ hoveredContainer.iso_type }} ({{ hoveredSize }})</span>
        </div>
        <div class="tooltip-row">
          <span class="label">Позиция:</span>
          <span class="value">{{ hoveredContainer.position.coordinate }}</span>
        </div>
        <div class="tooltip-row">
          <span class="label">На терминале:</span>
          <span class="value">{{ hoveredContainer.dwell_time_days }} дн.</span>
        </div>
      </div>
    </div>

    <!-- Position marker tooltip -->
    <div
      v-if="hoveredMarker"
      class="marker-tooltip"
      :style="{ left: markerTooltipPosition.x + 'px', top: markerTooltipPosition.y + 'px' }"
    >
      <div class="marker-tooltip-header">
        <span v-if="hoveredMarker.type === 'primary'" class="marker-badge primary">★ Рекомендуемая</span>
        <span v-else-if="hoveredMarker.type === 'alternative'" class="marker-badge alternative">Альтернатива {{ hoveredMarker.index + 1 }}</span>
        <span v-else class="marker-badge available">Свободная позиция</span>
      </div>
      <div class="marker-tooltip-body">
        <span class="marker-coordinate">{{ hoveredMarker.coordinate }}</span>
        <span class="marker-hint">Нажмите для выбора</span>
      </div>
    </div>

    <!-- Placement mode instruction overlay -->
    <Transition name="fade">
      <div v-if="isPlacementMode" class="placement-mode-overlay">
        <div class="placement-instruction">
          <span class="instruction-icon">👆</span>
          <span class="instruction-text">Нажмите на позицию для размещения</span>
        </div>
      </div>
    </Transition>

    <!-- Zone legend -->
    <div class="zone-legend">
      <div class="legend-section">
        <div class="legend-title">Зоны</div>
        <div class="legend-items">
          <div class="legend-item" v-for="zone in ZONES" :key="zone">
            <span class="legend-color" :style="{ backgroundColor: getLegendColor(zone) }"></span>
            <span>{{ zone }}</span>
          </div>
        </div>
      </div>
      <div class="legend-divider"></div>
      <div class="legend-section">
        <!-- Status mode legend with size-specific colors -->
        <template v-if="colorMode === 'status'">
          <div class="legend-title">Статус + Размер</div>
          <div class="legend-items status-size-grid">
            <!-- Header row -->
            <div class="legend-header"></div>
            <div class="legend-header">20ft</div>
            <div class="legend-header">40ft</div>
            <!-- Laden row -->
            <div class="legend-row-label">Гружёный</div>
            <div class="legend-color-cell" style="background-color: #52c41a;" title="Гружёный 20ft"></div>
            <div class="legend-color-cell" style="background-color: #7cb305;" title="Гружёный 40ft"></div>
            <!-- Empty row -->
            <div class="legend-row-label">Порожний</div>
            <div class="legend-color-cell" style="background-color: #1890ff;" title="Порожний 20ft"></div>
            <div class="legend-color-cell" style="background-color: #722ed1;" title="Порожний 40ft"></div>
            <!-- Pending row -->
            <div class="legend-row-label">Ожидает</div>
            <div class="legend-color-cell" style="background-color: #fa8c16;" title="Ожидает размещения" colspan="2"></div>
            <div class="legend-color-cell" style="background-color: #fa8c16;" title="Ожидает размещения"></div>
          </div>
          <div class="legend-note">Зелёные = Груж., Синие = Пор., Оранж. = Ожидает</div>
        </template>
        <!-- Dwell time heatmap legend -->
        <template v-else>
          <div class="legend-title">Время хранения</div>
          <div class="legend-items dwell-items">
            <div class="legend-item">
              <span class="legend-color" style="background-color: #52c41a;"></span>
              <span>0-3 дн.</span>
            </div>
            <div class="legend-item">
              <span class="legend-color" style="background-color: #fadb14;"></span>
              <span>4-7 дн.</span>
            </div>
            <div class="legend-item">
              <span class="legend-color" style="background-color: #fa8c16;"></span>
              <span>8-14 дн.</span>
            </div>
            <div class="legend-item">
              <span class="legend-color" style="background-color: #f5222d;"></span>
              <span>15-21 дн.</span>
            </div>
            <div class="legend-item">
              <span class="legend-color" style="background-color: #722ed1;"></span>
              <span>21+ дн.</span>
            </div>
          </div>
        </template>
      </div>
      <div class="legend-divider"></div>
      <div class="legend-section">
        <div class="legend-title">Высота</div>
        <div class="legend-items height-items">
          <div class="legend-item">
            <span class="height-box height-std"></span>
            <span>Станд.</span>
          </div>
          <div class="legend-item">
            <span class="height-box height-hc"></span>
            <span>High Cube</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Controls overlay -->
    <div class="controls-overlay">
      <a-space>
        <a-button size="small" @click="toggleLabels()">
          <template #icon>
            <TagFilled v-if="showLabels" />
            <TagOutlined v-else />
          </template>
          {{ showLabels ? 'Скрыть метки' : 'Метки' }}
        </a-button>
        <a-button
          size="small"
          :type="showWallText ? 'primary' : 'default'"
          @click="toggleWallText()"
        >
          <template #icon><FontSizeOutlined /></template>
          {{ showWallText ? 'Тт Стена: Вкл' : 'Тт Стена: Выкл' }}
        </a-button>
        <a-button
          size="small"
          :type="colorMode === 'dwell_time' ? 'primary' : 'default'"
          @click="toggleHeatmap"
        >
          <template #icon><HeatMapOutlined /></template>
          Статус
        </a-button>
        <a-dropdown>
          <a-button size="small">
            <template #icon><CameraOutlined /></template>
            Камера
          </a-button>
          <template #overlay>
            <a-menu @click="({ key }: { key: string }) => setCameraPreset(key as CameraPreset)">
              <a-menu-item v-for="preset in cameraPresets" :key="preset.key">
                <span>{{ preset.icon }} {{ preset.label }}</span>
                <span v-if="currentPreset === preset.key" class="preset-active">✓</span>
              </a-menu-item>
              <a-menu-divider />
              <a-menu-item key="fit" @click="fitToContainers">
                <ExpandOutlined /> Показать все (F)
              </a-menu-item>
              <a-menu-item key="reset" @click="resetCamera">
                <ReloadOutlined /> Сброс (R)
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
        <a-popover
          v-model:open="showNavHelp"
          trigger="click"
          placement="bottomRight"
        >
          <template #content>
            <div class="nav-help">
              <div class="nav-help-title">🖱️ Управление мышью</div>
              <div class="nav-help-item">
                <kbd>ЛКМ + тянуть</kbd>
                <span>Вращение</span>
              </div>
              <div class="nav-help-item">
                <kbd>ПКМ + тянуть</kbd>
                <span>Перемещение</span>
              </div>
              <div class="nav-help-item">
                <kbd>Колесо</kbd>
                <span>Масштаб</span>
              </div>

              <div class="nav-help-title">⌨️ Клавиатура</div>
              <div class="nav-help-item">
                <kbd>F</kbd>
                <span>Показать все контейнеры</span>
              </div>
              <div class="nav-help-item">
                <kbd>R</kbd>
                <span>Сброс камеры</span>
              </div>
              <div class="nav-help-item">
                <kbd>1-4</kbd>
                <span>Виды камеры</span>
              </div>
              <div class="nav-help-item">
                <kbd>T</kbd>
                <span>Вкл/выкл метки</span>
              </div>
              <div class="nav-help-item">
                <kbd>H</kbd>
                <span>Режим хранения</span>
              </div>
            </div>
          </template>
          <a-button size="small" type="text">
            <template #icon><QuestionCircleOutlined /></template>
          </a-button>
        </a-popover>
      </a-space>
    </div>
  </div>
</template>

<style scoped>
.terminal-3d-container {
  position: relative;
  width: 100%;
  height: calc(100vh - 280px);
  min-height: 500px;
  background: #f5f5f5;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e0e0e0;
}

/* Fullscreen mode - fill entire viewport */
.terminal-3d-container.is-fullscreen {
  height: 100vh;
  min-height: 100vh;
  border-radius: 0;
  border: none;
  background: #d4d4d4; /* Matches ground color for seamless look */
}

.terminal-canvas {
  width: 100%;
  height: 100%;
  display: block;
  cursor: crosshair;
}

/* Error overlay */
.error-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 20;
  max-width: 400px;
}

/* Loading overlay - doesn't block canvas events */
.loading-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
  background: rgba(255, 255, 255, 0.8);
  padding: 20px 40px;
  border-radius: 8px;
  pointer-events: none;
}

/* Tooltip styles */
.container-tooltip {
  position: absolute;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 12px;
  min-width: 220px;
  pointer-events: none;
  z-index: 100;
  border: 1px solid #e8e8e8;
}

.tooltip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.container-number {
  font-weight: 600;
  font-size: 14px;
  color: #262626;
}

.tooltip-body {
  font-size: 12px;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.tooltip-row .label {
  color: #8c8c8c;
}

.tooltip-row .value {
  color: #262626;
  font-weight: 500;
}

/* Legend styles - Light theme */
.zone-legend {
  position: absolute;
  bottom: 12px;
  left: 12px;
  background: white;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 1px solid #e8e8e8;
  max-width: 280px;
}

.legend-section {
  margin-bottom: 0;
}

.legend-title {
  font-size: 10px;
  font-weight: 600;
  color: #8c8c8c;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.legend-items {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #262626;
  font-size: 12px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-divider {
  height: 1px;
  background: #f0f0f0;
  margin: 10px 0;
}

/* Dwell time legend - vertical layout for 5 items */
.dwell-items {
  flex-direction: column;
  gap: 4px;
}

/* Status + Size grid legend */
.status-size-grid {
  display: grid;
  grid-template-columns: auto 36px 36px;
  gap: 4px 8px;
  align-items: center;
}

.legend-header {
  font-size: 10px;
  font-weight: 500;
  color: #8c8c8c;
  text-align: center;
}

.legend-row-label {
  font-size: 11px;
  color: #262626;
}

.legend-color-cell {
  width: 28px;
  height: 16px;
  border-radius: 3px;
  cursor: help;
}

.legend-note {
  margin-top: 6px;
  font-size: 10px;
  color: #8c8c8c;
  font-style: italic;
}

/* Height legend */
.height-items .legend-item {
  align-items: flex-end;
}

.height-box {
  width: 16px;
  background: #999;
  border-radius: 2px;
}

.height-std {
  height: 10px;
}

.height-hc {
  height: 14px;
}

/* Controls overlay */
.controls-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
}

/* Camera preset active indicator */
.preset-active {
  margin-left: 8px;
  color: #1677ff;
  font-weight: bold;
}

/* Navigation help popover styles */
.nav-help {
  min-width: 220px;
}

.nav-help-title {
  font-weight: 600;
  font-size: 13px;
  color: #262626;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #f0f0f0;
}

.nav-help-title:not(:first-child) {
  margin-top: 12px;
}

.nav-help-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 12px;
}

.nav-help-item kbd {
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 2px 6px;
  font-family: monospace;
  font-size: 11px;
  color: #595959;
}

.nav-help-item span {
  color: #8c8c8c;
}

/* Position marker tooltip styles */
.marker-tooltip {
  position: absolute;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 10px 14px;
  min-width: 180px;
  pointer-events: none;
  z-index: 100;
  border: 1px solid #e8e8e8;
}

.marker-tooltip-header {
  margin-bottom: 6px;
}

.marker-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.marker-badge.primary {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.marker-badge.alternative {
  background: #e6f4ff;
  color: #1677ff;
  border: 1px solid #91caff;
}

.marker-badge.available {
  background: #f5f5f5;
  color: #8c8c8c;
  border: 1px solid #d9d9d9;
}

.marker-tooltip-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.marker-coordinate {
  font-family: monospace;
  font-size: 14px;
  font-weight: 600;
  color: #262626;
}

.marker-hint {
  font-size: 11px;
  color: #8c8c8c;
}

/* Placement mode instruction overlay */
.placement-mode-overlay {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 15;
  pointer-events: none;
}

.placement-instruction {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(22, 119, 255, 0.95);
  color: white;
  padding: 10px 20px;
  border-radius: 24px;
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.3);
  font-size: 14px;
  font-weight: 500;
  animation: pulse-shadow 2s ease-in-out infinite;
}

.instruction-icon {
  font-size: 18px;
}

.instruction-text {
  white-space: nowrap;
}

@keyframes pulse-shadow {
  0%, 100% {
    box-shadow: 0 4px 12px rgba(22, 119, 255, 0.3);
  }
  50% {
    box-shadow: 0 4px 20px rgba(22, 119, 255, 0.5);
  }
}

/* Fade transition for overlay */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
