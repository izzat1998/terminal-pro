/**
 * Coordinate Transformation Utilities
 *
 * Provides bidirectional transforms between DXF and Three.js coordinate systems.
 * DXF uses a 2D plan view (X right, Y up), while Three.js uses 3D (X right, Y up, Z toward camera).
 *
 * Key transformation: DXF Y becomes negative Three.js Z (plan view to 3D conversion)
 */

import * as THREE from 'three'
import type { DxfCoordinateSystem } from '@/types/dxf'

/**
 * Options for coordinate transformation
 */
export interface CoordinateTransformOptions {
  /** Scale factor (default: 1.0) */
  scale?: number
  /** Center point for origin alignment */
  center?: { x: number; y: number }
  /** Full coordinate system (overrides scale and center) */
  coordinateSystem?: DxfCoordinateSystem
}

/**
 * Convert DXF coordinates to Three.js world coordinates
 *
 * @param dxfX - DXF X coordinate
 * @param dxfY - DXF Y coordinate
 * @param options - Transformation options (scale, center, or full coordinateSystem)
 * @returns Three.js Vector3 with Y=0 (ground plane), or null if coordinate system not available
 *
 * @example
 * // With coordinate system
 * const worldPos = dxfToWorld(13016, 73253, { coordinateSystem })
 * // worldPos = Vector3(1782, 0, -257)
 *
 * @example
 * // With explicit scale and center
 * const worldPos = dxfToWorld(100, 200, { scale: 1, center: { x: 0, y: 0 } })
 */
export function dxfToWorld(
  dxfX: number,
  dxfY: number,
  options: CoordinateTransformOptions = {}
): THREE.Vector3 | null {
  // Extract scale and center from options or coordinateSystem
  let scale: number
  let centerX: number
  let centerY: number

  if (options.coordinateSystem) {
    const coord = options.coordinateSystem
    scale = coord.scale ?? 1.0
    centerX = coord.center?.x ?? 0
    centerY = coord.center?.y ?? 0
  } else {
    scale = options.scale ?? 1.0
    centerX = options.center?.x ?? 0
    centerY = options.center?.y ?? 0
  }

  // Validate scale
  if (!Number.isFinite(scale) || scale === 0) {
    scale = 1.0
  }

  // Apply transformation: center, scale, and axis swap
  // DXF Y becomes negative Three.js Z (plan view to 3D conversion)
  const x = (dxfX - centerX) * scale
  const z = -(dxfY - centerY) * scale

  // Validate result
  if (!Number.isFinite(x) || !Number.isFinite(z)) {
    console.warn('⚠️ dxfToWorld produced invalid coordinates:', { dxfX, dxfY, options, x, z })
    return null
  }

  return new THREE.Vector3(x, 0, z)
}

/**
 * Convert Three.js world coordinates to DXF coordinates
 *
 * @param worldX - Three.js world X coordinate
 * @param worldZ - Three.js world Z coordinate (note: Y in Three.js is up, Z is forward)
 * @param options - Transformation options (scale, center, or full coordinateSystem)
 * @returns DXF coordinates { x, y }, or null if coordinate system not available
 *
 * @example
 * const dxfPos = worldToDxf(1782, -257, { coordinateSystem })
 * // dxfPos = { x: 13016, y: 73253 }
 */
export function worldToDxf(
  worldX: number,
  worldZ: number,
  options: CoordinateTransformOptions = {}
): { x: number; y: number } | null {
  // Extract scale and center from options or coordinateSystem
  let scale: number
  let centerX: number
  let centerY: number

  if (options.coordinateSystem) {
    const coord = options.coordinateSystem
    scale = coord.scale ?? 1.0
    centerX = coord.center?.x ?? 0
    centerY = coord.center?.y ?? 0
  } else {
    scale = options.scale ?? 1.0
    centerX = options.center?.x ?? 0
    centerY = options.center?.y ?? 0
  }

  // Validate scale
  if (!Number.isFinite(scale) || scale === 0) {
    return null
  }

  // Reverse transformation: Z is negated when converting back
  const dxfX = worldX / scale + centerX
  const dxfY = -worldZ / scale + centerY

  // Validate result
  if (!Number.isFinite(dxfX) || !Number.isFinite(dxfY)) {
    console.warn('⚠️ worldToDxf produced invalid coordinates:', { worldX, worldZ, options })
    return null
  }

  return { x: Math.round(dxfX), y: Math.round(dxfY) }
}

/**
 * Transform a 2D DXF position to Three.js world coordinates
 * (Alternative signature matching scenePositions.ts transformToWorld)
 *
 * @param dxfPos - Position in DXF coordinates { x, y }
 * @param coordSystem - DXF coordinate system
 * @returns Position in Three.js world space { x, y, z }
 */
export function transformToWorld(
  dxfPos: { x: number; y: number },
  coordSystem: DxfCoordinateSystem
): { x: number; y: number; z: number } {
  const scale = coordSystem.scale ?? 1.0
  const center = coordSystem.center ?? { x: 0, y: 0 }

  // DXF Y becomes negative Three.js Z (plan view to 3D conversion)
  const x = (dxfPos.x - center.x) * scale
  const z = -(dxfPos.y - center.y) * scale

  return { x, y: 0, z }
}

/**
 * Transform an array of DXF points to Three.js world coordinates.
 *
 * @param points - Array of DXF coordinate points
 * @param options - Transformation options
 * @returns Array of Vector3 in world space (filters out null results)
 */
export function dxfPointsToWorld(
  points: Array<{ x: number; y: number }>,
  options: CoordinateTransformOptions = {}
): THREE.Vector3[] {
  return points
    .map(p => dxfToWorld(p.x, p.y, options))
    .filter((v): v is THREE.Vector3 => v !== null)
}

/**
 * Calculate direction vector at a specific index along a path.
 * Handles edge cases for first, last, and middle points.
 *
 * @param points - Array of world-space points
 * @param index - Current point index
 * @returns Normalized direction vector
 */
export function getPathDirection(
  points: THREE.Vector3[],
  index: number
): THREE.Vector3 {
  const len = points.length

  if (len < 2) {
    return new THREE.Vector3(1, 0, 0)  // Default forward
  }

  let dir: THREE.Vector3

  if (index === 0) {
    // First point: direction to next
    dir = new THREE.Vector3().subVectors(points[1]!, points[0]!)
  } else if (index === len - 1) {
    // Last point: direction from previous
    dir = new THREE.Vector3().subVectors(points[len - 1]!, points[len - 2]!)
  } else {
    // Middle point: average of incoming and outgoing directions
    const incoming = new THREE.Vector3().subVectors(points[index]!, points[index - 1]!)
    const outgoing = new THREE.Vector3().subVectors(points[index + 1]!, points[index]!)
    dir = incoming.add(outgoing)
  }

  return dir.normalize()
}

/**
 * Calculate perpendicular (right) vector from a direction on the XZ plane.
 *
 * @param direction - Direction vector (should be normalized)
 * @returns Perpendicular vector pointing "right" relative to direction
 */
export function getPerpendicularXZ(direction: THREE.Vector3): THREE.Vector3 {
  return new THREE.Vector3(-direction.z, 0, direction.x).normalize()
}

/**
 * Calculate rotation angle (radians) from a direction vector on the XZ plane.
 * Returns the angle that would make an object face in the given direction.
 *
 * @param direction - Direction vector
 * @returns Rotation angle in radians around Y axis
 */
export function getRotationFromDirection(direction: THREE.Vector3): number {
  return Math.atan2(direction.x, direction.z)
}
