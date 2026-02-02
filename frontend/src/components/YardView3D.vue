<script setup lang="ts">
/**
 * YardView3D - Unified 3D Terminal Yard Visualization
 * Renders DXF infrastructure + interactive container boxes
 */

import { ref, shallowRef, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useDxfYard, type YardLayerInfo } from '@/composables/useDxfYard'
import { disposeObject3D } from '@/utils/threeUtils'
import { clearGeometryCaches } from '@/utils/geometryUtils'
import { disposeSharedMaterials } from '@/composables/useMaterials3D'
import { useContainers3D, type ContainerPosition, type ContainerData } from '@/composables/useContainers3D'
import { useContainerLabels3D } from '@/composables/useContainerLabels3D'
import { useYardSettings, type ColorMode } from '@/composables/useYardSettings'
import YardSettingsDrawer from '@/components/yard/YardSettingsDrawer.vue'
import ContainerTooltip from '@/components/yard/ContainerTooltip.vue'
import { useBuildings3D, type BuildingPosition } from '@/composables/useBuildings3D'
import { useFences3D, type FenceSegment } from '@/composables/useFences3D'
import { useRailway3D, type RailwayTrack } from '@/composables/useRailway3D'
import { usePlatforms3D, type PlatformData } from '@/composables/usePlatforms3D'
import { useRoads3D, type RoadSegment, type SidewalkData } from '@/composables/useRoads3D'
import { useVehicleModels, disposeLicensePlatePool } from '@/composables/useVehicleModels'
import { useMaterials3D } from '@/composables/useMaterials3D'
import { useVehicles3D, type ActiveVehicle } from '@/composables/useVehicles3D'
import { useExitDetection, type ExitDetectionResult } from '@/composables/useExitDetection'
import { detectOptimalQuality, getQualityPreset, type QualityLevel } from '@/utils/qualityPresets'
import { GATES, transformToWorld } from '@/data/scenePositions'
import buildingsJson from '@/data/buildings.json'
import warehousesJson from '@/data/warehouses.json'
import fencesJson from '@/data/fences.json'
import railwayJson from '@/data/railway.json'
import storagePlatformsJson from '@/data/storagePlatforms.json'
import roadsJson from '@/data/roads.json'
import sidewalksJson from '@/data/sidewalks.json'

// Premium color palette (from Hero3DView)
const PREMIUM_COLORS = {
  primary: 0x0077B6,     // Deep Blue
  secondary: 0x00B4D8,   // Light Cyan
  accent: 0x023E8A,      // Navy
  light: 0xCAF0F8,       // Light Sky
  ground: 0xE8F4F8,      // Pale Blue
  background: 0xF0F7FA,  // Scene background
  white: 0xFFFFFF,
  gridCenter: 0xCCE5ED,
  gridLines: 0xDDEEF4,
}

// Props
interface Props {
  /** DXF file URL or content */
  dxfUrl?: string
  dxfContent?: string
  /** Container data from backend */
  containerData?: ContainerData[]
  /** Container positions (overrides built-in JSON when provided) */
  containerPositions?: ContainerPosition[]
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
  /** Show test vehicles at gates (for demo, disable when using live detection) */
  showTestVehicles?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  height: '100%',
  showLayerPanel: true,
  showStats: true,
  colorMode: 'visual',  // Default to visual mode for colorful display
  interactive: true,
  showTestVehicles: true,  // Set to false when using live gate detection
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
let raycastPending = false  // RAF gate for mousemove raycasting

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

// Container positions: use prop if provided, otherwise empty (parent must supply data)
const containerPositions = ref<ContainerPosition[]>(
  props.containerPositions && props.containerPositions.length > 0
    ? props.containerPositions
    : []
)
const containerDataRef = computed(() => props.containerData ?? [])

// Watch for prop-driven position updates (e.g., from API)
// When positions arrive after initial mount, rebuild container meshes
watch(() => props.containerPositions, (newPositions) => {
  if (newPositions && newPositions.length > 0) {
    containerPositions.value = newPositions
    // Rebuild meshes if scene is already initialized but containers weren't rendered yet
    if (isInitialized.value && coordinateSystem.value && !containerGroup.value) {
      rebuildContainerMeshes()
    }
  }
})

const {
  containerGroup,
  containers,
  selectedIds,
  createContainerMeshes,
  setColorMode,
  selectContainer,
  clearSelection,
  setHovered,
  getContainerAtIntersection,
  findContainersByNumber,
  highlightContainer,
  stopHighlight,
  dispose: disposeContainers,
} = useContainers3D(containerPositions, containerDataRef)

// Container labels composable
const {
  labelsGroup: containerLabelsGroup,
  createLabels: createContainerLabels,
  updateVisibility: updateContainerLabelVisibility,
  setVisibility: setContainerLabelsVisibility,
  dispose: disposeContainerLabels,
} = useContainerLabels3D(containers, containerPositions, containerDataRef)

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

// Vehicle models composable
const {
  createTruckModel,
  createCarModel,
  createWagonModel,
} = useVehicleModels()

// Materials composable
const {
  dispose: disposeMaterials,
} = useMaterials3D()

// Quality level (auto-detected or user-selected)
const qualityLevel = ref<QualityLevel>('medium')

// ============ Gate Camera & Vehicle Detection ============
// Vehicle management composable (initialized after scene is ready)
const vehicles3DRef = shallowRef<ReturnType<typeof useVehicles3D> | null>(null)

// Exit detection composable (initialized after vehicles3D is ready)
const exitDetectionRef = shallowRef<ReturnType<typeof useExitDetection> | null>(null)

/**
 * Initialize vehicle management and exit detection composables
 * Called after scene and coordinate system are ready
 */
function initVehicleManagement(): void {
  if (!scene.value || !coordinateSystem.value) return

  // Initialize vehicles3D composable
  vehicles3DRef.value = useVehicles3D(scene.value, coordinateSystem)

  // Initialize exit detection with vehicle registry
  exitDetectionRef.value = useExitDetection({
    vehicleRegistry: vehicles3DRef.value.vehicles,
    onVehicleMatched: handleExitVehicleMatched,
    onUnknownVehicle: handleUnknownVehicleExit,
  })

  if (import.meta.env.DEV) {
    console.log('[YardView3D] Vehicle management initialized')
  }
}

/**
 * Callback when exit detection matches a vehicle in registry
 */
async function handleExitVehicleMatched(vehicle: ActiveVehicle, result: ExitDetectionResult): Promise<void> {
  if (!vehicles3DRef.value) return

  if (import.meta.env.DEV) {
    console.log(`[YardView3D] Exit matched: ${vehicle.plateNumber} from zone ${vehicle.targetZone}`)
  }

  // Animate vehicle exit sequence
  await vehicles3DRef.value.animateVehicleExit(vehicle, () => {
    // Notify backend after animation completes
    exitDetectionRef.value?.notifyBackendExit(
      vehicle.id,
      vehicle.plateNumber,
      result.confidence
    )
  })
}

/**
 * Callback when exit detection finds unknown vehicle
 */
function handleUnknownVehicleExit(plateNumber: string, result: ExitDetectionResult): void {
  if (import.meta.env.DEV) {
    console.log(`[YardView3D] Unknown exit: ${plateNumber} (not tracked)`)
  }

  // Silent logging - notify backend for audit trail
  exitDetectionRef.value?.notifyBackendExit(null, plateNumber, result.confidence)
}

// Test vehicles group (for demonstration)
const testVehiclesGroup = shallowRef<THREE.Group | null>(null)

// State
const isInitialized = ref(false)
const isSettingsOpen = ref(false)

// Tooltip state
const tooltipX = ref(0)
const tooltipY = ref(0)
const hoveredContainerData = ref<ContainerData | null>(null)
let tooltipDebounceTimer: ReturnType<typeof setTimeout> | null = null

// ============ Container Search ============
const searchQuery = ref('')
const searchOpen = ref(false)
const searchInputRef = ref<HTMLInputElement>()
let flyAnimationId: number | null = null

const searchResults = computed(() => {
  if (!searchQuery.value || searchQuery.value.length < 2) return []
  return findContainersByNumber(searchQuery.value).slice(0, 8)
})

const selectedSearchIndex = ref(0)

function openSearch(): void {
  searchOpen.value = true
  nextTick(() => searchInputRef.value?.focus())
}

function closeSearch(): void {
  searchOpen.value = false
  searchQuery.value = ''
  selectedSearchIndex.value = 0
  stopHighlight()
}

function handleSearchKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') {
    closeSearch()
    return
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedSearchIndex.value = Math.min(selectedSearchIndex.value + 1, searchResults.value.length - 1)
    return
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedSearchIndex.value = Math.max(selectedSearchIndex.value - 1, 0)
    return
  }
  if (e.key === 'Enter' && searchResults.value.length > 0) {
    e.preventDefault()
    const result = searchResults.value[selectedSearchIndex.value]
    if (result) flyToSearchResult(result)
    return
  }
}

function flyToSearchResult(result: { container: { id: number; data?: { container_number: string; status: string; container_type: string; dwell_days?: number } }; position: THREE.Vector3; index: number }): void {
  // Highlight container (shows pulsing green — integrated into updateColors)
  highlightContainer(result.index)

  // Fly camera to position
  flyToPosition(result.position, 6)

  // Show selected container number in search input
  searchQuery.value = result.container.data?.container_number ?? ''
}

/**
 * Smoothly animate camera to a world position with easeOutCubic easing.
 * For orthographic camera: pans target and adjusts zoom, keeping top-down orientation stable.
 */
function flyToPosition(targetPos: THREE.Vector3, zoomLevel: number = 5, duration: number = 800): void {
  if (!camera.value || !controls.value) return

  // Cancel previous fly animation
  if (flyAnimationId !== null) {
    cancelAnimationFrame(flyAnimationId)
    flyAnimationId = null
  }

  // Snapshot start state (clone everything upfront)
  const startTarget = controls.value.target.clone()
  const startCamPos = camera.value.position.clone()
  const startZoom = camera.value.zoom

  // End state: camera directly above the target position
  const endTarget = new THREE.Vector3(targetPos.x, 0, targetPos.z)
  const endCamPos = new THREE.Vector3(targetPos.x, startCamPos.y, targetPos.z)

  const startTime = performance.now()

  function easeOutCubic(t: number): number {
    return 1 - Math.pow(1 - t, 3)
  }

  function animateFly(): void {
    const elapsed = performance.now() - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = easeOutCubic(progress)

    if (!camera.value || !controls.value) return

    // Interpolate all values from frozen start to frozen end
    controls.value.target.lerpVectors(startTarget, endTarget, eased)
    camera.value.position.lerpVectors(startCamPos, endCamPos, eased)
    camera.value.zoom = startZoom + (zoomLevel - startZoom) * eased
    camera.value.updateProjectionMatrix()
    controls.value.update()

    if (progress < 1) {
      flyAnimationId = requestAnimationFrame(animateFly)
    } else {
      flyAnimationId = null
    }
  }

  animateFly()
}

// Global keyboard shortcut for search
function handleGlobalKeydown(e: KeyboardEvent): void {
  // Ctrl+F or Cmd+F to open search
  if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
    // Only intercept if we're focused on the yard view
    if (containerRef.value?.contains(document.activeElement) || document.activeElement === document.body) {
      e.preventDefault()
      openSearch()
    }
  }
  // "/" to open search (like GitHub)
  if (e.key === '/' && !searchOpen.value) {
    const target = e.target as HTMLElement
    if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
      e.preventDefault()
      openSearch()
    }
  }
}

// Yard settings (centralized)
const {
  layers: settingsLayers,
  labels: settingsLabels,
  display: settingsDisplay,
} = useYardSettings()

// Color mode from settings (reactive)
const currentColorMode = computed(() => settingsDisplay.value.colorMode)

// Computed
const heightStyle = computed(() =>
  typeof props.height === 'number' ? `${props.height}px` : props.height
)

const totalContainers = computed(() => containerPositions.value.length)
const selectedCount = computed(() => selectedIds.value.size)

// Initialize scene
function initScene(): void {
  if (!canvasRef.value || isInitialized.value) return

  // Auto-detect optimal quality level
  qualityLevel.value = detectOptimalQuality()
  const qualityPreset = getQualityPreset(qualityLevel.value)

  // Create scene with premium background
  scene.value = new THREE.Scene()
  scene.value.background = new THREE.Color(PREMIUM_COLORS.background)

  // Fog disabled - creates too much haze on large yards
  scene.value.fog = null

  // Create orthographic camera (guard against zero height)
  const canvasHeight = canvasRef.value.clientHeight || 1
  const aspect = canvasRef.value.clientWidth / canvasHeight
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

  // Create renderer with quality-based settings
  renderer.value = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    antialias: qualityPreset.antialias,
  })
  renderer.value.setSize(canvasRef.value.clientWidth, canvasRef.value.clientHeight)
  renderer.value.setPixelRatio(qualityPreset.pixelRatio)
  renderer.value.shadowMap.enabled = qualityPreset.shadows
  renderer.value.shadowMap.type = THREE.PCFSoftShadowMap
  if (qualityPreset.toneMapping) {
    renderer.value.toneMapping = THREE.ACESFilmicToneMapping
    renderer.value.toneMappingExposure = qualityPreset.toneMappingExposure
  }

  // Set correct color space for accurate color reproduction
  renderer.value.outputColorSpace = THREE.SRGBColorSpace

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


  // Professional 4-light setup for premium visuals
  // 1. Ambient light (base illumination)
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.7)
  scene.value.add(ambientLight)

  // 2. Main directional light (key light with shadows)
  const mainLight = new THREE.DirectionalLight(0xffffff, 1.2)
  mainLight.position.set(80, 120, 60)
  mainLight.castShadow = qualityPreset.shadows
  mainLight.shadow.mapSize.width = qualityPreset.shadowMapSize
  mainLight.shadow.mapSize.height = qualityPreset.shadowMapSize
  mainLight.shadow.camera.near = 10
  mainLight.shadow.camera.far = 400
  mainLight.shadow.camera.left = -100
  mainLight.shadow.camera.right = 100
  mainLight.shadow.camera.top = 100
  mainLight.shadow.camera.bottom = -100
  mainLight.shadow.bias = -0.0001
  scene.value.add(mainLight)

  // 3. Fill light (cyan accent from opposite side)
  const fillLight = new THREE.DirectionalLight(PREMIUM_COLORS.secondary, 0.3)
  fillLight.position.set(-50, 30, -50)
  scene.value.add(fillLight)

  // 4. Hemisphere light (natural sky/ground reflection)
  const hemiLight = new THREE.HemisphereLight(0xffffff, PREMIUM_COLORS.ground, 0.6)
  scene.value.add(hemiLight)

  // Add ground plane with premium pale blue color
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
  ground.name = 'ground'
  scene.value.add(ground)

  // Add grid helper with blue-tinted lines
  const gridHelper = new THREE.GridHelper(200, 100, PREMIUM_COLORS.gridCenter, PREMIUM_COLORS.gridLines)
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

  // Update container label visibility based on camera position
  if (settingsLabels.value.containers && containerLabelsGroup.value) {
    updateContainerLabelVisibility(camera.value)
  }

  // Direct render (no post-processing for maximum sharpness)
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

    // Get current quality preset for edge line settings
    const qualityPreset = getQualityPreset(qualityLevel.value)

    const containersGroup = createContainerMeshes({
      scale,
      center: coordinateSystem.value.center,
      colorMode: currentColorMode.value,
      coordinateSystem: coordinateSystem.value,
      showEdgeLines: qualityPreset.containerEdges,
      edgeLineOpacity: qualityPreset.containerEdgeOpacity,
    })

    if (containersGroup && scene.value) {
      scene.value.add(containersGroup)
    }

    // Create container labels (if enabled in settings)
    if (settingsLabels.value.containers) {
      const labelsGroup = createContainerLabels({
        scale,
        coordinateSystem: coordinateSystem.value,
        visible: true,
      })
      if (labelsGroup && scene.value) {
        scene.value.add(labelsGroup)
      }
    }
  } else if (containerPositions.value.length > 0) {
    // Fallback: no DXF loaded, place containers at origin
    const qualityPresetFallback = getQualityPreset(qualityLevel.value)
    const containersGroup = createContainerMeshes({
      scale,
      center: { x: 0, y: 0 },
      colorMode: currentColorMode.value,
      showEdgeLines: qualityPresetFallback.containerEdges,
      edgeLineOpacity: qualityPresetFallback.containerEdgeOpacity,
    })
    if (containersGroup && scene.value) {
      scene.value.add(containersGroup)
    }

    // Create container labels (fallback)
    if (settingsLabels.value.containers) {
      const labelsGroup = createContainerLabels({
        scale,
        center: { x: 0, y: 0 },
        visible: true,
      })
      if (labelsGroup && scene.value) {
        scene.value.add(labelsGroup)
      }
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

  // Create test vehicles at gate positions (optional, for demo purposes)
  if (coordinateSystem.value && props.showTestVehicles) {
    createTestVehicles()
  }

  // Initialize vehicle management for gate camera detection
  if (coordinateSystem.value) {
    initVehicleManagement()
  }

  // Fit camera to content
  fitCameraToContent()

  // Emit loaded event
  emit('loaded', {
    entityCount: dxfStats.value?.entityCount.total ?? 0,
    containerCount: containerPositions.value.length,
  })
}

/**
 * Rebuild container meshes when positions arrive after initial load.
 * Called by the containerPositions watcher when API data lands.
 */
function rebuildContainerMeshes(): void {
  if (!scene.value || !coordinateSystem.value) return

  const scale = coordinateSystem.value.scale ?? 1.0

  // Filter to DXF bounds
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

  const qualityPreset = getQualityPreset(qualityLevel.value)

  const containersGroup = createContainerMeshes({
    scale,
    center: coordinateSystem.value.center,
    colorMode: currentColorMode.value,
    coordinateSystem: coordinateSystem.value,
    showEdgeLines: qualityPreset.containerEdges,
    edgeLineOpacity: qualityPreset.containerEdgeOpacity,
  })

  if (containersGroup && scene.value) {
    scene.value.add(containersGroup)
  }

  if (settingsLabels.value.containers) {
    const labelsGroup = createContainerLabels({
      scale,
      coordinateSystem: coordinateSystem.value,
      visible: true,
    })
    if (labelsGroup && scene.value) {
      scene.value.add(labelsGroup)
    }
  }

  fitCameraToContent()
}

/**
 * Create test vehicles at gate positions for visual verification
 * Demonstrates truck, car, and wagon models
 */
function createTestVehicles(): void {
  if (!scene.value || !coordinateSystem.value) return

  // Clean up existing test vehicles
  if (testVehiclesGroup.value) {
    scene.value.remove(testVehiclesGroup.value)
    disposeObject3D(testVehiclesGroup.value)
  }

  testVehiclesGroup.value = new THREE.Group()
  testVehiclesGroup.value.name = 'test-vehicles'

  // Get main gate position
  const mainGate = GATES['main']
  if (mainGate) {
    const worldPos = transformToWorld(mainGate.position, coordinateSystem.value)
    const rotationRad = -mainGate.rotation * (Math.PI / 180)

    // Create truck with 40ft chassis at main gate
    const truck = createTruckModel({ withChassis: true, chassisSize: '40ft' })
    truck.position.set(worldPos.x, 0, worldPos.z)
    truck.rotation.y = rotationRad
    truck.name = 'test-truck-main-gate'
    testVehiclesGroup.value.add(truck)

    // Create a car slightly behind the truck (in waiting area direction)
    const carOffsetX = Math.cos(rotationRad + Math.PI) * 25
    const carOffsetZ = Math.sin(rotationRad + Math.PI) * 25
    const car = createCarModel({ color: 0xCC0000 })  // Red car
    car.position.set(worldPos.x + carOffsetX, 0, worldPos.z - carOffsetZ)
    car.rotation.y = rotationRad
    car.name = 'test-car-behind-truck'
    testVehiclesGroup.value.add(car)
  }

  // Get secondary gate position and add a wagon nearby
  const secondaryGate = GATES['secondary']
  if (secondaryGate) {
    const worldPos = transformToWorld(secondaryGate.position, coordinateSystem.value)
    const rotationRad = -secondaryGate.rotation * (Math.PI / 180)

    // Create wagon at secondary gate (rail siding)
    const wagon = createWagonModel()
    wagon.position.set(worldPos.x, 0, worldPos.z)
    wagon.rotation.y = rotationRad
    wagon.name = 'test-wagon-secondary-gate'
    testVehiclesGroup.value.add(wagon)
  }

  scene.value.add(testVehiclesGroup.value)
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

// Handle quality level change
function handleQualityChange(level: QualityLevel): void {
  if (level === qualityLevel.value) return

  qualityLevel.value = level
  const preset = getQualityPreset(level)

  // Update renderer settings
  if (renderer.value) {
    renderer.value.setPixelRatio(preset.pixelRatio)
    renderer.value.shadowMap.enabled = preset.shadows
    if (preset.toneMapping) {
      renderer.value.toneMapping = THREE.ACESFilmicToneMapping
      renderer.value.toneMappingExposure = preset.toneMappingExposure
    } else {
      renderer.value.toneMapping = THREE.NoToneMapping
    }
  }

  // Update shadow map size on main light
  if (scene.value) {
    scene.value.traverse((child) => {
      if (child instanceof THREE.DirectionalLight && child.castShadow) {
        child.shadow.mapSize.width = preset.shadowMapSize
        child.shadow.mapSize.height = preset.shadowMapSize
        child.shadow.map?.dispose()
        child.shadow.map = null
      }
    })
  }

  if (import.meta.env.DEV) console.log(`Quality changed to: ${level}`)
}

// Collect raycast targets (only interactive meshes, not entire scene)
function getRaycastTargets(): THREE.Object3D[] {
  const targets: THREE.Object3D[] = []
  if (containerGroup.value) targets.push(containerGroup.value)
  // Building groups are added to scene directly — gather them by name
  scene.value?.children.forEach(child => {
    if (child.name === 'buildings' || child.name === 'warehouses') {
      targets.push(child)
    }
  })
  return targets
}

// Handle mouse events for container/building interaction
function onMouseMove(event: MouseEvent): void {
  if (!props.interactive || !canvasRef.value || !camera.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  // Update tooltip position immediately for smooth tracking
  tooltipX.value = event.clientX
  tooltipY.value = event.clientY

  // Throttle raycasting to one per animation frame
  if (raycastPending) return
  raycastPending = true
  requestAnimationFrame(() => {
    raycastPending = false
    performRaycast(event)
  })
}

function performRaycast(_event: MouseEvent): void {
  if (!canvasRef.value || !camera.value) return

  raycaster.setFromCamera(mouse, camera.value)

  const intersects = raycaster.intersectObjects(getRaycastTargets(), true)

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

  // Debounced tooltip update to prevent flickering
  if (tooltipDebounceTimer) {
    clearTimeout(tooltipDebounceTimer)
  }

  if (hoveredContainer) {
    canvasRef.value.style.cursor = 'pointer'
    emit('containerHover', hoveredContainer)

    // Show tooltip with container data (debounced)
    tooltipDebounceTimer = setTimeout(() => {
      hoveredContainerData.value = hoveredContainer?.data ?? null
    }, 50)
  } else if (hoveredBuilding) {
    canvasRef.value.style.cursor = 'pointer'
    emit('containerHover', null)
    hoveredContainerData.value = null
  } else {
    canvasRef.value.style.cursor = 'default'
    emit('containerHover', null)
    hoveredContainerData.value = null
  }
}

function onClick(event: MouseEvent): void {
  if (!props.interactive || !canvasRef.value || !camera.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(mouse, camera.value)

  const intersects = raycaster.intersectObjects(getRaycastTargets(), true)

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
  const height = canvasRef.value.clientHeight || 1
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

// Dispose
function dispose(): void {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }

  // Dispose test vehicles
  if (testVehiclesGroup.value) {
    disposeObject3D(testVehiclesGroup.value)
    testVehiclesGroup.value = null
  }

  // Dispose vehicle management
  if (vehicles3DRef.value) {
    vehicles3DRef.value.dispose()
    vehicles3DRef.value = null
  }
  exitDetectionRef.value = null

  disposeYard()
  disposeContainers()
  disposeContainerLabels()
  disposeBuildings()
  disposeWarehouses()
  disposeFences()
  disposeRailway()
  disposePlatforms()
  disposeRoads()
  disposeMaterials()

  // Cleanup pooled resources
  clearGeometryCaches()
  disposeSharedMaterials()
  disposeLicensePlatePool()

  controls.value?.dispose()
  renderer.value?.dispose()

  // Recursively dispose all remaining geometries and materials in the scene
  if (scene.value) {
    scene.value.traverse((obj) => {
      if (obj instanceof THREE.Mesh) {
        obj.geometry?.dispose()
        const materials = Array.isArray(obj.material) ? obj.material : [obj.material]
        for (const mat of materials) {
          if (mat && typeof mat.dispose === 'function') mat.dispose()
        }
      }
    })
    scene.value.clear()
  }

  isInitialized.value = false
}

// Watch settings and sync with composables
watch(() => settingsLayers.value.fences, (visible) => {
  if (fencesVisible.value !== visible) toggleFences()
})

watch(() => settingsLayers.value.railway, (visible) => {
  if (railwayVisible.value !== visible) toggleRailway()
})

watch(() => settingsLayers.value.platforms, (visible) => {
  if (platformsVisible.value !== visible) togglePlatforms()
})

watch(() => settingsLayers.value.roads, (visible) => {
  if (roadsVisible.value !== visible) toggleRoadsAndSidewalks()
})

watch(() => settingsLabels.value.buildings, (visible) => {
  if (buildingLabelsVisible.value !== visible) toggleBuildingLabels()
})

watch(() => settingsLabels.value.containers, (visible) => {
  setContainerLabelsVisibility(visible)
})

watch(() => settingsDisplay.value.colorMode, (mode) => {
  setColorMode(mode)  // Update container meshes
})

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
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('keydown', handleGlobalKeydown)
  if (flyAnimationId !== null) cancelAnimationFrame(flyAnimationId)
  if (tooltipDebounceTimer) clearTimeout(tooltipDebounceTimer)
  stopHighlight()
  dispose()
})

// Watch for prop changes
watch(() => props.dxfUrl, async () => {
  if (isInitialized.value) {
    await loadYard()
  }
})

// Expose internals for debug system integration
defineExpose({
  scene,
  camera,
  containerRef,
  coordinateSystem,
  fitCameraToContent,
  openSearch,
  flyToPosition,
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

    <!-- Container Search Command Bar -->
    <Transition name="search-bar">
      <div v-if="searchOpen" class="search-command-bar">
        <div class="search-input-wrapper">
          <span class="search-icon">🔍</span>
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Поиск контейнера... (например MSCU1234567)"
            autocomplete="off"
            spellcheck="false"
            @keydown="handleSearchKeydown"
            @blur="() => { if (!searchQuery) closeSearch() }"
          />
          <kbd v-if="!searchQuery" class="search-hint">ESC для закрытия</kbd>
          <button v-if="searchQuery" class="search-clear" @click="closeSearch">✕</button>
        </div>

        <!-- Search Results Dropdown -->
        <div v-if="searchResults.length > 0" class="search-results">
          <div
            v-for="(result, i) in searchResults"
            :key="result.container.id"
            class="search-result-item"
            :class="{ active: i === selectedSearchIndex }"
            @mouseenter="selectedSearchIndex = i"
            @click="flyToSearchResult(result)"
          >
            <span class="result-number">{{ result.container.data?.container_number ?? `#${result.container.id}` }}</span>
            <span class="result-meta">
              <span class="result-type">{{ result.container.data?.container_type ?? '—' }}</span>
              <span class="result-status" :class="result.container.data?.status?.toLowerCase()">
                {{ result.container.data?.status === 'LADEN' ? 'Груженый' : 'Пустой' }}
              </span>
              <span v-if="result.container.data?.dwell_days" class="result-dwell">
                {{ result.container.data.dwell_days }}д
              </span>
            </span>
          </div>
        </div>

        <!-- No results -->
        <div v-else-if="searchQuery.length >= 2" class="search-results">
          <div class="search-no-results">Контейнер не найден</div>
        </div>
      </div>
    </Transition>

    <!-- Search trigger hint (when closed) -->
    <div v-if="!searchOpen" class="search-trigger" @click="openSearch">
      <span class="search-icon-small">🔍</span>
      <span class="search-trigger-text">Поиск контейнера</span>
      <kbd class="search-kbd">/</kbd>
    </div>

    <!-- Loading overlay -->
    <div v-if="dxfLoading" class="yard-overlay">
      <a-spin size="large" />
      <span class="loading-text">Загрузка терминала...</span>
    </div>

    <!-- Error overlay -->
    <div v-if="dxfError" class="yard-overlay error">
      <a-result status="error" :title="dxfError" />
    </div>

    <!-- Controls -->
    <div class="yard-controls">
      <a-space direction="vertical" size="small">
        <a-tooltip title="Настройки" placement="left">
          <a-button shape="circle" @click="isSettingsOpen = true">
            <template #icon><span>⚙️</span></template>
          </a-button>
        </a-tooltip>
        <a-divider style="margin: 4px 0; min-width: 32px;" />
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
      </a-space>
    </div>

    <!-- Settings Drawer -->
    <YardSettingsDrawer
      v-model:visible="isSettingsOpen"
      :dxf-layers="layers"
      :quality-level="qualityLevel"
      @camera-top="setTopView"
      @camera-isometric="setIsometricView"
      @camera-fit="fitCameraToContent"
      @dxf-layer-toggle="toggleLayer"
      @dxf-show-all="showAllLayers"
      @dxf-hide-all="hideAllLayers"
      @quality-change="handleQualityChange"
    />

    <!-- Stats panel -->
    <div v-if="settingsDisplay.showStats && dxfStats" class="yard-stats">
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

    <!-- Container Tooltip -->
    <ContainerTooltip
      :container="hoveredContainerData"
      :x="tooltipX"
      :y="tooltipY"
      :visible="hoveredContainerData !== null"
    />

    <!-- Legend -->
    <div class="color-legend">
      <div v-if="currentColorMode === 'visual'" class="legend-items">
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#0077B6' }" />
          <span class="legend-color" :style="{ background: '#00B4D8' }" />
          <span class="legend-color" :style="{ background: '#023E8A' }" />
          <span class="legend-color" :style="{ background: '#48CAE4' }" />
          <span class="legend-color" :style="{ background: '#90E0EF' }" />
          <span class="legend-color" :style="{ background: '#F97316' }" />
          <span style="margin-left: 4px;">Визуальный режим</span>
        </div>
      </div>
      <div v-else-if="currentColorMode === 'status'" class="legend-items">
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#0077B6' }" />
          <span>Груженые</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#F97316' }" />
          <span>Пустые</span>
        </div>
      </div>
      <div v-else-if="currentColorMode === 'dwell'" class="legend-items dwell-legend">
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#22C55E' }" />
          <span>0-3д</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#3B82F6' }" />
          <span>4-7д</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#F59E0B' }" />
          <span>8-14д</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#F97316' }" />
          <span>15-21д</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" :style="{ background: '#EF4444' }" />
          <span>22+д</span>
        </div>
      </div>
      <div v-else-if="currentColorMode === 'hazmat'" class="legend-items hazmat-legend">
        <div class="legend-row">
          <div class="legend-item">
            <span class="legend-color" :style="{ background: '#F97316' }" />
            <span>1</span>
          </div>
          <div class="legend-item">
            <span class="legend-color" :style="{ background: '#22C55E' }" />
            <span>2</span>
          </div>
          <div class="legend-item">
            <span class="legend-color" :style="{ background: '#EF4444' }" />
            <span>3</span>
          </div>
          <div class="legend-item">
            <span class="legend-color" :style="{ background: '#DC2626' }" />
            <span>4</span>
          </div>
          <div class="legend-item">
            <span class="legend-color" :style="{ background: '#FACC15' }" />
            <span>5</span>
          </div>
        </div>
        <div class="legend-row">
          <div class="legend-item">
            <span class="legend-color bordered" :style="{ background: '#F8FAFC' }" />
            <span>6</span>
          </div>
          <div class="legend-item">
            <span class="legend-color" :style="{ background: '#FDE047' }" />
            <span>7</span>
          </div>
          <div class="legend-item">
            <span class="legend-color" :style="{ background: '#1F2937' }" />
            <span>8</span>
          </div>
          <div class="legend-item">
            <span class="legend-color bordered" :style="{ background: '#E5E7EB' }" />
            <span>9</span>
          </div>
          <div class="legend-item">
            <span class="legend-color" :style="{ background: '#6B7280' }" />
            <span>—</span>
          </div>
        </div>
        <div class="legend-label">IMO классы</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.yard-view-3d {
  /* Premium color palette CSS variables */
  --yard-bg: #F0F7FA;
  --yard-ground: #E8F4F8;
  --yard-primary: #0077B6;
  --yard-secondary: #00B4D8;

  position: relative;
  width: 100%;
  background: var(--yard-bg);
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

/* 5-tier dwell legend fits more items compactly */
.dwell-legend {
  gap: 10px;
}

.dwell-legend .legend-item {
  gap: 4px;
}

/* IMO hazmat legend - two rows of 5 classes each */
.hazmat-legend {
  flex-direction: column;
  gap: 6px;
}

.hazmat-legend .legend-row {
  display: flex;
  gap: 8px;
}

.hazmat-legend .legend-item {
  gap: 3px;
  font-size: 11px;
}

.hazmat-legend .legend-label {
  font-size: 10px;
  color: #888;
  text-align: center;
  margin-top: 2px;
}

.hazmat-legend .legend-color.bordered {
  border: 1px solid #ccc;
}

/* ============ Search Command Bar ============ */
.search-command-bar {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  width: min(520px, calc(100% - 32px));
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(12px);
  border: 1px solid #d9d9d9;
  border-radius: 10px;
  padding: 10px 16px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0, 119, 182, 0.08);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-input-wrapper:focus-within {
  border-color: var(--yard-primary, #0077B6);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12), 0 0 0 2px rgba(0, 119, 182, 0.15);
}

.search-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  letter-spacing: 0.5px;
  background: transparent;
  color: #1a1a1a;
}

.search-input::placeholder {
  color: #aaa;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  letter-spacing: 0;
}

.search-hint {
  font-size: 11px;
  color: #999;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid #e5e5e5;
  white-space: nowrap;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

.search-clear {
  border: none;
  background: none;
  color: #999;
  cursor: pointer;
  font-size: 16px;
  padding: 2px 4px;
  border-radius: 4px;
  transition: color 0.15s, background 0.15s;
}

.search-clear:hover {
  color: #333;
  background: #f0f0f0;
}

/* Results dropdown */
.search-results {
  margin-top: 4px;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(12px);
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  overflow: hidden;
}

.search-result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.1s;
  border-bottom: 1px solid #f5f5f5;
}

.search-result-item:last-child {
  border-bottom: none;
}

.search-result-item:hover,
.search-result-item.active {
  background: #f0f7fa;
}

.result-number {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-weight: 600;
  font-size: 14px;
  color: #1a1a1a;
  letter-spacing: 0.5px;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #888;
}

.result-type {
  background: #f0f0f0;
  padding: 1px 6px;
  border-radius: 3px;
}

.result-status {
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.result-status.laden {
  background: rgba(0, 119, 182, 0.1);
  color: #0077B6;
}

.result-status.empty {
  background: rgba(249, 115, 22, 0.1);
  color: #F97316;
}

.result-dwell {
  color: #aaa;
}

.search-no-results {
  padding: 16px;
  text-align: center;
  color: #999;
  font-size: 13px;
}

/* Search trigger button (when search is closed) */
.search-trigger {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s, border-color 0.15s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.search-trigger:hover {
  background: rgba(255, 255, 255, 0.98);
  border-color: var(--yard-primary, #0077B6);
  box-shadow: 0 2px 12px rgba(0, 119, 182, 0.1);
}

.search-icon-small {
  font-size: 13px;
}

.search-trigger-text {
  font-size: 13px;
  color: #888;
}

.search-kbd {
  font-size: 11px;
  color: #aaa;
  background: #f5f5f5;
  padding: 1px 6px;
  border-radius: 3px;
  border: 1px solid #e0e0e0;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Search bar transitions */
.search-bar-enter-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.search-bar-leave-active {
  transition: opacity 0.1s ease, transform 0.1s ease;
}

.search-bar-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(-8px);
}

.search-bar-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-4px);
}

</style>
