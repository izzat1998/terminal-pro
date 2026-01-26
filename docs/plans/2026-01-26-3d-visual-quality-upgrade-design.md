# 3D Visual Quality Upgrade Design

**Date:** 2026-01-26
**Status:** Draft
**Goal:** Transform the yard 3D visualization from functional to architectural-quality rendering

## Overview

Upgrade the existing Three.js yard visualization with professional-grade visual quality including HDR environment lighting, PBR materials, post-processing effects, and enhanced atmosphere.

## Current State

The yard already has:
- ✅ DXF infrastructure (buildings, roads, railways, fences, platforms)
- ✅ Container meshes with color modes (status, dwell, visual)
- ✅ Vehicle models (trucks, cars, wagons)
- ✅ Basic lighting (ambient + directional + hemisphere)
- ✅ Soft shadows with PCF
- ✅ OrbitControls with damping
- ✅ ACES filmic tone mapping

## Target State

After upgrade:
- 🎯 HDR environment map with realistic sky reflections
- 🎯 PBR materials with textures (metal containers, concrete, asphalt)
- 🎯 Post-processing pipeline (SSAO, bloom, vignette, color grading)
- 🎯 Enhanced shadows and ambient occlusion
- 🎯 Atmospheric depth (improved fog, subtle haze)
- 🎯 Performance-optimized with quality presets

---

## Architecture

### New Files

```
frontend/src/
├── composables/
│   ├── useEnvironment3D.ts      # HDR environment, skybox, fog
│   ├── usePostProcessing.ts     # EffectComposer pipeline
│   └── useMaterials3D.ts        # PBR material library
├── assets/
│   └── hdri/
│       └── industrial_sky.hdr   # Environment map
└── utils/
    └── qualityPresets.ts        # Low/Medium/High/Ultra settings
```

### Modified Files

```
frontend/src/
├── components/
│   └── YardView3D.vue           # Integrate new composables
├── composables/
│   ├── useContainers3D.ts       # Add metallic materials
│   ├── useBuildings3D.ts        # Add concrete/glass materials
│   └── useRoads3D.ts            # Add asphalt texture
```

---

## Phase 1: Environment & Atmosphere

### 1.1 HDR Environment Map

Create `useEnvironment3D.ts` composable:

```typescript
export function useEnvironment3D() {
  const envMap = shallowRef<THREE.Texture | null>(null)

  async function loadEnvironment(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    options: {
      hdrPath?: string
      intensity?: number
      rotation?: number
    }
  ): Promise<void>

  function createProceduralSky(): THREE.Mesh  // Fallback if no HDR

  function setTimeOfDay(hour: number): void  // 0-24, affects lighting color

  return { envMap, loadEnvironment, createProceduralSky, setTimeOfDay }
}
```

**Options:**
- Use RGBELoader for `.hdr` files
- PMREMGenerator for environment reflections
- Fallback to procedural gradient sky (no external assets)

### 1.2 Enhanced Fog & Atmosphere

```typescript
// Exponential fog for more realistic depth
scene.fog = new THREE.FogExp2(0xE8F4F8, 0.0015)

// Atmospheric haze layer (optional)
const haze = createAtmosphericHaze()
scene.add(haze)
```

---

## Phase 2: Post-Processing Pipeline

### 2.1 EffectComposer Setup

Create `usePostProcessing.ts`:

```typescript
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { SSAOPass } from 'three/examples/jsm/postprocessing/SSAOPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js'

export function usePostProcessing() {
  const composer = shallowRef<EffectComposer | null>(null)

  function initComposer(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    camera: THREE.Camera,
    options: PostProcessingOptions
  ): EffectComposer

  function setQuality(level: 'low' | 'medium' | 'high' | 'ultra'): void

  function toggleEffect(effect: 'ssao' | 'bloom' | 'vignette', enabled: boolean): void

  return { composer, initComposer, setQuality, toggleEffect }
}
```

### 2.2 Effect Parameters

| Effect | Purpose | Default |
|--------|---------|---------|
| **SSAO** | Ambient occlusion for depth | radius: 16, intensity: 1.0 |
| **Bloom** | Glow on bright surfaces | threshold: 0.9, strength: 0.15 |
| **Vignette** | Focus attention on center | offset: 0.5, darkness: 0.4 |
| **Color Grading** | Cinematic look | contrast: 1.05, saturation: 1.1 |

### 2.3 Custom Color Grading Shader

```glsl
// ColorGradingShader.js
uniform sampler2D tDiffuse;
uniform float contrast;
uniform float saturation;
uniform float brightness;
uniform vec3 tint;

void main() {
  vec4 color = texture2D(tDiffuse, vUv);

  // Contrast
  color.rgb = (color.rgb - 0.5) * contrast + 0.5;

  // Saturation
  float gray = dot(color.rgb, vec3(0.299, 0.587, 0.114));
  color.rgb = mix(vec3(gray), color.rgb, saturation);

  // Tint
  color.rgb *= tint;

  gl_FragColor = color;
}
```

---

## Phase 3: PBR Materials Library

### 3.1 Material System

Create `useMaterials3D.ts`:

```typescript
export interface MaterialPreset {
  name: string
  color: number
  metalness: number
  roughness: number
  normalMap?: THREE.Texture
  roughnessMap?: THREE.Texture
  aoMap?: THREE.Texture
  envMapIntensity: number
}

export const MATERIAL_PRESETS = {
  containerMetal: {
    metalness: 0.9,
    roughness: 0.4,
    envMapIntensity: 1.0,
  },
  containerPainted: {
    metalness: 0.1,
    roughness: 0.6,
    envMapIntensity: 0.5,
  },
  concrete: {
    metalness: 0.0,
    roughness: 0.9,
    envMapIntensity: 0.2,
  },
  asphalt: {
    metalness: 0.0,
    roughness: 0.95,
    envMapIntensity: 0.1,
  },
  glass: {
    metalness: 0.0,
    roughness: 0.05,
    transparent: true,
    opacity: 0.3,
    envMapIntensity: 1.5,
  },
}

export function useMaterials3D() {
  function createMaterial(preset: keyof typeof MATERIAL_PRESETS, color?: number): THREE.MeshStandardMaterial
  function applyEnvMap(material: THREE.MeshStandardMaterial, envMap: THREE.Texture): void
  function createProceduralTexture(type: 'noise' | 'grid' | 'concrete'): THREE.Texture
}
```

### 3.2 Procedural Textures (No External Assets)

Generate textures programmatically for:
- **Container corrugation** - Subtle bump map for metal ridges
- **Asphalt noise** - Rough surface variation
- **Concrete grain** - Subtle surface texture

```typescript
function createNoiseTexture(size: number, intensity: number): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4)
  for (let i = 0; i < size * size; i++) {
    const noise = Math.random() * intensity * 255
    data[i * 4] = noise
    data[i * 4 + 1] = noise
    data[i * 4 + 2] = noise
    data[i * 4 + 3] = 255
  }
  return new THREE.DataTexture(data, size, size)
}
```

---

## Phase 4: Enhanced Container Materials

### 4.1 Container Visual Upgrade

Modify `useContainers3D.ts`:

```typescript
// Before: Simple colored boxes
const material = new THREE.MeshStandardMaterial({
  color: containerColor,
  roughness: 0.6,
  metalness: 0.2,
})

// After: Metallic containers with environment reflections
const material = new THREE.MeshStandardMaterial({
  color: containerColor,
  roughness: 0.35,           // Slightly smooth for reflections
  metalness: 0.85,           // High metalness for steel look
  envMap: environmentMap,    // From useEnvironment3D
  envMapIntensity: 0.8,
  flatShading: false,
})
```

### 4.2 Container Edge Highlights

Add subtle edge bevels for realism:

```typescript
// Use EdgesGeometry for container outlines
const edges = new THREE.EdgesGeometry(boxGeometry, 15)
const edgeMaterial = new THREE.LineBasicMaterial({
  color: 0x000000,
  opacity: 0.2,
  transparent: true
})
const edgeLines = new THREE.LineSegments(edges, edgeMaterial)
```

---

## Phase 5: Quality Presets

### 5.1 Performance Tiers

Create `qualityPresets.ts`:

```typescript
export const QUALITY_PRESETS = {
  low: {
    shadows: false,
    ssao: false,
    bloom: false,
    envMapIntensity: 0,
    pixelRatio: 1,
    antialias: false,
  },
  medium: {
    shadows: true,
    shadowMapSize: 1024,
    ssao: false,
    bloom: true,
    bloomStrength: 0.1,
    envMapIntensity: 0.5,
    pixelRatio: 1,
    antialias: true,
  },
  high: {
    shadows: true,
    shadowMapSize: 2048,
    ssao: true,
    ssaoRadius: 12,
    bloom: true,
    bloomStrength: 0.15,
    envMapIntensity: 0.8,
    pixelRatio: Math.min(window.devicePixelRatio, 2),
    antialias: true,
  },
  ultra: {
    shadows: true,
    shadowMapSize: 4096,
    ssao: true,
    ssaoRadius: 16,
    bloom: true,
    bloomStrength: 0.2,
    envMapIntensity: 1.0,
    pixelRatio: window.devicePixelRatio,
    antialias: true,
  },
}
```

### 5.2 Auto-Detection

```typescript
function detectOptimalQuality(): 'low' | 'medium' | 'high' | 'ultra' {
  const gl = document.createElement('canvas').getContext('webgl2')
  if (!gl) return 'low'

  const debugInfo = gl.getExtension('WEBGL_debug_renderer_info')
  const renderer = debugInfo
    ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
    : ''

  // Check for discrete GPU
  if (/nvidia|radeon|geforce|rtx|gtx/i.test(renderer)) {
    return 'high'
  }

  // Check device memory (if available)
  if ('deviceMemory' in navigator && (navigator as any).deviceMemory >= 8) {
    return 'high'
  }

  return 'medium'
}
```

---

## Phase 6: Integration

### 6.1 YardView3D.vue Updates

```vue
<script setup lang="ts">
// New imports
import { useEnvironment3D } from '@/composables/useEnvironment3D'
import { usePostProcessing } from '@/composables/usePostProcessing'
import { useMaterials3D } from '@/composables/useMaterials3D'
import { detectOptimalQuality, QUALITY_PRESETS } from '@/utils/qualityPresets'

// Initialize
const { envMap, loadEnvironment } = useEnvironment3D()
const { composer, initComposer, setQuality } = usePostProcessing()
const { createMaterial, applyEnvMap } = useMaterials3D()

// In initScene()
const quality = detectOptimalQuality()
await loadEnvironment(renderer, scene, { intensity: 0.8 })
initComposer(renderer, scene, camera, QUALITY_PRESETS[quality])

// In animate()
if (composer.value) {
  composer.value.render()
} else {
  renderer.render(scene, camera)
}
</script>
```

### 6.2 Settings Drawer Enhancement

Add quality controls to `YardSettingsDrawer.vue`:

```vue
<a-form-item label="Качество графики">
  <a-segmented
    v-model:value="displaySettings.quality"
    :options="['low', 'medium', 'high', 'ultra']"
  />
</a-form-item>

<a-form-item label="Эффекты">
  <a-checkbox v-model:checked="displaySettings.ssao">Ambient Occlusion</a-checkbox>
  <a-checkbox v-model:checked="displaySettings.bloom">Bloom</a-checkbox>
</a-form-item>
```

---

## Task Summary

| # | Task | Priority | Dependencies |
|---|------|----------|--------------|
| 1 | Create `useEnvironment3D.ts` | High | None |
| 2 | Create `usePostProcessing.ts` | High | None |
| 3 | Create `useMaterials3D.ts` | High | Task 1 |
| 4 | Create `qualityPresets.ts` | Medium | None |
| 5 | Upgrade container materials | High | Tasks 1, 3 |
| 6 | Upgrade building materials | Medium | Tasks 1, 3 |
| 7 | Upgrade road/ground materials | Medium | Tasks 1, 3 |
| 8 | Integrate into `YardView3D.vue` | High | Tasks 1-4 |
| 9 | Add quality controls to settings | Low | Task 4 |
| 10 | Performance testing & optimization | High | All above |

---

## Success Criteria

- [ ] Scene has visible environment reflections on containers
- [ ] SSAO creates subtle shadows in corners and under containers
- [ ] Bloom adds subtle glow to sky/bright areas
- [ ] Materials look distinctly metallic (containers) vs matte (concrete)
- [ ] Performance stays above 30fps on medium-tier hardware
- [ ] Quality preset toggle works in settings drawer

---

## References

- [Three.js Post-Processing](https://threejs.org/docs/#examples/en/postprocessing/EffectComposer)
- [PMREM Generator](https://threejs.org/docs/#api/en/extras/PMREMGenerator)
- [PBR Materials Guide](https://marmoset.co/posts/basic-theory-of-physically-based-rendering/)
