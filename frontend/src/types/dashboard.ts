/**
 * Executive Dashboard Types
 * Matches backend ExecutiveDashboardService response structure
 */

// ============ Summary Metrics ============

export interface DashboardSummary {
  total_containers_on_terminal: number;
  total_revenue_usd: string;
  total_revenue_uzs: string;
  containers_entered_today: number;
  containers_exited_today: number;
  vehicles_on_terminal: number;
  active_customers: number;
  laden_count: number;
  empty_count: number;
}

// ============ Container Status ============

export interface ContainerSizeBreakdown {
  '20ft': number;
  '40ft': number;
}

export interface ContainerStatusBreakdown {
  laden: number;
  empty: number;
  by_size: ContainerSizeBreakdown;
}

// ============ Revenue Trends ============

export interface RevenueTrendPoint {
  date: string;
  entries: number;
  exits: number;
  revenue_usd: string;
}

// ============ Top Customers ============

export interface TopCustomer {
  company_id: number;
  company_name: string;
  company_slug: string;
  container_count: number;
  revenue_usd: string;
}

// ============ Throughput ============

export interface ThroughputPeriod {
  entries: number;
  exits: number;
}

export interface ThroughputDailyPoint {
  date: string;
  entries: number;
  exits: number;
}

export interface ThroughputMetrics {
  last_7_days: ThroughputPeriod;
  last_30_days: ThroughputPeriod;
  daily_average: number;
  daily_data: ThroughputDailyPoint[];
}

// ============ Vehicle Metrics ============

export interface VehicleTypeCount {
  count: number;
  label: string;
}

export interface VehicleMetrics {
  total_on_terminal: number;
  avg_dwell_hours: number;
  by_type: Record<string, VehicleTypeCount>;
}

// ============ Pre-order Stats ============

export interface PreorderStats {
  pending: number;
  matched: number;
  completed_today: number;
}

// ============ Complete Dashboard Response ============

export interface ExecutiveDashboardData {
  summary: DashboardSummary;
  container_status: ContainerStatusBreakdown;
  revenue_trends: RevenueTrendPoint[];
  top_customers: TopCustomer[];
  throughput: ThroughputMetrics;
  vehicle_metrics: VehicleMetrics;
  preorder_stats: PreorderStats;
  generated_at: string;
}

// ============ KPI Card Types ============

export interface KpiCardData {
  value: number | string;
  label: string;
  trend?: number; // Percentage change, positive = up
  prefix?: string;
  suffix?: string;
}
