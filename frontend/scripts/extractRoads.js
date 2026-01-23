/**
 * Extract Roads from yard.json
 *
 * Filters LINE, ARC, and LWPOLYLINE entities from the "Т-Дороги" layer
 * and outputs road path data for 3D rendering with curbs.
 *
 * Usage: node scripts/extractRoads.js
 * Output: src/data/roads.json
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Configuration
const ROAD_LAYER = 'Т-Дороги'
const YARD_MIN_X = 12000  // Filter out legend entries
const YARD_MIN_Y = 70000
const ARC_SEGMENTS = 16   // Number of segments to approximate arcs

/**
 * Check if entity is in the main yard area (not legend)
 */
function isInYard(entity) {
  if (entity.vertices && entity.vertices.length > 0) {
    return entity.vertices[0].x > YARD_MIN_X && entity.vertices[0].y > YARD_MIN_Y
  }
  if (entity.center) {
    return entity.center.x > YARD_MIN_X && entity.center.y > YARD_MIN_Y
  }
  return false
}

/**
 * Convert arc to polyline points
 */
function arcToPoints(arc) {
  const points = []
  const { center, radius, startAngle, endAngle } = arc

  // Handle angle wrapping
  let start = startAngle
  let end = endAngle
  if (end < start) {
    end += Math.PI * 2
  }

  const angleStep = (end - start) / ARC_SEGMENTS

  for (let i = 0; i <= ARC_SEGMENTS; i++) {
    const angle = start + i * angleStep
    points.push({
      x: center.x + radius * Math.cos(angle),
      y: center.y + radius * Math.sin(angle),
    })
  }

  return points
}

/**
 * Calculate total length of a path
 */
function calculateLength(points) {
  let length = 0
  for (let i = 1; i < points.length; i++) {
    const dx = points[i].x - points[i - 1].x
    const dy = points[i].y - points[i - 1].y
    length += Math.sqrt(dx * dx + dy * dy)
  }
  return length
}

/**
 * Calculate bounding box
 */
function calculateBounds(points) {
  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity

  for (const p of points) {
    if (p.x < minX) minX = p.x
    if (p.x > maxX) maxX = p.x
    if (p.y < minY) minY = p.y
    if (p.y > maxY) maxY = p.y
  }

  return { minX, maxX, minY, maxY }
}

/**
 * Main extraction function
 */
function extractRoads() {
  console.log('🛣️ Extracting roads from yard.json...\n')

  // Load yard data
  const yardPath = path.join(__dirname, '../public/yard.json')
  const yardData = JSON.parse(fs.readFileSync(yardPath, 'utf8'))

  console.log(`Total entities in DXF: ${yardData.entities.length}`)

  // Filter entities on road layer
  const roadEntities = yardData.entities.filter(
    (e) => e.layer === ROAD_LAYER
  )
  console.log(`Entities on "${ROAD_LAYER}" layer: ${roadEntities.length}`)

  // Filter to yard area only (exclude legend)
  const yardEntities = roadEntities.filter(isInYard)
  console.log(`Entities in yard area: ${yardEntities.length}`)

  // Count by type
  const typeCounts = {}
  yardEntities.forEach((e) => {
    typeCounts[e.type] = (typeCounts[e.type] || 0) + 1
  })
  console.log(`Entity types: ${JSON.stringify(typeCounts)}`)

  // Process each road segment
  const segments = []

  yardEntities.forEach((entity, index) => {
    let points = []
    let segmentType = 'line'

    if (entity.type === 'LINE' || entity.type === 'LWPOLYLINE') {
      points = entity.vertices.map((v) => ({ x: v.x, y: v.y }))
      segmentType = entity.type === 'LINE' ? 'line' : 'polyline'
    } else if (entity.type === 'ARC') {
      points = arcToPoints(entity)
      segmentType = 'arc'
    } else {
      return // Skip unknown types
    }

    if (points.length < 2) return

    const length = calculateLength(points)
    const bounds = calculateBounds(points)

    segments.push({
      id: index + 1,
      handle: entity.handle,
      type: segmentType,
      points,
      length,
      bounds,
      closed: entity.closed || false,
    })
  })

  // Sort by length (longest first)
  segments.sort((a, b) => b.length - a.length)

  // Reassign IDs after sorting
  segments.forEach((s, i) => {
    s.id = i + 1
  })

  // Calculate overall stats
  const allPoints = segments.flatMap((s) => s.points)
  const overallBounds = calculateBounds(allPoints)
  const totalLength = segments.reduce((sum, s) => sum + s.length, 0)

  console.log('\n📊 Road Statistics:')
  console.log(`   Total road segments: ${segments.length}`)
  console.log(`   Total road length: ${totalLength.toFixed(2)} m`)
  console.log(`   X range: ${overallBounds.minX.toFixed(2)} - ${overallBounds.maxX.toFixed(2)}`)
  console.log(`   Y range: ${overallBounds.minY.toFixed(2)} - ${overallBounds.maxY.toFixed(2)}`)

  // Show longest segments
  console.log('\n🛣️ Longest road segments:')
  segments.slice(0, 5).forEach((s, i) => {
    console.log(`   ${i + 1}. ID ${s.id}: ${s.length.toFixed(2)} m (${s.type}, ${s.points.length} points)`)
  })

  // Create output data
  const output = {
    meta: {
      source: 'yard.json',
      layer: ROAD_LAYER,
      extractedAt: new Date().toISOString(),
      count: segments.length,
      totalLength,
    },
    bounds: overallBounds,
    segments,
  }

  // Write output
  const outputPath = path.join(__dirname, '../src/data/roads.json')

  // Ensure directory exists
  const outputDir = path.dirname(outputPath)
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true })
  }

  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2))
  console.log(`\n✅ Saved to ${outputPath}`)

  return output
}

// Run extraction
extractRoads()
