<script setup lang="ts">
/**
 * KPI Card Component
 *
 * Displays a key performance indicator with optional trend indicator.
 * Used in the hero section of the executive dashboard.
 */

import { computed, type Component } from 'vue';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons-vue';

interface Props {
  /** Display value (number or pre-formatted string) */
  value: number | string;
  /** Label describing the metric */
  label: string;
  /** Ant Design icon component */
  icon: Component;
  /** Icon foreground color */
  iconColor?: string;
  /** Icon background color */
  iconBgColor?: string;
  /** Percentage trend (positive = up arrow green, negative = down arrow red) */
  trend?: number;
  /** Prefix for value display (e.g., "$") */
  prefix?: string;
  /** Suffix for value display (e.g., "%") */
  suffix?: string;
  /** Loading state */
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  iconColor: '#1677ff',
  iconBgColor: '#e6f4ff',
  loading: false,
});

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    return new Intl.NumberFormat('ru-RU').format(props.value);
  }
  return props.value;
});

const trendClass = computed(() => {
  if (!props.trend) return '';
  return props.trend >= 0 ? 'positive' : 'negative';
});

const trendIcon = computed(() => {
  if (!props.trend) return null;
  return props.trend >= 0 ? ArrowUpOutlined : ArrowDownOutlined;
});
</script>

<template>
  <a-card class="kpi-card" :bordered="false" :loading="loading">
    <div class="kpi-content">
      <div class="kpi-icon" :style="{ backgroundColor: iconBgColor }">
        <component :is="icon" :style="{ color: iconColor, fontSize: '24px' }" />
      </div>
      <div class="kpi-data">
        <div class="kpi-value">
          <span v-if="prefix" class="kpi-prefix">{{ prefix }}</span>
          {{ formattedValue }}
          <span v-if="suffix" class="kpi-suffix">{{ suffix }}</span>
        </div>
        <div class="kpi-label">{{ label }}</div>
        <div v-if="trend !== undefined" class="kpi-trend" :class="trendClass">
          <component :is="trendIcon" />
          <span>{{ Math.abs(trend) }}%</span>
        </div>
      </div>
    </div>
  </a-card>
</template>

<style scoped>
.kpi-card {
  height: 100%;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.kpi-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.kpi-content {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.kpi-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 12px;
  flex-shrink: 0;
}

.kpi-data {
  flex: 1;
  min-width: 0;
}

.kpi-value {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.2;
  color: #262626;
}

.kpi-prefix,
.kpi-suffix {
  font-size: 18px;
  font-weight: 500;
  color: #8c8c8c;
}

.kpi-label {
  font-size: 14px;
  color: #8c8c8c;
  margin-top: 4px;
}

.kpi-trend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  margin-top: 8px;
  padding: 2px 8px;
  border-radius: 4px;
}

.kpi-trend.positive {
  color: #52c41a;
  background-color: #f6ffed;
}

.kpi-trend.negative {
  color: #ff4d4f;
  background-color: #fff2f0;
}
</style>
