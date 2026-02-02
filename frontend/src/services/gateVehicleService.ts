/**
 * Gate Vehicle Service
 *
 * API client for vehicle entry/exit operations at the gate.
 * Uses the /api/vehicles/entries/ endpoints.
 */

import { http } from '@/utils/httpClient'

/** Backend vehicle entry response */
export interface GateVehicleEntry {
  id: number
  status: string
  status_display: string
  license_plate: string
  vehicle_type: string
  vehicle_type_display: string
  transport_type: string | null
  transport_type_display: string | null
  entry_time: string | null
  exit_time: string | null
  is_on_terminal: boolean
  dwell_time_hours: number | null
}

interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
}

class GateVehicleService {
  /**
   * Create a new vehicle entry (gate check-in).
   * Sets status to ON_TERMINAL with entry_time = now (auto-set by backend).
   * DRF create endpoint returns the entry directly (not wrapped in {success, data}).
   */
  async createEntry(licensePlate: string, transportType: 'TRUCK' | 'WAGON' = 'TRUCK'): Promise<GateVehicleEntry> {
    // Backend transport_type choices: PLATFORM, TRUCK, TRAILER, MINI_TRUCK, ZIL, GAZELLE, LABO
    // WAGON is a 3D vehicle type for rail — gate traffic is always road, so map to TRUCK
    const backendTransport = transportType === 'WAGON' ? 'TRUCK' : transportType
    const response = await http.post<GateVehicleEntry>('/vehicles/entries/', {
      license_plate: licensePlate,
      vehicle_type: 'CARGO',
      transport_type: backendTransport,
      entry_load_status: 'EMPTY',
      status: 'ON_TERMINAL',
    })
    return response
  }

  /**
   * Register a vehicle exit.
   * Transitions status: ON_TERMINAL → EXITED.
   */
  async registerExit(licensePlate: string): Promise<GateVehicleEntry> {
    const response = await http.post<ApiResponse<GateVehicleEntry>>('/vehicles/entries/exit/', {
      license_plate: licensePlate,
      exit_time: new Date().toISOString(),
    })
    return response.data
  }

  /**
   * Get vehicles currently on terminal.
   */
  async getOnTerminal(): Promise<GateVehicleEntry[]> {
    const response = await http.get<ApiResponse<GateVehicleEntry[]>>('/vehicles/entries/on-terminal/')
    return response.data
  }
}

export const gateVehicleService = new GateVehicleService()
