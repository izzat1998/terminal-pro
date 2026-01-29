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
    const sample = block.instances[0]
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
  // Look for blocks that might represent containers
  // Criteria: repeated insertions with consistent patterns

  const candidates = blocks.filter(block => {
    // Check layer
    const onContainerLayer = CONTAINER_LAYERS.some(l =>
      block.layer.toLowerCase().includes(l.toLowerCase())
    )

    // Check block name patterns
    const matchesPattern = CONTAINER_BLOCK_PATTERNS.some(p => p.test(block.name))

    // Check count (containers usually have many instances)
    const hasEnoughInstances = block.instances.length >= 10

    return onContainerLayer || matchesPattern || (hasEnoughInstances && block.instances.length < 1000)
  })

  return candidates
}

function extractContainerPositions(dxf, blocks) {
  // Calculate bounds from all geometry for centering
  let minX = Infinity, maxX = -Infinity
  let minY = Infinity, maxY = -Infinity

  // Use INSERT positions for bounds (more reliable than all entities)
  const allInserts = dxf.entities.filter(e => e.type === 'INSERT')
  allInserts.forEach(ins => {
    minX = Math.min(minX, ins.position.x)
    maxX = Math.max(maxX, ins.position.x)
    minY = Math.min(minY, ins.position.y)
    maxY = Math.max(maxY, ins.position.y)
  })

  const center = {
    x: (minX + maxX) / 2,
    y: (minY + maxY) / 2
  }

  console.log(`\n📍 Center point: X=${center.x.toFixed(2)}, Y=${center.y.toFixed(2)}`)
  console.log(`📐 Bounds: X=[${minX.toFixed(2)}, ${maxX.toFixed(2)}], Y=[${minY.toFixed(2)}, ${maxY.toFixed(2)}]`)

  // Extract container positions
  const containers = []
  let id = 1

  // If no specific container blocks found, use all inserts from likely layers
  const targetBlocks = blocks.length > 0 ? blocks : [{
    instances: dxf.entities.filter(e =>
      e.type === 'INSERT' &&
      CONTAINER_LAYERS.some(l => e.layer?.toLowerCase().includes(l.toLowerCase()))
    )
  }]

  targetBlocks.forEach(block => {
    block.instances.forEach(ins => {
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
