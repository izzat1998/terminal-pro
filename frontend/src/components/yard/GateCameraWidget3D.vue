<script setup lang="ts">
/**
 * GateCameraWidget3D - CSS3D Wrapper for Gate Camera Widget
 *
 * Wraps GateCameraWidget for positioning in 3D space using CSS3DObject.
 * Designed to be placed in a CSS3DRenderer scene alongside the WebGL yard view.
 */

import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { CSS3DObject } from 'three/examples/jsm/renderers/CSS3DRenderer.js'
import GateCameraWidget from './GateCameraWidget.vue'
import type { VehicleDetectionResult } from '@/composables/useGateDetection'

// Widget dimensions for dock positioning (matching useCSS3DRenderer)
const WIDGET_WIDTH = 260
const WIDGET_HEIGHT = 200
const WIDGET_MARGIN = 16

type DockPosition = 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right'
type GateMode = 'entry' | 'exit'

interface Props {
  /** The CSS3D scene to add the widget to */
  css3DScene: THREE.Scene
  /** Dock position on screen */
  dockPosition: DockPosition
  /** Gate identifier */
  gateId?: string
  /** Container dimensions for position calculation */
  containerSize: { width: number; height: number }
  /** Gate mode - entry (inbound) or exit (outbound) */
  mode?: GateMode
}

const props = withDefaults(defineProps<Props>(), {
  dockPosition: 'bottom-left',
  gateId: 'Gate 01',
  mode: 'entry',
})

const emit = defineEmits<{
  vehicleDetected: [result: VehicleDetectionResult]
}>()

// Template ref for the wrapper element
const widgetWrapperRef = ref<HTMLDivElement | null>(null)

// CSS3DObject instance
let css3dObject: CSS3DObject | null = null

/**
 * Calculate screen position for a dock position
 * CSS3D uses screen coordinates with (0,0) at center
 */
function calculateDockPosition(
  dockPosition: DockPosition,
  screenWidth: number,
  screenHeight: number
): { x: number; y: number } {
  switch (dockPosition) {
    case 'bottom-left':
      return {
        x: -screenWidth / 2 + WIDGET_WIDTH / 2 + WIDGET_MARGIN,
        y: -screenHeight / 2 + WIDGET_HEIGHT / 2 + WIDGET_MARGIN,
      }

    case 'bottom-right':
      return {
        x: screenWidth / 2 - WIDGET_WIDTH / 2 - WIDGET_MARGIN,
        y: -screenHeight / 2 + WIDGET_HEIGHT / 2 + WIDGET_MARGIN,
      }

    case 'top-left':
      return {
        x: -screenWidth / 2 + WIDGET_WIDTH / 2 + WIDGET_MARGIN,
        y: screenHeight / 2 - WIDGET_HEIGHT / 2 - WIDGET_MARGIN,
      }

    case 'top-right':
      return {
        x: screenWidth / 2 - WIDGET_WIDTH / 2 - WIDGET_MARGIN,
        y: screenHeight / 2 - WIDGET_HEIGHT / 2 - WIDGET_MARGIN,
      }
  }
}

/**
 * Update the CSS3DObject position based on current container size and dock position
 */
function updatePosition(): void {
  if (!css3dObject) return

  const pos = calculateDockPosition(
    props.dockPosition,
    props.containerSize.width,
    props.containerSize.height
  )

  // Position in CSS3D space (Z=0 keeps it at the "screen plane")
  css3dObject.position.set(pos.x, pos.y, 0)
}

// Watch containerSize and update position on resize
watch(
  () => props.containerSize,
  () => {
    updatePosition()
  },
  { deep: true }
)

// Watch dockPosition changes
watch(
  () => props.dockPosition,
  () => {
    updatePosition()
  }
)

onMounted(() => {
  if (!widgetWrapperRef.value) {
    console.warn('GateCameraWidget3D: Wrapper element not available')
    return
  }

  // Enable pointer events on the widget itself
  widgetWrapperRef.value.style.pointerEvents = 'auto'

  // Create CSS3DObject from the wrapper element
  css3dObject = new CSS3DObject(widgetWrapperRef.value)
  css3dObject.name = `gate-widget-${props.dockPosition}`

  // Calculate initial position
  updatePosition()

  // Add to the CSS3D scene
  props.css3DScene.add(css3dObject)
})

onUnmounted(() => {
  // Remove CSS3DObject from scene
  if (css3dObject && props.css3DScene) {
    props.css3DScene.remove(css3dObject)
    css3dObject = null
  }
})
</script>

<template>
  <div ref="widgetWrapperRef" class="gate-widget-3d-wrapper">
    <GateCameraWidget
      :visible="true"
      :gateId="gateId"
      :mode="mode"
      @vehicleDetected="$emit('vehicleDetected', $event)"
    />
  </div>
</template>

<style scoped>
.gate-widget-3d-wrapper {
  /* Ensure widget is interactive */
  pointer-events: auto;
}
</style>
