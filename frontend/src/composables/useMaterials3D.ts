/**
 * useMaterials3D - PBR Materials Library for 3D Yard
 *
 * Provides:
 * - PBR material presets for containers, concrete, asphalt, glass
 * - Procedural texture generation (no external assets)
 * - Environment map application
 * - Material caching for performance
 */

import { shallowRef, type ShallowRef } from 'vue'
import * as THREE from 'three'

export interface MaterialPreset {
  name: string
  color: number
  metalness: number
  roughness: number
  envMapIntensity: number
  transparent?: boolean
  opacity?: number
  side?: THREE.Side
}

// Predefined material presets for different surface types
export const MATERIAL_PRESETS: Record<string, MaterialPreset> = {
  // Container materials
  containerMetal: {
    name: 'Container Metal',
    color: 0x3b82f6,
    metalness: 0.85,
    roughness: 0.35,
    envMapIntensity: 0.8,
  },
  containerPainted: {
    name: 'Container Painted',
    color: 0x64748b,
    metalness: 0.2,
    roughness: 0.55,
    envMapIntensity: 0.4,
  },
  containerRusted: {
    name: 'Container Rusted',
    color: 0x8b5c3f,
    metalness: 0.6,
    roughness: 0.75,
    envMapIntensity: 0.3,
  },

  // Infrastructure materials
  concrete: {
    name: 'Concrete',
    color: 0x94a3b8,
    metalness: 0.0,
    roughness: 0.9,
    envMapIntensity: 0.15,
  },
  concreteDark: {
    name: 'Concrete Dark',
    color: 0x64748b,
    metalness: 0.0,
    roughness: 0.85,
    envMapIntensity: 0.1,
  },
  asphalt: {
    name: 'Asphalt',
    color: 0x374151,
    metalness: 0.0,
    roughness: 0.95,
    envMapIntensity: 0.05,
  },
  asphaltWet: {
    name: 'Asphalt Wet',
    color: 0x1f2937,
    metalness: 0.1,
    roughness: 0.6,
    envMapIntensity: 0.3,
  },

  // Building materials
  buildingWall: {
    name: 'Building Wall',
    color: 0xf1f5f9,
    metalness: 0.0,
    roughness: 0.8,
    envMapIntensity: 0.2,
  },
  buildingRoof: {
    name: 'Building Roof',
    color: 0x475569,
    metalness: 0.3,
    roughness: 0.6,
    envMapIntensity: 0.4,
  },
  glass: {
    name: 'Glass',
    color: 0x87ceeb,
    metalness: 0.0,
    roughness: 0.05,
    envMapIntensity: 1.5,
    transparent: true,
    opacity: 0.3,
  },

  // Ground materials
  grass: {
    name: 'Grass',
    color: 0x4ade80,
    metalness: 0.0,
    roughness: 0.95,
    envMapIntensity: 0.1,
  },
  dirt: {
    name: 'Dirt',
    color: 0x92400e,
    metalness: 0.0,
    roughness: 0.95,
    envMapIntensity: 0.05,
  },

  // Metal materials
  steelShiny: {
    name: 'Steel Shiny',
    color: 0xc0c0c0,
    metalness: 0.95,
    roughness: 0.2,
    envMapIntensity: 1.2,
  },
  steelBrushed: {
    name: 'Steel Brushed',
    color: 0xa8a8a8,
    metalness: 0.9,
    roughness: 0.45,
    envMapIntensity: 0.8,
  },

  // Railway
  railTrack: {
    name: 'Rail Track',
    color: 0x78716c,
    metalness: 0.8,
    roughness: 0.5,
    envMapIntensity: 0.5,
  },
  railBed: {
    name: 'Rail Bed',
    color: 0x57534e,
    metalness: 0.0,
    roughness: 0.95,
    envMapIntensity: 0.05,
  },
}

// Container status colors (for colorizing container materials)
export const CONTAINER_STATUS_COLORS = {
  LADEN: 0x3b82f6, // Blue
  EMPTY: 0x22c55e, // Green
  DAMAGED: 0xef4444, // Red
  RESERVED: 0xf59e0b, // Amber
  DEFAULT: 0x64748b, // Slate
}

// Container dwell time colors (for heat map visualization)
export const CONTAINER_DWELL_COLORS = {
  fresh: 0x22c55e, // 0-7 days: Green
  normal: 0xf59e0b, // 7-14 days: Amber
  aged: 0xf97316, // 14-21 days: Orange
  critical: 0xef4444, // 21+ days: Red
}

export function useMaterials3D() {
  // Material cache for reuse
  const materialCache: ShallowRef<Map<string, THREE.MeshStandardMaterial>> = shallowRef(new Map())
  const textureCache: ShallowRef<Map<string, THREE.Texture>> = shallowRef(new Map())

  // Current environment map (set by useEnvironment3D)
  const currentEnvMap: ShallowRef<THREE.Texture | null> = shallowRef(null)

  /**
   * Set the environment map for all materials.
   */
  function setEnvironmentMap(envMap: THREE.Texture | null): void {
    currentEnvMap.value = envMap

    // Update all cached materials with new env map
    materialCache.value.forEach((material) => {
      material.envMap = envMap
      material.needsUpdate = true
    })
  }

  /**
   * Create a PBR material from a preset.
   */
  function createMaterial(
    presetKey: keyof typeof MATERIAL_PRESETS | string,
    colorOverride?: number | THREE.Color
  ): THREE.MeshStandardMaterial {
    const preset = MATERIAL_PRESETS[presetKey]

    if (!preset) {
      console.warn(`Material preset '${presetKey}' not found, using default`)
      return createMaterial('containerPainted', colorOverride)
    }

    const cacheKey = `${presetKey}_${colorOverride ?? preset.color}`

    // Check cache first
    const cached = materialCache.value.get(cacheKey)
    if (cached) {
      return cached.clone()
    }

    const color = colorOverride !== undefined
      ? (colorOverride instanceof THREE.Color ? colorOverride : new THREE.Color(colorOverride))
      : new THREE.Color(preset.color)

    const material = new THREE.MeshStandardMaterial({
      color,
      metalness: preset.metalness,
      roughness: preset.roughness,
      envMap: currentEnvMap.value,
      envMapIntensity: preset.envMapIntensity,
      transparent: preset.transparent ?? false,
      opacity: preset.opacity ?? 1.0,
      side: preset.side ?? THREE.FrontSide,
      flatShading: false,
    })

    // Cache the material
    materialCache.value.set(cacheKey, material)

    return material
  }

  /**
   * Create a container material with proper PBR settings.
   */
  function createContainerMaterial(
    color: number | THREE.Color,
    options: {
      metalness?: number
      roughness?: number
      envMapIntensity?: number
    } = {}
  ): THREE.MeshStandardMaterial {
    const {
      metalness = 0.85,
      roughness = 0.35,
      envMapIntensity = 0.8,
    } = options

    const material = new THREE.MeshStandardMaterial({
      color: color instanceof THREE.Color ? color : new THREE.Color(color),
      metalness,
      roughness,
      envMap: currentEnvMap.value,
      envMapIntensity,
      flatShading: false,
    })

    return material
  }

  /**
   * Apply environment map to an existing material.
   */
  function applyEnvMap(
    material: THREE.MeshStandardMaterial,
    envMap: THREE.Texture,
    intensity?: number
  ): void {
    material.envMap = envMap
    if (intensity !== undefined) {
      material.envMapIntensity = intensity
    }
    material.needsUpdate = true
  }

  /**
   * Create procedural noise texture (for surface variation).
   */
  function createNoiseTexture(
    size: number = 256,
    intensity: number = 0.1
  ): THREE.DataTexture {
    const cacheKey = `noise_${size}_${intensity}`
    const cached = textureCache.value.get(cacheKey)
    if (cached) {
      return cached as THREE.DataTexture
    }

    const data = new Uint8Array(size * size * 4)

    for (let i = 0; i < size * size; i++) {
      const noise = 128 + (Math.random() - 0.5) * intensity * 255
      data[i * 4] = noise
      data[i * 4 + 1] = noise
      data[i * 4 + 2] = noise
      data[i * 4 + 3] = 255
    }

    const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat)
    texture.wrapS = THREE.RepeatWrapping
    texture.wrapT = THREE.RepeatWrapping
    texture.needsUpdate = true

    textureCache.value.set(cacheKey, texture)
    return texture
  }

  /**
   * Create procedural concrete texture.
   */
  function createConcreteTexture(size: number = 256): THREE.DataTexture {
    const cacheKey = `concrete_${size}`
    const cached = textureCache.value.get(cacheKey)
    if (cached) {
      return cached as THREE.DataTexture
    }

    const data = new Uint8Array(size * size * 4)

    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const i = (y * size + x) * 4

        // Base noise
        let noise = 180 + Math.random() * 30

        // Add larger-scale variation
        const largeNoise = Math.sin(x * 0.1) * Math.cos(y * 0.1) * 10
        noise += largeNoise

        // Add occasional darker spots (aggregate)
        if (Math.random() < 0.05) {
          noise -= 40
        }

        data[i] = Math.min(255, Math.max(0, noise))
        data[i + 1] = Math.min(255, Math.max(0, noise - 5))
        data[i + 2] = Math.min(255, Math.max(0, noise - 10))
        data[i + 3] = 255
      }
    }

    const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat)
    texture.wrapS = THREE.RepeatWrapping
    texture.wrapT = THREE.RepeatWrapping
    texture.needsUpdate = true

    textureCache.value.set(cacheKey, texture)
    return texture
  }

  /**
   * Create procedural asphalt texture.
   */
  function createAsphaltTexture(size: number = 256): THREE.DataTexture {
    const cacheKey = `asphalt_${size}`
    const cached = textureCache.value.get(cacheKey)
    if (cached) {
      return cached as THREE.DataTexture
    }

    const data = new Uint8Array(size * size * 4)

    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const i = (y * size + x) * 4

        // Dark base with fine grain
        let noise = 50 + Math.random() * 20

        // Add lighter specks (aggregate)
        if (Math.random() < 0.1) {
          noise += 30 + Math.random() * 20
        }

        data[i] = noise
        data[i + 1] = noise
        data[i + 2] = noise + 5
        data[i + 3] = 255
      }
    }

    const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat)
    texture.wrapS = THREE.RepeatWrapping
    texture.wrapT = THREE.RepeatWrapping
    texture.needsUpdate = true

    textureCache.value.set(cacheKey, texture)
    return texture
  }

  /**
   * Create corrugated container bump map.
   */
  function createContainerBumpMap(
    width: number = 256,
    height: number = 64
  ): THREE.DataTexture {
    const cacheKey = `container_bump_${width}_${height}`
    const cached = textureCache.value.get(cacheKey)
    if (cached) {
      return cached as THREE.DataTexture
    }

    const data = new Uint8Array(width * height * 4)

    const corrugationWidth = width / 12 // Number of corrugations

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const i = (y * width + x) * 4

        // Create corrugation pattern (sine wave)
        const corrugation = Math.sin((x / corrugationWidth) * Math.PI * 2)
        const value = 128 + corrugation * 60

        data[i] = value
        data[i + 1] = value
        data[i + 2] = value
        data[i + 3] = 255
      }
    }

    const texture = new THREE.DataTexture(data, width, height, THREE.RGBAFormat)
    texture.wrapS = THREE.RepeatWrapping
    texture.wrapT = THREE.RepeatWrapping
    texture.needsUpdate = true

    textureCache.value.set(cacheKey, texture)
    return texture
  }

  /**
   * Get container color based on status.
   */
  function getContainerStatusColor(status: keyof typeof CONTAINER_STATUS_COLORS | string): number {
    return CONTAINER_STATUS_COLORS[status as keyof typeof CONTAINER_STATUS_COLORS]
      ?? CONTAINER_STATUS_COLORS.DEFAULT
  }

  /**
   * Get container color based on dwell time (days).
   */
  function getContainerDwellColor(days: number): number {
    if (days <= 7) return CONTAINER_DWELL_COLORS.fresh
    if (days <= 14) return CONTAINER_DWELL_COLORS.normal
    if (days <= 21) return CONTAINER_DWELL_COLORS.aged
    return CONTAINER_DWELL_COLORS.critical
  }

  /**
   * Interpolate between two colors.
   */
  function lerpColor(color1: number, color2: number, t: number): THREE.Color {
    const c1 = new THREE.Color(color1)
    const c2 = new THREE.Color(color2)
    return c1.lerp(c2, Math.max(0, Math.min(1, t)))
  }

  /**
   * Clear all cached materials and textures.
   */
  function clearCache(): void {
    materialCache.value.forEach((material) => material.dispose())
    materialCache.value.clear()

    textureCache.value.forEach((texture) => texture.dispose())
    textureCache.value.clear()
  }

  /**
   * Dispose all resources.
   */
  function dispose(): void {
    clearCache()
    currentEnvMap.value = null
  }

  return {
    // State
    currentEnvMap,
    materialCache,

    // Environment
    setEnvironmentMap,

    // Material creation
    createMaterial,
    createContainerMaterial,
    applyEnvMap,

    // Procedural textures
    createNoiseTexture,
    createConcreteTexture,
    createAsphaltTexture,
    createContainerBumpMap,

    // Color utilities
    getContainerStatusColor,
    getContainerDwellColor,
    lerpColor,

    // Presets
    MATERIAL_PRESETS,
    CONTAINER_STATUS_COLORS,
    CONTAINER_DWELL_COLORS,

    // Cleanup
    clearCache,
    dispose,
  }
}
