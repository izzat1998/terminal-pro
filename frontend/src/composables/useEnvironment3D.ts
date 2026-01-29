/**
 * useEnvironment3D - HDR Environment & Atmosphere Composable
 *
 * Provides:
 * - HDR environment map loading with PMREM generation
 * - Procedural gradient sky fallback (no external assets)
 * - Time-of-day lighting adjustments
 * - Atmospheric fog with exponential falloff
 */

import { shallowRef, type ShallowRef } from 'vue'
import * as THREE from 'three'
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js'

export interface EnvironmentOptions {
  hdrPath?: string
  intensity?: number
  rotation?: number
  backgroundColor?: number
}

export interface TimeOfDayConfig {
  hour: number // 0-24
  sunColor: THREE.Color
  skyColor: THREE.Color
  groundColor: THREE.Color
  intensity: number
  fogColor: THREE.Color
  fogDensity: number
}

// Predefined time-of-day configurations
// Fog density values are kept subtle (0.0002-0.0004) for large terminal yards
const TIME_PRESETS: Record<string, TimeOfDayConfig> = {
  dawn: {
    hour: 6,
    sunColor: new THREE.Color(0xffd4a6),
    skyColor: new THREE.Color(0xffecd2),
    groundColor: new THREE.Color(0x8b9dc3),
    intensity: 0.6,
    fogColor: new THREE.Color(0xd4e5f7),
    fogDensity: 0.0004,  // Slightly more fog at dawn
  },
  morning: {
    hour: 9,
    sunColor: new THREE.Color(0xfff5e6),
    skyColor: new THREE.Color(0xe8f4fc),
    groundColor: new THREE.Color(0x94a3b8),
    intensity: 0.9,
    fogColor: new THREE.Color(0xe8f4f8),
    fogDensity: 0.0003,
  },
  midday: {
    hour: 12,
    sunColor: new THREE.Color(0xffffff),
    skyColor: new THREE.Color(0x87ceeb),
    groundColor: new THREE.Color(0x64748b),
    intensity: 1.0,
    fogColor: new THREE.Color(0xf0f9ff),
    fogDensity: 0.0002,  // Clearest at midday
  },
  afternoon: {
    hour: 15,
    sunColor: new THREE.Color(0xfff8e7),
    skyColor: new THREE.Color(0xb4d7e8),
    groundColor: new THREE.Color(0x78909c),
    intensity: 0.95,
    fogColor: new THREE.Color(0xe8f4f8),
    fogDensity: 0.00025,
  },
  sunset: {
    hour: 18,
    sunColor: new THREE.Color(0xffb347),
    skyColor: new THREE.Color(0xff7f50),
    groundColor: new THREE.Color(0x4a5568),
    intensity: 0.7,
    fogColor: new THREE.Color(0xffd4b8),
    fogDensity: 0.0004,  // More atmospheric at sunset
  },
  evening: {
    hour: 20,
    sunColor: new THREE.Color(0x9ca3af),
    skyColor: new THREE.Color(0x374151),
    groundColor: new THREE.Color(0x1f2937),
    intensity: 0.4,
    fogColor: new THREE.Color(0x4b5563),
    fogDensity: 0.0005,  // Slightly more fog in evening
  },
}

export function useEnvironment3D() {
  const envMap: ShallowRef<THREE.Texture | null> = shallowRef(null)
  const pmremGenerator: ShallowRef<THREE.PMREMGenerator | null> = shallowRef(null)
  const currentTimeOfDay = shallowRef<string>('midday')

  /**
   * Load HDR environment map for realistic reflections.
   * Falls back to procedural sky if loading fails.
   */
  async function loadEnvironment(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    options: EnvironmentOptions = {}
  ): Promise<THREE.Texture | null> {
    const { hdrPath, intensity = 1.0, rotation = 0 } = options

    // Initialize PMREM generator for environment map processing
    pmremGenerator.value = new THREE.PMREMGenerator(renderer)
    pmremGenerator.value.compileEquirectangularShader()

    if (hdrPath) {
      try {
        const texture = await loadHDR(hdrPath, rotation)
        envMap.value = texture
        scene.environment = texture
        return texture
      } catch (error) {
        console.warn('Failed to load HDR environment, using procedural sky:', error)
      }
    }

    // Fallback to procedural sky
    const proceduralEnv = createProceduralSkyEnvironment(renderer, intensity)
    envMap.value = proceduralEnv
    scene.environment = proceduralEnv

    return proceduralEnv
  }

  /**
   * Load HDR file using RGBELoader.
   */
  function loadHDR(
    path: string,
    rotation: number
  ): Promise<THREE.Texture> {
    return new Promise((resolve, reject) => {
      const loader = new RGBELoader()

      loader.load(
        path,
        (texture) => {
          if (!pmremGenerator.value) {
            reject(new Error('PMREM generator not initialized'))
            return
          }

          texture.mapping = THREE.EquirectangularReflectionMapping

          const envTexture = pmremGenerator.value.fromEquirectangular(texture).texture
          envTexture.colorSpace = THREE.SRGBColorSpace

          // Apply rotation if specified
          if (rotation !== 0) {
            envTexture.offset.x = rotation / (2 * Math.PI)
          }

          texture.dispose()
          resolve(envTexture)
        },
        undefined,
        reject
      )
    })
  }

  /**
   * Create a procedural gradient sky for environment reflections.
   * This provides realistic ambient lighting without external assets.
   */
  function createProceduralSkyEnvironment(
    renderer: THREE.WebGLRenderer,
    intensity: number = 1.0
  ): THREE.Texture {
    const size = 256
    const data = new Float32Array(size * size * 4)

    // Sky gradient colors (top to horizon to ground)
    const skyTop = new THREE.Color(0x87ceeb) // Light blue
    const skyHorizon = new THREE.Color(0xd4e5f7) // Pale blue
    const ground = new THREE.Color(0x94a3b8) // Slate gray
    const tempColor = new THREE.Color() // Reusable to avoid per-pixel allocation

    for (let y = 0; y < size; y++) {
      // Calculate normalized position once per row (constant across x)
      const normalizedY = y / size

      if (normalizedY > 0.5) {
        const t = (normalizedY - 0.5) * 2
        tempColor.copy(skyHorizon).lerp(skyTop, t)
      } else {
        const t = normalizedY * 2
        tempColor.copy(ground).lerp(skyHorizon, t)
      }

      const r = tempColor.r * intensity
      const g = tempColor.g * intensity
      const b = tempColor.b * intensity

      for (let x = 0; x < size; x++) {
        const i = (y * size + x) * 4
        data[i] = r
        data[i + 1] = g
        data[i + 2] = b
        data[i + 3] = 1.0
      }
    }

    const texture = new THREE.DataTexture(
      data,
      size,
      size,
      THREE.RGBAFormat,
      THREE.FloatType
    )
    texture.mapping = THREE.EquirectangularReflectionMapping
    texture.needsUpdate = true

    if (!pmremGenerator.value) {
      pmremGenerator.value = new THREE.PMREMGenerator(renderer)
      pmremGenerator.value.compileEquirectangularShader()
    }

    const envTexture = pmremGenerator.value.fromEquirectangular(texture).texture
    texture.dispose()

    return envTexture
  }

  /**
   * Create a procedural sky mesh for the scene background.
   * Renders as a large sphere with gradient shader.
   */
  function createProceduralSky(options: {
    topColor?: THREE.Color
    horizonColor?: THREE.Color
    groundColor?: THREE.Color
    offset?: number
    exponent?: number
  } = {}): THREE.Mesh {
    const {
      topColor = new THREE.Color(0x87ceeb),
      horizonColor = new THREE.Color(0xd4e5f7),
      groundColor = new THREE.Color(0x94a3b8),
      offset = 0,
      exponent = 0.6,
    } = options

    const vertexShader = `
      varying vec3 vWorldPosition;
      void main() {
        vec4 worldPosition = modelMatrix * vec4(position, 1.0);
        vWorldPosition = worldPosition.xyz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `

    const fragmentShader = `
      uniform vec3 topColor;
      uniform vec3 horizonColor;
      uniform vec3 groundColor;
      uniform float offset;
      uniform float exponent;
      varying vec3 vWorldPosition;

      void main() {
        float h = normalize(vWorldPosition + offset).y;

        if (h > 0.0) {
          // Sky gradient
          gl_FragColor = vec4(mix(horizonColor, topColor, pow(max(h, 0.0), exponent)), 1.0);
        } else {
          // Ground gradient
          gl_FragColor = vec4(mix(horizonColor, groundColor, pow(max(-h, 0.0), exponent)), 1.0);
        }
      }
    `

    const uniforms = {
      topColor: { value: topColor },
      horizonColor: { value: horizonColor },
      groundColor: { value: groundColor },
      offset: { value: offset },
      exponent: { value: exponent },
    }

    const skyGeometry = new THREE.SphereGeometry(5000, 32, 32)
    const skyMaterial = new THREE.ShaderMaterial({
      uniforms,
      vertexShader,
      fragmentShader,
      side: THREE.BackSide,
      depthWrite: false,
    })

    const sky = new THREE.Mesh(skyGeometry, skyMaterial)
    sky.name = 'ProceduralSky'
    sky.renderOrder = -1000

    return sky
  }

  /**
   * Set time of day, affecting lighting colors and fog.
   * Returns configuration for use with lights.
   */
  function setTimeOfDay(
    hour: number
  ): TimeOfDayConfig {
    // Clamp hour to 0-24
    const h = Math.max(0, Math.min(24, hour))

    // Find nearest presets and interpolate
    const presets = Object.values(TIME_PRESETS).sort((a, b) => a.hour - b.hour)

    // Ensure we have presets (always true since TIME_PRESETS is const)
    if (presets.length === 0) {
      // This never happens but satisfies TypeScript
      return {
        hour: 12,
        sunColor: new THREE.Color(0xffffff),
        skyColor: new THREE.Color(0x87ceeb),
        groundColor: new THREE.Color(0x64748b),
        intensity: 1.0,
        fogColor: new THREE.Color(0xf0f9ff),
        fogDensity: 0.0002,
      }
    }

    // Find surrounding presets with guaranteed non-null values
    const lastPreset = presets[presets.length - 1]!
    const firstPreset = presets[0]!

    let lower: TimeOfDayConfig = lastPreset
    let upper: TimeOfDayConfig = firstPreset

    for (let i = 0; i < presets.length; i++) {
      const preset = presets[i]!
      if (preset.hour <= h) {
        lower = preset
        const nextIndex = (i + 1) % presets.length
        upper = presets[nextIndex]!
      }
    }

    // Calculate interpolation factor
    let t: number
    if (upper.hour > lower.hour) {
      t = (h - lower.hour) / (upper.hour - lower.hour)
    } else {
      // Wrap around midnight
      const range = 24 - lower.hour + upper.hour
      t = h >= lower.hour
        ? (h - lower.hour) / range
        : (24 - lower.hour + h) / range
    }

    // Interpolate colors
    const config: TimeOfDayConfig = {
      hour: h,
      sunColor: lower.sunColor.clone().lerp(upper.sunColor, t),
      skyColor: lower.skyColor.clone().lerp(upper.skyColor, t),
      groundColor: lower.groundColor.clone().lerp(upper.groundColor, t),
      intensity: THREE.MathUtils.lerp(lower.intensity, upper.intensity, t),
      fogColor: lower.fogColor.clone().lerp(upper.fogColor, t),
      fogDensity: THREE.MathUtils.lerp(lower.fogDensity, upper.fogDensity, t),
    }

    // Store current time
    currentTimeOfDay.value = getTimeOfDayName(h)

    return config
  }

  /**
   * Get time of day name from hour.
   */
  function getTimeOfDayName(hour: number): string {
    if (hour >= 5 && hour < 8) return 'dawn'
    if (hour >= 8 && hour < 11) return 'morning'
    if (hour >= 11 && hour < 14) return 'midday'
    if (hour >= 14 && hour < 17) return 'afternoon'
    if (hour >= 17 && hour < 20) return 'sunset'
    return 'evening'
  }

  /**
   * Create exponential fog for atmospheric depth.
   */
  function createFog(
    color: THREE.ColorRepresentation = 0xe8f4f8,
    density: number = 0.0015
  ): THREE.FogExp2 {
    return new THREE.FogExp2(color, density)
  }

  /**
   * Apply fog to scene with optional configuration.
   */
  function applyFog(
    scene: THREE.Scene,
    options: {
      color?: THREE.ColorRepresentation
      density?: number
      enabled?: boolean
    } = {}
  ): void {
    const { color = 0xe8f4f8, density = 0.0015, enabled = true } = options

    if (enabled) {
      scene.fog = createFog(color, density)
    } else {
      scene.fog = null
    }
  }

  /**
   * Cleanup resources.
   */
  function dispose(): void {
    if (envMap.value) {
      envMap.value.dispose()
      envMap.value = null
    }
    if (pmremGenerator.value) {
      pmremGenerator.value.dispose()
      pmremGenerator.value = null
    }
  }

  return {
    // State
    envMap,
    currentTimeOfDay,

    // Environment
    loadEnvironment,
    createProceduralSky,
    createProceduralSkyEnvironment,

    // Time of day
    setTimeOfDay,
    getTimeOfDayName,
    TIME_PRESETS,

    // Fog
    createFog,
    applyFog,

    // Cleanup
    dispose,
  }
}
