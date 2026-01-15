/**
 * Composable for vehicle gate statistics
 * Handles fetching and managing gate statistics state
 */

import { ref } from 'vue';
import { http } from '../utils/httpClient';
import type { GateStatistics, GateStats } from '../types/vehicle';

/** Default stats state */
function getDefaultStats(): GateStats {
  return {
    total: 0,
    light: 0,
    cargo: 0,
    overstayers: 0,
    avgDwellHours: 0,
    entriesLast30Days: 0,
    exitsLast30Days: 0,
    longestStay: {
      plate: '',
      hours: 0,
    },
  };
}

/**
 * Composable for managing vehicle gate statistics
 *
 * @example
 * ```vue
 * <script setup lang="ts">
 * const { gateStats, statsLoading, fetchGateStats } = useVehicleStats();
 *
 * onMounted(() => {
 *   fetchGateStats();
 * });
 * </script>
 * ```
 */
export function useVehicleStats() {
  const statsLoading = ref(false);
  const gateStats = ref<GateStats>(getDefaultStats());

  /**
   * Fetch gate statistics from API
   * Silently handles errors since stats are supplementary info
   */
  async function fetchGateStats(): Promise<void> {
    try {
      statsLoading.value = true;
      const response = await http.get<{ success: boolean; data: GateStatistics }>('/vehicles/statistics/');
      const stats = response.data;
      const longestStay = stats.time_metrics?.longest_current_stay;

      gateStats.value = {
        total: stats.current?.total_on_terminal ?? 0,
        light: stats.current?.by_vehicle_type?.['LIGHT']?.count ?? 0,
        cargo: stats.current?.by_vehicle_type?.['CARGO']?.count ?? 0,
        overstayers: stats.overstayers?.count ?? 0,
        avgDwellHours: stats.time_metrics?.avg_dwell_hours ?? 0,
        entriesLast30Days: stats.last_30_days?.total_entries ?? 0,
        exitsLast30Days: stats.last_30_days?.total_exits ?? 0,
        longestStay: {
          plate: longestStay?.license_plate ?? '',
          hours: longestStay?.hours ?? 0,
        },
      };
    } catch (error) {
      console.error('Failed to fetch gate stats:', error);
      // Don't show error toast for stats - just log it
      // Stats are supplementary info, page is still usable without them
    } finally {
      statsLoading.value = false;
    }
  }

  /**
   * Reset stats to default values
   */
  function resetStats(): void {
    gateStats.value = getDefaultStats();
  }

  return {
    gateStats,
    statsLoading,
    fetchGateStats,
    resetStats,
  };
}
