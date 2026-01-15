import { http } from '../utils/httpClient';
import type { PaginatedResponse } from '../types/api';

export interface TelegramActivityLog {
  id: number;
  user: number | null;
  user_full_name: string | null;
  user_type: 'manager' | 'customer';
  user_type_display: string;
  telegram_user_id: number | null;
  action: string;
  action_display: string;
  details: Record<string, unknown>;
  success: boolean;
  error_message: string;
  related_object_str: string | null;
  created_at: string;
}

export interface ActivityLogSummary {
  total_count: number;
  success_count: number;
  error_count: number;
  by_action: Array<{
    action: string;
    action_display: string;
    count: number;
  }>;
  by_user_type: Record<string, number>;
}

export interface ActivityLogFilters {
  action?: string;
  user_type?: 'manager' | 'customer';
  success?: boolean;
  user?: number;
  search?: string;
}

class TelegramActivityService {
  /**
   * Get paginated activity logs with optional filters
   */
  async getActivityLogs(
    filters?: ActivityLogFilters,
    page: number = 1,
    pageSize: number = 20
  ): Promise<{ data: TelegramActivityLog[]; total: number }> {
    const params = new URLSearchParams();

    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }

    const url = `/telegram/activity-logs/?${params.toString()}`;
    const response = await http.get<PaginatedResponse<TelegramActivityLog>>(url);

    return {
      data: response.results,
      total: response.count,
    };
  }

  /**
   * Get a single activity log by ID
   */
  async getActivityLogById(id: number): Promise<TelegramActivityLog> {
    return http.get<TelegramActivityLog>(`/telegram/activity-logs/${id}/`);
  }

  /**
   * Get activity summary statistics
   */
  async getSummary(days: number = 7): Promise<ActivityLogSummary> {
    return http.get<ActivityLogSummary>(`/telegram/activity-logs/summary/?days=${days}`);
  }

  /**
   * Get recent activity logs (last 24 hours, max 50)
   */
  async getRecentLogs(): Promise<TelegramActivityLog[]> {
    return http.get<TelegramActivityLog[]>('/telegram/activity-logs/recent/');
  }
}

export const telegramActivityService = new TelegramActivityService();
