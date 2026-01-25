<script setup lang="ts">
/**
 * GateCamera3D - Interactive 3D camera component for yard scene
 *
 * Renders a 3D security camera at the gate position.
 * Handles mouse interaction (hover, click) using raycasting.
 */

import { ref, shallowRef, onMounted, onUnmounted, watch } from 'vue'
import * as THREE from 'three'
import { useGateCamera3D, type UseGateCamera3DReturn } from '@/composables/useGateCamera3D'
import { GATES, transformToWorld } from '@/data/scenePositions'
import type { DxfCoordinateSystem } from '@/types/dxf'

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
}

const props = withDefaults(defineProps<Props>(), {
  gateId: 'main',
  isWidgetOpen: false,
})

const emit = defineEmits<{
  click: [screenPosition: { x: number; y: number }]
  hover: [isHovered: boolean]
}>()

// Camera instance
const cameraInstance = shallowRef<UseGateCamera3DReturn | null>(null)

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

  // Create camera instance
  const camera3D = useGateCamera3D()
  cameraInstance.value = camera3D

  // Position at gate
  const worldPos = transformToWorld(gate.position, props.coordinateSystem)
  camera3D.mesh.position.set(worldPos.x, 0, worldPos.z)

  // Rotate to face into the yard (opposite of vehicle entry direction)
  const rotationRad = -gate.rotation * (Math.PI / 180) + Math.PI
  camera3D.mesh.rotation.y = rotationRad

  // Add to scene
  props.scene.add(camera3D.mesh)

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
})
</script>

<template>
  <!-- This is a renderless component - all rendering happens in Three.js -->
  <slot />
</template>
