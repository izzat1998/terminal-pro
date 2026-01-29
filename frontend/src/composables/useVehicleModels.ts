/**
 * Vehicle 3D Model Composable
 * Creates low-poly procedural 3D models for trucks, cars, and rail wagons
 *
 * Real-world dimensions used:
 * - Truck Tractor: 6.0m × 2.55m × 3.8m
 * - Container Chassis (40ft): 12.5m × 2.5m × 1.55m
 * - Container Chassis (20ft): 6.1m × 2.5m × 1.55m
 * - Light Vehicle: 4.5m × 1.8m × 1.6m
 * - Rail Wagon (NX70): 16.4m × 3.0m × 1.4m
 */

import * as THREE from 'three'

// Vehicle types supported by the gate camera system
export type VehicleType = 'TRUCK' | 'CAR' | 'WAGON' | 'UNKNOWN'

// License plate dimensions (real-world: ~52cm × 11cm for EU standard)
const PLATE_DIMS = {
  width: 0.52,
  height: 0.11,
}

// Pooled geometry for license plates (all plates are same size)
let licensePlateGeometry: THREE.PlaneGeometry | null = null

/**
 * Get or create the shared license plate geometry.
 * All plates are identical in size, so we pool the geometry.
 */
function getLicensePlateGeometry(): THREE.PlaneGeometry {
  if (!licensePlateGeometry) {
    licensePlateGeometry = new THREE.PlaneGeometry(PLATE_DIMS.width, PLATE_DIMS.height)
  }
  return licensePlateGeometry
}

/**
 * Dispose the pooled license plate geometry.
 * Call this when the 3D scene is being torn down.
 */
export function disposeLicensePlatePool(): void {
  if (licensePlateGeometry) {
    licensePlateGeometry.dispose()
    licensePlateGeometry = null
  }
}

// Color palette matching the premium yard theme
export const VEHICLE_COLORS = {
  truckPrimary: 0x0077B6,    // Deep blue (matches yard theme)
  truckSecondary: 0x005588,  // Darker blue for accents
  truckChassis: 0x333333,    // Dark gray
  carColors: [0xFFFFFF, 0x333333, 0x666666, 0xCC0000, 0x0066CC], // White, black, gray, red, blue
  wagonDeck: 0x8B4513,       // Brown/rust
  wagonMetal: 0x444444,      // Dark metal
  wheel: 0x222222,           // Near black
  chrome: 0xCCCCCC,          // Light gray metallic
  glass: 0x88CCFF,           // Light blue tint
}

// Options for creating vehicle models
export interface VehicleModelOptions {
  /** Primary color override */
  color?: number
  /** Whether truck should have container chassis attached */
  withChassis?: boolean
  /** Container size for chassis */
  chassisSize?: '20ft' | '40ft'
  /** Scale factor (default 1.0 = real-world meters) */
  scale?: number
  /** License plate number to display on the vehicle */
  plateNumber?: string
}

/**
 * Composable for creating 3D vehicle models
 * Returns factory functions for each vehicle type
 */
export function useVehicleModels() {
  /**
   * Create a 3D license plate mesh with the plate number rendered as texture
   *
   * Uses canvas to render realistic plate with:
   * - Yellow background (Uzbekistan/EU style)
   * - Dark embossed text
   * - Subtle border
   *
   * @param plateNumber - The license plate text to display
   * @param facingBack - If true, plate faces +X (rear), otherwise -X (front)
   * @returns THREE.Mesh with the license plate
   */
  function createLicensePlate(plateNumber: string, facingBack = false): THREE.Mesh {
    // Create canvas for plate texture
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')!

    // High resolution for crisp text (will be scaled down)
    canvas.width = 512
    canvas.height = 128

    // Draw plate background - yellow gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height)
    gradient.addColorStop(0, '#fef9c3')    // Light yellow top
    gradient.addColorStop(0.5, '#fde047')  // Bright yellow middle
    gradient.addColorStop(1, '#facc15')    // Darker yellow bottom

    // Plate background with rounded corners
    const radius = 12
    ctx.fillStyle = gradient
    ctx.beginPath()
    ctx.roundRect(4, 4, canvas.width - 8, canvas.height - 8, radius)
    ctx.fill()

    // Plate border
    ctx.strokeStyle = '#a16207'
    ctx.lineWidth = 4
    ctx.stroke()

    // Outer frame (dark)
    ctx.strokeStyle = '#374151'
    ctx.lineWidth = 8
    ctx.beginPath()
    ctx.roundRect(0, 0, canvas.width, canvas.height, radius + 4)
    ctx.stroke()

    // Draw plate number text
    ctx.fillStyle = '#1a1a1a'
    ctx.font = 'bold 72px Arial Black, Arial, sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    // Text shadow for embossed effect
    ctx.shadowColor = 'rgba(255, 255, 255, 0.5)'
    ctx.shadowOffsetX = 2
    ctx.shadowOffsetY = 2
    ctx.shadowBlur = 0

    ctx.fillText(plateNumber.toUpperCase(), canvas.width / 2, canvas.height / 2 + 4)

    // Reset shadow and add dark outline
    ctx.shadowColor = 'transparent'
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.2)'
    ctx.lineWidth = 1
    ctx.strokeText(plateNumber.toUpperCase(), canvas.width / 2, canvas.height / 2 + 4)

    // Create texture from canvas
    const texture = new THREE.CanvasTexture(canvas)
    texture.minFilter = THREE.LinearFilter
    texture.magFilter = THREE.LinearFilter
    texture.anisotropy = 4

    // Create plate mesh using pooled geometry
    const material = new THREE.MeshStandardMaterial({
      map: texture,
      roughness: 0.3,
      metalness: 0.1,
    })

    const plate = new THREE.Mesh(getLicensePlateGeometry(), material)
    plate.name = facingBack ? 'license-plate-rear' : 'license-plate-front'

    // Rotate to face the correct direction
    if (facingBack) {
      plate.rotation.y = 0  // Face +X (rear of vehicle)
    } else {
      plate.rotation.y = Math.PI  // Face -X (front of vehicle)
    }

    return plate
  }

  /**
   * Create a low-poly truck tractor (cab) model
   * Dimensions: 6.0m length × 2.55m width × 3.8m height
   */
  function createTruckModel(options: VehicleModelOptions = {}): THREE.Group {
    const {
      color = VEHICLE_COLORS.truckPrimary,
      withChassis = false,
      chassisSize = '40ft',
      scale = 1.0,
      plateNumber,
    } = options

    const truck = new THREE.Group()
    truck.name = 'truck'

    // Materials
    const cabMaterial = new THREE.MeshStandardMaterial({
      color,
      roughness: 0.4,
      metalness: 0.3,
    })
    const darkMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.truckSecondary,
      roughness: 0.5,
    })
    const wheelMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.wheel,
      roughness: 0.8,
    })
    const glassMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.glass,
      roughness: 0.1,
      metalness: 0.9,
      transparent: true,
      opacity: 0.7,
    })
    const chassisMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.truckChassis,
      roughness: 0.7,
    })

    // Main cab body (6.0m × 2.4m × 2.8m)
    const cabGeom = new THREE.BoxGeometry(6.0, 2.8, 2.55)
    const cab = new THREE.Mesh(cabGeom, cabMaterial)
    cab.position.set(0, 1.9, 0)
    cab.castShadow = true
    cab.receiveShadow = true
    truck.add(cab)

    // Cab roof (slightly smaller, raised)
    const roofGeom = new THREE.BoxGeometry(2.5, 0.3, 2.4)
    const roof = new THREE.Mesh(roofGeom, darkMaterial)
    roof.position.set(-1.5, 3.45, 0)
    roof.castShadow = true
    truck.add(roof)

    // Windshield (angled front)
    const windshieldGeom = new THREE.BoxGeometry(0.1, 1.2, 2.2)
    const windshield = new THREE.Mesh(windshieldGeom, glassMaterial)
    windshield.position.set(-2.9, 2.5, 0)
    windshield.rotation.z = -0.2
    truck.add(windshield)

    // Front grille
    const grilleGeom = new THREE.BoxGeometry(0.3, 1.0, 2.3)
    const grille = new THREE.Mesh(grilleGeom, darkMaterial)
    grille.position.set(-3.0, 1.2, 0)
    grille.castShadow = true
    truck.add(grille)

    // Chassis frame (underneath)
    const frameGeom = new THREE.BoxGeometry(7.0, 0.4, 0.8)
    const frameL = new THREE.Mesh(frameGeom, chassisMaterial)
    frameL.position.set(0.5, 0.5, 0.8)
    truck.add(frameL)
    const frameR = new THREE.Mesh(frameGeom, chassisMaterial)
    frameR.position.set(0.5, 0.5, -0.8)
    truck.add(frameR)

    // Wheels (6 wheels: 2 front, 4 rear dual)
    const wheelGeom = new THREE.CylinderGeometry(0.5, 0.5, 0.35, 16)

    // Front wheels
    const wheelPositions = [
      { x: -2.0, z: 1.35 },   // Front left
      { x: -2.0, z: -1.35 },  // Front right
      { x: 1.5, z: 1.35 },    // Rear left outer
      { x: 1.5, z: 1.0 },     // Rear left inner
      { x: 1.5, z: -1.35 },   // Rear right outer
      { x: 1.5, z: -1.0 },    // Rear right inner
    ]

    wheelPositions.forEach(pos => {
      const wheel = new THREE.Mesh(wheelGeom, wheelMaterial)
      wheel.rotation.x = Math.PI / 2
      wheel.position.set(pos.x, 0.5, pos.z)
      wheel.castShadow = true
      truck.add(wheel)
    })

    // Side mirrors (small boxes)
    const mirrorGeom = new THREE.BoxGeometry(0.3, 0.4, 0.1)
    const mirrorL = new THREE.Mesh(mirrorGeom, darkMaterial)
    mirrorL.position.set(-2.0, 2.8, 1.4)
    truck.add(mirrorL)
    const mirrorR = new THREE.Mesh(mirrorGeom, darkMaterial)
    mirrorR.position.set(-2.0, 2.8, -1.4)
    truck.add(mirrorR)

    // Exhaust stack
    const exhaustGeom = new THREE.CylinderGeometry(0.08, 0.1, 1.5, 8)
    const exhaust = new THREE.Mesh(exhaustGeom, chassisMaterial)
    exhaust.position.set(1.0, 3.5, 1.3)
    truck.add(exhaust)

    // License plates (if plate number provided)
    if (plateNumber) {
      // Front plate - on the grille
      const frontPlate = createLicensePlate(plateNumber, false)
      frontPlate.position.set(-3.15, 0.9, 0)  // Front of truck, below grille
      truck.add(frontPlate)

      // Rear plate - on the back of the cab
      const rearPlate = createLicensePlate(plateNumber, true)
      rearPlate.position.set(3.0, 0.9, 0)  // Back of truck
      truck.add(rearPlate)
    }

    // Optionally add chassis
    if (withChassis) {
      const chassis = createChassisModel({ size: chassisSize })
      chassis.position.set(6.0 + (chassisSize === '40ft' ? 6.25 : 3.05), 0, 0)
      truck.add(chassis)
    }

    // Apply scale
    truck.scale.setScalar(scale)

    return truck
  }

  /**
   * Create a container chassis model
   */
  function createChassisModel(options: { size?: '20ft' | '40ft' } = {}): THREE.Group {
    const { size = '40ft' } = options
    const length = size === '40ft' ? 12.5 : 6.1

    const chassis = new THREE.Group()
    chassis.name = 'chassis'

    const frameMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.truckChassis,
      roughness: 0.7,
    })
    const wheelMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.wheel,
      roughness: 0.8,
    })

    // Main frame rails
    const railGeom = new THREE.BoxGeometry(length, 0.3, 0.2)
    const railL = new THREE.Mesh(railGeom, frameMaterial)
    railL.position.set(0, 1.2, 1.0)
    chassis.add(railL)
    const railR = new THREE.Mesh(railGeom, frameMaterial)
    railR.position.set(0, 1.2, -1.0)
    chassis.add(railR)

    // Cross members
    const crossCount = size === '40ft' ? 6 : 3
    const crossGeom = new THREE.BoxGeometry(0.15, 0.2, 2.2)
    for (let i = 0; i < crossCount; i++) {
      const x = -length / 2 + (length / (crossCount - 1)) * i
      const cross = new THREE.Mesh(crossGeom, frameMaterial)
      cross.position.set(x, 1.1, 0)
      chassis.add(cross)
    }

    // Wheels (triple axle for 40ft, dual for 20ft)
    const axleCount = size === '40ft' ? 3 : 2
    const wheelGeom = new THREE.CylinderGeometry(0.5, 0.5, 0.3, 16)

    for (let i = 0; i < axleCount; i++) {
      const x = length / 2 - 1.5 - i * 1.3
      // Left wheels (dual)
      const wl1 = new THREE.Mesh(wheelGeom, wheelMaterial)
      wl1.rotation.x = Math.PI / 2
      wl1.position.set(x, 0.5, 1.2)
      wl1.castShadow = true
      chassis.add(wl1)
      const wl2 = new THREE.Mesh(wheelGeom, wheelMaterial)
      wl2.rotation.x = Math.PI / 2
      wl2.position.set(x, 0.5, 0.85)
      chassis.add(wl2)
      // Right wheels (dual)
      const wr1 = new THREE.Mesh(wheelGeom, wheelMaterial)
      wr1.rotation.x = Math.PI / 2
      wr1.position.set(x, 0.5, -1.2)
      wr1.castShadow = true
      chassis.add(wr1)
      const wr2 = new THREE.Mesh(wheelGeom, wheelMaterial)
      wr2.rotation.x = Math.PI / 2
      wr2.position.set(x, 0.5, -0.85)
      chassis.add(wr2)
    }

    return chassis
  }

  /**
   * Create a low-poly car model
   * Dimensions: 4.5m length × 1.8m width × 1.6m height
   */
  function createCarModel(options: VehicleModelOptions = {}): THREE.Group {
    const {
      color = VEHICLE_COLORS.carColors[Math.floor(Math.random() * VEHICLE_COLORS.carColors.length)],
      scale = 1.0,
      plateNumber,
    } = options

    const car = new THREE.Group()
    car.name = 'car'

    const bodyMaterial = new THREE.MeshStandardMaterial({
      color,
      roughness: 0.3,
      metalness: 0.4,
    })
    const glassMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.glass,
      roughness: 0.1,
      metalness: 0.9,
      transparent: true,
      opacity: 0.6,
    })
    const wheelMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.wheel,
      roughness: 0.8,
    })

    // Main body (lower part)
    const bodyGeom = new THREE.BoxGeometry(4.5, 0.8, 1.8)
    const body = new THREE.Mesh(bodyGeom, bodyMaterial)
    body.position.set(0, 0.7, 0)
    body.castShadow = true
    body.receiveShadow = true
    car.add(body)

    // Cabin (upper part, smaller)
    const cabinGeom = new THREE.BoxGeometry(2.2, 0.7, 1.6)
    const cabin = new THREE.Mesh(cabinGeom, bodyMaterial)
    cabin.position.set(-0.3, 1.45, 0)
    cabin.castShadow = true
    car.add(cabin)

    // Windshield (angled)
    const wsGeom = new THREE.BoxGeometry(0.6, 0.6, 1.5)
    const windshield = new THREE.Mesh(wsGeom, glassMaterial)
    windshield.position.set(-1.5, 1.3, 0)
    windshield.rotation.z = -0.4
    car.add(windshield)

    // Rear window
    const rwGeom = new THREE.BoxGeometry(0.4, 0.5, 1.4)
    const rearWindow = new THREE.Mesh(rwGeom, glassMaterial)
    rearWindow.position.set(0.9, 1.35, 0)
    rearWindow.rotation.z = 0.3
    car.add(rearWindow)

    // Wheels (4)
    const wheelGeom = new THREE.CylinderGeometry(0.35, 0.35, 0.25, 16)
    const wheelPositions = [
      { x: -1.4, z: 0.95 },
      { x: -1.4, z: -0.95 },
      { x: 1.4, z: 0.95 },
      { x: 1.4, z: -0.95 },
    ]
    wheelPositions.forEach(pos => {
      const wheel = new THREE.Mesh(wheelGeom, wheelMaterial)
      wheel.rotation.x = Math.PI / 2
      wheel.position.set(pos.x, 0.35, pos.z)
      wheel.castShadow = true
      car.add(wheel)
    })

    // Headlights (small emissive boxes)
    const headlightGeom = new THREE.BoxGeometry(0.1, 0.15, 0.3)
    const headlightMaterial = new THREE.MeshStandardMaterial({
      color: 0xFFFFAA,
      emissive: 0xFFFFAA,
      emissiveIntensity: 0.3,
    })
    const hlL = new THREE.Mesh(headlightGeom, headlightMaterial)
    hlL.position.set(-2.25, 0.7, 0.6)
    car.add(hlL)
    const hlR = new THREE.Mesh(headlightGeom, headlightMaterial)
    hlR.position.set(-2.25, 0.7, -0.6)
    car.add(hlR)

    // License plates (if plate number provided)
    if (plateNumber) {
      // Front plate - below headlights
      const frontPlate = createLicensePlate(plateNumber, false)
      frontPlate.position.set(-2.26, 0.45, 0)  // Front bumper area
      car.add(frontPlate)

      // Rear plate - on the back
      const rearPlate = createLicensePlate(plateNumber, true)
      rearPlate.position.set(2.26, 0.45, 0)  // Rear bumper area
      car.add(rearPlate)
    }

    car.scale.setScalar(scale)

    return car
  }

  /**
   * Create a railway flat wagon model
   * Dimensions: 16.4m length × 3.0m width × 1.4m height (NX70 standard)
   */
  function createWagonModel(options: VehicleModelOptions = {}): THREE.Group {
    const { scale = 1.0 } = options

    const wagon = new THREE.Group()
    wagon.name = 'wagon'

    const deckMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.wagonDeck,
      roughness: 0.8,
    })
    const metalMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.wagonMetal,
      roughness: 0.6,
      metalness: 0.4,
    })
    const wheelMaterial = new THREE.MeshStandardMaterial({
      color: VEHICLE_COLORS.wheel,
      roughness: 0.7,
    })

    // Main deck platform
    const deckGeom = new THREE.BoxGeometry(16.4, 0.3, 2.8)
    const deck = new THREE.Mesh(deckGeom, deckMaterial)
    deck.position.set(0, 1.2, 0)
    deck.castShadow = true
    deck.receiveShadow = true
    wagon.add(deck)

    // Side rails
    const railGeom = new THREE.BoxGeometry(16.4, 0.15, 0.1)
    const railL = new THREE.Mesh(railGeom, metalMaterial)
    railL.position.set(0, 1.42, 1.45)
    wagon.add(railL)
    const railR = new THREE.Mesh(railGeom, metalMaterial)
    railR.position.set(0, 1.42, -1.45)
    wagon.add(railR)

    // End rails
    const endRailGeom = new THREE.BoxGeometry(0.1, 0.15, 2.8)
    const endF = new THREE.Mesh(endRailGeom, metalMaterial)
    endF.position.set(-8.15, 1.42, 0)
    wagon.add(endF)
    const endB = new THREE.Mesh(endRailGeom, metalMaterial)
    endB.position.set(8.15, 1.42, 0)
    wagon.add(endB)

    // Bogies (wheel assemblies) - 2 sets
    const bogiePositions = [-5.5, 5.5]
    const wheelGeom = new THREE.CylinderGeometry(0.45, 0.45, 0.2, 16)

    bogiePositions.forEach(bogieX => {
      // Bogie frame
      const bogieFrame = new THREE.BoxGeometry(2.5, 0.25, 2.2)
      const bogie = new THREE.Mesh(bogieFrame, metalMaterial)
      bogie.position.set(bogieX, 0.7, 0)
      wagon.add(bogie)

      // 4 wheels per bogie
      const wheelOffsets = [
        { x: -0.8, z: 0.9 },
        { x: -0.8, z: -0.9 },
        { x: 0.8, z: 0.9 },
        { x: 0.8, z: -0.9 },
      ]
      wheelOffsets.forEach(offset => {
        const wheel = new THREE.Mesh(wheelGeom, wheelMaterial)
        wheel.rotation.x = Math.PI / 2
        wheel.position.set(bogieX + offset.x, 0.45, offset.z)
        wheel.castShadow = true
        wagon.add(wheel)
      })
    })

    // Buffer/coupler ends
    const bufferGeom = new THREE.CylinderGeometry(0.15, 0.15, 0.4, 8)
    const bufferPositions = [
      { x: -8.3, z: 0.8 },
      { x: -8.3, z: -0.8 },
      { x: 8.3, z: 0.8 },
      { x: 8.3, z: -0.8 },
    ]
    bufferPositions.forEach(pos => {
      const buffer = new THREE.Mesh(bufferGeom, metalMaterial)
      buffer.rotation.z = Math.PI / 2
      buffer.position.set(pos.x, 0.9, pos.z)
      wagon.add(buffer)
    })

    wagon.scale.setScalar(scale)

    return wagon
  }

  /**
   * Factory function to create any vehicle type
   */
  function createVehicle(type: VehicleType, options: VehicleModelOptions = {}): THREE.Group {
    switch (type) {
      case 'TRUCK':
        return createTruckModel(options)
      case 'CAR':
        return createCarModel(options)
      case 'WAGON':
        return createWagonModel(options)
      default:
        // Unknown type - return a simple placeholder box
        const placeholder = new THREE.Group()
        placeholder.name = 'unknown-vehicle'
        const boxGeom = new THREE.BoxGeometry(4, 2, 2)
        const boxMat = new THREE.MeshStandardMaterial({ color: 0x888888 })
        const box = new THREE.Mesh(boxGeom, boxMat)
        box.position.y = 1
        placeholder.add(box)
        return placeholder
    }
  }

  /**
   * Dispose of all geometries and materials in a vehicle group
   */
  function disposeVehicle(vehicle: THREE.Group): void {
    vehicle.traverse(child => {
      if (child instanceof THREE.Mesh) {
        child.geometry.dispose()
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.dispose())
        } else {
          child.material.dispose()
        }
      }
    })
  }

  return {
    createTruckModel,
    createChassisModel,
    createCarModel,
    createWagonModel,
    createVehicle,
    createLicensePlate,
    disposeVehicle,
    VEHICLE_COLORS,
  }
}
