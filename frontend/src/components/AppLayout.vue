<template>
  <a-layout style="min-height: 100vh;">
    <a-layout-sider v-if="isAdmin" v-model:collapsed="collapsed" :trigger="null" collapsible theme="light"
      :style="{ overflow: 'auto', height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0 }">
      <div class="logo">
        <span v-if="!collapsed">MTT Terminal</span>
        <span v-else>MTT</span>
      </div>
      <a-menu :style="{ padding: '0 5px' }" v-model:selectedKeys="selectedKeys" v-model:openKeys="openKeys"
        theme="light" mode="inline" @click="handleMenuClick">

        <!-- Dashboard -->
        <a-menu-item key="dashboard">
          <DashboardOutlined />
          <span>Главная</span>
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
        <a-menu-item key="telegram-bot">
          <RobotOutlined />
          <span>Telegram Бот</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout :style="isAdmin ? { marginLeft: collapsed ? '80px' : '200px', transition: 'margin-left 0.2s' } : {}">
      <a-layout-header
        style="background: #fff; padding: 0; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100;">

        <template v-if="isAdmin">
          <menu-unfold-outlined v-if="collapsed" class="trigger" @click="() => (collapsed = !collapsed)" />
          <menu-fold-outlined v-else class="trigger" @click="() => (collapsed = !collapsed)" />
        </template>
        <div v-else>
          <div class="logo" style="padding: 0 15px;">
            <span v-if="!collapsed">MTT SYSTEM</span>
            <span v-else>MTT</span>
          </div>
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
      <a-layout-content :style="{ margin: '24px 16px' }">
        <router-view />
      </a-layout-content>
      <a-layout-footer style="text-align: center;">
        MTT
      </a-layout-footer>
    </a-layout>
  </a-layout>
</template>

<script lang="ts" setup>
import { computed, ref, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import {
  UserOutlined,
  DownOutlined,
  LogoutOutlined,
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  ContainerOutlined,
  TeamOutlined,
  CarOutlined,
  BankOutlined,
  DashboardOutlined,
  ShopOutlined,
  IdcardOutlined,
  RobotOutlined,
} from '@ant-design/icons-vue';
import { useAuth } from '../composables/useAuth';

const router = useRouter();
const route = useRoute();
const { user, logout } = useAuth();
const selectedKeys = ref<string[]>(['dashboard']);
const openKeys = ref<string[]>([]);
const collapsed = ref<boolean>(false);

// Route to menu key mapping
const routeToKey: Record<string, string> = {
  '/': 'dashboard',
  '/dashboard': 'dashboard',
  '/gate': 'gate',
  '/vehicles': 'gate',
  '/containers': 'containers',
  '/accounts/companies': 'companies',
  '/owners': 'owners',
  '/vehicles-customers': 'vehicles-customers',
  '/managers': 'managers',
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
  'gate': '/gate',
  'containers': '/containers',
  'companies': '/accounts/companies',
  'owners': '/owners',
  'vehicles-customers': '/vehicles-customers',
  'managers': '/managers',
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
.trigger {
  font-size: 18px;
  line-height: 64px;
  padding: 0 24px;
  cursor: pointer;
  transition: color var(--transition-fast);
  color: var(--color-text-secondary);
}

.trigger:hover {
  color: var(--color-primary);
}

.logo {
  height: 40px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
  margin: 16px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.5px;
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 12px rgba(0, 102, 255, 0.25);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.logo:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(0, 102, 255, 0.35);
}

.user-dropdown {
  color: var(--color-text);
  padding: 0 24px;
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: color var(--transition-fast);
  font-weight: 500;
}

.user-dropdown:hover {
  color: var(--color-primary);
}

/* Sidebar enhancements */
:deep(.ant-layout-sider) {
  border-right: 1px solid var(--color-border-light);
}

:deep(.ant-menu-item) {
  margin: 4px 8px;
  border-radius: var(--radius-md);
}

:deep(.ant-menu-item-group-title) {
  padding: 16px 16px 8px 16px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-text-muted);
}

:deep(.ant-divider) {
  margin: 8px 0;
  border-color: var(--color-border-light);
}
</style>
