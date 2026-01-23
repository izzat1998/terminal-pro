/**
 * JSON Coordinate Utilities
 * Convert between DXF JSON coordinates and Three.js world coordinates
 *
 * These functions mirror the coordinate transforms in dxfToThree.ts but work
 * with the pre-computed coordinateSystem from JSON files (avoiding re-parsing DXF)
 */

import type { DxfPoint, DxfCoordinateSystem } from '@/types/dxf'

/**
 * Result of Three.js coordinate transform
 */
export interface ThreeCoordinate {
  x: number
  y: number
  z: number
}

/**
 * Convert DXF JSON coordinates to Three.js world coordinates
 *
 * This applies the same transform as dxfToThree.ts:toThreePoint():
 * - Subtracts center for origin alignment
 * - Applies scale factor
 * - Swaps Y and Z for Three.js (Y up instead of Z up)
 *
 * @param dxfX - X coordinate from JSON entity (DXF coordinate)
 * @param dxfY - Y coordinate from JSON entity (DXF coordinate)
 * @param dxfZ - Z coordinate from JSON entity (DXF coordinate), defaults to 0
 * @param coordSystem - Coordinate system from JSON file
 * @param flatten2D - If true, flattens Z to 0 (default: true)
 * @returns Three.js world coordinates {x, y, z}
 *
 * @example
 * ```ts
 * import { jsonToThreeCoordinates } from '@/utils/jsonCoordinates'
 *
 * // Using coordinateSystem from JSON
 * const entity = json.entities[0]
 * const worldPos = jsonToThreeCoordinates(
 *   entity.center.x,
 *   entity.center.y,
 *   entity.center.z ?? 0,
 *   json.coordinateSystem
 * )
 * mesh.position.set(worldPos.x, worldPos.y, worldPos.z)
 * ```
 */
export function jsonToThreeCoordinates(
  dxfX: number,
  dxfY: number,
  dxfZ: number = 0,
  coordSystem: DxfCoordinateSystem,
  flatten2D: boolean = true
): ThreeCoordinate {
  const centerX = coordSystem.center.x
  const centerY = coordSystem.center.y
  const centerZ = coordSystem.center.z ?? 0
  const scale = coordSystem.scale

  // Apply centering and scale
  const x = (dxfX - centerX) * scale
  const y = (dxfY - centerY) * scale
  const z = flatten2D ? 0 : (dxfZ - centerZ) * scale

  // Swap Y and Z for Three.js coordinate system
  // DXF: Y is up in 2D view, Z is up in 3D
  // Three.js: Y is up
  return {
    x: x,
    y: z,    // DXF Z becomes Three.js Y (up)
    z: -y    // DXF Y becomes negative Three.js Z (depth)
  }
}

/**
 * Convert Three.js world coordinates back to DXF JSON coordinates
 *
 * This is the inverse of jsonToThreeCoordinates(), useful for:
 * - Converting click positions back to DXF coordinates
 * - Saving modifications back to DXF format
 * - Displaying DXF coordinates in UI
 *
 * @param worldX - Three.js world X coordinate
 * @param worldY - Three.js world Y coordinate (up)
 * @param worldZ - Three.js world Z coordinate (depth)
 * @param coordSystem - Coordinate system from JSON file
 * @returns DXF coordinates {x, y, z}
 *
 * @example
 * ```ts
 * import { threeToJsonCoordinates } from '@/utils/jsonCoordinates'
 *
 * // Convert raycast hit point back to DXF coords
 * const dxfCoords = threeToJsonCoordinates(
 *   intersect.point.x,
 *   intersect.point.y,
 *   intersect.point.z,
 *   json.coordinateSystem
 * )
 * console.log(`Clicked at DXF: (${dxfCoords.x}, ${dxfCoords.y})`)
 * ```
 */
export function threeToJsonCoordinates(
  worldX: number,
  worldY: number,
  worldZ: number,
  coordSystem: DxfCoordinateSystem
): DxfPoint {
  const centerX = coordSystem.center.x
  const centerY = coordSystem.center.y
  const centerZ = coordSystem.center.z ?? 0
  const scale = coordSystem.scale

  // Reverse the axis swap: Three.js Y up → DXF Z up, Three.js -Z → DXF Y
  // Then reverse centering and scale
  return {
    x: (worldX / scale) + centerX,
    y: (-worldZ / scale) + centerY,
    z: (worldY / scale) + centerZ
  }
}

/**
 * Convert a DXF point object to Three.js coordinates
 *
 * Convenience wrapper for jsonToThreeCoordinates() that accepts a DxfPoint
 *
 * @param point - DXF point object with x, y, and optional z
 * @param coordSystem - Coordinate system from JSON file
 * @param flatten2D - If true, flattens Z to 0 (default: true)
 * @returns Three.js world coordinates
 */
export function dxfPointToThree(
  point: DxfPoint,
  coordSystem: DxfCoordinateSystem,
  flatten2D: boolean = true
): ThreeCoordinate {
  return jsonToThreeCoordinates(point.x, point.y, point.z ?? 0, coordSystem, flatten2D)
}

/**
 * Convert Three.js coordinates to a DXF point object
 *
 * Convenience wrapper for threeToJsonCoordinates()
 *
 * @param coords - Three.js coordinates {x, y, z}
 * @param coordSystem - Coordinate system from JSON file
 * @returns DXF point object
 */
export function threeToDxfPoint(
  coords: ThreeCoordinate,
  coordSystem: DxfCoordinateSystem
): DxfPoint {
  return threeToJsonCoordinates(coords.x, coords.y, coords.z, coordSystem)
}

/**
 * Get the effective bounds in Three.js world coordinates
 *
 * Converts the DXF coordinate system bounds to Three.js coordinates,
 * useful for camera fitting and scene setup.
 *
 * @param coordSystem - Coordinate system from JSON file
 * @returns Bounds in Three.js coordinates
 */
export function getThreeBounds(coordSystem: DxfCoordinateSystem): {
  min: ThreeCoordinate
  max: ThreeCoordinate
  width: number
  height: number
  center: ThreeCoordinate
} {
  const min = dxfPointToThree(coordSystem.bounds.min, coordSystem)
  const max = dxfPointToThree(coordSystem.bounds.max, coordSystem)

  // After transform, min/max may be swapped on some axes
  const actualMin: ThreeCoordinate = {
    x: Math.min(min.x, max.x),
    y: Math.min(min.y, max.y),
    z: Math.min(min.z, max.z)
  }
  const actualMax: ThreeCoordinate = {
    x: Math.max(min.x, max.x),
    y: Math.max(min.y, max.y),
    z: Math.max(min.z, max.z)
  }

  return {
    min: actualMin,
    max: actualMax,
    width: actualMax.x - actualMin.x,
    height: actualMax.z - actualMin.z,  // In Three.js XZ plane for top-down view
    center: {
      x: (actualMin.x + actualMax.x) / 2,
      y: (actualMin.y + actualMax.y) / 2,
      z: (actualMin.z + actualMax.z) / 2
    }
  }
}
