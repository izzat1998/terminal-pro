<template>
  <div class="dashboard">
    <a-spin :spinning="loading">
      <!-- Hero Stats Row -->
      <a-row :gutter="[16, 16]" style="margin-bottom: 24px;">
        <!-- Primary Stat: Total on Terminal -->
        <a-col :xs="12" :sm="12" :lg="6">
          <a-card hoverable size="small">
            <a-statistic
              title="На терминале"
              :value="stats?.status?.total_on_terminal || 0"
              :value-style="{ color: '#1677ff' }"
              suffix="контейнеров"
            >
              <template #prefix><ContainerOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>

        <!-- Laden containers -->
        <a-col :xs="12" :sm="12" :lg="6">
          <a-card hoverable size="small">
            <a-statistic
              title="Гружёных"
              :value="stats?.status?.by_status?.LADEN || 0"
              :value-style="{ color: '#52c41a' }"
            >
              <template #prefix><CheckCircleOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>

        <!-- Empty containers -->
        <a-col :xs="12" :sm="12" :lg="6">
          <a-card hoverable size="small">
            <a-statistic
              title="Порожних"
              :value="stats?.status?.by_status?.EMPTY || 0"
              :value-style="{ color: '#faad14' }"
            >
              <template #prefix><InboxOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>

        <!-- Average dwell time -->
        <a-col :xs="12" :sm="12" :lg="6">
          <a-card hoverable size="small">
            <a-statistic
              title="Ср. простой (дней)"
              :value="(stats?.dwell?.average_dwell_days || 0).toFixed(1)"
            >
              <template #prefix><ClockCircleOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
      </a-row>

      <!-- Secondary Stats Row -->
      <a-row :gutter="[16, 16]">
        <!-- Transport Type Breakdown -->
        <a-col :xs="24" :lg="8">
          <a-card size="small">
            <template #title>
              <a-space>
                <CarOutlined style="color: #1677ff;" />
                <span>По типу транспорта</span>
              </a-space>
            </template>
            <a-list :data-source="transportData" :split="false">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #avatar>
                      <a-avatar :style="{ backgroundColor: item.color }">
                        <template #icon><component :is="item.icon" /></template>
                      </a-avatar>
                    </template>
                    <template #title>{{ item.label }}</template>
                  </a-list-item-meta>
                  <template #extra>
                    <span style="font-size: 18px; font-weight: 600;">{{ item.value }}</span>
                  </template>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </a-col>

        <!-- Dwell Time Alert -->
        <a-col :xs="24" :lg="8">
          <a-card size="small">
            <template #title>
              <a-space>
                <WarningOutlined style="color: #faad14;" />
                <span>Превышение срока</span>
                <a-badge v-if="stats?.dwell?.overstayer_count" :count="stats.dwell.overstayer_count" :overflow-count="99" />
              </a-space>
            </template>
            <template v-if="stats && stats.dwell && stats.dwell.overstayer_count > 0">
              <a-list :data-source="stats.dwell.overstayers.slice(0, 3)" :split="false" size="small">
                <template #renderItem="{ item }">
                  <a-list-item>
                    <span style="font-weight: 500;">{{ item.container__container_number }}</span>
                    <template #extra>
                      <a-tag :color="getDwellTimeColor(item.dwell_time_days)">
                        {{ item.dwell_time_days }} дн.
                      </a-tag>
                    </template>
                  </a-list-item>
                </template>
              </a-list>
              <div v-if="stats.dwell.overstayers.length > 3" style="text-align: center; color: #8c8c8c; padding: 8px;">
                +{{ stats.dwell.overstayers.length - 3 }} ещё
              </div>
            </template>
            <a-empty v-else :image="null" description="Всё в норме">
              <template #image>
                <CheckCircleOutlined style="font-size: 32px; color: #52c41a;" />
              </template>
            </a-empty>
          </a-card>
        </a-col>

        <!-- Cargo Summary -->
        <a-col :xs="24" :lg="8">
          <a-card size="small">
            <template #title>
              <a-space>
                <DatabaseOutlined style="color: #1677ff;" />
                <span>Груз на терминале</span>
              </a-space>
            </template>
            <a-row :gutter="8">
              <a-col :span="8" style="text-align: center;">
                <a-statistic :value="formatWeight(stats?.cargo?.total_weight_kg)" :value-style="{ fontSize: '18px' }" />
                <div style="font-size: 12px; color: #8c8c8c;">Всего груза</div>
              </a-col>
              <a-col :span="8" style="text-align: center; border-left: 1px solid #f0f0f0; border-right: 1px solid #f0f0f0;">
                <a-statistic :value="stats?.cargo?.laden_count || 0" :value-style="{ fontSize: '18px' }" />
                <div style="font-size: 12px; color: #8c8c8c;">Гружёных</div>
              </a-col>
              <a-col :span="8" style="text-align: center;">
                <a-statistic :value="formatWeight(stats?.cargo?.average_weight_kg)" :value-style="{ fontSize: '18px' }" />
                <div style="font-size: 12px; color: #8c8c8c;">Средний вес</div>
              </a-col>
            </a-row>
          </a-card>
        </a-col>
      </a-row>

    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { message } from 'ant-design-vue';
import {
  ContainerOutlined,
  CheckCircleOutlined,
  InboxOutlined,
  ClockCircleOutlined,
  CarOutlined,
  NodeIndexOutlined,
  WarningOutlined,
  DatabaseOutlined,
} from '@ant-design/icons-vue';
import { http } from '../../utils/httpClient';

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface StatisticsData {
  status: {
    total_on_terminal: number;
    by_status: { LADEN?: number; EMPTY?: number };
    by_transport: { TRUCK?: number; WAGON?: number };
  };
  dwell: {
    average_dwell_days: number;
    overstayer_count: number;
    overstayer_threshold_days: number;
    overstayers: Array<{
      id: number;
      container__container_number: string;
      dwell_time_days: number;
    }>;
    longest_stay: { container_number: string; days: number } | null;
  };
  cargo: {
    laden_count: number;
    total_weight_kg: number;
    average_weight_kg: number;
  };
  generated_at: string;
}

interface StatisticsResponse {
  success: boolean;
  data: StatisticsData;
}

const props = defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const stats = ref<StatisticsData | null>(null);
const loading = ref(false);

const transportData = computed(() => [
  {
    label: 'Авто',
    value: stats.value?.status?.by_transport?.TRUCK || 0,
    icon: CarOutlined,
    color: '#1677ff',
  },
  {
    label: 'Ж/Д вагон',
    value: stats.value?.status?.by_transport?.WAGON || 0,
    icon: NodeIndexOutlined,
    color: '#722ed1',
  },
]);

const formatWeight = (kg: number | undefined): string => {
  if (!kg) return '0 кг';
  if (kg >= 1000) return `${(kg / 1000).toFixed(1)} т`;
  return `${Math.round(kg)} кг`;
};

const getDwellTimeColor = (days: number): string => {
  if (days <= 3) return 'success';
  if (days <= 7) return 'warning';
  return 'error';
};

const fetchStatistics = async () => {
  loading.value = true;
  try {
    const result = await http.get<StatisticsResponse>('/customer/profile/statistics/');
    if (result.success) {
      stats.value = result.data;
    }
  } catch (error) {
    console.error('Error fetching statistics:', error);
    message.error(error instanceof Error ? error.message : 'Не удалось загрузить статистику. Попробуйте обновить страницу.');
  } finally {
    loading.value = false;
  }
};

watch(
  () => props.company,
  (newCompany) => {
    if (newCompany?.slug) {
      fetchStatistics();
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.dashboard {
  padding: 0;
}
</style>
