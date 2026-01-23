/**
 * Extract Fence Segments from yard.json
 *
 * Extracts LINE and LWPOLYLINE entities from fence layers
 * for rendering as 3D vertical walls.
 *
 * Usage: node scripts/extractFences.js
 * Output: src/data/fences.json
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Configuration
const FENCE_LAYERS = ['(040) Ограда', 'Т-ограждение']

function calculateBounds(points) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
  for (const p of points) {
    if (p.x < minX) minX = p.x
    if (p.x > maxX) maxX = p.x
    if (p.y < minY) minY = p.y
    if (p.y > maxY) maxY = p.y
  }
  return { minX, maxX, minY, maxY }
}

function calculateLength(points) {
  let length = 0
  for (let i = 0; i < points.length - 1; i++) {
    const dx = points[i + 1].x - points[i].x
    const dy = points[i + 1].y - points[i].y
    length += Math.sqrt(dx * dx + dy * dy)
  }
  return length
}

function extractFences() {
  console.log('🚧 Extracting fence segments from yard.json...\n')

  const yardPath = path.join(__dirname, '../public/yard.json')
  const yardData = JSON.parse(fs.readFileSync(yardPath, 'utf8'))

  const fenceSegments = []
  let segmentId = 1

  FENCE_LAYERS.forEach(layer => {
    const entities = yardData.entities.filter(e => e.layer === layer)
    console.log(`Layer "${layer}": ${entities.length} entities`)

    entities.forEach(entity => {
      if (entity.type === 'LINE') {
        // LINE has two vertices
        const vertices = entity.vertices || []
        if (vertices.length >= 2) {
          fenceSegments.push({
            id: segmentId++,
            handle: entity.handle,
            layer,
            type: 'line',
            points: vertices.map(v => ({ x: v.x, y: v.y })),
            length: calculateLength(vertices),
          })
        }
      } else if (entity.type === 'LWPOLYLINE') {
        // LWPOLYLINE is a connected series of segments
        const vertices = entity.vertices || []
        if (vertices.length >= 2) {
          fenceSegments.push({
            id: segmentId++,
            handle: entity.handle,
            layer,
            type: 'polyline',
            points: vertices.map(v => ({ x: v.x, y: v.y })),
            length: calculateLength(vertices),
            closed: entity.shape || false,
          })
        }
      }
      // Skip ARC for now - could be added later
    })
  })

  // Filter to main yard area (exclude legend/title block)
  const yardSegments = fenceSegments.filter(s => {
    const p = s.points[0]
    return p && p.x > 12000 && p.y > 70000
  })
  console.log(`Fences in main yard area: ${yardSegments.length}`)

  const allPoints = yardSegments.flatMap(s => s.points)
  const overallBounds = calculateBounds(allPoints)
  const totalLength = yardSegments.reduce((sum, s) => sum + s.length, 0)

  console.log(`\n📊 Fence Statistics:`)
  console.log(`   Total segments: ${yardSegments.length}`)
  console.log(`   Total length: ${totalLength.toFixed(2)} m`)
  console.log(`   X range: ${overallBounds.minX.toFixed(2)} - ${overallBounds.maxX.toFixed(2)}`)
  console.log(`   Y range: ${overallBounds.minY.toFixed(2)} - ${overallBounds.maxY.toFixed(2)}`)

  const output = {
    meta: {
      source: 'yard.json',
      layers: FENCE_LAYERS,
      extractedAt: new Date().toISOString(),
      count: yardSegments.length,
      totalLength,
    },
    bounds: overallBounds,
    segments: yardSegments,
  }

  const outputPath = path.join(__dirname, '../src/data/fences.json')
  const outputDir = path.dirname(outputPath)
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true })
  }

  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2))
  console.log(`\n✅ Saved to ${outputPath}`)

  return output
}

extractFences()
