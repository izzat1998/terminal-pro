/**
 * Container Labels 3D Composable
 *
 * Creates sprite-based container number labels visible from top-down views.
 * Labels are rendered to canvas textures for crisp text at any zoom level.
 *
 * Performance considerations:
 * - Maximum 200 visible labels at once
 * - Labels only show when camera height > 50m (top-down view)
 * - Labels fade based on distance from camera center
 */

import { ref, shallowRef, type Ref } from 'vue'
import * as THREE from 'three'
import type { ContainerPosition, ContainerData, Container3D } from './useContainers3D'
import { CONTAINER_DIMENSIONS } from './useContainers3D'
import type { DxfCoordinateSystem } from '@/types/dxf'
import { dxfToWorld as dxfToWorldUtil } from '@/utils/coordinateTransforms'
import { disposeObject3D } from '@/utils/threeUtils'

// Configuration
const MAX_VISIBLE_LABELS = 200
const MIN_CAMERA_HEIGHT = 50  // Meters - labels only visible above this height
const LABEL_SCALE = 8  // Base scale factor for sprites

// Reusable vector to avoid per-frame allocation
const _labelCameraTarget = new THREE.Vector3()

export interface UseContainerLabels3DOptions {
  /** Scale factor for coordinates (from DXF) */
  scale?: number
  /** Center point for coordinate transformation */
  center?: { x: number; y: number }
  /** DXF coordinate system for alignment */
  coordinateSystem?: DxfCoordinateSystem
  /** Font size for label text */
  fontSize?: number
  /** Show labels initially */
  visible?: boolean
}

const DEFAULT_OPTIONS = {
  scale: 1.0,
  center: { x: 0, y: 0 },
  fontSize: 32,
  visible: true,
}

type LabelOptions = typeof DEFAULT_OPTIONS & { coordinateSystem?: DxfCoordinateSystem }

/**
 * Create a canvas texture with container number text
 */
function createLabelTexture(
  text: string,
  fontSize: number = 32
): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')!

  // Measure text to size canvas appropriately
  ctx.font = `bold ${fontSize}px Arial, sans-serif`
  const metrics = ctx.measureText(text)
  const textWidth = metrics.width

  // Set canvas size with padding
  const padding = fontSize * 0.5
  canvas.width = Math.ceil(textWidth + padding * 2)
  canvas.height = Math.ceil(fontSize * 1.5)

  // White background with rounded corners
  ctx.fillStyle = 'rgba(255, 255, 255, 0.95)'
  const radius = fontSize * 0.2
  ctx.beginPath()
  ctx.roundRect(0, 0, canvas.width, canvas.height, radius)
  ctx.fill()

  // Draw text
  ctx.font = `bold ${fontSize}px Arial, sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#1a1a1a'
  ctx.fillText(text, canvas.width / 2, canvas.height / 2)

  // Create texture
  const texture = new THREE.CanvasTexture(canvas)
  texture.minFilter = THREE.LinearFilter
  texture.magFilter = THREE.LinearFilter

  return texture
}

/**
 * Convert DXF coordinates to Three.js world coordinates
 */
function dxfToWorld(
  dxfX: number,
  dxfY: number,
  opts: LabelOptions
): THREE.Vector3 {
  const result = dxfToWorldUtil(dxfX, dxfY, {
    scale: opts.scale,
    center: opts.center,
    coordinateSystem: opts.coordinateSystem,
  })
  return result ?? new THREE.Vector3(0, 0, 0)
}

export function useContainerLabels3D(
  containersRef: Ref<Container3D[]>,
  positionsRef: Ref<ContainerPosition[]>,
  _dataRef: Ref<ContainerData[]> = ref([])
) {
  // Options
  const options = ref<LabelOptions>({ ...DEFAULT_OPTIONS })

  // Three.js objects
  const labelsGroup = shallowRef<THREE.Group | null>(null)
  const spritePool: THREE.Sprite[] = []
  const textureCache = new Map<string, THREE.CanvasTexture>()

  // State
  const isVisible = ref(true)
  const visibleLabelCount = ref(0)

  /**
   * Initialize container labels
   */
  function createLabels(opts: UseContainerLabels3DOptions = {}): THREE.Group {
    const mergedOpts: LabelOptions = {
      ...DEFAULT_OPTIONS,
      ...opts,
      scale: opts.coordinateSystem?.scale ?? opts.scale ?? DEFAULT_OPTIONS.scale,
      center: opts.coordinateSystem
        ? { x: opts.coordinateSystem.center.x, y: opts.coordinateSystem.center.y }
        : (opts.center ?? DEFAULT_OPTIONS.center),
    }
    options.value = mergedOpts
    isVisible.value = opts.visible ?? true

    // Create group
    const group = new THREE.Group()
    group.name = 'container_labels'
    group.visible = isVisible.value
    labelsGroup.value = group

    const containers = containersRef.value
    const positions = positionsRef.value
    if (containers.length === 0) return group

    // Get container dimensions for positioning
    const dims = CONTAINER_DIMENSIONS['40GP']

    // Create sprites for each container (limited by MAX_VISIBLE_LABELS)
    const labelsToCreate = Math.min(containers.length, MAX_VISIBLE_LABELS * 2) // Create extra for pooling

    for (let i = 0; i < labelsToCreate; i++) {
      const container = containers[i]
      const pos = positions[i]
      if (!container || !pos) continue

      // Get container number from data or generate placeholder
      const containerNumber = container.data?.container_number ?? `C-${container.id}`

      // Get or create texture (cache for reuse)
      let texture = textureCache.get(containerNumber)
      if (!texture) {
        texture = createLabelTexture(containerNumber, mergedOpts.fontSize)
        textureCache.set(containerNumber, texture)
      }

      // Create sprite material
      const material = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        opacity: 1,
        depthTest: true,
        depthWrite: false,
      })

      // Create sprite
      const sprite = new THREE.Sprite(material)
      sprite.name = `label_${container.id}`

      // Calculate position (above container center)
      const useOriginal = mergedOpts.coordinateSystem && pos._original
      const dxfX = useOriginal ? pos._original!.x : pos.x
      const dxfY = useOriginal ? pos._original!.y : pos.y
      const worldPos = dxfToWorld(dxfX, dxfY, mergedOpts)

      // Container center offset (same as in useContainers3D)
      const rotationRad = (pos.rotation * Math.PI) / 180
      const halfLength = dims.length / 2
      const halfWidth = dims.width / 2
      const cos = Math.cos(rotationRad)
      const sin = Math.sin(rotationRad)
      const offsetX = halfLength * cos - halfWidth * sin
      const offsetZ = -(halfLength * sin + halfWidth * cos)

      const finalX = worldPos.x + offsetX
      const finalZ = worldPos.z + offsetZ

      // Position above container stack
      const tier = pos.tier ?? 1
      const yPosition = tier * dims.height + 2 // 2m above top of stack

      sprite.position.set(finalX, yPosition, finalZ)

      // Scale based on texture aspect ratio
      const aspectRatio = texture.image.width / texture.image.height
      sprite.scale.set(LABEL_SCALE * aspectRatio, LABEL_SCALE, 1)

      // Store in pool
      spritePool.push(sprite)
      group.add(sprite)
    }

    return group
  }

  // Throttle label updates — sorting thousands of sprites is expensive
  let lastLabelUpdate = 0
  const LABEL_UPDATE_INTERVAL = 200 // ms

  /**
   * Update label visibility based on camera position.
   * Throttled to run at most every 200ms (not every frame).
   */
  function updateVisibility(camera: THREE.Camera): void {
    if (!labelsGroup.value || !isVisible.value) return

    const cameraHeight = camera.position.y

    if (cameraHeight < MIN_CAMERA_HEIGHT) {
      if (labelsGroup.value.visible) {
        labelsGroup.value.visible = false
        visibleLabelCount.value = 0
      }
      return
    }

    // Throttle the expensive sort+update
    const now = performance.now()
    if (now - lastLabelUpdate < LABEL_UPDATE_INTERVAL) return
    lastLabelUpdate = now

    labelsGroup.value.visible = true

    // Reuse module-level vector to avoid allocation per call
    camera.getWorldDirection(_labelCameraTarget)
    _labelCameraTarget.multiplyScalar(-100).add(camera.position)

    // Sort sprites by distance to camera target
    const spritesWithDistance = spritePool.map(sprite => ({
      sprite,
      distance: sprite.position.distanceTo(_labelCameraTarget),
    }))

    spritesWithDistance.sort((a, b) => a.distance - b.distance)

    // Show only closest MAX_VISIBLE_LABELS
    let visibleCount = 0
    for (let i = 0; i < spritesWithDistance.length; i++) {
      const { sprite, distance } = spritesWithDistance[i]!
      if (i < MAX_VISIBLE_LABELS) {
        sprite.visible = true
        visibleCount++

        const material = sprite.material as THREE.SpriteMaterial
        if (distance > 300) {
          material.opacity = Math.max(0, 1 - (distance - 300) / 200)
        } else {
          material.opacity = 1
        }
      } else {
        sprite.visible = false
      }
    }

    visibleLabelCount.value = visibleCount
  }

  /**
   * Toggle label visibility
   */
  function toggleVisibility(): void {
    isVisible.value = !isVisible.value
    if (labelsGroup.value) {
      labelsGroup.value.visible = isVisible.value
    }
  }

  /**
   * Set label visibility
   */
  function setVisibility(visible: boolean): void {
    isVisible.value = visible
    if (labelsGroup.value) {
      labelsGroup.value.visible = visible
    }
  }

  /**
   * Dispose of all resources
   */
  function dispose(): void {
    // Dispose textures
    textureCache.forEach(texture => texture.dispose())
    textureCache.clear()

    // Dispose sprites
    spritePool.forEach(sprite => {
      const material = sprite.material as THREE.SpriteMaterial
      material.dispose()
    })
    spritePool.length = 0

    // Dispose group
    if (labelsGroup.value) {
      disposeObject3D(labelsGroup.value)
      labelsGroup.value.clear()
      labelsGroup.value = null
    }

    visibleLabelCount.value = 0
  }

  return {
    // Three.js objects
    labelsGroup,

    // State
    isVisible,
    visibleLabelCount,

    // Methods
    createLabels,
    updateVisibility,
    toggleVisibility,
    setVisibility,
    dispose,
  }
}
