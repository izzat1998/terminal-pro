<script setup lang="ts">
/**
 * GateCamera3D - Interactive 3D camera component for yard scene
 *
 * Renders a 3D security camera at the gate position.
 * Handles mouse interaction (hover, click) using raycasting.
 */

import { ref, shallowRef, onMounted, onUnmounted, watch } from 'vue'
import * as THREE from 'three'
import {
  useGateCamera3D,
  createCustomDetectionZone,
  updateDetectionZoneState,
  type UseGateCamera3DReturn,
  type DetectionZoneVertex,
} from '@/composables/useGateCamera3D'
import { GATES, transformToWorld } from '@/data/scenePositions'
import type { DxfCoordinateSystem } from '@/types/dxf'
import { removeAndDispose } from '@/utils/threeUtils'

/** Camera rotation offset: 65 degrees in radians (45° + 20° adjustment) */
const CAMERA_ROTATION_OFFSET_RAD = 65 * Math.PI / 180

/** Detection zone vertex in DXF coordinates */
interface DxfVertex {
  x: number
  y: number
}

interface Props {
  /** Three.js scene to add camera to */
  scene: THREE.Scene
  /** Three.js camera for raycasting */
  camera: THREE.Camera
  /** DXF coordinate system for position transform */
  coordinateSystem: DxfCoordinateSystem
  /** Container element for mouse events */
  container: HTMLElement
  /** Gate ID to position camera at */
  gateId?: string
  /** Whether the widget is currently open */
  isWidgetOpen?: boolean
  /** Custom detection zone vertices in DXF coordinates (overrides default cone) */
  detectionZoneVertices?: DxfVertex[]
}

const props = withDefaults(defineProps<Props>(), {
  gateId: 'main',
  isWidgetOpen: false,
  detectionZoneVertices: undefined,
})

const emit = defineEmits<{
  click: [screenPosition: { x: number; y: number }]
  hover: [isHovered: boolean]
}>()

// Camera instance
const cameraInstance = shallowRef<UseGateCamera3DReturn | null>(null)

// Custom detection zone mesh (when using custom vertices)
const customZoneMesh = shallowRef<THREE.Mesh | null>(null)

// Raycaster for mouse interaction
const raycaster = new THREE.Raycaster()
const mouse = new THREE.Vector2()

// Hover state
const isHovered = ref(false)

// Initialize camera
function initCamera(): void {
  const gate = GATES[props.gateId]
  if (!gate) {
    console.warn(`[GateCamera3D] Gate ${props.gateId} not found`)
    return
  }

  // Determine if we have custom detection zone vertices
  const hasCustomZone = props.detectionZoneVertices && props.detectionZoneVertices.length >= 3

  // Create camera instance (disable default cone if using custom zone)
  const camera3D = useGateCamera3D({
    showDefaultDetectionZone: !hasCustomZone,
  })
  cameraInstance.value = camera3D

  // Position at gate
  const worldPos = transformToWorld(gate.position, props.coordinateSystem)
  camera3D.mesh.position.set(worldPos.x, 0, worldPos.z)

  // Rotate to face vehicle entry direction
  const rotationRad = -gate.rotation * (Math.PI / 180) - CAMERA_ROTATION_OFFSET_RAD
  camera3D.mesh.rotation.y = rotationRad

  // Scale the camera to be visible in the yard
  // Make camera 5x larger for better visibility
  const cameraScale = 5.0
  camera3D.mesh.scale.setScalar(cameraScale)

  // Add to scene
  props.scene.add(camera3D.mesh)

  // Create custom detection zone if vertices provided
  if (hasCustomZone && props.detectionZoneVertices) {
    // Transform DXF vertices to world coordinates
    const worldVertices: DetectionZoneVertex[] = props.detectionZoneVertices.map(v => {
      const world = transformToWorld(v, props.coordinateSystem)
      return { x: world.x, z: world.z }
    })

    // Create the custom zone mesh
    const zoneMesh = createCustomDetectionZone(worldVertices, props.isWidgetOpen)
    customZoneMesh.value = zoneMesh
    props.scene.add(zoneMesh)
  }

  // Set initial state if widget is already open
  if (props.isWidgetOpen) {
    camera3D.setActive(true)
  }
}

// Handle mouse move for hover detection
function onMouseMove(event: MouseEvent): void {
  if (!cameraInstance.value || !props.container) return

  const rect = props.container.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(mouse, props.camera)

  const intersects = raycaster.intersectObjects(cameraInstance.value.mesh.children, true)

  const nowHovered = intersects.length > 0
  if (nowHovered !== isHovered.value) {
    isHovered.value = nowHovered
    cameraInstance.value.setHovered(nowHovered && !props.isWidgetOpen)
    emit('hover', nowHovered)
  }
}

// Handle click on camera
function onClick(_event: MouseEvent): void {
  if (!cameraInstance.value || !isHovered.value) return

  // Calculate screen position for widget
  const cameraWorldPos = new THREE.Vector3()
  cameraInstance.value.mesh.getWorldPosition(cameraWorldPos)

  // Project to screen coordinates
  const screenPos = cameraWorldPos.clone().project(props.camera)

  const rect = props.container.getBoundingClientRect()
  const x = ((screenPos.x + 1) / 2) * rect.width + rect.left
  const y = ((-screenPos.y + 1) / 2) * rect.height + rect.top

  // Offset to the right of the camera
  const offsetX = 20
  const widgetWidth = 300
  const widgetHeight = 400

  // Check if widget would go off-screen, if so position to the left
  let finalX = x + offsetX
  if (finalX + widgetWidth > window.innerWidth - 20) {
    finalX = x - offsetX - widgetWidth
  }

  // Ensure widget stays within vertical bounds
  let finalY = Math.max(20, Math.min(y - 50, window.innerHeight - widgetHeight - 20))

  emit('click', { x: finalX, y: finalY })
}

// Watch for widget state changes
watch(() => props.isWidgetOpen, (isOpen) => {
  if (cameraInstance.value) {
    cameraInstance.value.setActive(isOpen)
  }
  // Also update custom detection zone if present
  if (customZoneMesh.value) {
    updateDetectionZoneState(customZoneMesh.value, isOpen)
  }
})

// Expose trigger pulse method
function triggerPulse(): void {
  cameraInstance.value?.triggerPulse()
}

defineExpose({
  triggerPulse,
})

// Lifecycle
onMounted(() => {
  initCamera()
  props.container.addEventListener('mousemove', onMouseMove)
  props.container.addEventListener('click', onClick)
})

onUnmounted(() => {
  props.container.removeEventListener('mousemove', onMouseMove)
  props.container.removeEventListener('click', onClick)
  cameraInstance.value?.dispose()

  // Dispose custom detection zone if present
  if (customZoneMesh.value) {
    removeAndDispose(customZoneMesh.value)
    customZoneMesh.value = null
  }
})
</script>

<template>
  <!-- This is a renderless component - all rendering happens in Three.js -->
  <slot />
</template>
