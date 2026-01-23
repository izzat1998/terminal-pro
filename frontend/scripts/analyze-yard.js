import fs from 'fs'

const data = fs.readFileSync('public/yard.json', 'utf8')
const json = JSON.parse(data)

console.log('=== STRUCTURE VALIDATION ===')
console.log('Has meta:', !!json.meta)
console.log('Has header:', !!json.header)
console.log('Has stats:', !!json.stats)
console.log('Has layers:', Array.isArray(json.layers), '- count:', json.layers.length)
console.log('Has blocks:', Array.isArray(json.blocks), '- count:', json.blocks.length)
console.log('Has entities:', Array.isArray(json.entities), '- count:', json.entities.length)

console.log('\n=== BOUNDS COMPARISON ===')
console.log('Calculated bounds:')
console.log('  Min:', JSON.stringify(json.stats.bounds.min))
console.log('  Max:', JSON.stringify(json.stats.bounds.max))
console.log('  Size:', json.stats.bounds.width.toFixed(2), 'x', json.stats.bounds.height.toFixed(2))

console.log('\nHeader bounds (from DXF):')
console.log('  EXTMIN:', JSON.stringify(json.header['$EXTMIN']))
console.log('  EXTMAX:', JSON.stringify(json.header['$EXTMAX']))

// Check for data integrity issues
console.log('\n=== DATA INTEGRITY CHECKS ===')

// Check entities have required fields
let missingLayer = 0
let missingType = 0
let missingHandle = 0
json.entities.forEach(e => {
  if (!e.layer) missingLayer++
  if (!e.type) missingType++
  if (!e.handle) missingHandle++
})
console.log('Entities missing layer:', missingLayer)
console.log('Entities missing type:', missingType)
console.log('Entities missing handle:', missingHandle)

// Check for NaN or invalid coordinates
let invalidCoords = 0
function checkPoint(p) {
  if (!p) return
  if (isNaN(p.x) || isNaN(p.y)) invalidCoords++
}
json.entities.forEach(e => {
  if (e.vertices) e.vertices.forEach(checkPoint)
  if (e.position) checkPoint(e.position)
  if (e.center) checkPoint(e.center)
  if (e.startPoint) checkPoint(e.startPoint)
})
console.log('Invalid coordinates found:', invalidCoords)

console.log('\n=== ALL LAYERS ===')
json.layers.forEach(l => console.log(' -', l.name.padEnd(25), '| color:', String(l.colorIndex).padStart(3), '| visible:', l.visible))

console.log('\n=== ENTITY TYPES BREAKDOWN ===')
Object.entries(json.stats.entityCount.byType)
  .sort((a, b) => b[1] - a[1])
  .forEach(([type, count]) => {
    console.log(' ', type.padEnd(12), count)
  })

console.log('\n=== SAMPLE BLOCKS (first 10) ===')
json.blocks.slice(0, 10).forEach(b => {
  console.log(' -', b.name, '| entities:', b.entities.length)
})

console.log('\n=== INTERPRETATION ===')
// Try to identify what this DXF represents
const layerNames = json.layers.map(l => l.name.toLowerCase())
const hasContainers = layerNames.some(n => n.includes('контейнер') || n.includes('container'))
const hasRoads = layerNames.some(n => n.includes('дорог') || n.includes('road'))
const hasBuildings = layerNames.some(n => n.includes('здан') || n.includes('building') || n.includes('doma'))
const hasFence = layerNames.some(n => n.includes('ограда') || n.includes('fence') || n.includes('граница'))
const hasWater = layerNames.some(n => n.includes('вод') || n.includes('water'))

console.log('Contains buildings/structures:', hasBuildings)
console.log('Contains roads:', hasRoads)
console.log('Contains fence/boundary:', hasFence)
console.log('Contains water infrastructure:', hasWater)
console.log('Contains container areas:', hasContainers)
