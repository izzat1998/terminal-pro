/**
 * Extract Warehouse Footprints from yard.json
 *
 * Filters closed LWPOLYLINE entities from the "Т-склад" layer
 * and outputs warehouse footprint data for 3D rendering.
 *
 * Usage: node scripts/extractWarehouses.js
 * Output: src/data/warehouses.json
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Configuration
const WAREHOUSE_LAYER = 'Т-склад'
const VERTEX_TOLERANCE = 0.01
const MIN_VERTICES = 3

function isClosed(entity) {
  // DXF shape property indicates implicit closure
  if (entity.shape === true) return true

  // Or check if vertices explicitly close
  const vertices = entity.vertices
  if (!vertices || vertices.length < MIN_VERTICES) return false
  const first = vertices[0]
  const last = vertices[vertices.length - 1]
  return (
    Math.abs(first.x - last.x) < VERTEX_TOLERANCE &&
    Math.abs(first.y - last.y) < VERTEX_TOLERANCE
  )
}

function calculateCentroid(vertices) {
  let sumX = 0, sumY = 0
  for (const v of vertices) {
    sumX += v.x
    sumY += v.y
  }
  return { x: sumX / vertices.length, y: sumY / vertices.length }
}

function calculateBounds(vertices) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
  for (const v of vertices) {
    if (v.x < minX) minX = v.x
    if (v.x > maxX) maxX = v.x
    if (v.y < minY) minY = v.y
    if (v.y > maxY) maxY = v.y
  }
  return { minX, maxX, minY, maxY }
}

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

function extractWarehouses() {
  console.log('🏭 Extracting warehouse footprints from yard.json...\n')

  const yardPath = path.join(__dirname, '../public/yard.json')
  const yardData = JSON.parse(fs.readFileSync(yardPath, 'utf8'))

  const warehouseEntities = yardData.entities.filter(e => e.layer === WAREHOUSE_LAYER)
  console.log(`Entities on "${WAREHOUSE_LAYER}" layer: ${warehouseEntities.length}`)

  const lwpolylines = warehouseEntities.filter(e => e.type === 'LWPOLYLINE')
  const closedPolylines = lwpolylines.filter(e => isClosed(e))
  console.log(`Closed polylines (warehouse footprints): ${closedPolylines.length}\n`)

  // Filter out entities from legend/title block area (outside main yard)
  // Main yard is roughly X: 12800-13200, Y: 73100-73800
  const yardPolylines = closedPolylines.filter(e => {
    const v = e.vertices[0]
    return v && v.x > 12000 && v.y > 70000
  })
  console.log(`Warehouses in main yard area: ${yardPolylines.length}\n`)

  const warehouses = yardPolylines.map((entity, index) => {
    const vertices = entity.vertices.map(v => ({ x: v.x, y: v.y }))
    return {
      id: index + 1,
      handle: entity.handle,
      vertices,
      centroid: calculateCentroid(vertices),
      bounds: calculateBounds(vertices),
      area: calculateArea(vertices),
      elevation: entity.elevation ?? 0,
      label: `Склад ${index + 1}`,
    }
  })

  warehouses.sort((a, b) => b.area - a.area)

  const allVertices = warehouses.flatMap(w => w.vertices)
  const overallBounds = calculateBounds(allVertices)

  console.log('📊 Warehouse Statistics:')
  console.log(`   Total warehouses: ${warehouses.length}`)
  console.log(`   Total area: ${warehouses.reduce((s, w) => s + w.area, 0).toFixed(2)} m²`)

  warehouses.forEach((w, i) => {
    console.log(`   ${i + 1}. ${w.label}: ${w.area.toFixed(2)} m²`)
  })

  const output = {
    meta: {
      source: 'yard.json',
      layer: WAREHOUSE_LAYER,
      extractedAt: new Date().toISOString(),
      count: warehouses.length,
    },
    bounds: overallBounds,
    warehouses,
  }

  const outputPath = path.join(__dirname, '../src/data/warehouses.json')
  const outputDir = path.dirname(outputPath)
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true })
  }

  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2))
  console.log(`\n✅ Saved to ${outputPath}`)

  return output
}

extractWarehouses()
