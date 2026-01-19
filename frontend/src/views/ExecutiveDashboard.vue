<script setup lang="ts">
/**
 * Executive Dashboard View
 *
 * Comprehensive CEO/Executive dashboard displaying all terminal KPIs.
 * Features:
 * - 6 Hero KPI cards with key metrics
 * - 4 Main charts in responsive 2x2 grid
 * - 3 Secondary metric sections
 * - Auto-refresh every 5 minutes
 * - Manual refresh button
 */

import { computed } from 'vue';
import {
  ReloadOutlined,
  ContainerOutlined,
  DollarOutlined,
  LoginOutlined,
  LogoutOutlined,
  CarOutlined,
  TeamOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  HourglassOutlined,
} from '@ant-design/icons-vue';

// Dashboard components
import { KpiCard, ChartCard } from '../components/dashboard';

// Dashboard composable
import { useExecutiveDashboard } from '../composables/useExecutiveDashboard';

// Initialize dashboard with 5-minute auto-refresh
const {
  loading,
  lastUpdated,
  summary,
  throughput,
  vehicleMetrics,
  preorderStats,
  revenueChartOption,
  containerStatusChartOption,
  topCustomersChartOption,
  throughputChartOption,
  refresh,
} = useExecutiveDashboard(300000);

// Format time for display
const formattedTime = computed(() => {
  if (!lastUpdated.value) return '';
  return lastUpdated.value.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  });
});

// Format currency for display
function formatCurrency(value: string | undefined): string {
  if (!value) return '$0';
  const num = parseFloat(value);
  if (num >= 1000000) {
    return `$${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `$${(num / 1000).toFixed(1)}K`;
  }
  return `$${num.toFixed(0)}`;
}
</script>

<template>
  <div class="executive-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <div class="header-left">
        <h1 class="dashboard-title">Аналитика</h1>
        <span v-if="lastUpdated" class="last-updated">
          <ClockCircleOutlined /> Обновлено в {{ formattedTime }}
        </span>
      </div>
      <a-button type="primary" :loading="loading" @click="refresh">
        <template #icon><ReloadOutlined /></template>
        Обновить
      </a-button>
    </div>

    <a-spin :spinning="loading" tip="Загрузка данных...">
      <!-- Hero KPI Cards Section -->
      <section class="kpi-section">
        <a-row :gutter="[16, 16]">
          <a-col :xs="12" :sm="8" :lg="4">
            <KpiCard
              :value="summary?.total_containers_on_terminal ?? 0"
              label="Контейнеров на терминале"
              :icon="ContainerOutlined"
              icon-color="#1677ff"
              icon-bg-color="#e6f4ff"
              :loading="loading"
            />
          </a-col>
          <a-col :xs="12" :sm="8" :lg="4">
            <KpiCard
              :value="formatCurrency(summary?.total_revenue_usd)"
              label="Выручка (USD)"
              :icon="DollarOutlined"
              icon-color="#52c41a"
              icon-bg-color="#f6ffed"
              :loading="loading"
            />
          </a-col>
          <a-col :xs="12" :sm="8" :lg="4">
            <KpiCard
              :value="summary?.containers_entered_today ?? 0"
              label="Въехало сегодня"
              :icon="LoginOutlined"
              icon-color="#13c2c2"
              icon-bg-color="#e6fffb"
              :loading="loading"
            />
          </a-col>
          <a-col :xs="12" :sm="8" :lg="4">
            <KpiCard
              :value="summary?.containers_exited_today ?? 0"
              label="Выехало сегодня"
              :icon="LogoutOutlined"
              icon-color="#fa8c16"
              icon-bg-color="#fff7e6"
              :loading="loading"
            />
          </a-col>
          <a-col :xs="12" :sm="8" :lg="4">
            <KpiCard
              :value="vehicleMetrics?.total_on_terminal ?? 0"
              label="Транспорт на терминале"
              :icon="CarOutlined"
              icon-color="#722ed1"
              icon-bg-color="#f9f0ff"
              :loading="loading"
            />
          </a-col>
          <a-col :xs="12" :sm="8" :lg="4">
            <KpiCard
              :value="summary?.active_customers ?? 0"
              label="Активных клиентов"
              :icon="TeamOutlined"
              icon-color="#eb2f96"
              icon-bg-color="#fff0f6"
              :loading="loading"
            />
          </a-col>
        </a-row>
      </section>

      <!-- Main Charts Section (2x2 Grid) -->
      <section class="charts-section">
        <a-row :gutter="[16, 16]">
          <a-col :xs="24" :lg="12">
            <ChartCard title="Динамика выручки" :option="revenueChartOption" :loading="loading">
              <template #extra><a-tag color="green">30 дней</a-tag></template>
            </ChartCard>
          </a-col>
          <a-col :xs="24" :lg="12">
            <ChartCard title="Статус контейнеров" :option="containerStatusChartOption" :loading="loading">
              <template #extra>
                <a-space>
                  <a-tag color="blue">Гружёные</a-tag>
                  <a-tag color="cyan">Порожние</a-tag>
                </a-space>
              </template>
            </ChartCard>
          </a-col>
          <a-col :xs="24" :lg="12">
            <ChartCard title="Топ клиенты" :option="topCustomersChartOption" :loading="loading">
              <template #extra><a-tag color="purple">По выручке</a-tag></template>
            </ChartCard>
          </a-col>
          <a-col :xs="24" :lg="12">
            <ChartCard title="Пропускная способность" :option="throughputChartOption" :loading="loading">
              <template #extra>
                <a-space>
                  <a-tag color="green">Въезд</a-tag>
                  <a-tag color="orange">Выезд</a-tag>
                </a-space>
              </template>
            </ChartCard>
          </a-col>
        </a-row>
      </section>

      <!-- Secondary Metrics Section -->
      <section class="secondary-section">
        <a-row :gutter="[16, 16]">
          <!-- Throughput Summary -->
          <a-col :xs="24" :md="8">
            <a-card title="Пропускная способность" :bordered="false" class="metric-card">
              <a-row :gutter="[16, 16]">
                <a-col :span="12">
                  <a-statistic
                    title="За 7 дней"
                    :value="throughput?.last_7_days.entries ?? 0"
                    :value-style="{ color: '#52c41a' }"
                  >
                    <template #prefix><LoginOutlined /></template>
                    <template #suffix>въезд</template>
                  </a-statistic>
                </a-col>
                <a-col :span="12">
                  <a-statistic
                    title="За 7 дней"
                    :value="throughput?.last_7_days.exits ?? 0"
                    :value-style="{ color: '#fa8c16' }"
                  >
                    <template #prefix><LogoutOutlined /></template>
                    <template #suffix>выезд</template>
                  </a-statistic>
                </a-col>
                <a-col :span="24">
                  <a-statistic
                    title="Среднее в день"
                    :value="throughput?.daily_average ?? 0"
                    :precision="1"
                  >
                    <template #prefix><SyncOutlined /></template>
                  </a-statistic>
                </a-col>
              </a-row>
            </a-card>
          </a-col>

          <!-- Vehicle Metrics -->
          <a-col :xs="24" :md="8">
            <a-card title="Транспорт" :bordered="false" class="metric-card">
              <a-row :gutter="[16, 16]">
                <a-col :span="12">
                  <a-statistic
                    title="На терминале"
                    :value="vehicleMetrics?.total_on_terminal ?? 0"
                    :value-style="{ color: '#722ed1' }"
                  >
                    <template #prefix><CarOutlined /></template>
                  </a-statistic>
                </a-col>
                <a-col :span="12">
                  <a-statistic
                    title="Среднее время"
                    :value="vehicleMetrics?.avg_dwell_hours ?? 0"
                    :precision="1"
                    suffix="ч"
                  >
                    <template #prefix><ClockCircleOutlined /></template>
                  </a-statistic>
                </a-col>
                <a-col :span="24">
                  <div class="vehicle-breakdown">
                    <template v-for="(data, type) in vehicleMetrics?.by_type" :key="type">
                      <a-tag :color="type === 'CARGO' ? 'blue' : 'green'">
                        {{ data.label }}: {{ data.count }}
                      </a-tag>
                    </template>
                  </div>
                </a-col>
              </a-row>
            </a-card>
          </a-col>

          <!-- Pre-order Stats -->
          <a-col :xs="24" :md="8">
            <a-card title="Предзаказы" :bordered="false" class="metric-card">
              <a-row :gutter="[16, 16]">
                <a-col :span="12">
                  <a-statistic
                    title="Ожидают"
                    :value="preorderStats?.pending ?? 0"
                    :value-style="{ color: '#faad14' }"
                  >
                    <template #prefix><HourglassOutlined /></template>
                  </a-statistic>
                </a-col>
                <a-col :span="12">
                  <a-statistic
                    title="Сопоставлено"
                    :value="preorderStats?.matched ?? 0"
                    :value-style="{ color: '#1677ff' }"
                  >
                    <template #prefix><SyncOutlined /></template>
                  </a-statistic>
                </a-col>
                <a-col :span="24">
                  <a-statistic
                    title="Выполнено сегодня"
                    :value="preorderStats?.completed_today ?? 0"
                    :value-style="{ color: '#52c41a' }"
                  >
                    <template #prefix><CheckCircleOutlined /></template>
                  </a-statistic>
                </a-col>
              </a-row>
            </a-card>
          </a-col>
        </a-row>
      </section>
    </a-spin>
  </div>
</template>

<style scoped>
.executive-dashboard {
  padding: 24px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 16px;
}

.dashboard-title {
  font-size: 28px;
  font-weight: 600;
  color: #262626;
  margin: 0;
}

.last-updated {
  font-size: 14px;
  color: #8c8c8c;
  display: flex;
  align-items: center;
  gap: 6px;
}

.kpi-section {
  margin-bottom: 24px;
}

.charts-section {
  margin-bottom: 24px;
}

.secondary-section {
  margin-bottom: 24px;
}

.metric-card {
  height: 100%;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.vehicle-breakdown {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .executive-dashboard {
    padding: 16px;
  }

  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .dashboard-title {
    font-size: 22px;
  }
}
</style>
