import { http } from '../utils/httpClient';
import type { PaginatedResponse } from '../types/api';

export interface FileObject {
  id: string;
  file_url: string;
  original_filename: string;
  mime_type: string;
  size: number;
  width?: number;
  height?: number;
}

export interface FileAttachment {
  attachment_id: number;
  attachment_type: string;
  description: string;
  display_order?: number;
  file: FileObject;
}

export interface Owner {
  id: number;
  name: string;
  slug: string;
}

export interface CraneOperation {
  id: number;
  operation_date: string;
  created_at: string;
}

export interface Container {
  id: number;
  container_number: string;
  iso_type: string;
}

export interface TerminalEntry {
  id: number;
  container: Container;
  status: string;
  transport_type: string;
  entry_train_number?: string;
  transport_number: string;
  exit_date?: string;
  exit_transport_type?: string;
  exit_train_number?: string;
  exit_transport_number?: string;
  destination_station?: string;
  location?: string;
  additional_crane_operation_date?: string;
  crane_operations?: CraneOperation[];
  note?: string;
  dwell_time_days?: number;
  cargo_weight?: number;
  cargo_name?: string;
  client_name?: string;
  company?: Owner | null;
  container_owner?: Owner | null;
  entry_time: string;
  recorded_by: number | null;
  created_at: string;
  updated_at: string;
  files: FileAttachment[];
  file_count: number;
  main_file: FileAttachment | null;
  // Billing status
  has_pending_invoice?: boolean;
}

class TerminalService {

  async getContainers(filters?: Record<string, string | number | string[] | undefined>, page: number = 1, pageSize: number = 10): Promise<{ data: TerminalEntry[], total: number }> {
    let url = '/terminal/entries/';

    const params = new URLSearchParams();

    // Add pagination parameters
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    // Build query string from filters
    if (filters && Object.keys(filters).length > 0) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          if (Array.isArray(value)) {
            value.forEach(v => params.append(key, v));
          } else {
            params.append(key, String(value));
          }
        }
      });
    }

    const queryString = params.toString();
    if (queryString) {
      url += `?${queryString}`;
    }

    const response = await http.get<PaginatedResponse<TerminalEntry> | TerminalEntry[]>(url);

    // Handle paginated response
    if (response && typeof response === 'object' && 'results' in response) {
      return {
        data: response.results,
        total: response.count,
      };
    }

    // Handle array response
    if (Array.isArray(response)) {
      return {
        data: response,
        total: response.length,
      };
    }

    return { data: [], total: 0 };
  }

  async getContainerById(id: number): Promise<TerminalEntry> {
    return http.get<TerminalEntry>(`/terminal/entries/${id}/`);
  }

  async getOwners(): Promise<Owner[]> {
    const response = await http.get<{ results: Owner[] } | Owner[]>('/terminal/owners/');

    // Handle paginated response
    if (response && typeof response === 'object' && 'results' in response) {
      return response.results;
    }

    // Handle array response
    if (Array.isArray(response)) {
      return response;
    }

    return [];
  }

  async getContainerHistory(containerNumber: string): Promise<TerminalEntry[]> {
    const response = await http.get<PaginatedResponse<TerminalEntry> | { success: boolean; data: TerminalEntry[] }>(
      `/terminal/entries/by-container/?container_number=${encodeURIComponent(containerNumber.toUpperCase())}`
    );

    // Handle paginated response
    if (response && typeof response === 'object' && 'results' in response) {
      return response.results;
    }

    // Handle success wrapper response
    if (response && typeof response === 'object' && 'data' in response) {
      return response.data;
    }

    return [];
  }
}

export const terminalService = new TerminalService();
