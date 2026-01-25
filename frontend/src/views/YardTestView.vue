<script setup lang="ts">
/**
 * Yard Test View
 * Test page for the YardView3D component with debug mode integration
 *
 * Features:
 * - 3D yard visualization with DXF-based infrastructure
 * - Interactive gate camera with vehicle detection
 * - Vehicle spawning and animation to parking zones
 * - Debug mode with grid overlay and element inspection
 *
 * Debug Mode:
 * - Press 'D' to toggle debug mode
 * - URL param: ?debug=true
 */

import { ref, shallowRef, onMounted, onUnmounted, watch } from 'vue'
import type * as THREE from 'three'
import YardView3D from '@/components/YardView3D.vue'
import YardGridOverlay from '@/components/yard/YardGridOverlay.vue'
import YardDebugTooltip from '@/components/yard/YardDebugTooltip.vue'
import GateCamera3D from '@/components/yard/GateCamera3D.vue'
import GateCameraWidget from '@/components/yard/GateCameraWidget.vue'
import { useYardDebug } from '@/composables/useYardDebug'
import { useVehicles3D, type VehicleDetection } from '@/composables/useVehicles3D'
import { PATHS, ZONES } from '@/data/scenePositions'
import type { ContainerPosition, ContainerData } from '@/composables/useContainers3D'
import type { DxfCoordinateSystem } from '@/types/dxf'
import type { VehicleDetectionResult } from '@/composables/useGateDetection'

// YardView3D ref for accessing exposed properties
const yardViewRef = ref<InstanceType<typeof YardView3D>>()

// GateCamera3D ref for triggering pulse
const gateCameraRef = ref<InstanceType<typeof GateCamera3D>>()

// Exposed properties from YardView3D
const scene = shallowRef<THREE.Scene>()
const camera = shallowRef<THREE.Camera>()
const containerRef = ref<HTMLElement>()
const coordinateSystem = shallowRef<DxfCoordinateSystem | null>(null)

// Debug mode
const { isDebugMode, debugSettings, initDebugMode, disposeDebugMode } = useYardDebug()

// Gate camera widget state
const isWidgetOpen = ref(false)
const widgetPosition = ref({ x: 100, y: 100 })

// Vehicles3D composable (initialized after scene is ready)
let vehicles3D: ReturnType<typeof useVehicles3D> | null = null

// Vehicle counter for unique IDs
let vehicleIdCounter = 0
function generateVehicleId(): string {
  return `vehicle-${Date.now()}-${++vehicleIdCounter}`
}

// Active vehicle count for display
const activeVehicleCount = ref(0)

// Mock container data for testing
const mockContainerData = ref<ContainerData[]>([
  { id: 1, container_number: 'HDMU6565958', status: 'LADEN', container_type: '40GP', dwell_days: 5 },
  { id: 2, container_number: 'TCLU7894521', status: 'EMPTY', container_type: '40GP', dwell_days: 12 },
  { id: 3, container_number: 'MSKU9876543', status: 'LADEN', container_type: '40GP', dwell_days: 3 },
  { id: 4, container_number: 'TEMU1234567', status: 'LADEN', container_type: '40GP', dwell_days: 18 },
  { id: 5, container_number: 'CSQU4567890', status: 'EMPTY', container_type: '40GP', dwell_days: 7 },
])

// Container event handlers
function onContainerClick(container: ContainerPosition & { data?: ContainerData }): void {
  console.log('Container clicked:', container)
}

function onContainerHover(container: ContainerPosition & { data?: ContainerData } | null): void {
  if (container) {
    console.log('Hovering:', container.id)
  }
}

function onLoaded(stats: { entityCount: number; containerCount: number }): void {
  console.log('Yard loaded:', stats)

  // Get exposed properties from YardView3D
  if (yardViewRef.value) {
    scene.value = yardViewRef.value.scene
    camera.value = yardViewRef.value.camera
    containerRef.value = yardViewRef.value.containerRef
    coordinateSystem.value = yardViewRef.value.coordinateSystem

    // Initialize vehicles3D composable
    if (scene.value && coordinateSystem.value) {
      vehicles3D = useVehicles3D(scene.value, coordinateSystem)

      // Initialize label renderer for vehicle plates
      if (containerRef.value) {
        vehicles3D.initLabelRenderer(containerRef.value)
      }
    }
  }
}

function onError(message: string): void {
  console.error('Yard error:', message)
}

// Gate camera event handlers
function onCameraClick(screenPosition: { x: number; y: number }): void {
  widgetPosition.value = screenPosition
  isWidgetOpen.value = true
}

function onWidgetClose(): void {
  isWidgetOpen.value = false
}

// Vehicle detection handler
async function onVehicleDetected(result: VehicleDetectionResult): Promise<void> {
  if (!vehicles3D || !coordinateSystem.value) {
    console.warn('Vehicles3D not initialized')
    return
  }

  // Trigger camera pulse effect
  gateCameraRef.value?.triggerPulse()

  const vehicleId = generateVehicleId()

  // Create vehicle detection object
  const detection: VehicleDetection = {
    id: vehicleId,
    plateNumber: result.plateNumber,
    vehicleType: result.vehicleType,
    gateId: 'main',
    direction: 'entering',
  }

  // Spawn vehicle at gate
  const vehicle = vehicles3D.spawnVehicle(detection)
  if (!vehicle) {
    console.error('Failed to spawn vehicle')
    return
  }

  activeVehicleCount.value = vehicles3D.getAllVehicles().length

  // Pick a random parking zone
  const zoneIds = Object.keys(ZONES)
  const targetZone = zoneIds[Math.floor(Math.random() * zoneIds.length)]
  const pathId = `main_to_${targetZone}`
  const path = PATHS[pathId]

  if (path) {
    // Animate vehicle along path
    await vehicles3D.animateVehicleAlongPath(vehicle, path)
  }

  // Remove vehicle after 30 seconds (for demo)
  setTimeout(() => {
    if (vehicles3D) {
      vehicles3D.removeVehicle(vehicleId)
      activeVehicleCount.value = vehicles3D.getAllVehicles().length
    }
  }, 30000)
}

// Watch for YardView3D to be ready
watch(yardViewRef, (ref) => {
  if (ref) {
    scene.value = ref.scene
    camera.value = ref.camera
    containerRef.value = ref.containerRef
    coordinateSystem.value = ref.coordinateSystem
  }
}, { immediate: true })

// Lifecycle
onMounted(() => {
  initDebugMode()
})

onUnmounted(() => {
  disposeDebugMode()
  vehicles3D?.dispose()
})
</script>

<template>
  <div class="yard-test-page">
    <div class="page-header">
      <h1>3D Yard Visualization Test</h1>
      <p>
        Testing DXF-based terminal rendering with interactive containers
        <span v-if="isDebugMode" class="debug-badge">DEBUG MODE (Press D to toggle)</span>
      </p>
    </div>

    <div class="yard-container">
      <YardView3D
        ref="yardViewRef"
        dxf-url="/yard.dxf"
        :container-data="mockContainerData"
        height="calc(100vh - 150px)"
        :show-layer-panel="true"
        :show-stats="true"
        color-mode="status"
        :interactive="true"
        @container-click="onContainerClick"
        @container-hover="onContainerHover"
        @loaded="onLoaded"
        @error="onError"
      />

      <!-- 3D Gate Camera (clickable) -->
      <GateCamera3D
        v-if="scene && camera && coordinateSystem && containerRef"
        ref="gateCameraRef"
        :scene="scene"
        :camera="camera"
        :coordinate-system="coordinateSystem"
        :container="containerRef"
        :is-widget-open="isWidgetOpen"
        gate-id="main"
        @click="onCameraClick"
      />

      <!-- Gate Camera Widget (floating panel) -->
      <GateCameraWidget
        :visible="isWidgetOpen"
        :position="widgetPosition"
        initial-source="mock"
        @close="onWidgetClose"
        @vehicle-detected="onVehicleDetected"
      />

      <!-- Vehicle Count Indicator -->
      <div v-if="activeVehicleCount > 0" class="vehicle-indicator">
        <span class="vehicle-icon">🚛</span>
        <span class="vehicle-count">{{ activeVehicleCount }}</span>
      </div>

      <!-- Debug Grid Overlay (lines only) -->
      <YardGridOverlay
        v-if="isDebugMode && debugSettings.showGrid && coordinateSystem && scene"
        :coordinate-system="coordinateSystem"
        :scene="scene"
        :visible="true"
      />

      <!-- Debug Tooltip (cursor-based) -->
      <YardDebugTooltip
        v-if="isDebugMode"
        :scene="scene"
        :camera="camera"
        :container="containerRef"
        :coordinate-system="coordinateSystem"
        :enabled="debugSettings.showLabels"
      />

      <!-- Debug Mode Indicator -->
      <div v-if="isDebugMode" class="debug-indicator">
        <div class="debug-controls">
          <a-checkbox v-model:checked="debugSettings.showGrid">Grid</a-checkbox>
          <a-checkbox v-model:checked="debugSettings.showLabels">Tooltip</a-checkbox>
          <a-checkbox v-model:checked="debugSettings.showCoordinates">Coords</a-checkbox>
        </div>
        <div v-if="debugSettings.showCoordinates && coordinateSystem" class="coord-display">
          Yard: {{ coordinateSystem.bounds?.width.toFixed(0) }}m × {{ coordinateSystem.bounds?.height.toFixed(0) }}m
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.yard-test-page {
  padding: 16px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-header {
  margin-bottom: 16px;
}

.page-header h1 {
  margin: 0 0 4px 0;
  font-size: 20px;
}

.page-header p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.debug-badge {
  display: inline-block;
  margin-left: 12px;
  padding: 2px 8px;
  background: #ff4d4f;
  color: white;
  font-size: 11px;
  font-weight: 600;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.yard-container {
  flex: 1;
  min-height: 0;
  position: relative;
}

.debug-indicator {
  position: absolute;
  bottom: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.95);
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 100;
}

.debug-controls {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}

.coord-display {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #666;
}

.vehicle-indicator {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.95);
  padding: 8px 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 100;
}

.vehicle-icon {
  font-size: 20px;
}

.vehicle-count {
  font-weight: 600;
  font-size: 16px;
  color: #1890ff;
}
</style>
