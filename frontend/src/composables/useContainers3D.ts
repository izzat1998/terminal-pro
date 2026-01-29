/**
 * Container 3D Rendering Composable
 * Renders interactive 3D container boxes using InstancedMesh
 */

import { ref, shallowRef, computed, watch, type Ref } from 'vue'
import * as THREE from 'three'
import type { DxfCoordinateSystem } from '@/types/dxf'
import { dxfToWorld as dxfToWorldUtil } from '@/utils/coordinateTransforms'
import { disposeObject3D } from '@/utils/threeUtils'

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

// IMO hazmat class codes (International Maritime Dangerous Goods)
export type ImoClass = '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9'

// Container priority levels
export type ContainerPriority = 'NORMAL' | 'HIGH' | 'URGENT'

// Container data from backend
export interface ContainerData {
  id: number
  container_number: string
  status: 'LADEN' | 'EMPTY'
  container_type: '20GP' | '40GP' | '40HC'
  entry_time?: string
  company_name?: string
  dwell_days?: number
  // Hazmat/IMO classification
  imo_class?: ImoClass
  is_hazmat?: boolean
  // Priority
  priority?: ContainerPriority
  // Shipping information
  vessel_name?: string
  booking_number?: string
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

  // 5-tier dwell time colors (enterprise heat map)
  dwellFresh: new THREE.Color(0x22C55E),    // Green (0-3 days) - Свежий
  dwellNormal: new THREE.Color(0x3B82F6),   // Blue (4-7 days) - Нормальный
  dwellAging: new THREE.Color(0xF59E0B),    // Amber (8-14 days) - Стареющий
  dwellOverdue: new THREE.Color(0xF97316),  // Orange (15-21 days) - Просроченный
  dwellCritical: new THREE.Color(0xEF4444), // Red (22+ days) - Критический

  // IMO Hazmat class colors (International Maritime Dangerous Goods)
  imoClass1: new THREE.Color(0xF97316),     // Orange - Explosives
  imoClass2: new THREE.Color(0x22C55E),     // Green - Gases (compressed, liquefied, dissolved)
  imoClass3: new THREE.Color(0xEF4444),     // Red - Flammable Liquids
  imoClass4: new THREE.Color(0xDC2626),     // Red/darker - Flammable Solids
  imoClass5: new THREE.Color(0xFACC15),     // Yellow - Oxidizers
  imoClass6: new THREE.Color(0xF8FAFC),     // White - Toxic/Infectious
  imoClass7: new THREE.Color(0xFDE047),     // Yellow/bright - Radioactive
  imoClass8: new THREE.Color(0x1F2937),     // Dark gray/black - Corrosive
  imoClass9: new THREE.Color(0xE5E7EB),     // Light gray - Miscellaneous
  nonHazmat: new THREE.Color(0x6B7280),     // Gray - Non-hazardous cargo
}

// Dwell time tier definitions for consistent use across components
export const DWELL_TIERS = [
  { maxDays: 3, color: CONTAINER_COLORS.dwellFresh, label: 'Свежий', labelEn: 'Fresh' },
  { maxDays: 7, color: CONTAINER_COLORS.dwellNormal, label: 'Нормальный', labelEn: 'Normal' },
  { maxDays: 14, color: CONTAINER_COLORS.dwellAging, label: 'Стареющий', labelEn: 'Aging' },
  { maxDays: 21, color: CONTAINER_COLORS.dwellOverdue, label: 'Просроченный', labelEn: 'Overdue' },
  { maxDays: Infinity, color: CONTAINER_COLORS.dwellCritical, label: 'Критический', labelEn: 'Critical' },
] as const

// IMO hazmat class definitions for legend display
export const IMO_TIERS = [
  { imoClass: '1' as ImoClass, color: CONTAINER_COLORS.imoClass1, label: 'Взрывчатые', labelEn: 'Explosives' },
  { imoClass: '2' as ImoClass, color: CONTAINER_COLORS.imoClass2, label: 'Газы', labelEn: 'Gases' },
  { imoClass: '3' as ImoClass, color: CONTAINER_COLORS.imoClass3, label: 'Горючие жидкости', labelEn: 'Flammable Liquids' },
  { imoClass: '4' as ImoClass, color: CONTAINER_COLORS.imoClass4, label: 'Горючие твёрдые', labelEn: 'Flammable Solids' },
  { imoClass: '5' as ImoClass, color: CONTAINER_COLORS.imoClass5, label: 'Окислители', labelEn: 'Oxidizers' },
  { imoClass: '6' as ImoClass, color: CONTAINER_COLORS.imoClass6, label: 'Токсичные', labelEn: 'Toxic' },
  { imoClass: '7' as ImoClass, color: CONTAINER_COLORS.imoClass7, label: 'Радиоактивные', labelEn: 'Radioactive' },
  { imoClass: '8' as ImoClass, color: CONTAINER_COLORS.imoClass8, label: 'Коррозионные', labelEn: 'Corrosive' },
  { imoClass: '9' as ImoClass, color: CONTAINER_COLORS.imoClass9, label: 'Прочие опасные', labelEn: 'Miscellaneous' },
  { imoClass: null, color: CONTAINER_COLORS.nonHazmat, label: 'Не опасный', labelEn: 'Non-hazmat' },
] as const

// Standard container dimensions in meters
export const CONTAINER_DIMENSIONS = {
  '20GP': { length: 6.058, width: 2.438, height: 2.591 },
  '40GP': { length: 12.192, width: 2.438, height: 2.591 },
  '40HC': { length: 12.192, width: 2.438, height: 2.896 },
}

/** Resolve container dimensions from blockName */
function getDimsForPosition(pos: ContainerPosition) {
  if (pos.blockName === '20ft') return CONTAINER_DIMENSIONS['20GP']
  if (pos.blockName === '40HC') return CONTAINER_DIMENSIONS['40HC']
  return CONTAINER_DIMENSIONS['40GP']
}

export type ColorMode = 'status' | 'dwell' | 'company' | 'visual' | 'hazmat'

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
  /** Enable edge lines for visual distinction (high/ultra quality) */
  showEdgeLines?: boolean
  /** Edge line opacity (0-1, default: 0.15) */
  edgeLineOpacity?: number
}

const DEFAULT_OPTIONS: Required<Omit<UseContainers3DOptions, 'coordinateSystem'>> = {
  scale: 1.0,  // Default to meters (matching DXF INSUNITS=6)
  center: { x: 0, y: 0 },
  colorMode: 'status',
  defaultContainerType: '40GP',
  showEdgeLines: false,
  edgeLineOpacity: 0.15,
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
  const edgeLinesMesh = shallowRef<THREE.LineSegments | null>(null)  // Edge outlines for visual distinction
  const containerGroup = shallowRef<THREE.Group | null>(null)

  // State
  const colorMode = ref<ColorMode>('visual')  // Default to visual mode for colorful display
  const selectedIds = ref<Set<number>>(new Set())
  const hoveredId = ref<number | null>(null)

  // Lookup: container ID → instance index (rebuilt when positions change)
  const idToIndex = computed(() => {
    const map = new Map<number, number>()
    positionsRef.value.forEach((p, i) => map.set(p.id, i))
    return map
  })

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
        // 5-tier enterprise dwell time coloring
        if (days <= 3) return CONTAINER_COLORS.dwellFresh
        if (days <= 7) return CONTAINER_COLORS.dwellNormal
        if (days <= 14) return CONTAINER_COLORS.dwellAging
        if (days <= 21) return CONTAINER_COLORS.dwellOverdue
        return CONTAINER_COLORS.dwellCritical

      case 'hazmat':
        // IMO hazmat class coloring
        if (!data.is_hazmat || !data.imo_class) {
          return CONTAINER_COLORS.nonHazmat
        }
        switch (data.imo_class) {
          case '1': return CONTAINER_COLORS.imoClass1
          case '2': return CONTAINER_COLORS.imoClass2
          case '3': return CONTAINER_COLORS.imoClass3
          case '4': return CONTAINER_COLORS.imoClass4
          case '5': return CONTAINER_COLORS.imoClass5
          case '6': return CONTAINER_COLORS.imoClass6
          case '7': return CONTAINER_COLORS.imoClass7
          case '8': return CONTAINER_COLORS.imoClass8
          case '9': return CONTAINER_COLORS.imoClass9
          default: return CONTAINER_COLORS.nonHazmat
        }

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
    // Build lookup map once (O(n) instead of O(n²) with .find())
    const dataMap = new Map<number, ContainerData>()
    for (const d of dataRef.value) {
      dataMap.set(d.id, d)
    }

    return positionsRef.value.map(pos => {
      const data = dataMap.get(pos.id)

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

    // Use default (40GP) geometry — 99% of slots are 40ft
    const defaultDims = CONTAINER_DIMENSIONS[mergedOpts.defaultContainerType]
    const geometry = new THREE.BoxGeometry(defaultDims.length, defaultDims.height, defaultDims.width)

    // Create PBR material for premium metallic container look
    // High metalness (0.85) + moderate roughness (0.35) = realistic steel containers
    const material = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.35,        // Slightly smooth for reflections
      metalness: 0.85,        // High metalness for steel look
      envMapIntensity: 0.8,   // Environment reflection strength
      transparent: false,
      flatShading: false,
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
      defaultDims.length + 0.2,
      defaultDims.height + 0.2,
      defaultDims.width + 0.2
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
      const dims = getDimsForPosition(pos)

      // Use original DXF coordinates when aligning with DXF infrastructure
      const useOriginal = mergedOpts.coordinateSystem && pos._original
      const dxfX = useOriginal ? pos._original!.x : pos.x
      const dxfY = useOriginal ? pos._original!.y : pos.y

      // Convert DXF coordinates to Three.js world coordinates
      const worldPos = dxfToWorld(dxfX, dxfY, mergedOpts)

      // DXF rotation → Three.js Y rotation (radians)
      const rotationRad = (pos.rotation * Math.PI) / 180

      // Calculate offset from corner (INSERT point) to center
      // Use per-container dims so 20ft slots get correct offset
      const halfLength = dims.length / 2
      const halfWidth = dims.width / 2

      // Rotate the offset by container rotation angle
      const cos = Math.cos(rotationRad)
      const sin = Math.sin(rotationRad)
      const offsetX = halfLength * cos - halfWidth * sin
      const offsetZ = -(halfLength * sin + halfWidth * cos)

      // Final position = INSERT point + rotated offset
      const finalX = worldPos.x + offsetX
      const finalZ = worldPos.z + offsetZ

      // Y position based on tier (stacking)
      const tier = pos.tier ?? 1
      const yPosition = dims.height / 2 + (tier - 1) * dims.height

      // Simple rotation + translation (geometry is pre-sized)
      matrix.identity()
      matrix.makeRotationY(rotationRad)
      matrix.setPosition(finalX, yPosition, finalZ)

      mesh.setMatrixAt(index, matrix)
      outline.setMatrixAt(index, matrix)

      // Position white strip on front face of container
      const stripOffsetY = 0.5
      const stripOffsetZ = halfWidth + 0.03

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

    // Create edge lines for visual distinction (only if enabled)
    if (mergedOpts.showEdgeLines) {
      const edgeLines = createContainerEdgeLines(
        positions,
        defaultDims,
        mergedOpts,
        containers.value
      )
      if (edgeLines) {
        edgeLinesMesh.value = edgeLines
        group.add(edgeLines)
      }
    }

    return group
  }

  /**
   * Create edge lines for all containers (architectural outlines)
   * Uses EdgesGeometry with 30° threshold to only show significant edges
   */
  function createContainerEdgeLines(
    positions: ContainerPosition[],
    dims: { length: number; width: number; height: number },
    opts: ContainerOptions,
    _containerData: Container3D[]
  ): THREE.LineSegments | null {
    if (positions.length === 0) return null

    // Create edge geometry from box (30° threshold = ~0.52 radians)
    const boxGeometry = new THREE.BoxGeometry(dims.length, dims.height, dims.width)
    const edgeGeometry = new THREE.EdgesGeometry(boxGeometry, 30)
    const edgePositions = edgeGeometry.getAttribute('position')
    const edgeCount = edgePositions.count

    // Create buffer for all edge lines (all containers)
    const totalVertices = positions.length * edgeCount
    const allPositions = new Float32Array(totalVertices * 3)

    // For each container, transform edge vertices to world position
    positions.forEach((pos, containerIndex) => {
      const useOriginal = opts.coordinateSystem && pos._original
      const dxfX = useOriginal ? pos._original!.x : pos.x
      const dxfY = useOriginal ? pos._original!.y : pos.y

      const worldPos = dxfToWorld(dxfX, dxfY, opts)
      const rotationRad = (pos.rotation * Math.PI) / 180
      const posDims = getDimsForPosition(pos)
      const tier = pos.tier ?? 1
      const yPosition = posDims.height / 2 + (tier - 1) * posDims.height

      // Calculate center offset (same as main mesh)
      const halfLength = posDims.length / 2
      const halfWidth = posDims.width / 2
      const cos = Math.cos(rotationRad)
      const sin = Math.sin(rotationRad)
      const offsetX = halfLength * cos - halfWidth * sin
      const offsetZ = -(halfLength * sin + halfWidth * cos)
      const finalX = worldPos.x + offsetX
      const finalZ = worldPos.z + offsetZ

      // Transform each edge vertex
      const baseIndex = containerIndex * edgeCount * 3
      for (let i = 0; i < edgeCount; i++) {
        const localX = edgePositions.getX(i)
        const localY = edgePositions.getY(i)
        const localZ = edgePositions.getZ(i)

        // Rotate around Y axis and translate
        const rotatedX = localX * cos - localZ * sin
        const rotatedZ = localX * sin + localZ * cos

        allPositions[baseIndex + i * 3] = finalX + rotatedX
        allPositions[baseIndex + i * 3 + 1] = yPosition + localY
        allPositions[baseIndex + i * 3 + 2] = finalZ - rotatedZ
      }
    })

    // Create merged geometry
    const mergedGeometry = new THREE.BufferGeometry()
    mergedGeometry.setAttribute('position', new THREE.BufferAttribute(allPositions, 3))

    // Semi-transparent black line material
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x000000,
      transparent: true,
      opacity: opts.edgeLineOpacity,
      depthWrite: false,  // Prevent z-fighting
    })

    const lineSegments = new THREE.LineSegments(mergedGeometry, lineMaterial)
    lineSegments.name = 'container_edge_lines'
    lineSegments.renderOrder = 1  // Render after containers

    // Clean up temporary geometry
    boxGeometry.dispose()
    edgeGeometry.dispose()

    return lineSegments
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
    const result = dxfToWorldUtil(dxfX, dxfY, {
      scale: opts.scale,
      center: opts.center,
      coordinateSystem: opts.coordinateSystem,
    })
    // Fallback to origin if utility returns null (maintains existing behavior)
    return result ?? new THREE.Vector3(0, 0, 0)
  }

  /**
   * Update center point (call after DXF loads)
   * Re-creates meshes and returns the new group so the caller can re-add to scene.
   */
  function setCenter(center: { x: number; y: number }): THREE.Group {
    options.value.center = center
    // Recreate meshes with new center
    if (containerGroup.value) {
      const parent = containerGroup.value.parent
      dispose()
      const newGroup = createContainerMeshes(options.value)
      if (parent) {
        parent.add(newGroup)
      }
      return newGroup
    }
    return createContainerMeshes(options.value)
  }

  /**
   * Update container colors.
   * Respects active highlight — highlighted container gets highlight color,
   * not the computed color from mode/selection/hover.
   */
  function updateColors(): void {
    if (!containerMesh.value) return

    const color = new THREE.Color()
    const hlIdx = highlightedIndex.value
    containers.value.forEach((container, index) => {
      if (index === hlIdx) {
        color.copy(HIGHLIGHT_COLOR)
      } else {
        color.copy(container.color)
      }
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
   * Clear all selections
   */
  function clearSelection(): void {
    selectedIds.value.clear()
    updateColors()
    updateOutlines()
  }

  /**
   * Set hovered container.
   * Optimized: only updates the old and new hovered instances (not all 3000+).
   */
  function setHovered(id: number | null): void {
    const prevId = hoveredId.value
    if (prevId === id) return

    hoveredId.value = id

    if (!containerMesh.value) return

    const color = new THREE.Color()
    const hlIdx = highlightedIndex.value

    // Restore previous hovered container to its normal color
    if (prevId !== null) {
      const prevIndex = idToIndex.value.get(prevId)
      if (prevIndex !== undefined && prevIndex !== hlIdx) {
        const c = containers.value[prevIndex]
        color.copy(c?.color ?? CONTAINER_COLORS.unknown)
        containerMesh.value.setColorAt(prevIndex, color)
      }
    }

    // Apply hover color to new container
    if (id !== null) {
      const newIndex = idToIndex.value.get(id)
      if (newIndex !== undefined && newIndex !== hlIdx) {
        color.copy(CONTAINER_COLORS.hovered)
        containerMesh.value.setColorAt(newIndex, color)
      }
    }

    if (containerMesh.value.instanceColor) {
      containerMesh.value.instanceColor.needsUpdate = true
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
   * Find container by number (partial match, case-insensitive)
   * Returns matching containers with their 3D world positions
   */
  function findContainersByNumber(query: string): Array<{ container: Container3D; position: THREE.Vector3; index: number }> {
    if (!query || query.length < 2) return []
    const q = query.toUpperCase()

    const results: Array<{ container: Container3D; position: THREE.Vector3; index: number }> = []

    containers.value.forEach((c, index) => {
      if (!c.data?.container_number) return
      if (!c.data.container_number.toUpperCase().includes(q)) return

      // Extract 3D position from instance matrix
      const pos = getContainerWorldPosition(index)
      if (pos) {
        results.push({ container: c, position: pos, index })
      }
    })

    return results
  }

  /**
   * Get the world position of a container by its index in the instanced mesh
   */
  function getContainerWorldPosition(index: number): THREE.Vector3 | null {
    if (!containerMesh.value || index < 0 || index >= containerMesh.value.count) return null

    const matrix = new THREE.Matrix4()
    containerMesh.value.getMatrixAt(index, matrix)
    const position = new THREE.Vector3()
    position.setFromMatrixPosition(matrix)
    return position
  }

  // Highlight state — tracked as reactive so updateColors() respects it
  let highlightIntervalId: ReturnType<typeof setInterval> | null = null
  const highlightedIndex = ref<number | null>(null)
  const HIGHLIGHT_COLOR = new THREE.Color(0x00FF88)
  const HIGHLIGHT_DIM = new THREE.Color(0x00CC66)

  /**
   * Highlight a container with a slow pulsing color.
   * The highlight is integrated into updateColors() so it survives
   * any reactive color refresh (hover, selection, color mode change).
   * Returns the world position of the highlighted container.
   */
  function highlightContainer(index: number): THREE.Vector3 | null {
    stopHighlight()

    highlightedIndex.value = index
    const pos = getContainerWorldPosition(index)
    if (!pos || !containerMesh.value) return null

    // Apply highlight immediately via full color update
    updateColors()

    // Slow blink between bright/dim green every 500ms
    let bright = true
    highlightIntervalId = setInterval(() => {
      if (!containerMesh.value || highlightedIndex.value !== index) return
      const c = bright ? HIGHLIGHT_DIM : HIGHLIGHT_COLOR
      bright = !bright
      containerMesh.value.setColorAt(index, c)
      if (containerMesh.value.instanceColor) {
        containerMesh.value.instanceColor.needsUpdate = true
      }
    }, 500)

    return pos
  }

  /**
   * Stop highlight and restore original color
   */
  function stopHighlight(): void {
    if (highlightIntervalId !== null) {
      clearInterval(highlightIntervalId)
      highlightIntervalId = null
    }
    if (highlightedIndex.value !== null) {
      highlightedIndex.value = null
      // Restore via full updateColors — guarantees correct color
      updateColors()
    }
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
   * Dispose of all resources
   */
  function dispose(): void {
    stopHighlight()

    if (containerGroup.value) {
      disposeObject3D(containerGroup.value)
      containerGroup.value.clear()
      containerGroup.value = null
    }

    containerMesh.value = null
    outlineMesh.value = null
    stripMesh.value = null
    edgeLinesMesh.value = null
    selectedIds.value.clear()
    hoveredId.value = null
  }

  // Watch for data/colorMode changes — update colors only
  // Note: positionsRef changes require full rebuild (call createContainerMeshes externally)
  watch([dataRef, colorMode], () => {
    updateColors()
  })

  // Watch for position reference changes (not deep — triggers on new array assignment)
  watch(positionsRef, () => {
    if (containerGroup.value) {
      const parent = containerGroup.value.parent
      dispose()
      const newGroup = createContainerMeshes(options.value)
      if (parent) {
        parent.add(newGroup)
      }
    }
  })

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
    idToIndex,

    // Methods
    createContainerMeshes,
    setCenter,
    setColorMode,
    updateColors,
    selectContainer,
    clearSelection,
    setHovered,
    getContainerAtIntersection,
    findContainersByNumber,
    highlightContainer,
    stopHighlight,
    dxfToWorld,
    dispose,
  }
}
