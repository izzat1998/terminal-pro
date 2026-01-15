/**
 * TypeScript types for 3D Terminal Placement feature
 */

// Zone codes for the terminal
// Currently only Zone A for simplified version
// Type allows future expansion to B-E
export type ZoneCode = 'A' | 'B' | 'C' | 'D' | 'E';

// Legacy type alias for backward compatibility
export type AllZoneCodes = ZoneCode;

// Sub-slot for bay subdivision (20ft containers)
export type SubSlot = 'A' | 'B';

// Position coordinates
export interface Position {
  zone: ZoneCode;
  row: number;  // 1-10
  bay: number;  // 1-10
  tier: number; // 1-4
  sub_slot: SubSlot; // A (left) or B (right) - for 20ft containers sharing a bay
  coordinate?: string; // Formatted: "A-R03-B15-T2-A"
}

// Container with position (for 3D rendering)
export interface ContainerPlacement {
  id: number;
  container_number: string;
  iso_type: string;
  status: 'LADEN' | 'EMPTY';
  position: Position;
  entry_time: string;
  dwell_time_days: number;
  company_name: string;
}

// Terminal dimensions
export interface TerminalDimensions {
  max_rows: number;
  max_bays: number;
  max_tiers: number;
}

// Zone statistics
export interface ZoneStats {
  occupied: number;
  available: number;
}

// Overall terminal statistics
export interface PlacementStats {
  total_capacity: number;
  occupied: number;
  available: number;
  by_zone: Record<ZoneCode, ZoneStats>;
}

// Complete layout response from API
export interface PlacementLayout {
  zones: ZoneCode[];
  dimensions: TerminalDimensions;
  containers: ContainerPlacement[];
  stats: PlacementStats;
}

// Auto-suggest response
export interface SuggestionResponse {
  suggested_position: Position;
  reason: string;
  alternatives: Position[];
}

// Container without position (needs placement)
export interface UnplacedContainer {
  id: number;
  container_number: string;
  iso_type: string;
  status: 'LADEN' | 'EMPTY';
  entry_time: string;
  dwell_time_days: number;
  company_name: string;
}

// Company statistics for filtering UI
export interface CompanyStats {
  name: string;
  containerCount: number;
  ladenCount: number;
  emptyCount: number;
}

// Container position record from API
export interface ContainerPositionRecord {
  id: number;
  container_entry: number;
  container_number: string;
  zone: ZoneCode;
  row: number;
  bay: number;
  tier: number;
  coordinate: string;
  auto_assigned: boolean;
  created_at: string;
  updated_at: string;
}

// API response wrappers (placement-specific, uses boolean instead of literal true)
// Note: Differs from types/api.ts ApiResponse which uses `success: true` for discriminated unions
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface ApiListResponse<T> {
  success: boolean;
  data: T[];
  count: number;
}

// Container size type
export type ContainerSize = '20ft' | '40ft' | '45ft';

// 3D rendering constants - ISO standard dimensions (scaled for visibility)
export const CONTAINER_DIMENSIONS = {
  // Standard height containers (8'6" = 2.591m)
  '20ft': { length: 6.1, width: 2.4, height: 2.6 },
  '40ft': { length: 12.2, width: 2.4, height: 2.6 },
  '45ft': { length: 13.7, width: 2.4, height: 2.6 },
  // High Cube containers (9'6" = 2.896m) - ~12% taller
  '20ft_HC': { length: 6.1, width: 2.4, height: 2.9 },
  '40ft_HC': { length: 12.2, width: 2.4, height: 2.9 },
  '45ft_HC': { length: 13.7, width: 2.4, height: 2.9 },
} as const;

// Get container size from ISO type (first character)
export function getContainerSize(isoType: string): ContainerSize {
  const firstChar = isoType.charAt(0);
  switch (firstChar) {
    case '2':
      return '20ft';
    case '4':
      return '40ft';
    case 'L':
    case '9':
      return '45ft';
    default:
      return '20ft';
  }
}

// Check if container is High Cube (second character is 5 or 9)
// ISO codes: 22G1 = standard, 25G1/45G1 = high cube
export function isHighCube(isoType: string): boolean {
  if (isoType.length < 2) return false;
  const secondChar = isoType.charAt(1);
  return secondChar === '5' || secondChar === '9';
}

// Get full dimension key including HC status
export function getContainerDimensionKey(isoType: string): keyof typeof CONTAINER_DIMENSIONS {
  const size = getContainerSize(isoType);
  const hc = isHighCube(isoType);
  return hc ? `${size}_HC` as keyof typeof CONTAINER_DIMENSIONS : size;
}

// Colors for container status
// Base colors (used when size distinction is not needed)
export const CONTAINER_COLORS = {
  LADEN: 0x52c41a,   // Green
  EMPTY: 0x1677ff,   // Blue
  SELECTED: 0xfaad14, // Gold
  HOVERED: 0xfa8c16,  // Orange
} as const;

// Size-variant colors: 20ft = bright, 40ft = darker (same hue, different saturation/lightness)
// This follows TOS industry best practice: size as secondary visual channel via saturation
export const CONTAINER_SIZE_COLORS = {
  // Laden containers (green family)
  LADEN_20: 0x73d13d,  // Bright green - HSL(96, 64%, 53%)
  LADEN_40: 0x237804,  // Dark green - HSL(102, 94%, 24%)
  // Empty containers (blue family)
  EMPTY_20: 0x40a9ff,  // Bright blue - HSL(209, 100%, 63%)
  EMPTY_40: 0x003eb3,  // Dark blue - HSL(221, 100%, 35%)
} as const;

// Edge colors for container outlines (darker versions for contrast)
export const CONTAINER_EDGE_COLORS = {
  LADEN_20: 0x389e0d,  // Medium-dark green
  LADEN_40: 0x135200,  // Very dark green
  EMPTY_20: 0x096dd9,  // Medium-dark blue
  EMPTY_40: 0x002766,  // Very dark blue
} as const;

// Get color based on status and size
export function getContainerColor(isLaden: boolean, size: ContainerSize): number {
  if (isLaden) {
    return size === '20ft' ? CONTAINER_SIZE_COLORS.LADEN_20 : CONTAINER_SIZE_COLORS.LADEN_40;
  }
  return size === '20ft' ? CONTAINER_SIZE_COLORS.EMPTY_20 : CONTAINER_SIZE_COLORS.EMPTY_40;
}

// Get edge color based on status and size
export function getContainerEdgeColor(isLaden: boolean, size: ContainerSize): number {
  if (isLaden) {
    return size === '20ft' ? CONTAINER_EDGE_COLORS.LADEN_20 : CONTAINER_EDGE_COLORS.LADEN_40;
  }
  return size === '20ft' ? CONTAINER_EDGE_COLORS.EMPTY_20 : CONTAINER_EDGE_COLORS.EMPTY_40;
}

// Dwell time heatmap colors (professional TOS standard)
export const DWELL_TIME_COLORS = {
  FRESH: 0x52c41a,    // Green - 0-3 days
  NORMAL: 0xfadb14,   // Yellow - 4-7 days
  AGING: 0xfa8c16,    // Orange - 8-14 days
  OVERDUE: 0xf5222d,  // Red - 15-21 days
  CRITICAL: 0x722ed1, // Purple - 21+ days
} as const;

// Color mode for container rendering
export type ColorMode = 'status' | 'dwell_time';

// Get color based on dwell time (days in yard)
export function getDwellTimeColor(dwellDays: number): number {
  if (dwellDays <= 3) return DWELL_TIME_COLORS.FRESH;
  if (dwellDays <= 7) return DWELL_TIME_COLORS.NORMAL;
  if (dwellDays <= 14) return DWELL_TIME_COLORS.AGING;
  if (dwellDays <= 21) return DWELL_TIME_COLORS.OVERDUE;
  return DWELL_TIME_COLORS.CRITICAL;
}

// Spacing between containers (meters) - sized for 40ft containers
// Bay spacing MUST accommodate 40ft containers (12.2m) to prevent overlap
//
// Container dimensions:
//   - 20ft: 6.1m length × 2.4m width × 2.6m height (2.9m for HC)
//   - 40ft: 12.2m length × 2.4m width × 2.6m height (2.9m for HC)
//
// Spacing calculation:
//   - Bay (X): 13.0m spacing - 12.2m (40ft) = 0.8m gap (0.4m each side)
//   - Row (Z): 3.0m spacing - 2.4m width = 0.6m gap (0.3m each side)
//   - Tier (Y): 3.2m spacing - 2.9m HC height = 0.3m gap
//
// Note: 20ft containers will have larger gaps (13.0 - 6.1 = 6.9m), but this
// is correct because in real terminals 40ft containers occupy 2× the bay space
//
export const SPACING = {
  bay: 13.0,   // X direction - sized for 40ft containers (12.2m + 0.8m gap)
  row: 3.0,    // Z direction - subtle front/back separation
  tier: 3.2,   // Y direction - thin line between stacked containers
  gap: 0.4,    // Minimum visual gap (reference value)
} as const;

// Zone layout positions in meters
// Currently only Zone A for simplified version
// X direction: 10 bays × 13.0m = 130m per zone
// Z direction: 10 rows × 3.0m = 30m per zone
export const ZONE_LAYOUT: Partial<Record<ZoneCode, { xOffset: number; zOffset: number }>> = {
  A: { xOffset: 0, zOffset: 0 },
} as const;

// Full zone layout for future expansion
export const FULL_ZONE_LAYOUT: Partial<Record<ZoneCode, { xOffset: number; zOffset: number }>> = {
  A: { xOffset: 0, zOffset: 0 },
  B: { xOffset: 140, zOffset: 0 },   // 130m zone + 10m gap
  C: { xOffset: 280, zOffset: 0 },   // (130m + 10m) × 2
  D: { xOffset: 0, zOffset: 40 },    // 30m zone + 10m gap
  E: { xOffset: 140, zOffset: 40 },
} as const;
