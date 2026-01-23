/**
 * Extract Storage Platforms from yard.json
 *
 * Filters closed LWPOLYLINE entities from the "Т-площадка хранения" layer
 * and outputs platform footprint data for 3D rendering.
 *
 * Usage: node scripts/extractStoragePlatforms.js
 * Output: src/data/storagePlatforms.json
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Configuration
const PLATFORM_LAYER = 'Т-площадка хранения'
const YARD_MIN_X = 12000  // Filter out legend entries
const YARD_MIN_Y = 70000
const VERTEX_TOLERANCE = 0.01 // meters - for detecting closed polylines

/**
 * Check if entity is in the main yard area (not legend)
 */
function isInYard(entity) {
  const v = entity.vertices?.[0] || entity.position
  if (!v) return false
  return v.x > YARD_MIN_X && v.y > YARD_MIN_Y
}

/**
 * Check if a polyline is closed (first vertex == last vertex)
 */
function isClosed(vertices) {
  if (!vertices || vertices.length < 3) return false

  const first = vertices[0]
  const last = vertices[vertices.length - 1]

  return (
    Math.abs(first.x - last.x) < VERTEX_TOLERANCE &&
    Math.abs(first.y - last.y) < VERTEX_TOLERANCE
  )
}

/**
 * Calculate polygon centroid
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
function calculateBounds(vertices) {
  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity

  for (const v of vertices) {
    if (v.x < minX) minX = v.x
    if (v.x > maxX) maxX = v.x
    if (v.y < minY) minY = v.y
    if (v.y > maxY) maxY = v.y
  }

  return { minX, maxX, minY, maxY }
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
 * Main extraction function
 */
function extractStoragePlatforms() {
  console.log('📦 Extracting storage platforms from yard.json...\n')

  // Load yard data
  const yardPath = path.join(__dirname, '../public/yard.json')
  const yardData = JSON.parse(fs.readFileSync(yardPath, 'utf8'))

  console.log(`Total entities in DXF: ${yardData.entities.length}`)

  // Filter entities on platform layer
  const platformEntities = yardData.entities.filter(
    (e) => e.layer === PLATFORM_LAYER
  )
  console.log(`Entities on "${PLATFORM_LAYER}" layer: ${platformEntities.length}`)

  // Filter to yard area only (exclude legend)
  const yardEntities = platformEntities.filter(isInYard)
  console.log(`Entities in yard area: ${yardEntities.length}`)

  // Get LWPOLYLINE entities (treat open polylines as area boundaries)
  // Note: These may be open polylines that outline storage areas
  const polylines = yardEntities.filter(
    (e) => e.type === 'LWPOLYLINE' && e.vertices && e.vertices.length >= 3
  )
  console.log(`Platform polylines: ${polylines.length}\n`)

  // Process each platform
  const platforms = polylines.map((entity, index) => {
    const vertices = entity.vertices.map((v) => ({ x: v.x, y: v.y }))
    const centroid = calculateCentroid(vertices)
    const bounds = calculateBounds(vertices)
    const area = calculateArea(vertices)

    return {
      id: index + 1,
      handle: entity.handle,
      vertices,
      centroid,
      bounds,
      area,
      elevation: entity.elevation ?? 0,
    }
  })

  // Sort by area (largest first)
  platforms.sort((a, b) => b.area - a.area)

  // Calculate overall stats
  const allVertices = platforms.flatMap((p) => p.vertices)
  const overallBounds = calculateBounds(allVertices)
  const totalArea = platforms.reduce((sum, p) => sum + p.area, 0)

  console.log('📊 Storage Platform Statistics:')
  console.log(`   Total platforms: ${platforms.length}`)
  console.log(`   Total footprint area: ${totalArea.toFixed(2)} m²`)
  console.log(`   X range: ${overallBounds.minX.toFixed(2)} - ${overallBounds.maxX.toFixed(2)}`)
  console.log(`   Y range: ${overallBounds.minY.toFixed(2)} - ${overallBounds.maxY.toFixed(2)}`)

  // Show platforms
  console.log('\n📦 Platforms by area:')
  platforms.forEach((p, i) => {
    console.log(`   ${i + 1}. ID ${p.id}: ${p.area.toFixed(2)} m² (${p.vertices.length} vertices)`)
  })

  // Create output data
  const output = {
    meta: {
      source: 'yard.json',
      layer: PLATFORM_LAYER,
      extractedAt: new Date().toISOString(),
      count: platforms.length,
      totalArea,
    },
    bounds: overallBounds,
    platforms,
  }

  // Write output
  const outputPath = path.join(__dirname, '../src/data/storagePlatforms.json')

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
extractStoragePlatforms()
