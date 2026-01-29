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
