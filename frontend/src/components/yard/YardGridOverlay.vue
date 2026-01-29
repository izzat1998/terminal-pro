<script setup lang="ts">
/**
 * YardGridOverlay Component (Simplified)
 *
 * Renders grid LINES only using Three.js LineSegments.
 * Grid cell labels (A1, B2) are shown via YardDebugTooltip on cursor hover.
 *
 * Cell size: 20m x 20m
 * Grid lines help visualize the coordinate system for debugging.
 */

import { watch, onMounted, onUnmounted, shallowRef } from 'vue'
import * as THREE from 'three'
import type { DxfCoordinateSystem } from '@/types/dxf'

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  /** DXF coordinate system for grid positioning */
  coordinateSystem: DxfCoordinateSystem | null
  /** Three.js scene to add the grid to */
  scene: THREE.Scene | null
  /** Whether the grid is visible */
  visible?: boolean
  /** Cell size in meters */
  cellSize?: number
  /** Grid line color */
  gridColor?: number
  /** Grid line opacity */
  gridOpacity?: number
}

const props = withDefaults(defineProps<Props>(), {
  visible: true,
  cellSize: 20,
  gridColor: 0x4a90d9,
  gridOpacity: 0.3,
})

const emit = defineEmits<{
  gridCreated: [group: THREE.Group]
}>()

// ============================================================================
// State
// ============================================================================

const gridGroup = shallowRef<THREE.Group | null>(null)
const addedToScene = shallowRef(false)

// ============================================================================
// Grid Creation
// ============================================================================

/**
 * Create grid lines using LineSegments
 */
function createGridLines(coordinateSystem: DxfCoordinateSystem): THREE.Group {
  const { bounds, center, scale } = coordinateSystem
  const cellSize = props.cellSize

  // Calculate grid dimensions
  const numColumns = Math.ceil(bounds.width / cellSize)
  const numRows = Math.ceil(bounds.height / cellSize)
  const gridWidth = numColumns * cellSize
  const gridHeight = numRows * cellSize

  console.log('[YardGridOverlay] Creating grid:', {
    columns: numColumns,
    rows: numRows,
    size: `${gridWidth}m x ${gridHeight}m`,
  })

  // Create geometry for grid lines
  const vertices: number[] = []
  const yOffset = 0.5 // Slightly above ground to prevent z-fighting

  // Vertical lines (columns)
  for (let i = 0; i <= numColumns; i++) {
    const dxfX = bounds.min.x + i * cellSize
    const worldX = (dxfX - center.x) * scale
    const worldZTop = -(bounds.max.y - center.y) * scale
    const worldZBottom = -(bounds.min.y - center.y) * scale

    vertices.push(worldX, yOffset, worldZTop)
    vertices.push(worldX, yOffset, worldZBottom)
  }

  // Horizontal lines (rows)
  for (let j = 0; j <= numRows; j++) {
    const dxfY = bounds.max.y - j * cellSize
    const worldZ = -(dxfY - center.y) * scale
    const worldXLeft = (bounds.min.x - center.x) * scale
    const worldXRight = (bounds.min.x + gridWidth - center.x) * scale

    vertices.push(worldXLeft, yOffset, worldZ)
    vertices.push(worldXRight, yOffset, worldZ)
  }

  // Create buffer geometry
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3))

  // Create material
  const material = new THREE.LineBasicMaterial({
    color: props.gridColor,
    transparent: true,
    opacity: props.gridOpacity,
    depthWrite: false,
  })

  // Create line segments
  const gridLines = new THREE.LineSegments(geometry, material)
  gridLines.name = 'debug-grid-lines'
  gridLines.renderOrder = 1

  // Wrap in group
  const group = new THREE.Group()
  group.name = 'debug-grid'
  group.add(gridLines)
  group.visible = props.visible

  return group
}

/**
 * Initialize the grid
 */
function initializeGrid(): void {
  if (!props.coordinateSystem || !props.scene) return

  // Remove existing grid
  if (gridGroup.value && addedToScene.value) {
    props.scene.remove(gridGroup.value)
    gridGroup.value.traverse((obj) => {
      if (obj instanceof THREE.LineSegments) {
        obj.geometry.dispose()
        if (obj.material instanceof THREE.Material) {
          obj.material.dispose()
        }
      }
    })
    addedToScene.value = false
  }

  // Create new grid
  const group = createGridLines(props.coordinateSystem)
  gridGroup.value = group

  // Add to scene
  props.scene.add(group)
  addedToScene.value = true

  emit('gridCreated', group)
}

// ============================================================================
// Visibility
// ============================================================================

function updateVisibility(visible: boolean): void {
  if (gridGroup.value) {
    gridGroup.value.visible = visible
  }
}

// ============================================================================
// Watchers
// ============================================================================

watch(() => props.coordinateSystem, (cs) => {
  if (cs && props.scene) initializeGrid()
})

watch(() => props.scene, (scene) => {
  if (scene && props.coordinateSystem) initializeGrid()
})

watch(() => props.visible, (visible) => {
  updateVisibility(visible)
})

// ============================================================================
// Lifecycle
// ============================================================================

onMounted(() => {
  if (props.coordinateSystem && props.scene) {
    initializeGrid()
  }
})

onUnmounted(() => {
  if (gridGroup.value && props.scene && addedToScene.value) {
    props.scene.remove(gridGroup.value)
    gridGroup.value.traverse((obj) => {
      if (obj instanceof THREE.LineSegments) {
        obj.geometry.dispose()
        if (obj.material instanceof THREE.Material) {
          obj.material.dispose()
        }
      }
    })
  }
  gridGroup.value = null
})

// ============================================================================
// Expose
// ============================================================================

defineExpose({
  gridGroup,
})
</script>

<template>
  <slot />
</template>
