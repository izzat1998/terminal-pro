# 3D Sharpness Re-engineering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Achieve pixel-perfect crisp 3D terminal yard visualization at all zoom levels by removing post-processing overhead and fixing pixel ratio handling.

**Architecture:** Remove the EffectComposer post-processing pipeline entirely and use direct WebGL rendering with proper `devicePixelRatio` handling. Simplify the quality presets to only control essential settings (pixel ratio, antialias, shadows).

**Tech Stack:** Three.js r160+, Vue 3 Composition API, TypeScript

---

## Summary of Changes

| Action | File | Reason |
|--------|------|--------|
| **Delete** | `usePostProcessing.ts` | Causes blurriness via render-to-texture |
| **Delete** | `useEnvironment3D.ts` | No longer needed without post-processing |
| **Simplify** | `qualityPresets.ts` | Remove post-processing settings, keep only essential |
| **Simplify** | `YardView3D.vue` | Remove all post-processing code, direct render |
| **Simplify** | `useMaterials3D.ts` | Remove environment map dependencies |
| **Update** | `YardSettingsDrawer.vue` | Update quality descriptions |

---

## Task 1: Delete Post-Processing Composable

**Files:**
- Delete: `frontend/src/composables/usePostProcessing.ts`

**Step 1: Delete the file**

```bash
rm frontend/src/composables/usePostProcessing.ts
```

**Step 2: Verify deletion**

```bash
ls frontend/src/composables/usePostProcessing.ts 2>&1 | grep -q "No such file" && echo "DELETED" || echo "STILL EXISTS"
```

Expected: `DELETED`

**Step 3: Commit**

```bash
git add -A && git commit -m "refactor(3d): remove usePostProcessing composable

Post-processing pipeline was causing blurriness by rendering at incorrect
resolution. Direct rendering provides sharper output.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Delete Environment3D Composable

**Files:**
- Delete: `frontend/src/composables/useEnvironment3D.ts`

**Step 1: Delete the file**

```bash
rm frontend/src/composables/useEnvironment3D.ts
```

**Step 2: Verify deletion**

```bash
ls frontend/src/composables/useEnvironment3D.ts 2>&1 | grep -q "No such file" && echo "DELETED" || echo "STILL EXISTS"
```

Expected: `DELETED`

**Step 3: Commit**

```bash
git add -A && git commit -m "refactor(3d): remove useEnvironment3D composable

HDR environment maps are not needed for sharp rendering. Basic lighting
is sufficient and performs better.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Simplify Quality Presets

**Files:**
- Modify: `frontend/src/utils/qualityPresets.ts`

**Step 1: Replace the entire file with simplified version**

Replace `frontend/src/utils/qualityPresets.ts` with:

```typescript
/**
 * Quality Presets for 3D Yard Visualization
 *
 * Simplified presets focused on sharpness:
 * - Proper pixel ratio for crisp rendering
 * - Hardware MSAA anti-aliasing
 * - Shadow quality settings
 */

export type QualityLevel = 'low' | 'medium' | 'high' | 'ultra'

export interface QualityPreset {
  // Rendering
  pixelRatio: number
  antialias: boolean

  // Shadows
  shadows: boolean
  shadowMapSize: number

  // Tone mapping
  toneMapping: boolean
  toneMappingExposure: number

  // Container rendering
  containerEdges: boolean
  containerEdgeOpacity: number
}

export const QUALITY_PRESETS: Record<QualityLevel, QualityPreset> = {
  low: {
    pixelRatio: Math.min(window.devicePixelRatio, 1),
    antialias: false,
    shadows: false,
    shadowMapSize: 512,
    toneMapping: false,
    toneMappingExposure: 1.0,
    containerEdges: false,
    containerEdgeOpacity: 0,
  },

  medium: {
    pixelRatio: Math.min(window.devicePixelRatio, 2),
    antialias: true,
    shadows: true,
    shadowMapSize: 1024,
    toneMapping: true,
    toneMappingExposure: 1.0,
    containerEdges: false,
    containerEdgeOpacity: 0,
  },

  high: {
    pixelRatio: window.devicePixelRatio,
    antialias: true,
    shadows: true,
    shadowMapSize: 2048,
    toneMapping: true,
    toneMappingExposure: 1.0,
    containerEdges: true,
    containerEdgeOpacity: 0.15,
  },

  ultra: {
    pixelRatio: window.devicePixelRatio,
    antialias: true,
    shadows: true,
    shadowMapSize: 4096,
    toneMapping: true,
    toneMappingExposure: 1.0,
    containerEdges: true,
    containerEdgeOpacity: 0.15,
  },
}

/**
 * Auto-detect optimal quality level based on hardware capabilities.
 */
export function detectOptimalQuality(): QualityLevel {
  const canvas = document.createElement('canvas')
  const gl = canvas.getContext('webgl2')

  if (!gl) {
    return 'low'
  }

  const debugInfo = gl.getExtension('WEBGL_debug_renderer_info')
  const renderer = debugInfo
    ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
    : ''

  // Check for discrete GPU (NVIDIA, AMD, Intel Arc)
  const hasDiscreteGPU = /nvidia|radeon|geforce|rtx|gtx|arc\s*a\d/i.test(renderer)

  // Check for Apple Silicon (M1/M2/M3 - excellent GPU)
  const hasAppleSilicon = /apple\s*(m1|m2|m3|gpu)/i.test(renderer)

  // Check device memory if available
  const deviceMemory = (navigator as { deviceMemory?: number }).deviceMemory ?? 4
  const hasHighMemory = deviceMemory >= 8

  // Check logical processor count
  const processorCount = navigator.hardwareConcurrency ?? 4
  const hasMultiCore = processorCount >= 8

  // Scoring system
  let score = 0
  if (hasDiscreteGPU) score += 3
  if (hasAppleSilicon) score += 3
  if (hasHighMemory) score += 2
  if (hasMultiCore) score += 1

  if (score >= 5) return 'ultra'
  if (score >= 3) return 'high'
  if (score >= 1) return 'medium'
  return 'low'
}

/**
 * Get quality preset by level with optional overrides.
 */
export function getQualityPreset(
  level: QualityLevel,
  overrides?: Partial<QualityPreset>
): QualityPreset {
  return {
    ...QUALITY_PRESETS[level],
    ...overrides,
  }
}

/**
 * Quality level labels for UI display (Russian).
 */
export const QUALITY_LABELS: Record<QualityLevel, string> = {
  low: 'Низкое',
  medium: 'Среднее',
  high: 'Высокое',
  ultra: 'Ультра',
}

/**
 * Quality level descriptions for tooltips (Russian).
 */
export const QUALITY_DESCRIPTIONS: Record<QualityLevel, string> = {
  low: 'Базовое качество, максимальная производительность',
  medium: 'Чёткое изображение с тенями',
  high: 'Максимальная чёткость на любых дисплеях',
  ultra: 'Максимальная чёткость + улучшенные тени',
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: Errors about missing imports in YardView3D (expected, will fix in Task 5)

**Step 3: Commit**

```bash
git add frontend/src/utils/qualityPresets.ts && git commit -m "refactor(3d): simplify quality presets for sharpness

Remove all post-processing settings (SSAO, bloom, vignette, fog).
Focus on essential rendering settings:
- Proper pixel ratio (no artificial caps on high/ultra)
- Hardware MSAA anti-aliasing
- Shadow map quality

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Simplify Materials3D Composable

**Files:**
- Modify: `frontend/src/composables/useMaterials3D.ts`

**Step 1: Remove environment map dependencies**

In `frontend/src/composables/useMaterials3D.ts`, make these changes:

1. Remove the `currentEnvMap` ref and `setEnvironmentMap` function
2. Remove `envMap` from all material creation
3. Remove `applyEnvMap` function
4. Update the return statement

Replace the entire file with:

```typescript
/**
 * useMaterials3D - PBR Materials Library for 3D Yard
 *
 * Provides:
 * - PBR material presets for containers, concrete, asphalt, glass
 * - Procedural texture generation (no external assets)
 * - Material caching for performance
 */

import { shallowRef, type ShallowRef } from 'vue'
import * as THREE from 'three'

export interface MaterialPreset {
  name: string
  color: number
  metalness: number
  roughness: number
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
  },
  containerPainted: {
    name: 'Container Painted',
    color: 0x64748b,
    metalness: 0.2,
    roughness: 0.55,
  },
  containerRusted: {
    name: 'Container Rusted',
    color: 0x8b5c3f,
    metalness: 0.6,
    roughness: 0.75,
  },

  // Infrastructure materials
  concrete: {
    name: 'Concrete',
    color: 0x94a3b8,
    metalness: 0.0,
    roughness: 0.9,
  },
  concreteDark: {
    name: 'Concrete Dark',
    color: 0x64748b,
    metalness: 0.0,
    roughness: 0.85,
  },
  asphalt: {
    name: 'Asphalt',
    color: 0x374151,
    metalness: 0.0,
    roughness: 0.95,
  },
  asphaltWet: {
    name: 'Asphalt Wet',
    color: 0x1f2937,
    metalness: 0.1,
    roughness: 0.6,
  },

  // Building materials
  buildingWall: {
    name: 'Building Wall',
    color: 0xf1f5f9,
    metalness: 0.0,
    roughness: 0.8,
  },
  buildingRoof: {
    name: 'Building Roof',
    color: 0x475569,
    metalness: 0.3,
    roughness: 0.6,
  },
  glass: {
    name: 'Glass',
    color: 0x87ceeb,
    metalness: 0.0,
    roughness: 0.05,
    transparent: true,
    opacity: 0.3,
  },

  // Ground materials
  grass: {
    name: 'Grass',
    color: 0x4ade80,
    metalness: 0.0,
    roughness: 0.95,
  },
  dirt: {
    name: 'Dirt',
    color: 0x92400e,
    metalness: 0.0,
    roughness: 0.95,
  },

  // Metal materials
  steelShiny: {
    name: 'Steel Shiny',
    color: 0xc0c0c0,
    metalness: 0.95,
    roughness: 0.2,
  },
  steelBrushed: {
    name: 'Steel Brushed',
    color: 0xa8a8a8,
    metalness: 0.9,
    roughness: 0.45,
  },

  // Railway
  railTrack: {
    name: 'Rail Track',
    color: 0x78716c,
    metalness: 0.8,
    roughness: 0.5,
  },
  railBed: {
    name: 'Rail Bed',
    color: 0x57534e,
    metalness: 0.0,
    roughness: 0.95,
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
    } = {}
  ): THREE.MeshStandardMaterial {
    const {
      metalness = 0.85,
      roughness = 0.35,
    } = options

    const material = new THREE.MeshStandardMaterial({
      color: color instanceof THREE.Color ? color : new THREE.Color(color),
      metalness,
      roughness,
      flatShading: false,
    })

    return material
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
  }

  return {
    // State
    materialCache,

    // Material creation
    createMaterial,
    createContainerMaterial,

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
```

**Step 2: Verify no TypeScript errors in the file**

```bash
cd frontend && npx tsc --noEmit src/composables/useMaterials3D.ts 2>&1 | head -10
```

**Step 3: Commit**

```bash
git add frontend/src/composables/useMaterials3D.ts && git commit -m "refactor(3d): remove environment map from materials

Environment maps were adding subtle blur through reflections.
Direct material colors provide sharper visual output.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Simplify YardView3D Component

**Files:**
- Modify: `frontend/src/components/YardView3D.vue`

This is the main task - removing all post-processing code from the component.

**Step 1: Remove imports for deleted composables**

Remove these lines (around lines 23-25):
```typescript
import { useEnvironment3D } from '@/composables/useEnvironment3D'
import { usePostProcessing } from '@/composables/usePostProcessing'
```

Keep the useMaterials3D import but we'll simplify its usage.

**Step 2: Remove composable destructuring**

Remove these blocks (around lines 251-268):

```typescript
// REMOVE THIS BLOCK:
const {
  loadEnvironment,
  dispose: disposeEnvironment,
} = useEnvironment3D()

// REMOVE THIS BLOCK:
const {
  initComposer,
  setQuality: setPostProcessingQuality,
  resize: resizePostProcessing,
  render: renderPostProcessing,
  isInitialized: isPostProcessingInitialized,
  dispose: disposePostProcessing,
} = usePostProcessing()

// SIMPLIFY THIS BLOCK (remove setEnvironmentMap):
const {
  dispose: disposeMaterials,
} = useMaterials3D()
```

**Step 3: Simplify initScene function**

In `initScene()`, remove environment and post-processing initialization (around lines 545-565):

```typescript
// REMOVE THIS:
loadEnvironment(renderer.value, scene.value, {
  intensity: qualityPreset.envMapIntensity,
}).then((envTexture) => {
  if (envTexture) {
    setEnvironmentMap(envTexture)
  }
})

// REMOVE THIS:
initComposer(renderer.value, scene.value, camera.value, {
  ssao: qualityPreset.ssao,
  ssaoRadius: qualityPreset.ssaoRadius,
  bloom: qualityPreset.bloom,
  bloomThreshold: qualityPreset.bloomThreshold,
  bloomStrength: qualityPreset.bloomStrength,
  bloomRadius: qualityPreset.bloomRadius,
  vignette: qualityPreset.vignette,
  vignetteOffset: qualityPreset.vignetteOffset,
  vignetteDarkness: qualityPreset.vignetteDarkness,
  colorGrading: qualityPreset.colorGrading,
})
```

**Step 4: Simplify animate function**

Replace the render logic (around lines 584-588):

```typescript
// BEFORE:
if (isPostProcessingInitialized()) {
  renderPostProcessing()
} else {
  renderer.value.render(scene.value, camera.value)
}

// AFTER:
renderer.value.render(scene.value, camera.value)
```

**Step 5: Simplify handleQualityChange function**

Replace the function (around lines 957-982):

```typescript
// BEFORE: Complex function with post-processing updates
// AFTER: Simple function
function handleQualityChange(level: QualityLevel): void {
  if (level === qualityLevel.value) return

  qualityLevel.value = level
  const preset = getQualityPreset(level)

  // Update renderer settings
  if (renderer.value) {
    renderer.value.setPixelRatio(preset.pixelRatio)
    renderer.value.shadowMap.enabled = preset.shadows
    if (preset.toneMapping) {
      renderer.value.toneMapping = THREE.ACESFilmicToneMapping
      renderer.value.toneMappingExposure = preset.toneMappingExposure
    } else {
      renderer.value.toneMapping = THREE.NoToneMapping
    }
  }

  // Update shadow map size on main light
  if (scene.value) {
    scene.value.traverse((child) => {
      if (child instanceof THREE.DirectionalLight && child.castShadow) {
        child.shadow.mapSize.width = preset.shadowMapSize
        child.shadow.mapSize.height = preset.shadowMapSize
        child.shadow.map?.dispose()
        child.shadow.map = null
      }
    })
  }

  if (import.meta.env.DEV) console.log(`Quality changed to: ${level}`)
}
```

**Step 6: Simplify handleResize function**

Remove post-processing resize (around line 1112):

```typescript
// REMOVE THIS LINE:
resizePostProcessing(width, height, pixelRatio)
```

**Step 7: Simplify dispose function**

Remove post-processing and environment disposal (around lines 1144-1146):

```typescript
// REMOVE THESE LINES:
disposePostProcessing()
disposeEnvironment()

// KEEP THIS:
disposeMaterials()
```

**Step 8: Verify build succeeds**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: Build succeeds with no errors

**Step 9: Commit**

```bash
git add frontend/src/components/YardView3D.vue && git commit -m "refactor(3d): remove post-processing for maximum sharpness

- Remove EffectComposer pipeline (was causing blur)
- Remove environment map loading
- Direct renderer.render() for crisp output
- Simplify quality change handler
- Keep shadow and tone mapping settings

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Verify and Test

**Step 1: Build the frontend**

```bash
cd frontend && npm run build
```

Expected: Build succeeds

**Step 2: Run development server**

```bash
cd frontend && npm run dev
```

**Step 3: Visual verification checklist**

Open the yard view and verify:
- [ ] Containers are crisp and sharp at all zoom levels
- [ ] No blurriness when zoomed out to full terminal view
- [ ] No blurriness when zoomed in to individual containers
- [ ] Quality toggle in settings still works
- [ ] Shadows work on medium/high/ultra settings
- [ ] Performance is smooth (60fps on modern hardware)

**Step 4: Final commit**

```bash
git add -A && git commit -m "test: verify 3D sharpness after re-engineering

Visual verification:
- Crisp containers at all zoom levels
- Quality settings functional
- Shadows working
- Performance smooth

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

After completing all tasks:

| Metric | Before | After |
|--------|--------|-------|
| **Rendering pipeline** | EffectComposer (render-to-texture) | Direct WebGL render |
| **Pixel ratio** | Capped at 1.5-2x | Full devicePixelRatio |
| **Post-processing files** | 2 composables (~1000 lines) | 0 |
| **Quality preset options** | 30+ settings | 8 essential settings |
| **Expected sharpness** | Blurry at all zooms | Pixel-perfect crisp |

---

## Rollback Plan

If issues arise, revert all changes:

```bash
git revert HEAD~6..HEAD
```

This will undo all 6 commits from this plan.
