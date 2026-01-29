#!/usr/bin/env node
/**
 * Add Semantic IDs to Infrastructure Data Files
 *
 * Generates semantic IDs for all infrastructure objects (roads, fences, railway, etc.)
 * following the pattern: {TYPE}-SEG-{GRID}{SUFFIX}
 *
 * Usage: node scripts/add-infrastructure-ids.mjs
 */

import { readFileSync, writeFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const dataDir = join(__dirname, '../src/data')

// Grid configuration (matches yardElements.json terminal area)
const GRID_CONFIG = {
  cellSize: 20,
  bounds: {
    minX: 12900,
    maxX: 13140,
    minY: 73180,
    maxY: 73680,
  },
}

/**
 * Convert DXF coordinates to grid cell label (A1, B2, etc.)
 */
function dxfToGridCell(dxfX, dxfY) {
  const { cellSize, bounds } = GRID_CONFIG

  // Column: left to right (A, B, C...)
  const col = Math.floor((dxfX - bounds.minX) / cellSize)
  // Row: top to bottom (1, 2, 3...) - Y decreases going down
  const row = Math.floor((bounds.maxY - dxfY) / cellSize)

  // Clamp to valid range (allow negative for outside bounds)
  const clampedCol = Math.max(0, Math.min(col, 25)) // A-Z
  const clampedRow = Math.max(0, row)

  const colLetter = String.fromCharCode(65 + clampedCol)
  return `${colLetter}${clampedRow + 1}`
}

/**
 * Calculate center point for different element types
 */
function calculateCenter(element, type) {
  switch (type) {
    case 'road':
    case 'fence':
    case 'railway': {
      // For line segments, use the midpoint of all points
      const points = element.points || element.vertices || []
      if (points.length === 0) return { x: 0, y: 0 }

      const sumX = points.reduce((sum, p) => sum + p.x, 0)
      const sumY = points.reduce((sum, p) => sum + p.y, 0)
      return { x: sumX / points.length, y: sumY / points.length }
    }

    case 'platform': {
      // Use centroid if available, otherwise calculate from vertices
      if (element.centroid) return element.centroid

      const vertices = element.vertices || []
      if (vertices.length === 0) return { x: 0, y: 0 }

      const sumX = vertices.reduce((sum, p) => sum + p.x, 0)
      const sumY = vertices.reduce((sum, p) => sum + p.y, 0)
      return { x: sumX / vertices.length, y: sumY / vertices.length }
    }

    case 'sidewalk': {
      // Use centroid if available
      if (element.centroid) return element.centroid

      const vertices = element.vertices || []
      if (vertices.length === 0) return { x: 0, y: 0 }

      const sumX = vertices.reduce((sum, p) => sum + p.x, 0)
      const sumY = vertices.reduce((sum, p) => sum + p.y, 0)
      return { x: sumX / vertices.length, y: sumY / vertices.length }
    }

    default:
      return { x: 0, y: 0 }
  }
}

/**
 * Generate semantic ID with duplicate handling
 */
function generateSemanticId(prefix, grid, usedIds) {
  let baseId = `${prefix}-${grid}`

  if (!usedIds.has(baseId)) {
    usedIds.add(baseId)
    return baseId
  }

  // Add suffix for duplicates: -A, -B, -C, etc.
  let suffix = 'A'
  while (usedIds.has(`${baseId}-${suffix}`)) {
    suffix = String.fromCharCode(suffix.charCodeAt(0) + 1)
  }

  const finalId = `${baseId}-${suffix}`
  usedIds.add(finalId)
  return finalId
}

/**
 * Process roads.json
 */
function processRoads() {
  const filePath = join(dataDir, 'roads.json')
  const data = JSON.parse(readFileSync(filePath, 'utf-8'))
  const usedIds = new Set()

  for (const segment of data.segments) {
    const center = calculateCenter(segment, 'road')
    const grid = dxfToGridCell(center.x, center.y)
    segment.semanticId = generateSemanticId('ROAD-SEG', grid, usedIds)
  }

  // Update meta
  data.meta.semanticIdsAdded = new Date().toISOString()

  writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n')
  console.log(`✓ roads.json: Added ${data.segments.length} semantic IDs`)
}

/**
 * Process fences.json - splits by layer:
 * - "(040) Ограда" → FENCE-SEG-*
 * - "Т-ограждение" → WALL-SEG-*
 */
function processFences() {
  const filePath = join(dataDir, 'fences.json')
  const data = JSON.parse(readFileSync(filePath, 'utf-8'))
  const usedFenceIds = new Set()
  const usedWallIds = new Set()

  let fenceCount = 0
  let wallCount = 0

  for (const segment of data.segments) {
    const center = calculateCenter(segment, 'fence')
    const grid = dxfToGridCell(center.x, center.y)

    // Split by layer: Т-ограждение = wall, (040) Ограда = fence
    if (segment.layer === 'Т-ограждение') {
      segment.semanticId = generateSemanticId('WALL-SEG', grid, usedWallIds)
      wallCount++
    } else {
      segment.semanticId = generateSemanticId('FENCE-SEG', grid, usedFenceIds)
      fenceCount++
    }
  }

  data.meta.semanticIdsAdded = new Date().toISOString()

  writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n')
  console.log(`✓ fences.json: Added ${fenceCount} FENCE-SEG + ${wallCount} WALL-SEG IDs (${data.segments.length} total)`)
}

/**
 * Process railway.json
 */
function processRailway() {
  const filePath = join(dataDir, 'railway.json')
  const data = JSON.parse(readFileSync(filePath, 'utf-8'))
  const usedIds = new Set()

  for (const track of data.tracks) {
    const center = calculateCenter(track, 'railway')
    const grid = dxfToGridCell(center.x, center.y)
    track.semanticId = generateSemanticId('RAIL-TRK', grid, usedIds)
  }

  data.meta.semanticIdsAdded = new Date().toISOString()

  writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n')
  console.log(`✓ railway.json: Added ${data.tracks.length} semantic IDs`)
}

/**
 * Process storagePlatforms.json
 */
function processStoragePlatforms() {
  const filePath = join(dataDir, 'storagePlatforms.json')
  const data = JSON.parse(readFileSync(filePath, 'utf-8'))
  const usedIds = new Set()

  for (const platform of data.platforms) {
    const center = calculateCenter(platform, 'platform')
    const grid = dxfToGridCell(center.x, center.y)
    platform.semanticId = generateSemanticId('PLAT', grid, usedIds)
  }

  data.meta.semanticIdsAdded = new Date().toISOString()

  writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n')
  console.log(`✓ storagePlatforms.json: Added ${data.platforms.length} semantic IDs`)
}

/**
 * Process sidewalks.json
 */
function processSidewalks() {
  const filePath = join(dataDir, 'sidewalks.json')
  const data = JSON.parse(readFileSync(filePath, 'utf-8'))
  const usedIds = new Set()

  for (const sidewalk of data.sidewalks) {
    const center = calculateCenter(sidewalk, 'sidewalk')
    const grid = dxfToGridCell(center.x, center.y)
    sidewalk.semanticId = generateSemanticId('SWLK', grid, usedIds)
  }

  data.meta.semanticIdsAdded = new Date().toISOString()

  writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n')
  console.log(`✓ sidewalks.json: Added ${data.sidewalks.length} semantic IDs`)
}

/**
 * Main entry point
 */
function main() {
  console.log('\n🏗️  Adding semantic IDs to infrastructure data files...\n')
  console.log(`Grid config: cellSize=${GRID_CONFIG.cellSize}m, bounds=(${GRID_CONFIG.bounds.minX}-${GRID_CONFIG.bounds.maxX}, ${GRID_CONFIG.bounds.minY}-${GRID_CONFIG.bounds.maxY})\n`)

  try {
    processRoads()
    processFences()
    processRailway()
    processStoragePlatforms()
    processSidewalks()

    console.log('\n✅ All infrastructure files updated with semantic IDs!')
    console.log('\nID formats:')
    console.log('  - Roads: ROAD-SEG-{grid}[-suffix]')
    console.log('  - Fences: FENCE-SEG-{grid}[-suffix]  (layer: (040) Ограда)')
    console.log('  - Walls: WALL-SEG-{grid}[-suffix]   (layer: Т-ограждение)')
    console.log('  - Railway: RAIL-TRK-{grid}[-suffix]')
    console.log('  - Platforms: PLAT-{grid}[-suffix]')
    console.log('  - Sidewalks: SWLK-{grid}[-suffix]')
    console.log('\nExample: ROAD-SEG-G12, FENCE-SEG-A3-B, WALL-SEG-C5\n')
  } catch (error) {
    console.error('❌ Error processing files:', error.message)
    process.exit(1)
  }
}

main()
