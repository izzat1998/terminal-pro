import { http } from '../utils/httpClient';

export interface ExpenseType {
  id: number;
  name: string;
  default_rate_usd: string;
  default_rate_uzs: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExpenseTypeCreateData {
  name: string;
  default_rate_usd: number;
  default_rate_uzs: number;
  is_active?: boolean;
}

interface ExpenseTypesResponse {
  success: boolean;
  data: ExpenseType[];
}

interface ExpenseTypeResponse {
  success: boolean;
  data: ExpenseType;
}

export const expenseTypesService = {
  async getAll(activeOnly = false): Promise<ExpenseType[]> {
    const url = activeOnly ? '/billing/expense-types/?is_active=true' : '/billing/expense-types/';
    const response = await http.get<ExpenseTypesResponse>(url);
    return response.data;
  },

  async getById(id: number): Promise<ExpenseType> {
    const response = await http.get<ExpenseTypeResponse>(`/billing/expense-types/${id}/`);
    return response.data;
  },

  async create(data: ExpenseTypeCreateData): Promise<ExpenseType> {
    const response = await http.post<ExpenseTypeResponse>('/billing/expense-types/', data);
    return response.data;
  },

  async update(id: number, data: Partial<ExpenseTypeCreateData>): Promise<ExpenseType> {
    const response = await http.patch<ExpenseTypeResponse>(`/billing/expense-types/${id}/`, data);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await http.delete(`/billing/expense-types/${id}/`);
  },
};
