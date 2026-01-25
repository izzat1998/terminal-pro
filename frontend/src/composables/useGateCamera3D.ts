/**
 * Gate Camera 3D Composable
 *
 * Creates a realistic 3D security camera model for the yard scene.
 * Supports hover/active states and pulse animation on detection.
 */

import * as THREE from 'three'

/** Camera visual states */
export type CameraState = 'normal' | 'hovered' | 'active'

/** Colors for different states */
const COLORS = {
  body: 0x2d3436,           // Dark gray camera body
  bodyHover: 0x3d4446,      // Slightly lighter on hover
  lens: 0x0a0a0a,           // Black lens
  lensGlass: 0x1a1a2e,      // Dark blue-ish glass
  metal: 0x8395a7,          // Metallic silver
  base: 0x636e72,           // Concrete gray
  emissiveHover: 0x00d9ff,  // Cyan glow on hover
  emissiveActive: 0x00ffaa, // Green glow when active
  emissivePulse: 0xffff00,  // Yellow flash on detection
}

/** Camera dimensions in meters */
const DIMS = {
  body: { width: 0.4, height: 0.25, depth: 0.2 },
  lens: { radius: 0.04, length: 0.06 },
  bracket: { width: 0.15, height: 0.1, depth: 0.1 },
  pole: { radius: 0.04, height: 2.5 },
  base: { radius: 0.15, height: 0.05 },
  tilt: -15 * (Math.PI / 180), // 15 degrees downward
}

export interface UseGateCamera3DOptions {
  /** Initial camera state */
  initialState?: CameraState
}

export interface UseGateCamera3DReturn {
  /** The camera mesh group */
  mesh: THREE.Group
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
  const { initialState = 'normal' } = options

  let currentState: CameraState = initialState
  let pulseAnimationId: number | null = null

  // Material references for state changes
  const materials: {
    body: THREE.MeshStandardMaterial
    lens: THREE.MeshStandardMaterial
    lensGlass: THREE.MeshStandardMaterial
    metal: THREE.MeshStandardMaterial
    base: THREE.MeshStandardMaterial
  } = {} as typeof materials

  // Create materials
  function createMaterials(): void {
    materials.body = new THREE.MeshStandardMaterial({
      color: COLORS.body,
      roughness: 0.7,
      metalness: 0.2,
    })

    materials.lens = new THREE.MeshStandardMaterial({
      color: COLORS.lens,
      roughness: 0.3,
      metalness: 0.8,
    })

    materials.lensGlass = new THREE.MeshStandardMaterial({
      color: COLORS.lensGlass,
      roughness: 0.1,
      metalness: 0.9,
      transparent: true,
      opacity: 0.8,
    })

    materials.metal = new THREE.MeshStandardMaterial({
      color: COLORS.metal,
      roughness: 0.4,
      metalness: 0.7,
    })

    materials.base = new THREE.MeshStandardMaterial({
      color: COLORS.base,
      roughness: 0.9,
      metalness: 0.1,
    })
  }

  // Create camera mesh group
  function createCameraMesh(): THREE.Group {
    createMaterials()

    const group = new THREE.Group()
    group.name = 'gate-camera'

    // Base (flat cylinder on ground)
    const baseGeom = new THREE.CylinderGeometry(
      DIMS.base.radius,
      DIMS.base.radius * 1.1,
      DIMS.base.height,
      16
    )
    const baseMesh = new THREE.Mesh(baseGeom, materials.base)
    baseMesh.position.y = DIMS.base.height / 2
    baseMesh.castShadow = true
    baseMesh.receiveShadow = true
    baseMesh.name = 'camera-base'
    group.add(baseMesh)

    // Pole (cylinder)
    const poleGeom = new THREE.CylinderGeometry(
      DIMS.pole.radius,
      DIMS.pole.radius,
      DIMS.pole.height,
      12
    )
    const poleMesh = new THREE.Mesh(poleGeom, materials.metal)
    poleMesh.position.y = DIMS.base.height + DIMS.pole.height / 2
    poleMesh.castShadow = true
    poleMesh.name = 'camera-pole'
    group.add(poleMesh)

    // Camera head group (for tilting)
    const headGroup = new THREE.Group()
    headGroup.name = 'camera-head'
    headGroup.position.y = DIMS.base.height + DIMS.pole.height
    headGroup.rotation.x = DIMS.tilt
    group.add(headGroup)

    // Bracket (small box connecting pole to camera)
    const bracketGeom = new THREE.BoxGeometry(
      DIMS.bracket.width,
      DIMS.bracket.height,
      DIMS.bracket.depth
    )
    const bracketMesh = new THREE.Mesh(bracketGeom, materials.metal)
    bracketMesh.position.set(0, -DIMS.bracket.height / 2, DIMS.bracket.depth / 2)
    bracketMesh.castShadow = true
    bracketMesh.name = 'camera-bracket'
    headGroup.add(bracketMesh)

    // Camera body (main box)
    const bodyGeom = new THREE.BoxGeometry(
      DIMS.body.width,
      DIMS.body.height,
      DIMS.body.depth
    )
    const bodyMesh = new THREE.Mesh(bodyGeom, materials.body)
    bodyMesh.position.set(0, -DIMS.bracket.height / 2, DIMS.bracket.depth + DIMS.body.depth / 2)
    bodyMesh.castShadow = true
    bodyMesh.name = 'camera-body'
    headGroup.add(bodyMesh)

    // Lens housing (cylinder)
    const lensHousingGeom = new THREE.CylinderGeometry(
      DIMS.lens.radius * 1.5,
      DIMS.lens.radius * 1.3,
      DIMS.lens.length,
      16
    )
    const lensHousingMesh = new THREE.Mesh(lensHousingGeom, materials.lens)
    lensHousingMesh.rotation.x = Math.PI / 2
    lensHousingMesh.position.set(
      0,
      -DIMS.bracket.height / 2,
      DIMS.bracket.depth + DIMS.body.depth + DIMS.lens.length / 2
    )
    lensHousingMesh.castShadow = true
    lensHousingMesh.name = 'camera-lens-housing'
    headGroup.add(lensHousingMesh)

    // Lens glass (front of lens)
    const lensGlassGeom = new THREE.CircleGeometry(DIMS.lens.radius * 1.2, 16)
    const lensGlassMesh = new THREE.Mesh(lensGlassGeom, materials.lensGlass)
    lensGlassMesh.position.set(
      0,
      -DIMS.bracket.height / 2,
      DIMS.bracket.depth + DIMS.body.depth + DIMS.lens.length + 0.01
    )
    lensGlassMesh.name = 'camera-lens-glass'
    headGroup.add(lensGlassMesh)

    // Small indicator LED (on top of body)
    const ledGeom = new THREE.SphereGeometry(0.015, 8, 8)
    const ledMat = new THREE.MeshStandardMaterial({
      color: 0x00ff00,
      emissive: 0x00ff00,
      emissiveIntensity: 0.5,
    })
    const ledMesh = new THREE.Mesh(ledGeom, ledMat)
    ledMesh.position.set(
      DIMS.body.width / 2 - 0.03,
      -DIMS.bracket.height / 2 + DIMS.body.height / 2 + 0.015,
      DIMS.bracket.depth + DIMS.body.depth / 2
    )
    ledMesh.name = 'camera-led'
    headGroup.add(ledMesh)

    // Set initial state
    updateVisualState(currentState)

    return group
  }

  const mesh = createCameraMesh()

  // Update visual appearance based on state
  function updateVisualState(state: CameraState): void {
    switch (state) {
      case 'hovered':
        materials.body.emissive.setHex(COLORS.emissiveHover)
        materials.body.emissiveIntensity = 0.15
        materials.metal.emissive.setHex(COLORS.emissiveHover)
        materials.metal.emissiveIntensity = 0.1
        break

      case 'active':
        materials.body.emissive.setHex(COLORS.emissiveActive)
        materials.body.emissiveIntensity = 0.2
        materials.metal.emissive.setHex(COLORS.emissiveActive)
        materials.metal.emissiveIntensity = 0.15
        break

      case 'normal':
      default:
        materials.body.emissive.setHex(0x000000)
        materials.body.emissiveIntensity = 0
        materials.metal.emissive.setHex(0x000000)
        materials.metal.emissiveIntensity = 0
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
    const duration = 300 // 300ms pulse

    // Store original emissive state
    const originalBodyEmissive = materials.body.emissive.getHex()
    const originalBodyIntensity = materials.body.emissiveIntensity
    const originalMetalEmissive = materials.metal.emissive.getHex()
    const originalMetalIntensity = materials.metal.emissiveIntensity

    function animate(currentTime: number): void {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1.0)

      // Pulse intensity: 0 -> 1 -> 0 (sine wave)
      const intensity = Math.sin(progress * Math.PI)

      // Apply pulse color
      materials.body.emissive.setHex(COLORS.emissivePulse)
      materials.body.emissiveIntensity = intensity * 0.8
      materials.metal.emissive.setHex(COLORS.emissivePulse)
      materials.metal.emissiveIntensity = intensity * 0.6

      if (progress < 1.0) {
        pulseAnimationId = requestAnimationFrame(animate)
      } else {
        // Restore original state
        materials.body.emissive.setHex(originalBodyEmissive)
        materials.body.emissiveIntensity = originalBodyIntensity
        materials.metal.emissive.setHex(originalMetalEmissive)
        materials.metal.emissiveIntensity = originalMetalIntensity
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

    // Dispose geometries and materials
    mesh.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.geometry.dispose()
        if (Array.isArray(child.material)) {
          child.material.forEach((mat) => mat.dispose())
        } else {
          child.material.dispose()
        }
      }
    })

    // Clear from parent if attached
    if (mesh.parent) {
      mesh.parent.remove(mesh)
    }
  }

  return {
    mesh,
    setHovered,
    setActive,
    triggerPulse,
    getState,
    dispose,
  }
}
