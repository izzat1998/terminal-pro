/**
 * DXF Yard Infrastructure Composable
 * Loads and renders the DXF-based terminal infrastructure
 */

import { ref, shallowRef, computed } from 'vue'
import * as THREE from 'three'
import { dxfToThree, loadDxfFromUrl, type DxfConversionResult } from '@/utils/dxfToThree'
import type { DxfStats, DxfCoordinateSystem } from '@/types/dxf'

// Layer color mapping for terminal infrastructure
// Based on actual layer names from yard.dxf file
export const YARD_LAYER_COLORS: Record<string, number> = {
  // Default/main layer (most entities)
  '0': 0x888888,                      // Default layer - medium gray

  // Fine details (many entities - often hidden for performance)
  '_2._Тонкая': 0x999999,             // Thin lines - light gray
  '_3._Осевая': 0x666666,             // Axis lines - dark gray

  // Terminal infrastructure
  'Т-КП': 0x1890ff,                   // Container yard / checkpoints - blue
  'Т-козловой кран пути': 0x333333,   // Gantry crane rails - very dark
  'Т-ось дороги': 0xff6600,           // Road axis - orange
  'Т-заливки2': 0xcccccc,             // Filled areas - light gray

  // Buildings and structures
  '(007) Здания': 0xbfbfbf,           // Buildings - light gray
  'КЖ': 0xa0a0a0,                     // Reinforced concrete - gray
  'DOMA': 0xcccccc,                   // Houses - light gray

  // Boundaries and fences
  '(040) Ограда': 0x8b4513,           // Fence - brown

  // Transportation
  '(023) Ж_дорога': 0x4a4a4a,         // Railway - dark gray
  'ЖД_упор': 0x333333,                // Railway stop - very dark

  // Utilities
  '(016) Кабель': 0xffd700,           // Cable - gold
  '(013) Газ': 0xffcc00,              // Gas - yellow
  '(020) Теплотрасса': 0xff4500,      // Heating - red-orange
  '(022) Возд. Линии': 0x9932cc,      // Power lines - purple
  'Irrigaciya': 0x4169e1,             // Irrigation - royal blue

  // Terrain features
  '(027) Гидрография': 0x1e90ff,      // Hydrography - dodger blue
  '(028) Гидротехн.': 0x00bfff,       // Hydraulic structures - deep sky blue
  '(029) Мосты': 0x696969,            // Bridges - dim gray
  '(035) Откосы': 0x8b7355,           // Slopes - tan
  '(009) Спец.': 0xff69b4,            // Special - hot pink
  '(011) Колодцы': 0x2f4f4f,          // Wells - dark slate gray

  // Labels and annotations
  'Defpoints': 0xaaaaaa,              // Definition points - light gray
  'Текст штампа': 0x333333,           // Stamp text - dark
  'SHTAMP': 0x333333,                 // Stamp - dark

  // Equipment
  'Shlakbaum': 0xff0000,              // Barrier - red
  'DLXLUM04': 0xffd700,               // Lighting fixtures - gold
  'DLXLUM01': 0xffd700,               // Lighting fixtures - gold
  'DLXLUMEX': 0xffd700,               // External lighting - gold
  'Kab stolbik': 0x808080,            // Cable post - gray
  'Pred. stolbik': 0xff6347,          // Warning post - tomato
}

// Layer categories for grouped visibility control
export const LAYER_CATEGORIES = {
  infrastructure: ['Т-КП', 'Т-козловой кран пути', 'Т-ось дороги', 'Т-заливки2', '(023) Ж_дорога', 'ЖД_упор'],
  boundaries: ['(040) Ограда'],
  buildings: ['(007) Здания', 'КЖ', 'DOMA'],
  utilities: ['(016) Кабель', '(013) Газ', '(020) Теплотрасса', '(022) Возд. Линии', 'Irrigaciya'],
  terrain: ['(027) Гидрография', '(028) Гидротехн.', '(029) Мосты', '(035) Откосы'],
  lighting: ['DLXLUM04', 'DLXLUM01', 'DLXLUMEX'],
  details: ['_2._Тонкая', '_3._Осевая', 'Defpoints'],
  equipment: ['Shlakbaum', 'Kab stolbik', 'Pred. stolbik'],
}

export interface YardLayerInfo {
  name: string
  visible: boolean
  objectCount: number
  category: string
}

export interface UseDxfYardOptions {
  /** Scale factor (auto-detected from DXF INSUNITS if not specified) */
  scale?: number
  /** Center geometry at origin (default: true) */
  centerAtOrigin?: boolean
  /** Layers to exclude from rendering */
  excludeLayers?: string[]
  /** Custom layer colors override */
  layerColors?: Record<string, number>
}

// Note: scale is now auto-detected from DXF INSUNITS header
// For yard.dxf with INSUNITS=6, the file is already in meters
const DEFAULT_OPTIONS: Omit<Required<UseDxfYardOptions>, 'scale'> & { scale?: number } = {
  scale: undefined,  // Let dxfToThree auto-detect from INSUNITS
  centerAtOrigin: true,
  excludeLayers: [],
  layerColors: YARD_LAYER_COLORS,
}

export function useDxfYard() {
  // State
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const dxfResult = shallowRef<DxfConversionResult | null>(null)
  const yardGroup = shallowRef<THREE.Group | null>(null)
  const stats = ref<DxfStats | null>(null)
  const coordinateSystem = shallowRef<DxfCoordinateSystem | null>(null)

  // Layer visibility state
  const layerVisibility = ref<Map<string, boolean>>(new Map())

  // Computed: list of layers with info
  const layers = computed<YardLayerInfo[]>(() => {
    if (!dxfResult.value) return []

    const result: YardLayerInfo[] = []
    for (const [name, group] of dxfResult.value.layerGroups) {
      // Determine category
      let category = 'other'
      for (const [cat, layers] of Object.entries(LAYER_CATEGORIES)) {
        if (layers.includes(name)) {
          category = cat
          break
        }
      }

      result.push({
        name,
        visible: layerVisibility.value.get(name) ?? true,
        objectCount: group.children.length,
        category,
      })
    }

    return result.sort((a, b) => a.name.localeCompare(b.name))
  })

  // Computed: bounds in world units (using coordinate system scale)
  const bounds = computed(() => {
    if (!stats.value || !coordinateSystem.value) return null
    const scale = coordinateSystem.value.scale
    return {
      width: stats.value.bounds.width * scale,
      height: stats.value.bounds.height * scale,
      minX: stats.value.bounds.min.x * scale,
      maxX: stats.value.bounds.max.x * scale,
      minY: stats.value.bounds.min.y * scale,
      maxY: stats.value.bounds.max.y * scale,
    }
  })

  /**
   * Load DXF from string content
   */
  function loadFromContent(
    content: string,
    userOptions: UseDxfYardOptions = {}
  ): THREE.Group | null {
    const options = { ...DEFAULT_OPTIONS, ...userOptions }

    isLoading.value = true
    error.value = null

    try {
      const result = dxfToThree(content, {
        scale: options.scale,  // undefined = auto-detect from INSUNITS
        centerAtOrigin: options.centerAtOrigin,
        excludeLayers: options.excludeLayers,
        layerColors: { ...YARD_LAYER_COLORS, ...options.layerColors },
      })

      dxfResult.value = result
      yardGroup.value = result.group
      stats.value = result.stats
      coordinateSystem.value = result.coordinateSystem

      // Initialize layer visibility
      for (const [name] of result.layerGroups) {
        layerVisibility.value.set(name, true)
      }

      isLoading.value = false
      return result.group
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to parse DXF'
      isLoading.value = false
      return null
    }
  }

  /**
   * Load DXF from URL
   */
  async function loadFromUrl(
    url: string,
    userOptions: UseDxfYardOptions = {}
  ): Promise<THREE.Group | null> {
    const options = { ...DEFAULT_OPTIONS, ...userOptions }

    isLoading.value = true
    error.value = null

    try {
      const result = await loadDxfFromUrl(url, {
        scale: options.scale,  // undefined = auto-detect from INSUNITS
        centerAtOrigin: options.centerAtOrigin,
        excludeLayers: options.excludeLayers,
        layerColors: { ...YARD_LAYER_COLORS, ...options.layerColors },
      })

      dxfResult.value = result
      yardGroup.value = result.group
      stats.value = result.stats
      coordinateSystem.value = result.coordinateSystem

      // Initialize layer visibility
      for (const [name] of result.layerGroups) {
        layerVisibility.value.set(name, true)
      }

      isLoading.value = false
      return result.group
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load DXF'
      isLoading.value = false
      return null
    }
  }

  /**
   * Load DXF from File object
   */
  async function loadFromFile(
    file: File,
    userOptions: UseDxfYardOptions = {}
  ): Promise<THREE.Group | null> {
    const content = await file.text()
    return loadFromContent(content, userOptions)
  }

  /**
   * Set visibility of a specific layer
   */
  function setLayerVisibility(layerName: string, visible: boolean): void {
    if (!dxfResult.value) return

    const layerGroup = dxfResult.value.layerGroups.get(layerName)
    if (layerGroup) {
      layerGroup.visible = visible
      layerVisibility.value.set(layerName, visible)
    }
  }

  /**
   * Set visibility of all layers in a category
   */
  function setCategoryVisibility(category: keyof typeof LAYER_CATEGORIES, visible: boolean): void {
    const layerNames = LAYER_CATEGORIES[category]
    for (const name of layerNames) {
      setLayerVisibility(name, visible)
    }
  }

  /**
   * Show all layers
   */
  function showAllLayers(): void {
    if (!dxfResult.value) return

    for (const [name, group] of dxfResult.value.layerGroups) {
      group.visible = true
      layerVisibility.value.set(name, true)
    }
  }

  /**
   * Hide all layers
   */
  function hideAllLayers(): void {
    if (!dxfResult.value) return

    for (const [name, group] of dxfResult.value.layerGroups) {
      group.visible = false
      layerVisibility.value.set(name, false)
    }
  }

  /**
   * Get Three.js group for a specific layer
   */
  function getLayerGroup(layerName: string): THREE.Group | undefined {
    return dxfResult.value?.layerGroups.get(layerName)
  }

  /**
   * Get all text sprites (for zoom-based scaling)
   */
  function getTextSprites(): THREE.Sprite[] {
    return dxfResult.value?.textSprites || []
  }

  /**
   * Convert DXF coordinates to Three.js world coordinates
   * Useful for placing objects at DXF positions
   */
  function dxfToWorld(dxfX: number, dxfY: number, dxfZ: number = 0): THREE.Vector3 {
    if (!coordinateSystem.value) {
      return new THREE.Vector3(0, 0, 0)
    }

    const { scale, center } = coordinateSystem.value

    const x = (dxfX - center.x) * scale
    const y = (dxfZ - (center.z || 0)) * scale  // DXF Z becomes Three.js Y (up)
    const z = -(dxfY - center.y) * scale  // DXF Y becomes -Z (depth)

    return new THREE.Vector3(x, y, z)
  }

  /**
   * Convert Three.js world coordinates to DXF coordinates
   */
  function worldToDxf(worldX: number, worldY: number, worldZ: number): { x: number; y: number; z: number } {
    if (!coordinateSystem.value) {
      return { x: 0, y: 0, z: 0 }
    }

    const { scale, center } = coordinateSystem.value

    return {
      x: (worldX / scale) + center.x,
      y: (-worldZ / scale) + center.y,
      z: (worldY / scale) + (center.z || 0),
    }
  }

  /**
   * Dispose of all resources
   */
  function dispose(): void {
    if (yardGroup.value) {
      yardGroup.value.traverse((obj) => {
        if (obj instanceof THREE.Mesh || obj instanceof THREE.Line) {
          obj.geometry?.dispose()
          if (obj.material instanceof THREE.Material) {
            obj.material.dispose()
          } else if (Array.isArray(obj.material)) {
            obj.material.forEach(m => m.dispose())
          }
        }
        if (obj instanceof THREE.Sprite && obj.material.map) {
          obj.material.map.dispose()
          obj.material.dispose()
        }
      })
    }

    dxfResult.value = null
    yardGroup.value = null
    stats.value = null
    coordinateSystem.value = null
    layerVisibility.value.clear()
    error.value = null
  }

  return {
    // State
    isLoading,
    error,
    yardGroup,
    stats,
    layers,
    bounds,
    layerVisibility,
    coordinateSystem,

    // Loading
    loadFromContent,
    loadFromUrl,
    loadFromFile,

    // Layer control
    setLayerVisibility,
    setCategoryVisibility,
    showAllLayers,
    hideAllLayers,
    getLayerGroup,
    getTextSprites,

    // Coordinate conversion
    dxfToWorld,
    worldToDxf,

    // Cleanup
    dispose,
  }
}
