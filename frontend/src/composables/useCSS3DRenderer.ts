/**
 * CSS3DRenderer Composable
 *
 * Manages CSS3DRenderer for displaying HTML elements in 3D space,
 * specifically for screen-anchored widgets like the gate camera widget.
 *
 * Features:
 * - Separate THREE.Scene for CSS3D objects
 * - Screen-anchored positioning (dock positions)
 * - Proper disposal and cleanup
 * - Resize handling
 */

import { shallowRef, type Ref } from 'vue'
import * as THREE from 'three'
import { CSS3DRenderer, CSS3DObject } from 'three/examples/jsm/renderers/CSS3DRenderer.js'

// Widget dimensions for dock positioning calculations
const WIDGET_DIMENSIONS = {
  width: 260,
  height: 200,
  margin: 16,  // Margin from screen edges
}

export interface UseCSS3DRendererOptions {
  /** Container element that holds both WebGL and CSS3D renderers */
  container: Ref<HTMLElement | null | undefined>
}

export type DockPosition = 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right'

export interface WidgetDockConfig {
  /** Dock position on screen */
  position: DockPosition
  /** Optional custom width override */
  width?: number
  /** Optional custom height override */
  height?: number
}

export interface CSS3DWidget {
  /** The CSS3DObject for 3D positioning */
  object: CSS3DObject
  /** The underlying HTML element */
  element: HTMLElement
  /** Update position based on dock config and screen size */
  updatePosition: (screenWidth: number, screenHeight: number) => void
  /** Current dock configuration */
  dockConfig: WidgetDockConfig
}

export interface UseCSS3DRendererReturn {
  /** The CSS3DRenderer instance */
  renderer: Ref<CSS3DRenderer | null>
  /** The separate Scene for CSS3D objects */
  scene: Ref<THREE.Scene | null>
  /** Initialize the renderer */
  init: (camera: THREE.Camera) => void
  /** Add a widget to the CSS3D scene with dock positioning */
  addWidget: (element: HTMLElement, config: WidgetDockConfig) => CSS3DWidget
  /** Remove a widget from the scene */
  removeWidget: (widget: CSS3DWidget) => void
  /** Update renderer size on container resize */
  updateSize: () => void
  /** Render the CSS3D scene (call in animation loop) */
  render: (camera: THREE.Camera) => void
  /** Dispose all resources */
  dispose: () => void
}

/**
 * Calculate screen position for a dock position
 */
function calculateDockPosition(
  dockPosition: DockPosition,
  screenWidth: number,
  screenHeight: number,
  widgetWidth: number,
  widgetHeight: number
): { x: number; y: number } {
  const margin = WIDGET_DIMENSIONS.margin

  // Calculate center position based on dock corner
  // CSS3D uses screen coordinates with (0,0) at center
  switch (dockPosition) {
    case 'bottom-left':
      return {
        x: -screenWidth / 2 + widgetWidth / 2 + margin,
        y: -screenHeight / 2 + widgetHeight / 2 + margin,
      }

    case 'bottom-right':
      return {
        x: screenWidth / 2 - widgetWidth / 2 - margin,
        y: -screenHeight / 2 + widgetHeight / 2 + margin,
      }

    case 'top-left':
      return {
        x: -screenWidth / 2 + widgetWidth / 2 + margin,
        y: screenHeight / 2 - widgetHeight / 2 - margin,
      }

    case 'top-right':
      return {
        x: screenWidth / 2 - widgetWidth / 2 - margin,
        y: screenHeight / 2 - widgetHeight / 2 - margin,
      }
  }
}

export function useCSS3DRenderer(options: UseCSS3DRendererOptions): UseCSS3DRendererReturn {
  const { container } = options

  // Renderer and scene refs
  const renderer = shallowRef<CSS3DRenderer | null>(null)
  const scene = shallowRef<THREE.Scene | null>(null)

  // Track all added widgets for cleanup and resize updates
  const widgets: CSS3DWidget[] = []

  /**
   * Initialize the CSS3DRenderer
   */
  function init(camera: THREE.Camera): void {
    if (!container.value) {
      console.warn('useCSS3DRenderer: Container element not available')
      return
    }

    // Create separate scene for CSS3D objects
    scene.value = new THREE.Scene()

    // Create CSS3DRenderer
    renderer.value = new CSS3DRenderer()

    // Set size to match container
    const width = container.value.clientWidth
    const height = container.value.clientHeight
    renderer.value.setSize(width, height)

    // Style the DOM element for overlay
    const domElement = renderer.value.domElement
    domElement.style.position = 'absolute'
    domElement.style.top = '0'
    domElement.style.left = '0'
    domElement.style.pointerEvents = 'none'  // Allow WebGL clicks to pass through

    // Append to container
    container.value.appendChild(domElement)

    // Initial render
    renderer.value.render(scene.value, camera)
  }

  /**
   * Add a widget with screen-anchored dock positioning
   */
  function addWidget(element: HTMLElement, config: WidgetDockConfig): CSS3DWidget {
    if (!scene.value || !container.value) {
      throw new Error('useCSS3DRenderer: Must call init() before addWidget()')
    }

    const widgetWidth = config.width ?? WIDGET_DIMENSIONS.width
    const widgetHeight = config.height ?? WIDGET_DIMENSIONS.height

    // Enable pointer events on the widget itself
    element.style.pointerEvents = 'auto'

    // Create CSS3DObject from the HTML element
    const css3dObject = new CSS3DObject(element)
    css3dObject.name = `widget-${config.position}`

    // Create update function for this widget
    const updatePosition = (screenWidth: number, screenHeight: number): void => {
      const pos = calculateDockPosition(
        config.position,
        screenWidth,
        screenHeight,
        widgetWidth,
        widgetHeight
      )

      // Position in CSS3D space
      // Z=0 keeps it at the "screen plane"
      css3dObject.position.set(pos.x, pos.y, 0)
    }

    // Initial position calculation
    updatePosition(container.value.clientWidth, container.value.clientHeight)

    // Add to scene
    scene.value.add(css3dObject)

    // Create widget object
    const widget: CSS3DWidget = {
      object: css3dObject,
      element,
      updatePosition,
      dockConfig: config,
    }

    // Track for resize updates
    widgets.push(widget)

    return widget
  }

  /**
   * Remove a widget from the scene
   */
  function removeWidget(widget: CSS3DWidget): void {
    if (!scene.value) return

    // Remove from scene
    scene.value.remove(widget.object)

    // Remove from tracking array
    const index = widgets.indexOf(widget)
    if (index !== -1) {
      widgets.splice(index, 1)
    }
  }

  /**
   * Update renderer size on container resize
   */
  function updateSize(): void {
    if (!renderer.value || !container.value) return

    const width = container.value.clientWidth
    const height = container.value.clientHeight

    // Update renderer size
    renderer.value.setSize(width, height)

    // Update all widget positions
    for (const widget of widgets) {
      widget.updatePosition(width, height)
    }
  }

  /**
   * Render the CSS3D scene
   * Call this in your animation loop after rendering the WebGL scene
   */
  function render(camera: THREE.Camera): void {
    if (!renderer.value || !scene.value) return

    renderer.value.render(scene.value, camera)
  }

  /**
   * Dispose all resources
   */
  function dispose(): void {
    // Remove all widgets
    for (const widget of widgets) {
      if (scene.value) {
        scene.value.remove(widget.object)
      }
    }
    widgets.length = 0

    // Remove renderer DOM element
    if (renderer.value && container.value) {
      const domElement = renderer.value.domElement
      if (domElement.parentElement) {
        domElement.parentElement.removeChild(domElement)
      }
    }

    // Clear scene
    if (scene.value) {
      scene.value.clear()
      scene.value = null
    }

    renderer.value = null
  }

  return {
    renderer,
    scene,
    init,
    addWidget,
    removeWidget,
    updateSize,
    render,
    dispose,
  }
}
