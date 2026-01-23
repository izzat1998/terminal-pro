/**
 * Extract Building Footprints from yard.json
 *
 * Filters closed LWPOLYLINE entities from the "(007) Здания" layer
 * and outputs building footprint data for 3D rendering.
 *
 * Usage: node scripts/extractBuildings.js
 * Output: src/data/buildings.json
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Configuration
const BUILDING_LAYER = '(007) Здания'
const VERTEX_TOLERANCE = 0.01 // meters - for detecting closed polylines
const MIN_VERTICES = 3 // Minimum vertices for a valid polygon

/**
 * Check if a polyline is closed (first vertex == last vertex)
 */
function isClosed(vertices) {
  if (!vertices || vertices.length < MIN_VERTICES) return false

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
function extractBuildings() {
  console.log('🏢 Extracting building footprints from yard.json...\n')

  // Load yard data
  const yardPath = path.join(__dirname, '../public/yard.json')
  const yardData = JSON.parse(fs.readFileSync(yardPath, 'utf8'))

  console.log(`Total entities in DXF: ${yardData.entities.length}`)

  // Filter entities on building layer
  const buildingEntities = yardData.entities.filter(
    (e) => e.layer === BUILDING_LAYER
  )
  console.log(`Entities on "${BUILDING_LAYER}" layer: ${buildingEntities.length}`)

  // Get LWPOLYLINE entities
  const lwpolylines = buildingEntities.filter((e) => e.type === 'LWPOLYLINE')
  console.log(`LWPOLYLINE entities: ${lwpolylines.length}`)

  // Filter to closed polylines only (building footprints)
  const closedPolylines = lwpolylines.filter((e) => isClosed(e.vertices))
  console.log(`Closed polylines (building footprints): ${closedPolylines.length}\n`)

  // Process each building
  const buildings = closedPolylines.map((entity, index) => {
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

  // Sort by area (largest first) for debugging
  buildings.sort((a, b) => b.area - a.area)

  // Calculate overall stats
  const allVertices = buildings.flatMap((b) => b.vertices)
  const overallBounds = calculateBounds(allVertices)
  const totalArea = buildings.reduce((sum, b) => sum + b.area, 0)

  console.log('📊 Building Statistics:')
  console.log(`   Total buildings: ${buildings.length}`)
  console.log(`   Total footprint area: ${totalArea.toFixed(2)} m²`)
  console.log(`   X range: ${overallBounds.minX.toFixed(2)} - ${overallBounds.maxX.toFixed(2)}`)
  console.log(`   Y range: ${overallBounds.minY.toFixed(2)} - ${overallBounds.maxY.toFixed(2)}`)

  // Show largest buildings
  console.log('\n🏗️ Largest buildings by area:')
  buildings.slice(0, 5).forEach((b, i) => {
    console.log(`   ${i + 1}. ID ${b.id}: ${b.area.toFixed(2)} m² (${b.vertices.length} vertices)`)
  })

  // Create output data
  const output = {
    meta: {
      source: 'yard.json',
      layer: BUILDING_LAYER,
      extractedAt: new Date().toISOString(),
      count: buildings.length,
    },
    bounds: overallBounds,
    buildings,
  }

  // Write output
  const outputPath = path.join(__dirname, '../src/data/buildings.json')

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
extractBuildings()
