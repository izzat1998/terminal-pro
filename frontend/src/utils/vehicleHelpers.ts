/**
 * Vehicle-related utility functions for КПП (Checkpoint Journal)
 * Extracted from Vehicles.vue for testability
 */

// Types
export interface ChoiceOption {
  value: string
  label: string
}

export type VehicleStatus = 'WAITING' | 'ON_TERMINAL' | 'EXITED' | 'CANCELLED'
export type VehicleType = 'LIGHT' | 'CARGO'
export type LoadStatus = 'LOADED' | 'EMPTY'
export type CargoType = 'CONTAINER' | 'FOOD' | 'METAL' | 'WOOD' | 'CHEMICAL' | 'EQUIPMENT' | 'OTHER'
export type TransportType = 'PLATFORM' | 'TRUCK' | 'TRAILER' | 'MINI_TRUCK' | 'ZIL' | 'GAZELLE' | 'LABO'

// Container-capable transport types
export const CONTAINER_CAPABLE_TRANSPORTS: TransportType[] = ['PLATFORM', 'TRUCK', 'TRAILER']

/**
 * Get the color for a vehicle status tag
 */
export function getStatusColor(status: string): string {
  switch (status) {
    case 'WAITING':
      return 'orange'
    case 'ON_TERMINAL':
      return 'success'
    case 'EXITED':
      return 'blue'
    case 'CANCELLED':
      return 'red'
    default:
      return 'default'
  }
}

/**
 * Get the display label for a choice value
 */
export function getChoiceLabel(choiceList: ChoiceOption[], value: string | null): string {
  if (!value) return '—'
  const found = choiceList.find((c) => c.value === value)
  return found ? found.label : value
}

/**
 * Determine if a vehicle form should show LIGHT vehicle fields
 */
export function isLightVehicle(vehicleType: string | null): boolean {
  return vehicleType === 'LIGHT'
}

/**
 * Determine if a vehicle form should show CARGO vehicle fields
 */
export function isCargoVehicle(vehicleType: string | null): boolean {
  return vehicleType === 'CARGO'
}

/**
 * Determine if cargo is loaded (shows cargo type field)
 */
export function isCargoLoaded(loadStatus: string | null): boolean {
  return loadStatus === 'LOADED'
}

/**
 * Determine if cargo type is container (shows container fields)
 */
export function isContainerCargo(cargoType: string | null): boolean {
  return cargoType === 'CONTAINER'
}

/**
 * Determine if transport type can carry containers
 */
export function isContainerCapableTransport(transportType: string | null): boolean {
  if (!transportType) return false
  return CONTAINER_CAPABLE_TRANSPORTS.includes(transportType as TransportType)
}

/**
 * Determine which cargo fields should be visible based on form state
 */
export interface CargoFormState {
  vehicleType: string | null
  loadStatus: string | null
  cargoType: string | null
  transportType: string | null
}

export interface CargoFieldVisibility {
  showVisitorType: boolean
  showTransportType: boolean
  showLoadStatus: boolean
  showCargoType: boolean
  showContainerFields: boolean
  showDestination: boolean
}

export function getCargoFieldVisibility(state: CargoFormState): CargoFieldVisibility {
  const isLight = isLightVehicle(state.vehicleType)
  const isCargo = isCargoVehicle(state.vehicleType)
  const isLoaded = isCargoLoaded(state.loadStatus)
  const isContainer = isContainerCargo(state.cargoType)
  const canCarryContainer = isContainerCapableTransport(state.transportType)

  return {
    showVisitorType: isLight,
    showTransportType: isCargo,
    showLoadStatus: isCargo,
    showCargoType: isCargo && isLoaded,
    showContainerFields: isCargo && isLoaded && isContainer && canCarryContainer,
    showDestination: isCargo,
  }
}

/**
 * Check if a vehicle can be exited (must be ON_TERMINAL)
 */
export function canExitVehicle(status: string): boolean {
  return status === 'ON_TERMINAL'
}

/**
 * Check if a vehicle can be reverted (must be EXITED)
 */
export function canRevertVehicle(status: string): boolean {
  return status === 'EXITED'
}

/**
 * Check if a vehicle can be cancelled (must be WAITING)
 */
export function canCancelVehicle(status: string): boolean {
  return status === 'WAITING'
}

/**
 * Format dwell time hours for display
 */
export function formatDwellTime(hours: number | null): string {
  if (hours === null || hours === undefined) return '—'
  return hours.toFixed(1)
}
