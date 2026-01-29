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
import { dxfToWorld as dxfToWorldUtil } from '@/utils/coordinateTransforms'

/** Default vehicle speed in meters per second (~36 km/h) */
const DEFAULT_VEHICLE_SPEED_MPS = 10

/** Model rotation offset - vehicle model's forward is 90° off from world +Z */
const MODEL_ROTATION_OFFSET = Math.PI / 2

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
  state: 'entering' | 'parked' | 'exiting' | 'fading'
  targetZone: string
  label: CSS2DObject | null
  animationId: number | null
  /** Timestamp when vehicle was spawned */
  spawnTime: number
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
  // Track pending timeouts per vehicle for cleanup
  const pendingTimeouts = new Map<string, ReturnType<typeof setTimeout>>()

  const { createVehicle, disposeVehicle } = useVehicleModels()

  // ============================================================================
  // Coordinate Conversion
  // ============================================================================

  /**
   * Convert DXF coordinates to Three.js world coordinates
   */
  function dxfToWorld(dxfX: number, dxfY: number): THREE.Vector3 | null {
    const coord = coordSystem.value
    if (!coord) return null

    return dxfToWorldUtil(dxfX, dxfY, { coordinateSystem: coord })
  }

  /**
   * Calculate rotation angle to face from one position to another
   */
  function getRotationToFace(from: THREE.Vector3, to: THREE.Vector3): number {
    const dx = to.x - from.x
    const dz = to.z - from.z
    // Add model offset: vehicle model's forward is 90° off from world +Z
    return Math.atan2(dx, dz) + MODEL_ROTATION_OFFSET
  }

  // ============================================================================
  // Label Renderer
  // ============================================================================

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
   * Create realistic license plate label for a vehicle
   *
   * Styled to look like a real license plate with:
   * - Yellow/white background (Uzbekistan style)
   * - Dark embossed text
   * - Plate frame with status-colored border
   * - Subtle 3D effect
   */
  function createVehicleLabel(
    plateNumber: string,
    state: 'entering' | 'parked' | 'exiting' | 'fading' = 'entering'
  ): CSS2DObject {
    // Status colors for the plate frame
    const statusColors = {
      entering: '#22c55e',  // Green - vehicle entering
      parked: '#3b82f6',    // Blue - vehicle parked
      exiting: '#f97316',   // Orange - vehicle exiting
      fading: '#6b7280',    // Gray - vehicle fading out
    }

    const borderColor = statusColors[state]

    const labelDiv = document.createElement('div')
    labelDiv.className = 'vehicle-license-plate'
    labelDiv.innerHTML = `
      <div class="plate-frame">
        <div class="plate-content">
          <span class="plate-number">${plateNumber}</span>
        </div>
      </div>
    `

    // Realistic license plate styling
    labelDiv.style.cssText = `
      pointer-events: none;
      user-select: none;
    `

    // Add styles to the inner elements
    const style = document.createElement('style')
    style.textContent = `
      .vehicle-license-plate .plate-frame {
        background: linear-gradient(180deg, #2a2a2a 0%, #1a1a1a 100%);
        padding: 3px;
        border-radius: 4px;
        box-shadow:
          0 2px 8px rgba(0, 0, 0, 0.4),
          inset 0 1px 0 rgba(255, 255, 255, 0.1);
        border: 2px solid ${borderColor};
      }

      .vehicle-license-plate .plate-content {
        background: linear-gradient(180deg, #fef9c3 0%, #fde047 50%, #facc15 100%);
        padding: 4px 12px;
        border-radius: 2px;
        box-shadow:
          inset 0 1px 2px rgba(255, 255, 255, 0.8),
          inset 0 -1px 2px rgba(0, 0, 0, 0.1);
        border: 1px solid #a16207;
      }

      .vehicle-license-plate .plate-number {
        font-family: 'Arial Black', 'Helvetica Neue', sans-serif;
        font-size: 14px;
        font-weight: 900;
        color: #1a1a1a;
        letter-spacing: 1px;
        text-shadow:
          1px 1px 0 rgba(255, 255, 255, 0.3),
          -1px -1px 0 rgba(0, 0, 0, 0.1);
        text-transform: uppercase;
        white-space: nowrap;
      }
    `

    // Inject styles (only once per document)
    if (!document.querySelector('#vehicle-plate-styles')) {
      style.id = 'vehicle-plate-styles'
      document.head.appendChild(style)
    }

    const label = new CSS2DObject(labelDiv)
    label.position.set(0, 4, 0) // Position above vehicle
    label.center.set(0.5, 0)

    return label
  }

  /**
   * Update the license plate border color based on vehicle state
   */
  function updateLabelState(
    label: CSS2DObject,
    state: 'entering' | 'parked' | 'exiting' | 'fading'
  ): void {
    const statusColors = {
      entering: '#22c55e',
      parked: '#3b82f6',
      exiting: '#f97316',
      fading: '#6b7280',
    }

    const frame = label.element.querySelector('.plate-frame') as HTMLElement
    if (frame) {
      frame.style.borderColor = statusColors[state]
    }
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

    // Create vehicle model with license plate
    const modelOptions: VehicleModelOptions = {
      withChassis: detection.vehicleType === 'TRUCK',
      chassisSize: '40ft',
      scale: 1.0,
      plateNumber: detection.plateNumber,  // Add plate directly to 3D model
    }
    const mesh = createVehicle(detection.vehicleType, modelOptions)
    mesh.name = `vehicle-${detection.id}`

    // Position at gate
    mesh.position.set(gatePos.x, gatePos.y, gatePos.z)
    mesh.rotation.y = gatePos.rotation

    // Add to scene
    scene.add(mesh)

    // Determine initial state
    const initialState = detection.direction === 'exiting' ? 'exiting' : 'entering'

    // Create floating label with state-aware styling (in addition to 3D plates)
    const label = createVehicleLabel(detection.plateNumber, initialState)
    mesh.add(label)

    // Create active vehicle record
    const activeVehicle: ActiveVehicle = {
      id: detection.id,
      mesh,
      plateNumber: detection.plateNumber,
      vehicleType: detection.vehicleType,
      state: initialState,
      targetZone: detection.targetZone ?? 'waiting',
      label,
      animationId: null,
      spawnTime: Date.now(),
    }

    // Add to tracking Map
    const newMap = new Map(vehicles.value)
    newMap.set(detection.id, activeVehicle)
    vehicles.value = newMap

    return activeVehicle
  }

  /**
   * Spawn a vehicle at gate for brief display (entry visualization)
   *
   * Simpler version of spawnVehicle - just creates and positions the vehicle.
   * Use with fadeOutVehicle() for the brief spawn + fade effect.
   *
   * @param detection - Vehicle detection data
   * @param displayDuration - How long to display before auto-fade (ms), 0 = manual
   * @returns The spawned vehicle or null if failed
   */
  function spawnEntryVehicle(
    detection: VehicleDetection,
    displayDuration: number = 0
  ): ActiveVehicle | null {
    const vehicle = spawnVehicle(detection)
    if (!vehicle) return null

    // Auto-fade after display duration if specified
    if (displayDuration > 0) {
      const timeoutId = setTimeout(() => {
        pendingTimeouts.delete(vehicle.id)
        fadeOutVehicle(vehicle.id, 1500) // 1.5s fade
      }, displayDuration)
      pendingTimeouts.set(vehicle.id, timeoutId)
    }

    return vehicle
  }

  /**
   * Spawn a vehicle at arbitrary DXF coordinates
   *
   * @param detection - Vehicle detection data
   * @param dxfX - DXF X coordinate
   * @param dxfY - DXF Y coordinate
   * @param targetDxf - Optional target position to face towards
   * @returns The spawned vehicle or null if failed
   */
  function spawnVehicleAtPosition(
    detection: VehicleDetection,
    dxfX: number,
    dxfY: number,
    targetDxf?: { x: number; y: number }
  ): ActiveVehicle | null {
    if (import.meta.env.DEV) console.log('[useVehicles3D] spawnVehicleAtPosition called with DXF:', { dxfX, dxfY })

    const coord = coordSystem.value
    if (!coord) {
      console.warn('[useVehicles3D] Coordinate system not ready')
      return null
    }

    if (import.meta.env.DEV) console.log('[useVehicles3D] Coordinate system:', {
      center: coord.center,
      scale: coord.scale,
    })

    // Check if vehicle already exists
    if (vehicles.value.has(detection.id)) {
      console.warn(`[useVehicles3D] Vehicle ${detection.id} already exists`)
      return vehicles.value.get(detection.id) || null
    }

    // Convert DXF to world coordinates
    const worldPos = dxfToWorld(dxfX, dxfY)
    if (!worldPos) {
      console.warn('[useVehicles3D] Failed to convert coordinates')
      return null
    }

    if (import.meta.env.DEV) console.log('[useVehicles3D] Converted to world position:', {
      x: worldPos.x.toFixed(2),
      y: worldPos.y.toFixed(2),
      z: worldPos.z.toFixed(2),
    })

    // Create vehicle model with license plate
    const modelOptions: VehicleModelOptions = {
      withChassis: detection.vehicleType === 'TRUCK',
      chassisSize: '40ft',
      scale: 1.0,
      plateNumber: detection.plateNumber,  // Add plate directly to 3D model
    }
    const mesh = createVehicle(detection.vehicleType, modelOptions)
    mesh.name = `vehicle-${detection.id}`

    // Position at specified coordinates
    mesh.position.copy(worldPos)

    // Calculate rotation to face target (or default forward)
    if (targetDxf) {
      const targetWorld = dxfToWorld(targetDxf.x, targetDxf.y)
      if (targetWorld) {
        mesh.rotation.y = getRotationToFace(worldPos, targetWorld)
      }
    }

    // Add to scene
    scene.add(mesh)

    // Determine initial state
    const initialState = detection.direction === 'exiting' ? 'exiting' : 'entering'

    // Create floating label with state-aware styling (in addition to 3D plates)
    const label = createVehicleLabel(detection.plateNumber, initialState)
    mesh.add(label)

    // Create active vehicle record
    const activeVehicle: ActiveVehicle = {
      id: detection.id,
      mesh,
      plateNumber: detection.plateNumber,
      vehicleType: detection.vehicleType,
      state: initialState,
      targetZone: detection.targetZone ?? 'custom',
      label,
      animationId: null,
      spawnTime: Date.now(),
    }

    // Add to tracking Map
    const newMap = new Map(vehicles.value)
    newMap.set(detection.id, activeVehicle)
    vehicles.value = newMap

    if (import.meta.env.DEV) console.log(`[useVehicles3D] Spawned vehicle at DXF (${dxfX}, ${dxfY}) → World (${worldPos.x.toFixed(1)}, ${worldPos.z.toFixed(1)})`)

    return activeVehicle
  }

  /**
   * Fade out and remove a vehicle with opacity animation
   *
   * Animates all mesh materials to transparent, then removes vehicle.
   *
   * @param vehicleId - ID of vehicle to fade out
   * @param duration - Fade duration in milliseconds
   * @returns Promise that resolves when fade completes
   */
  function fadeOutVehicle(vehicleId: string, duration: number = 1000): Promise<void> {
    return new Promise((resolve) => {
      const vehicle = vehicles.value.get(vehicleId)
      if (!vehicle) {
        resolve()
        return
      }

      // Mark as fading to prevent double-fade
      if (vehicle.state === 'fading') {
        resolve()
        return
      }
      // Cancel any running animation before starting fade
      if (vehicle.animationId !== null) {
        cancelAnimationFrame(vehicle.animationId)
        vehicle.animationId = null
      }

      // Update state and label to fading appearance (gray border)
      setVehicleState(vehicle, 'fading')

      // Collect all materials for opacity animation
      const materialsToFade: THREE.Material[] = []
      vehicle.mesh.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          const materials = Array.isArray(child.material) ? child.material : [child.material]
          materials.forEach((mat) => {
            if (mat instanceof THREE.MeshStandardMaterial || mat instanceof THREE.MeshBasicMaterial) {
              mat.transparent = true
              materialsToFade.push(mat)
            }
          })
        }
      })

      // Fade label if exists
      const labelElement = vehicle.label?.element as HTMLElement | undefined

      const startTime = performance.now()
      // Store reference to avoid closure issues with TypeScript
      const vehicleRef = vehicle

      function animate(currentTime: number): void {
        const elapsed = currentTime - startTime
        const progress = Math.min(elapsed / duration, 1.0)
        const opacity = 1 - progress

        // Update material opacity
        materialsToFade.forEach((mat) => {
          if ('opacity' in mat) {
            mat.opacity = opacity
          }
        })

        // Update label opacity
        if (labelElement) {
          labelElement.style.opacity = String(opacity)
        }

        if (progress < 1.0) {
          vehicleRef.animationId = requestAnimationFrame(animate)
        } else {
          // Fade complete - remove vehicle
          removeVehicle(vehicleId)
          resolve()
        }
      }

      vehicleRef.animationId = requestAnimationFrame(animate)
    })
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

      // Cancel any running animation before starting path animation
      if (vehicle.animationId !== null) {
        cancelAnimationFrame(vehicle.animationId)
        vehicle.animationId = null
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

    // Update vehicle state and label
    if (zoneId === 'exit' || vehicle.state === 'exiting') {
      setVehicleState(vehicle, 'exiting')
    } else {
      setVehicleState(vehicle, 'parked')
      vehicle.targetZone = zoneId
    }
  }

  /**
   * Update vehicle state and sync the license plate label appearance
   */
  function setVehicleState(
    vehicle: ActiveVehicle,
    newState: 'entering' | 'parked' | 'exiting' | 'fading'
  ): void {
    vehicle.state = newState
    if (vehicle.label) {
      updateLabelState(vehicle.label, newState)
    }
  }

  /**
   * Animate vehicle from current position to target DXF coordinates
   *
   * Simple linear interpolation with smooth rotation.
   *
   * @param vehicle - Vehicle to animate
   * @param targetDxfX - Target DXF X coordinate
   * @param targetDxfY - Target DXF Y coordinate
   * @param duration - Animation duration in seconds (default: calculated from distance)
   * @returns Promise that resolves when animation completes
   */
  function animateVehicleToPosition(
    vehicle: ActiveVehicle,
    targetDxfX: number,
    targetDxfY: number,
    duration?: number
  ): Promise<void> {
    return new Promise((resolve) => {
      const targetWorld = dxfToWorld(targetDxfX, targetDxfY)
      if (!targetWorld) {
        console.warn('[useVehicles3D] Failed to convert target coordinates')
        resolve()
        return
      }

      // Cancel any running animation before starting position animation
      if (vehicle.animationId !== null) {
        cancelAnimationFrame(vehicle.animationId)
        vehicle.animationId = null
      }

      const startPos = vehicle.mesh.position.clone()
      const endPos = targetWorld

      // Calculate distance for default duration
      const distance = startPos.distanceTo(endPos)
      const speed = DEFAULT_VEHICLE_SPEED_MPS
      const calculatedDuration = duration ?? distance / speed
      const durationMs = calculatedDuration * 1000

      // Calculate target rotation
      const targetRotation = getRotationToFace(startPos, endPos)

      const startTime = performance.now()
      const vehicleRef = vehicle

      if (import.meta.env.DEV) console.log(`[useVehicles3D] Animating to DXF (${targetDxfX}, ${targetDxfY}), distance: ${distance.toFixed(1)}m, duration: ${calculatedDuration.toFixed(1)}s`)

      function animate(currentTime: number): void {
        const elapsed = currentTime - startTime
        const progress = Math.min(elapsed / durationMs, 1.0)

        // Ease-in-out for smoother motion
        const easedProgress = progress < 0.5
          ? 2 * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 2) / 2

        // Interpolate position
        vehicleRef.mesh.position.x = startPos.x + (endPos.x - startPos.x) * easedProgress
        vehicleRef.mesh.position.z = startPos.z + (endPos.z - startPos.z) * easedProgress

        // Smoothly interpolate rotation
        const currentRotation = vehicleRef.mesh.rotation.y
        const rotationDiff = targetRotation - currentRotation
        const normalizedDiff = Math.atan2(Math.sin(rotationDiff), Math.cos(rotationDiff))
        vehicleRef.mesh.rotation.y += normalizedDiff * 0.15

        if (progress < 1.0) {
          vehicleRef.animationId = requestAnimationFrame(animate)
        } else {
          // Ensure final position is exact
          vehicleRef.mesh.position.copy(endPos)
          vehicleRef.mesh.rotation.y = targetRotation
          vehicleRef.animationId = null
          if (import.meta.env.DEV) console.log('[useVehicles3D] Animation complete')
          resolve()
        }
      }

      vehicleRef.animationId = requestAnimationFrame(animate)
    })
  }

  /**
   * Animate vehicle forward in its current facing direction
   *
   * Simple animation that moves vehicle forward by specified distance.
   *
   * @param vehicle - Vehicle to animate
   * @param distance - Distance to travel in meters
   * @param speed - Speed in meters per second (default: 10 m/s = 36 km/h)
   * @returns Promise that resolves when animation completes
   */
  function animateVehicleForward(
    vehicle: ActiveVehicle,
    distance: number,
    speed: number = 10
  ): Promise<void> {
    return new Promise((resolve) => {
      // Cancel any running animation before starting forward animation
      if (vehicle.animationId !== null) {
        cancelAnimationFrame(vehicle.animationId)
        vehicle.animationId = null
      }

      const startPos = vehicle.mesh.position.clone()
      const rotation = vehicle.mesh.rotation.y

      // Calculate end position based on current rotation
      // In Three.js: rotation.y = 0 means facing +Z, rotation increases counter-clockwise
      // Forward direction: sin(rotation) for X, cos(rotation) for Z
      const endPos = new THREE.Vector3(
        startPos.x + Math.sin(rotation) * distance,
        startPos.y,
        startPos.z + Math.cos(rotation) * distance
      )

      const durationMs = (distance / speed) * 1000
      const startTime = performance.now()
      const vehicleRef = vehicle

      function animate(currentTime: number): void {
        const elapsed = currentTime - startTime
        const progress = Math.min(elapsed / durationMs, 1.0)

        // Ease-in-out for smoother motion
        const easedProgress = progress < 0.5
          ? 2 * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 2) / 2

        // Interpolate position
        vehicleRef.mesh.position.x = startPos.x + (endPos.x - startPos.x) * easedProgress
        vehicleRef.mesh.position.z = startPos.z + (endPos.z - startPos.z) * easedProgress

        if (progress < 1.0) {
          vehicleRef.animationId = requestAnimationFrame(animate)
        } else {
          vehicleRef.mesh.position.copy(endPos)
          vehicleRef.animationId = null
          resolve()
        }
      }

      vehicleRef.animationId = requestAnimationFrame(animate)
    })
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

    // Cancel any pending timeout
    const timeout = pendingTimeouts.get(vehicleId)
    if (timeout !== undefined) {
      clearTimeout(timeout)
      pendingTimeouts.delete(vehicleId)
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
   * Get all vehicles
   */
  function getAllVehicles(): ActiveVehicle[] {
    return Array.from(vehicles.value.values())
  }

  /**
   * Find a vehicle by its license plate number
   *
   * Searches through all active vehicles (excluding those already exiting/fading)
   * and returns the first match.
   *
   * @param plateNumber - License plate number to search for
   * @returns The matched vehicle or null if not found
   */
  function findVehicleByPlate(plateNumber: string): ActiveVehicle | null {
    for (const vehicle of vehicles.value.values()) {
      if (
        vehicle.plateNumber === plateNumber &&
        vehicle.state !== 'exiting' &&
        vehicle.state !== 'fading'
      ) {
        return vehicle
      }
    }
    return null
  }

  /**
   * Animate a vehicle through the complete exit sequence
   *
   * Full exit flow:
   * 1. Change state to 'exiting' (label turns orange)
   * 2. Animate along exit path from current zone to gate
   * 3. Continue driving 20m past gate (off-screen)
   * 4. Fade out and remove from scene
   *
   * @param vehicle - The vehicle to exit
   * @param onComplete - Optional callback when exit animation completes
   * @returns Promise that resolves when vehicle is fully removed
   */
  async function animateVehicleExit(
    vehicle: ActiveVehicle,
    onComplete?: () => void
  ): Promise<void> {
    // 1. Change state to exiting
    setVehicleState(vehicle, 'exiting')

    // 2. Animate along exit path from zone to gate
    const exitPathId = `${vehicle.targetZone}_to_exit`
    const exitPath = PATHS[exitPathId]

    if (exitPath) {
      await animateVehicleAlongPath(vehicle, exitPath)
    } else {
      // Fallback: animate directly to main gate if no exit path defined
      const mainGatePos = getGateWorldPosition('main', coordSystem.value!)
      if (mainGatePos) {
        // Get DXF coordinates for main gate
        const gateConfig = PATHS['main_to_waiting']?.waypoints?.[0]
        if (gateConfig) {
          await animateVehicleToPosition(vehicle, gateConfig.x, gateConfig.y, 3)
        }
      }
    }

    // 3. Drive off-screen (20m forward past gate)
    await animateVehicleForward(vehicle, 20, 8)

    // 4. Fade out and remove
    await fadeOutVehicle(vehicle.id, 1000)

    // Call completion callback
    onComplete?.()
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
    spawnEntryVehicle,
    spawnVehicleAtPosition,
    setVehicleState,
    fadeOutVehicle,
    removeVehicle,
    removeAllVehicles,
    getAllVehicles,
    findVehicleByPlate,

    // Exit animation
    animateVehicleExit,

    // Animation
    animateVehicleAlongPath,
    animateToZone,
    animateVehicleToPosition,
    animateVehicleForward,

    // Coordinate conversion (for external use)
    dxfToWorld,

    // Cleanup
    dispose,
  }
}
