/**
 * Terminal Vehicle Service
 *
 * API service for CRUD operations on terminal vehicles (yard equipment).
 */

import { http } from '../utils/httpClient'
import type {
  TerminalVehicle,
  TerminalVehicleCreateRequest,
  TerminalVehicleUpdateRequest,
  TerminalVehicleListResponse,
  TerminalVehicleSingleResponse,
  VehicleOperator,
  OperatorsListResponse,
} from '../types/terminalVehicles'

const BASE_URL = '/terminal/terminal-vehicles'

/**
 * Fetch all terminal vehicles.
 *
 * Returns all vehicles including inactive ones for admin management.
 */
export async function getTerminalVehicles(): Promise<TerminalVehicle[]> {
  const response = await http.get<TerminalVehicleListResponse>(`${BASE_URL}/`)
  return response.data
}

/**
 * Fetch a single terminal vehicle by ID.
 */
export async function getTerminalVehicle(id: number): Promise<TerminalVehicle> {
  const response = await http.get<TerminalVehicleSingleResponse>(`${BASE_URL}/${id}/`)
  return response.data
}

/**
 * Create a new terminal vehicle.
 */
export async function createTerminalVehicle(
  data: TerminalVehicleCreateRequest
): Promise<TerminalVehicle> {
  const response = await http.post<TerminalVehicleSingleResponse>(`${BASE_URL}/`, data)
  return response.data
}

/**
 * Update an existing terminal vehicle.
 */
export async function updateTerminalVehicle(
  id: number,
  data: TerminalVehicleUpdateRequest
): Promise<TerminalVehicle> {
  const response = await http.patch<TerminalVehicleSingleResponse>(`${BASE_URL}/${id}/`, data)
  return response.data
}

/**
 * Delete a terminal vehicle.
 *
 * Note: Cannot delete vehicles with active work orders.
 */
export async function deleteTerminalVehicle(id: number): Promise<void> {
  await http.delete<{ success: boolean; message: string }>(`${BASE_URL}/${id}/`)
}

/**
 * Fetch available operators (managers) for assignment.
 */
export async function getAvailableOperators(): Promise<VehicleOperator[]> {
  const response = await http.get<OperatorsListResponse>(`${BASE_URL}/operators/`)
  return response.data
}
