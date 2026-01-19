/**
 * Composable for work order task management in the placement view.
 * Handles fetching pending/active work orders and terminal vehicles for assignment.
 *
 * Uses singleton pattern (module-level refs) for shared state across components.
 */

import { ref, computed, onUnmounted } from 'vue';
import { message } from 'ant-design-vue';
import { workOrderService, type TerminalVehicle } from '../services/workOrderService';
import type { WorkOrder, Position } from '../types/placement';

// Shared state (singleton pattern)
const pendingTasks = ref<WorkOrder[]>([]);
const vehicles = ref<TerminalVehicle[]>([]);
const loading = ref(false);
const vehiclesLoading = ref(false);
const selectedTaskId = ref<number | null>(null);
const error = ref<string | null>(null);

// Auto-refresh interval handle
let refreshIntervalId: ReturnType<typeof setInterval> | null = null;
const REFRESH_INTERVAL_MS = 30_000; // 30 seconds

export function useWorkOrderTasks() {
  /**
   * Fetch pending/active work orders (PENDING, ASSIGNED, IN_PROGRESS).
   */
  async function fetchTasks(): Promise<void> {
    loading.value = true;
    error.value = null;

    try {
      // Fetch work orders with active statuses (must match placement_service.py)
      // PENDING, ASSIGNED, ACCEPTED, IN_PROGRESS all show as orange in 3D view
      const orders = await workOrderService.getWorkOrders({
        status: 'PENDING,ASSIGNED,ACCEPTED,IN_PROGRESS',
      });
      pendingTasks.value = orders;
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Не удалось загрузить задания';
      error.value = errorMsg;
      message.error(errorMsg);
    } finally {
      loading.value = false;
    }
  }

  /**
   * Fetch terminal vehicles for assignment dropdown.
   */
  async function fetchVehicles(): Promise<void> {
    vehiclesLoading.value = true;

    try {
      vehicles.value = await workOrderService.getTerminalVehicles();
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Не удалось загрузить технику';
      message.error(errorMsg);
    } finally {
      vehiclesLoading.value = false;
    }
  }

  /**
   * Assign a terminal vehicle to a work order.
   */
  async function assignVehicle(workOrderId: number, vehicleId: number): Promise<void> {
    try {
      await workOrderService.assignWorkOrder(workOrderId, vehicleId);
      message.success('Техника назначена');
      // Refresh tasks to get updated status
      await fetchTasks();
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Не удалось назначить технику';
      message.error(errorMsg);
      throw e;
    }
  }

  /**
   * Select a task (for camera focus in 3D view).
   */
  function selectTask(taskId: number | null): void {
    selectedTaskId.value = taskId;
  }

  /**
   * Get position from work order for 3D camera focus.
   */
  function getTaskPosition(task: WorkOrder): Position {
    return {
      zone: task.target_zone,
      row: task.target_row,
      bay: task.target_bay,
      tier: task.target_tier,
      sub_slot: task.target_sub_slot,
      coordinate: task.target_coordinate,
    };
  }

  /**
   * Start auto-refresh (every 30 seconds).
   */
  function startAutoRefresh(): void {
    if (refreshIntervalId) return; // Already running
    refreshIntervalId = setInterval(() => {
      void fetchTasks();
    }, REFRESH_INTERVAL_MS);
  }

  /**
   * Stop auto-refresh.
   */
  function stopAutoRefresh(): void {
    if (refreshIntervalId) {
      clearInterval(refreshIntervalId);
      refreshIntervalId = null;
    }
  }

  /**
   * Initialize: fetch tasks and vehicles, start auto-refresh.
   */
  async function initialize(): Promise<void> {
    await Promise.all([fetchTasks(), fetchVehicles()]);
    startAutoRefresh();
  }

  /**
   * Cleanup on component unmount.
   */
  function cleanup(): void {
    stopAutoRefresh();
  }

  // Computed: active vehicles only (for dropdown)
  const activeVehicles = computed(() =>
    vehicles.value.filter(v => v.is_active)
  );

  // Computed: task count badge
  const taskCount = computed(() => pendingTasks.value.length);

  // Computed: currently selected task
  const selectedTask = computed(() =>
    pendingTasks.value.find(t => t.id === selectedTaskId.value) ?? null
  );

  // Auto-cleanup on unmount (for components that use this)
  onUnmounted(() => {
    // Don't stop auto-refresh on unmount since singleton state persists
    // Only stop when explicitly called or page navigation
  });

  return {
    // State
    pendingTasks,
    vehicles,
    loading,
    vehiclesLoading,
    selectedTaskId,
    error,

    // Computed
    activeVehicles,
    taskCount,
    selectedTask,

    // Actions
    fetchTasks,
    fetchVehicles,
    assignVehicle,
    selectTask,
    getTaskPosition,
    initialize,
    cleanup,
    startAutoRefresh,
    stopAutoRefresh,
  };
}
