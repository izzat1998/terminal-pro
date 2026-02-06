<template>
  <div class="dashboard">
    <h1 class="dashboard-title">Панель управления</h1>

    <!-- Stats Row -->
    <a-row :gutter="[16, 16]" style="margin-bottom: 24px;">
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card class="stat-card" :loading="loading">
          <a-statistic
            title="Контейнеров на терминале"
            :value="stats.containersOnTerminal"
            :value-style="{ color: 'var(--color-primary)' }"
          >
            <template #prefix>
              <ContainerOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card class="stat-card" :loading="loading">
          <a-statistic
            title="Транспорт на территории"
            :value="stats.vehiclesOnTerminal"
            :value-style="{ color: 'var(--color-entry)' }"
          >
            <template #prefix>
              <CarOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card class="stat-card" :loading="loading">
          <a-statistic
            title="Активных компаний"
            :value="stats.activeCompanies"
            :value-style="{ color: 'var(--color-info)' }"
          >
            <template #prefix>
              <BankOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card class="stat-card" :loading="loading">
          <a-statistic
            title="Менеджеров онлайн"
            :value="stats.activeManagers"
            :value-style="{ color: 'var(--color-success)' }"
          >
            <template #prefix>
              <TeamOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- Quick Actions -->
    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :lg="12">
        <a-card title="Быстрые действия" :bordered="false">
          <a-space direction="vertical" style="width: 100%;">
            <a-button type="primary" block @click="$router.push('/containers')">
              <template #icon><ContainerOutlined /></template>
              Просмотр контейнеров
            </a-button>
            <a-button block @click="$router.push('/vehicles')">
              <template #icon><CarOutlined /></template>
              Журнал транспорта
            </a-button>
            <a-button block @click="$router.push('/accounts/companies')">
              <template #icon><DollarOutlined /></template>
              Биллинг компаний
            </a-button>
          </a-space>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="12">
        <a-card title="Сводка за сегодня" :bordered="false">
          <a-descriptions :column="1" size="small">
            <a-descriptions-item label="Въехало контейнеров">
              <a-tag color="green">{{ stats.containersEnteredToday }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="Выехало контейнеров">
              <a-tag color="blue">{{ stats.containersExitedToday }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="Въехало транспорта">
              <a-tag color="green">{{ stats.vehiclesEnteredToday }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="Выехало транспорта">
              <a-tag color="blue">{{ stats.vehiclesExitedToday }}</a-tag>
            </a-descriptions-item>
          </a-descriptions>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { ContainerOutlined, CarOutlined, BankOutlined, TeamOutlined, DollarOutlined } from '@ant-design/icons-vue';
import { http } from '../utils/httpClient';
import dayjs from '@/config/dayjs';

interface DashboardStats {
  containersOnTerminal: number;
  vehiclesOnTerminal: number;
  activeCompanies: number;
  activeManagers: number;
  containersEnteredToday: number;
  containersExitedToday: number;
  vehiclesEnteredToday: number;
  vehiclesExitedToday: number;
}

const loading = ref(true);
const stats = ref<DashboardStats>({
  containersOnTerminal: 0,
  vehiclesOnTerminal: 0,
  activeCompanies: 0,
  activeManagers: 0,
  containersEnteredToday: 0,
  containersExitedToday: 0,
  vehiclesEnteredToday: 0,
  vehiclesExitedToday: 0,
});

const fetchStats = async () => {
  try {
    loading.value = true;

    // Fetch from multiple endpoints in parallel
    const [containersRes, vehiclesRes, companiesRes, managersRes] = await Promise.all([
      http.get<any>('/terminal/entries/?has_exited=false&page_size=1'),
      http.get<any>('/vehicles/entries/?status=ON_TERMINAL&page_size=1'),
      http.get<any>('/auth/companies/stats/'),
      http.get<any>('/auth/managers/stats/'),
    ]);

    stats.value.containersOnTerminal = containersRes.count || 0;
    stats.value.vehiclesOnTerminal = vehiclesRes.count || 0;
    stats.value.activeCompanies = companiesRes.data?.active_companies || 0;
    stats.value.activeManagers = managersRes.data?.managers_with_access || 0;

    // Today's stats - simplified (could add dedicated endpoint)
    const today = dayjs().format('YYYY-MM-DD');
    const [todayContainers, todayVehicles] = await Promise.all([
      http.get<any>(`/terminal/entries/?entry_date_after=${today}&page_size=1`),
      http.get<any>(`/vehicles/entries/?entry_date_after=${today}&page_size=1`),
    ]);

    stats.value.containersEnteredToday = todayContainers.count || 0;
    stats.value.vehiclesEnteredToday = todayVehicles.count || 0;

  } catch (error) {
    console.error('Failed to fetch dashboard stats:', error);
    message.error('Не удалось загрузить статистику панели управления. Попробуйте обновить страницу.');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchStats();
});
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.dashboard-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 24px;
  color: var(--color-text);
}

.stat-card {
  height: 100%;
}

.stat-card :deep(.ant-statistic-title) {
  font-size: 13px;
}

.stat-card :deep(.ant-statistic-content-prefix) {
  margin-right: 8px;
}
</style>
