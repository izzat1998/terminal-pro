/**
 * Railway 3D Rendering Composable
 * Renders railway tracks with parallel rails and wooden sleepers using InstancedMesh
 */

import { ref, shallowRef, type Ref } from 'vue'
import * as THREE from 'three'
import type { DxfCoordinateSystem } from '@/types/dxf'

// Railway track data from extraction
export interface RailwayTrack {
  id: number
  handle?: string
  type: string
  points: { x: number; y: number }[]
  length: number
  bounds: { minX: number; maxX: number; minY: number; maxY: number }
}

// Color scheme
export const RAILWAY_COLORS = {
  rail: 0x4a4a4a,       // Dark gray steel
  sleeper: 0x8b4513,    // Saddle brown (wooden sleepers)
  ballast: 0x808080,    // Gray ballast/gravel
}

// Railway dimensions (Russian broad gauge 1520mm)
const RAIL_GAUGE = 1.52           // Distance between rail centers (meters)
const RAIL_WIDTH = 0.075          // Rail head width
const RAIL_HEIGHT = 0.18          // Rail profile height
const SLEEPER_LENGTH = 2.7        // Sleeper length (across tracks)
const SLEEPER_WIDTH = 0.25        // Sleeper width (along tracks)
const SLEEPER_HEIGHT = 0.15       // Sleeper height
const SLEEPER_SPACING = 0.55      // Distance between sleepers

export interface UseRailway3DOptions {
  /** Scale factor for coordinates */
  scale?: number
  /** Center point for coordinate transformation */
  center?: { x: number; y: number }
  /** DXF coordinate system for alignment */
  coordinateSystem?: DxfCoordinateSystem
}

const DEFAULT_OPTIONS = {
  scale: 1.0,
  center: { x: 0, y: 0 },
}

type RailwayOptions = typeof DEFAULT_OPTIONS & { coordinateSystem?: DxfCoordinateSystem }

export function useRailway3D(tracksRef: Ref<RailwayTrack[]>) {
  // Options
  const options = ref<RailwayOptions>({ ...DEFAULT_OPTIONS })

  // Three.js objects
  const railwayGroup = shallowRef<THREE.Group | null>(null)
  const railMesh = shallowRef<THREE.Mesh | null>(null)
  const sleeperMesh = shallowRef<THREE.InstancedMesh | null>(null)

  // State
  const isVisible = ref(true)

  /**
   * Convert DXF coordinates to Three.js world coordinates
   */
  function dxfToWorld(
    dxfX: number,
    dxfY: number,
    opts: RailwayOptions = options.value
  ): THREE.Vector3 {
    const scale = opts.scale ?? 1
    const centerX = opts.center?.x ?? 0
    const centerY = opts.center?.y ?? 0

    const x = (dxfX - centerX) * scale
    const z = -(dxfY - centerY) * scale

    return new THREE.Vector3(x, 0, z)
  }

  /**
   * Create rail segment geometry between two points
   */
  function createRailSegmentGeometry(
    p1: THREE.Vector3,
    p2: THREE.Vector3,
    offset: number  // Perpendicular offset for left/right rail
  ): THREE.BufferGeometry {
    // Direction from p1 to p2
    const dir = new THREE.Vector3().subVectors(p2, p1).normalize()

    // Perpendicular direction (for offset)
    const perp = new THREE.Vector3(-dir.z, 0, dir.x)

    // Offset positions for this rail
    const offsetVec = perp.clone().multiplyScalar(offset)
    const r1 = p1.clone().add(offsetVec)
    const r2 = p2.clone().add(offsetVec)

    // Create rail profile (simplified I-beam cross-section)
    const halfWidth = RAIL_WIDTH / 2
    const perpHalf = perp.clone().multiplyScalar(halfWidth)

    // Bottom corners
    const b1 = r1.clone().sub(perpHalf)
    const b2 = r1.clone().add(perpHalf)
    const b3 = r2.clone().add(perpHalf)
    const b4 = r2.clone().sub(perpHalf)

    // Top corners
    const t1 = b1.clone().setY(RAIL_HEIGHT)
    const t2 = b2.clone().setY(RAIL_HEIGHT)
    const t3 = b3.clone().setY(RAIL_HEIGHT)
    const t4 = b4.clone().setY(RAIL_HEIGHT)

    // Create vertices array
    const vertices = new Float32Array([
      // Front face
      b1.x, b1.y, b1.z,
      b4.x, b4.y, b4.z,
      t4.x, t4.y, t4.z,
      t1.x, t1.y, t1.z,
      // Back face
      b2.x, b2.y, b2.z,
      t2.x, t2.y, t2.z,
      t3.x, t3.y, t3.z,
      b3.x, b3.y, b3.z,
      // Top face
      t1.x, t1.y, t1.z,
      t4.x, t4.y, t4.z,
      t3.x, t3.y, t3.z,
      t2.x, t2.y, t2.z,
      // Bottom face
      b1.x, b1.y, b1.z,
      b2.x, b2.y, b2.z,
      b3.x, b3.y, b3.z,
      b4.x, b4.y, b4.z,
      // Left cap
      b2.x, b2.y, b2.z,
      b1.x, b1.y, b1.z,
      t1.x, t1.y, t1.z,
      t2.x, t2.y, t2.z,
      // Right cap
      b4.x, b4.y, b4.z,
      b3.x, b3.y, b3.z,
      t3.x, t3.y, t3.z,
      t4.x, t4.y, t4.z,
    ])

    const indices = new Uint16Array([
      0, 1, 2, 0, 2, 3,       // Front
      4, 5, 6, 4, 6, 7,       // Back
      8, 9, 10, 8, 10, 11,    // Top
      12, 13, 14, 12, 14, 15, // Bottom
      16, 17, 18, 16, 18, 19, // Left cap
      20, 21, 22, 20, 22, 23, // Right cap
    ])

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3))
    geometry.setIndex(new THREE.BufferAttribute(indices, 1))
    geometry.computeVertexNormals()

    return geometry
  }

  /**
   * Count total sleepers needed for all tracks
   */
  function countSleepers(tracks: RailwayTrack[], opts: RailwayOptions): number {
    let count = 0
    tracks.forEach(track => {
      const points = track.points
      for (let i = 0; i < points.length - 1; i++) {
        const pt1 = points[i]
        const pt2 = points[i + 1]
        if (!pt1 || !pt2) continue
        const p1 = dxfToWorld(pt1.x, pt1.y, opts)
        const p2 = dxfToWorld(pt2.x, pt2.y, opts)
        const segmentLength = p1.distanceTo(p2)
        count += Math.floor(segmentLength / SLEEPER_SPACING)
      }
    })
    return count
  }

  /**
   * Create all railway meshes
   */
  function createRailwayMeshes(opts: UseRailway3DOptions = {}): THREE.Group {
    // Merge options
    const coordSys = opts.coordinateSystem
    const mergedOpts: RailwayOptions = {
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
    group.name = 'railway'
    railwayGroup.value = group

    const tracks = tracksRef.value
    if (tracks.length === 0) return group

    // Collect all rail geometries for merging
    const railGeometries: THREE.BufferGeometry[] = []

    // Count sleepers for instancing
    const totalSleepers = countSleepers(tracks, mergedOpts)

    // Create sleeper geometry
    const sleeperGeometry = new THREE.BoxGeometry(
      SLEEPER_WIDTH,
      SLEEPER_HEIGHT,
      SLEEPER_LENGTH
    )

    // Create sleeper material
    const sleeperMaterial = new THREE.MeshStandardMaterial({
      color: RAILWAY_COLORS.sleeper,
      roughness: 0.9,
      metalness: 0.0,
    })

    // Create instanced mesh for sleepers
    const sleepers = new THREE.InstancedMesh(
      sleeperGeometry,
      sleeperMaterial,
      totalSleepers
    )
    sleepers.name = 'railway_sleepers'
    sleepers.castShadow = true
    sleepers.receiveShadow = true

    const sleeperMatrix = new THREE.Matrix4()
    let sleeperIndex = 0

    // Process each track
    tracks.forEach(track => {
      const points = track.points
      if (points.length < 2) return

      // Create rail segments between each pair of points
      for (let i = 0; i < points.length - 1; i++) {
        const pt1 = points[i]
        const pt2 = points[i + 1]
        if (!pt1 || !pt2) continue
        const p1 = dxfToWorld(pt1.x, pt1.y, mergedOpts)
        const p2 = dxfToWorld(pt2.x, pt2.y, mergedOpts)

        // Skip very short segments
        if (p1.distanceTo(p2) < 0.1) continue

        // Create left and right rails
        const leftRailGeom = createRailSegmentGeometry(p1, p2, -RAIL_GAUGE / 2)
        const rightRailGeom = createRailSegmentGeometry(p1, p2, RAIL_GAUGE / 2)
        railGeometries.push(leftRailGeom)
        railGeometries.push(rightRailGeom)

        // Add sleepers along this segment
        const segmentLength = p1.distanceTo(p2)
        const dir = new THREE.Vector3().subVectors(p2, p1).normalize()
        const sleeperCount = Math.floor(segmentLength / SLEEPER_SPACING)

        // Calculate rotation angle (align sleeper perpendicular to track)
        const angle = Math.atan2(dir.z, dir.x)

        for (let j = 0; j < sleeperCount; j++) {
          const t = (j + 0.5) * SLEEPER_SPACING / segmentLength
          const pos = p1.clone().lerp(p2, t)

          sleeperMatrix.identity()
          sleeperMatrix.makeRotationY(-angle + Math.PI / 2)
          sleeperMatrix.setPosition(pos.x, SLEEPER_HEIGHT / 2, pos.z)

          sleepers.setMatrixAt(sleeperIndex, sleeperMatrix)
          sleeperIndex++
        }
      }
    })

    sleepers.instanceMatrix.needsUpdate = true
    sleeperMesh.value = sleepers
    group.add(sleepers)

    // Merge all rail geometries
    if (railGeometries.length > 0) {
      const mergedRailGeometry = mergeBufferGeometries(railGeometries)
      railGeometries.forEach(g => g.dispose())

      if (mergedRailGeometry) {
        // Create rail material
        const railMaterial = new THREE.MeshStandardMaterial({
          color: RAILWAY_COLORS.rail,
          roughness: 0.4,
          metalness: 0.8,
        })

        const rails = new THREE.Mesh(mergedRailGeometry, railMaterial)
        rails.name = 'railway_rails'
        rails.castShadow = true
        rails.receiveShadow = true

        railMesh.value = rails
        group.add(rails)
      }
    }

    console.log(`🚂 Created railway with ${tracks.length} tracks, ${sleeperIndex} sleepers`)

    return group
  }

  /**
   * Simple geometry merge
   */
  function mergeBufferGeometries(geometries: THREE.BufferGeometry[]): THREE.BufferGeometry | null {
    if (geometries.length === 0) return null

    let totalVertices = 0
    let totalIndices = 0

    geometries.forEach(geom => {
      const pos = geom.getAttribute('position')
      const idx = geom.getIndex()
      if (pos) totalVertices += pos.count
      if (idx) totalIndices += idx.count
    })

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

      if (idx) {
        for (let i = 0; i < idx.count; i++) {
          mergedIndices[indexOffset + i] = idx.getX(i) + vertexCount
        }
        indexOffset += idx.count
      }

      vertexOffset += pos.count * 3
      vertexCount += pos.count
    })

    const merged = new THREE.BufferGeometry()
    merged.setAttribute('position', new THREE.BufferAttribute(mergedPositions, 3))
    merged.setAttribute('normal', new THREE.BufferAttribute(mergedNormals, 3))
    merged.setIndex(new THREE.BufferAttribute(mergedIndices, 1))

    return merged
  }

  /**
   * Toggle railway visibility
   */
  function toggleVisibility(visible?: boolean): void {
    const newState = visible ?? !isVisible.value
    isVisible.value = newState
    if (railwayGroup.value) {
      railwayGroup.value.visible = newState
    }
  }

  /**
   * Dispose of all resources
   */
  function dispose(): void {
    if (railMesh.value) {
      railMesh.value.geometry.dispose()
      if (railMesh.value.material instanceof THREE.Material) {
        railMesh.value.material.dispose()
      }
      railMesh.value = null
    }

    if (sleeperMesh.value) {
      sleeperMesh.value.geometry.dispose()
      if (sleeperMesh.value.material instanceof THREE.Material) {
        sleeperMesh.value.material.dispose()
      }
      sleeperMesh.value = null
    }

    if (railwayGroup.value) {
      railwayGroup.value.clear()
      railwayGroup.value = null
    }
  }

  return {
    // Three.js objects
    railwayGroup,
    railMesh,
    sleeperMesh,

    // State
    isVisible,

    // Methods
    createRailwayMeshes,
    toggleVisibility,
    dispose,
  }
}
