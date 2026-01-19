/**
 * Work Order Service - API client for placement work order management
 *
 * Work orders represent placement tasks assigned to terminal vehicles (yard equipment).
 * Flow: Create → Assign → Accept → Start → Complete → Verify
 */

import { http } from '../utils/httpClient';
import type {
  ApiResponse,
  WorkOrder,
  WorkOrderCreateRequest,
  Position,
} from '../types/placement';

const BASE_URL = '/terminal/work-orders';
const VEHICLES_URL = '/terminal/terminal-vehicles';

// Terminal vehicle type for dropdown selection
export interface TerminalVehicle {
  id: number;
  name: string;
  vehicle_type: 'REACH_STACKER' | 'FORKLIFT' | 'YARD_TRUCK' | 'RTG_CRANE';
  vehicle_type_display: string;
  license_plate: string;
  is_active: boolean;
}

/**
 * Get list of active terminal vehicles for assignment dropdown.
 * Returns all active yard equipment (reach stackers, forklifts, yard trucks, RTG cranes).
 */
export async function getTerminalVehicles(): Promise<TerminalVehicle[]> {
  const response = await http.get<{ success: boolean; data: TerminalVehicle[]; count: number }>(
    `${VEHICLES_URL}/`
  );
  return response.data;
}

/**
 * Create a new work order for container placement.
 *
 * When position is not specified, the backend auto-suggests an optimal position.
 * If assigned_to_vehicle_id is provided, the vehicle will be assigned to the task.
 *
 * @param data - Work order creation parameters
 * @returns Created work order
 */
export async function createWorkOrder(data: WorkOrderCreateRequest): Promise<WorkOrder> {
  const response = await http.post<ApiResponse<WorkOrder>>(`${BASE_URL}/`, data);
  return response.data;
}

/**
 * Create work order from a suggested position.
 * Convenience method that converts Position to WorkOrderCreateRequest.
 *
 * @param containerEntryId - Container entry to place
 * @param position - Suggested position from PlacementService
 * @param priority - Order priority (default: MEDIUM)
 * @param assignedToVehicleId - Optional terminal vehicle to assign
 */
export async function createWorkOrderFromPosition(
  containerEntryId: number,
  position: Position,
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT' = 'MEDIUM',
  assignedToVehicleId?: number,
): Promise<WorkOrder> {
  return createWorkOrder({
    container_entry_id: containerEntryId,
    zone: position.zone,
    row: position.row,
    bay: position.bay,
    tier: position.tier,
    sub_slot: position.sub_slot,
    priority,
    assigned_to_vehicle_id: assignedToVehicleId,
  });
}

// Paginated response type from DRF
interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Get list of work orders with optional filters.
 *
 * @param params - Filter parameters
 */
export async function getWorkOrders(params?: {
  status?: string;
  assigned_to?: number;
  priority?: string;
}): Promise<WorkOrder[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.append('status', params.status);
  if (params?.assigned_to) searchParams.append('assigned_to', params.assigned_to.toString());
  if (params?.priority) searchParams.append('priority', params.priority);

  const queryString = searchParams.toString();
  const url = queryString ? `${BASE_URL}/?${queryString}` : `${BASE_URL}/`;

  // API returns paginated response with results array
  const response = await http.get<PaginatedResponse<WorkOrder>>(url);
  return response.results;
}

/**
 * Extended work order filter parameters for full-page view.
 */
export interface WorkOrderFilterParams {
  status?: string;
  assigned_to?: number;
  priority?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

/**
 * Get all work orders with extended filters and pagination.
 * Used by the dedicated Tasks page for full work order management.
 *
 * @param params - Extended filter parameters including search and pagination
 */
export async function getAllWorkOrders(params?: WorkOrderFilterParams): Promise<{
  results: WorkOrder[];
  count: number;
}> {
  const searchParams = new URLSearchParams();

  if (params?.status) searchParams.append('status', params.status);
  if (params?.assigned_to) searchParams.append('assigned_to', params.assigned_to.toString());
  if (params?.priority) searchParams.append('priority', params.priority);
  if (params?.search) searchParams.append('search', params.search);
  if (params?.page) searchParams.append('page', params.page.toString());
  if (params?.page_size) searchParams.append('page_size', params.page_size.toString());

  const queryString = searchParams.toString();
  const url = queryString ? `${BASE_URL}/?${queryString}` : `${BASE_URL}/`;

  const response = await http.get<PaginatedResponse<WorkOrder>>(url);
  return {
    results: response.results,
    count: response.count,
  };
}

/**
 * Get count of work orders by status (for sidebar badge).
 * Returns only active (non-completed) work orders count.
 */
export async function getActiveWorkOrdersCount(): Promise<number> {
  // Get work orders that are not completed or verified
  const response = await http.get<PaginatedResponse<WorkOrder>>(
    `${BASE_URL}/?status__in=PENDING,ASSIGNED,ACCEPTED,IN_PROGRESS&page_size=1`
  );
  return response.count;
}

/**
 * Get pending work orders (waiting to be assigned).
 */
export async function getPendingWorkOrders(): Promise<WorkOrder[]> {
  const response = await http.get<{ success: boolean; data: WorkOrder[] }>(`${BASE_URL}/pending/`);
  return response.data;
}

/**
 * Assign work order to a terminal vehicle.
 *
 * @param workOrderId - Work order to assign
 * @param vehicleId - Terminal vehicle to assign to
 */
export async function assignWorkOrder(
  workOrderId: number,
  vehicleId: number,
): Promise<WorkOrder> {
  const response = await http.post<ApiResponse<WorkOrder>>(
    `${BASE_URL}/${workOrderId}/assign/`,
    { vehicle_id: vehicleId },
  );
  return response.data;
}

// Export as service object
export const workOrderService = {
  createWorkOrder,
  createWorkOrderFromPosition,
  getWorkOrders,
  getAllWorkOrders,
  getActiveWorkOrdersCount,
  getPendingWorkOrders,
  assignWorkOrder,
  getTerminalVehicles,
};
