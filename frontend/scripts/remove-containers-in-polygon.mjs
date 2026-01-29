#!/usr/bin/env node
/**
 * Remove containers that fall within a specified polygon area
 *
 * Usage: node remove-containers-in-polygon.mjs
 */

import { readFileSync, writeFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const containersPath = join(__dirname, '../src/data/containers.json')

// Polygon vertices (DXF coordinates) - captured by user
const polygon = [
  { x: 13079, y: 73547 },
  { x: 13041, y: 73555 },
  { x: 13034, y: 73529 },
  { x: 13072, y: 73522 },
  { x: 13079, y: 73547 }
]

/**
 * Ray casting algorithm to check if point is inside polygon
 * @param {number} x - Point X coordinate
 * @param {number} y - Point Y coordinate
 * @param {Array<{x: number, y: number}>} polygon - Polygon vertices
 * @returns {boolean} True if point is inside polygon
 */
function isPointInPolygon(x, y, polygon) {
  let inside = false
  const n = polygon.length

  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = polygon[i].x
    const yi = polygon[i].y
    const xj = polygon[j].x
    const yj = polygon[j].y

    // Check if ray from point crosses this edge
    if (((yi > y) !== (yj > y)) &&
        (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
      inside = !inside
    }
  }

  return inside
}

// Read containers
console.log('Reading containers from:', containersPath)
const containers = JSON.parse(readFileSync(containersPath, 'utf-8'))
console.log(`Total containers: ${containers.length}`)

// Find containers inside the polygon
const containersInPolygon = containers.filter(c => {
  if (!c._original) return false
  return isPointInPolygon(c._original.x, c._original.y, polygon)
})

console.log(`\nContainers inside polygon: ${containersInPolygon.length}`)
console.log('\nRemoving containers with IDs:')
containersInPolygon.forEach(c => {
  console.log(`  ID ${c.id}: (${c._original.x.toFixed(2)}, ${c._original.y.toFixed(2)})`)
})

// Filter out containers in polygon
const filteredContainers = containers.filter(c => {
  if (!c._original) return true
  return !isPointInPolygon(c._original.x, c._original.y, polygon)
})

// Re-assign IDs to keep them sequential
const reindexedContainers = filteredContainers.map((c, index) => ({
  ...c,
  id: index + 1
}))

console.log(`\nContainers after removal: ${reindexedContainers.length}`)

// Write back
writeFileSync(containersPath, JSON.stringify(reindexedContainers, null, 2))
console.log('\nSaved updated containers.json')
