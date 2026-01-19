<script setup lang="ts">
/**
 * Dashboard Chart Wrapper Component
 *
 * Generic wrapper for ECharts that handles loading states and responsive sizing.
 * All specific chart components use this as their base.
 */

import { ref, onMounted, onUnmounted } from 'vue';
import { VChart } from '../../utils/echarts';
import type { EChartsOption } from '../../utils/echarts';

interface Props {
  /** ECharts configuration option */
  option: EChartsOption;
  /** Chart height (default: 300px) */
  height?: string;
  /** Loading state */
  loading?: boolean;
  /** Auto-resize on window resize */
  autoresize?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  height: '300px',
  loading: false,
  autoresize: true,
});

const chartRef = ref<InstanceType<typeof VChart> | null>(null);

// Handle manual resize for complex layouts
function handleResize() {
  chartRef.value?.resize();
}

onMounted(() => {
  if (props.autoresize) {
    window.addEventListener('resize', handleResize);
  }
});

onUnmounted(() => {
  if (props.autoresize) {
    window.removeEventListener('resize', handleResize);
  }
});

// Expose chart instance for parent component access
defineExpose({
  chartRef,
  resize: handleResize,
});
</script>

<template>
  <div class="dashboard-chart" :style="{ height }">
    <a-spin :spinning="loading" tip="Загрузка...">
      <VChart
        ref="chartRef"
        :option="option"
        :autoresize="autoresize"
        :not-merge="true"
        class="chart-instance"
      />
    </a-spin>
  </div>
</template>

<style scoped>
.dashboard-chart {
  width: 100%;
  position: relative;
}

.chart-instance {
  width: 100%;
  height: 100%;
}

:deep(.ant-spin-nested-loading) {
  height: 100%;
}

:deep(.ant-spin-container) {
  height: 100%;
}
</style>
