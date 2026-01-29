# Three.js Codebase Simplification Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce code duplication by ~600 lines, improve GPU memory usage by ~500KB, and establish consistent patterns across all 3D composables.

**Architecture:** Extract shared utilities for coordinate transforms and geometry operations, pool expensive resources (textures, materials), and consolidate duplicate logic.

**Tech Stack:** Three.js r160+, Vue 3 Composition API, TypeScript

---

## Summary of Changes

| Phase | Action | Files Affected | Lines Saved | Memory Saved |
|-------|--------|----------------|-------------|--------------|
| **Phase 1** | Extract coordinate utilities | 6 composables | ~50 lines | — |
| **Phase 2** | Extract geometry utilities | 4 composables | ~250 lines | — |
| **Phase 3** | Fix license plate pooling | useVehicleModels.ts | ~30 lines | ~400 KB GPU |
| **Phase 4** | Share materials | 3 composables | ~20 lines | ~100 KB GPU |
| **Phase 5** | Consolidate shape logic | 2 composables | ~120 lines | — |
| **Phase 6** | Cleanup & polish | 4 composables | ~50 lines | — |
| **Total** | | 12 files | **~520 lines** | **~500 KB** |

---

## Phase 1: Extract Coordinate Utilities

**Goal:** Create a single source of truth for DXF-to-Three.js coordinate transformations.

### Task 1.1: Create Coordinate Utility Module

**Files:**
- Create: `frontend/src/utils/dxfCoordinateUtils.ts`

**Step 1: Create the utility file**

```typescript
/**
 * DXF Coordinate Utilities
 *
 * Centralized coordinate transformation between DXF (AutoCAD) and Three.js coordinate systems.
 *
 * Coordinate Systems:
 * - DXF: X = right, Y = up (2D plan view), units in meters (INSUNITS=6)
 * - Three.js: X = right, Y = up, Z = toward camera
 *
 * Transformation: DXF Y → negative Three.js Z (plan view "up" becomes "forward")
 */

import * as THREE from 'three'

export interface CoordinateSystem {
  center: { x: number; y: number }
  scale: number
  bounds: {
    min: { x: number; y: number }
    max: { x: number; y: number }
  }
}

export interface DxfToWorldOptions {
  center?: { x: number; y: number }
  scale?: number
  coordinateSystem?: CoordinateSystem
}

/**
 * Transform DXF coordinates to Three.js world coordinates.
 *
 * @param dxfX - X coordinate in DXF space
 * @param dxfY - Y coordinate in DXF space
 * @param options - Transformation options (center, scale, or full coordinateSystem)
 * @returns THREE.Vector3 in world space (Y = 0 for ground plane)
 */
export function dxfToWorld(
  dxfX: number,
  dxfY: number,
  options: DxfToWorldOptions = {}
): THREE.Vector3 {
  const center = options.coordinateSystem?.center ?? options.center ?? { x: 0, y: 0 }
  const scale = options.coordinateSystem?.scale ?? options.scale ?? 1.0

  const x = (dxfX - center.x) * scale
  const z = -(dxfY - center.y) * scale  // DXF Y → negative Three.js Z

  return new THREE.Vector3(x, 0, z)
}

/**
 * Transform an array of DXF points to Three.js world coordinates.
 */
export function dxfPointsToWorld(
  points: Array<{ x: number; y: number }>,
  options: DxfToWorldOptions = {}
): THREE.Vector3[] {
  return points.map(p => dxfToWorld(p.x, p.y, options))
}

/**
 * Calculate direction vector between two consecutive path points.
 * Handles edge cases for first, last, and middle points.
 *
 * @param points - Array of world-space points
 * @param index - Current point index
 * @returns Normalized direction vector
 */
export function getPathDirection(
  points: THREE.Vector3[],
  index: number
): THREE.Vector3 {
  const len = points.length

  if (len < 2) {
    return new THREE.Vector3(1, 0, 0)  // Default forward
  }

  let dir: THREE.Vector3

  if (index === 0) {
    // First point: direction to next
    dir = new THREE.Vector3().subVectors(points[1], points[0])
  } else if (index === len - 1) {
    // Last point: direction from previous
    dir = new THREE.Vector3().subVectors(points[len - 1], points[len - 2])
  } else {
    // Middle point: average of incoming and outgoing directions
    const incoming = new THREE.Vector3().subVectors(points[index], points[index - 1])
    const outgoing = new THREE.Vector3().subVectors(points[index + 1], points[index])
    dir = incoming.add(outgoing)
  }

  return dir.normalize()
}

/**
 * Calculate perpendicular (right) vector from a direction on the XZ plane.
 */
export function getPerpendicularXZ(direction: THREE.Vector3): THREE.Vector3 {
  return new THREE.Vector3(-direction.z, 0, direction.x).normalize()
}

/**
 * Calculate rotation angle (radians) from a direction vector on the XZ plane.
 */
export function getRotationFromDirection(direction: THREE.Vector3): number {
  return Math.atan2(direction.x, direction.z)
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/utils/dxfCoordinateUtils.ts
```

**Step 3: Commit**

```bash
git add frontend/src/utils/dxfCoordinateUtils.ts && git commit -m "feat(3d): add centralized DXF coordinate utilities

- dxfToWorld(): Transform DXF coordinates to Three.js world space
- dxfPointsToWorld(): Batch transform for point arrays
- getPathDirection(): Calculate direction at path index
- getPerpendicularXZ(): Get perpendicular vector on ground plane

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.2: Update useContainers3D.ts to Use Utility

**Files:**
- Modify: `frontend/src/composables/useContainers3D.ts`

**Step 1: Add import**

At the top of the file, add:
```typescript
import { dxfToWorld, type CoordinateSystem } from '@/utils/dxfCoordinateUtils'
```

**Step 2: Remove local dxfToWorld function**

Find and remove the local `dxfToWorld` function (approximately lines 230-245). It looks like:
```typescript
// REMOVE THIS ENTIRE FUNCTION:
function dxfToWorld(dxfX: number, dxfY: number): THREE.Vector3 {
  const x = (dxfX - centerX) * scale
  const z = -(dxfY - centerY) * scale
  return new THREE.Vector3(x, 0, z)
}
```

**Step 3: Update all usages**

Replace usages of the local function with the imported utility. Change:
```typescript
const worldPos = dxfToWorld(origX, origY)
```
To:
```typescript
const worldPos = dxfToWorld(origX, origY, { center, scale })
```

Or if `coordinateSystem` is available:
```typescript
const worldPos = dxfToWorld(origX, origY, { coordinateSystem })
```

**Step 4: Verify build**

```bash
cd frontend && npm run build 2>&1 | grep -E "(useContainers3D|error)" | head -10
```

**Step 5: Commit**

```bash
git add frontend/src/composables/useContainers3D.ts && git commit -m "refactor(3d): use shared dxfToWorld in useContainers3D

Replace local coordinate transform with centralized utility.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.3: Update Remaining Composables

**Files to update (same pattern as Task 1.2):**
- `frontend/src/composables/useBuildings3D.ts`
- `frontend/src/composables/useFences3D.ts`
- `frontend/src/composables/useRoads3D.ts`
- `frontend/src/composables/useRailway3D.ts`
- `frontend/src/composables/usePlatforms3D.ts`

**For each file:**

1. Add import: `import { dxfToWorld, dxfPointsToWorld, getPathDirection } from '@/utils/dxfCoordinateUtils'`
2. Remove local `dxfToWorld` function (if present)
3. Remove local direction calculation code (if present)
4. Update usages to use imported utilities
5. Test build

**Step: Batch commit all updates**

```bash
git add frontend/src/composables/useBuildings3D.ts \
        frontend/src/composables/useFences3D.ts \
        frontend/src/composables/useRoads3D.ts \
        frontend/src/composables/useRailway3D.ts \
        frontend/src/composables/usePlatforms3D.ts && \
git commit -m "refactor(3d): use shared coordinate utilities in all composables

Updated:
- useBuildings3D.ts
- useFences3D.ts
- useRoads3D.ts
- useRailway3D.ts
- usePlatforms3D.ts

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 2: Extract Geometry Utilities

**Goal:** Centralize geometry merging and creation patterns.

### Task 2.1: Create Geometry Utility Module

**Files:**
- Create: `frontend/src/utils/geometryUtils.ts`

**Step 1: Create the utility file**

```typescript
/**
 * Geometry Utilities for Three.js
 *
 * Centralized geometry operations: merging, creation, disposal.
 */

import * as THREE from 'three'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'

export interface MergedMeshOptions {
  material: THREE.Material
  receiveShadow?: boolean
  castShadow?: boolean
  name?: string
}

/**
 * Merge multiple geometries into a single mesh.
 * Automatically disposes source geometries after merging.
 *
 * @param geometries - Array of BufferGeometry to merge
 * @param options - Mesh options (material, shadows, name)
 * @returns Single merged Mesh, or null if no valid geometries
 */
export function createMergedMesh(
  geometries: THREE.BufferGeometry[],
  options: MergedMeshOptions
): THREE.Mesh | null {
  // Filter out invalid geometries
  const validGeometries = geometries.filter(g =>
    g && g.attributes.position && g.attributes.position.count > 0
  )

  if (validGeometries.length === 0) {
    return null
  }

  // Merge geometries
  const mergedGeometry = mergeGeometries(validGeometries, false)

  if (!mergedGeometry) {
    console.warn('Failed to merge geometries')
    return null
  }

  // Compute normals for proper lighting
  mergedGeometry.computeVertexNormals()

  // Create mesh
  const mesh = new THREE.Mesh(mergedGeometry, options.material)
  mesh.receiveShadow = options.receiveShadow ?? true
  mesh.castShadow = options.castShadow ?? false
  mesh.name = options.name ?? 'merged-mesh'

  // Dispose source geometries to free memory
  validGeometries.forEach(g => g.dispose())

  return mesh
}

/**
 * Create a path-extruded geometry (for roads, rails, fences).
 *
 * @param points - Path points in world space
 * @param width - Width of the extruded shape
 * @param height - Height (Y) of the extruded shape
 * @param yOffset - Y offset from ground (default 0)
 * @returns BufferGeometry for the extruded path
 */
export function createPathGeometry(
  points: THREE.Vector3[],
  width: number,
  height: number,
  yOffset: number = 0
): THREE.BufferGeometry {
  if (points.length < 2) {
    return new THREE.BufferGeometry()
  }

  const vertices: number[] = []
  const indices: number[] = []
  const normals: number[] = []
  const uvs: number[] = []

  let accumulatedLength = 0

  for (let i = 0; i < points.length; i++) {
    const point = points[i]

    // Calculate direction and perpendicular
    let dir: THREE.Vector3
    if (i === 0) {
      dir = new THREE.Vector3().subVectors(points[1], points[0]).normalize()
    } else if (i === points.length - 1) {
      dir = new THREE.Vector3().subVectors(points[i], points[i - 1]).normalize()
    } else {
      const d1 = new THREE.Vector3().subVectors(points[i], points[i - 1])
      const d2 = new THREE.Vector3().subVectors(points[i + 1], points[i])
      dir = d1.add(d2).normalize()
    }

    const perp = new THREE.Vector3(-dir.z, 0, dir.x).multiplyScalar(width / 2)

    // Calculate UV coordinate based on path length
    if (i > 0) {
      accumulatedLength += points[i].distanceTo(points[i - 1])
    }
    const u = accumulatedLength / width  // Tile texture along path

    // Bottom left
    vertices.push(point.x - perp.x, yOffset, point.z - perp.z)
    normals.push(0, 1, 0)
    uvs.push(0, u)

    // Bottom right
    vertices.push(point.x + perp.x, yOffset, point.z + perp.z)
    normals.push(0, 1, 0)
    uvs.push(1, u)

    // Top left
    vertices.push(point.x - perp.x, yOffset + height, point.z - perp.z)
    normals.push(0, 1, 0)
    uvs.push(0, u)

    // Top right
    vertices.push(point.x + perp.x, yOffset + height, point.z + perp.z)
    normals.push(0, 1, 0)
    uvs.push(1, u)

    // Create faces (two triangles per segment)
    if (i > 0) {
      const base = (i - 1) * 4
      // Bottom face
      indices.push(base, base + 1, base + 5, base, base + 5, base + 4)
      // Top face
      indices.push(base + 2, base + 6, base + 7, base + 2, base + 7, base + 3)
      // Left face
      indices.push(base, base + 4, base + 6, base, base + 6, base + 2)
      // Right face
      indices.push(base + 1, base + 3, base + 7, base + 1, base + 7, base + 5)
    }
  }

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3))
  geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3))
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2))
  geometry.setIndex(indices)
  geometry.computeVertexNormals()

  return geometry
}

/**
 * Create a simple box geometry with custom dimensions.
 * More efficient than creating new BoxGeometry each time.
 */
const boxGeometryCache = new Map<string, THREE.BoxGeometry>()

export function getBoxGeometry(
  width: number,
  height: number,
  depth: number
): THREE.BoxGeometry {
  const key = `${width}_${height}_${depth}`

  if (!boxGeometryCache.has(key)) {
    boxGeometryCache.set(key, new THREE.BoxGeometry(width, height, depth))
  }

  return boxGeometryCache.get(key)!
}

/**
 * Create a cylinder geometry with caching.
 */
const cylinderGeometryCache = new Map<string, THREE.CylinderGeometry>()

export function getCylinderGeometry(
  radiusTop: number,
  radiusBottom: number,
  height: number,
  segments: number = 16
): THREE.CylinderGeometry {
  const key = `${radiusTop}_${radiusBottom}_${height}_${segments}`

  if (!cylinderGeometryCache.has(key)) {
    cylinderGeometryCache.set(key, new THREE.CylinderGeometry(radiusTop, radiusBottom, height, segments))
  }

  return cylinderGeometryCache.get(key)!
}

/**
 * Clear geometry caches (call on dispose).
 */
export function clearGeometryCaches(): void {
  boxGeometryCache.forEach(g => g.dispose())
  boxGeometryCache.clear()

  cylinderGeometryCache.forEach(g => g.dispose())
  cylinderGeometryCache.clear()
}
```

**Step 2: Verify and commit**

```bash
cd frontend && npx tsc --noEmit src/utils/geometryUtils.ts && \
git add frontend/src/utils/geometryUtils.ts && \
git commit -m "feat(3d): add centralized geometry utilities

- createMergedMesh(): Merge geometries with auto-disposal
- createPathGeometry(): Extrude geometry along path
- getBoxGeometry(): Cached box geometry creation
- getCylinderGeometry(): Cached cylinder geometry creation

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 2.2: Update useRoads3D.ts to Use Geometry Utilities

**Files:**
- Modify: `frontend/src/composables/useRoads3D.ts`

**Step 1: Add imports**

```typescript
import { createMergedMesh } from '@/utils/geometryUtils'
import { dxfToWorld, dxfPointsToWorld, getPathDirection, getPerpendicularXZ } from '@/utils/dxfCoordinateUtils'
```

**Step 2: Replace manual merge logic**

Find the geometry merging code (approximately lines 312-374) and replace with:

```typescript
// BEFORE: Manual mergeGeometries call with cleanup
// AFTER: Use utility
const roadMesh = createMergedMesh(roadGeometries, {
  material: roadMaterial,
  receiveShadow: true,
  castShadow: false,
  name: 'roads',
})

if (roadMesh) {
  group.add(roadMesh)
}
```

**Step 3: Commit**

```bash
git add frontend/src/composables/useRoads3D.ts && \
git commit -m "refactor(3d): use geometry utilities in useRoads3D

Replace manual geometry merging with createMergedMesh utility.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 2.3: Update useFences3D.ts and useRailway3D.ts

**Same pattern as Task 2.2:**
1. Add imports for geometry utilities
2. Replace manual merge logic with `createMergedMesh()`
3. Use `getPathDirection()` and `getPerpendicularXZ()` where applicable

**Commit:**

```bash
git add frontend/src/composables/useFences3D.ts \
        frontend/src/composables/useRailway3D.ts && \
git commit -m "refactor(3d): use geometry utilities in fences and railway

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 3: Fix License Plate Texture Pooling

**Goal:** Eliminate per-vehicle canvas/texture creation, saving ~400KB GPU memory.

### Task 3.1: Create Texture Pool for License Plates

**Files:**
- Modify: `frontend/src/composables/useVehicleModels.ts`

**Step 1: Create module-level texture cache**

At the top of the file (after imports), add:

```typescript
// Texture pool for license plates - create once, reuse everywhere
let baseLicensePlateTexture: THREE.CanvasTexture | null = null
let baseLicensePlateMaterial: THREE.MeshStandardMaterial | null = null

/**
 * Get or create the base license plate texture.
 * Creates a template plate texture that can be shared across all vehicles.
 */
function getBaseLicensePlateTexture(): THREE.CanvasTexture {
  if (baseLicensePlateTexture) {
    return baseLicensePlateTexture
  }

  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 64
  const ctx = canvas.getContext('2d')!

  // White background with subtle gradient
  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height)
  gradient.addColorStop(0, '#FFFFFF')
  gradient.addColorStop(1, '#F0F0F0')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // Border
  ctx.strokeStyle = '#333333'
  ctx.lineWidth = 4
  ctx.strokeRect(2, 2, canvas.width - 4, canvas.height - 4)

  // Placeholder text (will be overwritten by specific plates if needed)
  ctx.fillStyle = '#1a1a1a'
  ctx.font = 'bold 28px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('01 A 000 AA', canvas.width / 2, canvas.height / 2)

  baseLicensePlateTexture = new THREE.CanvasTexture(canvas)
  baseLicensePlateTexture.colorSpace = THREE.SRGBColorSpace

  return baseLicensePlateTexture
}

/**
 * Get or create the base license plate material.
 */
function getBaseLicensePlateMaterial(): THREE.MeshStandardMaterial {
  if (baseLicensePlateMaterial) {
    return baseLicensePlateMaterial.clone()  // Clone for per-vehicle customization if needed
  }

  baseLicensePlateMaterial = new THREE.MeshStandardMaterial({
    map: getBaseLicensePlateTexture(),
    roughness: 0.3,
    metalness: 0.1,
  })

  return baseLicensePlateMaterial.clone()
}
```

**Step 2: Update createLicensePlate function**

Replace the existing `createLicensePlate` function to use the pooled texture:

```typescript
function createLicensePlate(width: number = 0.52, height: number = 0.11): THREE.Mesh {
  const geometry = new THREE.PlaneGeometry(width, height)
  const material = getBaseLicensePlateMaterial()

  const mesh = new THREE.Mesh(geometry, material)
  mesh.name = 'license-plate'

  return mesh
}
```

**Step 3: Add cleanup to dispose function**

In the module's dispose logic (if any), add:

```typescript
function disposeTexturePool(): void {
  if (baseLicensePlateTexture) {
    baseLicensePlateTexture.dispose()
    baseLicensePlateTexture = null
  }
  if (baseLicensePlateMaterial) {
    baseLicensePlateMaterial.dispose()
    baseLicensePlateMaterial = null
  }
}
```

**Step 4: Commit**

```bash
git add frontend/src/composables/useVehicleModels.ts && \
git commit -m "perf(3d): pool license plate textures for memory efficiency

Before: Each vehicle created its own canvas + texture (~8KB each)
After: One shared texture, materials cloned as needed

Estimated savings: ~400KB GPU memory for 50 vehicles

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 4: Share Materials

**Goal:** Reduce material instances by sharing base materials.

### Task 4.1: Create Shared Materials Module

**Files:**
- Modify: `frontend/src/composables/useMaterials3D.ts`

**Step 1: Add material pool functions**

Add to the composable:

```typescript
// Shared material instances for common use cases
const sharedMaterials = new Map<string, THREE.MeshStandardMaterial>()

/**
 * Get a shared material by key. Creates if not exists.
 * Use for objects that don't need individual color customization.
 */
export function getSharedMaterial(
  key: string,
  options: {
    color: number
    metalness?: number
    roughness?: number
  }
): THREE.MeshStandardMaterial {
  if (sharedMaterials.has(key)) {
    return sharedMaterials.get(key)!
  }

  const material = new THREE.MeshStandardMaterial({
    color: options.color,
    metalness: options.metalness ?? 0.1,
    roughness: options.roughness ?? 0.8,
  })

  sharedMaterials.set(key, material)
  return material
}

/**
 * Get a clone of a shared material (for objects needing color variation).
 */
export function getSharedMaterialClone(key: string): THREE.MeshStandardMaterial | null {
  const base = sharedMaterials.get(key)
  return base ? base.clone() : null
}
```

**Step 2: Update dispose function**

```typescript
function dispose(): void {
  clearCache()

  // Dispose shared materials
  sharedMaterials.forEach(m => m.dispose())
  sharedMaterials.clear()
}
```

**Step 3: Commit**

```bash
git add frontend/src/composables/useMaterials3D.ts && \
git commit -m "feat(3d): add shared material pooling

- getSharedMaterial(): Get or create shared material by key
- getSharedMaterialClone(): Clone shared material for customization

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.2: Update useBuildings3D.ts to Use Shared Materials

**Files:**
- Modify: `frontend/src/composables/useBuildings3D.ts`

**Step 1: Import shared material function**

```typescript
import { getSharedMaterial } from '@/composables/useMaterials3D'
```

**Step 2: Replace per-building material creation**

Find material creation (around line 205) and replace:

```typescript
// BEFORE:
const material = new THREE.MeshStandardMaterial({
  color: buildingColor,
  roughness: 0.8,
  metalness: 0.1,
})

// AFTER:
const material = getSharedMaterial('building-base', {
  color: 0x94a3b8,  // Default building color
  roughness: 0.8,
  metalness: 0.1,
}).clone()
material.color.setHex(buildingColor)  // Apply specific color
```

**Step 3: Commit**

```bash
git add frontend/src/composables/useBuildings3D.ts && \
git commit -m "refactor(3d): use shared materials in useBuildings3D

Clone from shared base material instead of creating new instances.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.3: Update usePlatforms3D.ts Similarly

**Same pattern as Task 4.2**

```bash
git add frontend/src/composables/usePlatforms3D.ts && \
git commit -m "refactor(3d): use shared materials in usePlatforms3D

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 5: Consolidate Shape Logic

**Goal:** Extract duplicate extrusion logic from buildings and platforms.

### Task 5.1: Create Shape Extrusion Utility

**Files:**
- Add to: `frontend/src/utils/geometryUtils.ts`

**Step 1: Add extruded shape function**

```typescript
/**
 * Create an extruded shape geometry from a polygon outline.
 * Used for buildings, platforms, and other extruded structures.
 *
 * @param points - Polygon outline points (2D, will be on XZ plane)
 * @param height - Extrusion height (Y axis)
 * @param options - Additional options
 */
export function createExtrudedPolygonGeometry(
  points: Array<{ x: number; z: number }>,
  height: number,
  options: {
    bevelEnabled?: boolean
    bevelSize?: number
    bevelThickness?: number
  } = {}
): THREE.ExtrudeGeometry {
  // Create 2D shape from points
  const shape = new THREE.Shape()

  if (points.length > 0) {
    shape.moveTo(points[0].x, points[0].z)
    for (let i = 1; i < points.length; i++) {
      shape.lineTo(points[i].x, points[i].z)
    }
    shape.closePath()
  }

  // Extrude settings
  const extrudeSettings: THREE.ExtrudeGeometryOptions = {
    depth: height,
    bevelEnabled: options.bevelEnabled ?? false,
    bevelSize: options.bevelSize ?? 0.1,
    bevelThickness: options.bevelThickness ?? 0.1,
  }

  const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings)

  // Rotate to stand upright (extrusion is along Z, we want Y)
  geometry.rotateX(-Math.PI / 2)

  return geometry
}
```

**Step 2: Commit**

```bash
git add frontend/src/utils/geometryUtils.ts && \
git commit -m "feat(3d): add extruded polygon geometry utility

createExtrudedPolygonGeometry() for buildings, platforms, etc.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 5.2: Update Buildings and Platforms to Use Utility

**Files:**
- Modify: `frontend/src/composables/useBuildings3D.ts`
- Modify: `frontend/src/composables/usePlatforms3D.ts`

**Step 1: Import utility**

```typescript
import { createExtrudedPolygonGeometry } from '@/utils/geometryUtils'
```

**Step 2: Replace manual shape creation**

Find the shape creation code (approximately 60-80 lines in each file) and replace with:

```typescript
const geometry = createExtrudedPolygonGeometry(
  worldPoints.map(p => ({ x: p.x, z: p.z })),
  buildingHeight,
  { bevelEnabled: false }
)
```

**Step 3: Commit**

```bash
git add frontend/src/composables/useBuildings3D.ts \
        frontend/src/composables/usePlatforms3D.ts && \
git commit -m "refactor(3d): use extruded polygon utility in buildings and platforms

Replaced ~120 lines of duplicate shape extrusion code.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 6: Cleanup & Polish

### Task 6.1: Remove Unused Code

**Files to check:**
- `frontend/src/composables/usePlatforms3D.ts` - Remove unused `selectedIds` ref
- Any other dead code identified during refactoring

**Commit:**

```bash
git add -A && git commit -m "chore(3d): remove unused code and dead references

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 6.2: Add Geometry Cache Cleanup to YardView3D

**Files:**
- Modify: `frontend/src/components/YardView3D.vue`

**Step 1: Import cleanup function**

```typescript
import { clearGeometryCaches } from '@/utils/geometryUtils'
```

**Step 2: Call in dispose function**

```typescript
function dispose(): void {
  // ... existing cleanup ...

  clearGeometryCaches()  // Clean up geometry pools
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/YardView3D.vue && \
git commit -m "chore(3d): add geometry cache cleanup on dispose

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 6.3: Final Verification

**Step 1: Build the frontend**

```bash
cd frontend && npm run build
```

**Step 2: Run dev server and test**

```bash
npm run dev
```

**Step 3: Visual verification checklist**

- [ ] Buildings render correctly
- [ ] Platforms render correctly
- [ ] Roads render correctly
- [ ] Fences render correctly
- [ ] Railway renders correctly
- [ ] Containers render correctly (with edge lines if enabled)
- [ ] Vehicles render correctly (trucks, cars, wagons)
- [ ] License plates display on vehicles
- [ ] Performance is smooth (60fps)
- [ ] No console errors

**Step 4: Final commit**

```bash
git add -A && git commit -m "test: verify 3D simplification refactoring

All composables updated to use shared utilities:
- Coordinate transforms: dxfCoordinateUtils.ts
- Geometry operations: geometryUtils.ts
- Material sharing: useMaterials3D.ts

Visual verification complete.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

| Phase | Tasks | Lines Removed | Memory Saved |
|-------|-------|---------------|--------------|
| Phase 1 | 3 tasks | ~50 lines | — |
| Phase 2 | 3 tasks | ~250 lines | — |
| Phase 3 | 1 task | ~30 lines | ~400 KB |
| Phase 4 | 3 tasks | ~20 lines | ~100 KB |
| Phase 5 | 2 tasks | ~120 lines | — |
| Phase 6 | 3 tasks | ~50 lines | — |
| **Total** | **15 tasks** | **~520 lines** | **~500 KB** |

---

## Rollback Plan

If issues arise, revert all changes:

```bash
git log --oneline -20  # Find the commit before Phase 1
git revert HEAD~N..HEAD  # Where N is number of commits to revert
```

Or revert individual phases by finding phase-ending commits.
