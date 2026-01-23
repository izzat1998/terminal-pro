#!/usr/bin/env node
/**
 * DXF to JSON Converter
 * Converts DXF files to JSON format for use in web applications
 *
 * Usage: node scripts/dxf-to-json.js <input.dxf> [output.json]
 */

import DxfParser from 'dxf-parser'
import fs from 'fs'
import path from 'path'

// Get command line arguments
const args = process.argv.slice(2)

if (args.length === 0) {
  console.log('Usage: node scripts/dxf-to-json.js <input.dxf> [output.json]')
  console.log('')
  console.log('Examples:')
  console.log('  node scripts/dxf-to-json.js public/yard.dxf')
  console.log('  node scripts/dxf-to-json.js public/yard.dxf public/yard.json')
  process.exit(1)
}

const inputFile = args[0]
const outputFile = args[1] || inputFile.replace(/\.dxf$/i, '.json')

// Verify input file exists
if (!fs.existsSync(inputFile)) {
  console.error(`Error: Input file not found: ${inputFile}`)
  process.exit(1)
}

console.log(`Converting: ${inputFile} → ${outputFile}`)

// Read and parse DXF
const content = fs.readFileSync(inputFile, 'utf8')
const parser = new DxfParser()

let dxf
try {
  dxf = parser.parse(content)
} catch (err) {
  console.error('Error parsing DXF:', err.message)
  process.exit(1)
}

// Calculate bounds from entities (for stats - may include distant block geometry)
function calculateBounds(entities) {
  let minX = Infinity, minY = Infinity, minZ = Infinity
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity

  function updateBounds(point) {
    if (!point) return
    if (point.x !== undefined) {
      minX = Math.min(minX, point.x)
      maxX = Math.max(maxX, point.x)
    }
    if (point.y !== undefined) {
      minY = Math.min(minY, point.y)
      maxY = Math.max(maxY, point.y)
    }
    if (point.z !== undefined) {
      minZ = Math.min(minZ, point.z)
      maxZ = Math.max(maxZ, point.z)
    }
  }

  entities.forEach(entity => {
    // Handle different entity types
    if (entity.vertices) {
      entity.vertices.forEach(updateBounds)
    }
    if (entity.position) updateBounds(entity.position)
    if (entity.center) updateBounds(entity.center)
    if (entity.startPoint) updateBounds(entity.startPoint)
    if (entity.endPoint) updateBounds(entity.endPoint)
    if (entity.points) entity.points.forEach(updateBounds)
  })

  return {
    min: { x: minX, y: minY, z: minZ === Infinity ? 0 : minZ },
    max: { x: maxX, y: maxY, z: maxZ === -Infinity ? 0 : maxZ },
    width: maxX - minX,
    height: maxY - minY,
    depth: maxZ === -Infinity ? 0 : maxZ - minZ
  }
}

// DXF INSUNITS to scale factors (meters)
const DXF_UNIT_SCALES = {
  0: 1.0,       // Unitless - assume meters
  1: 0.0254,    // Inches → meters
  2: 0.3048,    // Feet → meters
  3: 1609.344,  // Miles → meters
  4: 0.001,     // Millimeters → meters
  5: 0.01,      // Centimeters → meters
  6: 1.0,       // Meters → meters
  7: 1000.0,    // Kilometers → meters
  8: 0.0000254, // Microinches → meters
  9: 0.000001,  // Mils → meters
  10: 0.9144,   // Yards → meters
  14: 0.1,      // Decimeters → meters
  15: 10.0,     // Decameters → meters
  16: 100.0,    // Hectometers → meters
}

/**
 * Build coordinate system from DXF header for Three.js compatibility
 * Uses $EXTMIN/$EXTMAX (authoritative drawing bounds) instead of calculated bounds
 */
function buildCoordinateSystem(header) {
  // Get header extents - these are the authoritative bounds set by the CAD application
  const extMin = header.$EXTMIN
  const extMax = header.$EXTMAX
  const insunits = header.$INSUNITS ?? 6 // Default to meters

  // Validate header bounds exist
  const hasValidBounds = extMin && extMax &&
    typeof extMin.x === 'number' && typeof extMin.y === 'number' &&
    typeof extMax.x === 'number' && typeof extMax.y === 'number' &&
    Number.isFinite(extMin.x) && Number.isFinite(extMin.y) &&
    Number.isFinite(extMax.x) && Number.isFinite(extMax.y)

  if (!hasValidBounds) {
    // Return null to indicate no valid coordinate system could be built
    return null
  }

  const bounds = {
    min: {
      x: extMin.x,
      y: extMin.y,
      z: extMin.z ?? 0
    },
    max: {
      x: extMax.x,
      y: extMax.y,
      z: extMax.z ?? 0
    },
    width: extMax.x - extMin.x,
    height: extMax.y - extMin.y
  }

  // Center point for origin alignment (matches Three.js converter logic)
  const center = {
    x: (bounds.min.x + bounds.max.x) / 2,
    y: (bounds.min.y + bounds.max.y) / 2,
    z: (bounds.min.z + bounds.max.z) / 2
  }

  // Get scale factor for unit conversion
  const scale = DXF_UNIT_SCALES[insunits] ?? 1.0

  return {
    center,
    scale,
    units: insunits,
    bounds
  }
}

// Count entities by type
function countEntitiesByType(entities) {
  const counts = {}
  entities.forEach(entity => {
    counts[entity.type] = (counts[entity.type] || 0) + 1
  })
  return counts
}

// Build coordinate system from header (for Three.js compatibility)
const coordinateSystem = buildCoordinateSystem(dxf.header || {})

// Build the output structure
const output = {
  // Metadata
  meta: {
    sourceFile: path.basename(inputFile),
    convertedAt: new Date().toISOString(),
    version: dxf.header?.$ACADVER || 'unknown'
  },

  // Header information
  header: dxf.header || {},

  // Coordinate system for Three.js compatibility
  // Uses header $EXTMIN/$EXTMAX (authoritative bounds) instead of calculated bounds
  coordinateSystem: coordinateSystem,

  // Statistics (note: bounds here may include distant block geometry)
  stats: {
    entityCount: {
      total: dxf.entities?.length || 0,
      byType: countEntitiesByType(dxf.entities || [])
    },
    bounds: calculateBounds(dxf.entities || []),
    layerCount: Object.keys(dxf.tables?.layer?.layers || {}).length,
    blockCount: Object.keys(dxf.blocks || {}).length
  },

  // Layer definitions
  layers: Object.entries(dxf.tables?.layer?.layers || {}).map(([name, layer]) => ({
    name,
    color: layer.color,
    colorIndex: layer.colorIndex,
    visible: !layer.frozen && !layer.off,
    frozen: layer.frozen || false,
    lineType: layer.lineTypeName
  })),

  // Block definitions
  blocks: Object.entries(dxf.blocks || {}).map(([name, block]) => ({
    name,
    handle: block.handle,
    layer: block.layer,
    position: block.position,
    entities: block.entities || []
  })),

  // All entities
  entities: dxf.entities || []
}

// Write JSON output
try {
  fs.writeFileSync(outputFile, JSON.stringify(output, null, 2))
  console.log(`✓ Successfully converted!`)
  console.log('')
  console.log('Statistics:')
  console.log(`  Total entities: ${output.stats.entityCount.total}`)
  console.log(`  Layers: ${output.stats.layerCount}`)
  console.log(`  Blocks: ${output.stats.blockCount}`)
  console.log('')
  console.log('Entity types:')
  Object.entries(output.stats.entityCount.byType)
    .sort((a, b) => b[1] - a[1])
    .forEach(([type, count]) => {
      console.log(`  ${type}: ${count}`)
    })
  console.log('')
  console.log(`Calculated bounds: ${output.stats.bounds.width.toFixed(2)} x ${output.stats.bounds.height.toFixed(2)}`)

  // Display coordinate system info
  if (output.coordinateSystem) {
    const cs = output.coordinateSystem
    console.log('')
    console.log('Coordinate System (from header $EXTMIN/$EXTMAX):')
    console.log(`  Effective bounds: ${cs.bounds.width.toFixed(2)} x ${cs.bounds.height.toFixed(2)}`)
    console.log(`  Center: (${cs.center.x.toFixed(2)}, ${cs.center.y.toFixed(2)}, ${cs.center.z.toFixed(2)})`)
    console.log(`  Scale: ${cs.scale} (INSUNITS: ${cs.units})`)
  } else {
    console.log('')
    console.log('⚠ Warning: No valid coordinate system - header $EXTMIN/$EXTMAX not found')
  }
} catch (err) {
  console.error('Error writing output file:', err.message)
  process.exit(1)
}
