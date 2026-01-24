<script setup lang="ts">
/**
 * GateCameraTestView - Development Testing Page for Gate Camera Integration
 *
 * Combines GateCameraPanel (left) with YardView3D (right) to test
 * the full flow from vehicle detection to 3D visualization.
 */

import { ref, shallowRef, onMounted, onUnmounted, computed, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import GateCameraPanel from '@/components/gate/GateCameraPanel.vue'
import { useVehicles3D, type VehicleDetection } from '@/composables/useVehicles3D'
import { useDxfYard } from '@/composables/useDxfYard'
import { useContainers3D, addRandomStacking, type ContainerPosition } from '@/composables/useContainers3D'
import { useBuildings3D, type BuildingPosition } from '@/composables/useBuildings3D'
import { PATHS, ZONES, GATES, transformToWorld } from '@/data/scenePositions'
import type { VehicleDetectionResult } from '@/composables/useGateDetection'
import containersJson from '@/data/containers.json'
import buildingsJson from '@/data/buildings.json'

// Premium color palette
const PREMIUM_COLORS = {
  primary: 0x0077B6,
  secondary: 0x00B4D8,
  ground: 0xE8F4F8,
  background: 0xF0F7FA,
  gridCenter: 0xCCE5ED,
  gridLines: 0xDDEEF4,
}

// Refs
const canvasRef = ref<HTMLCanvasElement>()
const containerRef = ref<HTMLDivElement>()

// Three.js core objects
const scene = shallowRef<THREE.Scene>()
const camera = shallowRef<THREE.OrthographicCamera>()
const renderer = shallowRef<THREE.WebGLRenderer>()
const controls = shallowRef<OrbitControls>()

// Animation
let animationId: number | null = null

// Container group reference for camera fitting
const containerGroup = shallowRef<THREE.Group | null>(null)

// State
const isInitialized = ref(false)
const isLoading = ref(true)
const activeVehicleCount = ref(0)

// DXF/Yard composable
const {
  coordinateSystem,
  loadFromUrl,
  yardGroup,
  dispose: disposeYard,
} = useDxfYard()

// Container positions from JSON
const containerPositions = ref<ContainerPosition[]>(
  addRandomStacking(containersJson as ContainerPosition[], {
    maxTier: 3,
    stackRate: 0.5,
  })
)
const containerDataRef = computed(() => [])

const {
  createContainerMeshes,
  dispose: disposeContainers,
} = useContainers3D(containerPositions, containerDataRef)

// Building positions
const buildingPositions = ref<BuildingPosition[]>(
  (buildingsJson as { buildings: BuildingPosition[] }).buildings
)

const {
  createBuildingMeshes,
  dispose: disposeBuildings,
} = useBuildings3D(buildingPositions)

// Vehicles3D composable - will be initialized after scene is ready
let vehicles3D: ReturnType<typeof useVehicles3D> | null = null

// Event log for display
interface DetectionLogEntry {
  id: string
  plateNumber: string
  vehicleType: string
  timestamp: string
  status: 'detected' | 'spawned' | 'animating' | 'parked'
}

const detectionLog = ref<DetectionLogEntry[]>([])
const MAX_LOG_ENTRIES = 20

// Generate unique ID for vehicles
let vehicleIdCounter = 0
function generateVehicleId(): string {
  return `vehicle-${Date.now()}-${++vehicleIdCounter}`
}

// Initialize Three.js scene
function initScene(): void {
  if (!canvasRef.value || isInitialized.value) return

  scene.value = new THREE.Scene()
  scene.value.background = new THREE.Color(PREMIUM_COLORS.background)
  scene.value.fog = new THREE.Fog(PREMIUM_COLORS.background, 300, 800)

  const aspect = canvasRef.value.clientWidth / canvasRef.value.clientHeight
  const frustumSize = 100
  camera.value = new THREE.OrthographicCamera(
    -frustumSize * aspect / 2,
    frustumSize * aspect / 2,
    frustumSize / 2,
    -frustumSize / 2,
    0.1,
    10000
  )
  camera.value.position.set(0, 100, 0)
  camera.value.lookAt(0, 0, 0)

  renderer.value = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    antialias: true,
  })
  renderer.value.setSize(canvasRef.value.clientWidth, canvasRef.value.clientHeight)
  renderer.value.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.value.shadowMap.enabled = true
  renderer.value.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.value.toneMapping = THREE.ACESFilmicToneMapping
  renderer.value.toneMappingExposure = 1.2

  controls.value = new OrbitControls(camera.value, renderer.value.domElement)
  controls.value.enableDamping = true
  controls.value.dampingFactor = 0.1
  controls.value.enableRotate = true
  controls.value.enablePan = true
  controls.value.panSpeed = 1.5
  controls.value.screenSpacePanning = true
  controls.value.minZoom = 0.1
  controls.value.maxZoom = 20
  controls.value.maxPolarAngle = Math.PI / 2.1

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.7)
  scene.value.add(ambientLight)

  const mainLight = new THREE.DirectionalLight(0xffffff, 1.2)
  mainLight.position.set(80, 120, 60)
  mainLight.castShadow = true
  mainLight.shadow.mapSize.width = 2048
  mainLight.shadow.mapSize.height = 2048
  mainLight.shadow.camera.near = 10
  mainLight.shadow.camera.far = 400
  mainLight.shadow.camera.left = -100
  mainLight.shadow.camera.right = 100
  mainLight.shadow.camera.top = 100
  mainLight.shadow.camera.bottom = -100
  scene.value.add(mainLight)

  const fillLight = new THREE.DirectionalLight(PREMIUM_COLORS.secondary, 0.3)
  fillLight.position.set(-50, 30, -50)
  scene.value.add(fillLight)

  const hemiLight = new THREE.HemisphereLight(0xffffff, PREMIUM_COLORS.ground, 0.6)
  scene.value.add(hemiLight)

  // Ground
  const groundGeometry = new THREE.PlaneGeometry(1000, 1000)
  const groundMaterial = new THREE.MeshStandardMaterial({
    color: PREMIUM_COLORS.ground,
    roughness: 0.9,
    metalness: 0.1,
  })
  const ground = new THREE.Mesh(groundGeometry, groundMaterial)
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -0.01
  ground.receiveShadow = true
  scene.value.add(ground)

  // Grid
  const gridHelper = new THREE.GridHelper(200, 100, PREMIUM_COLORS.gridCenter, PREMIUM_COLORS.gridLines)
  scene.value.add(gridHelper)

  isInitialized.value = true
  animate()
}

// Animation loop
function animate(): void {
  if (!renderer.value || !scene.value || !camera.value || !controls.value) return

  animationId = requestAnimationFrame(animate)
  controls.value.update()

  // Render vehicle labels
  if (vehicles3D) {
    vehicles3D.renderLabels(camera.value)
  }

  renderer.value.render(scene.value, camera.value)
}

// Load yard assets
async function loadYard(): Promise<void> {
  if (!scene.value) return
  isLoading.value = true

  // Load DXF infrastructure
  const dxfGroup = await loadFromUrl('/yard.dxf')
  if (dxfGroup) {
    scene.value.add(dxfGroup)
  }

  const scale = coordinateSystem.value?.scale ?? 1.0

  // Create containers
  if (containerPositions.value.length > 0 && coordinateSystem.value) {
    const dxfBounds = coordinateSystem.value.bounds
    const padding = 100
    containerPositions.value = containerPositions.value.filter(pos => {
      const origX = pos._original?.x ?? pos.x
      const origY = pos._original?.y ?? pos.y
      return origX >= dxfBounds.min.x - padding &&
             origX <= dxfBounds.max.x + padding &&
             origY >= dxfBounds.min.y - padding &&
             origY <= dxfBounds.max.y + padding
    })

    const containersGroup = createContainerMeshes({
      scale,
      center: coordinateSystem.value.center,
      colorMode: 'visual',
      coordinateSystem: coordinateSystem.value,
    })

    if (containersGroup) {
      scene.value.add(containersGroup)
      containerGroup.value = containersGroup // Store reference for camera fitting
    }
  }

  // Create buildings
  if (buildingPositions.value.length > 0 && coordinateSystem.value) {
    const buildingsGroup = createBuildingMeshes({
      scale,
      center: coordinateSystem.value.center,
      coordinateSystem: coordinateSystem.value,
    })
    if (buildingsGroup) {
      scene.value.add(buildingsGroup)
    }
  }

  // Initialize vehicles3D composable with coordinate system
  if (coordinateSystem.value && scene.value) {
    vehicles3D = useVehicles3D(scene.value, coordinateSystem)

    // Initialize label renderer
    if (containerRef.value) {
      vehicles3D.initLabelRenderer(containerRef.value)
    }
  }

  // Add gate markers for visual reference
  if (coordinateSystem.value) {
    addGateMarkers()
  }

  fitCameraToContent()
  isLoading.value = false
}

// Add visual markers at gate positions
function addGateMarkers(): void {
  if (!scene.value || !coordinateSystem.value) return

  Object.values(GATES).forEach(gate => {
    const worldPos = transformToWorld(gate.position, coordinateSystem.value!)

    // Gate marker sphere
    const markerGeom = new THREE.SphereGeometry(2)
    const markerMat = new THREE.MeshStandardMaterial({
      color: gate.direction === 'inbound' ? 0x52c41a : 0xf5222d,
      emissive: gate.direction === 'inbound' ? 0x52c41a : 0xf5222d,
      emissiveIntensity: 0.3,
    })
    const marker = new THREE.Mesh(markerGeom, markerMat)
    marker.position.set(worldPos.x, 3, worldPos.z)
    marker.name = `gate-marker-${gate.id}`
    scene.value!.add(marker)
  })
}

// Fit camera to content
function fitCameraToContent(): void {
  if (!camera.value || !controls.value || !canvasRef.value) return

  // Priority: Use container bounds if available (they're always reasonable)
  // DXF bounds can be massive due to title blocks, legends, reference points
  let box = new THREE.Box3()

  if (containerGroup.value) {
    const containerBox = new THREE.Box3().setFromObject(containerGroup.value)
    if (!containerBox.isEmpty()) {
      box = containerBox
    }
  }

  // Only use yard bounds if no containers, and clamp to reasonable size
  if (box.isEmpty() && yardGroup.value) {
    const yardBox = new THREE.Box3().setFromObject(yardGroup.value)
    const yardSize = yardBox.getSize(new THREE.Vector3())
    if (yardSize.x < 50000 && yardSize.z < 50000) {
      box = yardBox
    }
  }

  // Fallback to reasonable default
  if (box.isEmpty()) {
    box.set(
      new THREE.Vector3(-500, -10, -500),
      new THREE.Vector3(500, 10, 500)
    )
  }

  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  const aspect = canvasRef.value.clientWidth / canvasRef.value.clientHeight
  const maxDim = Math.max(size.x, size.z) * 1.5
  const frustumSize = Math.max(maxDim, 100)

  camera.value.left = -frustumSize * aspect / 2
  camera.value.right = frustumSize * aspect / 2
  camera.value.top = frustumSize / 2
  camera.value.bottom = -frustumSize / 2
  camera.value.zoom = 1
  camera.value.near = 0.1
  camera.value.far = frustumSize * 100
  camera.value.position.set(center.x, frustumSize, center.z)
  camera.value.lookAt(center.x, 0, center.z)
  camera.value.updateProjectionMatrix()

  controls.value.target.set(center.x, 0, center.z)
  controls.value.update()
}

// Handle vehicle detected from camera panel
async function onVehicleDetected(result: VehicleDetectionResult): Promise<void> {
  if (!vehicles3D || !coordinateSystem.value) return

  const vehicleId = generateVehicleId()

  // Add to log
  const logEntry: DetectionLogEntry = {
    id: vehicleId,
    plateNumber: result.plateNumber,
    vehicleType: result.vehicleType,
    timestamp: result.timestamp,
    status: 'detected',
  }
  detectionLog.value.unshift(logEntry)
  if (detectionLog.value.length > MAX_LOG_ENTRIES) {
    detectionLog.value.pop()
  }

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

  updateLogStatus(vehicleId, 'spawned')
  activeVehicleCount.value = vehicles3D.getAllVehicles().length

  // Pick a random parking zone
  const zoneIds = Object.keys(ZONES)
  const targetZone = zoneIds[Math.floor(Math.random() * zoneIds.length)]
  const pathId = `main_to_${targetZone}`
  const path = PATHS[pathId]

  if (path) {
    updateLogStatus(vehicleId, 'animating')

    // Animate vehicle along path
    await vehicles3D.animateVehicleAlongPath(vehicle, path)

    updateLogStatus(vehicleId, 'parked')
  }

  // Remove vehicle after timeout (for demo purposes)
  setTimeout(() => {
    if (vehicles3D) {
      vehicles3D.removeVehicle(vehicleId)
      activeVehicleCount.value = vehicles3D.getAllVehicles().length
    }
  }, 30000) // Remove after 30 seconds
}

function updateLogStatus(vehicleId: string, status: DetectionLogEntry['status']): void {
  const entry = detectionLog.value.find(e => e.id === vehicleId)
  if (entry) {
    entry.status = status
  }
}

function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString('ru-RU')
}

function getStatusColor(status: DetectionLogEntry['status']): string {
  switch (status) {
    case 'detected': return 'blue'
    case 'spawned': return 'cyan'
    case 'animating': return 'orange'
    case 'parked': return 'green'
    default: return 'default'
  }
}

function getStatusLabel(status: DetectionLogEntry['status']): string {
  switch (status) {
    case 'detected': return 'Обнаружен'
    case 'spawned': return 'Создан'
    case 'animating': return 'В движении'
    case 'parked': return 'Припаркован'
    default: return status
  }
}

// Handle resize
function handleResize(): void {
  if (!canvasRef.value || !camera.value || !renderer.value) return

  const width = canvasRef.value.clientWidth
  const height = canvasRef.value.clientHeight
  const aspect = width / height

  const frustumSize = (camera.value.right - camera.value.left) / camera.value.zoom
  camera.value.left = -frustumSize * aspect / 2
  camera.value.right = frustumSize * aspect / 2
  camera.value.updateProjectionMatrix()

  renderer.value.setSize(width, height)

  if (vehicles3D) {
    vehicles3D.updateLabelRendererSize(width, height)
  }
}

// Dispose
function dispose(): void {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }

  if (vehicles3D) {
    vehicles3D.dispose()
  }

  disposeYard()
  disposeContainers()
  disposeBuildings()
  controls.value?.dispose()
  renderer.value?.dispose()
  scene.value?.clear()

  isInitialized.value = false
}

// Lifecycle
onMounted(async () => {
  await nextTick()
  initScene()
  await loadYard()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  dispose()
})
</script>

<template>
  <div class="gate-camera-test-view">
    <!-- Left Panel: Camera -->
    <div class="camera-panel">
      <GateCameraPanel
        initial-source="mock"
        @vehicle-detected="onVehicleDetected"
      />
    </div>

    <!-- Right Panel: 3D View -->
    <div ref="containerRef" class="yard-panel">
      <canvas ref="canvasRef" class="yard-canvas" />

      <!-- Loading overlay -->
      <div v-if="isLoading" class="loading-overlay">
        <a-spin size="large" />
        <span class="loading-text">Загрузка 3D площадки...</span>
      </div>

      <!-- Stats bar -->
      <div class="stats-bar">
        <div class="stat-item">
          <span class="stat-label">Активных ТС:</span>
          <span class="stat-value">{{ activeVehicleCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Событий:</span>
          <span class="stat-value">{{ detectionLog.length }}</span>
        </div>
      </div>

      <!-- Detection log overlay -->
      <div v-if="detectionLog.length > 0" class="detection-log-overlay">
        <div class="log-header">Журнал событий</div>
        <div class="log-list">
          <div
            v-for="entry in detectionLog.slice(0, 5)"
            :key="entry.id"
            class="log-entry"
          >
            <span class="log-plate">{{ entry.plateNumber }}</span>
            <a-tag :color="getStatusColor(entry.status)" size="small">
              {{ getStatusLabel(entry.status) }}
            </a-tag>
            <span class="log-time">{{ formatTime(entry.timestamp) }}</span>
          </div>
        </div>
      </div>

      <!-- View controls -->
      <div class="view-controls">
        <a-tooltip title="Вписать в окно" placement="left">
          <a-button shape="circle" @click="fitCameraToContent">
            <template #icon><span style="font-size: 16px">🔄</span></template>
          </a-button>
        </a-tooltip>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gate-camera-test-view {
  display: flex;
  height: 100vh;
  background: #f0f2f5;
}

.camera-panel {
  width: 360px;
  flex-shrink: 0;
  border-right: 1px solid #e8e8e8;
  background: #fff;
  overflow-y: auto;
}

.yard-panel {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.yard-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 10;
}

.loading-text {
  margin-top: 16px;
  color: #666;
  font-size: 14px;
}

.stats-bar {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  gap: 16px;
  background: rgba(255, 255, 255, 0.95);
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 5;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-label {
  color: #888;
  font-size: 12px;
}

.stat-value {
  font-weight: 600;
  color: #333;
}

.detection-log-overlay {
  position: absolute;
  bottom: 16px;
  left: 16px;
  width: 300px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 5;
  overflow: hidden;
}

.log-header {
  padding: 12px 16px;
  font-weight: 500;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  color: #666;
}

.log-list {
  max-height: 200px;
  overflow-y: auto;
}

.log-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-bottom: 1px solid #fafafa;
  font-size: 12px;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-plate {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: #333;
}

.log-time {
  margin-left: auto;
  color: #999;
  font-size: 11px;
}

.view-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 5;
}
</style>
