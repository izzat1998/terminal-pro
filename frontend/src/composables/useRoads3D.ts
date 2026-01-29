/**
 * Roads & Sidewalks 3D Rendering Composable
 * Renders roads as surface planes with curbs, and sidewalks as elevated paths
 */

import { ref, shallowRef, type Ref } from 'vue'
import * as THREE from 'three'
import type { DxfCoordinateSystem } from '@/types/dxf'
import {
  dxfToWorld as dxfToWorldUtil,
  type CoordinateTransformOptions
} from '@/utils/coordinateTransforms'
import { mergeBufferGeometries } from '@/utils/geometryUtils'

// Road segment data from extraction
export interface RoadSegment {
  id: number
  handle?: string
  type: 'line' | 'polyline' | 'arc'
  points: { x: number; y: number }[]
  length: number
  bounds: { minX: number; maxX: number; minY: number; maxY: number }
  closed?: boolean
}

// Sidewalk data from extraction
export interface SidewalkData {
  id: number
  handle?: string
  type: 'polygon' | 'path'
  vertices: { x: number; y: number }[]
  centroid: { x: number; y: number }
  bounds: { minX: number; maxX: number; minY: number; maxY: number }
  length: number
  area: number
  closed: boolean
}

// Color scheme
export const ROAD_COLORS = {
  road: 0x505050,        // Dark gray asphalt
  curb: 0x808080,        // Light gray concrete curb
  sidewalk: 0xb0b0b0,    // Lighter gray for sidewalks
  marking: 0xffffff,     // White road markings
}

// Dimensions
const ROAD_WIDTH = 6.0          // meters (standard road width)
const CURB_WIDTH = 0.2          // meters
const CURB_HEIGHT = 0.15        // meters
const SIDEWALK_HEIGHT = 0.1     // meters (slight elevation)
const SIDEWALK_WIDTH = 2.0      // meters for path-type sidewalks

export interface UseRoads3DOptions {
  /** Scale factor for coordinates */
  scale?: number
  /** Center point for coordinate transformation */
  center?: { x: number; y: number }
  /** DXF coordinate system for alignment */
  coordinateSystem?: DxfCoordinateSystem
  /** Road width in meters */
  roadWidth?: number
  /** Whether to render curbs */
  showCurbs?: boolean
}

const DEFAULT_OPTIONS = {
  scale: 1.0,
  center: { x: 0, y: 0 },
  roadWidth: ROAD_WIDTH,
  showCurbs: true,
}

type RoadOptions = typeof DEFAULT_OPTIONS & { coordinateSystem?: DxfCoordinateSystem }

export function useRoads3D(
  roadsRef: Ref<RoadSegment[]>,
  sidewalksRef: Ref<SidewalkData[]>
) {
  // Options
  const options = ref<RoadOptions>({ ...DEFAULT_OPTIONS })

  // Three.js objects
  const roadsGroup = shallowRef<THREE.Group | null>(null)
  const roadMesh = shallowRef<THREE.Mesh | null>(null)
  const curbMesh = shallowRef<THREE.Mesh | null>(null)
  const sidewalkMesh = shallowRef<THREE.Mesh | null>(null)

  // State
  const roadsVisible = ref(true)
  const sidewalksVisible = ref(true)

  /**
   * Convert DXF coordinates to Three.js world coordinates
   * (Wrapper around central utility for convenience)
   */
  function dxfToWorld(
    dxfX: number,
    dxfY: number,
    opts: RoadOptions = options.value
  ): THREE.Vector3 {
    const transformOpts: CoordinateTransformOptions = {
      scale: opts.scale,
      center: opts.center,
    }
    return dxfToWorldUtil(dxfX, dxfY, transformOpts) ?? new THREE.Vector3(0, 0, 0)
  }

  /**
   * Create road surface geometry for a segment (as a ribbon/strip)
   */
  function createRoadSurfaceGeometry(
    points: { x: number; y: number }[],
    width: number,
    opts: RoadOptions
  ): THREE.BufferGeometry | null {
    if (points.length < 2) return null

    const vertices: number[] = []
    const indices: number[] = []
    const normals: number[] = []

    // Convert all points to world coordinates
    const worldPoints = points.map(p => dxfToWorld(p.x, p.y, opts))

    // Create ribbon geometry by extruding along path
    for (let i = 0; i < worldPoints.length; i++) {
      const curr = worldPoints[i]
      if (!curr) continue

      // Calculate direction
      let dir: THREE.Vector3
      if (i === 0) {
        const next = worldPoints[i + 1]
        if (!next) continue
        dir = new THREE.Vector3().subVectors(next, curr).normalize()
      } else if (i === worldPoints.length - 1) {
        const prev = worldPoints[i - 1]
        if (!prev) continue
        dir = new THREE.Vector3().subVectors(curr, prev).normalize()
      } else {
        const prev = worldPoints[i - 1]
        const next = worldPoints[i + 1]
        if (!prev || !next) continue
        // Average direction for smooth corners
        const d1 = new THREE.Vector3().subVectors(curr, prev).normalize()
        const d2 = new THREE.Vector3().subVectors(next, curr).normalize()
        dir = d1.add(d2).normalize()
      }

      // Perpendicular direction (for width)
      const perp = new THREE.Vector3(-dir.z, 0, dir.x).multiplyScalar(width / 2)

      // Add left and right vertices
      const left = curr.clone().add(perp)
      const right = curr.clone().sub(perp)

      vertices.push(left.x, 0.01, left.z)   // Slightly above ground to avoid z-fighting
      vertices.push(right.x, 0.01, right.z)

      normals.push(0, 1, 0)
      normals.push(0, 1, 0)

      // Create triangles (except for first point)
      if (i > 0) {
        const baseIdx = (i - 1) * 2
        // Two triangles forming a quad
        indices.push(baseIdx, baseIdx + 2, baseIdx + 1)
        indices.push(baseIdx + 1, baseIdx + 2, baseIdx + 3)
      }
    }

    if (vertices.length < 6) return null

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3))
    geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3))
    geometry.setIndex(indices)

    return geometry
  }

  /**
   * Create curb geometry along a path
   */
  function createCurbGeometry(
    points: { x: number; y: number }[],
    roadWidth: number,
    side: 'left' | 'right',
    opts: RoadOptions
  ): THREE.BufferGeometry | null {
    if (points.length < 2) return null

    const vertices: number[] = []
    const indices: number[] = []

    const worldPoints = points.map(p => dxfToWorld(p.x, p.y, opts))
    const offset = (roadWidth / 2) * (side === 'left' ? 1 : -1)

    for (let i = 0; i < worldPoints.length; i++) {
      const curr = worldPoints[i]
      if (!curr) continue

      // Calculate direction
      let dir: THREE.Vector3
      if (i === 0) {
        const next = worldPoints[i + 1]
        if (!next) continue
        dir = new THREE.Vector3().subVectors(next, curr).normalize()
      } else if (i === worldPoints.length - 1) {
        const prev = worldPoints[i - 1]
        if (!prev) continue
        dir = new THREE.Vector3().subVectors(curr, prev).normalize()
      } else {
        const prev = worldPoints[i - 1]
        const next = worldPoints[i + 1]
        if (!prev || !next) continue
        const d1 = new THREE.Vector3().subVectors(curr, prev).normalize()
        const d2 = new THREE.Vector3().subVectors(next, curr).normalize()
        dir = d1.add(d2).normalize()
      }

      // Perpendicular direction
      const perp = new THREE.Vector3(-dir.z, 0, dir.x)

      // Curb position (offset from road center)
      const curbCenter = curr.clone().add(perp.clone().multiplyScalar(offset))

      // Four vertices per point: inner bottom, outer bottom, outer top, inner top
      const innerOffset = perp.clone().multiplyScalar(-CURB_WIDTH / 2 * (side === 'left' ? 1 : -1))
      const outerOffset = perp.clone().multiplyScalar(CURB_WIDTH / 2 * (side === 'left' ? 1 : -1))

      const innerBottom = curbCenter.clone().add(innerOffset)
      const outerBottom = curbCenter.clone().add(outerOffset)
      const outerTop = outerBottom.clone().setY(CURB_HEIGHT)
      const innerTop = innerBottom.clone().setY(CURB_HEIGHT)

      vertices.push(
        innerBottom.x, innerBottom.y, innerBottom.z,
        outerBottom.x, outerBottom.y, outerBottom.z,
        outerTop.x, outerTop.y, outerTop.z,
        innerTop.x, innerTop.y, innerTop.z
      )

      // Create faces (except for first point)
      if (i > 0) {
        const baseIdx = (i - 1) * 4
        // Top face
        indices.push(baseIdx + 3, baseIdx + 7, baseIdx + 6)
        indices.push(baseIdx + 3, baseIdx + 6, baseIdx + 2)
        // Outer face
        indices.push(baseIdx + 1, baseIdx + 5, baseIdx + 6)
        indices.push(baseIdx + 1, baseIdx + 6, baseIdx + 2)
        // Inner face
        indices.push(baseIdx + 0, baseIdx + 3, baseIdx + 7)
        indices.push(baseIdx + 0, baseIdx + 7, baseIdx + 4)
      }
    }

    if (vertices.length < 8) return null

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3))
    geometry.setIndex(indices)
    geometry.computeVertexNormals()

    return geometry
  }

  /**
   * Create sidewalk surface geometry
   */
  function createSidewalkGeometry(
    sidewalk: SidewalkData,
    opts: RoadOptions
  ): THREE.BufferGeometry | null {
    const vertices = sidewalk.vertices
    if (vertices.length < 3) return null

    if (sidewalk.closed && sidewalk.type === 'polygon') {
      // Create filled polygon using Shape
      const shape = new THREE.Shape()
      const firstVertex = vertices[0]
      if (!firstVertex) return null

      const firstWorld = dxfToWorld(firstVertex.x, firstVertex.y, opts)
      shape.moveTo(firstWorld.x, -firstWorld.z)

      for (let i = 1; i < vertices.length; i++) {
        const vertex = vertices[i]
        if (!vertex) continue
        const world = dxfToWorld(vertex.x, vertex.y, opts)
        shape.lineTo(world.x, -world.z)
      }
      shape.closePath()

      const extrudeSettings: THREE.ExtrudeGeometryOptions = {
        depth: SIDEWALK_HEIGHT,
        bevelEnabled: false,
      }

      const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings)
      geometry.rotateX(-Math.PI / 2)

      return geometry
    } else {
      // Create path-like sidewalk as a ribbon
      return createRoadSurfaceGeometry(vertices, SIDEWALK_WIDTH, opts)
    }
  }

  /**
   * Create all road and sidewalk meshes
   */
  function createRoadMeshes(opts: UseRoads3DOptions = {}): THREE.Group {
    // Merge options
    const coordSys = opts.coordinateSystem
    const mergedOpts: RoadOptions = {
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
    group.name = 'roads_and_sidewalks'
    roadsGroup.value = group

    const roads = roadsRef.value
    const sidewalks = sidewalksRef.value
    const roadWidth = mergedOpts.roadWidth

    // Create road surface geometries
    const roadGeometries: THREE.BufferGeometry[] = []
    const leftCurbGeometries: THREE.BufferGeometry[] = []
    const rightCurbGeometries: THREE.BufferGeometry[] = []

    roads.forEach(segment => {
      const surfaceGeom = createRoadSurfaceGeometry(segment.points, roadWidth, mergedOpts)
      if (surfaceGeom) {
        roadGeometries.push(surfaceGeom)
      }

      if (mergedOpts.showCurbs) {
        const leftCurb = createCurbGeometry(segment.points, roadWidth, 'left', mergedOpts)
        const rightCurb = createCurbGeometry(segment.points, roadWidth, 'right', mergedOpts)
        if (leftCurb) leftCurbGeometries.push(leftCurb)
        if (rightCurb) rightCurbGeometries.push(rightCurb)
      }
    })

    // Merge and create road mesh
    if (roadGeometries.length > 0) {
      const mergedRoad = mergeBufferGeometries(roadGeometries)
      roadGeometries.forEach(g => g.dispose())

      if (mergedRoad) {
        const roadMaterial = new THREE.MeshStandardMaterial({
          color: ROAD_COLORS.road,
          roughness: 0.95,           // Very rough asphalt surface
          metalness: 0.0,
          envMapIntensity: 0.05,     // Minimal reflections
        })
        const mesh = new THREE.Mesh(mergedRoad, roadMaterial)
        mesh.receiveShadow = true
        mesh.name = 'road_surface'
        roadMesh.value = mesh
        group.add(mesh)
      }
    }

    // Merge and create curb meshes
    if (mergedOpts.showCurbs) {
      const allCurbGeometries = [...leftCurbGeometries, ...rightCurbGeometries]
      if (allCurbGeometries.length > 0) {
        const mergedCurb = mergeBufferGeometries(allCurbGeometries)
        allCurbGeometries.forEach(g => g.dispose())

        if (mergedCurb) {
          const curbMaterial = new THREE.MeshStandardMaterial({
            color: ROAD_COLORS.curb,
            roughness: 0.85,           // Concrete curb
            metalness: 0.0,
            envMapIntensity: 0.1,      // Subtle reflections
          })
          const mesh = new THREE.Mesh(mergedCurb, curbMaterial)
          mesh.castShadow = true
          mesh.receiveShadow = true
          mesh.name = 'road_curbs'
          curbMesh.value = mesh
          group.add(mesh)
        }
      }
    }

    // Create sidewalk geometries
    const sidewalkGeometries: THREE.BufferGeometry[] = []

    sidewalks.forEach(sidewalk => {
      const geom = createSidewalkGeometry(sidewalk, mergedOpts)
      if (geom) {
        sidewalkGeometries.push(geom)
      }
    })

    // Merge and create sidewalk mesh
    if (sidewalkGeometries.length > 0) {
      const mergedSidewalk = mergeBufferGeometries(sidewalkGeometries)
      sidewalkGeometries.forEach(g => g.dispose())

      if (mergedSidewalk) {
        const sidewalkMaterial = new THREE.MeshStandardMaterial({
          color: ROAD_COLORS.sidewalk,
          roughness: 0.9,              // Matte concrete sidewalk
          metalness: 0.0,
          envMapIntensity: 0.15,       // Subtle reflections
        })
        const mesh = new THREE.Mesh(mergedSidewalk, sidewalkMaterial)
        mesh.receiveShadow = true
        mesh.name = 'sidewalks'
        sidewalkMesh.value = mesh
        group.add(mesh)
      }
    }

    console.log(`🛣️ Created ${roads.length} road segments and ${sidewalks.length} sidewalks`)

    return group
  }

  /**
   * Toggle roads visibility
   */
  function toggleRoads(visible?: boolean): void {
    const newState = visible ?? !roadsVisible.value
    roadsVisible.value = newState
    if (roadMesh.value) roadMesh.value.visible = newState
    if (curbMesh.value) curbMesh.value.visible = newState
  }

  /**
   * Toggle sidewalks visibility
   */
  function toggleSidewalks(visible?: boolean): void {
    const newState = visible ?? !sidewalksVisible.value
    sidewalksVisible.value = newState
    if (sidewalkMesh.value) sidewalkMesh.value.visible = newState
  }

  /**
   * Toggle all visibility
   */
  function toggleVisibility(visible?: boolean): void {
    const newState = visible ?? (!roadsVisible.value && !sidewalksVisible.value)
    toggleRoads(newState)
    toggleSidewalks(newState)
  }

  /**
   * Dispose of all resources
   */
  function dispose(): void {
    if (roadMesh.value) {
      roadMesh.value.geometry.dispose()
      if (roadMesh.value.material instanceof THREE.Material) {
        roadMesh.value.material.dispose()
      }
      roadMesh.value = null
    }

    if (curbMesh.value) {
      curbMesh.value.geometry.dispose()
      if (curbMesh.value.material instanceof THREE.Material) {
        curbMesh.value.material.dispose()
      }
      curbMesh.value = null
    }

    if (sidewalkMesh.value) {
      sidewalkMesh.value.geometry.dispose()
      if (sidewalkMesh.value.material instanceof THREE.Material) {
        sidewalkMesh.value.material.dispose()
      }
      sidewalkMesh.value = null
    }

    if (roadsGroup.value) {
      roadsGroup.value.clear()
      roadsGroup.value = null
    }
  }

  return {
    // Three.js objects
    roadsGroup,
    roadMesh,
    curbMesh,
    sidewalkMesh,

    // State
    roadsVisible,
    sidewalksVisible,

    // Methods
    createRoadMeshes,
    toggleRoads,
    toggleSidewalks,
    toggleVisibility,
    dispose,
  }
}
