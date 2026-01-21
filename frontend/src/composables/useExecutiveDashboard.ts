/**
 * Executive Dashboard Composable
 *
 * Manages dashboard data fetching, auto-refresh, and computed chart options.
 * Provides reactive state for all dashboard components.
 */

import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue';
import { message } from 'ant-design-vue';
import dayjs from '@/config/dayjs';
import { getExecutiveDashboard } from '../services/executiveDashboardService';
import type {
  ExecutiveDashboardData,
  DashboardSummary,
  ContainerStatusBreakdown,
  RevenueTrendPoint,
  TopCustomer,
  ThroughputMetrics,
  VehicleMetrics,
  PreorderStats,
} from '../types/dashboard';
import type { EChartsOption } from '../utils/echarts';

// ============ Chart Constants ============

const COLORS = {
  primary: '#1677ff',
  success: '#52c41a',
  warning: '#faad14',
  error: '#ff4d4f',
  purple: '#722ed1',
  cyan: '#13c2c2',
  blue: '#1677ff',
  green: '#52c41a',
  orange: '#fa8c16',
  pink: '#eb2f96',
};

const EMPTY_CHART_OPTION: EChartsOption = {
  title: { text: 'Нет данных', left: 'center', top: 'center' },
};

const DEFAULT_GRID = {
  left: '3%',
  right: '4%',
  bottom: '15%',
  top: '10%',
  containLabel: true,
};

function formatDateLabel(value: string): string {
  return dayjs(value).format('D/M');
}

// ============ Composable Interface ============

interface UseExecutiveDashboardReturn {
  // Data
  data: Ref<ExecutiveDashboardData | null>;
  loading: Ref<boolean>;
  error: Ref<string | null>;
  lastUpdated: Ref<Date | null>;

  // Computed sections
  summary: ComputedRef<DashboardSummary | null>;
  containerStatus: ComputedRef<ContainerStatusBreakdown | null>;
  revenueTrends: ComputedRef<RevenueTrendPoint[]>;
  topCustomers: ComputedRef<TopCustomer[]>;
  throughput: ComputedRef<ThroughputMetrics | null>;
  vehicleMetrics: ComputedRef<VehicleMetrics | null>;
  preorderStats: ComputedRef<PreorderStats | null>;

  // Chart options
  revenueChartOption: ComputedRef<EChartsOption>;
  containerStatusChartOption: ComputedRef<EChartsOption>;
  topCustomersChartOption: ComputedRef<EChartsOption>;
  throughputChartOption: ComputedRef<EChartsOption>;

  // Actions
  fetchData: () => Promise<void>;
  refresh: () => Promise<void>;
}

/**
 * Executive Dashboard composable for managing dashboard state and charts.
 *
 * @param autoRefreshInterval - Auto-refresh interval in ms (default: 5 minutes, 0 to disable)
 *
 * @example
 * ```ts
 * const {
 *   data,
 *   loading,
 *   summary,
 *   revenueChartOption,
 *   fetchData
 * } = useExecutiveDashboard();
 *
 * onMounted(() => fetchData());
 * ```
 */
export function useExecutiveDashboard(
  autoRefreshInterval: number = 300000 // 5 minutes
): UseExecutiveDashboardReturn {
  // ============ State ============

  const data = ref<ExecutiveDashboardData | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdated = ref<Date | null>(null);

  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  // ============ Computed Data Sections ============

  const summary = computed(() => data.value?.summary ?? null);
  const containerStatus = computed(() => data.value?.container_status ?? null);
  const revenueTrends = computed(() => data.value?.revenue_trends ?? []);
  const topCustomers = computed(() => data.value?.top_customers ?? []);
  const throughput = computed(() => data.value?.throughput ?? null);
  const vehicleMetrics = computed(() => data.value?.vehicle_metrics ?? null);
  const preorderStats = computed(() => data.value?.preorder_stats ?? null);

  // ============ Chart Options ============

  /**
   * Revenue trend line chart (30-day)
   */
  const revenueChartOption = computed<EChartsOption>(() => {
    const trends = revenueTrends.value;
    if (!trends.length) return EMPTY_CHART_OPTION;

    return {
      title: { show: false },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: {
        data: ['Выручка (USD)', 'Въезд', 'Выезд'],
        bottom: 0,
      },
      grid: DEFAULT_GRID,
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: trends.map((t) => t.date),
        axisLabel: { formatter: formatDateLabel },
      },
      yAxis: [
        {
          type: 'value',
          name: 'USD',
          position: 'left',
          axisLabel: { formatter: '${value}' },
        },
        {
          type: 'value',
          name: 'Контейнеры',
          position: 'right',
        },
      ],
      series: [
        {
          name: 'Выручка (USD)',
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.3 },
          data: trends.map((t) => parseFloat(t.revenue_usd)),
          itemStyle: { color: COLORS.success },
        },
        {
          name: 'Въезд',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          data: trends.map((t) => t.entries),
          itemStyle: { color: COLORS.blue },
        },
        {
          name: 'Выезд',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          data: trends.map((t) => t.exits),
          itemStyle: { color: COLORS.orange },
        },
      ],
    };
  });

  /**
   * Container status donut chart (laden/empty)
   */
  const containerStatusChartOption = computed<EChartsOption>(() => {
    const status = containerStatus.value;
    if (!status) return EMPTY_CHART_OPTION;

    return {
      title: { show: false },
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'vertical',
        right: '5%',
        top: 'center',
      },
      series: [
        {
          name: 'Статус',
          type: 'pie',
          radius: ['45%', '70%'],
          center: ['40%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 8,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: true,
            position: 'center',
            formatter: () => {
              const total = status.laden + status.empty;
              return `{total|${total}}\n{label|Всего}`;
            },
            rich: {
              total: { fontSize: 28, fontWeight: 'bold', color: '#333' },
              label: { fontSize: 14, color: '#999' },
            },
          },
          emphasis: {
            label: { show: true, fontSize: 16, fontWeight: 'bold' },
          },
          data: [
            { value: status.laden, name: 'Гружёные', itemStyle: { color: COLORS.blue } },
            { value: status.empty, name: 'Порожние', itemStyle: { color: COLORS.cyan } },
          ],
        },
        // Inner ring for size breakdown
        {
          name: 'Размер',
          type: 'pie',
          radius: ['25%', '40%'],
          center: ['40%', '50%'],
          label: { show: false },
          data: [
            { value: status.by_size['20ft'], name: '20ft', itemStyle: { color: COLORS.purple } },
            { value: status.by_size['40ft'], name: '40ft', itemStyle: { color: COLORS.pink } },
          ],
        },
      ],
    };
  });

  /**
   * Top customers horizontal bar chart
   */
  const topCustomersChartOption = computed<EChartsOption>(() => {
    const customers = topCustomers.value;
    if (!customers.length) return EMPTY_CHART_OPTION;

    // Take top 8 and reverse for horizontal bar (bottom to top)
    const top8 = customers.slice(0, 8).reverse();

    return {
      title: { show: false },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: unknown) => {
          const items = params as Array<{ name: string; value: number }>;
          const item = items[0];
          if (!item) return '';
          const customer = customers.find((c) => c.company_name === item.name);
          return `${item.name}<br/>Контейнеров: ${customer?.container_count ?? 0}<br/>Выручка: $${item.value.toLocaleString()}`;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        axisLabel: { formatter: '${value}' },
      },
      yAxis: {
        type: 'category',
        data: top8.map((c) => c.company_name),
        axisLabel: {
          width: 100,
          overflow: 'truncate',
        },
      },
      series: [
        {
          name: 'Выручка',
          type: 'bar',
          data: top8.map((c) => parseFloat(c.revenue_usd)),
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: COLORS.blue },
                { offset: 1, color: COLORS.cyan },
              ],
            },
            borderRadius: [0, 4, 4, 0],
          },
          label: {
            show: true,
            position: 'right',
            formatter: '{c}',
          },
        },
      ],
    };
  });

  /**
   * Throughput area chart (entries vs exits)
   */
  const throughputChartOption = computed<EChartsOption>(() => {
    const tp = throughput.value;
    if (!tp || !tp.daily_data.length) return EMPTY_CHART_OPTION;

    return {
      title: { show: false },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: {
        data: ['Въезд', 'Выезд'],
        bottom: 0,
      },
      grid: DEFAULT_GRID,
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: tp.daily_data.map((d) => d.date),
        axisLabel: { formatter: formatDateLabel },
      },
      yAxis: {
        type: 'value',
        name: 'Контейнеры',
      },
      series: [
        {
          name: 'Въезд',
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.4 },
          emphasis: { focus: 'series' },
          data: tp.daily_data.map((d) => d.entries),
          itemStyle: { color: COLORS.success },
        },
        {
          name: 'Выезд',
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.4 },
          emphasis: { focus: 'series' },
          data: tp.daily_data.map((d) => d.exits),
          itemStyle: { color: COLORS.warning },
        },
      ],
    };
  });

  // ============ Actions ============

  /**
   * Fetch dashboard data from API
   */
  async function fetchData(): Promise<void> {
    loading.value = true;
    error.value = null;

    try {
      data.value = await getExecutiveDashboard();
      lastUpdated.value = dayjs().toDate();
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Не удалось загрузить данные';
      message.error(error.value);
    } finally {
      loading.value = false;
    }
  }

  /**
   * Manual refresh (alias for fetchData with user feedback)
   */
  async function refresh(): Promise<void> {
    await fetchData();
    if (!error.value) {
      message.success('Данные обновлены');
    }
  }

  // ============ Lifecycle ============

  onMounted(() => {
    fetchData();

    // Setup auto-refresh
    if (autoRefreshInterval > 0) {
      refreshTimer = setInterval(fetchData, autoRefreshInterval);
    }
  });

  onUnmounted(() => {
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  });

  // ============ Return ============

  return {
    // Data
    data,
    loading,
    error,
    lastUpdated,

    // Computed sections
    summary,
    containerStatus,
    revenueTrends,
    topCustomers,
    throughput,
    vehicleMetrics,
    preorderStats,

    // Chart options
    revenueChartOption,
    containerStatusChartOption,
    topCustomersChartOption,
    throughputChartOption,

    // Actions
    fetchData,
    refresh,
  };
}
