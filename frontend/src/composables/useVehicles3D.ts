/**
 * Vehicle 3D Management Composable
 *
 * Manages 3D vehicle objects in the yard scene:
 * - Spawning vehicles at gates
 * - Animating along waypoint paths
 * - Floating info labels
 * - Cleanup and disposal
 */

import { shallowRef, type ShallowRef, type Ref } from 'vue'
import * as THREE from 'three'
import { CSS2DObject, CSS2DRenderer } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import { useVehicleModels, type VehicleType, type VehicleModelOptions } from './useVehicleModels'
import {
  transformPath,
  getGateWorldPosition,
  PATHS,
  DEFAULT_GATE_ID,
  type PathDefinition,
} from '@/data/scenePositions'
import type { DxfCoordinateSystem } from '@/types/dxf'

// Vehicle detection event from gate camera
export interface VehicleDetection {
  id: string
  plateNumber: string
  vehicleType: VehicleType
  gateId?: string
  targetZone?: string
  direction?: 'entering' | 'exiting'
}

// Active vehicle in the scene
export interface ActiveVehicle {
  id: string
  mesh: THREE.Group
  plateNumber: string
  vehicleType: VehicleType
  state: 'entering' | 'parked' | 'exiting'
  targetZone: string
  label: CSS2DObject | null
  animationId: number | null
}

/**
 * useVehicles3D composable
 *
 * Manages 3D vehicle lifecycle in the yard scene.
 *
 * @param scene - Three.js scene to add vehicles to
 * @param coordSystem - DXF coordinate system for position transforms
 */
export function useVehicles3D(
  scene: THREE.Scene,
  coordSystem: Ref<DxfCoordinateSystem | null>
) {
  const vehicles: ShallowRef<Map<string, ActiveVehicle>> = shallowRef(new Map())
  const labelRenderer: ShallowRef<CSS2DRenderer | null> = shallowRef(null)

  const { createVehicle, disposeVehicle } = useVehicleModels()

  /**
   * Initialize CSS2D renderer for vehicle labels
   * Must be called after DOM is ready and container is available
   */
  function initLabelRenderer(container: HTMLElement): CSS2DRenderer {
    const renderer = new CSS2DRenderer()
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.domElement.style.position = 'absolute'
    renderer.domElement.style.top = '0'
    renderer.domElement.style.pointerEvents = 'none'
    container.appendChild(renderer.domElement)
    labelRenderer.value = renderer
    return renderer
  }

  /**
   * Update label renderer size on container resize
   */
  function updateLabelRendererSize(width: number, height: number): void {
    if (labelRenderer.value) {
      labelRenderer.value.setSize(width, height)
    }
  }

  /**
   * Render labels (call in animation loop)
   */
  function renderLabels(camera: THREE.Camera): void {
    if (labelRenderer.value) {
      labelRenderer.value.render(scene, camera)
    }
  }

  /**
   * Create floating info label for a vehicle
   */
  function createVehicleLabel(plateNumber: string): CSS2DObject {
    const labelDiv = document.createElement('div')
    labelDiv.className = 'vehicle-label'
    labelDiv.textContent = plateNumber
    labelDiv.style.cssText = `
      background: rgba(0, 0, 0, 0.8);
      color: #00ff88;
      padding: 4px 8px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 600;
      white-space: nowrap;
      text-shadow: 0 0 4px rgba(0, 255, 136, 0.5);
      border: 1px solid rgba(0, 255, 136, 0.3);
    `

    const label = new CSS2DObject(labelDiv)
    label.position.set(0, 5, 0) // Position above vehicle
    label.center.set(0.5, 0)

    return label
  }

  /**
   * Spawn a vehicle at a gate
   *
   * Creates 3D model, positions at gate, adds to scene and tracking Map.
   */
  function spawnVehicle(detection: VehicleDetection): ActiveVehicle | null {
    const coord = coordSystem.value
    if (!coord) {
      console.warn('[useVehicles3D] Coordinate system not ready')
      return null
    }

    // Check if vehicle already exists
    if (vehicles.value.has(detection.id)) {
      console.warn(`[useVehicles3D] Vehicle ${detection.id} already exists`)
      return vehicles.value.get(detection.id) || null
    }

    const gateId = detection.gateId ?? DEFAULT_GATE_ID
    const gatePos = getGateWorldPosition(gateId, coord)
    if (!gatePos) {
      console.warn(`[useVehicles3D] Gate ${gateId} not found`)
      return null
    }

    // Create vehicle model
    const modelOptions: VehicleModelOptions = {
      withChassis: detection.vehicleType === 'TRUCK',
      chassisSize: '40ft',
      scale: 1.0,
    }
    const mesh = createVehicle(detection.vehicleType, modelOptions)
    mesh.name = `vehicle-${detection.id}`

    // Position at gate
    mesh.position.set(gatePos.x, gatePos.y, gatePos.z)
    mesh.rotation.y = gatePos.rotation

    // Add to scene
    scene.add(mesh)

    // Create label
    const label = createVehicleLabel(detection.plateNumber)
    mesh.add(label)

    // Create active vehicle record
    const activeVehicle: ActiveVehicle = {
      id: detection.id,
      mesh,
      plateNumber: detection.plateNumber,
      vehicleType: detection.vehicleType,
      state: detection.direction === 'exiting' ? 'exiting' : 'entering',
      targetZone: detection.targetZone ?? 'waiting',
      label,
      animationId: null,
    }

    // Add to tracking Map
    const newMap = new Map(vehicles.value)
    newMap.set(detection.id, activeVehicle)
    vehicles.value = newMap

    return activeVehicle
  }

  /**
   * Animate vehicle along a path using manual interpolation
   *
   * Smoothly moves vehicle through waypoints with rotation following direction.
   *
   * @returns Promise that resolves when animation completes
   */
  function animateVehicleAlongPath(
    vehicle: ActiveVehicle,
    pathDef: PathDefinition
  ): Promise<void> {
    return new Promise((resolve) => {
      const coord = coordSystem.value
      if (!coord) {
        resolve()
        return
      }

      // Transform path to world coordinates
      const worldPath = transformPath(pathDef, coord)
      if (worldPath.waypoints.length < 2) {
        resolve()
        return
      }

      const { waypoints, duration } = worldPath
      const totalDuration = duration * 1000 // Convert to milliseconds
      const startTime = performance.now()

      // Calculate total path length for even interpolation
      const segmentLengths: number[] = []
      let totalLength = 0
      for (let i = 0; i < waypoints.length - 1; i++) {
        const current = waypoints[i]
        const next = waypoints[i + 1]
        if (current && next) {
          const dx = next.x - current.x
          const dz = next.z - current.z
          const length = Math.sqrt(dx * dx + dz * dz)
          segmentLengths.push(length)
          totalLength += length
        }
      }

      // Animation frame function
      function animate(currentTime: number): void {
        const elapsed = currentTime - startTime
        const progress = Math.min(elapsed / totalDuration, 1.0)

        // Find current position along path
        const targetDistance = progress * totalLength
        let accumulatedDistance = 0
        let segmentIndex = 0

        for (let i = 0; i < segmentLengths.length; i++) {
          const segmentLen = segmentLengths[i]
          if (segmentLen !== undefined && accumulatedDistance + segmentLen >= targetDistance) {
            segmentIndex = i
            break
          }
          if (segmentLen !== undefined) {
            accumulatedDistance += segmentLen
          }
        }

        // Interpolate within current segment
        const currentSegmentLength = segmentLengths[segmentIndex] ?? 0
        const segmentProgress =
          currentSegmentLength > 0
            ? (targetDistance - accumulatedDistance) / currentSegmentLength
            : 0

        const startWaypoint = waypoints[segmentIndex]
        const endWaypoint = waypoints[Math.min(segmentIndex + 1, waypoints.length - 1)]

        if (!startWaypoint || !endWaypoint) {
          vehicle.animationId = null
          resolve()
          return
        }

        const currentX = startWaypoint.x + (endWaypoint.x - startWaypoint.x) * segmentProgress
        const currentZ = startWaypoint.z + (endWaypoint.z - startWaypoint.z) * segmentProgress

        // Update vehicle position
        vehicle.mesh.position.x = currentX
        vehicle.mesh.position.z = currentZ

        // Calculate rotation to face movement direction
        const dx = endWaypoint.x - startWaypoint.x
        const dz = endWaypoint.z - startWaypoint.z
        if (dx !== 0 || dz !== 0) {
          const targetRotation = Math.atan2(dx, dz)
          // Smoothly interpolate rotation
          const currentRotation = vehicle.mesh.rotation.y
          const rotationDiff = targetRotation - currentRotation
          // Handle angle wrapping
          const normalizedDiff = Math.atan2(Math.sin(rotationDiff), Math.cos(rotationDiff))
          vehicle.mesh.rotation.y += normalizedDiff * 0.1
        }

        // Continue animation or resolve
        if (progress < 1.0) {
          vehicle.animationId = requestAnimationFrame(animate)
        } else {
          vehicle.animationId = null
          resolve()
        }
      }

      // Start animation
      vehicle.animationId = requestAnimationFrame(animate)
    })
  }

  /**
   * Animate vehicle to a specific zone
   *
   * Finds appropriate path and animates vehicle along it.
   */
  async function animateToZone(vehicle: ActiveVehicle, zoneId: string): Promise<void> {
    // Determine path based on current state and target
    let pathId: string
    if (vehicle.state === 'entering') {
      pathId = `main_to_${zoneId}`
    } else if (vehicle.state === 'exiting') {
      pathId = `${zoneId}_to_exit`
    } else {
      pathId = `${vehicle.targetZone}_to_${zoneId}`
    }

    const path = PATHS[pathId]
    if (!path) {
      console.warn(`[useVehicles3D] Path ${pathId} not found`)
      return
    }

    await animateVehicleAlongPath(vehicle, path)

    // Update vehicle state
    if (zoneId === 'exit' || vehicle.state === 'exiting') {
      vehicle.state = 'exiting'
    } else {
      vehicle.state = 'parked'
      vehicle.targetZone = zoneId
    }
  }

  /**
   * Remove vehicle from scene and cleanup resources
   *
   * Properly disposes geometries, materials, and labels to prevent memory leaks.
   */
  function removeVehicle(vehicleId: string): void {
    const vehicle = vehicles.value.get(vehicleId)
    if (!vehicle) {
      return
    }

    // Cancel any running animation
    if (vehicle.animationId !== null) {
      cancelAnimationFrame(vehicle.animationId)
      vehicle.animationId = null
    }

    // Remove label from mesh and DOM
    if (vehicle.label) {
      vehicle.mesh.remove(vehicle.label)
      if (vehicle.label.element && vehicle.label.element.parentNode) {
        vehicle.label.element.parentNode.removeChild(vehicle.label.element)
      }
    }

    // Remove from scene
    scene.remove(vehicle.mesh)

    // Dispose geometries and materials
    disposeVehicle(vehicle.mesh)

    // Remove from tracking Map
    const newMap = new Map(vehicles.value)
    newMap.delete(vehicleId)
    vehicles.value = newMap
  }

  /**
   * Remove all vehicles and cleanup
   */
  function removeAllVehicles(): void {
    for (const vehicleId of vehicles.value.keys()) {
      removeVehicle(vehicleId)
    }
  }

  /**
   * Get vehicle by ID
   */
  function getVehicle(vehicleId: string): ActiveVehicle | undefined {
    return vehicles.value.get(vehicleId)
  }

  /**
   * Get all vehicles
   */
  function getAllVehicles(): ActiveVehicle[] {
    return Array.from(vehicles.value.values())
  }

  /**
   * Update vehicle state
   */
  function updateVehicleState(
    vehicleId: string,
    state: ActiveVehicle['state']
  ): void {
    const vehicle = vehicles.value.get(vehicleId)
    if (vehicle) {
      vehicle.state = state
    }
  }

  /**
   * Cleanup all resources
   */
  function dispose(): void {
    removeAllVehicles()

    // Remove label renderer
    if (labelRenderer.value) {
      if (labelRenderer.value.domElement.parentNode) {
        labelRenderer.value.domElement.parentNode.removeChild(
          labelRenderer.value.domElement
        )
      }
      labelRenderer.value = null
    }
  }

  return {
    // State
    vehicles,
    labelRenderer,

    // Initialization
    initLabelRenderer,
    updateLabelRendererSize,
    renderLabels,

    // Vehicle management
    spawnVehicle,
    removeVehicle,
    removeAllVehicles,
    getVehicle,
    getAllVehicles,
    updateVehicleState,

    // Animation
    animateVehicleAlongPath,
    animateToZone,

    // Cleanup
    dispose,
  }
}
