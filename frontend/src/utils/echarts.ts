/**
 * ECharts Setup - Tree-shakable Configuration
 *
 * Only imports chart types and components needed for the executive dashboard.
 * This significantly reduces bundle size compared to importing all of ECharts.
 */

import { use } from 'echarts/core';

// Renderers
import { CanvasRenderer } from 'echarts/renderers';

// Chart types
import { LineChart, BarChart, PieChart, GaugeChart } from 'echarts/charts';

// Components
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  ToolboxComponent,
} from 'echarts/components';

// Register required components
use([
  // Renderer
  CanvasRenderer,
  // Charts
  LineChart,
  BarChart,
  PieChart,
  GaugeChart,
  // Components
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  ToolboxComponent,
]);

// Re-export VChart component for use in Vue templates
export { default as VChart } from 'vue-echarts';

// Export types for chart options
export type { EChartsOption } from 'echarts';
export type {
  LineSeriesOption,
  BarSeriesOption,
  PieSeriesOption,
  GaugeSeriesOption,
} from 'echarts/charts';
export type {
  TitleComponentOption,
  TooltipComponentOption,
  LegendComponentOption,
  GridComponentOption,
} from 'echarts/components';
