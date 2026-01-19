/**
 * Terminal Vehicle Status Service
 *
 * API service for fetching terminal vehicles with work status.
 */

import { http } from '../utils/httpClient'
import type {
  TerminalVehicleStatusResponse,
  TerminalVehicleWithStatus,
} from '../types/terminalVehicles'

/**
 * Fetch terminal vehicles with computed work status.
 *
 * Returns all vehicles with:
 * - operator_name: Full name of assigned operator
 * - status: 'available', 'working', or 'offline'
 * - current_task: Container number and target coordinate if working
 */
export async function getTerminalVehiclesWithStatus(): Promise<{
  vehicles: TerminalVehicleWithStatus[]
  workingCount: number
}> {
  const response = await http.get<TerminalVehicleStatusResponse>(
    '/terminal/terminal-vehicles/with-status/'
  )

  return {
    vehicles: response.data,
    workingCount: response.working_count,
  }
}
