<template>
  <div class="company-layout">
    <Card style="margin-bottom: 15px;">
      <a-breadcrumb class="page-breadcrumb">
        <a-breadcrumb-item>
          <router-link to="/customer">Главная</router-link>
        </a-breadcrumb-item>
        <a-breadcrumb-item>{{ company?.name || 'Моя компания' }}</a-breadcrumb-item>
      </a-breadcrumb>

      <div class="header-content">
        <div class="header-left">
          <a-avatar :size="72" class="company-avatar">
            <template #icon>
              <BankOutlined />
            </template>
          </a-avatar>
          <div class="header-info">
            <div class="header-title">
              <span class="company-name">{{ company?.name || 'Загрузка...' }}</span>
              <a-tag v-if="loading" color="default" class="status-tag">
                <LoadingOutlined /> Загрузка...
              </a-tag>
              <a-tag v-else :color="company?.is_active ? 'green' : 'red'" class="status-tag">
                {{ company?.is_active ? 'Активна' : 'Неактивна' }}
              </a-tag>
            </div>
            <div class="header-description">
              <template v-if="loading">Загрузка данных...</template>
              <template v-else>Компания зарегистрирована {{ company?.created_at ? formatDateTime(company.created_at) : '' }}</template>
            </div>
          </div>
        </div>
      </div>

      <!-- Header Tabs -->
      <a-tabs v-if="company" v-model:activeKey="activeTab" class="header-tabs" @change="handleTabChange">
        <a-tab-pane key="dashboard" tab="Статистика" />
        <a-tab-pane key="containers" tab="Контейнеры" />
        <a-tab-pane key="billing" tab="Биллинг" />
        <a-tab-pane key="orders" tab="Заказы" />
        <a-tab-pane key="users" tab="Пользователи" />
      </a-tabs>
    </Card>

    <!-- Tab Content -->
    <div class="tab-content">
      <router-view v-slot="{ Component }">
        <component :is="Component" :company="company" :loading="loading" @updated="handleCompanyUpdated" />
      </router-view>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Card } from 'ant-design-vue';
import { BankOutlined, LoadingOutlined } from '@ant-design/icons-vue';
import { formatDateTime } from '../utils/dateFormat';
import { useAuth } from '../composables/useAuth';
import type { UserCompany } from '../services/userService';

const route = useRoute();
const router = useRouter();
const { user } = useAuth();

// Use company from user profile directly
const company = computed(() => user.value?.company || null);
const loading = computed(() => !user.value);

// Helper to determine tab from route name
const getTabFromRoute = (routeName: string | undefined): string => {
  if (routeName?.includes('Dashboard')) return 'dashboard';
  if (routeName?.includes('Containers')) return 'containers';
  if (routeName?.includes('Billing')) return 'billing';
  if (routeName?.includes('Orders')) return 'orders';
  if (routeName?.includes('Users')) return 'users';
  return 'dashboard';
};

// Active tab state (ref instead of computed so v-model can write to it)
const activeTab = ref(getTabFromRoute(route.name as string));

// Sync tab with route changes
watch(() => route.name, (newRouteName) => {
  activeTab.value = getTabFromRoute(newRouteName as string);
});

const handleTabChange = (key: string) => {
  const tabRoutes: Record<string, string> = {
    dashboard: '/customer/dashboard',
    containers: '/customer/containers',
    billing: '/customer/billing',
    orders: '/customer/orders',
    users: '/customer/users',
  };
  const targetRoute = tabRoutes[key];
  if (targetRoute) {
    router.push(targetRoute);
  }
};

const handleCompanyUpdated = (_updatedCompany: UserCompany) => {
  // Company is from user profile, refresh would need to update user
};
</script>

<style scoped>
.company-layout {
  min-height: 100%;
  overflow-x: hidden;
}

.page-header {
  background: var(--color-bg-card);
  padding: var(--space-4) var(--space-6) 0;
  margin: calc(-1 * var(--space-6)) calc(-1 * var(--space-6)) var(--space-6);
}

.header-tabs {
  margin-top: var(--space-4);
}

.header-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 0;
}

.header-tabs :deep(.ant-tabs-nav::before) {
  border-bottom: none;
}

.header-tabs :deep(.ant-tabs-tab) {
  padding: 12px 0;
  font-weight: 500;
  color: var(--color-text-secondary);
  transition: color var(--transition-fast);
}

.header-tabs :deep(.ant-tabs-tab:hover) {
  color: var(--color-primary);
}

.header-tabs :deep(.ant-tabs-tab-active .ant-tabs-tab-btn) {
  color: var(--color-primary);
  font-weight: 600;
}

.header-tabs :deep(.ant-tabs-ink-bar) {
  background: var(--color-primary);
  height: 3px;
  border-radius: 3px 3px 0 0;
}

.page-breadcrumb {
  margin-bottom: var(--space-4);
}

.page-breadcrumb :deep(.ant-breadcrumb-link),
.page-breadcrumb :deep(.ant-breadcrumb a) {
  color: var(--color-text-secondary);
  transition: color var(--transition-fast);
}

.page-breadcrumb :deep(.ant-breadcrumb a:hover) {
  color: var(--color-primary);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: var(--space-6);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.company-avatar {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
  flex-shrink: 0;
  box-shadow: 0 8px 24px rgba(0, 102, 255, 0.25);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.company-avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 12px 32px rgba(0, 102, 255, 0.35);
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.company-name {
  font-family: var(--font-body);
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: -0.02em;
}

.status-tag {
  margin: 0;
  font-weight: 500;
  border-radius: var(--radius-md);
}

.header-description {
  color: var(--color-text-secondary);
  font-size: 14px;
}

.tab-content {
  min-height: 200px;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Card enhancements */
:deep(.ant-card) {
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
  }

  .company-name {
    font-size: 20px;
  }
}
</style>
