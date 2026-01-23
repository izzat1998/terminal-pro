/**
 * Type definitions for DXF parsing and Three.js conversion
 * Based on dxf-parser library structure
 */

// Base entity interface
export interface DxfEntity {
  type: string
  handle: string
  layer: string
  lineType?: string
  lineWeight?: number
  colorIndex?: number
}

// LINE entity
export interface DxfLine extends DxfEntity {
  type: 'LINE'
  vertices: [DxfPoint, DxfPoint]
}

// LWPOLYLINE entity (lightweight polyline)
export interface DxfLwPolyline extends DxfEntity {
  type: 'LWPOLYLINE'
  vertices: DxfPolylineVertex[]
  shape: boolean // closed shape
  elevation?: number
}

// POLYLINE entity
export interface DxfPolyline extends DxfEntity {
  type: 'POLYLINE'
  vertices: DxfPolylineVertex[]
  shape: boolean
}

// CIRCLE entity
export interface DxfCircle extends DxfEntity {
  type: 'CIRCLE'
  center: DxfPoint
  radius: number
}

// ARC entity
export interface DxfArc extends DxfEntity {
  type: 'ARC'
  center: DxfPoint
  radius: number
  startAngle: number
  endAngle: number
}

// INSERT entity (block reference)
export interface DxfInsert extends DxfEntity {
  type: 'INSERT'
  name: string
  position: DxfPoint
  xScale?: number
  yScale?: number
  zScale?: number
  rotation?: number
}

// TEXT entity
export interface DxfText extends DxfEntity {
  type: 'TEXT'
  startPoint: DxfPoint
  text: string
  textHeight?: number
  rotation?: number
}

// MTEXT entity (multiline text)
export interface DxfMText extends DxfEntity {
  type: 'MTEXT'
  position: DxfPoint
  text: string
  height?: number
  width?: number
  rotation?: number
}

// HATCH entity
export interface DxfHatch extends DxfEntity {
  type: 'HATCH'
  patternName: string
  solid: boolean
  boundaryPaths: DxfBoundaryPath[]
}

// SPLINE entity
export interface DxfSpline extends DxfEntity {
  type: 'SPLINE'
  controlPoints: DxfPoint[]
  fitPoints: DxfPoint[]
  knotValues: number[]
  degree: number
}

// DIMENSION entity
export interface DxfDimension extends DxfEntity {
  type: 'DIMENSION'
  block: string
  anchorPoint: DxfPoint
  middleOfText: DxfPoint
  insertionPoint?: DxfPoint
  linearOrAngularPoint1?: DxfPoint
  linearOrAngularPoint2?: DxfPoint
  dimensionType: number
  text?: string
  rotation?: number
}

// SOLID entity (filled triangle/quad)
export interface DxfSolid extends DxfEntity {
  type: 'SOLID'
  points: [DxfPoint, DxfPoint, DxfPoint, DxfPoint?]
}

// ELLIPSE entity
export interface DxfEllipse extends DxfEntity {
  type: 'ELLIPSE'
  center: DxfPoint
  majorAxisEndPoint: DxfPoint
  axisRatio: number
  startAngle: number
  endAngle: number
}

// Point coordinates
export interface DxfPoint {
  x: number
  y: number
  z?: number
}

// Polyline vertex with optional bulge
export interface DxfPolylineVertex extends DxfPoint {
  bulge?: number // Arc bulge factor
}

// Boundary path for hatches
export interface DxfBoundaryPath {
  type: number
  polylines?: DxfPolylineVertex[][]
  lines?: { start: DxfPoint; end: DxfPoint }[]
  arcs?: { center: DxfPoint; radius: number; startAngle: number; endAngle: number }[]
}

// Block definition
export interface DxfBlock {
  name: string
  handle: string
  layer: string
  position: DxfPoint
  entities: DxfAnyEntity[]
}

// Layer definition
export interface DxfLayer {
  name: string
  color: number
  visible: boolean
  frozen: boolean
  lineType?: string
}

// Union of all entity types
export type DxfAnyEntity =
  | DxfLine
  | DxfLwPolyline
  | DxfPolyline
  | DxfCircle
  | DxfArc
  | DxfInsert
  | DxfText
  | DxfMText
  | DxfHatch
  | DxfSpline
  | DxfDimension
  | DxfSolid
  | DxfEllipse

// Header variables from DXF
export interface DxfHeader {
  $ACADVER?: string
  $EXTMIN?: DxfPoint
  $EXTMAX?: DxfPoint
  $LIMMIN?: DxfPoint
  $LIMMAX?: DxfPoint
  $INSUNITS?: number  // Drawing units (see DXF_UNIT_SCALES)
  [key: string]: unknown
}

// Complete parsed DXF structure
export interface ParsedDxf {
  header: DxfHeader
  entities: DxfAnyEntity[]
  blocks: Record<string, DxfBlock>
  layers: Record<string, DxfLayer>
}

// Conversion options for Three.js
export interface DxfConversionOptions {
  /** Scale factor (default: 1) */
  scale?: number
  /** Center the geometry at origin (default: true) */
  centerAtOrigin?: boolean
  /** Default color for entities without explicit color (default: 0x333333) */
  defaultColor?: number
  /** Layer color mapping */
  layerColors?: Record<string, number>
  /** Layers to exclude from rendering */
  excludeLayers?: string[]
  /** Line width for rendering (default: 1) */
  lineWidth?: number
  /** Flatten Z coordinate to 0 for 2D drawings (default: true) */
  flatten2D?: boolean
}

// Statistics about parsed DXF
export interface DxfStats {
  entityCount: {
    total: number
    byType: Record<string, number>
  }
  bounds: {
    min: DxfPoint
    max: DxfPoint
    width: number
    height: number
    depth: number
  }
  layerCount: number
  blockCount: number
}

/**
 * DXF Coordinate System - for bidirectional transforms between DXF and Three.js
 * Used to ensure consistent coordinate mapping across all components
 */
export interface DxfCoordinateSystem {
  /** Center point in DXF coordinates (used for origin alignment) */
  center: DxfPoint
  /** Scale factor applied to convert DXF units to world units */
  scale: number
  /** Original DXF unit system (from INSUNITS header) */
  units: number
  /** Bounds in DXF coordinates */
  bounds: {
    min: DxfPoint
    max: DxfPoint
    width: number
    height: number
  }
}

/**
 * DXF INSUNITS values to scale factors (converting to meters)
 * Reference: AutoCAD DXF documentation
 */
export const DXF_UNIT_SCALES: Record<number, number> = {
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
  11: 1.0e-10,  // Angstroms → meters
  12: 1.0e-9,   // Nanometers → meters
  13: 1.0e-6,   // Microns → meters
  14: 0.1,      // Decimeters → meters
  15: 10.0,     // Decameters → meters
  16: 100.0,    // Hectometers → meters
  17: 1.0e12,   // Gigameters → meters
  18: 1.496e11, // Astronomical units → meters
  19: 9.461e15, // Light years → meters
  20: 3.086e16, // Parsecs → meters
}

// AutoCAD color index to hex mapping (ACI) - Extended palette
export const ACI_COLORS: Record<number, number> = {
  0: 0x000000,   // ByBlock
  1: 0xff0000,   // Red
  2: 0xffff00,   // Yellow
  3: 0x00ff00,   // Green
  4: 0x00ffff,   // Cyan
  5: 0x0000ff,   // Blue
  6: 0xff00ff,   // Magenta
  7: 0xffffff,   // White (or black in light theme)
  8: 0x414141,   // Dark gray
  9: 0x808080,   // Gray
  // Extended colors 10-255 (commonly used subset)
  10: 0xff0000,  11: 0xff7f7f,  12: 0xa50000,  13: 0xa55252,  14: 0x7f0000,
  15: 0x7f3f3f,  16: 0x4c0000,  17: 0x4c2626,  18: 0x260000,  19: 0x261313,
  20: 0xff3f00,  21: 0xff9f7f,  22: 0xa52900,  23: 0xa56852,  24: 0x7f1f00,
  25: 0x7f4f3f,  26: 0x4c1300,  27: 0x4c2f26,  28: 0x260900,  29: 0x261713,
  30: 0xff7f00,  31: 0xffbf7f,  32: 0xa55200,  33: 0xa57d52,  34: 0x7f3f00,
  35: 0x7f5f3f,  36: 0x4c2600,  37: 0x4c3926,  38: 0x261300,  39: 0x261c13,
  40: 0xffbf00,  41: 0xffdf7f,  42: 0xa57c00,  43: 0xa59152,  44: 0x7f5f00,
  45: 0x7f6f3f,  46: 0x4c3900,  47: 0x4c4226,  48: 0x261c00,  49: 0x262113,
  50: 0xffff00,  51: 0xffff7f,  52: 0xa5a500,  53: 0xa5a552,  54: 0x7f7f00,
  55: 0x7f7f3f,  56: 0x4c4c00,  57: 0x4c4c26,  58: 0x262600,  59: 0x262613,
  60: 0xbfff00,  61: 0xdfff7f,  62: 0x7ca500,  63: 0x91a552,  64: 0x5f7f00,
  65: 0x6f7f3f,  66: 0x394c00,  67: 0x424c26,  68: 0x1c2600,  69: 0x212613,
  70: 0x7fff00,  71: 0xbfff7f,  72: 0x52a500,  73: 0x7da552,  74: 0x3f7f00,
  75: 0x5f7f3f,  76: 0x264c00,  77: 0x394c26,  78: 0x132600,  79: 0x1c2613,
  80: 0x3fff00,  81: 0x9fff7f,  82: 0x29a500,  83: 0x68a552,  84: 0x1f7f00,
  85: 0x4f7f3f,  86: 0x134c00,  87: 0x2f4c26,  88: 0x092600,  89: 0x172613,
  90: 0x00ff00,  91: 0x7fff7f,  92: 0x00a500,  93: 0x52a552,  94: 0x007f00,
  95: 0x3f7f3f,  96: 0x004c00,  97: 0x264c26,  98: 0x002600,  99: 0x132613,
  // Continue with cyan-green to blue range
  100: 0x00ff3f, 110: 0x00ff7f, 120: 0x00ffbf, 130: 0x00ffff, 140: 0x00bfff,
  150: 0x007fff, 160: 0x003fff, 170: 0x0000ff, 180: 0x3f00ff, 190: 0x7f00ff,
  200: 0xbf00ff, 210: 0xff00ff, 220: 0xff00bf, 230: 0xff007f, 240: 0xff003f,
  // Grays
  250: 0x333333, 251: 0x505050, 252: 0x696969, 253: 0x828282, 254: 0xbebebe, 255: 0xffffff,
  256: 0x000000, // ByLayer
}

/**
 * Get ACI color with fallback to default
 */
export function getAciColor(colorIndex: number, defaultColor: number = 0x333333): number {
  return ACI_COLORS[colorIndex] ?? defaultColor
}
