/**
 * Extract Sidewalks from yard.json
 *
 * Filters LWPOLYLINE entities from the "Т-тротуары" layer
 * and outputs sidewalk path data for 3D rendering.
 *
 * Usage: node scripts/extractSidewalks.js
 * Output: src/data/sidewalks.json
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Configuration
const SIDEWALK_LAYER = 'Т-тротуары'
const YARD_MIN_X = 12000  // Filter out legend entries
const YARD_MIN_Y = 70000
const VERTEX_TOLERANCE = 0.5 // meters - for detecting closed polylines

/**
 * Check if entity is in the main yard area (not legend)
 */
function isInYard(entity) {
  const v = entity.vertices?.[0]
  if (!v) return false
  return v.x > YARD_MIN_X && v.y > YARD_MIN_Y
}

/**
 * Check if a polyline is closed
 */
function isClosed(vertices) {
  if (!vertices || vertices.length < 3) return false
  const first = vertices[0]
  const last = vertices[vertices.length - 1]
  const dist = Math.sqrt(
    Math.pow(first.x - last.x, 2) + Math.pow(first.y - last.y, 2)
  )
  return dist < VERTEX_TOLERANCE
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
 * Calculate polygon area using Shoelace formula
 */
function calculateArea(vertices) {
  let area = 0
  const n = vertices.length

  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n
    area += vertices[i].x * vertices[j].y
    area -= vertices[j].x * vertices[i].y
  }

  return Math.abs(area / 2)
}

/**
 * Calculate centroid
 */
function calculateCentroid(vertices) {
  let sumX = 0
  let sumY = 0
  const n = vertices.length

  for (const v of vertices) {
    sumX += v.x
    sumY += v.y
  }

  return { x: sumX / n, y: sumY / n }
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
function extractSidewalks() {
  console.log('🚶 Extracting sidewalks from yard.json...\n')

  // Load yard data
  const yardPath = path.join(__dirname, '../public/yard.json')
  const yardData = JSON.parse(fs.readFileSync(yardPath, 'utf8'))

  console.log(`Total entities in DXF: ${yardData.entities.length}`)

  // Filter entities on sidewalk layer
  const sidewalkEntities = yardData.entities.filter(
    (e) => e.layer === SIDEWALK_LAYER
  )
  console.log(`Entities on "${SIDEWALK_LAYER}" layer: ${sidewalkEntities.length}`)

  // Filter to yard area only (exclude legend)
  const yardEntities = sidewalkEntities.filter(isInYard)
  console.log(`Entities in yard area: ${yardEntities.length}`)

  // Process each sidewalk
  const sidewalks = yardEntities.map((entity, index) => {
    const vertices = entity.vertices.map((v) => ({ x: v.x, y: v.y }))
    const closed = isClosed(vertices)
    const length = calculateLength(vertices)
    const centroid = calculateCentroid(vertices)
    const bounds = calculateBounds(vertices)
    const area = closed ? calculateArea(vertices) : 0

    return {
      id: index + 1,
      handle: entity.handle,
      type: closed ? 'polygon' : 'path',
      vertices,
      centroid,
      bounds,
      length,
      area,
      closed,
    }
  })

  // Calculate overall stats
  const allVertices = sidewalks.flatMap((s) => s.vertices)
  const overallBounds = calculateBounds(allVertices)
  const totalLength = sidewalks.reduce((sum, s) => sum + s.length, 0)
  const totalArea = sidewalks.reduce((sum, s) => sum + s.area, 0)

  console.log('\n📊 Sidewalk Statistics:')
  console.log(`   Total sidewalks: ${sidewalks.length}`)
  console.log(`   Closed polygons: ${sidewalks.filter((s) => s.closed).length}`)
  console.log(`   Open paths: ${sidewalks.filter((s) => !s.closed).length}`)
  console.log(`   Total length: ${totalLength.toFixed(2)} m`)
  console.log(`   Total area (closed): ${totalArea.toFixed(2)} m²`)
  console.log(`   X range: ${overallBounds.minX.toFixed(2)} - ${overallBounds.maxX.toFixed(2)}`)
  console.log(`   Y range: ${overallBounds.minY.toFixed(2)} - ${overallBounds.maxY.toFixed(2)}`)

  // Show sidewalks
  console.log('\n🚶 Sidewalks:')
  sidewalks.forEach((s, i) => {
    console.log(`   ${i + 1}. ID ${s.id}: ${s.type}, ${s.vertices.length} vertices, ${s.length.toFixed(2)} m`)
  })

  // Create output data
  const output = {
    meta: {
      source: 'yard.json',
      layer: SIDEWALK_LAYER,
      extractedAt: new Date().toISOString(),
      count: sidewalks.length,
      totalLength,
      totalArea,
    },
    bounds: overallBounds,
    sidewalks,
  }

  // Write output
  const outputPath = path.join(__dirname, '../src/data/sidewalks.json')

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
extractSidewalks()
