/**
 * Scene Positions for Gate Camera 3D Visualization
 *
 * Defines gate locations, parking zones, and animation paths.
 * Coordinates are in DXF space (same as containers, buildings).
 * Use transformPosition() to convert to Three.js world coordinates.
 */

import gatePositionsJson from './gatePositions.json'
import type { DxfCoordinateSystem } from '@/types/dxf'

// Types
export interface Position2D {
  x: number
  y: number
}

export interface GateDefinition {
  id: string
  name: string
  nameRu: string
  position: Position2D
  rotation: number        // Degrees, direction vehicle faces when entering
  direction: 'inbound' | 'outbound'
}

export interface ZoneDefinition {
  id: string
  name: string
  nameRu: string
  position: Position2D    // Center of zone
  bounds: {
    width: number         // X dimension in meters
    depth: number         // Y dimension in meters
  }
  capacity: number        // Max vehicles
}

export interface PathDefinition {
  name: string
  waypoints: Position2D[]
  duration: number        // Animation duration in seconds
}

// Parsed data
export const GATES: Record<string, GateDefinition> = gatePositionsJson.gates as Record<string, GateDefinition>
export const ZONES: Record<string, ZoneDefinition> = gatePositionsJson.zones as Record<string, ZoneDefinition>
export const PATHS: Record<string, PathDefinition> = gatePositionsJson.paths as Record<string, PathDefinition>

// Default gate for when no specific gate is specified
export const DEFAULT_GATE_ID = 'main'

/**
 * Transform DXF position to Three.js world coordinates
 *
 * @param dxfPos - Position in DXF coordinates
 * @param coordSystem - Coordinate system from useDxfYard
 * @returns Position in Three.js world space { x, y, z }
 */
export function transformToWorld(
  dxfPos: Position2D,
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
 * Transform a path's waypoints to Three.js world coordinates
 */
export function transformPath(
  path: PathDefinition,
  coordSystem: DxfCoordinateSystem
): { waypoints: { x: number; z: number }[]; duration: number } {
  return {
    waypoints: path.waypoints.map(wp => {
      const world = transformToWorld(wp, coordSystem)
      return { x: world.x, z: world.z }
    }),
    duration: path.duration,
  }
}

/**
 * Get gate position in Three.js world coordinates
 */
export function getGateWorldPosition(
  gateId: string,
  coordSystem: DxfCoordinateSystem
): { x: number; y: number; z: number; rotation: number } | null {
  const gate = GATES[gateId]
  if (!gate) return null

  const world = transformToWorld(gate.position, coordSystem)
  // Convert DXF rotation (CCW from +X) to Three.js rotation (around Y axis)
  const rotation = -gate.rotation * (Math.PI / 180)

  return { ...world, rotation }
}

/**
 * Get zone position in Three.js world coordinates
 */
export function getZoneWorldPosition(
  zoneId: string,
  coordSystem: DxfCoordinateSystem
): { x: number; y: number; z: number; width: number; depth: number } | null {
  const zone = ZONES[zoneId]
  if (!zone) return null

  const world = transformToWorld(zone.position, coordSystem)
  const scale = coordSystem.scale ?? 1.0

  return {
    ...world,
    width: zone.bounds.width * scale,
    depth: zone.bounds.depth * scale,
  }
}

/**
 * Get the path between two points
 */
export function getPath(pathId: string): PathDefinition | null {
  return PATHS[pathId] ?? null
}

/**
 * Find path from gate to zone
 */
export function findPathToZone(gateId: string, zoneId: string): PathDefinition | null {
  const pathId = `${gateId}_to_${zoneId}`
  return PATHS[pathId] ?? null
}
