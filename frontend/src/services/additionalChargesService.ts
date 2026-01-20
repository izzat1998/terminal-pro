import { http } from '../utils/httpClient';

export interface AdditionalCharge {
  id: number;
  container_entry: number;
  container_number: string;
  company_name: string | null;
  description: string;
  amount_usd: string;
  amount_uzs: string;
  charge_date: string;
  created_at: string;
  updated_at: string;
  created_by: number | null;
  created_by_name: string;
}

export interface AdditionalChargeCreateData {
  container_entry: number;
  description: string;
  amount_usd: number;
  amount_uzs: number;
  charge_date: string;
}

export interface AdditionalChargeSummary {
  total_charges: number;
  total_usd: string;
  total_uzs: string;
}

export interface AdditionalChargesResponse {
  success: boolean;
  data: AdditionalCharge[];
  summary: AdditionalChargeSummary;
}

interface ChargeParams {
  date_from?: string;
  date_to?: string;
  search?: string;
  company_id?: number;
}

function buildQueryString(params?: ChargeParams): string {
  if (!params) return '';
  const searchParams = new URLSearchParams();
  if (params.date_from) searchParams.append('date_from', params.date_from);
  if (params.date_to) searchParams.append('date_to', params.date_to);
  if (params.search) searchParams.append('search', params.search);
  if (params.company_id) searchParams.append('company_id', params.company_id.toString());
  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

export const additionalChargesService = {
  async getCustomerCharges(params?: ChargeParams): Promise<AdditionalChargesResponse> {
    return http.get<AdditionalChargesResponse>(`/customer/additional-charges/${buildQueryString(params)}`);
  },

  async getCompanyCharges(companySlug: string, params?: ChargeParams): Promise<AdditionalChargesResponse> {
    return http.get<AdditionalChargesResponse>(`/auth/companies/${companySlug}/additional-charges/${buildQueryString(params)}`);
  },

  async getAllCharges(params?: ChargeParams): Promise<AdditionalChargesResponse> {
    const response = await http.get<{ success: boolean; data: AdditionalCharge[] }>(
      `/billing/additional-charges/${buildQueryString(params)}`
    );
    // Calculate summary from results
    const data = response.data || [];
    const totalUsd = data.reduce((sum, c) => sum + parseFloat(c.amount_usd), 0);
    const totalUzs = data.reduce((sum, c) => sum + parseFloat(c.amount_uzs), 0);
    return {
      success: response.success,
      data,
      summary: {
        total_charges: data.length,
        total_usd: totalUsd.toFixed(2),
        total_uzs: totalUzs.toFixed(0),
      },
    };
  },

  async create(data: AdditionalChargeCreateData): Promise<{ success: boolean; data: AdditionalCharge }> {
    return http.post('/billing/additional-charges/', data);
  },

  async update(id: number, data: Partial<AdditionalChargeCreateData>): Promise<{ success: boolean; data: AdditionalCharge }> {
    return http.patch(`/billing/additional-charges/${id}/`, data);
  },

  async delete(id: number): Promise<{ success: boolean; message: string }> {
    return http.delete(`/billing/additional-charges/${id}/`);
  },

  async getByContainerId(containerId: number): Promise<AdditionalCharge[]> {
    const response = await http.get<{ success: boolean; data: AdditionalCharge[] }>(
      `/billing/additional-charges/?container_entry_id=${containerId}`
    );
    return response.data || [];
  },

  async getBulkSummary(containerEntryIds: number[]): Promise<AdditionalChargeBulkSummary[]> {
    const response = await http.post<{ success: boolean; data: AdditionalChargeBulkSummary[] }>(
      '/billing/additional-charges/bulk-summary/',
      { container_entry_ids: containerEntryIds }
    );
    return response.data || [];
  },
};

export interface AdditionalChargeBulkSummary {
  container_entry_id: number;
  total_usd: string;
  total_uzs: string;
  charge_count: number;
}
