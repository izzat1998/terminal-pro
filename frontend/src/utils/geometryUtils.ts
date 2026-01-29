/**
 * Geometry Utilities for Three.js
 *
 * Centralized geometry operations: merging, creation, disposal.
 * These utilities help reduce code duplication across 3D composables.
 */

import * as THREE from 'three'

export interface MergedMeshOptions {
  material: THREE.Material
  receiveShadow?: boolean
  castShadow?: boolean
  name?: string
}

/**
 * Merge multiple BufferGeometries into a single geometry.
 * This is a simplified implementation that doesn't require BufferGeometryUtils.
 *
 * @param geometries - Array of BufferGeometry to merge
 * @returns Single merged BufferGeometry, or null if no valid geometries
 */
export function mergeBufferGeometries(
  geometries: THREE.BufferGeometry[]
): THREE.BufferGeometry | null {
  // Filter out invalid geometries
  const validGeometries = geometries.filter(
    g => g && g.attributes.position && g.attributes.position.count > 0
  )

  if (validGeometries.length === 0) {
    return null
  }

  // Calculate total vertex and index counts
  let totalVertices = 0
  let totalIndices = 0

  validGeometries.forEach(geom => {
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

  validGeometries.forEach(geom => {
    const pos = geom.getAttribute('position') as THREE.BufferAttribute
    const norm = geom.getAttribute('normal') as THREE.BufferAttribute | null
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
      } else {
        // Default to up normal if not provided
        mergedNormals[vertexOffset + i * 3] = 0
        mergedNormals[vertexOffset + i * 3 + 1] = 1
        mergedNormals[vertexOffset + i * 3 + 2] = 0
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
 * Merge multiple geometries into a single mesh.
 * Automatically disposes source geometries after merging.
 *
 * @param geometries - Array of BufferGeometry to merge
 * @param options - Mesh options (material, shadows, name)
 * @returns Single merged Mesh, or null if no valid geometries
 */
export function createMergedMesh(
  geometries: THREE.BufferGeometry[],
  options: MergedMeshOptions
): THREE.Mesh | null {
  const mergedGeometry = mergeBufferGeometries(geometries)

  if (!mergedGeometry) {
    return null
  }

  // Compute normals for proper lighting if not already set
  mergedGeometry.computeVertexNormals()

  // Create mesh
  const mesh = new THREE.Mesh(mergedGeometry, options.material)
  mesh.receiveShadow = options.receiveShadow ?? true
  mesh.castShadow = options.castShadow ?? false
  mesh.name = options.name ?? 'merged-mesh'

  // Dispose source geometries to free memory
  geometries.forEach(g => {
    if (g) g.dispose()
  })

  return mesh
}

// Geometry caches for commonly used shapes
const boxGeometryCache = new Map<string, THREE.BoxGeometry>()
const cylinderGeometryCache = new Map<string, THREE.CylinderGeometry>()

/**
 * Get a cached box geometry. Creates if not exists.
 * More efficient than creating new BoxGeometry each time for repeated dimensions.
 *
 * @param width - Box width (X axis)
 * @param height - Box height (Y axis)
 * @param depth - Box depth (Z axis)
 * @returns Cached BoxGeometry (do not dispose - managed by cache)
 */
export function getBoxGeometry(
  width: number,
  height: number,
  depth: number
): THREE.BoxGeometry {
  const key = `${width}_${height}_${depth}`

  if (!boxGeometryCache.has(key)) {
    boxGeometryCache.set(key, new THREE.BoxGeometry(width, height, depth))
  }

  return boxGeometryCache.get(key)!
}

/**
 * Get a cached cylinder geometry. Creates if not exists.
 *
 * @param radiusTop - Radius at top of cylinder
 * @param radiusBottom - Radius at bottom of cylinder
 * @param height - Cylinder height
 * @param segments - Number of radial segments (default: 16)
 * @returns Cached CylinderGeometry (do not dispose - managed by cache)
 */
export function getCylinderGeometry(
  radiusTop: number,
  radiusBottom: number,
  height: number,
  segments: number = 16
): THREE.CylinderGeometry {
  const key = `${radiusTop}_${radiusBottom}_${height}_${segments}`

  if (!cylinderGeometryCache.has(key)) {
    cylinderGeometryCache.set(
      key,
      new THREE.CylinderGeometry(radiusTop, radiusBottom, height, segments)
    )
  }

  return cylinderGeometryCache.get(key)!
}

/**
 * Clear geometry caches. Call on dispose to free GPU memory.
 */
export function clearGeometryCaches(): void {
  boxGeometryCache.forEach(g => g.dispose())
  boxGeometryCache.clear()

  cylinderGeometryCache.forEach(g => g.dispose())
  cylinderGeometryCache.clear()
}

/**
 * Create an extruded shape geometry from a polygon outline.
 * Used for buildings, platforms, and other extruded structures.
 *
 * @param points - Polygon outline points (world coordinates, XZ plane)
 * @param height - Extrusion height (Y axis)
 * @param options - Additional extrusion options
 * @returns ExtrudeGeometry rotated to stand upright
 */
export function createExtrudedPolygonGeometry(
  points: Array<{ x: number; z: number }>,
  height: number,
  options: {
    bevelEnabled?: boolean
    bevelSize?: number
    bevelThickness?: number
  } = {}
): THREE.ExtrudeGeometry | null {
  if (points.length < 3) {
    return null
  }

  // Create 2D shape from points
  // Shape uses X,Y coordinates, so we map world X to shape X and world -Z to shape Y
  const shape = new THREE.Shape()

  const firstPoint = points[0]!
  shape.moveTo(firstPoint.x, -firstPoint.z)

  for (let i = 1; i < points.length; i++) {
    const point = points[i]!
    shape.lineTo(point.x, -point.z)
  }
  shape.closePath()

  // Extrude settings
  const extrudeSettings: THREE.ExtrudeGeometryOptions = {
    depth: height,
    bevelEnabled: options.bevelEnabled ?? false,
    bevelSize: options.bevelSize ?? 0.1,
    bevelThickness: options.bevelThickness ?? 0.1,
  }

  const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings)

  // Rotate to stand upright (extrusion is along Z, we want Y)
  geometry.rotateX(-Math.PI / 2)

  return geometry
}
