/**
 * Terminal Vehicle Types
 *
 * Types for terminal vehicles (yard equipment) management and status display.
 */

// ============ Vehicle Type Constants ============

/**
 * Vehicle type enum values matching backend choices
 */
export type VehicleType = 'REACH_STACKER' | 'FORKLIFT' | 'YARD_TRUCK' | 'RTG_CRANE'

/**
 * Vehicle type options for dropdowns (Russian labels)
 */
export const VEHICLE_TYPE_OPTIONS: { value: VehicleType; label: string }[] = [
  { value: 'REACH_STACKER', label: 'Ричстакер' },
  { value: 'FORKLIFT', label: 'Погрузчик' },
  { value: 'YARD_TRUCK', label: 'Тягач' },
  { value: 'RTG_CRANE', label: 'Козловой кран (RTG)' },
]

// ============ Operator Types ============

/**
 * Operator info nested in vehicle response
 */
export interface VehicleOperator {
  id: number
  full_name: string
}

// ============ Vehicle CRUD Types ============

/**
 * Terminal vehicle for management views (full data)
 */
export interface TerminalVehicle {
  id: number
  name: string
  vehicle_type: VehicleType
  vehicle_type_display: string
  license_plate: string
  is_active: boolean
  operator: VehicleOperator | null
}

/**
 * Request body for creating a terminal vehicle
 */
export interface TerminalVehicleCreateRequest {
  name: string
  vehicle_type: VehicleType
  license_plate?: string
  operator_id?: number | null
  is_active?: boolean
}

/**
 * Request body for updating a terminal vehicle
 */
export interface TerminalVehicleUpdateRequest {
  name?: string
  vehicle_type?: VehicleType
  license_plate?: string
  operator_id?: number | null
  is_active?: boolean
}

/**
 * API response for vehicle list
 */
export interface TerminalVehicleListResponse {
  success: boolean
  data: TerminalVehicle[]
  count: number
}

/**
 * API response for single vehicle
 */
export interface TerminalVehicleSingleResponse {
  success: boolean
  data: TerminalVehicle
  message?: string
}

/**
 * API response for operators list
 */
export interface OperatorsListResponse {
  success: boolean
  data: VehicleOperator[]
  count: number
}

// ============ Vehicle Status Types (for sidebar) ============

/**
 * Vehicle status:
 * - available: Active, has operator, no active work
 * - working: Has active work order (ASSIGNED/ACCEPTED/IN_PROGRESS)
 * - offline: Inactive or no operator assigned
 */
export type VehicleStatus = 'available' | 'working' | 'offline'

/**
 * Current task info when vehicle is working
 */
export interface VehicleCurrentTask {
  container_number: string
  target_coordinate: string
}

/**
 * Terminal vehicle with computed status for sidebar display
 */
export interface TerminalVehicleWithStatus {
  id: number
  name: string
  vehicle_type: string
  vehicle_type_display: string
  operator_name: string | null
  status: VehicleStatus
  current_task: VehicleCurrentTask | null
}

/**
 * API response for vehicles with status endpoint
 */
export interface TerminalVehicleStatusResponse {
  success: boolean
  data: TerminalVehicleWithStatus[]
  count: number
  working_count: number
}

/**
 * Status configuration for UI display
 */
export interface VehicleStatusConfig {
  icon: string
  color: string
  label: string
}

/**
 * Status configuration mapping
 */
export const VEHICLE_STATUS_CONFIG: Record<VehicleStatus, VehicleStatusConfig> = {
  available: {
    icon: '🟢',
    color: '#52c41a', // Green
    label: 'Свободен',
  },
  working: {
    icon: '🟠',
    color: '#fa8c16', // Orange
    label: 'Работает',
  },
  offline: {
    icon: '⚪',
    color: '#8c8c8c', // Gray
    label: 'Оффлайн',
  },
}
