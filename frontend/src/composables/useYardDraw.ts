/**
 * Yard Draw Mode Composable
 *
 * Provides coordinate drawing/marking functionality for the 3D yard.
 * Used to capture DXF coordinates by clicking on the scene.
 *
 * Activation: Press 'M' when debug mode is active
 * Controls:
 * - Click: Place numbered marker
 * - C: Clear all markers
 * - Enter: Export points to console and clipboard
 * - Z: Undo last point
 */

import { ref, shallowRef, type Ref, type ShallowRef } from 'vue'
import * as THREE from 'three'
import type { DxfCoordinateSystem } from '@/types/dxf'
import { worldToDxf as worldToDxfUtil } from '@/utils/coordinateTransforms'
import { isInputElement } from '@/utils/keyboardUtils'

// ============================================================================
// Types
// ============================================================================

export interface DrawnPoint {
  id: number
  dxf: { x: number; y: number }
  world: THREE.Vector3
}

export interface UseYardDrawOptions {
  scene: ShallowRef<THREE.Scene | undefined>
  camera: ShallowRef<THREE.Camera | undefined>
  container: Ref<HTMLElement | undefined>
  coordinateSystem: ShallowRef<DxfCoordinateSystem | null>
  /** Called when points change (for visual updates) */
  onPointsChange?: (points: DrawnPoint[]) => void
}

export interface UseYardDrawReturn {
  isDrawMode: Ref<boolean>
  points: ShallowRef<DrawnPoint[]>
  toggleDrawMode: () => void
  addPoint: (screenX: number, screenY: number) => DrawnPoint | null
  removeLastPoint: () => void
  clearPoints: () => void
  exportPoints: () => void
  initDrawMode: () => void
  disposeDrawMode: () => void
}

// ============================================================================
// Composable
// ============================================================================

export function useYardDraw(options: UseYardDrawOptions): UseYardDrawReturn {
  const { camera, container, coordinateSystem, onPointsChange } = options

  // State
  const isDrawMode = ref(false)
  const points: ShallowRef<DrawnPoint[]> = shallowRef([])
  let nextPointId = 1

  // Raycaster for ground plane intersection
  const raycaster = new THREE.Raycaster()
  const mouse = new THREE.Vector2()
  const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0) // Y=0 plane

  // ============================================================================
  // Coordinate Conversion
  // ============================================================================

  /**
   * Convert world position to DXF coordinates
   */
  function worldToDxf(worldX: number, worldZ: number): { x: number; y: number } | null {
    const coord = coordinateSystem.value
    if (!coord) return null

    return worldToDxfUtil(worldX, worldZ, { coordinateSystem: coord })
  }

  /**
   * Get world position from screen coordinates using raycasting
   */
  function screenToWorld(screenX: number, screenY: number): THREE.Vector3 | null {
    const cam = camera.value
    const cont = container.value
    if (!cam || !cont) return null

    const rect = cont.getBoundingClientRect()

    // Calculate normalized device coordinates
    mouse.x = ((screenX - rect.left) / rect.width) * 2 - 1
    mouse.y = -((screenY - rect.top) / rect.height) * 2 + 1

    // Update raycaster
    raycaster.setFromCamera(mouse, cam)

    // Find intersection with ground plane
    const intersection = new THREE.Vector3()
    const hasIntersection = raycaster.ray.intersectPlane(groundPlane, intersection)

    return hasIntersection ? intersection : null
  }

  // ============================================================================
  // Point Management
  // ============================================================================

  /**
   * Toggle draw mode on/off
   */
  function toggleDrawMode(): void {
    isDrawMode.value = !isDrawMode.value

    if (import.meta.env.DEV) {
      if (isDrawMode.value) {
        console.log('[YardDraw] Draw mode ENABLED - Click to place markers')
        console.log('[YardDraw] Controls: [C] clear, [Z] undo, [Enter] export')
      } else {
        console.log('[YardDraw] Draw mode DISABLED')
      }
    }
  }

  /**
   * Add a point at screen coordinates
   */
  function addPoint(screenX: number, screenY: number): DrawnPoint | null {
    if (!isDrawMode.value) return null

    const worldPos = screenToWorld(screenX, screenY)
    if (!worldPos) return null

    const dxfCoords = worldToDxf(worldPos.x, worldPos.z)
    if (!dxfCoords) return null

    const point: DrawnPoint = {
      id: nextPointId++,
      dxf: dxfCoords,
      world: worldPos.clone(),
    }

    points.value = [...points.value, point]
    onPointsChange?.(points.value)

    if (import.meta.env.DEV) {
      console.log(`[YardDraw] Point ${point.id}: { x: ${dxfCoords.x}, y: ${dxfCoords.y} }`)
    }

    return point
  }

  /**
   * Remove the last placed point
   */
  function removeLastPoint(): void {
    if (points.value.length === 0) return

    const newPoints = points.value.slice(0, -1)
    points.value = newPoints
    onPointsChange?.(newPoints)

    if (import.meta.env.DEV) {
      console.log(`[YardDraw] Undo - ${newPoints.length} points remaining`)
    }
  }

  /**
   * Clear all points
   */
  function clearPoints(): void {
    points.value = []
    nextPointId = 1
    onPointsChange?.([])

    if (import.meta.env.DEV) {
      console.log('[YardDraw] Cleared all points')
    }
  }

  /**
   * Export points to console and clipboard
   */
  function exportPoints(): void {
    const currentPoints = points.value
    if (currentPoints.length === 0) {
      console.log('[YardDraw] No points to export')
      return
    }

    // Format as simple array
    const exportData = currentPoints.map((p) => ({
      x: p.dxf.x,
      y: p.dxf.y,
    }))

    const jsonString = JSON.stringify(exportData, null, 2)

    // Log to console
    console.log(`[YardDraw] ${currentPoints.length} points captured:`)
    console.log(jsonString)

    // Copy to clipboard
    navigator.clipboard
      .writeText(jsonString)
      .then(() => {
        console.log('[YardDraw] Copied to clipboard ✓')
      })
      .catch((err) => {
        console.warn('[YardDraw] Failed to copy to clipboard:', err)
      })
  }

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle click events - uses window listener to catch clicks on canvas
   */
  function handleClick(event: MouseEvent): void {
    if (!isDrawMode.value) return

    const cont = container.value
    if (!cont) return

    // Check if click is within container bounds
    const rect = cont.getBoundingClientRect()
    if (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    ) {
      return
    }

    // Ignore if clicking on UI elements (overlays, buttons, etc.)
    const target = event.target as HTMLElement
    if (
      target.closest('.yard-draw-indicator') ||
      target.closest('.draw-mode-indicator') ||
      target.closest('.debug-indicator') ||
      target.closest('.vehicle-stats-overlay') ||
      target.closest('.gate-camera-widget') ||
      target.closest('.layer-panel') ||
      target.closest('button') ||
      target.closest('input') ||
      target.closest('.ant-')
    ) {
      return
    }

    addPoint(event.clientX, event.clientY)
  }

  /**
   * Handle keyboard events
   */
  function handleKeyDown(event: KeyboardEvent): void {
    // Ignore if typing in an input
    if (isInputElement(event)) return

    const key = event.key.toLowerCase()

    // M: Toggle draw mode
    if (key === 'm') {
      toggleDrawMode()
      return
    }

    // Only handle these if draw mode is active
    if (!isDrawMode.value) return

    // C: Clear points
    if (key === 'c') {
      clearPoints()
      return
    }

    // Z: Undo last point
    if (key === 'z') {
      removeLastPoint()
      return
    }

    // Enter: Export points
    if (key === 'enter') {
      exportPoints()
      return
    }
  }

  // ============================================================================
  // Console API
  // ============================================================================

  interface YardDrawApi {
    getPoints: () => Array<{ x: number; y: number }>
    clear: () => void
    export: () => void
    undo: () => void
    toggle: () => void
  }

  function exposeConsoleApi(): void {
    const api: YardDrawApi = {
      getPoints: () => points.value.map((p) => ({ x: p.dxf.x, y: p.dxf.y })),
      clear: clearPoints,
      export: exportPoints,
      undo: removeLastPoint,
      toggle: toggleDrawMode,
    }

    ;(window as Window & { yardDraw?: YardDrawApi }).yardDraw = api

    if (import.meta.env.DEV) {
      console.log('[YardDraw] Console API: window.yardDraw.getPoints(), clear(), export(), undo()')
    }
  }

  function removeConsoleApi(): void {
    delete (window as Window & { yardDraw?: YardDrawApi }).yardDraw
  }

  // ============================================================================
  // Lifecycle
  // ============================================================================

  /**
   * Initialize draw mode - call in onMounted
   * Uses window-level listeners since container may not be ready yet
   */
  function initDrawMode(): void {
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('click', handleClick)
    exposeConsoleApi()
  }

  /**
   * Dispose draw mode - call in onUnmounted
   */
  function disposeDrawMode(): void {
    window.removeEventListener('keydown', handleKeyDown)
    window.removeEventListener('click', handleClick)
    removeConsoleApi()
    clearPoints()
    isDrawMode.value = false
  }

  return {
    isDrawMode,
    points,
    toggleDrawMode,
    addPoint,
    removeLastPoint,
    clearPoints,
    exportPoints,
    initDrawMode,
    disposeDrawMode,
  }
}
