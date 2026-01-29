/**
 * Building 3D Rendering Composable
 * Renders extruded building footprints using ExtrudeGeometry
 */

import { ref, shallowRef, computed, type Ref } from 'vue'
import * as THREE from 'three'
import type { DxfCoordinateSystem } from '@/types/dxf'
import {
  dxfToWorld as dxfToWorldUtil,
  type CoordinateTransformOptions
} from '@/utils/coordinateTransforms'

// Building footprint data from extraction
export interface BuildingPosition {
  id: number
  handle?: string
  vertices: { x: number; y: number }[]  // DXF coordinates
  centroid: { x: number; y: number }
  bounds: { minX: number; maxX: number; minY: number; maxY: number }
  area: number
  elevation?: number
  height?: number  // Override default height
  label?: string   // Building label/name
}

// Combined building info for rendering
export interface Building3D extends BuildingPosition {
  mesh?: THREE.Mesh
  isSelected: boolean
  isHovered: boolean
}

// Visual building color palette (creates variety like Hero3DView)
export const VISUAL_BUILDING_PALETTE = [
  0xE5E7EB,   // Light Gray (offices)
  0xD1D5DB,   // Medium Gray
  0x9CA3AF,   // Darker Gray (warehouses)
  0x0077B6,   // Deep Blue (main buildings)
  0x00B4D8,   // Light Cyan (facilities)
  0xF97316,   // Orange (gates, special)
  0xD4A574,   // Tan (storage)
  0x6B7280,   // Slate (industrial)
]

// Functional color schemes
export const BUILDING_COLORS = {
  default: 0xE5E7EB,     // Light gray (premium)
  hovered: 0x48CAE4,     // Sky blue (premium)
  selected: 0x52c41a,    // Green
  roof: 0xD1D5DB,        // Slightly darker for roof distinction
}

// Default building height in meters
const DEFAULT_BUILDING_HEIGHT = 8

export interface UseBuildings3DOptions {
  /** Scale factor for coordinates */
  scale?: number
  /** Center point for coordinate transformation */
  center?: { x: number; y: number }
  /** DXF coordinate system for alignment with infrastructure */
  coordinateSystem?: DxfCoordinateSystem
  /** Default building height in meters */
  defaultHeight?: number
  /** Show building labels */
  showLabels?: boolean
}

const DEFAULT_OPTIONS: Required<Omit<UseBuildings3DOptions, 'coordinateSystem'>> = {
  scale: 1.0,
  center: { x: 0, y: 0 },
  defaultHeight: DEFAULT_BUILDING_HEIGHT,
  showLabels: true,
}

type BuildingOptions = typeof DEFAULT_OPTIONS & { coordinateSystem?: DxfCoordinateSystem }

export function useBuildings3D(
  positionsRef: Ref<BuildingPosition[]>
) {
  // Options
  const options = ref<BuildingOptions>({ ...DEFAULT_OPTIONS })

  // Three.js objects
  const buildingGroup = shallowRef<THREE.Group | null>(null)
  const buildingMeshes = shallowRef<Map<number, THREE.Mesh>>(new Map())
  const labelSprites = shallowRef<Map<number, THREE.Sprite>>(new Map())
  const labelsGroup = shallowRef<THREE.Group | null>(null)

  // State
  const selectedIds = ref<Set<number>>(new Set())
  const hoveredId = ref<number | null>(null)
  const labelsVisible = ref(true)

  // Computed: merged building data
  const buildings = computed<Building3D[]>(() => {
    return positionsRef.value.map(pos => ({
      ...pos,
      mesh: buildingMeshes.value.get(pos.id),
      isSelected: selectedIds.value.has(pos.id),
      isHovered: hoveredId.value === pos.id,
    }))
  })

  /**
   * Get visual color for building based on its characteristics
   * Larger buildings get more prominent colors, smaller ones are neutral
   */
  function getBuildingVisualColor(building: BuildingPosition): number {
    // Use label to determine building type if available
    const label = building.label?.toLowerCase() ?? ''

    // Special buildings get distinctive colors
    if (label.includes('ворота') || label.includes('gate') || label.includes('кпп')) {
      return 0x0077B6  // Deep Blue for gates
    }
    if (label.includes('офис') || label.includes('office') || label.includes('admin')) {
      return 0xE5E7EB  // Light Gray for offices
    }
    if (label.includes('склад') || label.includes('warehouse') || label.includes('storage')) {
      return 0xD4A574  // Tan for warehouses
    }

    // For unlabeled buildings, use area-based coloring
    const area = building.area
    if (area > 2000) {
      // Large buildings - prominent colors
      return VISUAL_BUILDING_PALETTE[building.id % 4]!  // First 4 neutral colors
    } else if (area > 500) {
      // Medium buildings
      return VISUAL_BUILDING_PALETTE[3 + (building.id % 3)]!  // Blue/cyan range
    } else {
      // Small buildings - neutral colors
      return VISUAL_BUILDING_PALETTE[building.id % VISUAL_BUILDING_PALETTE.length]!
    }
  }

  /**
   * Convert DXF coordinates to Three.js world coordinates
   * (Wrapper around central utility for convenience)
   */
  function dxfToWorld(
    dxfX: number,
    dxfY: number,
    opts: BuildingOptions = options.value
  ): THREE.Vector3 {
    const transformOpts: CoordinateTransformOptions = {
      scale: opts.scale,
      center: opts.center,
    }
    return dxfToWorldUtil(dxfX, dxfY, transformOpts) ?? new THREE.Vector3(0, 0, 0)
  }

  /**
   * Create a single building mesh from footprint vertices
   */
  function createBuildingMesh(
    building: BuildingPosition,
    opts: BuildingOptions
  ): THREE.Mesh | null {
    const vertices = building.vertices
    if (vertices.length < 3) {
      console.warn(`Building ${building.id} has fewer than 3 vertices, skipping`)
      return null
    }

    // Create 2D shape from vertices (in XZ plane)
    const shape = new THREE.Shape()

    // Convert first vertex to world coordinates
    const firstVertex = vertices[0]!
    const firstWorld = dxfToWorld(firstVertex.x, firstVertex.y, opts)
    shape.moveTo(firstWorld.x, -firstWorld.z)  // Shape uses X,Y; we'll rotate later

    // Add remaining vertices
    for (let i = 1; i < vertices.length - 1; i++) {  // Skip last vertex (same as first for closed)
      const vertex = vertices[i]!
      const world = dxfToWorld(vertex.x, vertex.y, opts)
      shape.lineTo(world.x, -world.z)
    }
    shape.closePath()

    // Extrude settings
    const height = building.height ?? opts.defaultHeight
    const extrudeSettings: THREE.ExtrudeGeometryOptions = {
      depth: height,
      bevelEnabled: false,
    }

    // Create geometry
    const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings)

    // Rotate to stand upright: ExtrudeGeometry extrudes along +Z,
    // we need buildings to stand up along +Y
    geometry.rotateX(-Math.PI / 2)

    // Pick color based on building characteristics for visual variety
    const buildingColor = getBuildingVisualColor(building)

    // Create material with premium PBR settings for concrete/wall look
    const material = new THREE.MeshStandardMaterial({
      color: buildingColor,
      roughness: 0.8,          // Matte concrete surface
      metalness: 0.0,          // Non-metallic
      envMapIntensity: 0.2,    // Subtle environment reflections
      flatShading: false,
    })

    const mesh = new THREE.Mesh(geometry, material)
    mesh.castShadow = true
    mesh.receiveShadow = true
    mesh.name = `building_${building.id}`
    mesh.userData = { type: 'building', buildingId: building.id }

    return mesh
  }

  /**
   * Create a text sprite for building label
   */
  function createLabelSprite(
    text: string,
    position: THREE.Vector3,
    height: number
  ): THREE.Sprite {
    // Create canvas for text rendering
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')!

    // Configure canvas size and font
    const fontSize = 48
    const padding = 16
    context.font = `bold ${fontSize}px Arial, sans-serif`
    const metrics = context.measureText(text)
    const textWidth = metrics.width

    canvas.width = textWidth + padding * 2
    canvas.height = fontSize + padding * 2

    // Redraw after resize (canvas clears on resize)
    context.font = `bold ${fontSize}px Arial, sans-serif`

    // Draw background with rounded corners
    context.fillStyle = 'rgba(255, 255, 255, 0.9)'
    const radius = 8
    context.beginPath()
    context.roundRect(0, 0, canvas.width, canvas.height, radius)
    context.fill()

    // Draw border
    context.strokeStyle = 'rgba(0, 0, 0, 0.3)'
    context.lineWidth = 2
    context.stroke()

    // Draw text
    context.fillStyle = '#333333'
    context.textAlign = 'center'
    context.textBaseline = 'middle'
    context.fillText(text, canvas.width / 2, canvas.height / 2)

    // Create texture from canvas
    const texture = new THREE.CanvasTexture(canvas)
    texture.minFilter = THREE.LinearFilter
    texture.magFilter = THREE.LinearFilter

    // Create sprite material
    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    })

    // Create sprite
    const sprite = new THREE.Sprite(material)

    // Scale sprite to reasonable size (based on canvas aspect ratio)
    const scale = 0.15  // Adjust for visibility
    sprite.scale.set(canvas.width * scale, canvas.height * scale, 1)

    // Position above building
    sprite.position.set(position.x, height + 2, position.z)

    return sprite
  }

  /**
   * Initialize building meshes
   */
  function createBuildingMeshes(opts: UseBuildings3DOptions = {}): THREE.Group {
    // Merge options
    const coordSys = opts.coordinateSystem
    const mergedOpts: BuildingOptions = {
      ...DEFAULT_OPTIONS,
      ...opts,
      scale: coordSys?.scale ?? opts.scale ?? DEFAULT_OPTIONS.scale,
      center: coordSys
        ? { x: coordSys.center.x, y: coordSys.center.y }
        : (opts.center ?? DEFAULT_OPTIONS.center),
    }
    options.value = mergedOpts

    // Create group
    const group = new THREE.Group()
    group.name = 'buildings'
    buildingGroup.value = group

    const positions = positionsRef.value
    if (positions.length === 0) return group

    // Create mesh for each building
    const meshMap = new Map<number, THREE.Mesh>()

    positions.forEach(building => {
      const mesh = createBuildingMesh(building, mergedOpts)
      if (mesh) {
        meshMap.set(building.id, mesh)
        group.add(mesh)
      }
    })

    buildingMeshes.value = meshMap

    // Create labels group
    const labels = new THREE.Group()
    labels.name = 'building_labels'
    labelsGroup.value = labels

    // Create labels for each building
    if (mergedOpts.showLabels) {
      const spriteMap = new Map<number, THREE.Sprite>()

      positions.forEach(building => {
        const label = building.label ?? `Здание ${building.id}`
        const centroidWorld = dxfToWorld(building.centroid.x, building.centroid.y, mergedOpts)
        const height = building.height ?? mergedOpts.defaultHeight

        const sprite = createLabelSprite(label, centroidWorld, height)
        sprite.userData = { type: 'building_label', buildingId: building.id }
        spriteMap.set(building.id, sprite)
        labels.add(sprite)
      })

      labelSprites.value = spriteMap
      labelsVisible.value = true
    }

    group.add(labels)

    console.log(`🏢 Created ${meshMap.size} building meshes with labels`)

    return group
  }

  /**
   * Get color for building based on state
   */
  function getBuildingColor(buildingId: number): number {
    if (selectedIds.value.has(buildingId)) {
      return BUILDING_COLORS.selected
    }
    if (hoveredId.value === buildingId) {
      return BUILDING_COLORS.hovered
    }
    return BUILDING_COLORS.default
  }

  /**
   * Update building colors based on selection/hover state
   */
  function updateColors(): void {
    buildingMeshes.value.forEach((mesh, id) => {
      const material = mesh.material as THREE.MeshStandardMaterial
      material.color.setHex(getBuildingColor(id))
    })
  }

  /**
   * Select a building by ID
   */
  function selectBuilding(id: number, additive: boolean = false): void {
    if (!additive) {
      selectedIds.value.clear()
    }
    selectedIds.value.add(id)
    updateColors()
  }

  /**
   * Deselect a building
   */
  function deselectBuilding(id: number): void {
    selectedIds.value.delete(id)
    updateColors()
  }

  /**
   * Clear all selections
   */
  function clearSelection(): void {
    selectedIds.value.clear()
    updateColors()
  }

  /**
   * Set hovered building
   */
  function setHovered(id: number | null): void {
    if (hoveredId.value !== id) {
      hoveredId.value = id
      updateColors()
    }
  }

  /**
   * Toggle labels visibility
   */
  function toggleLabels(visible?: boolean): void {
    const newState = visible ?? !labelsVisible.value
    labelsVisible.value = newState
    if (labelsGroup.value) {
      labelsGroup.value.visible = newState
    }
  }

  /**
   * Get building at raycast intersection
   */
  function getBuildingAtIntersection(intersection: THREE.Intersection): Building3D | null {
    const mesh = intersection.object
    if (mesh.userData?.type !== 'building') return null

    const buildingId = mesh.userData.buildingId as number
    return buildings.value.find(b => b.id === buildingId) ?? null
  }

  /**
   * Get building by ID
   */
  function getBuildingById(id: number): Building3D | null {
    return buildings.value.find(b => b.id === id) ?? null
  }

  /**
   * Dispose of all resources
   */
  function dispose(): void {
    // Dispose building meshes
    buildingMeshes.value.forEach(mesh => {
      mesh.geometry.dispose()
      if (mesh.material instanceof THREE.Material) {
        mesh.material.dispose()
      }
    })
    buildingMeshes.value.clear()

    // Dispose label sprites
    labelSprites.value.forEach(sprite => {
      if (sprite.material instanceof THREE.SpriteMaterial) {
        sprite.material.map?.dispose()
        sprite.material.dispose()
      }
    })
    labelSprites.value.clear()

    if (labelsGroup.value) {
      labelsGroup.value.clear()
      labelsGroup.value = null
    }

    if (buildingGroup.value) {
      buildingGroup.value.clear()
      buildingGroup.value = null
    }

    selectedIds.value.clear()
    hoveredId.value = null
  }

  return {
    // Three.js objects
    buildingGroup,
    buildingMeshes,
    labelsGroup,

    // State
    buildings,
    selectedIds,
    hoveredId,
    labelsVisible,

    // Methods
    createBuildingMeshes,
    selectBuilding,
    deselectBuilding,
    clearSelection,
    setHovered,
    toggleLabels,
    getBuildingAtIntersection,
    getBuildingById,
    dxfToWorld,
    dispose,
  }
}
