/**
 * Composable for fetching and merging storage costs into container records.
 * Extracts duplicate storage cost fetching logic from ContainerTable.vue and Containers.vue.
 *
 * Usage:
 *   import { useStorageCosts } from '@/composables/useStorageCosts'
 *   const { fetchStorageCosts, isLoading } = useStorageCosts()
 *   await fetchStorageCosts(records, record => record.id)
 */

import { ref } from 'vue';
import { tariffsService, type StorageCostResult } from '../services/tariffsService';
import { useAuth } from './useAuth';

/**
 * Interface for records that can have storage cost fields merged into them
 */
export interface StorageCostFields {
  storageCostUsd?: string;
  storageCostUzs?: string;
  storageBillableDays?: number;
  storageCostLoading?: boolean;
}

export function useStorageCosts() {
  const isLoading = ref(false);
  const { user } = useAuth();

  /**
   * Fetch storage costs for a list of records and merge results into each record.
   * Uses customer endpoint for customer users, admin endpoint for admin users.
   *
   * @param records - Array of records to update with storage costs
   * @param getContainerId - Function to extract container entry ID from a record
   */
  async function fetchStorageCosts<T extends StorageCostFields>(
    records: T[],
    getContainerId: (record: T) => number
  ): Promise<void> {
    if (records.length === 0) return;

    const containerIds = records.map(getContainerId);
    isLoading.value = true;

    // Mark all records as loading
    records.forEach(record => {
      record.storageCostLoading = true;
    });

    try {
      // Use customer endpoint for customer users, admin endpoint for admins
      const isCustomer = user.value?.user_type === 'customer';
      const response = isCustomer
        ? await tariffsService.calculateCustomerBulkStorageCosts({
            container_entry_ids: containerIds,
          })
        : await tariffsService.calculateBulkStorageCosts({
            container_entry_ids: containerIds,
          });

      if (response.success && response.data?.results) {
        // Build a map for O(1) lookup
        const costsMap = new Map<number, StorageCostResult>();
        for (const cost of response.data.results) {
          costsMap.set(cost.container_entry_id, cost);
        }

        // Merge costs into records
        records.forEach(record => {
          const cost = costsMap.get(getContainerId(record));
          if (cost) {
            record.storageCostUsd = cost.total_usd;
            record.storageCostUzs = cost.total_uzs;
            record.storageBillableDays = cost.billable_days;
          }
          record.storageCostLoading = false;
        });
      }
    } catch (error) {
      console.error('Failed to fetch storage costs:', error);
      // Clear loading state on error
      records.forEach(record => {
        record.storageCostLoading = false;
      });
    } finally {
      isLoading.value = false;
    }
  }

  return {
    fetchStorageCosts,
    isLoading,
  };
}
