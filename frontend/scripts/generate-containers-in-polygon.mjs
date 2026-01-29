#!/usr/bin/env node
/**
 * Generate containers within a specified polygon area
 * Matches the pattern of existing nearby containers
 *
 * Usage: node generate-containers-in-polygon.mjs
 */

import { readFileSync, writeFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const containersPath = join(__dirname, '../src/data/containers.json')

// Polygon vertices (DXF coordinates) - area to fill with containers
const polygon = [
  { x: 13030, y: 73501 },
  { x: 13033, y: 73515 },
  { x: 13052, y: 73510 },
  { x: 13049, y: 73495 },
  { x: 13030, y: 73501 }
]

// Container pattern (matching nearby containers)
const CONTAINER_ROTATION = 256.1662496331838  // degrees
const CONTAINER_SPACING_X = 2.525  // spacing between containers (width direction)
const ROW_SPACING = 13.5  // spacing between rows (length direction, ~container length)
const BLOCK_NAME = '40ft'
const LAYER = 'Т-Контейнеры'

// Center point for calculating pre-centered x,y (from DXF extraction)
const CENTER = {
  x: 6714.830106,
  y: 37044.421895
}

/**
 * Ray casting algorithm to check if point is inside polygon
 */
function isPointInPolygon(x, y, poly) {
  let inside = false
  const n = poly.length

  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = poly[i].x
    const yi = poly[i].y
    const xj = poly[j].x
    const yj = poly[j].y

    if (((yi > y) !== (yj > y)) &&
        (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
      inside = !inside
    }
  }

  return inside
}

/**
 * Get bounding box of polygon
 */
function getBoundingBox(poly) {
  const xs = poly.map(p => p.x)
  const ys = poly.map(p => p.y)
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys)
  }
}

/**
 * Convert DXF coordinates to pre-centered coordinates
 */
function dxfToPreCentered(dxfX, dxfY) {
  return {
    x: dxfX - CENTER.x,
    y: dxfY - CENTER.y
  }
}

// Read existing containers
console.log('Reading containers from:', containersPath)
const containers = JSON.parse(readFileSync(containersPath, 'utf-8'))
console.log(`Existing containers: ${containers.length}`)

// Get next ID
let nextId = Math.max(...containers.map(c => c.id)) + 1

// Calculate generation parameters based on polygon orientation
// The polygon is a parallelogram - we'll generate along its natural axes
const bbox = getBoundingBox(polygon)
console.log(`Bounding box: x[${bbox.minX}, ${bbox.maxX}] y[${bbox.minY}, ${bbox.maxY}]`)

// Generate containers in a grid pattern
const newContainers = []

// Direction vector along the polygon (roughly the row direction)
// From bottom-left to bottom-right edge
const rowDirX = (polygon[3].x - polygon[0].x) / Math.hypot(polygon[3].x - polygon[0].x, polygon[3].y - polygon[0].y)
const rowDirY = (polygon[3].y - polygon[0].y) / Math.hypot(polygon[3].x - polygon[0].x, polygon[3].y - polygon[0].y)

// Perpendicular direction (column direction)
const colDirX = -rowDirY
const colDirY = rowDirX

console.log(`Row direction: (${rowDirX.toFixed(3)}, ${rowDirY.toFixed(3)})`)
console.log(`Col direction: (${colDirX.toFixed(3)}, ${colDirY.toFixed(3)})`)

// Start from a corner and generate grid
const startX = polygon[0].x
const startY = polygon[0].y

// Calculate how many rows/cols we need
const polygonWidth = Math.hypot(polygon[3].x - polygon[0].x, polygon[3].y - polygon[0].y)
const polygonHeight = Math.hypot(polygon[1].x - polygon[0].x, polygon[1].y - polygon[0].y)

const numCols = Math.floor(polygonWidth / CONTAINER_SPACING_X)
const numRows = Math.floor(polygonHeight / ROW_SPACING)

console.log(`Grid size: ${numRows} rows x ${numCols} cols`)

for (let row = 0; row <= numRows; row++) {
  for (let col = 0; col <= numCols; col++) {
    // Calculate position along parallelogram axes
    const dxfX = startX + col * CONTAINER_SPACING_X * rowDirX + row * ROW_SPACING * colDirX
    const dxfY = startY + col * CONTAINER_SPACING_X * rowDirY + row * ROW_SPACING * colDirY

    // Check if inside polygon
    if (!isPointInPolygon(dxfX, dxfY, polygon)) continue

    // Convert to pre-centered coordinates
    const preCentered = dxfToPreCentered(dxfX, dxfY)

    const container = {
      id: nextId++,
      x: preCentered.x,
      y: preCentered.y,
      rotation: CONTAINER_ROTATION,
      blockName: BLOCK_NAME,
      layer: LAYER,
      _original: {
        x: dxfX,
        y: dxfY
      }
    }

    newContainers.push(container)
  }
}

console.log(`\nGenerated ${newContainers.length} new containers:`)
newContainers.forEach(c => {
  console.log(`  ID ${c.id}: (${c._original.x.toFixed(2)}, ${c._original.y.toFixed(2)})`)
})

// Merge and save
const allContainers = [...containers, ...newContainers]
console.log(`\nTotal containers: ${allContainers.length}`)

writeFileSync(containersPath, JSON.stringify(allContainers, null, 2))
console.log('Saved updated containers.json')
