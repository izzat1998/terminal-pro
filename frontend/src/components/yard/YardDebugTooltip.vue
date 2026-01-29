<script setup lang="ts">
/**
 * YardDebugTooltip - Cursor-based debug information display
 *
 * Shows grid cell (A1, B2) and element info at cursor position.
 * Uses raycasting to detect 3D position and elements under cursor.
 *
 * Usage:
 * - Enable debug mode (press D or ?debug=true)
 * - Move mouse over 3D yard
 * - Tooltip shows grid cell and element info
 */

import { ref, onMounted, onUnmounted, computed } from 'vue'
import * as THREE from 'three'

// ============================================================================
// Props
// ============================================================================

interface Props {
  /** Three.js scene */
  scene: THREE.Scene | undefined
  /** Three.js camera */
  camera: THREE.Camera | undefined
  /** Container element for mouse events */
  container: HTMLElement | undefined
  /** DXF coordinate system */
  coordinateSystem: {
    center: { x: number; y: number }
    scale: number
    bounds: { width: number; height: number; min: { x: number; y: number }; max: { x: number; y: number } }
  } | null | undefined
  /** Grid cell size in meters */
  cellSize?: number
  /** Whether tooltip is enabled */
  enabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  cellSize: 20,
  enabled: true,
})

// ============================================================================
// State
// ============================================================================

const tooltipVisible = ref(false)
const tooltipX = ref(0)
const tooltipY = ref(0)
const gridCell = ref('')
const dxfCoords = ref({ x: 0, y: 0 })
const elementInfo = ref<{ type: string; name: string; id?: number } | null>(null)

// Raycaster for 3D picking
const raycaster = new THREE.Raycaster()
const mouse = new THREE.Vector2()
const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0) // Y=0 plane

// ============================================================================
// Computed
// ============================================================================

const tooltipStyle = computed(() => ({
  left: `${tooltipX.value + 15}px`,
  top: `${tooltipY.value + 15}px`,
}))

// ============================================================================
// Grid Conversion
// ============================================================================

/**
 * Convert world position to DXF coordinates
 */
function worldToDxf(worldX: number, worldZ: number): { x: number; y: number } {
  if (!props.coordinateSystem) return { x: 0, y: 0 }

  const { center, scale } = props.coordinateSystem
  const dxfX = worldX / scale + center.x
  const dxfY = -worldZ / scale + center.y // Note: Z is negated

  return { x: dxfX, y: dxfY }
}

/**
 * Convert DXF coordinates to grid cell label (A1, B2, etc.)
 */
function dxfToGridCell(dxfX: number, dxfY: number): string {
  if (!props.coordinateSystem) return ''

  const { bounds } = props.coordinateSystem
  const cellSize = props.cellSize

  // Column: left to right (A, B, C...)
  const col = Math.floor((dxfX - bounds.min.x) / cellSize)
  // Row: top to bottom (1, 2, 3...)
  const row = Math.floor((bounds.max.y - dxfY) / cellSize)

  // Clamp to valid range
  const clampedCol = Math.max(0, Math.min(col, 25)) // A-Z
  const clampedRow = Math.max(0, row)

  const colLetter = String.fromCharCode(65 + clampedCol)
  return `${colLetter}${clampedRow + 1}`
}

// ============================================================================
// Mouse Handling
// ============================================================================

function handleMouseMove(event: MouseEvent): void {
  if (!props.enabled || !props.container || !props.camera || !props.scene || !props.coordinateSystem) {
    tooltipVisible.value = false
    return
  }

  const rect = props.container.getBoundingClientRect()

  // Calculate normalized device coordinates
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  // Update raycaster
  raycaster.setFromCamera(mouse, props.camera)

  // Find intersection with ground plane
  const intersection = new THREE.Vector3()
  const hasIntersection = raycaster.ray.intersectPlane(groundPlane, intersection)

  if (!hasIntersection) {
    tooltipVisible.value = false
    return
  }

  // Convert to DXF coordinates
  const dxf = worldToDxf(intersection.x, intersection.z)
  dxfCoords.value = dxf

  // Convert to grid cell
  gridCell.value = dxfToGridCell(dxf.x, dxf.y)

  // Check for element under cursor
  const intersects = raycaster.intersectObjects(props.scene.children, true)
  elementInfo.value = null

  for (const hit of intersects) {
    const userData = hit.object.userData
    if (userData && (userData.type || userData.buildingId || userData.containerId)) {
      elementInfo.value = {
        type: userData.type || 'unknown',
        name: userData.label || userData.name || `ID: ${userData.buildingId || userData.containerId || 'unknown'}`,
        id: userData.buildingId || userData.containerId,
      }
      break
    }
  }

  // Update tooltip position
  tooltipX.value = event.clientX - rect.left
  tooltipY.value = event.clientY - rect.top
  tooltipVisible.value = true
}

function handleMouseLeave(): void {
  tooltipVisible.value = false
}

// ============================================================================
// Lifecycle
// ============================================================================

onMounted(() => {
  if (props.container) {
    props.container.addEventListener('mousemove', handleMouseMove)
    props.container.addEventListener('mouseleave', handleMouseLeave)
  }
})

onUnmounted(() => {
  if (props.container) {
    props.container.removeEventListener('mousemove', handleMouseMove)
    props.container.removeEventListener('mouseleave', handleMouseLeave)
  }
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="tooltipVisible && enabled"
      class="yard-debug-tooltip"
      :style="tooltipStyle"
    >
      <div class="tooltip-grid">{{ gridCell }}</div>
      <div v-if="elementInfo" class="tooltip-element">
        <span class="element-type">{{ elementInfo.type }}</span>
        <span class="element-name">{{ elementInfo.name }}</span>
      </div>
      <div class="tooltip-coords">
        {{ dxfCoords.x.toFixed(0) }}, {{ dxfCoords.y.toFixed(0) }}
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.yard-debug-tooltip {
  position: fixed;
  z-index: 10000;
  background: rgba(0, 0, 0, 0.85);
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
  font-family: 'SF Mono', Monaco, 'Courier New', monospace;
  font-size: 12px;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  min-width: 80px;
}

.tooltip-grid {
  font-size: 18px;
  font-weight: 700;
  color: #4fc3f7;
  margin-bottom: 4px;
}

.tooltip-element {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  margin: 4px 0;
}

.element-type {
  font-size: 10px;
  color: #90caf9;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.element-name {
  color: #fff;
  font-weight: 500;
}

.tooltip-coords {
  font-size: 10px;
  color: #888;
}
</style>
