/**
 * Fence 3D Rendering Composable
 * Renders fence segments as thin vertical walls using BufferGeometry
 */

import { ref, shallowRef, type Ref } from 'vue'
import * as THREE from 'three'
import type { DxfCoordinateSystem } from '@/types/dxf'

// Fence segment data from extraction
export interface FenceSegment {
  id: number
  handle?: string
  layer: string
  type: 'line' | 'polyline'
  points: { x: number; y: number }[]
  length: number
  closed?: boolean
}

// Color scheme
export const FENCE_COLORS = {
  default: 0x8b4513,     // Saddle brown (wooden fence look)
  metal: 0x696969,       // Dim gray (metal fence)
  hovered: 0x69c0ff,     // Light blue
}

// Default fence dimensions
const DEFAULT_FENCE_HEIGHT = 2.5  // meters
const DEFAULT_FENCE_THICKNESS = 0.15  // meters

export interface UseFences3DOptions {
  /** Scale factor for coordinates */
  scale?: number
  /** Center point for coordinate transformation */
  center?: { x: number; y: number }
  /** DXF coordinate system for alignment */
  coordinateSystem?: DxfCoordinateSystem
  /** Fence height in meters */
  height?: number
  /** Fence thickness in meters */
  thickness?: number
}

const DEFAULT_OPTIONS = {
  scale: 1.0,
  center: { x: 0, y: 0 },
  height: DEFAULT_FENCE_HEIGHT,
  thickness: DEFAULT_FENCE_THICKNESS,
}

type FenceOptions = typeof DEFAULT_OPTIONS & { coordinateSystem?: DxfCoordinateSystem }

export function useFences3D(
  segmentsRef: Ref<FenceSegment[]>
) {
  // Options
  const options = ref<FenceOptions>({ ...DEFAULT_OPTIONS })

  // Three.js objects
  const fenceGroup = shallowRef<THREE.Group | null>(null)
  const fenceMesh = shallowRef<THREE.Mesh | null>(null)

  // State
  const isVisible = ref(true)

  /**
   * Convert DXF coordinates to Three.js world coordinates
   */
  function dxfToWorld(
    dxfX: number,
    dxfY: number,
    opts: FenceOptions = options.value
  ): THREE.Vector3 {
    const scale = opts.scale ?? 1
    const centerX = opts.center?.x ?? 0
    const centerY = opts.center?.y ?? 0

    const x = (dxfX - centerX) * scale
    const z = -(dxfY - centerY) * scale

    return new THREE.Vector3(x, 0, z)
  }

  /**
   * Create a wall segment between two points
   */
  function createWallGeometry(
    p1: THREE.Vector3,
    p2: THREE.Vector3,
    height: number,
    thickness: number
  ): THREE.BufferGeometry {
    // Direction from p1 to p2
    const dir = new THREE.Vector3().subVectors(p2, p1)
    dir.normalize()

    // Perpendicular direction (for thickness)
    const perp = new THREE.Vector3(-dir.z, 0, dir.x).multiplyScalar(thickness / 2)

    // Four corners at bottom
    const b1 = new THREE.Vector3().addVectors(p1, perp)
    const b2 = new THREE.Vector3().subVectors(p1, perp)
    const b3 = new THREE.Vector3().subVectors(p2, perp)
    const b4 = new THREE.Vector3().addVectors(p2, perp)

    // Four corners at top
    const t1 = b1.clone().setY(height)
    const t2 = b2.clone().setY(height)
    const t3 = b3.clone().setY(height)
    const t4 = b4.clone().setY(height)

    // Create vertices array (8 corners)
    const vertices = new Float32Array([
      // Front face (facing outward from perp direction)
      b1.x, b1.y, b1.z,  // 0
      b4.x, b4.y, b4.z,  // 1
      t4.x, t4.y, t4.z,  // 2
      t1.x, t1.y, t1.z,  // 3

      // Back face
      b2.x, b2.y, b2.z,  // 4
      t2.x, t2.y, t2.z,  // 5
      t3.x, t3.y, t3.z,  // 6
      b3.x, b3.y, b3.z,  // 7

      // Top face
      t1.x, t1.y, t1.z,  // 8
      t4.x, t4.y, t4.z,  // 9
      t3.x, t3.y, t3.z,  // 10
      t2.x, t2.y, t2.z,  // 11

      // Bottom face
      b1.x, b1.y, b1.z,  // 12
      b2.x, b2.y, b2.z,  // 13
      b3.x, b3.y, b3.z,  // 14
      b4.x, b4.y, b4.z,  // 15

      // Left face (start cap)
      b2.x, b2.y, b2.z,  // 16
      b1.x, b1.y, b1.z,  // 17
      t1.x, t1.y, t1.z,  // 18
      t2.x, t2.y, t2.z,  // 19

      // Right face (end cap)
      b4.x, b4.y, b4.z,  // 20
      b3.x, b3.y, b3.z,  // 21
      t3.x, t3.y, t3.z,  // 22
      t4.x, t4.y, t4.z,  // 23
    ])

    // Indices for triangles
    const indices = new Uint16Array([
      // Front
      0, 1, 2, 0, 2, 3,
      // Back
      4, 5, 6, 4, 6, 7,
      // Top
      8, 9, 10, 8, 10, 11,
      // Bottom
      12, 13, 14, 12, 14, 15,
      // Left
      16, 17, 18, 16, 18, 19,
      // Right
      20, 21, 22, 20, 22, 23,
    ])

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3))
    geometry.setIndex(new THREE.BufferAttribute(indices, 1))
    geometry.computeVertexNormals()

    return geometry
  }

  /**
   * Create all fence meshes
   */
  function createFenceMeshes(opts: UseFences3DOptions = {}): THREE.Group {
    // Merge options
    const coordSys = opts.coordinateSystem
    const mergedOpts: FenceOptions = {
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
    group.name = 'fences'
    fenceGroup.value = group

    const segments = segmentsRef.value
    if (segments.length === 0) return group

    const height = mergedOpts.height
    const thickness = mergedOpts.thickness

    // Collect all geometries for merging (better performance)
    const geometries: THREE.BufferGeometry[] = []

    segments.forEach(segment => {
      const points = segment.points
      if (points.length < 2) return

      // Create wall between each pair of consecutive points
      for (let i = 0; i < points.length - 1; i++) {
        const p1World = dxfToWorld(points[i]!.x, points[i]!.y, mergedOpts)
        const p2World = dxfToWorld(points[i + 1]!.x, points[i + 1]!.y, mergedOpts)

        // Skip very short segments
        if (p1World.distanceTo(p2World) < 0.1) continue

        const wallGeom = createWallGeometry(p1World, p2World, height, thickness)
        geometries.push(wallGeom)
      }
    })

    if (geometries.length === 0) return group

    // Merge all geometries into one for better performance
    const mergedGeometry = mergeBufferGeometries(geometries)
    geometries.forEach(g => g.dispose())  // Clean up individual geometries

    if (!mergedGeometry) {
      console.warn('Failed to merge fence geometries')
      return group
    }

    // Create material
    const material = new THREE.MeshStandardMaterial({
      color: FENCE_COLORS.default,
      roughness: 0.9,
      metalness: 0.1,
    })

    // Create mesh
    const mesh = new THREE.Mesh(mergedGeometry, material)
    mesh.castShadow = true
    mesh.receiveShadow = true
    mesh.name = 'fence_walls'
    mesh.userData = { type: 'fence' }

    fenceMesh.value = mesh
    group.add(mesh)

    console.log(`🚧 Created fence mesh with ${segments.length} segments`)

    return group
  }

  /**
   * Simple geometry merge (since BufferGeometryUtils may not be available)
   */
  function mergeBufferGeometries(geometries: THREE.BufferGeometry[]): THREE.BufferGeometry | null {
    if (geometries.length === 0) return null

    // Calculate total vertex count
    let totalVertices = 0
    let totalIndices = 0

    geometries.forEach(geom => {
      const pos = geom.getAttribute('position')
      const idx = geom.getIndex()
      if (pos) totalVertices += pos.count
      if (idx) totalIndices += idx.count
    })

    // Create merged arrays
    const mergedPositions = new Float32Array(totalVertices * 3)
    const mergedNormals = new Float32Array(totalVertices * 3)
    const mergedIndices = new Uint32Array(totalIndices)

    let vertexOffset = 0
    let indexOffset = 0
    let vertexCount = 0

    geometries.forEach(geom => {
      const pos = geom.getAttribute('position') as THREE.BufferAttribute
      const norm = geom.getAttribute('normal') as THREE.BufferAttribute
      const idx = geom.getIndex()

      if (!pos) return

      // Copy positions
      for (let i = 0; i < pos.count; i++) {
        mergedPositions[vertexOffset + i * 3] = pos.getX(i)
        mergedPositions[vertexOffset + i * 3 + 1] = pos.getY(i)
        mergedPositions[vertexOffset + i * 3 + 2] = pos.getZ(i)

        if (norm) {
          mergedNormals[vertexOffset + i * 3] = norm.getX(i)
          mergedNormals[vertexOffset + i * 3 + 1] = norm.getY(i)
          mergedNormals[vertexOffset + i * 3 + 2] = norm.getZ(i)
        }
      }

      // Copy indices (offset by current vertex count)
      if (idx) {
        for (let i = 0; i < idx.count; i++) {
          mergedIndices[indexOffset + i] = idx.getX(i) + vertexCount
        }
        indexOffset += idx.count
      }

      vertexOffset += pos.count * 3
      vertexCount += pos.count
    })

    // Create merged geometry
    const merged = new THREE.BufferGeometry()
    merged.setAttribute('position', new THREE.BufferAttribute(mergedPositions, 3))
    merged.setAttribute('normal', new THREE.BufferAttribute(mergedNormals, 3))
    merged.setIndex(new THREE.BufferAttribute(mergedIndices, 1))

    return merged
  }

  /**
   * Toggle fence visibility
   */
  function toggleVisibility(visible?: boolean): void {
    const newState = visible ?? !isVisible.value
    isVisible.value = newState
    if (fenceGroup.value) {
      fenceGroup.value.visible = newState
    }
  }

  /**
   * Dispose of all resources
   */
  function dispose(): void {
    if (fenceMesh.value) {
      fenceMesh.value.geometry.dispose()
      if (fenceMesh.value.material instanceof THREE.Material) {
        fenceMesh.value.material.dispose()
      }
      fenceMesh.value = null
    }

    if (fenceGroup.value) {
      fenceGroup.value.clear()
      fenceGroup.value = null
    }
  }

  return {
    // Three.js objects
    fenceGroup,
    fenceMesh,

    // State
    isVisible,

    // Methods
    createFenceMeshes,
    toggleVisibility,
    dispose,
  }
}
