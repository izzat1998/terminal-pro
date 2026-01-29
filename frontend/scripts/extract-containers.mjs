#!/usr/bin/env node
/**
 * Container Position Extraction Script
 * Parses DXF file and extracts container positions from INSERT entities
 *
 * Usage: node scripts/extract-containers.mjs [dxf-file] [output-file]
 * Example: node scripts/extract-containers.mjs frontend/public/yard.dxf frontend/src/data/containers.json
 */

import { readFileSync, writeFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'
import DxfParser from 'dxf-parser'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Container-related layer names (Russian)
const CONTAINER_LAYERS = [
  'Т-КП',           // Container yard / checkpoints
  'Т-Контейнеры',   // Containers (if exists)
  'containers',     // English alternative
]

// Block names that represent containers (will be auto-detected)
const CONTAINER_BLOCK_PATTERNS = [
  /контейнер/i,     // Russian for container
  /container/i,     // English
  /^20[GH][PC]$/i,  // Container type codes
  /^40[GH][PC]$/i,
  /^45[GH][PC]$/i,
]

function parseArgs() {
  const args = process.argv.slice(2)
  const dxfPath = args[0] || resolve(__dirname, '../frontend/public/yard.dxf')
  const outputPath = args[1] || resolve(__dirname, '../frontend/src/data/containers.json')
  return { dxfPath, outputPath }
}

function parseDxf(filePath) {
  console.log(`📂 Reading DXF: ${filePath}`)
  const content = readFileSync(filePath, 'utf8')
  const parser = new DxfParser()
  const dxf = parser.parse(content)

  if (!dxf) {
    throw new Error('Failed to parse DXF file')
  }

  return dxf
}

function analyzeBlocks(dxf) {
  const inserts = dxf.entities.filter(e => e.type === 'INSERT')

  // Group by block name
  const byBlock = {}
  inserts.forEach(ins => {
    const key = `${ins.name}|${ins.layer}`
    byBlock[key] = byBlock[key] || { name: ins.name, layer: ins.layer, instances: [] }
    byBlock[key].instances.push(ins)
  })

  console.log('\n📊 Block analysis:')
  const sorted = Object.values(byBlock).sort((a, b) => b.instances.length - a.instances.length)

  sorted.slice(0, 15).forEach(block => {
    console.log(`  ${block.name} (${block.layer}): ${block.instances.length} instances`)
    if (block.instances.length <= 3) {
      block.instances.forEach((ins, i) => {
        console.log(`    ${i+1}. X=${ins.position.x.toFixed(1)}, Y=${ins.position.y.toFixed(1)}, Rot=${ins.rotation?.toFixed(1) || 0}°`)
      })
    }
  })

  return sorted
}

function findContainerBlocks(blocks) {
  // Look for blocks that represent containers
  // Primary criteria: 40ft/20ft blocks ONLY on Т-Контейнеры layer

  const candidates = blocks.filter(block => {
    // Only consider blocks on the specific container layer
    if (block.layer !== 'Т-Контейнеры') {
      return false
    }

    // Require matching container block name (40ft or 20ft)
    return block.name === '40ft' || block.name === '20ft'
  })

  return candidates
}

function extractContainerPositions(dxf, blocks) {
  // Collect ALL container instances (no outlier filtering)
  // The yard has multiple container regions that should all be included
  const containerInstances = []
  blocks.forEach(block => {
    block.instances.forEach(ins => {
      containerInstances.push(ins)
    })
  })

  console.log(`\n📊 Total container instances: ${containerInstances.length}`)

  // Calculate bounds from ALL container positions
  let minX = Infinity, maxX = -Infinity
  let minY = Infinity, maxY = -Infinity

  if (containerInstances.length > 0) {
    containerInstances.forEach(ins => {
      minX = Math.min(minX, ins.position.x)
      maxX = Math.max(maxX, ins.position.x)
      minY = Math.min(minY, ins.position.y)
      maxY = Math.max(maxY, ins.position.y)
    })
  } else {
    // Fallback to DXF extents if no containers found
    const extmin = dxf.header['$EXTMIN']
    const extmax = dxf.header['$EXTMAX']
    if (extmin && extmax) {
      minX = extmin.x; minY = extmin.y
      maxX = extmax.x; maxY = extmax.y
    }
  }

  const center = {
    x: (minX + maxX) / 2,
    y: (minY + maxY) / 2
  }

  console.log(`\n📍 Center point (from containers): X=${center.x.toFixed(2)}, Y=${center.y.toFixed(2)}`)
  console.log(`📐 Bounds: X=[${minX.toFixed(2)}, ${maxX.toFixed(2)}], Y=[${minY.toFixed(2)}, ${maxY.toFixed(2)}]`)

  // Extract container positions from filtered instances
  const containers = []
  let id = 1

  containerInstances.forEach(ins => {
    containers.push({
      id: id++,
      x: ins.position.x - center.x,  // Center-relative coordinates
      y: ins.position.y - center.y,
      rotation: ins.rotation || 0,
      blockName: ins.name,
      layer: ins.layer,
      // Store original coordinates for reference
      _original: {
        x: ins.position.x,
        y: ins.position.y
      }
    })
  })

  // Add metadata
  const output = {
    _meta: {
      generated: new Date().toISOString(),
      source: 'yard.dxf',
      center,
      bounds: { minX, maxX, minY, maxY },
      units: 'meters',  // INSUNITS=6
      count: containers.length
    },
    containers
  }

  return output
}

function main() {
  const { dxfPath, outputPath } = parseArgs()

  console.log('🔧 Container Position Extraction Script')
  console.log('=' .repeat(50))

  // Parse DXF
  const dxf = parseDxf(dxfPath)

  // Analyze blocks
  const blocks = analyzeBlocks(dxf)

  // Find container-related blocks
  const containerBlocks = findContainerBlocks(blocks)

  if (containerBlocks.length > 0) {
    console.log(`\n✅ Found ${containerBlocks.length} potential container block types:`)
    containerBlocks.forEach(b => console.log(`  - ${b.name} (${b.instances.length} instances)`))
  } else {
    console.log('\n⚠️  No specific container blocks found, using all INSERTs')
  }

  // Extract positions
  const result = extractContainerPositions(dxf, containerBlocks)

  console.log(`\n📦 Extracted ${result.containers.length} container positions`)

  // Write output
  writeFileSync(outputPath, JSON.stringify(result.containers, null, 2))
  console.log(`\n✅ Saved to: ${outputPath}`)

  // Also save with metadata for debugging
  const debugPath = outputPath.replace('.json', '.debug.json')
  writeFileSync(debugPath, JSON.stringify(result, null, 2))
  console.log(`📋 Debug info saved to: ${debugPath}`)
}

main()
