/**
 * Tariffs Service
 *
 * API service for managing storage tariffs and calculating storage costs.
 */

import { http } from '../utils/httpClient';
import type { ApiResponse, PaginatedResponse } from '../types/api';

// ============================================================================
// Types
// ============================================================================

export type ContainerSize = '20ft' | '40ft';
export type ContainerBillingStatus = 'laden' | 'empty';

export interface TariffRate {
  id: number;
  container_size: ContainerSize;
  container_size_display: string;
  container_status: ContainerBillingStatus;
  container_status_display: string;
  daily_rate_usd: string;
  daily_rate_uzs: string;
  free_days: number;
}

export interface Tariff {
  id: number;
  company: number | null;
  company_name: string | null;
  effective_from: string;
  effective_to: string | null;
  is_active: boolean;
  is_general: boolean;
  notes: string;
  rates: TariffRate[];
  created_by: number;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface TariffRateInput {
  container_size: ContainerSize;
  container_status: ContainerBillingStatus;
  daily_rate_usd: string;
  daily_rate_uzs: string;
  free_days: number;
}

export interface TariffCreateInput {
  company?: number | null;
  effective_from: string;
  effective_to?: string | null;
  notes?: string;
  rates: TariffRateInput[];
}

export interface TariffUpdateInput {
  effective_to?: string | null;
  notes?: string;
}

// Storage Cost Types
export interface StorageCostPeriod {
  start_date: string;
  end_date: string;
  days: number;
  free_days_used: number;
  billable_days: number;
  tariff_id: number;
  tariff_type: 'general' | 'special';
  daily_rate_usd: string;
  daily_rate_uzs: string;
  amount_usd: string;
  amount_uzs: string;
}

export interface StorageCostResult {
  container_entry_id: number;
  container_number: string;
  company_name: string | null;
  container_size: string;
  container_status: string;
  entry_date: string;
  end_date: string;
  is_active: boolean;
  total_days: number;
  free_days_applied: number;
  billable_days: number;
  total_usd: string;
  total_uzs: string;
  periods: StorageCostPeriod[];
  calculated_at: string;
}

// ============================================================================
// Service
// ============================================================================

class TariffsService {
  /**
   * Get all tariffs with optional filters
   */
  async getTariffs(params?: {
    company_id?: number;
    general?: boolean;
    active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Tariff>> {
    const searchParams = new URLSearchParams();

    if (params?.company_id) {
      searchParams.append('company_id', params.company_id.toString());
    }
    if (params?.general) {
      searchParams.append('general', 'true');
    }
    if (params?.active !== undefined) {
      searchParams.append('active', params.active.toString());
    }
    if (params?.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params?.page_size) {
      searchParams.append('page_size', params.page_size.toString());
    }

    const query = searchParams.toString();
    const endpoint = query ? `/billing/tariffs/?${query}` : '/billing/tariffs/';

    return http.get<PaginatedResponse<Tariff>>(endpoint);
  }

  /**
   * Get active tariffs
   */
  async getActiveTariffs(companyId?: number): Promise<ApiResponse<Tariff[]>> {
    const params = companyId ? `?company_id=${companyId}` : '';
    return http.get<ApiResponse<Tariff[]>>(`/billing/tariffs/active/${params}`);
  }

  /**
   * Get general (default) tariffs
   */
  async getGeneralTariffs(): Promise<ApiResponse<Tariff[]>> {
    return http.get<ApiResponse<Tariff[]>>('/billing/tariffs/general/');
  }

  /**
   * Get a single tariff by ID
   */
  async getTariff(id: number): Promise<ApiResponse<Tariff>> {
    return http.get<ApiResponse<Tariff>>(`/billing/tariffs/${id}/`);
  }

  /**
   * Create a new tariff with rates
   */
  async createTariff(data: TariffCreateInput): Promise<ApiResponse<Tariff>> {
    return http.post<ApiResponse<Tariff>>('/billing/tariffs/', data);
  }

  /**
   * Update a tariff (only effective_to and notes can be updated)
   */
  async updateTariff(id: number, data: TariffUpdateInput): Promise<ApiResponse<Tariff>> {
    return http.patch<ApiResponse<Tariff>>(`/billing/tariffs/${id}/`, data);
  }

  /**
   * Delete a tariff
   */
  async deleteTariff(id: number): Promise<ApiResponse<{ message: string }>> {
    return http.delete<ApiResponse<{ message: string }>>(`/billing/tariffs/${id}/`);
  }

  /**
   * Calculate storage cost for a container entry
   */
  async calculateStorageCost(
    entryId: number,
    asOfDate?: string
  ): Promise<ApiResponse<StorageCostResult>> {
    const params = asOfDate ? `?as_of_date=${asOfDate}` : '';
    return http.get<ApiResponse<StorageCostResult>>(
      `/billing/container-entries/${entryId}/storage-cost/${params}`
    );
  }

  /**
   * Calculate storage costs for multiple containers (admin endpoint)
   */
  async calculateBulkStorageCosts(params: {
    container_entry_ids?: number[];
    filters?: {
      company_id?: number;
      status?: 'active' | 'exited' | 'all';
      entry_date_from?: string;
      entry_date_to?: string;
    };
    as_of_date?: string;
  }): Promise<
    ApiResponse<{
      results: StorageCostResult[];
      summary: {
        total_containers: number;
        total_usd: string;
        total_uzs: string;
        total_billable_days: number;
      };
    }>
  > {
    return http.post('/billing/storage-costs/calculate/', params);
  }

  /**
   * Calculate storage costs for multiple containers (customer endpoint)
   * Only calculates costs for containers belonging to the customer's company
   */
  async calculateCustomerBulkStorageCosts(params: {
    container_entry_ids: number[];
    as_of_date?: string;
  }): Promise<
    ApiResponse<{
      results: StorageCostResult[];
      summary: {
        total_containers: number;
        total_usd: string;
        total_uzs: string;
        total_billable_days: number;
      };
    }>
  > {
    return http.post('/customer/storage-costs/calculate/', params);
  }
}

export const tariffsService = new TariffsService();
