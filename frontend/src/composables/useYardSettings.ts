/**
 * useYardSettings - Centralized settings state for 3D yard visualization
 *
 * Manages all visibility toggles, display options, and label settings
 * in a single composable for consistent state across components.
 */

import { reactive, toRefs } from 'vue'

// ============================================================================
// Types
// ============================================================================

export interface YardLayerSettings {
  containers: boolean
  buildings: boolean
  roads: boolean
  fences: boolean
  railway: boolean
  platforms: boolean
  testVehicles: boolean
}

export interface YardLabelSettings {
  buildings: boolean
  containers: boolean
  vehicles: boolean
}

export type ColorMode = 'visual' | 'status' | 'dwell' | 'hazmat'

export interface YardDisplaySettings {
  colorMode: ColorMode
  showGrid: boolean
  showStats: boolean
}

export interface YardSettings {
  layers: YardLayerSettings
  labels: YardLabelSettings
  display: YardDisplaySettings
}

// ============================================================================
// Default Values
// ============================================================================

const DEFAULT_LAYER_SETTINGS: YardLayerSettings = {
  containers: true,
  buildings: true,
  roads: true,
  fences: true,
  railway: false,
  platforms: false,
  testVehicles: false,
}

const DEFAULT_LABEL_SETTINGS: YardLabelSettings = {
  buildings: false,
  containers: false,
  vehicles: false,
}

const DEFAULT_DISPLAY_SETTINGS: YardDisplaySettings = {
  colorMode: 'visual',
  showGrid: false,
  showStats: true,
}

// ============================================================================
// Singleton State (shared across all component instances)
// ============================================================================

const state = reactive<YardSettings>({
  layers: { ...DEFAULT_LAYER_SETTINGS },
  labels: { ...DEFAULT_LABEL_SETTINGS },
  display: { ...DEFAULT_DISPLAY_SETTINGS },
})

// ============================================================================
// Composable
// ============================================================================

export function useYardSettings() {
  // Layer toggles
  function toggleLayer(layer: keyof YardLayerSettings): void {
    state.layers[layer] = !state.layers[layer]
  }

  function setLayerVisibility(layer: keyof YardLayerSettings, visible: boolean): void {
    state.layers[layer] = visible
  }

  function showAllLayers(): void {
    Object.keys(state.layers).forEach((key) => {
      state.layers[key as keyof YardLayerSettings] = true
    })
  }

  function hideAllLayers(): void {
    Object.keys(state.layers).forEach((key) => {
      state.layers[key as keyof YardLayerSettings] = false
    })
  }

  // Label toggles
  function toggleLabel(label: keyof YardLabelSettings): void {
    state.labels[label] = !state.labels[label]
  }

  function setLabelVisibility(label: keyof YardLabelSettings, visible: boolean): void {
    state.labels[label] = visible
  }

  // Display settings
  function setColorMode(mode: ColorMode): void {
    state.display.colorMode = mode
  }

  function toggleGrid(): void {
    state.display.showGrid = !state.display.showGrid
  }

  function toggleStats(): void {
    state.display.showStats = !state.display.showStats
  }

  // Reset to defaults
  function resetToDefaults(): void {
    state.layers = { ...DEFAULT_LAYER_SETTINGS }
    state.labels = { ...DEFAULT_LABEL_SETTINGS }
    state.display = { ...DEFAULT_DISPLAY_SETTINGS }
  }

  return {
    // State (reactive refs)
    ...toRefs(state),

    // Direct state access (for watchers)
    settings: state,

    // Layer functions
    toggleLayer,
    setLayerVisibility,
    showAllLayers,
    hideAllLayers,

    // Label functions
    toggleLabel,
    setLabelVisibility,

    // Display functions
    setColorMode,
    toggleGrid,
    toggleStats,

    // Reset
    resetToDefaults,
  }
}
