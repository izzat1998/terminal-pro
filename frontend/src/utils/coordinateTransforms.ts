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
