/**
 * Storage Platform 3D Rendering Composable
 * Renders designated container storage areas as slightly elevated concrete slabs
 */

import { ref, shallowRef, type Ref } from 'vue'
import * as THREE from 'three'
import type { DxfCoordinateSystem } from '@/types/dxf'
import {
  dxfToWorld as dxfToWorldUtil,
  type CoordinateTransformOptions
} from '@/utils/coordinateTransforms'
import { createExtrudedPolygonGeometry } from '@/utils/geometryUtils'

// Platform footprint data from extraction
export interface PlatformData {
  id: number
  handle?: string
  vertices: { x: number; y: number }[]
  centroid: { x: number; y: number }
  bounds: { minX: number; maxX: number; minY: number; maxY: number }
  area: number
  elevation?: number
  label?: string
}

// Color scheme
export const PLATFORM_COLORS = {
  default: 0xc0c0c0,    // Silver gray (concrete)
  hover: 0x69c0ff,      // Light blue
  selected: 0x52c41a,   // Green
  border: 0x808080,     // Darker gray for borders
}

// Default platform dimensions
const DEFAULT_PLATFORM_HEIGHT = 0.15  // meters (slight elevation above ground)

export interface UsePlatforms3DOptions {
  /** Scale factor for coordinates */
  scale?: number
  /** Center point for coordinate transformation */
  center?: { x: number; y: number }
  /** DXF coordinate system for alignment */
  coordinateSystem?: DxfCoordinateSystem
  /** Platform height in meters */
  height?: number
}

const DEFAULT_OPTIONS = {
  scale: 1.0,
  center: { x: 0, y: 0 },
  height: DEFAULT_PLATFORM_HEIGHT,
}

type PlatformOptions = typeof DEFAULT_OPTIONS & { coordinateSystem?: DxfCoordinateSystem }

export function usePlatforms3D(platformsRef: Ref<PlatformData[]>) {
  // Options
  const options = ref<PlatformOptions>({ ...DEFAULT_OPTIONS })

  // Three.js objects
  const platformGroup = shallowRef<THREE.Group | null>(null)
  const platformMeshes = shallowRef<Map<number, THREE.Mesh>>(new Map())

  // State
  const isVisible = ref(true)
  const selectedIds = ref<Set<number>>(new Set())
  const hoveredId = ref<number | null>(null)

  /**
   * Convert DXF coordinates to Three.js world coordinates
   * (Wrapper around central utility for convenience)
   */
  function dxfToWorld(
    dxfX: number,
    dxfY: number,
    opts: PlatformOptions = options.value
  ): THREE.Vector3 {
    const transformOpts: CoordinateTransformOptions = {
      scale: opts.scale,
      center: opts.center,
    }
    return dxfToWorldUtil(dxfX, dxfY, transformOpts) ?? new THREE.Vector3(0, 0, 0)
  }

  /**
   * Create a platform mesh from footprint vertices
   */
  function createPlatformMesh(
    platform: PlatformData,
    opts: PlatformOptions
  ): THREE.Mesh | null {
    const vertices = platform.vertices
    if (vertices.length < 3) {
      console.warn(`Platform ${platform.id} has fewer than 3 vertices, skipping`)
      return null
    }

    // Transform vertices to world coordinates
    const worldPoints: Array<{ x: number; z: number }> = []
    for (const vertex of vertices) {
      const world = dxfToWorld(vertex.x, vertex.y, opts)
      worldPoints.push({ x: world.x, z: world.z })
    }

    // Create extruded geometry using utility
    const height = opts.height
    const geometry = createExtrudedPolygonGeometry(worldPoints, height, { bevelEnabled: false })

    if (!geometry) {
      console.warn(`Platform ${platform.id} failed to create geometry`)
      return null
    }

    // Create material with slight transparency
    const material = new THREE.MeshStandardMaterial({
      color: PLATFORM_COLORS.default,
      roughness: 0.9,
      metalness: 0.1,
      transparent: true,
      opacity: 0.8,
    })

    const mesh = new THREE.Mesh(geometry, material)
    mesh.receiveShadow = true
    mesh.name = `platform_${platform.id}`
    mesh.userData = { type: 'storage_platform', platformId: platform.id }

    return mesh
  }

  /**
   * Create all platform meshes
   */
  function createPlatformMeshes(opts: UsePlatforms3DOptions = {}): THREE.Group {
    // Merge options
    const coordSys = opts.coordinateSystem
    const mergedOpts: PlatformOptions = {
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
    group.name = 'storage_platforms'
    platformGroup.value = group

    const platforms = platformsRef.value
    if (platforms.length === 0) return group

    // Create mesh for each platform
    const meshMap = new Map<number, THREE.Mesh>()

    platforms.forEach(platform => {
      const mesh = createPlatformMesh(platform, mergedOpts)
      if (mesh) {
        meshMap.set(platform.id, mesh)
        group.add(mesh)
      }
    })

    platformMeshes.value = meshMap

    console.log(`📦 Created ${meshMap.size} storage platform meshes`)

    return group
  }

  /**
   * Get color for platform based on state
   */
  function getPlatformColor(platformId: number): number {
    if (selectedIds.value.has(platformId)) {
      return PLATFORM_COLORS.selected
    }
    if (hoveredId.value === platformId) {
      return PLATFORM_COLORS.hover
    }
    return PLATFORM_COLORS.default
  }

  /**
   * Update platform colors based on selection/hover state
   */
  function updateColors(): void {
    platformMeshes.value.forEach((mesh, id) => {
      const material = mesh.material as THREE.MeshStandardMaterial
      material.color.setHex(getPlatformColor(id))
    })
  }

  /**
   * Set hovered platform
   */
  function setHovered(id: number | null): void {
    if (hoveredId.value !== id) {
      hoveredId.value = id
      updateColors()
    }
  }

  /**
   * Toggle platform visibility
   */
  function toggleVisibility(visible?: boolean): void {
    const newState = visible ?? !isVisible.value
    isVisible.value = newState
    if (platformGroup.value) {
      platformGroup.value.visible = newState
    }
  }

  /**
   * Get platform at raycast intersection
   */
  function getPlatformAtIntersection(intersection: THREE.Intersection): PlatformData | null {
    const mesh = intersection.object
    if (mesh.userData?.type !== 'storage_platform') return null

    const platformId = mesh.userData.platformId as number
    return platformsRef.value.find(p => p.id === platformId) ?? null
  }

  /**
   * Dispose of all resources
   */
  function dispose(): void {
    platformMeshes.value.forEach(mesh => {
      mesh.geometry.dispose()
      if (mesh.material instanceof THREE.Material) {
        mesh.material.dispose()
      }
    })
    platformMeshes.value.clear()

    if (platformGroup.value) {
      platformGroup.value.clear()
      platformGroup.value = null
    }

    selectedIds.value.clear()
    hoveredId.value = null
  }

  return {
    // Three.js objects
    platformGroup,
    platformMeshes,

    // State
    isVisible,
    selectedIds,
    hoveredId,

    // Methods
    createPlatformMeshes,
    setHovered,
    toggleVisibility,
    getPlatformAtIntersection,
    updateColors,
    dispose,
  }
}
