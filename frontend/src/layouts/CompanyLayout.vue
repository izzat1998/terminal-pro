<template>
  <div class="company-layout">
    <!-- Header -->
    <div class="company-header">
      <div class="header-top">
        <a-button type="link" class="back-link" @click="router.push('/accounts/companies')">
          <ArrowLeftOutlined />
          Компании
        </a-button>
      </div>

      <div class="header-info">
        <a-avatar :size="48" class="company-avatar">
          <template #icon><BankOutlined /></template>
        </a-avatar>
        <div class="header-text">
          <div class="header-title">
            <span class="company-name">{{ company?.name || 'Загрузка...' }}</span>
            <a-tag v-if="loading" color="default"><LoadingOutlined /> Загрузка...</a-tag>
            <a-tag v-else :color="company?.is_active ? 'green' : 'red'">
              {{ company?.is_active ? 'Активна' : 'Неактивна' }}
            </a-tag>
          </div>
          <div class="header-meta">
            Создана {{ company?.created_at ? formatDateTime(company.created_at) : '...' }}
          </div>
        </div>
      </div>

      <!-- Stats Bar -->
      <div v-if="company" class="stats-bar">
        <div class="stat-card">
          <div class="stat-label">Баланс USD</div>
          <div class="stat-value" :class="{ 'stat-negative': Number(company.balance_usd) > 0 }">
            {{ Number(company.balance_usd) > 0 ? `-$${formatMoney(company.balance_usd)}` : '$0' }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Баланс UZS</div>
          <div class="stat-value" :class="{ 'stat-negative': Number(company.balance_uzs) > 0 }">
            {{ Number(company.balance_uzs) > 0 ? `${formatMoney(company.balance_uzs)} сум` : '0 сум' }}
          </div>
        </div>
        <div
          class="stat-card stat-clickable"
          @click="navigateTo('containers')"
        >
          <div class="stat-label">На терминале</div>
          <div class="stat-value">{{ company.entries_count }}</div>
        </div>
        <div
          class="stat-card stat-clickable"
          @click="navigateTo('users')"
        >
          <div class="stat-label">Клиентов</div>
          <div class="stat-value">{{ company.customers_count }}</div>
        </div>
      </div>
    </div>

    <!-- Body: Sidebar + Content -->
    <div class="company-body">
      <div class="company-sidebar">
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="inline"
          :inline-collapsed="false"
          @click="handleMenuClick"
        >
          <a-menu-item-group title="ОСНОВНОЕ">
            <a-menu-item key="info">
              <template #icon><InfoCircleOutlined /></template>
              Реквизиты
            </a-menu-item>
          </a-menu-item-group>

          <a-menu-item-group title="КЛИЕНТЫ">
            <a-menu-item key="users">
              <template #icon><TeamOutlined /></template>
              Список
            </a-menu-item>
            <a-menu-item key="orders">
              <template #icon><FileTextOutlined /></template>
              Заказы
            </a-menu-item>
          </a-menu-item-group>

          <a-menu-item-group title="СКЛАД">
            <a-menu-item key="containers">
              <template #icon><ContainerOutlined /></template>
              Контейнеры
            </a-menu-item>
          </a-menu-item-group>

          <a-menu-item-group title="РАСЧЁТЫ">
            <a-menu-item key="billing-current">
              <template #icon><DollarOutlined /></template>
              Текущие
            </a-menu-item>
            <a-menu-item key="billing-statements">
              <template #icon><AuditOutlined /></template>
              Акты
            </a-menu-item>
            <a-menu-item key="billing-invoices">
              <template #icon><FileProtectOutlined /></template>
              Счета
              <a-badge
                v-if="company?.draft_invoices_count"
                :count="company.draft_invoices_count"
                :number-style="{ backgroundColor: '#faad14', marginLeft: '8px' }"
              />
            </a-menu-item>
          </a-menu-item-group>

          <a-menu-item-group title="НАСТРОЙКИ">
            <a-menu-item key="settings-telegram">
              <template #icon><SendOutlined /></template>
              Telegram
            </a-menu-item>
            <a-menu-item key="settings-general">
              <template #icon><SettingOutlined /></template>
              Общие
            </a-menu-item>
          </a-menu-item-group>
        </a-menu>
      </div>

      <div class="company-content">
        <router-view v-slot="{ Component }">
          <component
            :is="Component"
            :company="company"
            :company-slug="company?.slug"
            :loading="loading"
            @updated="handleCompanyUpdated"
          />
        </router-view>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import {
  ArrowLeftOutlined,
  BankOutlined,
  LoadingOutlined,
  InfoCircleOutlined,
  TeamOutlined,
  FileTextOutlined,
  ContainerOutlined,
  DollarOutlined,
  AuditOutlined,
  FileProtectOutlined,
  SendOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue';
import { formatDateTime } from '../utils/dateFormat';
import { http } from '../utils/httpClient';
import type { Company } from '../types/company';

const route = useRoute();
const router = useRouter();
const company = ref<Company | null>(null);
const loading = ref(false);

const formatMoney = (value: string): string => {
  const num = Number(value);
  if (isNaN(num) || num === 0) return '0';
  return num.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
};

// Map route names to sidebar menu keys
const menuKeyMap: Record<string, string> = {
  CompanyInfo: 'info',
  CompanyUsers: 'users',
  CompanyOrders: 'orders',
  CompanyContainers: 'containers',
  CompanyBillingCurrent: 'billing-current',
  CompanyBillingStatements: 'billing-statements',
  CompanyBillingInvoices: 'billing-invoices',
  CompanySettingsTelegram: 'settings-telegram',
  CompanySettingsGeneral: 'settings-general',
};

// Reverse map: menu key → route path suffix
const routeMap: Record<string, string> = {
  'info': '',
  'users': '/users',
  'orders': '/orders',
  'containers': '/containers',
  'billing-current': '/billing/current',
  'billing-statements': '/billing/statements',
  'billing-invoices': '/billing/invoices',
  'settings-telegram': '/settings/telegram',
  'settings-general': '/settings/general',
};

const selectedKeys = computed(() => {
  const routeName = route.name as string;
  const key = menuKeyMap[routeName] || 'info';
  return [key];
});

const handleMenuClick = ({ key }: { key: string }) => {
  const slug = route.params.slug;
  const suffix = routeMap[key] ?? '';
  router.push(`/accounts/companies/${slug}${suffix}`);
};

const navigateTo = (section: string) => {
  const slug = route.params.slug;
  const suffix = routeMap[section] ?? '';
  router.push(`/accounts/companies/${slug}${suffix}`);
};

const fetchCompany = async () => {
  try {
    loading.value = true;
    const slug = route.params.slug;
    const result = await http.get<{ data: Company }>(`/auth/companies/${slug}/`);
    company.value = result.data;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка загрузки данных');
  } finally {
    loading.value = false;
  }
};

watch(() => route.params.slug, (newSlug) => {
  if (newSlug) fetchCompany();
});

const handleCompanyUpdated = (updatedCompany: Company) => {
  company.value = updatedCompany;
};

onMounted(() => {
  fetchCompany();
});
</script>

<style scoped>
.company-layout {
  min-height: 100%;
}

/* Header */
.company-header {
  background: #fff;
  border-radius: 6px;
  padding: 16px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.header-top {
  margin-bottom: 12px;
}

.back-link {
  padding: 0;
  color: rgba(0, 0, 0, 0.45);
  font-size: 14px;
  height: auto;
}

.back-link:hover {
  color: #1890ff;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.company-avatar {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  flex-shrink: 0;
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.company-name {
  font-size: 20px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}

.header-meta {
  color: rgba(0, 0, 0, 0.45);
  font-size: 13px;
}

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 120px;
  background: #fafafa;
  border-radius: 6px;
  padding: 12px 16px;
  border: 1px solid #f0f0f0;
  transition: all 0.2s;
}

.stat-clickable {
  cursor: pointer;
}

.stat-clickable:hover {
  border-color: #1890ff;
  background: #e6f7ff;
}

.stat-label {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}

.stat-negative {
  color: #cf1322;
}

/* Body */
.company-body {
  display: flex;
  gap: 16px;
  min-height: 500px;
}

.company-sidebar {
  width: 200px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  padding: 8px 0;
  align-self: flex-start;
  position: sticky;
  top: 16px;
}

.company-sidebar :deep(.ant-menu) {
  border-inline-end: none !important;
}

.company-sidebar :deep(.ant-menu-item-group-title) {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: rgba(0, 0, 0, 0.35);
  padding: 12px 16px 4px;
}

.company-sidebar :deep(.ant-menu-item) {
  height: 36px;
  line-height: 36px;
  margin: 2px 8px;
  border-radius: 4px;
  padding-left: 16px !important;
}

.company-content {
  flex: 1;
  min-width: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .company-body {
    flex-direction: column;
  }

  .company-sidebar {
    width: 100%;
    position: static;
  }

  .company-sidebar :deep(.ant-menu) {
    display: flex;
    flex-wrap: wrap;
  }

  .company-sidebar :deep(.ant-menu-item-group) {
    flex: 1;
    min-width: 150px;
  }

  .stats-bar {
    flex-wrap: wrap;
  }

  .stat-card {
    min-width: calc(50% - 8px);
    flex: unset;
  }
}
</style>
