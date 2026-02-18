<script setup lang="ts">
/**
 * Unified Yard View
 * Production terminal operations center with 3D yard visualization
 * backed by real API data.
 *
 * Features:
 * - 3D yard visualization with DXF-based infrastructure
 * - Real container data from backend API (auto-refreshes every 30s)
 * - Interactive gate camera with vehicle detection
 * - Vehicle spawning and animation to parking zones
 * - Real-time statistics and monitoring
 * - Debug mode for development (Press D)
 */

import { ref, shallowRef, onMounted, onUnmounted, watch, computed } from 'vue'
import type * as THREE from 'three'
import YardView3D from '@/components/YardView3D.vue'
import { isInputElement } from '@/utils/keyboardUtils'

import YardGridOverlay from '@/components/yard/YardGridOverlay.vue'
import YardDebugTooltip from '@/components/yard/YardDebugTooltip.vue'
import YardDrawOverlay from '@/components/yard/YardDrawOverlay.vue'
import GateCamera3D from '@/components/yard/GateCamera3D.vue'
import GateCameraWidget from '@/components/yard/GateCameraWidget.vue'
import GateStatsHeader from '@/components/yard/GateStatsHeader.vue'
import { useYardDebug } from '@/composables/useYardDebug'
import { useYardDraw } from '@/composables/useYardDraw'
import { useVehicles3D, type VehicleDetection } from '@/composables/useVehicles3D'
import { useGateEventPoller, type GateEntryEvent } from '@/composables/useGateEventPoller'
import type { ContainerPosition, ContainerData } from '@/composables/useContainers3D'
import type { DxfCoordinateSystem } from '@/types/dxf'
import type { VehicleDetectionResult } from '@/composables/useGateDetection'
import type { VehicleType } from '@/composables/useVehicleModels'
import { getYardSlots, type YardSlot } from '@/services/yardService'
import { gateVehicleService } from '@/services/gateVehicleService'

// ============ API Data Loading ============

const containerData = ref<ContainerData[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
let refreshInterval: ReturnType<typeof setInterval> | null = null

/** Map API yard slots to ContainerData[] for the 3D renderer */
function mapSlotsToContainerData(slots: YardSlot[]): ContainerData[] {
  return slots
    .filter((s): s is YardSlot & { container_entry: NonNullable<YardSlot['container_entry']> } =>
      s.container_entry !== null
    )
    .map((s) => ({
      id: s.id,
      container_number: s.container_entry.container_number,
      status: s.container_entry.status === 'LADEN' ? 'LADEN' : 'EMPTY',
      container_type: s.container_entry.iso_type?.startsWith('4') ? '40GP' : '20GP',
      dwell_days: s.container_entry.dwell_time_days,
      company_name: s.container_entry.company_name ?? undefined,
      is_hazmat: s.container_entry.is_hazmat,
      imo_class: s.container_entry.imo_class ?? undefined,
      priority: s.container_entry.priority as ContainerData['priority'],
      entry_time: s.container_entry.entry_time,
    } as ContainerData))
}

/** Map API yard slots to ContainerPosition[] for 3D positioning */
function mapSlotsToPositions(slots: YardSlot[]): ContainerPosition[] {
  return slots
    .filter((s) => s.dxf_x !== null && s.dxf_y !== null)
    .map((s) => ({
      id: s.id,
      x: 0, // Will be computed from _original by useContainers3D
      y: 0,
      rotation: s.rotation,
      blockName: s.container_size === '20ft' ? '20ft' : '40ft',
      layer: 'Т-Контейнеры',
      tier: s.tier,
      _original: {
        x: s.dxf_x!,
        y: s.dxf_y!,
      },
    }))
}

// Store slot positions for the 3D renderer
const slotPositions = ref<ContainerPosition[]>([])

async function fetchYardData(): Promise<void> {
  try {
    const slots = await getYardSlots()
    slotPositions.value = mapSlotsToPositions(slots)
    containerData.value = mapSlotsToContainerData(slots)
    error.value = null
  } catch (e) {
    console.error('[UnifiedYardView] Failed to fetch yard data:', e)
    error.value = 'Не удалось загрузить данные площадки'
  } finally {
    loading.value = false
  }
}

// ============ YardView3D Setup ============

const yardViewRef = ref<InstanceType<typeof YardView3D>>()
const gateCameraRef = ref<InstanceType<typeof GateCamera3D>>()

const scene = shallowRef<THREE.Scene>()
const camera = shallowRef<THREE.Camera>()
const containerRef = ref<HTMLElement>()
const coordinateSystem = shallowRef<DxfCoordinateSystem | null>(null)

// Debug mode
const { isDebugMode, debugSettings, initDebugMode, disposeDebugMode } = useYardDebug()

// Draw mode for coordinate capture
const {
  isDrawMode,
  points: drawPoints,
  initDrawMode,
  disposeDrawMode,
} = useYardDraw({
  scene,
  camera,
  container: containerRef,
  coordinateSystem,
})

// Test vehicle movement using drawn points
async function testVehicleWithPoints(): Promise<void> {
  if (!vehicles3D) return

  const points = drawPoints.value
  if (points.length < 2) return

  const startPoint = points[0]
  const endPoint = points[1]
  if (!startPoint || !endPoint) return

  const vehicleId = generateVehicleId()
  const detection = {
    id: vehicleId,
    plateNumber: 'TEST-001',
    vehicleType: 'TRUCK' as const,
    direction: 'entering' as const,
  }

  const vehicle = vehicles3D.spawnVehicleAtPosition(
    detection,
    startPoint.dxf.x,
    startPoint.dxf.y,
    { x: endPoint.dxf.x, y: endPoint.dxf.y }
  )

  if (!vehicle) return

  activeVehicleCount.value = vehicles3D.getAllVehicles().length

  await new Promise(r => setTimeout(r, 500))
  await vehicles3D.animateVehicleToPosition(vehicle, endPoint.dxf.x, endPoint.dxf.y)

  await new Promise(r => setTimeout(r, 1000))
  await vehicles3D.fadeOutVehicle(vehicleId, 1500)

  activeVehicleCount.value = vehicles3D.getAllVehicles().length
}

// Expose test function to console
if (import.meta.env.DEV) {
  (window as Window & { testVehicle?: () => void }).testVehicle = testVehicleWithPoints
}

// Gate camera widget state
const isWidgetOpen = ref(false)
const isCameraWidgetVisible = ref(true)
const isExitCameraWidgetVisible = ref(true)

// Vehicles3D composable
let vehicles3D: ReturnType<typeof useVehicles3D> | null = null

// Vehicle counter for unique IDs
let vehicleIdCounter = 0
function generateVehicleId(): string {
  return `vehicle-${Date.now()}-${++vehicleIdCounter}`
}

const activeVehicleCount = ref(0)

// Vehicle entry statistics
interface VehicleEntryRecord {
  id: string
  plateNumber: string
  vehicleType: VehicleType
  timestamp: number
  direction: 'entering' | 'exiting'
}
const vehicleEntries = ref<VehicleEntryRecord[]>([])

// Guard map to prevent concurrent animation chains per vehicle plate
const animatingPlates = new Set<string>()

// ============ Gate Event Poller (API-driven animations) ============

// Gate animation waypoints (DXF coordinates)
const GATE_SPAWN = { x: 12866, y: 73398 }   // Gate entrance
const GATE_DEST  = { x: 12925, y: 73382 }   // Inside yard

// Detection zone polygon for 3D gate camera (DXF coordinates)
const GATE_DETECTION_ZONE = [
  { x: 12860, y: 73390 },
  { x: 12865, y: 73407 },
  { x: 12871, y: 73402 },
  { x: 12870, y: 73392 },
]

/** Options to control DB interaction */
interface AnimateOptions {
  /** If true, validate + write to DB before animating (camera-triggered).
   *  If false, just animate (poller-triggered — DB already has the record). */
  saveToDB?: boolean
}

/** Animate an entry event (shared by camera + poller) */
async function animateEntry(
  plateNumber: string,
  vehicleType: VehicleType,
  options: AnimateOptions = {},
): Promise<void> {
  if (!vehicles3D || !coordinateSystem.value) return
  if (animatingPlates.has(plateNumber)) return
  animatingPlates.add(plateNumber)

  try {
    // Camera-triggered: create VehicleEntry in DB first. Skip animation if it fails.
    if (options.saveToDB) {
      try {
        const transportType = vehicleType === 'WAGON' ? 'WAGON' : 'TRUCK'
        await gateVehicleService.createEntry(plateNumber, transportType)
      } catch (e) {
        // Entry failed (duplicate plate on terminal, validation error, etc.)
        if (import.meta.env.DEV) console.warn('[Gate] Entry rejected:', e)
        return
      }
    }

    const vehicleId = generateVehicleId()
    const detection: VehicleDetection = {
      id: vehicleId,
      plateNumber,
      vehicleType,
      direction: 'entering',
    }

    vehicleEntries.value = [
      ...vehicleEntries.value,
      { id: vehicleId, plateNumber, vehicleType, timestamp: Date.now(), direction: 'entering' },
    ]

    // Spawn at gate, facing destination
    const vehicle = vehicles3D.spawnVehicleAtPosition(
      detection, GATE_SPAWN.x, GATE_SPAWN.y,
      { x: GATE_DEST.x, y: GATE_DEST.y },
    )
    if (!vehicle) return

    activeVehicleCount.value = vehicles3D.getAllVehicles().length
    await vehicles3D.animateVehicleToPosition(vehicle, GATE_DEST.x, GATE_DEST.y)
    await vehicles3D.fadeOutVehicle(vehicleId, 1000)
    activeVehicleCount.value = vehicles3D.getAllVehicles().length
  } finally {
    animatingPlates.delete(plateNumber)
  }
}

/** Animate an exit event (shared by camera + poller) */
async function animateExit(
  plateNumber: string,
  vehicleType: VehicleType,
  options: AnimateOptions = {},
): Promise<void> {
  if (!vehicles3D || !coordinateSystem.value) return
  if (animatingPlates.has(plateNumber)) return
  animatingPlates.add(plateNumber)

  try {
    // Camera-triggered: register exit in DB first. Skip animation if vehicle not on terminal.
    if (options.saveToDB) {
      try {
        await gateVehicleService.registerExit(plateNumber)
      } catch (e) {
        // Exit failed (vehicle not on terminal, not found, etc.)
        if (import.meta.env.DEV) console.warn('[Gate] Exit rejected — vehicle not on terminal:', e)
        return
      }
    }

    const vehicleId = generateVehicleId()
    const detection: VehicleDetection = {
      id: vehicleId,
      plateNumber,
      vehicleType,
      direction: 'exiting',
    }

    vehicleEntries.value = [
      ...vehicleEntries.value,
      { id: vehicleId, plateNumber, vehicleType, timestamp: Date.now(), direction: 'exiting' },
    ]

    // Spawn inside yard, facing gate (reverse of entry)
    const vehicle = vehicles3D.spawnVehicleAtPosition(
      detection, GATE_DEST.x, GATE_DEST.y,
      { x: GATE_SPAWN.x, y: GATE_SPAWN.y },
    )
    if (!vehicle) return

    activeVehicleCount.value = vehicles3D.getAllVehicles().length
    await vehicles3D.animateVehicleToPosition(vehicle, GATE_SPAWN.x, GATE_SPAWN.y)
    await vehicles3D.fadeOutVehicle(vehicleId, 1000)
    activeVehicleCount.value = vehicles3D.getAllVehicles().length
  } finally {
    animatingPlates.delete(plateNumber)
  }
}

const gatePoller = useGateEventPoller({
  interval: 5000,
  onNewEntry(event: GateEntryEvent) {
    animateEntry(event.plateNumber, event.vehicleType)
  },
  onNewExit(event: GateEntryEvent) {
    animateExit(event.plateNumber, event.vehicleType)
  },
})

// Current time for header
const currentTime = ref(new Date())
let timeInterval: ReturnType<typeof setInterval> | null = null

const formattedTime = computed(() => {
  return currentTime.value.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
})

const formattedDate = computed(() => {
  return currentTime.value.toLocaleDateString('ru-RU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
})

// Container event handlers
function onContainerClick(container: ContainerPosition & { data?: ContainerData }): void {
  if (import.meta.env.DEV) console.log('Container clicked:', container)
}

function onContainerHover(container: ContainerPosition & { data?: ContainerData } | null): void {
  if (import.meta.env.DEV && container) {
    console.log('Hovering:', container.id)
  }
}

function onLoaded(stats: { entityCount: number; containerCount: number }): void {
  if (import.meta.env.DEV) console.log('Yard loaded:', stats)

  if (yardViewRef.value) {
    scene.value = yardViewRef.value.scene
    camera.value = yardViewRef.value.camera
    containerRef.value = yardViewRef.value.containerRef
    coordinateSystem.value = yardViewRef.value.coordinateSystem

    if (scene.value && coordinateSystem.value) {
      vehicles3D = useVehicles3D(scene.value, coordinateSystem)

      if (containerRef.value) {
        vehicles3D.initLabelRenderer(containerRef.value)
      }

      // Start polling for gate events (Telegram bot entries/exits)
      gatePoller.start()
    }
  }
}

// ============ Event Handlers ============

function onError(message: string): void {
  if (import.meta.env.DEV) console.error('Yard error:', message)
}

function onCameraClick(): void {
  isCameraWidgetVisible.value = !isCameraWidgetVisible.value
  isWidgetOpen.value = isCameraWidgetVisible.value
}

/** Handle entry camera detection -- deduplicates and animates.
 *  WebSocket/IP-cam detections skip saveToDB because the ANPR webhook
 *  already saved the detection on the backend side. */
async function onVehicleDetected(result: VehicleDetectionResult): Promise<void> {
  gateCameraRef.value?.triggerPulse()
  gatePoller.addCameraPlate(result.plateNumber)
  await animateEntry(result.plateNumber, result.vehicleType)
}

/** Handle exit camera detection -- saves to DB, deduplicates, and animates */
async function onExitDetected(result: VehicleDetectionResult): Promise<void> {
  gatePoller.addCameraPlate(result.plateNumber)
  await animateExit(result.plateNumber, result.vehicleType, { saveToDB: true })
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

// Keyboard handler for test vehicle (T key)
function handleTestKeydown(event: KeyboardEvent): void {
  if (isInputElement(event)) return

  if (event.key.toLowerCase() === 't' && isDrawMode.value && drawPoints.value.length >= 2) {
    testVehicleWithPoints()
  }
}

// Lifecycle
onMounted(async () => {
  initDebugMode()
  initDrawMode()
  window.addEventListener('keydown', handleTestKeydown)

  // Start clock
  timeInterval = setInterval(() => {
    currentTime.value = new Date()
  }, 1000)

  // Fetch yard data
  await fetchYardData()

  // Auto-refresh every 30 seconds
  refreshInterval = setInterval(fetchYardData, 30_000)
})

onUnmounted(() => {
  gatePoller.stop()
  disposeDebugMode()
  disposeDrawMode()
  window.removeEventListener('keydown', handleTestKeydown)
  vehicles3D?.dispose()
  if (refreshInterval) clearInterval(refreshInterval)
  if (timeInterval) clearInterval(timeInterval)
})
</script>

<template>
  <div class="ops-center">
    <!-- Top Navigation Bar -->
    <header class="ops-header">
      <div class="header-left">
        <div class="brand">
          <div class="brand-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="6" width="22" height="12" rx="2"/>
              <path d="M1 10h22"/>
              <path d="M6 6V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2"/>
            </svg>
          </div>
          <div class="brand-text">
            <span class="brand-name">MTT Terminal</span>
            <span class="brand-sub">Operations Center</span>
          </div>
        </div>
      </div>

      <div class="header-center">
        <GateStatsHeader
          :entries="vehicleEntries"
          :is-active="activeVehicleCount > 0"
        />
      </div>

      <div class="header-right">
        <div class="header-time">
          <span class="time-value">{{ formattedTime }}</span>
          <span class="time-date">{{ formattedDate }}</span>
        </div>

        <div v-if="isDebugMode" class="debug-pill">
          <span class="debug-dot"></span>
          <span>DEV</span>
        </div>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="ops-main">
      <!-- Loading State -->
      <div v-if="loading" class="yard-loading">
        <a-spin size="large" />
        <span class="loading-text">Загрузка площадки...</span>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="yard-error">
        <a-result status="warning" :title="error" sub-title="Попробуйте обновить страницу">
          <template #extra>
            <a-button type="primary" @click="fetchYardData">Повторить</a-button>
          </template>
        </a-result>
      </div>

      <!-- 3D Yard Visualization -->
      <div v-else class="yard-viewport">
        <YardView3D
          ref="yardViewRef"
          dxf-url="/yard.dxf"
          :container-data="containerData"
          :container-positions="slotPositions"
          height="100%"
          :show-layer-panel="true"
          :show-stats="true"
          color-mode="status"
          :interactive="true"
          :show-test-vehicles="false"
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
          :detection-zone-vertices="GATE_DETECTION_ZONE"
          gate-id="main"
          @click="onCameraClick"
        />

        <!-- Debug Grid Overlay -->
        <YardGridOverlay
          v-if="isDebugMode && debugSettings.showGrid && coordinateSystem && scene"
          :coordinate-system="coordinateSystem"
          :scene="scene"
          :visible="true"
        />

        <!-- Debug Tooltip -->
        <YardDebugTooltip
          v-if="isDebugMode"
          :scene="scene"
          :camera="camera"
          :container="containerRef"
          :coordinate-system="coordinateSystem"
          :enabled="debugSettings.showLabels"
        />

        <!-- Draw Mode Overlay -->
        <YardDrawOverlay
          v-if="isDebugMode && scene"
          :scene="scene"
          :points="drawPoints"
          :active="isDrawMode"
        />

      </div>

      <!-- Gate Camera Widgets (docked to right side) -->
      <div class="gate-widgets-dock">
        <!-- Entry Camera Widget -->
        <GateCameraWidget
          :visible="isCameraWidgetVisible"
          mode="entry"
          initial-source="mock"
          gate-id="Въезд А"
          @vehicle-detected="onVehicleDetected"
        />

        <!-- Exit Camera Widget -->
        <GateCameraWidget
          :visible="isExitCameraWidgetVisible"
          mode="exit"
          initial-source="mock"
          gate-id="Выезд А"
          @vehicle-detected="onExitDetected"
        />
      </div>
    </main>

    <!-- Debug Panel (only in debug mode) -->
    <Transition name="panel-slide">
      <aside v-if="isDebugMode" class="debug-panel">
        <div class="debug-panel-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 20h9"/>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
          </svg>
          <span>Инструменты разработчика</span>
        </div>

        <div class="debug-section">
          <div class="debug-section-title">Отображение</div>
          <label class="debug-toggle">
            <input type="checkbox" v-model="debugSettings.showGrid" />
            <span class="toggle-slider"></span>
            <span class="toggle-label">Сетка координат</span>
          </label>
          <label class="debug-toggle">
            <input type="checkbox" v-model="debugSettings.showLabels" />
            <span class="toggle-slider"></span>
            <span class="toggle-label">Подсказки</span>
          </label>
          <label class="debug-toggle">
            <input type="checkbox" v-model="debugSettings.showCoordinates" />
            <span class="toggle-slider"></span>
            <span class="toggle-label">Координаты</span>
          </label>
        </div>

        <div v-if="debugSettings.showCoordinates && coordinateSystem" class="debug-section">
          <div class="debug-section-title">Размеры площадки</div>
          <div class="debug-info">
            <span class="info-label">Ширина:</span>
            <span class="info-value">{{ coordinateSystem.bounds?.width.toFixed(0) }}м</span>
          </div>
          <div class="debug-info">
            <span class="info-label">Высота:</span>
            <span class="info-value">{{ coordinateSystem.bounds?.height.toFixed(0) }}м</span>
          </div>
        </div>

        <div v-if="isDrawMode" class="debug-section draw-mode-section">
          <div class="debug-section-title">
            <span class="draw-dot"></span>
            Режим рисования
          </div>
          <div class="draw-point-count">
            <span class="count-value">{{ drawPoints.length }}</span>
            <span class="count-label">точек</span>
          </div>
          <div class="draw-shortcuts">
            <kbd>M</kbd> переключить
            <kbd>C</kbd> очистить
            <kbd>Z</kbd> отменить
            <kbd>Enter</kbd> экспорт
          </div>
          <div v-if="drawPoints.length >= 2" class="draw-test-action">
            <kbd>T</kbd> Тест движения
          </div>
        </div>

        <div class="debug-footer">
          <kbd>D</kbd> скрыть панель
        </div>
      </aside>
    </Transition>
  </div>
</template>

<style scoped>
/* ============================================
   OPERATIONS CENTER - Light Professional Theme
   ============================================ */

.ops-center {
  --color-bg: var(--color-bg-page, #f8fafc);
  --color-surface: var(--color-bg-card, #ffffff);
  --color-surface-elevated: var(--color-bg-card, #ffffff);
  --color-border: var(--color-border, #e2e8f0);
  --color-border-subtle: var(--color-border-light, #f1f5f9);

  --color-text-primary: var(--color-text, #1e293b);
  --color-text-secondary: var(--color-text-secondary, #64748b);
  --color-text-muted: var(--color-text-muted, #94a3b8);

  --color-accent: var(--color-primary, #3b82f6);
  --color-accent-hover: var(--color-primary-hover, #2563eb);
  --color-accent-light: var(--color-primary-light, #dbeafe);
  --color-success: var(--color-success, #10b981);
  --color-success-light: var(--color-success-light, #d1fae5);
  --color-warning: var(--color-warning, #f59e0b);
  --color-warning-light: var(--color-warning-light, #fef3c7);
  --color-error: var(--color-danger, #ef4444);

  --shadow-sm: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.06));
  --shadow-md: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.08));
  --shadow-lg: var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.08));

  --radius-sm: var(--radius-sm, 4px);
  --radius-md: var(--radius-md, 6px);
  --radius-lg: var(--radius-lg, 8px);
  --radius-xl: 16px;

  --font-sans: var(--font-body, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
  --font-mono: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;

  --transition-fast: 150ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;

  display: flex;
  flex-direction: column;
  /* Account for AppLayout: header(64px) + content margin(32px) + footer(~50px) */
  height: calc(100vh - 160px);
  background: var(--color-bg);
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  overflow: hidden;
}

/* ============ HEADER ============ */
.ops-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 12px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  z-index: 100;
  flex-shrink: 0;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  max-width: 800px;
  margin: 0 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--color-accent) 0%, #1d4ed8 100%);
  border-radius: var(--radius-sm);
  color: white;
}

.brand-icon svg {
  width: 18px;
  height: 18px;
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
}

.brand-sub {
  font-size: 10px;
  font-weight: 500;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.header-time {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}

.time-value {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
}

.time-date {
  font-size: 10px;
  color: var(--color-text-muted);
}

.debug-pill {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: var(--color-warning-light);
  border: 1px solid #fcd34d;
  border-radius: 100px;
  font-size: 9px;
  font-weight: 600;
  color: var(--color-warning);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.debug-dot {
  width: 6px;
  height: 6px;
  background: var(--color-warning);
  border-radius: 50%;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ============ MAIN CONTENT ============ */
.ops-main {
  flex: 1;
  display: flex;
  position: relative;
  min-height: 0;
  padding: 8px;
  gap: 8px;
}

.yard-viewport {
  flex: 1;
  position: relative;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

/* Loading & Error States */
.yard-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
}

.loading-text {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.yard-error {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
}

/* ============ DEBUG PANEL ============ */
.debug-panel {
  position: absolute;
  bottom: 16px;
  right: 16px;
  width: 280px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 100;
  overflow: hidden;
}

.debug-panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.debug-panel-header svg {
  width: 16px;
  height: 16px;
  color: var(--color-text-muted);
}

.debug-section {
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.debug-section:last-of-type {
  border-bottom: none;
}

.debug-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.debug-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  margin-bottom: 8px;
}

.debug-toggle:last-child {
  margin-bottom: 0;
}

.debug-toggle input {
  display: none;
}

.toggle-slider {
  position: relative;
  width: 36px;
  height: 20px;
  background: var(--color-border);
  border-radius: 10px;
  transition: background var(--transition-fast);
  flex-shrink: 0;
}

.toggle-slider::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: white;
  border-radius: 50%;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast);
}

.debug-toggle input:checked + .toggle-slider {
  background: var(--color-accent);
}

.debug-toggle input:checked + .toggle-slider::after {
  transform: translateX(16px);
}

.toggle-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.debug-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
}

.info-label {
  font-size: 13px;
  color: var(--color-text-muted);
}

.info-value {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.draw-mode-section {
  background: linear-gradient(to bottom, rgba(239, 68, 68, 0.05), transparent);
}

.draw-dot {
  width: 8px;
  height: 8px;
  background: var(--color-error);
  border-radius: 50%;
  animation: pulse-dot 1s ease-in-out infinite;
}

.draw-point-count {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 12px;
}

.count-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-error);
}

.count-label {
  font-size: 13px;
  color: var(--color-text-muted);
}

.draw-shortcuts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: var(--color-text-muted);
}

.draw-test-action {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  font-size: 12px;
  color: var(--color-success);
  font-weight: 500;
}

kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.debug-footer {
  padding: 10px 16px;
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
  font-size: 11px;
  color: var(--color-text-muted);
  text-align: center;
}

.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all var(--transition-slow);
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

/* ============ Gate Camera Widgets Dock ============ */
.gate-widgets-dock {
  position: absolute;
  right: 12px;
  bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 50;
}
</style>
