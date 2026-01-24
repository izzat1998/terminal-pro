/**
 * Container 3D Rendering Composable
 * Renders interactive 3D container boxes using InstancedMesh
 */

import { ref, shallowRef, computed, watch, type Ref } from 'vue'
import * as THREE from 'three'
import type { DxfCoordinateSystem } from '@/types/dxf'

// Container position data from DXF extraction
export interface ContainerPosition {
  id: number
  x: number      // Centered X coordinate (relative to extraction center)
  y: number      // Centered Y coordinate (relative to extraction center)
  rotation: number  // Degrees
  blockName?: string
  layer?: string
  tier?: number  // Stack level (1 = ground, 2-4 = stacked on top)
  // Original DXF coordinates (before centering) - used for alignment with DXF infrastructure
  _original?: {
    x: number
    y: number
  }
}

/**
 * Add random stacking (tiers) to existing containers
 * Takes existing ground-level containers and randomly stacks more on top
 */
export function addRandomStacking(
  baseContainers: ContainerPosition[],
  options: {
    maxTier?: number     // Maximum stack height (default: 4)
    stackRate?: number   // Probability of stacking on existing container (0-1, default: 0.6)
  } = {}
): ContainerPosition[] {
  const {
    maxTier = 4,
    stackRate = 0.6,
  } = options

  // Mark all base containers as tier 1
  const groundContainers = baseContainers.map(c => ({
    ...c,
    tier: 1,
  }))

  const result: ContainerPosition[] = [...groundContainers]
  let nextId = Math.max(...baseContainers.map(c => c.id)) + 1

  // Track current tier for each ground container
  const tierMap: Map<number, number> = new Map()
  groundContainers.forEach(c => tierMap.set(c.id, 1))

  // Add stacked containers on top of existing ones
  for (let tier = 2; tier <= maxTier; tier++) {
    for (const groundContainer of groundContainers) {
      const currentTier = tierMap.get(groundContainer.id) ?? 1

      // Only stack if this container is at tier-1 and random check passes
      if (currentTier === tier - 1 && Math.random() < stackRate) {
        tierMap.set(groundContainer.id, tier)

        // Create stacked container at same position but higher tier
        result.push({
          id: nextId++,
          x: groundContainer.x,
          y: groundContainer.y,
          rotation: groundContainer.rotation,
          blockName: groundContainer.blockName,
          layer: groundContainer.layer,
          tier,
          _original: groundContainer._original,
        })
      }
    }
  }

  return result
}

// Container data from backend
export interface ContainerData {
  id: number
  container_number: string
  status: 'LADEN' | 'EMPTY'
  container_type: '20GP' | '40GP' | '40HC'
  entry_time?: string
  company_name?: string
  dwell_days?: number
}

// Combined container info for rendering
export interface Container3D extends ContainerPosition {
  data?: ContainerData
  color: THREE.Color
  isSelected: boolean
  isHovered: boolean
}

// Premium visual color palette (from Hero3DView - creates variety)
export const VISUAL_CONTAINER_PALETTE = [
  new THREE.Color(0x0077B6),   // Deep Blue
  new THREE.Color(0x00B4D8),   // Light Cyan
  new THREE.Color(0x023E8A),   // Navy
  new THREE.Color(0x48CAE4),   // Sky Blue
  new THREE.Color(0x90E0EF),   // Light Blue
  new THREE.Color(0xF97316),   // Orange accent
]

// Functional color schemes (for status/dwell modes)
export const CONTAINER_COLORS = {
  // Status colors (premium blue palette)
  laden: new THREE.Color(0x0077B6),    // Deep Blue
  empty: new THREE.Color(0xF97316),    // Orange
  unknown: new THREE.Color(0x8c8c8c),  // Gray

  // Selection colors (always override visual colors)
  selected: new THREE.Color(0x52c41a), // Green
  hovered: new THREE.Color(0x48CAE4),  // Sky Blue

  // Dwell time colors (heat map)
  dwellLow: new THREE.Color(0x52c41a),    // Green (0-7 days)
  dwellMedium: new THREE.Color(0xfaad14), // Yellow (7-14 days)
  dwellHigh: new THREE.Color(0xf5222d),   // Red (14+ days)
}

// Standard container dimensions in meters
export const CONTAINER_DIMENSIONS = {
  '20GP': { length: 6.058, width: 2.438, height: 2.591 },
  '40GP': { length: 12.192, width: 2.438, height: 2.591 },
  '40HC': { length: 12.192, width: 2.438, height: 2.896 },
}

export type ColorMode = 'status' | 'dwell' | 'company' | 'visual'

export interface UseContainers3DOptions {
  /** Scale factor for coordinates (default: 1.0 for meters, or from DXF) */
  scale?: number
  /** Center point for coordinate transformation (if not using coordinateSystem) */
  center?: { x: number; y: number }
  /** DXF coordinate system for alignment with infrastructure */
  coordinateSystem?: DxfCoordinateSystem
  /** Initial color mode */
  colorMode?: ColorMode
  /** Default container type for sizing */
  defaultContainerType?: keyof typeof CONTAINER_DIMENSIONS
}

const DEFAULT_OPTIONS: Required<Omit<UseContainers3DOptions, 'coordinateSystem'>> = {
  scale: 1.0,  // Default to meters (matching DXF INSUNITS=6)
  center: { x: 0, y: 0 },
  colorMode: 'status',
  defaultContainerType: '40GP',
}

// Runtime options type (coordinateSystem is optional)
type ContainerOptions = typeof DEFAULT_OPTIONS & { coordinateSystem?: DxfCoordinateSystem }

export function useContainers3D(
  positionsRef: Ref<ContainerPosition[]>,
  dataRef: Ref<ContainerData[]> = ref([])
) {
  // Options
  const options = ref<ContainerOptions>({ ...DEFAULT_OPTIONS })

  // Three.js objects
  const containerMesh = shallowRef<THREE.InstancedMesh | null>(null)
  const outlineMesh = shallowRef<THREE.InstancedMesh | null>(null)
  const stripMesh = shallowRef<THREE.InstancedMesh | null>(null)  // White ID strips
  const containerGroup = shallowRef<THREE.Group | null>(null)

  // State
  const colorMode = ref<ColorMode>('visual')  // Default to visual mode for colorful display
  const selectedIds = ref<Set<number>>(new Set())
  const hoveredId = ref<number | null>(null)

  // Simple string hash for consistent company colors
  function hashString(str: string): number {
    let hash = 0
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i)
      hash |= 0
    }
    return Math.abs(hash)
  }

  // Get visual color for container (ID-based for consistent variety)
  function getVisualColor(containerId: number): THREE.Color {
    const colorIndex = containerId % VISUAL_CONTAINER_PALETTE.length
    return VISUAL_CONTAINER_PALETTE[colorIndex]!.clone()
  }

  // Get color based on mode
  function getContainerColor(data: ContainerData, mode: ColorMode): THREE.Color {
    switch (mode) {
      case 'status':
        return data.status === 'LADEN' ? CONTAINER_COLORS.laden : CONTAINER_COLORS.empty

      case 'dwell':
        const days = data.dwell_days ?? 0
        if (days <= 7) return CONTAINER_COLORS.dwellLow
        if (days <= 14) return CONTAINER_COLORS.dwellMedium
        return CONTAINER_COLORS.dwellHigh

      case 'company':
        // Generate consistent color from company name
        if (!data.company_name) return CONTAINER_COLORS.unknown
        const hash = hashString(data.company_name)
        return new THREE.Color().setHSL((hash % 360) / 360, 0.7, 0.5)

      case 'visual':
        // Use ID-based color from visual palette for consistent variety
        return getVisualColor(data.id)

      default:
        return CONTAINER_COLORS.unknown
    }
  }

  // Computed: merged container data
  const containers = computed<Container3D[]>(() => {
    return positionsRef.value.map(pos => {
      // Find matching backend data by ID
      const data = dataRef.value.find(d => d.id === pos.id)

      // Determine color based on mode and state
      let color = CONTAINER_COLORS.unknown
      if (selectedIds.value.has(pos.id)) {
        color = CONTAINER_COLORS.selected
      } else if (hoveredId.value === pos.id) {
        color = CONTAINER_COLORS.hovered
      } else if (colorMode.value === 'visual') {
        // Visual mode: use colorful palette regardless of data
        color = getVisualColor(pos.id)
      } else if (data) {
        color = getContainerColor(data, colorMode.value)
      } else {
        // No data and not visual mode: use visual colors as fallback for variety
        color = getVisualColor(pos.id)
      }

      return {
        ...pos,
        data,
        color,
        isSelected: selectedIds.value.has(pos.id),
        isHovered: hoveredId.value === pos.id,
      }
    })
  })

  /**
   * Initialize container meshes
   */
  function createContainerMeshes(opts: UseContainers3DOptions = {}): THREE.Group {
    // Merge options, using coordinateSystem values if provided
    const mergedOpts: ContainerOptions = {
      ...DEFAULT_OPTIONS,
      ...opts,
      // If coordinateSystem provided, use its scale and center
      scale: opts.coordinateSystem?.scale ?? opts.scale ?? DEFAULT_OPTIONS.scale,
      center: opts.coordinateSystem
        ? { x: opts.coordinateSystem.center.x, y: opts.coordinateSystem.center.y }
        : (opts.center ?? DEFAULT_OPTIONS.center),
    }
    options.value = mergedOpts

    // Create group
    const group = new THREE.Group()
    group.name = 'containers'
    containerGroup.value = group

    const positions = positionsRef.value
    if (positions.length === 0) return group

    // Create box geometry for containers (default 40ft)
    const dims = CONTAINER_DIMENSIONS[mergedOpts.defaultContainerType]
    const geometry = new THREE.BoxGeometry(dims.length, dims.height, dims.width)

    // Create PBR material for premium visuals (metallic sheen)
    const material = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.4,
      metalness: 0.3,
      transparent: true,
      opacity: 0.95,
    })

    // Create instanced mesh
    const mesh = new THREE.InstancedMesh(geometry, material, positions.length)
    mesh.name = 'container_boxes'
    mesh.castShadow = true
    mesh.receiveShadow = true

    // Create outline material for selection
    const outlineMaterial = new THREE.MeshBasicMaterial({
      color: 0x000000,
      side: THREE.BackSide,
    })
    const outlineGeometry = new THREE.BoxGeometry(
      dims.length + 0.2,
      dims.height + 0.2,
      dims.width + 0.2
    )
    const outline = new THREE.InstancedMesh(outlineGeometry, outlineMaterial, positions.length)
    outline.name = 'container_outlines'
    outline.visible = false // Only show for selected

    // Create white identification strips (like real container labels)
    const stripGeometry = new THREE.BoxGeometry(2, 0.8, 0.05)
    const stripMaterial = new THREE.MeshStandardMaterial({
      color: 0xFFFFFF,
      roughness: 0.3,
      metalness: 0.1,
    })
    const strips = new THREE.InstancedMesh(stripGeometry, stripMaterial, positions.length)
    strips.name = 'container_strips'
    strips.castShadow = true
    strips.receiveShadow = true

    // Position containers
    const matrix = new THREE.Matrix4()
    const stripMatrix = new THREE.Matrix4()
    const color = new THREE.Color()

    positions.forEach((pos, index) => {
      // Use original DXF coordinates when aligning with DXF infrastructure
      // Otherwise use the pre-centered coordinates
      const useOriginal = mergedOpts.coordinateSystem && pos._original
      const dxfX = useOriginal ? pos._original!.x : pos.x
      const dxfY = useOriginal ? pos._original!.y : pos.y

      // Convert DXF coordinates to Three.js world coordinates
      const worldPos = dxfToWorld(dxfX, dxfY, mergedOpts)

      // DXF rotation: counter-clockwise from +X axis (degrees)
      // Three.js Y rotation: counter-clockwise from +X when viewed from +Y (radians)
      const rotationRad = (pos.rotation * Math.PI) / 180

      // Calculate offset from corner (INSERT point) to center
      // DXF block origin is at corner, we need to offset to container center
      const halfLength = dims.length / 2  // ~6.1m for 40ft
      const halfWidth = dims.width / 2    // ~1.2m

      // Rotate the offset by container rotation angle
      // In DXF: offset is (halfLength, halfWidth) from corner to center
      // After rotation θ (counter-clockwise):
      //   dx = halfLength * cos(θ) - halfWidth * sin(θ)
      //   dy = halfLength * sin(θ) + halfWidth * cos(θ)
      // Convert to Three.js: X stays same, Z = -dy
      const cos = Math.cos(rotationRad)
      const sin = Math.sin(rotationRad)
      const offsetX = halfLength * cos - halfWidth * sin
      const offsetZ = -(halfLength * sin + halfWidth * cos)

      // Final position = INSERT point + rotated offset
      const finalX = worldPos.x + offsetX
      const finalZ = worldPos.z + offsetZ

      // Calculate Y position based on tier (stacking)
      // Tier 1 = ground level, Tier 2+ = stacked on top
      const tier = pos.tier ?? 1
      const yPosition = dims.height / 2 + (tier - 1) * dims.height

      matrix.identity()
      matrix.makeRotationY(rotationRad)
      matrix.setPosition(
        finalX,
        yPosition,
        finalZ
      )

      mesh.setMatrixAt(index, matrix)
      outline.setMatrixAt(index, matrix)

      // Position white strip on front face of container
      // Strip is offset: Y +0.5 (upper area), Z +halfWidth (front face)
      const stripOffsetY = 0.5
      const stripOffsetZ = halfWidth + 0.03  // Slightly in front of container face

      // Rotate strip offset by container rotation
      const stripLocalX = 0
      const stripLocalZ = stripOffsetZ
      const stripWorldOffsetX = stripLocalX * cos - stripLocalZ * sin
      const stripWorldOffsetZ = -(stripLocalX * sin + stripLocalZ * cos)

      stripMatrix.identity()
      stripMatrix.makeRotationY(rotationRad)
      stripMatrix.setPosition(
        finalX + stripWorldOffsetX,
        yPosition + stripOffsetY,
        finalZ + stripWorldOffsetZ
      )
      strips.setMatrixAt(index, stripMatrix)

      // Set initial color
      const container = containers.value[index]
      color.copy(container?.color ?? CONTAINER_COLORS.unknown)
      mesh.setColorAt(index, color)
    })

    mesh.instanceMatrix.needsUpdate = true
    outline.instanceMatrix.needsUpdate = true
    strips.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true

    containerMesh.value = mesh
    outlineMesh.value = outline
    stripMesh.value = strips

    group.add(mesh)
    group.add(outline)
    group.add(strips)

    return group
  }

  /**
   * Convert DXF coordinates to Three.js world coordinates
   * For containers with pre-centered coordinates, center should be {x:0, y:0}
   */
  function dxfToWorld(
    dxfX: number,
    dxfY: number,
    opts: ContainerOptions = options.value
  ): THREE.Vector3 {
    // Ensure scale is valid (fallback to 1 if undefined/NaN)
    const scale = typeof opts.scale === 'number' && Number.isFinite(opts.scale) ? opts.scale : 1
    const centerX = typeof opts.center.x === 'number' && Number.isFinite(opts.center.x) ? opts.center.x : 0
    const centerY = typeof opts.center.y === 'number' && Number.isFinite(opts.center.y) ? opts.center.y : 0

    const x = (dxfX - centerX) * scale
    const z = -(dxfY - centerY) * scale

    // Validate result
    if (!Number.isFinite(x) || !Number.isFinite(z)) {
      console.warn('⚠️ dxfToWorld produced NaN:', { dxfX, dxfY, opts, x, z })
      return new THREE.Vector3(0, 0, 0)
    }

    return new THREE.Vector3(x, 0, z)
  }

  /**
   * Update center point (call after DXF loads)
   */
  function setCenter(center: { x: number; y: number }): void {
    options.value.center = center
    // Recreate meshes with new center
    if (containerGroup.value) {
      dispose()
      createContainerMeshes(options.value)
    }
  }

  /**
   * Update container colors
   */
  function updateColors(): void {
    if (!containerMesh.value) return

    const color = new THREE.Color()
    containers.value.forEach((container, index) => {
      color.copy(container.color)
      containerMesh.value!.setColorAt(index, color)
    })

    if (containerMesh.value.instanceColor) {
      containerMesh.value.instanceColor.needsUpdate = true
    }
  }

  /**
   * Set color mode
   */
  function setColorMode(mode: ColorMode): void {
    colorMode.value = mode
    updateColors()
  }

  /**
   * Select a container by ID
   */
  function selectContainer(id: number, additive: boolean = false): void {
    if (!additive) {
      selectedIds.value.clear()
    }
    selectedIds.value.add(id)
    updateColors()
    updateOutlines()
  }

  /**
   * Deselect a container
   */
  function deselectContainer(id: number): void {
    selectedIds.value.delete(id)
    updateColors()
    updateOutlines()
  }

  /**
   * Clear all selections
   */
  function clearSelection(): void {
    selectedIds.value.clear()
    updateColors()
    updateOutlines()
  }

  /**
   * Set hovered container
   */
  function setHovered(id: number | null): void {
    if (hoveredId.value !== id) {
      hoveredId.value = id
      updateColors()
    }
  }

  /**
   * Update outline visibility for selected containers
   */
  function updateOutlines(): void {
    if (!outlineMesh.value) return

    // Show outline only for selected containers
    outlineMesh.value.visible = selectedIds.value.size > 0

    // Could also update individual instance visibility here if needed
  }

  /**
   * Get container at raycast intersection
   */
  function getContainerAtIntersection(intersection: THREE.Intersection): Container3D | null {
    if (intersection.object !== containerMesh.value) return null
    if (intersection.instanceId === undefined) return null

    return containers.value[intersection.instanceId] ?? null
  }

  /**
   * Get container by ID
   */
  function getContainerById(id: number): Container3D | null {
    return containers.value.find(c => c.id === id) ?? null
  }

  /**
   * Get world position of a container
   */
  function getContainerWorldPosition(id: number): THREE.Vector3 | null {
    const container = getContainerById(id)
    if (!container) return null
    return dxfToWorld(container.x, container.y)
  }

  /**
   * Dispose of all resources
   */
  function dispose(): void {
    if (containerMesh.value) {
      containerMesh.value.geometry.dispose()
      if (containerMesh.value.material instanceof THREE.Material) {
        containerMesh.value.material.dispose()
      }
      containerMesh.value = null
    }

    if (outlineMesh.value) {
      outlineMesh.value.geometry.dispose()
      if (outlineMesh.value.material instanceof THREE.Material) {
        outlineMesh.value.material.dispose()
      }
      outlineMesh.value = null
    }

    if (stripMesh.value) {
      stripMesh.value.geometry.dispose()
      if (stripMesh.value.material instanceof THREE.Material) {
        stripMesh.value.material.dispose()
      }
      stripMesh.value = null
    }

    if (containerGroup.value) {
      containerGroup.value.clear()
      containerGroup.value = null
    }

    selectedIds.value.clear()
    hoveredId.value = null
  }

  // Watch for data changes and update colors
  watch([positionsRef, dataRef, colorMode], () => {
    updateColors()
  }, { deep: true })

  return {
    // Three.js objects
    containerMesh,
    outlineMesh,
    containerGroup,

    // State
    containers,
    colorMode,
    selectedIds,
    hoveredId,

    // Methods
    createContainerMeshes,
    setCenter,
    setColorMode,
    updateColors,
    selectContainer,
    deselectContainer,
    clearSelection,
    setHovered,
    getContainerAtIntersection,
    getContainerById,
    getContainerWorldPosition,
    dxfToWorld,
    dispose,
  }
}
