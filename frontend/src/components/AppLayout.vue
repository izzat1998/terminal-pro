<template>
  <a-layout style="min-height: 100vh;">
    <!-- Dark sidebar with nested ConfigProvider -->
    <a-config-provider v-if="isAdmin" :theme="sidebarTheme">
      <a-layout-sider v-model:collapsed="collapsed" :trigger="null" collapsible theme="dark"
        :style="{ overflow: 'auto', height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0, display: 'flex', flexDirection: 'column' }">
        <div class="logo">
          <span v-if="!collapsed">MTT Terminal</span>
          <span v-else>MTT</span>
        </div>
        <a-menu :style="{ padding: '0 5px' }" v-model:selectedKeys="selectedKeys" v-model:openKeys="openKeys"
          theme="dark" mode="inline" @click="handleMenuClick">

          <!-- Dashboard -->
          <a-menu-item key="dashboard">
            <DashboardOutlined />
            <span>Главная</span>
          </a-menu-item>
          <a-menu-item key="executive">
            <FundOutlined />
            <span>Аналитика</span>
          </a-menu-item>

          <!-- КПП Section -->
          <a-menu-item-group v-if="!collapsed" title="КПП" />
          <a-divider v-if="collapsed" style="margin: 8px 16px;" />

          <a-menu-item key="gate">
            <CarOutlined />
            <span>Журнал КПП</span>
          </a-menu-item>

          <!-- Operations Section -->
          <a-menu-item-group v-if="!collapsed" title="Операции" />
          <a-divider v-if="collapsed" style="margin: 8px 16px;" />

          <a-menu-item key="containers">
            <ContainerOutlined />
            <span>Контейнеры</span>
          </a-menu-item>
          <a-menu-item key="placement">
            <AppstoreOutlined />
            <span>Площадка 3D</span>
          </a-menu-item>
          <a-menu-item key="tasks">
            <UnorderedListOutlined />
            <span>Задания</span>
            <a-badge
              v-if="!collapsed && taskCount > 0"
              :count="taskCount"
              :number-style="{ backgroundColor: '#1677ff', marginLeft: '8px' }"
            />
          </a-menu-item>

          <!-- Directory Section -->
          <a-menu-item-group v-if="!collapsed" title="Справочники" />
          <a-divider v-if="collapsed" style="margin: 8px 16px;" />

          <a-menu-item key="companies">
            <BankOutlined />
            <span>Компании</span>
          </a-menu-item>
          <a-menu-item key="owners">
            <ShopOutlined />
            <span>Собственники</span>
          </a-menu-item>
          <a-menu-item key="vehicles-customers">
            <IdcardOutlined />
            <span>Клиенты</span>
          </a-menu-item>

          <!-- Users Section -->
          <a-menu-item-group v-if="!collapsed" title="Управление" />
          <a-divider v-if="collapsed" style="margin: 8px 16px;" />

          <a-menu-item key="managers">
            <TeamOutlined />
            <span>Менеджеры</span>
          </a-menu-item>
          <a-menu-item key="terminal-vehicles">
            <ToolOutlined />
            <span>Техника</span>
          </a-menu-item>
          <a-menu-item key="tariffs">
            <DollarOutlined />
            <span>Тарифы</span>
          </a-menu-item>
          <a-menu-item key="telegram-bot">
            <RobotOutlined />
            <span>Telegram Бот</span>
          </a-menu-item>
        </a-menu>

        <!-- Vehicle Status Panel -->
        <SidebarVehicleStatus :collapsed="collapsed" />
      </a-layout-sider>
    </a-config-provider>

    <a-layout :style="isAdmin ? { marginLeft: collapsed ? '80px' : '200px', transition: 'margin-left 0.2s' } : {}">
      <a-layout-header class="app-header">
        <template v-if="isAdmin">
          <menu-unfold-outlined v-if="collapsed" class="trigger" @click="() => (collapsed = !collapsed)" />
          <menu-fold-outlined v-else class="trigger" @click="() => (collapsed = !collapsed)" />
        </template>
        <div v-else>
          <div class="logo header-logo">
            <span v-if="!collapsed">MTT SYSTEM</span>
            <span v-else>MTT</span>
          </div>
        </div>

        <!-- Container History Search (admin only) - centered -->
        <div v-if="isAdmin" class="header-search">
          <a-input-search
            v-model:value="containerSearchQuery"
            placeholder="История контейнера..."
            style="width: 240px;"
            allow-clear
            @search="handleContainerSearch"
            @pressEnter="handleContainerSearch"
          >
            <template #prefix>
              <HistoryOutlined style="color: rgba(255,255,255,0.5);" />
            </template>
          </a-input-search>
        </div>

        <!-- User Dropdown -->
        <a-dropdown :trigger="['click']">
          <a class="user-dropdown" @click.prevent>
            <UserOutlined style="margin-right: 8px;" />
            <span>{{ user?.first_name || user?.username || 'Пользователь' }}</span>
            <DownOutlined style="margin-left: 8px;" />
          </a>
          <template #overlay>
            <a-menu>
              <a-menu-item key="logout" @click="handleLogout">
                <LogoutOutlined style="margin-right: 8px;" />
                Выйти
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </a-layout-header>
      <a-layout-content :style="{ margin: '16px 16px' }">
        <router-view />
      </a-layout-content>
      <a-layout-footer style="text-align: center;">
        MTT
      </a-layout-footer>
    </a-layout>

    <!-- Container Full History Modal -->
    <ContainerFullHistoryModal
      v-model:open="containerHistoryModalVisible"
      :container-number="containerHistoryNumber"
    />
  </a-layout>
</template>

<script lang="ts" setup>
import { computed, ref, watch, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import {
  AppstoreOutlined,
  BankOutlined,
  CarOutlined,
  ContainerOutlined,
  DashboardOutlined,
  DollarOutlined,
  DownOutlined,
  FundOutlined,
  HistoryOutlined,
  IdcardOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
  ShopOutlined,
  TeamOutlined,
  ToolOutlined,
  UnorderedListOutlined,
  UserOutlined,
} from '@ant-design/icons-vue';
import { useAuth } from '../composables/useAuth';
import { sidebarTheme } from '../theme';
import { getActiveWorkOrdersCount } from '../services/workOrderService';
import SidebarVehicleStatus from './SidebarVehicleStatus.vue';
import ContainerFullHistoryModal from './ContainerFullHistoryModal.vue';

const router = useRouter();
const route = useRoute();
const { user, logout } = useAuth();
const selectedKeys = ref<string[]>(['dashboard']);
const openKeys = ref<string[]>([]);
const collapsed = ref<boolean>(false);
const taskCount = ref<number>(0);

// Container history search state
const containerSearchQuery = ref('');
const containerHistoryModalVisible = ref(false);
const containerHistoryNumber = ref('');

function handleContainerSearch() {
  const query = containerSearchQuery.value.trim().toUpperCase();
  if (!query) return;

  containerHistoryNumber.value = query;
  containerHistoryModalVisible.value = true;
}

// Fetch active work orders count for sidebar badge
async function fetchTaskCount(): Promise<void> {
  try {
    taskCount.value = await getActiveWorkOrdersCount();
  } catch {
    // Silently fail - badge just won't show
    taskCount.value = 0;
  }
}

// Refresh task count periodically
onMounted(() => {
  fetchTaskCount();
  // Refresh every 60 seconds
  setInterval(fetchTaskCount, 60_000);
});

// Route to menu key mapping
const routeToKey: Record<string, string> = {
  '/': 'dashboard',
  '/dashboard': 'dashboard',
  '/executive': 'executive',
  '/gate': 'gate',
  '/vehicles': 'gate',
  '/containers': 'containers',
  '/placement': 'placement',
  '/tasks': 'tasks',
  '/accounts/companies': 'companies',
  '/owners': 'owners',
  '/vehicles-customers': 'vehicles-customers',
  '/managers': 'managers',
  '/terminal-vehicles': 'terminal-vehicles',
  '/tariffs': 'tariffs',
  '/telegram-bot': 'telegram-bot',
};

// Update selected keys based on current route
watch(() => route.path, (newPath) => {
  // Find matching route (check longer paths first)
  const sortedRoutes = Object.keys(routeToKey).sort((a, b) => b.length - a.length);
  for (const routePath of sortedRoutes) {
    if (newPath.startsWith(routePath) || newPath.includes(routePath.slice(1))) {
      selectedKeys.value = [routeToKey[routePath] as string];
      break;
    }
  }
}, { immediate: true });

// Menu key to route mapping
const keyToRoute: Record<string, string> = {
  'dashboard': '/',
  'executive': '/executive',
  'gate': '/gate',
  'containers': '/containers',
  'placement': '/placement',
  'tasks': '/tasks',
  'companies': '/accounts/companies',
  'owners': '/owners',
  'vehicles-customers': '/vehicles-customers',
  'managers': '/managers',
  'terminal-vehicles': '/terminal-vehicles',
  'tariffs': '/tariffs',
  'telegram-bot': '/telegram-bot',
};

const handleMenuClick = ({ key }: { key: string }) => {
  const route = keyToRoute[key];
  if (route) {
    router.push(route);
  }
};

const handleLogout = () => {
  logout();
  router.push('/login');
};

const isAdmin = computed(() => user.value?.user_type === 'admin')
</script>

<style scoped>
/* Header styling */
.app-header {
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

/* Header trigger - compact */
.trigger {
  font-size: 16px;
  line-height: 48px;
  padding: 0 16px;
  cursor: pointer;
  transition: color 0.15s ease;
  color: rgba(255, 255, 255, 0.7);
}

.trigger:hover {
  color: #3b82f6;
}

/* Logo - compact corporate style */
.logo {
  height: 32px;
  background: #3b82f6;
  margin: 12px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  font-size: 12px;
  letter-spacing: 0.3px;
  border-radius: 4px;
  transition: background 0.15s ease;
}

.logo:hover {
  background: #2563eb;
}

.header-logo {
  margin: 0;
  padding: 0 15px;
}

/* User dropdown - compact */
.user-dropdown {
  color: rgba(255, 255, 255, 0.7);
  padding: 0 16px;
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: color 0.15s ease;
  font-size: 12px;
  font-weight: 500;
}

.user-dropdown:hover {
  color: #3b82f6;
}

/* Header search - centered */
.header-search {
  flex: 1;
  display: flex;
  justify-content: center;
}

.header-search :deep(.ant-input-search) {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.header-search :deep(.ant-input) {
  background: transparent;
  color: rgba(255, 255, 255, 0.85);
  border: none;
}

.header-search :deep(.ant-input::placeholder) {
  color: rgba(255, 255, 255, 0.45);
}

.header-search :deep(.ant-input-search-button) {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: rgba(255, 255, 255, 0.65);
}

.header-search :deep(.ant-input-search-button:hover) {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.header-search :deep(.ant-input-clear-icon) {
  color: rgba(255, 255, 255, 0.45);
}

.header-search :deep(.ant-input-clear-icon:hover) {
  color: rgba(255, 255, 255, 0.85);
}

/* Menu group titles */
:deep(.ant-menu-item-group-title) {
  padding: 16px 16px 8px 16px;
}

/* Dividers */
:deep(.ant-divider) {
  margin: 8px 0;
  border-color: rgba(255, 255, 255, 0.1);
}
</style>
