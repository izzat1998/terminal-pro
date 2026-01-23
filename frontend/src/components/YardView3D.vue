<script setup lang="ts">
/**
 * YardView3D - Unified 3D Terminal Yard Visualization
 * Renders DXF infrastructure + interactive container boxes
 */

import { ref, shallowRef, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useDxfYard, type YardLayerInfo } from '@/composables/useDxfYard'
import { useContainers3D, type ContainerPosition, type ContainerData, type ColorMode } from '@/composables/useContainers3D'
import { useBuildings3D, type BuildingPosition } from '@/composables/useBuildings3D'
import { useFences3D, type FenceSegment } from '@/composables/useFences3D'
import { useRailway3D, type RailwayTrack } from '@/composables/useRailway3D'
import { usePlatforms3D, type PlatformData } from '@/composables/usePlatforms3D'
import { useRoads3D, type RoadSegment, type SidewalkData } from '@/composables/useRoads3D'
import containersJson from '@/data/containers.json'
import buildingsJson from '@/data/buildings.json'
import warehousesJson from '@/data/warehouses.json'
import fencesJson from '@/data/fences.json'
import railwayJson from '@/data/railway.json'
import storagePlatformsJson from '@/data/storagePlatforms.json'
import roadsJson from '@/data/roads.json'
import sidewalksJson from '@/data/sidewalks.json'

// Props
interface Props {
  /** DXF file URL or content */
  dxfUrl?: string
  dxfContent?: string
  /** Container data from backend */
  containerData?: ContainerData[]
  /** Height of the viewer */
  height?: string | number
  /** Show layer control panel */
  showLayerPanel?: boolean
  /** Show stats panel */
  showStats?: boolean
  /** Initial color mode */
  colorMode?: ColorMode
  /** Enable container interaction */
  interactive?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  height: '100%',
  showLayerPanel: true,
  showStats: true,
  colorMode: 'status',
  interactive: true,
})

const emit = defineEmits<{
  containerClick: [container: ContainerPosition & { data?: ContainerData }]
  containerHover: [container: ContainerPosition & { data?: ContainerData } | null]
  loaded: [stats: { entityCount: number; containerCount: number }]
  error: [message: string]
}>()

// Refs
const canvasRef = ref<HTMLCanvasElement>()
const containerRef = ref<HTMLDivElement>()

// Three.js core objects
const scene = shallowRef<THREE.Scene>()
const camera = shallowRef<THREE.OrthographicCamera>()
const renderer = shallowRef<THREE.WebGLRenderer>()
const controls = shallowRef<OrbitControls>()
const raycaster = new THREE.Raycaster()
const mouse = new THREE.Vector2()

// Animation
let animationId: number | null = null

// Camera state for view presets
const currentFrustumSize = ref(1000)

// Composables
const {
  isLoading: dxfLoading,
  error: dxfError,
  yardGroup,
  stats: dxfStats,
  layers,
  bounds,
  coordinateSystem,
  loadFromUrl,
  loadFromContent,
  setLayerVisibility,
  showAllLayers,
  hideAllLayers,
  dispose: disposeYard,
} = useDxfYard()

// Container positions from JSON
const containerPositions = ref<ContainerPosition[]>(containersJson as ContainerPosition[])
const containerDataRef = computed(() => props.containerData ?? [])

const {
  containerGroup,
  selectedIds,
  createContainerMeshes,
  setColorMode,
  selectContainer,
  clearSelection,
  setHovered,
  getContainerAtIntersection,
  dispose: disposeContainers,
} = useContainers3D(containerPositions, containerDataRef)

// Building positions from JSON
const buildingPositions = ref<BuildingPosition[]>(
  (buildingsJson as { buildings: BuildingPosition[] }).buildings
)

const {
  createBuildingMeshes,
  setHovered: setBuildingHovered,
  getBuildingAtIntersection,
  toggleLabels: toggleBuildingLabels,
  labelsVisible: buildingLabelsVisible,
  dispose: disposeBuildings,
} = useBuildings3D(buildingPositions)

// Warehouse positions (treated as buildings with different height/color)
const warehousePositions = ref<BuildingPosition[]>(
  (warehousesJson as { warehouses: BuildingPosition[] }).warehouses
)

const {
  createBuildingMeshes: createWarehouseMeshes,
  dispose: disposeWarehouses,
} = useBuildings3D(warehousePositions)

// Fence segments
const fenceSegments = ref<FenceSegment[]>(
  (fencesJson as { segments: FenceSegment[] }).segments
)

const {
  createFenceMeshes,
  toggleVisibility: toggleFences,
  isVisible: fencesVisible,
  dispose: disposeFences,
} = useFences3D(fenceSegments)

// Railway tracks
const railwayTracks = ref<RailwayTrack[]>(
  (railwayJson as { tracks: RailwayTrack[] }).tracks
)

const {
  createRailwayMeshes,
  toggleVisibility: toggleRailway,
  isVisible: railwayVisible,
  dispose: disposeRailway,
} = useRailway3D(railwayTracks)

// Storage platforms
const storagePlatforms = ref<PlatformData[]>(
  (storagePlatformsJson as { platforms: PlatformData[] }).platforms
)

const {
  createPlatformMeshes,
  toggleVisibility: togglePlatforms,
  isVisible: platformsVisible,
  dispose: disposePlatforms,
} = usePlatforms3D(storagePlatforms)

// Roads and sidewalks
const roadSegments = ref<RoadSegment[]>(
  (roadsJson as { segments: RoadSegment[] }).segments
)
const sidewalkData = ref<SidewalkData[]>(
  (sidewalksJson as { sidewalks: SidewalkData[] }).sidewalks
)

const {
  createRoadMeshes,
  toggleVisibility: toggleRoadsAndSidewalks,
  roadsVisible,
  dispose: disposeRoads,
} = useRoads3D(roadSegments, sidewalkData)

// State
const isInitialized = ref(false)
const showLayerPanelState = ref(props.showLayerPanel)
const currentColorMode = ref<ColorMode>(props.colorMode)

// Computed
const heightStyle = computed(() =>
  typeof props.height === 'number' ? `${props.height}px` : props.height
)

const totalContainers = computed(() => containerPositions.value.length)
const selectedCount = computed(() => selectedIds.value.size)

// Initialize scene
function initScene(): void {
  if (!canvasRef.value || isInitialized.value) return

  // Create scene
  scene.value = new THREE.Scene()
  scene.value.background = new THREE.Color(0xf0f2f5)

  // Create orthographic camera
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

  // Create renderer
  renderer.value = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    antialias: true,
  })
  renderer.value.setSize(canvasRef.value.clientWidth, canvasRef.value.clientHeight)
  renderer.value.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.value.shadowMap.enabled = true
  renderer.value.shadowMap.type = THREE.PCFSoftShadowMap

  // Create controls
  controls.value = new OrbitControls(camera.value, renderer.value.domElement)
  controls.value.enableDamping = true
  controls.value.dampingFactor = 0.1
  controls.value.enableRotate = true
  controls.value.enablePan = true
  controls.value.panSpeed = 1.5
  controls.value.screenSpacePanning = true
  controls.value.minZoom = 0.1
  controls.value.maxZoom = 20
  controls.value.maxPolarAngle = Math.PI / 2.1 // Prevent going underground

  // Add lights
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.value.add(ambientLight)

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight.position.set(50, 100, 50)
  directionalLight.castShadow = true
  directionalLight.shadow.mapSize.width = 2048
  directionalLight.shadow.mapSize.height = 2048
  directionalLight.shadow.camera.near = 0.5
  directionalLight.shadow.camera.far = 500
  scene.value.add(directionalLight)

  // Add ground plane
  const groundGeometry = new THREE.PlaneGeometry(1000, 1000)
  const groundMaterial = new THREE.MeshStandardMaterial({
    color: 0xe8e8e8,
    roughness: 0.8,
  })
  const ground = new THREE.Mesh(groundGeometry, groundMaterial)
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -0.01
  ground.receiveShadow = true
  ground.name = 'ground'
  scene.value.add(ground)

  // Add grid helper
  const gridHelper = new THREE.GridHelper(200, 100, 0xcccccc, 0xdddddd)
  gridHelper.name = 'grid'
  scene.value.add(gridHelper)

  isInitialized.value = true
  animate()
}

// Animation loop
function animate(): void {
  if (!renderer.value || !scene.value || !camera.value || !controls.value) return

  animationId = requestAnimationFrame(animate)
  controls.value.update()
  renderer.value.render(scene.value, camera.value)
}

// Load DXF and containers
async function loadYard(): Promise<void> {
  if (!scene.value) return

  // Load DXF infrastructure
  let dxfGroup: THREE.Group | null = null
  if (props.dxfContent) {
    dxfGroup = loadFromContent(props.dxfContent)
  } else if (props.dxfUrl) {
    dxfGroup = await loadFromUrl(props.dxfUrl)
  }

  // Get scale from DXF coordinate system (auto-detected from INSUNITS)
  const scale = coordinateSystem.value?.scale ?? 1.0

  if (dxfGroup && scene.value) {
    scene.value.add(dxfGroup)
  }

  // Create container meshes aligned with DXF infrastructure
  if (containerPositions.value.length > 0 && coordinateSystem.value) {
    // Filter containers to only those within DXF bounds (excludes legends, title blocks)
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
      colorMode: currentColorMode.value,
      coordinateSystem: coordinateSystem.value,
    })

    if (containersGroup && scene.value) {
      scene.value.add(containersGroup)
    }
  } else if (containerPositions.value.length > 0) {
    // Fallback: no DXF loaded, place containers at origin
    const containersGroup = createContainerMeshes({
      scale,
      center: { x: 0, y: 0 },
      colorMode: currentColorMode.value,
    })
    if (containersGroup && scene.value) {
      scene.value.add(containersGroup)
    }
  }

  // Create building meshes
  if (buildingPositions.value.length > 0 && coordinateSystem.value) {
    const buildingsGroup = createBuildingMeshes({
      scale,
      center: coordinateSystem.value.center,
      coordinateSystem: coordinateSystem.value,
    })
    if (buildingsGroup && scene.value) {
      scene.value.add(buildingsGroup)
    }
  }

  // Create warehouse meshes (lower height, different color)
  if (warehousePositions.value.length > 0 && coordinateSystem.value) {
    const warehousesGroup = createWarehouseMeshes({
      scale,
      center: coordinateSystem.value.center,
      coordinateSystem: coordinateSystem.value,
      defaultHeight: 5,  // Lower than buildings
    })
    if (warehousesGroup && scene.value) {
      // Apply different color to warehouse materials
      warehousesGroup.traverse((child) => {
        if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
          child.material.color.setHex(0xd4a574)  // Tan/warehouse color
        }
      })
      scene.value.add(warehousesGroup)
    }
  }

  // Create fence meshes
  if (fenceSegments.value.length > 0 && coordinateSystem.value) {
    const fencesGroup = createFenceMeshes({
      scale,
      center: coordinateSystem.value.center,
      coordinateSystem: coordinateSystem.value,
    })
    if (fencesGroup && scene.value) {
      scene.value.add(fencesGroup)
    }
  }

  // Create railway track meshes
  if (railwayTracks.value.length > 0 && coordinateSystem.value) {
    const railwayGroup = createRailwayMeshes({
      scale,
      center: coordinateSystem.value.center,
      coordinateSystem: coordinateSystem.value,
    })
    if (railwayGroup && scene.value) {
      scene.value.add(railwayGroup)
    }
  }

  // Create storage platform meshes
  if (storagePlatforms.value.length > 0 && coordinateSystem.value) {
    const platformsGroup = createPlatformMeshes({
      scale,
      center: coordinateSystem.value.center,
      coordinateSystem: coordinateSystem.value,
    })
    if (platformsGroup && scene.value) {
      scene.value.add(platformsGroup)
    }
  }

  // Create road and sidewalk meshes
  if ((roadSegments.value.length > 0 || sidewalkData.value.length > 0) && coordinateSystem.value) {
    const roadsGroup = createRoadMeshes({
      scale,
      center: coordinateSystem.value.center,
      coordinateSystem: coordinateSystem.value,
    })
    if (roadsGroup && scene.value) {
      scene.value.add(roadsGroup)
    }
  }

  // Fit camera to content
  fitCameraToContent()

  // Emit loaded event
  emit('loaded', {
    entityCount: dxfStats.value?.entityCount.total ?? 0,
    containerCount: containerPositions.value.length,
  })
}

// Fit camera to show all content
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
    } else {
      // Use a default reasonable box centered at origin
      box.set(
        new THREE.Vector3(-500, -10, -500),
        new THREE.Vector3(500, 10, 500)
      )
    }
  }

  if (box.isEmpty()) return

  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  const aspect = canvasRef.value.clientWidth / canvasRef.value.clientHeight
  const maxDim = Math.max(size.x, size.z) * 1.5
  const frustumSize = Math.max(maxDim, 100)

  currentFrustumSize.value = frustumSize

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

// Camera view presets
function setTopView(): void {
  if (!camera.value || !controls.value) return
  const target = controls.value.target.clone()
  // Use frustum size for camera height to ensure proper view distance
  const height = currentFrustumSize.value
  camera.value.position.set(target.x, height, target.z)
  camera.value.lookAt(target)
  camera.value.updateProjectionMatrix()
  controls.value.update()
}

function setIsometricView(): void {
  if (!camera.value || !controls.value) return
  const target = controls.value.target.clone()
  // Use frustum size for proper isometric distance
  const distance = currentFrustumSize.value * 0.5
  camera.value.position.set(target.x + distance, distance * 0.8, target.z + distance)
  camera.value.lookAt(target)
  camera.value.updateProjectionMatrix()
  controls.value.update()
}

// Handle mouse events for container/building interaction
function onMouseMove(event: MouseEvent): void {
  if (!props.interactive || !canvasRef.value || !camera.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(mouse, camera.value)

  const intersects = raycaster.intersectObjects(scene.value?.children ?? [], true)

  let hoveredContainer = null
  let hoveredBuilding = null

  for (const intersect of intersects) {
    // Check containers first (priority)
    const container = getContainerAtIntersection(intersect)
    if (container) {
      hoveredContainer = container
      break
    }
    // Then check buildings
    const building = getBuildingAtIntersection(intersect)
    if (building) {
      hoveredBuilding = building
      break
    }
  }

  setHovered(hoveredContainer?.id ?? null)
  setBuildingHovered(hoveredBuilding?.id ?? null)

  if (hoveredContainer) {
    canvasRef.value.style.cursor = 'pointer'
    emit('containerHover', hoveredContainer)
  } else if (hoveredBuilding) {
    canvasRef.value.style.cursor = 'pointer'
    emit('containerHover', null)  // Clear container hover
  } else {
    canvasRef.value.style.cursor = 'default'
    emit('containerHover', null)
  }
}

function onClick(event: MouseEvent): void {
  if (!props.interactive || !canvasRef.value || !camera.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(mouse, camera.value)

  const intersects = raycaster.intersectObjects(scene.value?.children ?? [], true)

  for (const intersect of intersects) {
    const container = getContainerAtIntersection(intersect)
    if (container) {
      const additive = event.ctrlKey || event.metaKey
      selectContainer(container.id, additive)
      emit('containerClick', container)
      return
    }
  }

  // Click on empty space clears selection
  clearSelection()
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
}

// Layer visibility toggle
function toggleLayer(layer: YardLayerInfo): void {
  setLayerVisibility(layer.name, !layer.visible)
}

// Color mode change
function onColorModeChange(mode: ColorMode): void {
  currentColorMode.value = mode
  setColorMode(mode)
}

// Dispose
function dispose(): void {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }

  disposeYard()
  disposeContainers()
  disposeBuildings()
  disposeWarehouses()
  disposeFences()
  disposeRailway()
  disposePlatforms()
  disposeRoads()
  controls.value?.dispose()
  renderer.value?.dispose()
  scene.value?.clear()

  isInitialized.value = false
}

// Lifecycle
onMounted(async () => {
  await nextTick()
  initScene()

  try {
    await loadYard()
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Failed to load yard'
    emit('error', message)
  }

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  dispose()
})

// Watch for prop changes
watch(() => props.colorMode, (mode) => {
  onColorModeChange(mode)
})

watch(() => props.dxfUrl, async () => {
  if (isInitialized.value) {
    await loadYard()
  }
})
</script>

<template>
  <div ref="containerRef" class="yard-view-3d" :style="{ height: heightStyle }">
    <!-- Canvas -->
    <canvas
      ref="canvasRef"
      class="yard-canvas"
      @mousemove="onMouseMove"
      @click="onClick"
    />

    <!-- Loading overlay -->
    <div v-if="dxfLoading" class="yard-overlay">
      <a-spin size="large" />
      <span class="loading-text">Загрузка терминала...</span>
    </div>

    <!-- Error overlay -->
    <div v-if="dxfError" class="yard-overlay error">
      <a-result status="error" :title="dxfError" />
    </div>

    <!-- Camera controls -->
    <div class="yard-controls">
      <a-space direction="vertical" size="small">
        <a-tooltip title="Вид сверху" placement="left">
          <a-button shape="circle" @click="setTopView">
            <template #icon><span>⬆</span></template>
          </a-button>
        </a-tooltip>
        <a-tooltip title="Изометрия" placement="left">
          <a-button shape="circle" @click="setIsometricView">
            <template #icon><span>◇</span></template>
          </a-button>
        </a-tooltip>
        <a-tooltip title="Вписать в окно" placement="left">
          <a-button shape="circle" @click="fitCameraToContent">
            <template #icon><span>⊞</span></template>
          </a-button>
        </a-tooltip>
        <a-tooltip :title="buildingLabelsVisible ? 'Скрыть названия зданий' : 'Показать названия зданий'" placement="left">
          <a-button
            shape="circle"
            :type="buildingLabelsVisible ? 'primary' : 'default'"
            @click="toggleBuildingLabels()"
          >
            <template #icon><span>🏷</span></template>
          </a-button>
        </a-tooltip>
        <a-tooltip :title="fencesVisible ? 'Скрыть ограждения' : 'Показать ограждения'" placement="left">
          <a-button
            shape="circle"
            :type="fencesVisible ? 'primary' : 'default'"
            @click="toggleFences()"
          >
            <template #icon><span>🚧</span></template>
          </a-button>
        </a-tooltip>
        <a-tooltip :title="railwayVisible ? 'Скрыть ж/д пути' : 'Показать ж/д пути'" placement="left">
          <a-button
            shape="circle"
            :type="railwayVisible ? 'primary' : 'default'"
            @click="toggleRailway()"
          >
            <template #icon><span>🚂</span></template>
          </a-button>
        </a-tooltip>
        <a-tooltip :title="platformsVisible ? 'Скрыть площадки' : 'Показать площадки'" placement="left">
          <a-button
            shape="circle"
            :type="platformsVisible ? 'primary' : 'default'"
            @click="togglePlatforms()"
          >
            <template #icon><span>📦</span></template>
          </a-button>
        </a-tooltip>
        <a-tooltip :title="roadsVisible ? 'Скрыть дороги' : 'Показать дороги'" placement="left">
          <a-button
            shape="circle"
            :type="roadsVisible ? 'primary' : 'default'"
            @click="toggleRoadsAndSidewalks()"
          >
            <template #icon><span>🛣️</span></template>
          </a-button>
        </a-tooltip>
      </a-space>
    </div>

    <!-- Color mode selector -->
    <div class="color-mode-selector">
      <a-segmented
        :value="currentColorMode"
        :options="[
          { value: 'status', label: 'Статус' },
          { value: 'dwell', label: 'Срок' },
        ]"
        @change="(val: ColorMode) => onColorModeChange(val)"
      />
    </div>

    <!-- Stats panel -->
    <div v-if="showStats && dxfStats" class="yard-stats">
      <div class="stat">
        <span class="label">Объектов:</span>
        <span class="value">{{ dxfStats.entityCount.total.toLocaleString() }}</span>
      </div>
      <div class="stat">
        <span class="label">Контейнеров:</span>
        <span class="value">{{ totalContainers }}</span>
      </div>
      <div v-if="selectedCount > 0" class="stat selected">
        <span class="label">Выбрано:</span>
        <span class="value">{{ selectedCount }}</span>
      </div>
      <div v-if="bounds" class="stat">
        <span class="label">Размер:</span>
        <span class="value">{{ bounds.width.toFixed(0) }}×{{ bounds.height.toFixed(0) }} м</span>
      </div>
    </div>

    <!-- Layer panel -->
    <div v-if="showLayerPanelState && layers.length > 0" class="layer-panel">
      <div class="layer-panel-header">
        <span>Слои</span>
        <a-space size="small">
          <a-button size="small" @click="showAllLayers">Все</a-button>
          <a-button size="small" @click="hideAllLayers">Нет</a-button>
        </a-space>
      </div>
      <div class="layer-list">
        <div
          v-for="layer in layers"
          :key="layer.name"
          class="layer-item"
          @click="toggleLayer(layer)"
        >
          <a-checkbox :checked="layer.visible" />
          <span class="layer-name">{{ layer.name }}</span>
          <span class="layer-count">{{ layer.objectCount }}</span>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="color-legend">
      <div v-if="currentColorMode === 'status'" class="legend-items">
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#1890ff' }" />
          <span>Груженые</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#fa8c16' }" />
          <span>Пустые</span>
        </div>
      </div>
      <div v-if="currentColorMode === 'dwell'" class="legend-items">
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#52c41a' }" />
          <span>0-7 дней</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#faad14' }" />
          <span>7-14 дней</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#f5222d' }" />
          <span>14+ дней</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.yard-view-3d {
  position: relative;
  width: 100%;
  background: #f0f2f5;
  border-radius: 8px;
  overflow: hidden;
}

.yard-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.yard-overlay {
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

.yard-overlay.error {
  background: rgba(255, 240, 240, 0.95);
}

.loading-text {
  margin-top: 16px;
  color: #666;
  font-size: 14px;
}

.yard-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 5;
}

.color-mode-selector {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
}

.yard-stats {
  position: absolute;
  bottom: 16px;
  left: 16px;
  background: rgba(255, 255, 255, 0.95);
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 12px;
  z-index: 5;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.yard-stats .stat {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
}

.yard-stats .stat:last-child {
  margin-bottom: 0;
}

.yard-stats .stat.selected {
  color: #52c41a;
  font-weight: 500;
}

.yard-stats .label {
  color: #888;
}

.yard-stats .value {
  color: #333;
  font-weight: 500;
}

.layer-panel {
  position: absolute;
  top: 16px;
  left: 16px;
  width: 220px;
  max-height: 400px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 5;
  overflow: hidden;
}

.layer-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  font-weight: 500;
}

.layer-list {
  max-height: 300px;
  overflow-y: auto;
  padding: 8px 0;
}

.layer-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.layer-item:hover {
  background: #f5f5f5;
}

.layer-name {
  flex: 1;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.layer-count {
  font-size: 11px;
  color: #999;
}

.color-legend {
  position: absolute;
  bottom: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.95);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  z-index: 5;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.legend-items {
  display: flex;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
</style>
