/**
 * Gate Camera 3D Composable
 *
 * Creates a realistic 3D security camera model for the yard scene.
 * Supports hover/active states and pulse animation on detection.
 */

import * as THREE from 'three'
import { disposeObject3D } from '@/utils/threeUtils'

/** Camera visual states */
export type CameraState = 'normal' | 'hovered' | 'active'

/** Colors for different states - Realistic security camera */
const COLORS = {
  body: 0x1a1a1a,           // Dark black/gray camera body
  bodyLight: 0x2d2d2d,      // Lighter parts of body
  lens: 0x0a0a0a,           // Black lens housing
  lensGlass: 0x111122,      // Very dark lens glass
  metal: 0x4a4a4a,          // Dark metallic parts
  metalLight: 0x6a6a6a,     // Lighter metal accents
  base: 0x3d3d3d,           // Dark base
  led: 0x00ff00,            // Green LED
  ledActive: 0xff3333,      // Red LED when active
  // Detection zone colors
  zoneIdle: 0x00ff88,       // Green detection zone (idle)
  zoneActive: 0xff4444,     // Red detection zone (detecting)
  // State emissives
  emissiveHover: 0x00d9ff,  // Cyan glow on hover
  emissiveActive: 0x00ffaa, // Green glow when active
  emissivePulse: 0xffff00,  // Yellow flash on detection
}

/** Camera dimensions in meters - Wall-mounted security camera style */
const DIMS = {
  // Main camera body (bullet style)
  body: { radius: 0.06, length: 0.18 },
  // Lens assembly
  lens: { radius: 0.035, length: 0.04 },
  lensRing: { radius: 0.045, depth: 0.015 },
  // Sun shield / hood
  hood: { radius: 0.07, length: 0.05, thickness: 0.008 },
  // Wall mount plate (attaches to wall)
  wallMount: { width: 0.12, height: 0.12, depth: 0.03 },
  // Mounting arm (extends from wall to camera)
  arm: { width: 0.04, length: 0.15, thickness: 0.03 },
  // Height on wall
  // NOTE: Camera mesh is scaled 5x in GateCamera3D.vue, so actual height = mountHeight × 5
  // Fence height is 2.5 units, so to mount near top: 2.5 / 5.0 = 0.5
  mountHeight: 0.45,        // 0.45 × 5 = 2.25 units (just below fence top at 2.5)
  // Detection zone (field of view cone)
  // NOTE: Mesh is scaled 5x, so internal values × 5 = world values
  // Camera height = 0.45 × 5 = 2.25 units
  // To reach ground at 25° tilt: distance = 2.25 / sin(25°) ≈ 5.3 units world
  // Internal distance = 5.3 / 5 = ~1.06
  detectionZone: {
    angle: 70,              // FOV angle in degrees
    distance: 1.0,          // Internal units (× 5 scale = 5 units world, stops near ground)
    opacity: 0.12,          // Transparency of the zone
  },
  // Camera tilt
  tilt: 5 * (Math.PI / 180), // 5 degrees upward (looking slightly up)
}

/** Detection zone vertex in world coordinates */
export interface DetectionZoneVertex {
  x: number
  z: number
}

export interface UseGateCamera3DOptions {
  /** Initial camera state */
  initialState?: CameraState
  /** Custom detection zone vertices (if provided, replaces default cone) */
  customDetectionZone?: DetectionZoneVertex[]
  /** Whether to show the default cone detection zone (default: true) */
  showDefaultDetectionZone?: boolean
}

export interface UseGateCamera3DReturn {
  /** The camera mesh group */
  mesh: THREE.Group
  /** The detection zone mesh (separate from camera for custom positioning) */
  detectionZoneMesh: THREE.Mesh | null
  /** Set hover state */
  setHovered: (hovered: boolean) => void
  /** Set active state (widget open) */
  setActive: (active: boolean) => void
  /** Trigger pulse animation (on detection) */
  triggerPulse: () => void
  /** Get current state */
  getState: () => CameraState
  /** Dispose all resources */
  dispose: () => void
}

/**
 * Create a 3D gate camera
 *
 * @param options - Configuration options
 * @returns Camera mesh and control functions
 */
export function useGateCamera3D(options: UseGateCamera3DOptions = {}): UseGateCamera3DReturn {
  const {
    initialState = 'normal',
    showDefaultDetectionZone = true,
  } = options

  let currentState: CameraState = initialState
  let pulseAnimationId: number | null = null

  // Material references for state changes
  const materials: {
    body: THREE.MeshStandardMaterial
    bodyLight: THREE.MeshStandardMaterial
    lens: THREE.MeshStandardMaterial
    lensGlass: THREE.MeshStandardMaterial
    metal: THREE.MeshStandardMaterial
    base: THREE.MeshStandardMaterial
    detectionZone: THREE.MeshBasicMaterial
  } = {} as typeof materials

  // Detection zone mesh reference (returned to caller for custom positioning)
  let detectionZoneMeshRef: THREE.Mesh | null = null

  // Create materials - Realistic security camera appearance
  function createMaterials(): void {
    // Main camera body - matte black plastic
    materials.body = new THREE.MeshStandardMaterial({
      color: COLORS.body,
      roughness: 0.8,
      metalness: 0.1,
    })

    // Lighter body parts
    materials.bodyLight = new THREE.MeshStandardMaterial({
      color: COLORS.bodyLight,
      roughness: 0.7,
      metalness: 0.15,
    })

    // Lens housing - glossy black
    materials.lens = new THREE.MeshStandardMaterial({
      color: COLORS.lens,
      roughness: 0.2,
      metalness: 0.3,
    })

    // Lens glass - dark and reflective
    materials.lensGlass = new THREE.MeshStandardMaterial({
      color: COLORS.lensGlass,
      roughness: 0.05,
      metalness: 0.9,
      transparent: true,
      opacity: 0.9,
    })

    // Metal parts - brushed metal look
    materials.metal = new THREE.MeshStandardMaterial({
      color: COLORS.metal,
      roughness: 0.4,
      metalness: 0.8,
    })

    // Base - dark concrete/metal
    materials.base = new THREE.MeshStandardMaterial({
      color: COLORS.base,
      roughness: 0.9,
      metalness: 0.2,
    })

    // Detection zone - semi-transparent
    materials.detectionZone = new THREE.MeshBasicMaterial({
      color: COLORS.zoneIdle,
      transparent: true,
      opacity: DIMS.detectionZone.opacity,
      side: THREE.DoubleSide,
      depthWrite: false,
    })
  }

  // Create camera mesh group - Wall-mounted security camera
  function createCameraMesh(): THREE.Group {
    createMaterials()

    const group = new THREE.Group()
    group.name = 'gate-camera'

    // ─────────────────────────────────────────────────────────────
    // Wall mount plate (attaches to wall - positioned at wall)
    // ─────────────────────────────────────────────────────────────
    const wallMountGeom = new THREE.BoxGeometry(
      DIMS.wallMount.width,
      DIMS.wallMount.height,
      DIMS.wallMount.depth
    )
    const wallMountMesh = new THREE.Mesh(wallMountGeom, materials.base)
    wallMountMesh.position.set(0, DIMS.mountHeight, -DIMS.wallMount.depth / 2)
    wallMountMesh.castShadow = true
    wallMountMesh.receiveShadow = true
    wallMountMesh.name = 'camera-wall-mount'
    group.add(wallMountMesh)

    // ─────────────────────────────────────────────────────────────
    // Camera head group (extends from wall)
    // ─────────────────────────────────────────────────────────────
    const headGroup = new THREE.Group()
    headGroup.name = 'camera-head'
    headGroup.position.y = DIMS.mountHeight
    group.add(headGroup)

    // ─────────────────────────────────────────────────────────────
    // Mounting arm (extends from wall mount to camera)
    // ─────────────────────────────────────────────────────────────
    const armGeom = new THREE.BoxGeometry(
      DIMS.arm.width,
      DIMS.arm.thickness,
      DIMS.arm.length
    )
    const armMesh = new THREE.Mesh(armGeom, materials.metal)
    armMesh.rotation.x = DIMS.tilt
    armMesh.position.set(0, 0, DIMS.arm.length / 2)
    armMesh.castShadow = true
    armMesh.name = 'camera-arm'
    headGroup.add(armMesh)

    // Calculate camera body position (at end of arm)
    const armEndZ = DIMS.arm.length + 0.02
    const armEndY = Math.sin(-DIMS.tilt) * DIMS.arm.length

    // ─────────────────────────────────────────────────────────────
    // Camera body (bullet style - cylinder)
    // ─────────────────────────────────────────────────────────────
    const bodyGeom = new THREE.CylinderGeometry(
      DIMS.body.radius,
      DIMS.body.radius,
      DIMS.body.length,
      16
    )
    const bodyMesh = new THREE.Mesh(bodyGeom, materials.body)
    bodyMesh.rotation.x = Math.PI / 2 + DIMS.tilt // Point forward
    bodyMesh.position.set(0, armEndY, armEndZ + DIMS.body.length / 2)
    bodyMesh.castShadow = true
    bodyMesh.name = 'camera-body'
    headGroup.add(bodyMesh)

    // ─────────────────────────────────────────────────────────────
    // Camera body end caps (rounded ends)
    // ─────────────────────────────────────────────────────────────
    // Back cap
    const backCapGeom = new THREE.SphereGeometry(DIMS.body.radius, 16, 12)
    const backCapMesh = new THREE.Mesh(backCapGeom, materials.body)
    backCapMesh.scale.z = 0.3 // Flatten into dome
    backCapMesh.rotation.x = DIMS.tilt
    backCapMesh.position.set(0, armEndY, armEndZ - 0.01)
    backCapMesh.name = 'camera-back-cap'
    headGroup.add(backCapMesh)

    // ─────────────────────────────────────────────────────────────
    // Lens ring (metallic ring around lens)
    // ─────────────────────────────────────────────────────────────
    const lensRingGeom = new THREE.CylinderGeometry(
      DIMS.lensRing.radius,
      DIMS.lensRing.radius,
      DIMS.lensRing.depth,
      16
    )
    const lensRingMesh = new THREE.Mesh(lensRingGeom, materials.metal)
    lensRingMesh.rotation.x = Math.PI / 2 + DIMS.tilt
    const lensZ = armEndZ + DIMS.body.length + 0.01
    const lensYOffset = Math.sin(-DIMS.tilt) * DIMS.body.length
    lensRingMesh.position.set(0, armEndY + lensYOffset, lensZ)
    lensRingMesh.name = 'camera-lens-ring'
    headGroup.add(lensRingMesh)

    // ─────────────────────────────────────────────────────────────
    // Lens housing (inner black cylinder)
    // ─────────────────────────────────────────────────────────────
    const lensHousingGeom = new THREE.CylinderGeometry(
      DIMS.lens.radius,
      DIMS.lens.radius * 0.8,
      DIMS.lens.length,
      16
    )
    const lensHousingMesh = new THREE.Mesh(lensHousingGeom, materials.lens)
    lensHousingMesh.rotation.x = Math.PI / 2 + DIMS.tilt
    lensHousingMesh.position.set(0, armEndY + lensYOffset, lensZ + DIMS.lens.length / 2)
    lensHousingMesh.name = 'camera-lens-housing'
    headGroup.add(lensHousingMesh)

    // ─────────────────────────────────────────────────────────────
    // Lens glass (front of lens - reflective)
    // ─────────────────────────────────────────────────────────────
    const lensGlassGeom = new THREE.CircleGeometry(DIMS.lens.radius * 0.7, 16)
    const lensGlassMesh = new THREE.Mesh(lensGlassGeom, materials.lensGlass)
    lensGlassMesh.rotation.x = DIMS.tilt
    lensGlassMesh.position.set(0, armEndY + lensYOffset, lensZ + DIMS.lens.length + 0.005)
    lensGlassMesh.name = 'camera-lens-glass'
    headGroup.add(lensGlassMesh)

    // ─────────────────────────────────────────────────────────────
    // Sun shield / hood (protects lens from glare)
    // ─────────────────────────────────────────────────────────────
    // Create hood as a partial cylinder (open bottom)
    const hoodGeom = new THREE.CylinderGeometry(
      DIMS.hood.radius,
      DIMS.hood.radius,
      DIMS.hood.length,
      16,
      1,
      true, // Open ended
      0,
      Math.PI * 1.5 // Only 3/4 of cylinder (open bottom)
    )
    const hoodMesh = new THREE.Mesh(hoodGeom, materials.bodyLight)
    hoodMesh.rotation.x = Math.PI / 2 + DIMS.tilt
    hoodMesh.rotation.z = Math.PI / 4 // Rotate so opening is at bottom
    hoodMesh.position.set(0, armEndY + lensYOffset, lensZ + DIMS.hood.length / 2)
    hoodMesh.name = 'camera-hood'
    headGroup.add(hoodMesh)

    // ─────────────────────────────────────────────────────────────
    // LED indicator (small light on body)
    // ─────────────────────────────────────────────────────────────
    const ledGeom = new THREE.SphereGeometry(0.008, 8, 8)
    const ledMat = new THREE.MeshStandardMaterial({
      color: COLORS.led,
      emissive: COLORS.led,
      emissiveIntensity: 0.8,
    })
    const ledMesh = new THREE.Mesh(ledGeom, ledMat)
    // Position on side of body
    ledMesh.position.set(
      DIMS.body.radius + 0.005,
      armEndY,
      armEndZ + DIMS.body.length * 0.3
    )
    ledMesh.name = 'camera-led'
    headGroup.add(ledMesh)

    // ─────────────────────────────────────────────────────────────
    // DETECTION ZONE (Field of View cone)
    // Cone originates from camera lens and extends toward ground
    // Only create if showDefaultDetectionZone is true
    // ─────────────────────────────────────────────────────────────
    if (showDefaultDetectionZone) {
      const fovAngleRad = (DIMS.detectionZone.angle / 2) * (Math.PI / 180)
      const coneLength = DIMS.detectionZone.distance
      const coneRadius = Math.tan(fovAngleRad) * coneLength

      // Create cone geometry
      // ConeGeometry creates cone centered at origin, tip at +Y, base at -Y
      const zoneGeom = new THREE.ConeGeometry(
        coneRadius,
        coneLength,
        24,
        1,
        true // Open ended (no base cap)
      )

      // Translate geometry so the TIP (apex) is at origin instead of center
      // This makes positioning easier - we can place the mesh at the lens
      zoneGeom.translate(0, -coneLength / 2, 0)

      detectionZoneMeshRef = new THREE.Mesh(zoneGeom, materials.detectionZone)

      // Rotate cone to point forward and down
      // Default cone points along +Y, we want it to point along +Z (forward) with tilt
      detectionZoneMeshRef.rotation.x = -Math.PI / 2 + DIMS.tilt

      // Position at the lens (apex of cone is now at mesh origin)
      const lensPosition = {
        x: 0,
        y: armEndY + lensYOffset,
        z: lensZ + DIMS.lens.length
      }
      detectionZoneMeshRef.position.set(lensPosition.x, lensPosition.y, lensPosition.z)
      detectionZoneMeshRef.name = 'camera-detection-zone'
      headGroup.add(detectionZoneMeshRef)
    }

    // Set initial state
    updateVisualState(currentState)

    return group
  }

  const mesh = createCameraMesh()

  // Update visual appearance based on state
  function updateVisualState(state: CameraState): void {
    switch (state) {
      case 'hovered':
        // Camera body glow
        materials.body.emissive.setHex(COLORS.emissiveHover)
        materials.body.emissiveIntensity = 0.15
        materials.metal.emissive.setHex(COLORS.emissiveHover)
        materials.metal.emissiveIntensity = 0.1
        // Detection zone stays green but slightly brighter
        materials.detectionZone.color.setHex(COLORS.zoneIdle)
        materials.detectionZone.opacity = DIMS.detectionZone.opacity * 1.5
        break

      case 'active':
        // Camera body glow (active/detecting)
        materials.body.emissive.setHex(COLORS.emissiveActive)
        materials.body.emissiveIntensity = 0.2
        materials.metal.emissive.setHex(COLORS.emissiveActive)
        materials.metal.emissiveIntensity = 0.15
        // Detection zone turns RED when active (detecting)
        materials.detectionZone.color.setHex(COLORS.zoneActive)
        materials.detectionZone.opacity = DIMS.detectionZone.opacity * 2
        break

      case 'normal':
      default:
        // No glow
        materials.body.emissive.setHex(0x000000)
        materials.body.emissiveIntensity = 0
        materials.metal.emissive.setHex(0x000000)
        materials.metal.emissiveIntensity = 0
        // Detection zone green (idle)
        materials.detectionZone.color.setHex(COLORS.zoneIdle)
        materials.detectionZone.opacity = DIMS.detectionZone.opacity
        break
    }
  }

  // Set hover state
  function setHovered(hovered: boolean): void {
    if (hovered && currentState === 'normal') {
      currentState = 'hovered'
      updateVisualState('hovered')
    } else if (!hovered && currentState === 'hovered') {
      currentState = 'normal'
      updateVisualState('normal')
    }
  }

  // Set active state (when widget is open)
  function setActive(active: boolean): void {
    if (active) {
      currentState = 'active'
      updateVisualState('active')
    } else {
      currentState = 'normal'
      updateVisualState('normal')
    }
  }

  // Trigger pulse animation on vehicle detection
  function triggerPulse(): void {
    // Cancel any existing pulse
    if (pulseAnimationId !== null) {
      cancelAnimationFrame(pulseAnimationId)
    }

    const startTime = performance.now()
    const duration = 500 // 500ms pulse (longer for visibility)

    // Store original state
    const originalBodyEmissive = materials.body.emissive.getHex()
    const originalBodyIntensity = materials.body.emissiveIntensity
    const originalMetalEmissive = materials.metal.emissive.getHex()
    const originalMetalIntensity = materials.metal.emissiveIntensity
    const originalZoneColor = materials.detectionZone.color.getHex()
    const originalZoneOpacity = materials.detectionZone.opacity

    function animate(currentTime: number): void {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1.0)

      // Pulse intensity: 0 -> 1 -> 0 (sine wave)
      const intensity = Math.sin(progress * Math.PI)

      // Apply pulse color to camera body
      materials.body.emissive.setHex(COLORS.emissivePulse)
      materials.body.emissiveIntensity = intensity * 0.8
      materials.metal.emissive.setHex(COLORS.emissivePulse)
      materials.metal.emissiveIntensity = intensity * 0.6

      // Flash detection zone RED during pulse
      materials.detectionZone.color.setHex(COLORS.zoneActive)
      materials.detectionZone.opacity = DIMS.detectionZone.opacity + intensity * 0.25

      if (progress < 1.0) {
        pulseAnimationId = requestAnimationFrame(animate)
      } else {
        // Restore original state
        materials.body.emissive.setHex(originalBodyEmissive)
        materials.body.emissiveIntensity = originalBodyIntensity
        materials.metal.emissive.setHex(originalMetalEmissive)
        materials.metal.emissiveIntensity = originalMetalIntensity
        materials.detectionZone.color.setHex(originalZoneColor)
        materials.detectionZone.opacity = originalZoneOpacity
        pulseAnimationId = null

        // Re-apply current state visuals
        updateVisualState(currentState)
      }
    }

    pulseAnimationId = requestAnimationFrame(animate)
  }

  // Get current state
  function getState(): CameraState {
    return currentState
  }

  // Dispose all resources
  function dispose(): void {
    // Cancel any running animation
    if (pulseAnimationId !== null) {
      cancelAnimationFrame(pulseAnimationId)
      pulseAnimationId = null
    }

    // Dispose geometries and materials using shared utility
    disposeObject3D(mesh)

    // Clear from parent if attached
    if (mesh.parent) {
      mesh.parent.remove(mesh)
    }
  }

  return {
    mesh,
    detectionZoneMesh: detectionZoneMeshRef,
    setHovered,
    setActive,
    triggerPulse,
    getState,
    dispose,
  }
}

/**
 * Create a custom polygon detection zone mesh
 *
 * Uses BufferGeometry to create a quad directly in 3D space (XZ plane).
 *
 * @param vertices - Array of 4 vertices in world coordinates { x, z }
 * @param isActive - Whether the zone is in active (detecting) state
 * @returns The detection zone mesh
 */
export function createCustomDetectionZone(
  vertices: DetectionZoneVertex[],
  isActive = false
): THREE.Mesh {
  if (vertices.length < 3) {
    throw new Error('Detection zone requires at least 3 vertices')
  }

  // Create BufferGeometry for a quad in XZ plane
  const geometry = new THREE.BufferGeometry()

  // Height above ground
  const y = 0.15

  // For 4 vertices, create 2 triangles (0-1-2 and 0-2-3)
  const positions: number[] = []
  const v0 = vertices[0]!
  const v1 = vertices[1]!
  const v2 = vertices[2]!
  const v3 = vertices[3] ?? vertices[2]! // Fallback for triangles

  // Triangle 1: v0 -> v1 -> v2
  positions.push(v0.x, y, v0.z)
  positions.push(v1.x, y, v1.z)
  positions.push(v2.x, y, v2.z)

  // Triangle 2: v0 -> v2 -> v3 (only if we have 4 vertices)
  if (vertices.length >= 4) {
    positions.push(v0.x, y, v0.z)
    positions.push(v2.x, y, v2.z)
    positions.push(v3.x, y, v3.z)
  }

  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geometry.computeVertexNormals()

  // Create material - visible green/red
  const material = new THREE.MeshBasicMaterial({
    color: isActive ? COLORS.zoneActive : COLORS.zoneIdle,
    transparent: true,
    opacity: 0.3,
    side: THREE.DoubleSide,
    depthWrite: false,
  })

  const mesh = new THREE.Mesh(geometry, material)
  mesh.name = 'camera-detection-zone-custom'

  return mesh
}

/**
 * Update custom detection zone state (active/idle)
 */
export function updateDetectionZoneState(
  mesh: THREE.Mesh,
  isActive: boolean
): void {
  const material = mesh.material as THREE.MeshBasicMaterial
  material.color.setHex(isActive ? COLORS.zoneActive : COLORS.zoneIdle)
  material.opacity = isActive
    ? DIMS.detectionZone.opacity * 2
    : DIMS.detectionZone.opacity
}
