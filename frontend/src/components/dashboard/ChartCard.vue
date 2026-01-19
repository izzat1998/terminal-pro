<script setup lang="ts">
/**
 * Chart Card Component
 *
 * Generic wrapper combining a-card with DashboardChart.
 * Replaces RevenueChart, ContainerStatusChart, TopCustomersChart, ThroughputChart.
 */

import DashboardChart from './DashboardChart.vue';
import type { EChartsOption } from '../../utils/echarts';

interface Props {
  /** Card title */
  title: string;
  /** ECharts option from composable */
  option: EChartsOption;
  /** Loading state */
  loading?: boolean;
  /** Chart height (default: 320px) */
  height?: string;
}

withDefaults(defineProps<Props>(), {
  loading: false,
  height: '320px',
});
</script>

<template>
  <a-card :title="title" :bordered="false" class="chart-card">
    <template v-if="$slots.extra" #extra>
      <slot name="extra" />
    </template>
    <DashboardChart :option="option" :loading="loading" :height="height" />
  </a-card>
</template>

<style scoped>
.chart-card {
  height: 100%;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

:deep(.ant-card-head) {
  border-bottom: 1px solid #f0f0f0;
}

:deep(.ant-card-body) {
  padding: 16px;
}
</style>
