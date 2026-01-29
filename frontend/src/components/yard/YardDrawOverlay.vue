<script setup lang="ts">
/**
 * YardDrawOverlay - Visual markers and lines for coordinate drawing
 *
 * Renders Three.js objects to show:
 * - Red spheres at each clicked point
 * - White number labels above spheres
 * - Green lines connecting consecutive points
 */

import { watch, onUnmounted, shallowRef } from 'vue'
import * as THREE from 'three'
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import type { DrawnPoint } from '@/composables/useYardDraw'

// ============================================================================
// Props
// ============================================================================

interface Props {
  /** Three.js scene to add markers to */
  scene: THREE.Scene | undefined
  /** Array of drawn points */
  points: DrawnPoint[]
  /** Whether draw mode is active */
  active: boolean
}

const props = defineProps<Props>()

// ============================================================================
// State
// ============================================================================

// Group to hold all draw mode objects
const drawGroup = shallowRef<THREE.Group | null>(null)

// Reusable geometry and materials
const sphereGeometry = new THREE.SphereGeometry(3, 16, 16)
const sphereMaterial = new THREE.MeshBasicMaterial({ color: 0xff4444 })
const lineMaterial = new THREE.LineBasicMaterial({ color: 0x44ff44, linewidth: 2 })

// ============================================================================
// Marker Management
// ============================================================================

/**
 * Create a numbered marker at a point
 */
function createMarker(point: DrawnPoint): THREE.Group {
  const markerGroup = new THREE.Group()
  markerGroup.name = `draw-marker-${point.id}`

  // Red sphere
  const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial)
  sphere.position.copy(point.world)
  sphere.position.y = 2 // Slightly above ground
  markerGroup.add(sphere)

  // Number label
  const labelDiv = document.createElement('div')
  labelDiv.className = 'draw-marker-label'
  labelDiv.textContent = String(point.id)
  labelDiv.style.cssText = `
    background: white;
    color: #333;
    padding: 2px 6px;
    border-radius: 10px;
    font-family: 'SF Mono', Monaco, monospace;
    font-size: 12px;
    font-weight: 700;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
  `

  const label = new CSS2DObject(labelDiv)
  label.position.copy(point.world)
  label.position.y = 8 // Above the sphere
  markerGroup.add(label)

  return markerGroup
}

/**
 * Create line connecting all points
 */
function createLine(points: DrawnPoint[]): THREE.Line | null {
  if (points.length < 2) return null

  const linePoints = points.map((p) => {
    const pos = p.world.clone()
    pos.y = 1 // Slightly above ground
    return pos
  })

  const geometry = new THREE.BufferGeometry().setFromPoints(linePoints)
  const line = new THREE.Line(geometry, lineMaterial)
  line.name = 'draw-line'

  return line
}

/**
 * Rebuild all visual elements from points array
 */
function rebuildVisuals(): void {
  const sceneRef = props.scene
  if (!sceneRef) return

  // Remove existing group
  if (drawGroup.value) {
    sceneRef.remove(drawGroup.value)
    disposeGroup(drawGroup.value)
    drawGroup.value = null
  }

  // Don't create visuals if not active or no points
  if (!props.active || props.points.length === 0) return

  // Create new group
  const group = new THREE.Group()
  group.name = 'yard-draw-group'

  // Add markers for each point
  for (const point of props.points) {
    const marker = createMarker(point)
    group.add(marker)
  }

  // Add connecting line
  const line = createLine(props.points)
  if (line) {
    group.add(line)
  }

  // Add to scene
  sceneRef.add(group)
  drawGroup.value = group
}

/**
 * Dispose a group and its children
 */
function disposeGroup(group: THREE.Group): void {
  group.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.geometry?.dispose()
      // Don't dispose shared materials
    }
    if (child instanceof THREE.Line) {
      child.geometry?.dispose()
    }
    if (child instanceof CSS2DObject) {
      if (child.element && child.element.parentNode) {
        child.element.parentNode.removeChild(child.element)
      }
    }
  })
  group.clear()
}

// ============================================================================
// Watchers
// ============================================================================

// Watch for points changes
watch(
  () => props.points,
  () => {
    rebuildVisuals()
  },
  { immediate: true, deep: true }
)

// Watch for active state changes
watch(
  () => props.active,
  () => {
    rebuildVisuals()
  }
)

// Watch for scene availability
watch(
  () => props.scene,
  () => {
    rebuildVisuals()
  }
)

// ============================================================================
// Cleanup
// ============================================================================

onUnmounted(() => {
  if (drawGroup.value && props.scene) {
    props.scene.remove(drawGroup.value)
    disposeGroup(drawGroup.value)
    drawGroup.value = null
  }
})
</script>

<template>
  <!-- This component renders directly to Three.js scene, no template needed -->
  <div v-if="false" />
</template>
