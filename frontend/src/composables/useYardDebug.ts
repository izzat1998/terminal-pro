import { ref, type Ref } from 'vue'
import { isInputElement } from '@/utils/keyboardUtils'

/**
 * Yard Debug Mode Composable
 *
 * Provides debug mode toggle for the 3D yard visualization.
 * Debug mode enables grid overlay, element labels, and inspector panel.
 *
 * Activation methods:
 * - Keyboard: Press 'D' to toggle (when no input is focused)
 * - URL parameter: ?debug=true
 * - Console: window.toggleYardDebug()
 */

export interface DebugSettings {
  showGrid: boolean
  showLabels: boolean
  showCoordinates: boolean
}

interface UseYardDebugReturn {
  isDebugMode: Ref<boolean>
  debugSettings: Ref<DebugSettings>
  toggleDebug: () => void
  initDebugMode: () => void
  disposeDebugMode: () => void
}

// Default debug settings
const defaultDebugSettings: DebugSettings = {
  showGrid: true,
  showLabels: true,
  showCoordinates: true,
}

export function useYardDebug(): UseYardDebugReturn {
  const isDebugMode = ref(false)
  const debugSettings = ref<DebugSettings>({ ...defaultDebugSettings })

  /**
   * Toggle debug mode on/off
   */
  function toggleDebug(): void {
    isDebugMode.value = !isDebugMode.value
    logDebugState()
  }

  /**
   * Force enable debug mode (internal use)
   */
  function enableDebug(): void {
    isDebugMode.value = true
    logDebugState()
  }

  /**
   * Log current debug state to console (dev only)
   */
  function logDebugState(): void {
    if (import.meta.env.DEV) {
      if (isDebugMode.value) {
        console.log('[YardDebug] Debug mode ENABLED - Press D to toggle')
      } else {
        console.log('[YardDebug] Debug mode DISABLED')
      }
    }
  }

  /**
   * Handle keyboard events for debug toggle
   */
  function handleKeyDown(event: KeyboardEvent): void {
    // Ignore if typing in an input or textarea
    if (isInputElement(event)) return

    // Toggle debug mode on 'D' key (case-insensitive)
    if (event.key.toLowerCase() === 'd') {
      toggleDebug()
    }
  }

  /**
   * Check URL parameter for debug mode on initialization
   */
  function checkUrlParameter(): void {
    const urlParams = new URLSearchParams(window.location.search)
    const debugParam = urlParams.get('debug')

    if (debugParam === 'true' || debugParam === '1') {
      enableDebug()
      if (import.meta.env.DEV) {
        console.log('[YardDebug] Enabled via URL parameter')
      }
    }
  }

  /**
   * Expose debug functions to window for console access
   */
  function exposeConsoleApi(): void {
    // Expose toggle function
    ;(window as Window & { toggleYardDebug?: () => void }).toggleYardDebug = () => {
      toggleDebug()
      return isDebugMode.value
    }

    // Expose getter for current state
    Object.defineProperty(window, 'yardDebugMode', {
      get: () => isDebugMode.value,
      configurable: true,
    })

    if (import.meta.env.DEV) {
      console.log('[YardDebug] Console API available: window.toggleYardDebug(), window.yardDebugMode')
    }
  }

  /**
   * Remove console API from window
   */
  function removeConsoleApi(): void {
    delete (window as Window & { toggleYardDebug?: () => void }).toggleYardDebug
    delete (window as Window & { yardDebugMode?: boolean }).yardDebugMode
  }

  /**
   * Initialize debug mode - call in onMounted
   * Sets up keyboard listener, checks URL param, exposes console API
   */
  function initDebugMode(): void {
    // Add keyboard listener
    window.addEventListener('keydown', handleKeyDown)

    // Check URL parameter
    checkUrlParameter()

    // Expose console API
    exposeConsoleApi()
  }

  /**
   * Dispose debug mode - call in onUnmounted
   * Cleans up keyboard listener and console API
   */
  function disposeDebugMode(): void {
    // Remove keyboard listener
    window.removeEventListener('keydown', handleKeyDown)

    // Remove console API
    removeConsoleApi()
  }

  return {
    isDebugMode,
    debugSettings,
    toggleDebug,
    initDebugMode,
    disposeDebugMode,
  }
}
