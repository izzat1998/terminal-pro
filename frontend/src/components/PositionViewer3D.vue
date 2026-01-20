<script setup lang="ts">
/**
 * Focused 3D Position Viewer
 * Shows a 5×5 grid area around a target position with nearby containers.
 * Target container highlighted with pulsing orange effect.
 */

import { ref, watch, onMounted, onUnmounted } from 'vue';
import * as THREE from 'three';
import { ReloadOutlined } from '@ant-design/icons-vue';
import { useMini3DScene, parseCoordinate } from '../composables/useMini3DScene';
import { placementService } from '../services/placementService';
import type { ContainerPlacement } from '../types/placement';
import {
  CONTAINER_DIMENSIONS,
  CONTAINER_SIZE_COLORS,
  ZONE_LAYOUT,
  SPACING,
  getContainerSize,
  isHighCube,
} from '../types/placement';

interface Props {
  coordinate: string;        // "A-R03-B05-T2-A"
  containerNumber?: string;  // Optional container at this position
}

const props = defineProps<Props>();

// Canvas ref
const canvasRef = ref<HTMLCanvasElement>();

// Scene composable
const {
  scene,
  isInitialized,
  initScene,
  handleResize,
  resetCamera,
  dispose,
} = useMini3DScene(canvasRef);

// State
const loading = ref(false);
const error = ref<string | null>(null);
const nearbyContainers = ref<ContainerPlacement[]>([]);

// Container meshes tracking
const containerMeshes: THREE.Mesh[] = [];
const containerEdges: THREE.LineSegments[] = [];

// Pulsing animation for target
let pulseAnimationId: number | null = null;
let targetMesh: THREE.Mesh | null = null;

// Filter range (±2 rows/bays)
const RANGE = 2;

/**
 * Filter containers to only those within ±2 rows/bays of target
 */
function filterNearbyContainers(
  containers: ContainerPlacement[],
  targetRow: number,
  targetBay: number
): ContainerPlacement[] {
  return containers.filter(c =>
    Math.abs(c.position.row - targetRow) <= RANGE &&
    Math.abs(c.position.bay - targetBay) <= RANGE
  );
}

/**
 * Create a container mesh with proper dimensions and color
 */
function createContainerMesh(
  container: ContainerPlacement,
  isTarget: boolean
): { mesh: THREE.Mesh; edges: THREE.LineSegments } {
  const size = getContainerSize(container.iso_type);
  const hc = isHighCube(container.iso_type);

  const dimKey = hc
    ? (size === '20ft' ? '20ft_HC' : '40ft_HC')
    : (size === '20ft' ? '20ft' : '40ft');
  const dimensions = CONTAINER_DIMENSIONS[dimKey];

  const geometry = new THREE.BoxGeometry(
    dimensions.length,
    dimensions.height,
    dimensions.width
  );

  // Color: orange for target, status colors for others
  let color: number;
  if (isTarget) {
    color = 0xfa8c16; // Orange for target
  } else {
    const isLaden = container.status === 'LADEN';
    color = isLaden
      ? (size === '20ft' ? CONTAINER_SIZE_COLORS.LADEN_20 : CONTAINER_SIZE_COLORS.LADEN_40)
      : (size === '20ft' ? CONTAINER_SIZE_COLORS.EMPTY_20 : CONTAINER_SIZE_COLORS.EMPTY_40);
  }

  const material = new THREE.MeshLambertMaterial({ color });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;

  // Calculate world position
  const pos = container.position;
  const zoneLayout = ZONE_LAYOUT[pos.zone];
  if (!zoneLayout) throw new Error(`Zone ${pos.zone} not found`);

  let x: number;
  const subSlot = pos.sub_slot || 'A';

  if (size === '20ft') {
    const bayStartX = zoneLayout.xOffset + (pos.bay - 1) * SPACING.bay;
    if (subSlot === 'A') {
      x = bayStartX + dimensions.length / 2 + SPACING.gap;
    } else {
      x = bayStartX + dimensions.length + SPACING.gap * 2 + dimensions.length / 2;
    }
  } else {
    x = zoneLayout.xOffset + (pos.bay - 0.5) * SPACING.bay;
  }

  const y = (pos.tier - 1) * SPACING.tier + dimensions.height / 2;
  const z = zoneLayout.zOffset + (pos.row - 0.5) * SPACING.row;

  mesh.position.set(x, y, z);

  // Create edges
  const edgesGeometry = new THREE.EdgesGeometry(geometry);
  const edgeColor = isTarget ? 0xd46b08 : 0x333333;
  const edgesMaterial = new THREE.LineBasicMaterial({ color: edgeColor, linewidth: 2 });
  const edges = new THREE.LineSegments(edgesGeometry, edgesMaterial);
  edges.position.copy(mesh.position);

  return { mesh, edges };
}

/**
 * Create a marker for the target position (if no container there)
 */
function createTargetMarker(coordinate: string): THREE.Mesh | null {
  const parsed = parseCoordinate(coordinate);
  if (!parsed) return null;

  const zoneLayout = ZONE_LAYOUT[parsed.zone];
  if (!zoneLayout) return null;

  // Default to 40ft dimensions for marker
  const dimensions = CONTAINER_DIMENSIONS['40ft'];

  const geometry = new THREE.BoxGeometry(
    dimensions.length * 0.95,
    dimensions.height * 0.95,
    dimensions.width * 0.95
  );

  const material = new THREE.MeshLambertMaterial({
    color: 0xfa8c16,
    transparent: true,
    opacity: 0.7,
  });

  const mesh = new THREE.Mesh(geometry, material);

  // Calculate position
  const x = zoneLayout.xOffset + (parsed.bay - 0.5) * SPACING.bay;
  const y = (parsed.tier - 1) * SPACING.tier + dimensions.height / 2;
  const z = zoneLayout.zOffset + (parsed.row - 0.5) * SPACING.row;

  mesh.position.set(x, y, z);
  mesh.castShadow = true;

  return mesh;
}

/**
 * Start pulsing animation for target
 */
function startPulseAnimation(): void {
  if (pulseAnimationId !== null || !targetMesh) return;

  let phase = 0;
  const baseMaterial = targetMesh.material as THREE.MeshLambertMaterial;
  const baseEmissive = new THREE.Color(0xfa8c16);

  // Enable emissive for pulsing effect
  baseMaterial.emissive = baseEmissive.clone();

  const animate = () => {
    if (!targetMesh) {
      stopPulseAnimation();
      return;
    }

    phase += 0.05;
    const intensity = 0.3 + Math.sin(phase) * 0.2; // 0.1 to 0.5

    const mat = targetMesh.material as THREE.MeshLambertMaterial;
    mat.emissiveIntensity = intensity;

    pulseAnimationId = requestAnimationFrame(animate);
  };

  pulseAnimationId = requestAnimationFrame(animate);
}

/**
 * Stop pulsing animation
 */
function stopPulseAnimation(): void {
  if (pulseAnimationId !== null) {
    cancelAnimationFrame(pulseAnimationId);
    pulseAnimationId = null;
  }
}

/**
 * Clear all container meshes from scene
 */
function clearContainers(): void {
  stopPulseAnimation();
  targetMesh = null;

  for (const mesh of containerMeshes) {
    mesh.geometry.dispose();
    (mesh.material as THREE.Material).dispose();
    scene.value?.remove(mesh);
  }
  containerMeshes.length = 0;

  for (const edge of containerEdges) {
    edge.geometry.dispose();
    (edge.material as THREE.Material).dispose();
    scene.value?.remove(edge);
  }
  containerEdges.length = 0;
}

/**
 * Render containers in the scene
 */
function renderContainers(): void {
  if (!scene.value) return;

  clearContainers();

  const parsed = parseCoordinate(props.coordinate);
  if (!parsed) return;

  // Check if target position has a container
  const targetContainer = nearbyContainers.value.find(c =>
    c.position.coordinate === props.coordinate ||
    (c.position.zone === parsed.zone &&
     c.position.row === parsed.row &&
     c.position.bay === parsed.bay &&
     c.position.tier === parsed.tier)
  );

  // Render all nearby containers
  for (const container of nearbyContainers.value) {
    const isTarget = container === targetContainer;
    const { mesh, edges } = createContainerMesh(container, isTarget);

    scene.value.add(mesh);
    scene.value.add(edges);
    containerMeshes.push(mesh);
    containerEdges.push(edges);

    if (isTarget) {
      targetMesh = mesh;
    }
  }

  // If no container at target position, create a marker
  if (!targetContainer) {
    const marker = createTargetMarker(props.coordinate);
    if (marker) {
      scene.value.add(marker);
      containerMeshes.push(marker);
      targetMesh = marker;
    }
  }

  // Start pulsing animation
  if (targetMesh) {
    startPulseAnimation();
  }
}

/**
 * Load containers and filter to nearby
 */
async function loadContainers(): Promise<void> {
  const parsed = parseCoordinate(props.coordinate);
  if (!parsed) {
    error.value = 'Invalid coordinate format';
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    const layout = await placementService.getLayout();
    nearbyContainers.value = filterNearbyContainers(
      layout.containers,
      parsed.row,
      parsed.bay
    );
    renderContainers();
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load containers';
    console.error('Failed to load containers:', e);
  } finally {
    loading.value = false;
  }
}

/**
 * Initialize scene and load data
 */
async function initialize(): Promise<void> {
  if (!canvasRef.value) return;

  const success = initScene(props.coordinate);
  if (!success) {
    error.value = 'Failed to initialize 3D scene';
    return;
  }

  await loadContainers();
}

// Watch for coordinate changes
watch(() => props.coordinate, async (newCoord, oldCoord) => {
  if (newCoord !== oldCoord && isInitialized.value) {
    // Re-initialize scene with new coordinate
    dispose();
    await initialize();
  }
});

// Lifecycle
onMounted(() => {
  initialize();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  stopPulseAnimation();
  clearContainers();
  dispose();
  window.removeEventListener('resize', handleResize);
});
</script>

<template>
  <div class="position-viewer-3d">
    <!-- Loading overlay -->
    <div v-if="loading" class="loading-overlay">
      <a-spin tip="Loading..." />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-overlay">
      <a-result status="error" :title="error">
        <template #extra>
          <a-button type="primary" @click="loadContainers">
            Retry
          </a-button>
        </template>
      </a-result>
    </div>

    <!-- 3D Canvas -->
    <canvas ref="canvasRef" class="viewer-canvas" />

    <!-- Controls -->
    <div class="controls-overlay">
      <a-tooltip title="Reset camera">
        <a-button size="small" @click="resetCamera">
          <template #icon><ReloadOutlined /></template>
        </a-button>
      </a-tooltip>
    </div>

    <!-- Info badge -->
    <div class="info-badge">
      <span class="coordinate">{{ coordinate }}</span>
      <span v-if="containerNumber" class="container-number">{{ containerNumber }}</span>
    </div>

    <!-- Legend -->
    <div class="mini-legend">
      <div class="legend-item">
        <span class="legend-color target"></span>
        <span>Target</span>
      </div>
      <div class="legend-item">
        <span class="legend-color laden"></span>
        <span>Laden</span>
      </div>
      <div class="legend-item">
        <span class="legend-color empty"></span>
        <span>Empty</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.position-viewer-3d {
  position: relative;
  width: 100%;
  height: 400px;
  min-height: 300px;
  background: #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
}

.viewer-canvas {
  width: 100%;
  height: 100%;
  display: block;
  cursor: grab;
}

.viewer-canvas:active {
  cursor: grabbing;
}

.loading-overlay,
.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 10;
}

.controls-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 5;
}

.info-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  background: white;
  padding: 8px 12px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.coordinate {
  font-family: monospace;
  font-size: 14px;
  font-weight: 600;
  color: #722ed1;
}

.container-number {
  font-size: 12px;
  color: #595959;
}

.mini-legend {
  position: absolute;
  bottom: 12px;
  left: 12px;
  background: white;
  padding: 8px 12px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 5;
  display: flex;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #595959;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-color.target {
  background: #fa8c16;
}

.legend-color.laden {
  background: #52c41a;
}

.legend-color.empty {
  background: #1890ff;
}
</style>
