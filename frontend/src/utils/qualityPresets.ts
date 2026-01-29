/**
 * Quality Presets for 3D Yard Visualization
 *
 * Provides performance tiers (Low/Medium/High/Ultra) with auto-detection
 * based on hardware capabilities.
 */

export type QualityLevel = 'low' | 'medium' | 'high' | 'ultra'

export interface QualityPreset {
  // Shadows
  shadows: boolean
  shadowMapSize: number

  // Post-processing
  ssao: boolean
  ssaoRadius: number
  ssaoIntensity: number
  bloom: boolean
  bloomThreshold: number
  bloomStrength: number
  bloomRadius: number
  vignette: boolean
  vignetteOffset: number
  vignetteDarkness: number
  colorGrading: boolean

  // Environment
  envMapIntensity: number
  fog: boolean
  fogDensity: number

  // Rendering
  pixelRatio: number
  antialias: boolean
  toneMapping: boolean
  toneMappingExposure: number

  // Container edges (subtle outlines for visual distinction)
  containerEdges: boolean
  containerEdgeOpacity: number
}

export const QUALITY_PRESETS: Record<QualityLevel, QualityPreset> = {
  low: {
    shadows: false,
    shadowMapSize: 512,
    ssao: false,
    ssaoRadius: 8,
    ssaoIntensity: 0.5,
    bloom: false,
    bloomThreshold: 0.9,
    bloomStrength: 0.1,
    bloomRadius: 0.5,
    vignette: false,
    vignetteOffset: 0.5,
    vignetteDarkness: 0.3,
    colorGrading: false,
    envMapIntensity: 0,
    fog: false,
    fogDensity: 0,
    pixelRatio: Math.min(window.devicePixelRatio, 1.5),  // At least 1.5x for sharpness
    antialias: false,
    toneMapping: true,
    toneMappingExposure: 1.0,
    containerEdges: false,
    containerEdgeOpacity: 0,
  },

  medium: {
    shadows: true,
    shadowMapSize: 1024,
    ssao: false,
    ssaoRadius: 12,
    ssaoIntensity: 0.8,
    bloom: false,
    bloomThreshold: 0.9,
    bloomStrength: 0,
    bloomRadius: 0,
    vignette: false,
    vignetteOffset: 0.5,
    vignetteDarkness: 0.3,
    colorGrading: false,
    envMapIntensity: 0.5,
    fog: false,
    fogDensity: 0,
    pixelRatio: Math.min(window.devicePixelRatio, 2),  // Full Retina support
    antialias: true,
    toneMapping: true,
    toneMappingExposure: 1.0,
    containerEdges: false,
    containerEdgeOpacity: 0,
  },

  high: {
    shadows: true,
    shadowMapSize: 2048,
    ssao: false,
    ssaoRadius: 16,
    ssaoIntensity: 1.0,
    bloom: false,
    bloomThreshold: 0.85,
    bloomStrength: 0,
    bloomRadius: 0,
    vignette: false,
    vignetteOffset: 0.5,
    vignetteDarkness: 0.4,
    colorGrading: true,
    envMapIntensity: 0.8,
    fog: false,
    fogDensity: 0,
    pixelRatio: Math.min(window.devicePixelRatio, 2),
    antialias: true,
    toneMapping: true,
    toneMappingExposure: 1.1,
    containerEdges: true,
    containerEdgeOpacity: 0.15,
  },

  ultra: {
    shadows: true,
    shadowMapSize: 4096,
    ssao: false,
    ssaoRadius: 20,
    ssaoIntensity: 1.2,
    bloom: false,
    bloomThreshold: 0.8,
    bloomStrength: 0,
    bloomRadius: 0,
    vignette: false,
    vignetteOffset: 0.5,
    vignetteDarkness: 0.5,
    colorGrading: true,
    envMapIntensity: 1.0,
    fog: false,
    fogDensity: 0,
    pixelRatio: window.devicePixelRatio,
    antialias: true,
    toneMapping: true,
    toneMappingExposure: 1.2,
    containerEdges: true,
    containerEdgeOpacity: 0.15,
  },
}

/**
 * Auto-detect optimal quality level based on hardware capabilities.
 * Checks for discrete GPU, device memory, and WebGL2 support.
 */
export function detectOptimalQuality(): QualityLevel {
  // Check WebGL2 support
  const canvas = document.createElement('canvas')
  const gl = canvas.getContext('webgl2')

  if (!gl) {
    return 'low'
  }

  // Try to get GPU renderer info
  const debugInfo = gl.getExtension('WEBGL_debug_renderer_info')
  const renderer = debugInfo
    ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
    : ''

  // Check for discrete GPU (NVIDIA, AMD, Intel Arc)
  const hasDiscreteGPU = /nvidia|radeon|geforce|rtx|gtx|arc\s*a\d/i.test(renderer)

  // Check for Apple Silicon (M1/M2/M3 - excellent GPU)
  const hasAppleSilicon = /apple\s*(m1|m2|m3|gpu)/i.test(renderer)

  // Check device memory if available (Navigator API)
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

  // Map score to quality level
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
  low: 'Базовое качество для слабых устройств',
  medium: 'Сбалансированное качество и производительность',
  high: 'Высокое качество с эффектами освещения',
  ultra: 'Максимальное качество для мощных устройств',
}
