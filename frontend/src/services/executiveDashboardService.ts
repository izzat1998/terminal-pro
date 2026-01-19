/**
 * Executive Dashboard Service
 *
 * Fetches aggregated dashboard data from the backend.
 * All executive KPIs are retrieved in a single optimized API call.
 */

import { http } from '../utils/httpClient';
import type { ApiResponse } from '../types/api';
import type { ExecutiveDashboardData } from '../types/dashboard';

/**
 * Fetch complete executive dashboard data.
 *
 * @param days - Number of days for historical trends (default: 30)
 * @returns Complete dashboard data with all KPIs
 *
 * @example
 * ```ts
 * const data = await getExecutiveDashboard();
 * console.log(data.summary.total_containers_on_terminal);
 * ```
 */
export async function getExecutiveDashboard(
  days: number = 30
): Promise<ExecutiveDashboardData> {
  const response = await http.get<ApiResponse<ExecutiveDashboardData>>(
    `/terminal/entries/executive-dashboard/?days=${days}`
  );
  return response.data;
}
