/**
 * Extract Railway Tracks from yard.json
 *
 * Filters LINE/LWPOLYLINE entities from the "(023) Ж_дорога" layer
 * and outputs railway path data for 3D rendering with parallel rails and sleepers.
 *
 * Usage: node scripts/extractRailway.js
 * Output: src/data/railway.json
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Configuration
const RAILWAY_LAYER = '(023) Ж_дорога'
const YARD_MIN_X = 12000  // Filter out legend entries
const YARD_MIN_Y = 70000

/**
 * Check if entity is in the main yard area (not legend)
 */
function isInYard(entity) {
  const v = entity.vertices?.[0] || entity.position
  if (!v) return false
  return v.x > YARD_MIN_X && v.y > YARD_MIN_Y
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
function extractRailway() {
  console.log('🚂 Extracting railway tracks from yard.json...\n')

  // Load yard data
  const yardPath = path.join(__dirname, '../public/yard.json')
  const yardData = JSON.parse(fs.readFileSync(yardPath, 'utf8'))

  console.log(`Total entities in DXF: ${yardData.entities.length}`)

  // Filter entities on railway layer
  const railwayEntities = yardData.entities.filter(
    (e) => e.layer === RAILWAY_LAYER
  )
  console.log(`Entities on "${RAILWAY_LAYER}" layer: ${railwayEntities.length}`)

  // Filter to yard area only (exclude legend)
  const yardEntities = railwayEntities.filter(isInYard)
  console.log(`Entities in yard area: ${yardEntities.length}`)

  // Process each rail segment
  const tracks = yardEntities.map((entity, index) => {
    const points = entity.vertices.map((v) => ({ x: v.x, y: v.y }))
    const length = calculateLength(points)
    const bounds = calculateBounds(points)

    return {
      id: index + 1,
      handle: entity.handle,
      type: entity.type.toLowerCase(),
      points,
      length,
      bounds,
    }
  })

  // Sort by length (longest first)
  tracks.sort((a, b) => b.length - a.length)

  // Calculate overall stats
  const allPoints = tracks.flatMap((t) => t.points)
  const overallBounds = calculateBounds(allPoints)
  const totalLength = tracks.reduce((sum, t) => sum + t.length, 0)

  console.log('\n📊 Railway Statistics:')
  console.log(`   Total track segments: ${tracks.length}`)
  console.log(`   Total track length: ${totalLength.toFixed(2)} m`)
  console.log(`   X range: ${overallBounds.minX.toFixed(2)} - ${overallBounds.maxX.toFixed(2)}`)
  console.log(`   Y range: ${overallBounds.minY.toFixed(2)} - ${overallBounds.maxY.toFixed(2)}`)

  // Show longest tracks
  console.log('\n🛤️ Longest track segments:')
  tracks.slice(0, 5).forEach((t, i) => {
    console.log(`   ${i + 1}. ID ${t.id}: ${t.length.toFixed(2)} m (${t.points.length} points)`)
  })

  // Create output data
  const output = {
    meta: {
      source: 'yard.json',
      layer: RAILWAY_LAYER,
      extractedAt: new Date().toISOString(),
      count: tracks.length,
      totalLength,
    },
    bounds: overallBounds,
    tracks,
  }

  // Write output
  const outputPath = path.join(__dirname, '../src/data/railway.json')

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
extractRailway()
