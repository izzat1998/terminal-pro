/**
 * coordinateParser - Parse terminal coordinate strings to Position objects
 *
 * Format: "A-R03-B15-T2-A"
 *   - Zone: A (single letter)
 *   - Row: R03 (R + 2-digit number)
 *   - Bay: B15 (B + 2-digit number)
 *   - Tier: T2 (T + 1-digit number)
 *   - SubSlot: A or B (for 20ft container placement)
 *
 * Used for navigation from Tasks page to 3D view with camera focus.
 */

import type { Position, ZoneCode, SubSlot } from '../types/placement';

// Regex to parse coordinate format: A-R03-B15-T2-A
// Groups: zone, row, bay, tier, sub_slot
const COORDINATE_REGEX = /^([A-E])-R(\d{2})-B(\d{2})-T(\d)-([AB])$/;

/**
 * Parse a coordinate string into a Position object.
 *
 * @param coordinate - Coordinate string like "A-R03-B15-T2-A"
 * @returns Position object or null if invalid format
 *
 * @example
 * parseCoordinate("A-R03-B15-T2-A")
 * // => { zone: 'A', row: 3, bay: 15, tier: 2, sub_slot: 'A', coordinate: 'A-R03-B15-T2-A' }
 */
export function parseCoordinate(coordinate: string): Position | null {
  if (!coordinate) return null;

  const match = coordinate.match(COORDINATE_REGEX);
  if (!match) return null;

  // Extract groups from regex match (indices 1-5)
  const zone = match[1];
  const row = match[2];
  const bay = match[3];
  const tier = match[4];
  const subSlot = match[5];

  // Ensure all parts are present
  if (!zone || !row || !bay || !tier || !subSlot) return null;

  return {
    zone: zone as ZoneCode,
    row: parseInt(row, 10),
    bay: parseInt(bay, 10),
    tier: parseInt(tier, 10),
    sub_slot: subSlot as SubSlot,
    coordinate,
  };
}

/**
 * Format a Position object into a coordinate string.
 *
 * @param position - Position object
 * @returns Formatted coordinate string like "A-R03-B15-T2-A"
 *
 * @example
 * formatCoordinate({ zone: 'A', row: 3, bay: 15, tier: 2, sub_slot: 'A' })
 * // => "A-R03-B15-T2-A"
 */
export function formatCoordinate(position: Position): string {
  const row = position.row.toString().padStart(2, '0');
  const bay = position.bay.toString().padStart(2, '0');
  return `${position.zone}-R${row}-B${bay}-T${position.tier}-${position.sub_slot}`;
}

/**
 * Validate if a string is a valid coordinate format.
 *
 * @param coordinate - String to validate
 * @returns true if valid coordinate format
 */
export function isValidCoordinate(coordinate: string): boolean {
  return COORDINATE_REGEX.test(coordinate);
}
