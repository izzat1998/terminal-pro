/**
 * useWorkOrdersPage - State management for the dedicated Tasks page
 *
 * Provides:
 * - Work order list with pagination
 * - Filter state (status, vehicle, search)
 * - Auto-refresh functionality
 * - Loading and error states
 *
 * Used by WorkOrdersPage.vue for full work order management.
 */

import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue';
import {
  getAllWorkOrders,
  getTerminalVehicles,
  type WorkOrderFilterParams,
  type TerminalVehicle,
} from '../services/workOrderService';
import type { WorkOrder, WorkOrderStatus } from '../types/placement';

// Filter state type
// Note: vehicleId uses 0 for "all" because Ant Design Select doesn't handle null well
interface FilterState {
  status: WorkOrderStatus | '';
  vehicleId: number;  // 0 = all vehicles
  search: string;
}

// Pagination state
interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
}

// Auto-refresh interval (30 seconds)
const REFRESH_INTERVAL = 30_000;

export function useWorkOrdersPage() {
  // Data state
  const workOrders = ref<WorkOrder[]>([]);
  const vehicles = ref<TerminalVehicle[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Filter state (vehicleId: 0 = all vehicles)
  const filters = reactive<FilterState>({
    status: '',
    vehicleId: 0,
    search: '',
  });

  // Pagination state
  const pagination = reactive<PaginationState>({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  // Auto-refresh timer
  let refreshTimer: number | null = null;

  // Build filter params for API call
  const filterParams = computed<WorkOrderFilterParams>(() => {
    const params: WorkOrderFilterParams = {
      page: pagination.current,
      page_size: pagination.pageSize,
    };

    if (filters.status) params.status = filters.status;
    if (filters.vehicleId > 0) params.assigned_to = filters.vehicleId;  // 0 = all
    if (filters.search) params.search = filters.search;

    return params;
  });

  // Fetch work orders with current filters
  async function fetchWorkOrders(): Promise<void> {
    loading.value = true;
    error.value = null;

    try {
      const response = await getAllWorkOrders(filterParams.value);
      workOrders.value = response.results;
      pagination.total = response.count;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Ошибка загрузки заданий';
      console.error('Failed to fetch work orders:', e);
    } finally {
      loading.value = false;
    }
  }

  // Fetch terminal vehicles for filter dropdown
  async function fetchVehicles(): Promise<void> {
    try {
      vehicles.value = await getTerminalVehicles();
    } catch (e) {
      console.error('Failed to fetch vehicles:', e);
    }
  }

  // Handle filter change - reset to page 1 and refetch
  function handleFilterChange(): void {
    pagination.current = 1;
    fetchWorkOrders();
  }

  // Handle page change
  function handlePageChange(page: number, pageSize: number): void {
    pagination.current = page;
    pagination.pageSize = pageSize;
    fetchWorkOrders();
  }

  // Reset filters to default
  function resetFilters(): void {
    filters.status = '';
    filters.vehicleId = 0;
    filters.search = '';
    pagination.current = 1;
    fetchWorkOrders();
  }

  // Manual refresh
  function refresh(): void {
    fetchWorkOrders();
  }

  // Start auto-refresh
  function startAutoRefresh(): void {
    stopAutoRefresh();
    refreshTimer = window.setInterval(() => {
      fetchWorkOrders();
    }, REFRESH_INTERVAL);
  }

  // Stop auto-refresh
  function stopAutoRefresh(): void {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }

  // Watch for filter changes (debounce search)
  let searchDebounce: number | null = null;
  watch(() => filters.search, () => {
    if (searchDebounce) clearTimeout(searchDebounce);
    searchDebounce = window.setTimeout(() => {
      handleFilterChange();
    }, 300);
  });

  // Watch for non-search filter changes
  watch(
    () => [filters.status, filters.vehicleId],
    () => {
      handleFilterChange();
    }
  );

  // Initialize on mount
  onMounted(() => {
    fetchWorkOrders();
    fetchVehicles();
    startAutoRefresh();
  });

  // Cleanup on unmount
  onUnmounted(() => {
    stopAutoRefresh();
    if (searchDebounce) clearTimeout(searchDebounce);
  });

  return {
    // Data
    workOrders,
    vehicles,
    loading,
    error,

    // Filters
    filters,

    // Pagination
    pagination,
    handlePageChange,

    // Actions
    refresh,
    resetFilters,
  };
}
