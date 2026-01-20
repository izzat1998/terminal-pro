/**
 * Composable for fetching and merging additional charges costs into container records.
 * Similar to useStorageCosts but for additional charges summary.
 *
 * Usage:
 *   import { useAdditionalChargesCosts } from '@/composables/useAdditionalChargesCosts'
 *   const { fetchAdditionalChargesCosts } = useAdditionalChargesCosts()
 *   await fetchAdditionalChargesCosts(records, record => record.containerId)
 */

import { ref } from 'vue';
import { additionalChargesService } from '../services/additionalChargesService';

/**
 * Interface for records that can have additional charges fields merged into them
 */
export interface AdditionalChargesFields {
  additionalChargesUsd?: string;
  additionalChargesUzs?: string;
  additionalChargesCount?: number;
  additionalChargesLoading?: boolean;
}

export function useAdditionalChargesCosts() {
  const isLoading = ref(false);

  /**
   * Fetch additional charges summary for a list of records and merge results into each record.
   *
   * @param records - Array of records to update with additional charges
   * @param getContainerId - Function to extract container entry ID from a record
   */
  async function fetchAdditionalChargesCosts<T extends AdditionalChargesFields>(
    records: T[],
    getContainerId: (record: T) => number
  ): Promise<void> {
    if (records.length === 0) return;

    const containerIds = records.map(getContainerId);
    isLoading.value = true;

    // Mark all records as loading
    records.forEach(record => {
      record.additionalChargesLoading = true;
    });

    try {
      const results = await additionalChargesService.getBulkSummary(containerIds);

      // Build a map for O(1) lookup
      const chargesMap = new Map<number, typeof results[0]>();
      for (const result of results) {
        chargesMap.set(result.container_entry_id, result);
      }

      // Merge charges into records
      records.forEach(record => {
        const charges = chargesMap.get(getContainerId(record));
        if (charges) {
          record.additionalChargesUsd = charges.total_usd;
          record.additionalChargesUzs = charges.total_uzs;
          record.additionalChargesCount = charges.charge_count;
        } else {
          record.additionalChargesUsd = '0.00';
          record.additionalChargesUzs = '0';
          record.additionalChargesCount = 0;
        }
        record.additionalChargesLoading = false;
      });
    } catch (error) {
      console.error('Failed to fetch additional charges:', error);
      // Clear loading state on error
      records.forEach(record => {
        record.additionalChargesLoading = false;
      });
    } finally {
      isLoading.value = false;
    }
  }

  return {
    fetchAdditionalChargesCosts,
    isLoading,
  };
}
