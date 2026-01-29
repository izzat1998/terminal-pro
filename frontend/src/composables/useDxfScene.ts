/**
 * DXF to Three.js Scene Composable
 * Renders DXF files in a Three.js scene with full interactivity
 */

import { ref, shallowRef, onUnmounted, type Ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { dxfToThree, loadDxfFromFile, loadDxfFromUrl } from '@/utils/dxfToThree'
import type { DxfConversionOptions, DxfStats } from '@/types/dxf'

export interface DxfSceneOptions extends DxfConversionOptions {
  /** Background color (default: 0xfafafa) */
  backgroundColor?: number
  /** Grid helper visible (default: true) */
  showGrid?: boolean
  /** Grid size (default: auto-calculated from DXF bounds) */
  gridSize?: number
  /** Grid divisions (default: 50) */
  gridDivisions?: number
}

export function useDxfScene(canvasRef: Ref<HTMLCanvasElement | undefined>) {
  // Three.js core objects
  const scene = shallowRef<THREE.Scene>()
  const camera = shallowRef<THREE.OrthographicCamera>()
  const renderer = shallowRef<THREE.WebGLRenderer>()
  const controls = shallowRef<OrbitControls>()

  // DXF content
  const dxfGroup = shallowRef<THREE.Group>()
  const dxfStats = ref<DxfStats | null>(null)

  // State
  const isInitialized = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  let animationId: number | null = null

  /**
   * Initialize the Three.js scene
   */
  function initScene(options: DxfSceneOptions = {}): void {
    if (!canvasRef.value || isInitialized.value) return

    const backgroundColor = options.backgroundColor ?? 0xfafafa

    // Create scene
    scene.value = new THREE.Scene()
    scene.value.background = new THREE.Color(backgroundColor)

    // Create orthographic camera (good for 2D drawings)
    const aspect = canvasRef.value.clientWidth / canvasRef.value.clientHeight
    const frustumSize = 1000 // Start with larger default for typical CAD drawings
    camera.value = new THREE.OrthographicCamera(
      -frustumSize * aspect / 2,
      frustumSize * aspect / 2,
      frustumSize / 2,
      -frustumSize / 2,
      0.1,
      100000 // Large far plane for big CAD drawings
    )
    camera.value.position.set(0, 1000, 0)
    camera.value.lookAt(0, 0, 0)

    // Create renderer
    renderer.value = new THREE.WebGLRenderer({
      canvas: canvasRef.value,
      antialias: true,
    })
    renderer.value.setSize(canvasRef.value.clientWidth, canvasRef.value.clientHeight)
    renderer.value.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    // Create controls
    controls.value = new OrbitControls(camera.value, renderer.value.domElement)
    controls.value.enableDamping = true
    controls.value.dampingFactor = 0.1
    controls.value.enableRotate = true
    controls.value.enablePan = true
    controls.value.panSpeed = 1.5
    controls.value.screenSpacePanning = true
    controls.value.minZoom = 0.01 // Allow zooming out far for large drawings
    controls.value.maxZoom = 100  // Allow zooming in close for details

    // Add ambient light
    const ambientLight = new THREE.AmbientLight(0xffffff, 1)
    scene.value.add(ambientLight)

    // Add grid if requested (will be resized when DXF loads)
    if (options.showGrid !== false) {
      const gridSize = options.gridSize ?? 1000 // Larger default
      const gridDivisions = options.gridDivisions ?? 50
      const gridHelper = new THREE.GridHelper(gridSize, gridDivisions, 0xcccccc, 0xeeeeee)
      gridHelper.rotation.x = 0 // Keep horizontal
      scene.value.add(gridHelper)
    }

    isInitialized.value = true
    animate()
  }

  /**
   * Animation loop
   */
  function animate(): void {
    if (!renderer.value || !scene.value || !camera.value || !controls.value) return

    animationId = requestAnimationFrame(animate)
    controls.value.update()
    renderer.value.render(scene.value, camera.value)
  }

  /**
   * Load DXF from string content
   */
  function loadDxfContent(content: string, options: DxfConversionOptions = {}): void {
    if (!scene.value) {
      error.value = 'Scene not initialized'
      return
    }

    isLoading.value = true
    error.value = null

    try {
      // Remove previous DXF group
      if (dxfGroup.value) {
        scene.value.remove(dxfGroup.value)
        dxfGroup.value.traverse((obj) => {
          if (obj instanceof THREE.Mesh || obj instanceof THREE.Line) {
            obj.geometry?.dispose()
            if (obj.material instanceof THREE.Material) {
              obj.material.dispose()
            }
          }
        })
      }

      // Convert and add new DXF
      const result = dxfToThree(content, options)
      dxfGroup.value = result.group
      dxfStats.value = result.stats
      scene.value.add(result.group)

      // Fit camera to content
      fitCameraToContent()

      isLoading.value = false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to parse DXF'
      isLoading.value = false
    }
  }

  /**
   * Load DXF from file
   */
  async function loadDxfFile(file: File, options: DxfConversionOptions = {}): Promise<void> {
    if (!scene.value) {
      error.value = 'Scene not initialized'
      return
    }

    isLoading.value = true
    error.value = null

    try {
      const result = await loadDxfFromFile(file, options)

      // Remove previous DXF group
      if (dxfGroup.value) {
        scene.value.remove(dxfGroup.value)
      }

      dxfGroup.value = result.group
      dxfStats.value = result.stats
      scene.value.add(result.group)

      // Fit camera to content
      fitCameraToContent()

      isLoading.value = false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load DXF file'
      isLoading.value = false
    }
  }

  /**
   * Load DXF from URL
   */
  async function loadDxfUrl(url: string, options: DxfConversionOptions = {}): Promise<void> {
    if (!scene.value) {
      error.value = 'Scene not initialized'
      return
    }

    isLoading.value = true
    error.value = null

    try {
      const result = await loadDxfFromUrl(url, options)

      // Remove previous DXF group
      if (dxfGroup.value) {
        scene.value.remove(dxfGroup.value)
      }

      dxfGroup.value = result.group
      dxfStats.value = result.stats
      scene.value.add(result.group)

      // Fit camera to content
      fitCameraToContent()

      isLoading.value = false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load DXF from URL'
      isLoading.value = false
    }
  }

  /**
   * Fit camera to show all DXF content
   */
  function fitCameraToContent(): void {
    if (!camera.value || !controls.value || !dxfGroup.value || !canvasRef.value) return

    // Calculate bounding box
    const box = new THREE.Box3().setFromObject(dxfGroup.value)

    // Check if bounding box is valid
    if (box.isEmpty()) {
      return
    }

    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())

    // Calculate required zoom to fit content
    const aspect = canvasRef.value.clientWidth / canvasRef.value.clientHeight
    const maxDim = Math.max(size.x, size.z, 1) * 1.2 // Add 20% padding, min 1 to avoid zero

    // Update camera frustum based on content size
    const frustumSize = maxDim
    camera.value.left = -frustumSize * aspect / 2
    camera.value.right = frustumSize * aspect / 2
    camera.value.top = frustumSize / 2
    camera.value.bottom = -frustumSize / 2
    camera.value.zoom = 1

    // Position camera above the center, at a height proportional to scene size
    const cameraHeight = Math.max(maxDim, 100)
    camera.value.position.set(center.x, cameraHeight, center.z)
    camera.value.lookAt(center.x, 0, center.z)

    // Update far plane to accommodate large scenes
    camera.value.far = Math.max(cameraHeight * 10, 10000)
    camera.value.updateProjectionMatrix()

    // Update controls target
    controls.value.target.set(center.x, 0, center.z)
    controls.value.update()

    // Update grid to match scene size
    updateGridSize(maxDim)
  }

  /**
   * Update grid helper to match scene size
   */
  function updateGridSize(sceneSize: number): void {
    if (!scene.value) return

    // Remove existing grid
    const existingGrid = scene.value.children.find(child => child instanceof THREE.GridHelper)
    if (existingGrid) {
      scene.value.remove(existingGrid)
    }

    // Create new grid sized to scene
    const gridSize = Math.ceil(sceneSize / 100) * 100 // Round up to nearest 100
    const divisions = Math.min(Math.max(Math.floor(gridSize / 10), 10), 100) // 10-100 divisions
    const gridHelper = new THREE.GridHelper(gridSize, divisions, 0xcccccc, 0xeeeeee)
    scene.value.add(gridHelper)
  }

  /**
   * Handle window resize
   */
  function handleResize(): void {
    if (!canvasRef.value || !camera.value || !renderer.value) return

    const width = canvasRef.value.clientWidth
    const height = canvasRef.value.clientHeight
    const aspect = width / height

    // Maintain current zoom level
    const frustumSize = (camera.value.right - camera.value.left) / camera.value.zoom
    camera.value.left = -frustumSize * aspect / 2
    camera.value.right = frustumSize * aspect / 2
    camera.value.updateProjectionMatrix()

    renderer.value.setSize(width, height)
  }

  /**
   * Set view to top-down (plan view)
   */
  function setTopView(): void {
    if (!camera.value || !controls.value) return

    const target = controls.value.target.clone()
    camera.value.position.set(target.x, 100, target.z)
    camera.value.lookAt(target)
    camera.value.updateProjectionMatrix()
    controls.value.update()
  }

  /**
   * Set view to isometric
   */
  function setIsometricView(): void {
    if (!camera.value || !controls.value) return

    const target = controls.value.target.clone()
    camera.value.position.set(target.x + 50, 60, target.z + 50)
    camera.value.lookAt(target)
    camera.value.updateProjectionMatrix()
    controls.value.update()
  }

  /**
   * Zoom to fit all content
   */
  function zoomToFit(): void {
    fitCameraToContent()
  }

  /**
   * Get all unique layers in the DXF
   */
  function getLayers(): string[] {
    if (!dxfGroup.value) return []

    const layers = new Set<string>()
    dxfGroup.value.traverse((obj) => {
      if (obj.name) {
        const parts = obj.name.split('_')
        if (parts.length >= 2) {
          layers.add(parts.slice(1).join('_'))
        }
      }
    })
    return Array.from(layers)
  }

  /**
   * Set layer visibility
   */
  function setLayerVisibility(layer: string, visible: boolean): void {
    if (!dxfGroup.value) return

    dxfGroup.value.traverse((obj) => {
      if (obj.name && obj.name.includes(`_${layer}`)) {
        obj.visible = visible
      }
    })
  }

  /**
   * Dispose of all resources
   */
  function dispose(): void {
    if (animationId) {
      cancelAnimationFrame(animationId)
      animationId = null
    }

    if (dxfGroup.value) {
      dxfGroup.value.traverse((obj) => {
        if (obj instanceof THREE.Mesh || obj instanceof THREE.Line) {
          obj.geometry?.dispose()
          if (obj.material instanceof THREE.Material) {
            obj.material.dispose()
          }
        }
      })
    }

    controls.value?.dispose()
    renderer.value?.dispose()
    scene.value?.clear()

    isInitialized.value = false
    dxfStats.value = null
    error.value = null
  }

  // Watch for canvas changes
  watch(canvasRef, (newCanvas) => {
    if (newCanvas && !isInitialized.value) {
      initScene()
    }
  })

  // Cleanup on unmount
  onUnmounted(() => {
    dispose()
  })

  return {
    // State
    scene,
    camera,
    renderer,
    controls,
    dxfGroup,
    dxfStats,
    isInitialized,
    isLoading,
    error,

    // Methods
    initScene,
    loadDxfContent,
    loadDxfFile,
    loadDxfUrl,
    handleResize,
    fitCameraToContent,
    setTopView,
    setIsometricView,
    zoomToFit,
    getLayers,
    setLayerVisibility,
    dispose,
  }
}
