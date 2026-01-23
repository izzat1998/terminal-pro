/**
 * DXF to Three.js Converter
 * Parses DXF files and creates Three.js geometry for rendering
 */

import * as THREE from 'three'
import DxfParser from 'dxf-parser'
import type {
  ParsedDxf,
  DxfAnyEntity,
  DxfLine,
  DxfLwPolyline,
  DxfCircle,
  DxfArc,
  DxfInsert,
  DxfPoint,
  DxfPolylineVertex,
  DxfConversionOptions,
  DxfStats,
  DxfBlock,
  DxfText,
  DxfMText,
  DxfHatch,
  DxfSpline,
  DxfSolid,
  DxfEllipse,
  DxfCoordinateSystem,
} from '@/types/dxf'
import { DXF_UNIT_SCALES } from '@/types/dxf'
// Re-export ACI_COLORS and getAciColor for external use
export { ACI_COLORS, getAciColor, DXF_UNIT_SCALES } from '@/types/dxf'
export type { DxfCoordinateSystem } from '@/types/dxf'

// Text rendering options
interface TextRenderOptions {
  fontSize: number
  fontFamily: string
  textColor: number
  backgroundColor?: number
  rotation?: number  // Rotation in degrees
}

// Default conversion options
const DEFAULT_OPTIONS: Required<DxfConversionOptions> = {
  scale: 1,
  centerAtOrigin: true,
  defaultColor: 0x333333,
  layerColors: {},
  excludeLayers: [],
  lineWidth: 1,
  flatten2D: true,
}

/**
 * Parse DXF content string into structured data
 */
export function parseDxf(dxfContent: string): ParsedDxf {
  const parser = new DxfParser()
  const parsed = parser.parse(dxfContent)

  if (!parsed) {
    throw new Error('Failed to parse DXF file')
  }

  return {
    header: parsed.header || {},
    entities: (parsed.entities || []) as unknown as DxfAnyEntity[],
    blocks: (parsed.blocks || {}) as unknown as Record<string, DxfBlock>,
    layers: parsed.tables?.layer?.layers || {},
  }
}

/**
 * Calculate statistics about the DXF file
 */
export function getDxfStats(dxf: ParsedDxf): DxfStats {
  const byType: Record<string, number> = {}
  let minX = Infinity, minY = Infinity, minZ = Infinity
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity

  function updateBounds(point: DxfPoint): void {
    minX = Math.min(minX, point.x)
    minY = Math.min(minY, point.y)
    minZ = Math.min(minZ, point.z || 0)
    maxX = Math.max(maxX, point.x)
    maxY = Math.max(maxY, point.y)
    maxZ = Math.max(maxZ, point.z || 0)
  }

  for (const entity of dxf.entities) {
    byType[entity.type] = (byType[entity.type] || 0) + 1

    switch (entity.type) {
      case 'LINE': {
        const line = entity as DxfLine
        if (line.vertices) {
          line.vertices.forEach(updateBounds)
        }
        break
      }
      case 'LWPOLYLINE':
      case 'POLYLINE': {
        const poly = entity as DxfLwPolyline
        if (poly.vertices) {
          poly.vertices.forEach(updateBounds)
        }
        break
      }
      case 'CIRCLE': {
        const circle = entity as DxfCircle
        updateBounds({ x: circle.center.x - circle.radius, y: circle.center.y - circle.radius })
        updateBounds({ x: circle.center.x + circle.radius, y: circle.center.y + circle.radius })
        break
      }
      case 'ARC': {
        const arc = entity as DxfArc
        updateBounds({ x: arc.center.x - arc.radius, y: arc.center.y - arc.radius })
        updateBounds({ x: arc.center.x + arc.radius, y: arc.center.y + arc.radius })
        break
      }
      case 'INSERT': {
        const insert = entity as DxfInsert
        updateBounds(insert.position)
        break
      }
    }
  }

  // Handle case with no geometry
  if (minX === Infinity) {
    minX = minY = minZ = 0
    maxX = maxY = maxZ = 1
  }

  return {
    entityCount: {
      total: dxf.entities.length,
      byType,
    },
    bounds: {
      min: { x: minX, y: minY, z: minZ },
      max: { x: maxX, y: maxY, z: maxZ },
      width: maxX - minX,
      height: maxY - minY,
      depth: maxZ - minZ,
    },
    layerCount: Object.keys(dxf.layers).length,
    blockCount: Object.keys(dxf.blocks).length,
  }
}

/**
 * Get color for an entity based on layer and color index
 */
function getEntityColor(
  entity: DxfAnyEntity,
  dxf: ParsedDxf,
  options: Required<DxfConversionOptions>
): number {
  // Check layer-specific color mapping first
  const layerColor = options.layerColors[entity.layer]
  if (layerColor !== undefined) {
    return layerColor
  }

  // Check entity's direct color index
  if (entity.colorIndex !== undefined && entity.colorIndex !== 256) {
    const aciColors: Record<number, number> = {
      0: 0x000000,
      1: 0xff0000,
      2: 0xffff00,
      3: 0x00ff00,
      4: 0x00ffff,
      5: 0x0000ff,
      6: 0xff00ff,
      7: 0x333333,
      8: 0x414141,
      9: 0x808080,
    }
    return aciColors[entity.colorIndex] || options.defaultColor
  }

  // Check layer color
  const layer = dxf.layers[entity.layer]
  if (layer?.color !== undefined) {
    const aciColors: Record<number, number> = {
      1: 0xff0000,
      2: 0xffff00,
      3: 0x00ff00,
      4: 0x00ffff,
      5: 0x0000ff,
      6: 0xff00ff,
      7: 0x333333,
    }
    return aciColors[layer.color] || options.defaultColor
  }

  return options.defaultColor
}

/**
 * Convert a point from DXF coordinates to Three.js coordinates
 * DXF: Y is up in 2D, Z is up in 3D
 * Three.js: Y is up
 */
function toThreePoint(
  point: DxfPoint,
  center: DxfPoint,
  options: Required<DxfConversionOptions>
): THREE.Vector3 {
  const x = (point.x - (options.centerAtOrigin ? center.x : 0)) * options.scale
  const y = (point.y - (options.centerAtOrigin ? center.y : 0)) * options.scale
  const z = options.flatten2D ? 0 : ((point.z || 0) - (options.centerAtOrigin ? (center.z || 0) : 0)) * options.scale

  // Swap Y and Z for Three.js (Y up instead of Z up)
  return new THREE.Vector3(x, z, -y)
}

/**
 * Convert LINE entity to Three.js geometry
 */
function convertLine(
  entity: DxfLine,
  center: DxfPoint,
  options: Required<DxfConversionOptions>
): THREE.BufferGeometry | null {
  if (!entity.vertices || entity.vertices.length < 2) return null

  const points: THREE.Vector3[] = []
  for (const v of entity.vertices) {
    if (!isValidNumber(v.x) || !isValidNumber(v.y)) continue
    const point = toThreePoint(v, center, options)
    if (isValidPoint(point)) {
      points.push(point)
    }
  }

  if (points.length < 2) return null
  return new THREE.BufferGeometry().setFromPoints(points)
}

/**
 * Check if a value is valid (not NaN, not Infinity)
 */
function isValidNumber(n: number): boolean {
  return Number.isFinite(n)
}

/**
 * Check if a point has valid coordinates
 */
function isValidPoint(p: THREE.Vector3): boolean {
  return isValidNumber(p.x) && isValidNumber(p.y) && isValidNumber(p.z)
}

/**
 * Calculate arc points from bulge factor
 * Bulge = tan(angle/4), where angle is the included angle of the arc
 */
function getArcPointsFromBulge(
  start: DxfPolylineVertex,
  end: DxfPolylineVertex,
  bulge: number,
  center: DxfPoint,
  options: Required<DxfConversionOptions>,
  segments: number = 16
): THREE.Vector3[] {
  const points: THREE.Vector3[] = []

  // Validate input coordinates
  if (!isValidNumber(start.x) || !isValidNumber(start.y) ||
      !isValidNumber(end.x) || !isValidNumber(end.y)) {
    return points // Return empty if invalid input
  }

  if (Math.abs(bulge) < 0.0001) {
    // Straight line
    const p1 = toThreePoint(start, center, options)
    const p2 = toThreePoint(end, center, options)
    if (isValidPoint(p1)) points.push(p1)
    if (isValidPoint(p2)) points.push(p2)
    return points
  }

  // Calculate arc parameters from bulge
  const angle = 4 * Math.atan(bulge)
  const dx = end.x - start.x
  const dy = end.y - start.y
  const chord = Math.sqrt(dx * dx + dy * dy)

  // Avoid division by zero or near-zero
  const sinHalfAngle = Math.sin(angle / 2)
  if (Math.abs(sinHalfAngle) < 0.0001 || chord < 0.0001) {
    // Degenerate case - treat as straight line
    const p1 = toThreePoint(start, center, options)
    const p2 = toThreePoint(end, center, options)
    if (isValidPoint(p1)) points.push(p1)
    if (isValidPoint(p2)) points.push(p2)
    return points
  }

  const radius = Math.abs(chord / (2 * sinHalfAngle))

  // Validate radius
  if (!isValidNumber(radius) || radius < 0.0001) {
    const p1 = toThreePoint(start, center, options)
    const p2 = toThreePoint(end, center, options)
    if (isValidPoint(p1)) points.push(p1)
    if (isValidPoint(p2)) points.push(p2)
    return points
  }

  // Arc center offset perpendicular to chord
  const chordAngle = Math.atan2(dy, dx)
  const h = radius * Math.cos(angle / 2) // Distance from chord midpoint to arc center
  const midX = (start.x + end.x) / 2
  const midY = (start.y + end.y) / 2

  // Center is perpendicular to chord, direction based on bulge sign
  const sign = bulge > 0 ? 1 : -1
  const arcCenterX = midX - sign * h * Math.sin(chordAngle)
  const arcCenterY = midY + sign * h * Math.cos(chordAngle)

  // Validate arc center
  if (!isValidNumber(arcCenterX) || !isValidNumber(arcCenterY)) {
    const p1 = toThreePoint(start, center, options)
    const p2 = toThreePoint(end, center, options)
    if (isValidPoint(p1)) points.push(p1)
    if (isValidPoint(p2)) points.push(p2)
    return points
  }

  // Calculate start and end angles
  const startAngle = Math.atan2(start.y - arcCenterY, start.x - arcCenterX)
  let endAngle = Math.atan2(end.y - arcCenterY, end.x - arcCenterX)

  // Ensure correct direction
  if (bulge > 0 && endAngle < startAngle) endAngle += 2 * Math.PI
  if (bulge < 0 && endAngle > startAngle) endAngle -= 2 * Math.PI

  // Generate arc points
  for (let i = 0; i <= segments; i++) {
    const t = i / segments
    const a = startAngle + t * (endAngle - startAngle)
    const px = arcCenterX + radius * Math.cos(a)
    const py = arcCenterY + radius * Math.sin(a)
    const point = toThreePoint({ x: px, y: py, z: start.z || 0 }, center, options)
    if (isValidPoint(point)) {
      points.push(point)
    }
  }

  return points
}

/**
 * Convert LWPOLYLINE/POLYLINE entity to Three.js geometry
 */
function convertPolyline(
  entity: DxfLwPolyline,
  center: DxfPoint,
  options: Required<DxfConversionOptions>
): THREE.BufferGeometry | null {
  if (!entity.vertices || entity.vertices.length < 2) return null

  const allPoints: THREE.Vector3[] = []
  const vertices = entity.vertices

  for (let i = 0; i < vertices.length - 1; i++) {
    const current = vertices[i]
    const next = vertices[i + 1]
    if (!current || !next) continue

    const bulge = current.bulge || 0

    const segmentPoints = getArcPointsFromBulge(current, next, bulge, center, options)
    // Skip first point if not the first segment (to avoid duplicates)
    const pointsToAdd = i === 0 ? segmentPoints : segmentPoints.slice(1)
    for (const p of pointsToAdd) {
      if (isValidPoint(p)) {
        allPoints.push(p)
      }
    }
  }

  // Close the shape if needed
  if (entity.shape && vertices.length > 2) {
    const last = vertices[vertices.length - 1]
    const first = vertices[0]
    if (last && first) {
      const bulge = last.bulge || 0

      const segmentPoints = getArcPointsFromBulge(last, first, bulge, center, options)
      for (const p of segmentPoints.slice(1)) {
        if (isValidPoint(p)) {
          allPoints.push(p)
        }
      }
    }
  }

  if (allPoints.length < 2) return null
  return new THREE.BufferGeometry().setFromPoints(allPoints)
}

/**
 * Convert CIRCLE entity to Three.js geometry
 */
function convertCircle(
  entity: DxfCircle,
  center: DxfPoint,
  options: Required<DxfConversionOptions>
): THREE.BufferGeometry | null {
  // Validate inputs
  if (!isValidNumber(entity.center.x) || !isValidNumber(entity.center.y) ||
      !isValidNumber(entity.radius) || entity.radius < 0.0001) {
    return null
  }

  const segments = 64
  const points: THREE.Vector3[] = []

  for (let i = 0; i <= segments; i++) {
    const angle = (i / segments) * Math.PI * 2
    const x = entity.center.x + entity.radius * Math.cos(angle)
    const y = entity.center.y + entity.radius * Math.sin(angle)
    const point = toThreePoint({ x, y, z: entity.center.z || 0 }, center, options)
    if (isValidPoint(point)) {
      points.push(point)
    }
  }

  if (points.length < 2) return null
  return new THREE.BufferGeometry().setFromPoints(points)
}

/**
 * Convert ARC entity to Three.js geometry
 */
function convertArc(
  entity: DxfArc,
  center: DxfPoint,
  options: Required<DxfConversionOptions>
): THREE.BufferGeometry | null {
  // Validate inputs
  if (!isValidNumber(entity.center.x) || !isValidNumber(entity.center.y) ||
      !isValidNumber(entity.radius) || entity.radius < 0.0001 ||
      !isValidNumber(entity.startAngle) || !isValidNumber(entity.endAngle)) {
    return null
  }

  const segments = 32
  const points: THREE.Vector3[] = []

  // DXF angles are in degrees
  const startRad = (entity.startAngle * Math.PI) / 180
  const endRad = (entity.endAngle * Math.PI) / 180

  // Handle angle wrapping
  let angleDiff = endRad - startRad
  if (angleDiff < 0) angleDiff += 2 * Math.PI

  for (let i = 0; i <= segments; i++) {
    const t = i / segments
    const angle = startRad + t * angleDiff
    const x = entity.center.x + entity.radius * Math.cos(angle)
    const y = entity.center.y + entity.radius * Math.sin(angle)
    const point = toThreePoint({ x, y, z: entity.center.z || 0 }, center, options)
    if (isValidPoint(point)) {
      points.push(point)
    }
  }

  if (points.length < 2) return null
  return new THREE.BufferGeometry().setFromPoints(points)
}

/**
 * Create a text sprite from canvas
 * Note: Sprites always face the camera, so rotation is applied to the canvas content
 */
function createTextSprite(
  text: string,
  position: THREE.Vector3,
  options: TextRenderOptions
): THREE.Sprite {
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')!

  // Clamp font size to reasonable range to avoid massive textures
  const clampedFontSize = Math.min(Math.max(options.fontSize, 1), 100)
  const fontSize = clampedFontSize * 10 // Scale up for quality

  context.font = `${fontSize}px ${options.fontFamily}`
  const metrics = context.measureText(text)
  const textWidth = metrics.width
  const textHeight = fontSize * 1.2

  // Account for rotation in canvas size (expand to fit rotated text)
  const rotation = options.rotation ?? 0
  const rotationRad = (rotation * Math.PI) / 180
  const cos = Math.abs(Math.cos(rotationRad))
  const sin = Math.abs(Math.sin(rotationRad))

  // Calculate rotated bounding box
  const rotatedWidth = textWidth * cos + textHeight * sin
  const rotatedHeight = textWidth * sin + textHeight * cos

  // Clamp canvas size to avoid WebGL texture limits (max 16384 typically)
  const maxCanvasSize = 4096
  canvas.width = Math.min(Math.ceil(rotatedWidth + 40), maxCanvasSize)
  canvas.height = Math.min(Math.ceil(rotatedHeight + 40), maxCanvasSize)

  // Draw background if specified (before rotation)
  if (options.backgroundColor !== undefined) {
    context.fillStyle = `#${options.backgroundColor.toString(16).padStart(6, '0')}`
    context.fillRect(0, 0, canvas.width, canvas.height)
  }

  // Apply rotation around canvas center
  context.translate(canvas.width / 2, canvas.height / 2)
  context.rotate(rotationRad)

  // Draw text (centered at origin after rotation)
  context.font = `${fontSize}px ${options.fontFamily}`
  context.fillStyle = `#${options.textColor.toString(16).padStart(6, '0')}`
  context.textBaseline = 'middle'
  context.textAlign = 'center'
  context.fillText(text, 0, 0)

  // Create texture and sprite
  const texture = new THREE.CanvasTexture(canvas)
  texture.minFilter = THREE.LinearFilter
  texture.magFilter = THREE.LinearFilter

  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
  })

  const sprite = new THREE.Sprite(material)
  sprite.position.copy(position)

  // Scale sprite to match text size
  const scale = options.fontSize * 0.1
  sprite.scale.set((canvas.width / canvas.height) * scale, scale, 1)

  // Store rotation in userData for reference
  sprite.userData.rotation = rotation

  return sprite
}

/**
 * Convert TEXT entity to Three.js sprite
 */
function convertText(
  entity: DxfText,
  center: DxfPoint,
  options: Required<DxfConversionOptions>,
  color: number
): THREE.Sprite | null {
  if (!entity.text || entity.text.trim() === '') return null

  // Validate start point
  if (!entity.startPoint ||
      !isValidNumber(entity.startPoint.x) || !isValidNumber(entity.startPoint.y)) {
    return null
  }

  const position = toThreePoint(entity.startPoint, center, options)
  if (!isValidPoint(position)) return null

  const sprite = createTextSprite(entity.text, position, {
    fontSize: (entity.textHeight || 2.5) * options.scale,
    fontFamily: 'Arial, sans-serif',
    textColor: color,
    rotation: entity.rotation ?? 0,  // Pass rotation to sprite creator
  })

  return sprite
}

/**
 * Clean MTEXT formatting codes
 * Removes AutoCAD formatting like {\fArial;text} etc.
 */
function cleanMTextFormatting(text: string): string {
  // Remove common MTEXT formatting codes
  return text
    .replace(/\\P/g, '\n')           // Paragraph breaks
    .replace(/\\[Ff][^;]*;/g, '')    // Font changes
    .replace(/\\[Hh]\d+(\.\d+)?;/g, '') // Height changes
    .replace(/\\[Ww]\d+(\.\d+)?;/g, '') // Width factor
    .replace(/\\[Oo]/g, '')          // Overline
    .replace(/\\[Ll]/g, '')          // Underline
    .replace(/\\[Kk]/g, '')          // Strikethrough
    .replace(/\{|\}/g, '')           // Braces
    .replace(/\\[^\\]/g, '')         // Other escape sequences
    .trim()
}

/**
 * Convert MTEXT entity to Three.js sprite
 */
function convertMText(
  entity: DxfMText,
  center: DxfPoint,
  options: Required<DxfConversionOptions>,
  color: number
): THREE.Sprite | null {
  if (!entity.text || entity.text.trim() === '') return null

  const cleanText = cleanMTextFormatting(entity.text)
  if (cleanText === '') return null

  // Validate position
  if (!entity.position ||
      !isValidNumber(entity.position.x) || !isValidNumber(entity.position.y)) {
    return null
  }

  const position = toThreePoint(entity.position, center, options)
  if (!isValidPoint(position)) return null

  const sprite = createTextSprite(cleanText, position, {
    fontSize: (entity.height || 2.5) * options.scale,
    fontFamily: 'Arial, sans-serif',
    textColor: color,
  })

  if (entity.rotation) {
    sprite.userData.rotation = entity.rotation
  }

  return sprite
}

/**
 * Check if a Vector2 has valid coordinates
 */
function isValidVector2(v: THREE.Vector2): boolean {
  return isValidNumber(v.x) && isValidNumber(v.y)
}

/**
 * Generate arc points for hatch boundaries
 */
function getHatchArcPoints(
  arc: { center: DxfPoint; radius: number; startAngle: number; endAngle: number },
  center: DxfPoint,
  options: Required<DxfConversionOptions>,
  segments: number = 16
): THREE.Vector2[] {
  const points: THREE.Vector2[] = []

  // Validate arc parameters
  if (!isValidNumber(arc.center.x) || !isValidNumber(arc.center.y) ||
      !isValidNumber(arc.radius) || arc.radius < 0.0001 ||
      !isValidNumber(arc.startAngle) || !isValidNumber(arc.endAngle)) {
    return points
  }

  // DXF angles are in degrees for hatch arcs
  const startRad = (arc.startAngle * Math.PI) / 180
  const endRad = (arc.endAngle * Math.PI) / 180

  // Handle angle wrapping
  let angleDiff = endRad - startRad
  if (angleDiff < 0) angleDiff += 2 * Math.PI

  for (let i = 0; i <= segments; i++) {
    const t = i / segments
    const angle = startRad + t * angleDiff
    const x = arc.center.x + arc.radius * Math.cos(angle)
    const y = arc.center.y + arc.radius * Math.sin(angle)
    const pt = toThreePoint({ x, y, z: arc.center.z || 0 }, center, options)
    const vec2 = new THREE.Vector2(pt.x, pt.z)
    if (isValidVector2(vec2)) {
      points.push(vec2)
    }
  }

  return points
}

/**
 * Convert HATCH boundary to filled mesh
 */
function convertHatch(
  entity: DxfHatch,
  center: DxfPoint,
  options: Required<DxfConversionOptions>,
  color: number
): THREE.Mesh | THREE.Group | null {
  if (!entity.boundaryPaths || entity.boundaryPaths.length === 0) return null

  const group = new THREE.Group()
  group.name = `hatch_${entity.layer}`

  for (const boundary of entity.boundaryPaths) {
    const points: THREE.Vector2[] = []

    // Handle polyline boundaries
    if (boundary.polylines) {
      for (const polyline of boundary.polylines) {
        for (const vertex of polyline) {
          if (!isValidNumber(vertex.x) || !isValidNumber(vertex.y)) continue
          const pt = toThreePoint({ x: vertex.x, y: vertex.y }, center, options)
          const vec2 = new THREE.Vector2(pt.x, pt.z)
          if (isValidVector2(vec2)) {
            points.push(vec2)
          }
        }
      }
    }

    // Handle line boundaries
    if (boundary.lines) {
      for (const line of boundary.lines) {
        if (!line.start || !line.end) continue
        if (!isValidNumber(line.start.x) || !isValidNumber(line.start.y) ||
            !isValidNumber(line.end.x) || !isValidNumber(line.end.y)) continue

        const startPt = toThreePoint(line.start, center, options)
        const endPt = toThreePoint(line.end, center, options)
        const startVec2 = new THREE.Vector2(startPt.x, startPt.z)
        const endVec2 = new THREE.Vector2(endPt.x, endPt.z)

        if (isValidVector2(startVec2)) points.push(startVec2)
        if (isValidVector2(endVec2)) points.push(endVec2)
      }
    }

    // Handle arc boundaries
    if (boundary.arcs) {
      for (const arc of boundary.arcs) {
        const arcPoints = getHatchArcPoints(arc, center, options)
        // Skip first point if not first segment to avoid duplicates
        const pointsToAdd = points.length === 0 ? arcPoints : arcPoints.slice(1)
        for (const ap of pointsToAdd) {
          if (isValidVector2(ap)) {
            points.push(ap)
          }
        }
      }
    }

    // Need at least 3 valid points for a shape
    if (points.length < 3) continue

    // Final validation - ensure all points are valid
    const validPoints = points.filter(isValidVector2)
    if (validPoints.length < 3) continue

    try {
      // Create shape from points
      const shape = new THREE.Shape(validPoints)
      const geometry = new THREE.ShapeGeometry(shape)

      // Rotate geometry to lie flat (XZ plane)
      geometry.rotateX(-Math.PI / 2)

      const material = new THREE.MeshBasicMaterial({
        color,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: entity.solid ? 0.8 : 0.5,
      })

      const mesh = new THREE.Mesh(geometry, material)
      mesh.position.y = 0.01 // Slightly above ground to avoid z-fighting
      group.add(mesh)
    } catch {
      // ShapeGeometry can throw on degenerate shapes
      continue
    }
  }

  return group.children.length > 0 ? group : null
}

/**
 * Convert SPLINE entity to Three.js curve
 * Handles both fit points (interpolation) and control points (approximation)
 */
function convertSpline(
  entity: DxfSpline,
  center: DxfPoint,
  options: Required<DxfConversionOptions>
): THREE.BufferGeometry | null {
  // Prefer fit points if available (they lie on the curve)
  // Otherwise use control points (curve approximates them)
  const hasFitPoints = entity.fitPoints && entity.fitPoints.length >= 2
  const hasControlPoints = entity.controlPoints && entity.controlPoints.length >= 2

  if (!hasFitPoints && !hasControlPoints) return null

  const sourcePoints = hasFitPoints ? entity.fitPoints : entity.controlPoints
  if (!sourcePoints || sourcePoints.length < 2) return null

  // Convert to Three.js points, filtering out invalid ones
  const points: THREE.Vector3[] = []
  for (const p of sourcePoints) {
    if (!isValidNumber(p.x) || !isValidNumber(p.y)) continue
    const point = toThreePoint(p, center, options)
    if (isValidPoint(point)) {
      points.push(point)
    }
  }

  // Need at least 2 valid points for a curve
  if (points.length < 2) return null

  // Determine interpolation quality based on spline degree
  // Higher degree = smoother curve = more sample points needed
  const degree = entity.degree ?? 3
  const sampleMultiplier = Math.max(degree * 4, 10)
  const numSamples = Math.max(points.length * sampleMultiplier, 50)

  // For fit points, use CatmullRom (passes through all points)
  // For control points, use CatmullRom with tension 0 for smoother B-spline approximation
  const tension = hasFitPoints ? 0.5 : 0.0

  try {
    const curve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', tension)
    const sampledPoints = curve.getPoints(numSamples)

    // Validate sampled points
    const validSampledPoints = sampledPoints.filter(isValidPoint)
    if (validSampledPoints.length < 2) return null

    return new THREE.BufferGeometry().setFromPoints(validSampledPoints)
  } catch {
    // CatmullRomCurve3 can throw on edge cases
    return null
  }
}

/**
 * Convert SOLID entity (filled triangle/quad) to Three.js mesh
 */
function convertSolid(
  entity: DxfSolid,
  center: DxfPoint,
  options: Required<DxfConversionOptions>,
  color: number
): THREE.Mesh | null {
  if (!entity.points || entity.points.length < 3) return null

  // Convert and validate points
  const points: THREE.Vector3[] = []
  for (const p of entity.points) {
    if (!p || !isValidNumber(p.x) || !isValidNumber(p.y)) continue
    const point = toThreePoint(p, center, options)
    if (isValidPoint(point)) {
      points.push(point)
    }
  }

  if (points.length < 3) return null

  const geometry = new THREE.BufferGeometry()
  const vertices: number[] = []

  // Triangle 1 - validate before adding
  const p0 = points[0]
  const p1 = points[1]
  const p2 = points[2]
  if (!p0 || !p1 || !p2) return null

  vertices.push(p0.x, p0.y, p0.z)
  vertices.push(p1.x, p1.y, p1.z)
  vertices.push(p2.x, p2.y, p2.z)

  // Triangle 2 (if quad)
  if (points.length >= 4) {
    const p3 = points[3]
    if (p3 && isValidPoint(p3)) {
      vertices.push(p0.x, p0.y, p0.z)
      vertices.push(p2.x, p2.y, p2.z)
      vertices.push(p3.x, p3.y, p3.z)
    }
  }

  // Final NaN check on all vertices
  for (const v of vertices) {
    if (!isValidNumber(v)) return null
  }

  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3))
  geometry.computeVertexNormals()

  const material = new THREE.MeshBasicMaterial({
    color,
    side: THREE.DoubleSide,
  })

  return new THREE.Mesh(geometry, material)
}

/**
 * Convert ELLIPSE entity to Three.js geometry
 */
function convertEllipse(
  entity: DxfEllipse,
  center: DxfPoint,
  options: Required<DxfConversionOptions>
): THREE.BufferGeometry | null {
  // Validate inputs
  if (!isValidNumber(entity.center.x) || !isValidNumber(entity.center.y) ||
      !isValidNumber(entity.majorAxisEndPoint.x) || !isValidNumber(entity.majorAxisEndPoint.y) ||
      !isValidNumber(entity.axisRatio) || entity.axisRatio < 0.0001 ||
      !isValidNumber(entity.startAngle) || !isValidNumber(entity.endAngle)) {
    return null
  }

  const segments = 64
  const points: THREE.Vector3[] = []

  // Calculate ellipse parameters
  const majorLength = Math.sqrt(
    entity.majorAxisEndPoint.x ** 2 + entity.majorAxisEndPoint.y ** 2
  )

  // Validate major axis length
  if (!isValidNumber(majorLength) || majorLength < 0.0001) {
    return null
  }

  const minorLength = majorLength * entity.axisRatio
  const rotation = Math.atan2(entity.majorAxisEndPoint.y, entity.majorAxisEndPoint.x)

  // DXF angles are in radians for ellipse
  const startAngle = entity.startAngle
  const endAngle = entity.endAngle
  let angleDiff = endAngle - startAngle
  if (angleDiff < 0) angleDiff += 2 * Math.PI

  for (let i = 0; i <= segments; i++) {
    const t = i / segments
    const angle = startAngle + t * angleDiff

    // Parametric ellipse
    const x = majorLength * Math.cos(angle)
    const y = minorLength * Math.sin(angle)

    // Rotate and translate
    const rx = x * Math.cos(rotation) - y * Math.sin(rotation) + entity.center.x
    const ry = x * Math.sin(rotation) + y * Math.cos(rotation) + entity.center.y

    const point = toThreePoint({ x: rx, y: ry, z: entity.center.z || 0 }, center, options)
    if (isValidPoint(point)) {
      points.push(point)
    }
  }

  if (points.length < 2) return null
  return new THREE.BufferGeometry().setFromPoints(points)
}

/**
 * Convert INSERT (block reference) to Three.js group
 */
function convertInsert(
  entity: DxfInsert,
  dxf: ParsedDxf,
  center: DxfPoint,
  options: Required<DxfConversionOptions>
): THREE.Group | null {
  const block = dxf.blocks[entity.name]
  if (!block || !block.entities) return null

  const group = new THREE.Group()
  group.name = `block_${entity.name}`

  // Process block entities
  for (const blockEntity of block.entities) {
    const geometry = convertEntity(blockEntity, dxf, { x: 0, y: 0, z: 0 }, {
      ...options,
      centerAtOrigin: false,
    })
    if (geometry) {
      group.add(geometry)
    }
  }

  // Apply transformations
  const pos = toThreePoint(entity.position, center, options)
  group.position.copy(pos)

  if (entity.rotation) {
    // DXF rotation is counter-clockwise from +X, same as Three.js Y rotation when viewed from above
    // No negation needed (was incorrectly negated before)
    group.rotation.y = (entity.rotation * Math.PI) / 180
  }

  if (entity.xScale !== undefined) group.scale.x = entity.xScale
  if (entity.yScale !== undefined) group.scale.z = entity.yScale
  if (entity.zScale !== undefined) group.scale.y = entity.zScale

  return group
}

/**
 * Convert a single DXF entity to Three.js object
 */
function convertEntity(
  entity: DxfAnyEntity,
  dxf: ParsedDxf,
  center: DxfPoint,
  options: Required<DxfConversionOptions>
): THREE.Object3D | null {
  // Skip excluded layers
  if (options.excludeLayers.includes(entity.layer)) {
    return null
  }

  const color = getEntityColor(entity, dxf, options)
  let geometry: THREE.BufferGeometry | null = null
  let object: THREE.Object3D | null = null

  switch (entity.type) {
    case 'LINE':
      geometry = convertLine(entity as DxfLine, center, options)
      break

    case 'LWPOLYLINE':
    case 'POLYLINE':
      geometry = convertPolyline(entity as DxfLwPolyline, center, options)
      break

    case 'CIRCLE':
      geometry = convertCircle(entity as DxfCircle, center, options)
      break

    case 'ARC':
      geometry = convertArc(entity as DxfArc, center, options)
      break

    case 'INSERT':
      object = convertInsert(entity as DxfInsert, dxf, center, options)
      break

    case 'TEXT':
      object = convertText(entity as DxfText, center, options, color)
      break

    case 'MTEXT':
      object = convertMText(entity as DxfMText, center, options, color)
      break

    case 'HATCH':
      object = convertHatch(entity as DxfHatch, center, options, color)
      break

    case 'SPLINE':
      geometry = convertSpline(entity as DxfSpline, center, options)
      break

    case 'SOLID':
      object = convertSolid(entity as DxfSolid, center, options, color)
      break

    case 'ELLIPSE':
      geometry = convertEllipse(entity as DxfEllipse, center, options)
      break

    // DIMENSION entities are typically rendered via their block reference
    case 'DIMENSION':
      // Dimensions usually have associated block inserts that render the geometry
      return null

    default:
      // Skip unsupported entity types
      return null
  }

  if (geometry) {
    const material = new THREE.LineBasicMaterial({
      color,
      linewidth: options.lineWidth,
    })
    object = new THREE.Line(geometry, material)
  }

  if (object) {
    object.name = `${entity.type}_${entity.layer}`
    object.userData.layer = entity.layer
    object.userData.entityType = entity.type
  }

  return object
}

/**
 * Result of DXF to Three.js conversion
 */
export interface DxfConversionResult {
  /** Root group containing all geometry */
  group: THREE.Group
  /** Statistics about the conversion */
  stats: DxfStats
  /** Parsed DXF data for reference */
  dxf: ParsedDxf
  /** Center point used for origin alignment */
  center: DxfPoint
  /** Layer groups for visibility control */
  layerGroups: Map<string, THREE.Group>
  /** Text sprites for separate handling */
  textSprites: THREE.Sprite[]
  /** Coordinate system for bidirectional transforms */
  coordinateSystem: DxfCoordinateSystem
}

/**
 * Detect unit scale from DXF header INSUNITS
 */
function getUnitScale(dxf: ParsedDxf): number {
  const insunits = dxf.header.$INSUNITS
  if (typeof insunits === 'number' && DXF_UNIT_SCALES[insunits] !== undefined) {
    return DXF_UNIT_SCALES[insunits]
  }
  // Default to meters if not specified
  return 1.0
}

/**
 * Convert entire DXF to Three.js group with layer organization
 */
export function dxfToThree(
  dxfContent: string,
  userOptions: DxfConversionOptions = {}
): DxfConversionResult {
  // Parse DXF
  const dxf = parseDxf(dxfContent)
  const stats = getDxfStats(dxf)

  // Detect unit scale from DXF header
  const detectedScale = getUnitScale(dxf)

  // Merge options, ensuring scale is properly set
  const mergedOptions = {
    ...DEFAULT_OPTIONS,
    ...userOptions,
  }
  // Ensure scale is set (use detected if user didn't provide a valid number)
  const finalScale = typeof userOptions.scale === 'number' ? userOptions.scale : detectedScale

  const options: Required<DxfConversionOptions> = {
    ...mergedOptions,
    scale: finalScale,
  } as Required<DxfConversionOptions>

  // Use DXF header extents ($EXTMIN/$EXTMAX) if available - these are more reliable
  // than calculated bounds which can include distant reference points
  const headerExtMin = dxf.header.$EXTMIN as DxfPoint | undefined
  const headerExtMax = dxf.header.$EXTMAX as DxfPoint | undefined

  let effectiveBounds = stats.bounds
  if (headerExtMin && headerExtMax &&
      isValidNumber(headerExtMin.x) && isValidNumber(headerExtMin.y) &&
      isValidNumber(headerExtMax.x) && isValidNumber(headerExtMax.y)) {
    effectiveBounds = {
      min: headerExtMin,
      max: headerExtMax,
      width: headerExtMax.x - headerExtMin.x,
      height: headerExtMax.y - headerExtMin.y,
      depth: (headerExtMax.z ?? 0) - (headerExtMin.z ?? 0),
    }
  }

  // Calculate center for origin alignment (use header extents if available)
  const center: DxfPoint = options.centerAtOrigin
    ? {
        x: (effectiveBounds.min.x + effectiveBounds.max.x) / 2,
        y: (effectiveBounds.min.y + effectiveBounds.max.y) / 2,
        z: ((effectiveBounds.min.z ?? 0) + (effectiveBounds.max.z ?? 0)) / 2,
      }
    : { x: 0, y: 0, z: 0 }

  // Create coordinate system for bidirectional transforms
  // Ensure scale is always a valid number (never undefined)
  const coordinateSystemScale = typeof options.scale === 'number' && Number.isFinite(options.scale)
    ? options.scale
    : 1.0

  const coordinateSystem: DxfCoordinateSystem = {
    center,
    scale: coordinateSystemScale,
    units: dxf.header.$INSUNITS ?? 6, // Default to meters
    bounds: {
      min: effectiveBounds.min,
      max: effectiveBounds.max,
      width: effectiveBounds.width,
      height: effectiveBounds.height,
    },
  }

  // Create root group
  const group = new THREE.Group()
  group.name = 'dxf_root'

  // Create layer groups for organized access
  const layerGroups = new Map<string, THREE.Group>()
  const textSprites: THREE.Sprite[] = []

  // ============================================
  // PERFORMANCE OPTIMIZATION: Merge LINE entities by layer
  // This reduces draw calls from 20,000+ to ~20 (one per layer)
  // ============================================

  // Collect LINE vertices by layer for batch processing
  const lineVerticesByLayer = new Map<string, { positions: number[]; color: number }>()

  // First pass: Collect LINE entities and process other entities
  for (const entity of dxf.entities) {
    // Skip excluded layers
    if (options.excludeLayers.includes(entity.layer)) continue

    const layerName = entity.layer || '0'

    // Ensure layer group exists
    if (!layerGroups.has(layerName)) {
      const layerGroup = new THREE.Group()
      layerGroup.name = `layer_${layerName}`
      layerGroup.userData.layerName = layerName
      layerGroups.set(layerName, layerGroup)
      group.add(layerGroup)
    }

    // Special handling for LINE entities - collect for merging
    if (entity.type === 'LINE') {
      const line = entity as DxfLine
      if (line.vertices && line.vertices.length >= 2) {
        const vertex0 = line.vertices[0]
        const vertex1 = line.vertices[1]

        // Validate input coordinates
        if (!vertex0 || !vertex1 ||
            !isValidNumber(vertex0.x) || !isValidNumber(vertex0.y) ||
            !isValidNumber(vertex1.x) || !isValidNumber(vertex1.y)) {
          continue // Skip invalid LINE
        }

        const v0 = toThreePoint(vertex0, center, options)
        const v1 = toThreePoint(vertex1, center, options)

        // Validate output coordinates
        if (!isValidPoint(v0) || !isValidPoint(v1)) {
          continue // Skip if conversion produced NaN
        }

        if (!lineVerticesByLayer.has(layerName)) {
          const color = getEntityColor(entity, dxf, options)
          lineVerticesByLayer.set(layerName, { positions: [], color })
        }

        const layerData = lineVerticesByLayer.get(layerName)!
        // Add as line segment (2 vertices per line)
        layerData.positions.push(v0.x, v0.y, v0.z, v1.x, v1.y, v1.z)
      }
      continue // Skip normal processing for LINEs
    }

    // Process all other entity types normally
    const object = convertEntity(entity, dxf, center, options)
    if (object) {
      const layerGroup = layerGroups.get(layerName)!
      layerGroup.add(object)

      // Track text sprites separately for zoom-based scaling
      if (object instanceof THREE.Sprite) {
        textSprites.push(object)
      }
    }
  }

  // Second pass: Create merged LineSegments for each layer's LINEs
  let skippedNaNCount = 0
  for (const [layerName, layerData] of lineVerticesByLayer) {
    if (layerData.positions.length === 0) continue

    // Final validation: check for NaN values in positions
    const validPositions: number[] = []
    for (let i = 0; i < layerData.positions.length; i += 6) {
      const x0 = layerData.positions[i] ?? NaN
      const y0 = layerData.positions[i + 1] ?? NaN
      const z0 = layerData.positions[i + 2] ?? NaN
      const x1 = layerData.positions[i + 3] ?? NaN
      const y1 = layerData.positions[i + 4] ?? NaN
      const z1 = layerData.positions[i + 5] ?? NaN

      if (isValidNumber(x0) && isValidNumber(y0) && isValidNumber(z0) &&
          isValidNumber(x1) && isValidNumber(y1) && isValidNumber(z1)) {
        validPositions.push(x0, y0, z0, x1, y1, z1)
      } else {
        skippedNaNCount++
      }
    }

    if (validPositions.length === 0) continue

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(validPositions, 3)
    )

    const material = new THREE.LineBasicMaterial({
      color: layerData.color,
      linewidth: options.lineWidth,
    })

    // Use LineSegments for disconnected line pairs (more efficient than Line)
    const lineSegments = new THREE.LineSegments(geometry, material)
    lineSegments.name = `merged_lines_${layerName}`
    lineSegments.userData.layer = layerName
    lineSegments.userData.entityType = 'LINE_MERGED'
    lineSegments.userData.lineCount = validPositions.length / 6

    const layerGroup = layerGroups.get(layerName)!
    layerGroup.add(lineSegments)
  }

  if (skippedNaNCount > 0) {
    console.warn(`Skipped ${skippedNaNCount} LINE segments with invalid (NaN) coordinates`)
  }

  return { group, stats, dxf, center, layerGroups, textSprites, coordinateSystem }
}

/**
 * Load DXF file from URL and convert to Three.js
 */
export async function loadDxfFromUrl(
  url: string,
  options: DxfConversionOptions = {}
): Promise<DxfConversionResult> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to load DXF: ${response.statusText}`)
  }
  const content = await response.text()
  return dxfToThree(content, options)
}

/**
 * Load DXF file from File object and convert to Three.js
 */
export async function loadDxfFromFile(
  file: File,
  options: DxfConversionOptions = {}
): Promise<DxfConversionResult> {
  const content = await file.text()
  return dxfToThree(content, options)
}

/**
 * Convert DXF coordinates to Three.js world coordinates
 * Uses the coordinate system from a DXF conversion result
 */
export function dxfToWorldCoordinates(
  dxfX: number,
  dxfY: number,
  dxfZ: number,
  coordSystem: DxfCoordinateSystem
): THREE.Vector3 {
  const x = (dxfX - coordSystem.center.x) * coordSystem.scale
  const y = (dxfZ - (coordSystem.center.z || 0)) * coordSystem.scale  // DXF Z becomes Three.js Y (up)
  const z = -(dxfY - coordSystem.center.y) * coordSystem.scale  // DXF Y becomes -Z (depth)
  return new THREE.Vector3(x, y, z)
}

/**
 * Convert Three.js world coordinates to DXF coordinates
 * Uses the coordinate system from a DXF conversion result
 */
export function worldToDxfCoordinates(
  worldX: number,
  worldY: number,
  worldZ: number,
  coordSystem: DxfCoordinateSystem
): DxfPoint {
  return {
    x: (worldX / coordSystem.scale) + coordSystem.center.x,
    y: (-worldZ / coordSystem.scale) + coordSystem.center.y,
    z: (worldY / coordSystem.scale) + (coordSystem.center.z || 0),
  }
}
