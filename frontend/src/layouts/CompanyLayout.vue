<template>
  <div class="company-layout">
    <Card style="margin-bottom: 15px;">
      <a-breadcrumb class="page-breadcrumb">
        <a-breadcrumb-item>
          <router-link to="/">Главная</router-link>
        </a-breadcrumb-item>
        <a-breadcrumb-item>
          <router-link to="/accounts/companies">Компании</router-link>
        </a-breadcrumb-item>
        <a-breadcrumb-item>{{ company?.name || 'Детали' }}</a-breadcrumb-item>
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
              <template v-else>Компания зарегистрирована {{ company?.created_at ? formatDateTime(company.created_at) :
                '' }}</template>
            </div>
          </div>
        </div>
      </div>

      <!-- Header Tabs -->
      <a-tabs v-if="company" v-model:activeKey="activeTab" class="header-tabs" @change="handleTabChange">
        <a-tab-pane key="info" tab="Информация" />
        <a-tab-pane key="users" tab="Пользователи" />
        <a-tab-pane key="orders" tab="Заказы" />
        <a-tab-pane key="containers" tab="Контейнеры" />
        <a-tab-pane key="settings" tab="Настройки" />
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
import { ref, onMounted, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Card, message } from 'ant-design-vue';
import { BankOutlined, LoadingOutlined } from '@ant-design/icons-vue';
import { formatDateTime } from '../utils/dateFormat';
import { http } from '../utils/httpClient';

export interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const route = useRoute();
const router = useRouter();
const company = ref<Company | null>(null);
const loading = ref(false);

// Determine active tab from current route
const activeTab = computed(() => {
  const routeName = route.name as string;
  if (routeName?.includes('Users')) return 'users';
  if (routeName?.includes('Orders')) return 'orders';
  if (routeName?.includes('Containers')) return 'containers';
  if (routeName?.includes('Settings')) return 'settings';
  return 'info';
});

const handleTabChange = (key: string) => {
  const slug = route.params.slug;
  const tabRoutes: Record<string, string> = {
    info: `/accounts/companies/${slug}`,
    users: `/accounts/companies/${slug}/users`,
    orders: `/accounts/companies/${slug}/orders`,
    containers: `/accounts/companies/${slug}/containers`,
    settings: `/accounts/companies/${slug}/settings`,
  };
  const targetRoute = tabRoutes[key];
  if (targetRoute) {
    router.push(targetRoute);
  }
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

// Watch for slug changes to refetch data
watch(() => route.params.slug, (newSlug) => {
  if (newSlug) {
    fetchCompany();
  }
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
  overflow-x: hidden;
}

.page-header {
  background: #fff;
  padding: 16px 24px 0;
  margin: -24px -24px 24px;
}

.header-tabs {
  margin-top: 16px;
}

.header-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 0;
}

.header-tabs :deep(.ant-tabs-nav::before) {
  border-bottom: none;
}

.page-breadcrumb {
  margin-bottom: 16px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.company-avatar {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  flex-shrink: 0;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.company-name {
  font-size: 20px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
}

.status-tag {
  margin: 0;
}

.header-description {
  color: rgba(0, 0, 0, 0.45);
  font-size: 14px;
}

.tab-content {
  min-height: 200px;
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
  }
}
</style>
