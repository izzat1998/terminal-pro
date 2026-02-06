import { createRouter, createWebHistory } from 'vue-router';
import ContainerTable from '../components/ContainerTable.vue';
import LoginView from '../views/LoginView.vue';
import ContainerOwners from '../views/ContainerOwners.vue';
import Managers from '../views/Managers.vue';
import Vehicles from '../views/Vehicles.vue';
import VehiclesCustomers from '../views/VehiclesCustomers.vue';
import Companies from '../views/Companies.vue';
import Dashboard from '../views/Dashboard.vue';
import CompanyLayout from '../layouts/CompanyLayout.vue';
import CustomerLayout from '../layouts/CustomerLayout.vue';
import CompanyInfo from '../views/company/CompanyInfo.vue';
import CompanyUsers from '../views/company/CompanyUsers.vue';
import CompanyOrders from '../views/company/CompanyOrders.vue';
import CustomerPreOrders from '../views/customer/PreOrders.vue';
import CustomerContainers from '../views/customer/Containers.vue';
import CustomerUsers from '../views/customer/Users.vue';
import CustomerDashboard from '../views/customer/Dashboard.vue';
import CustomerBilling from '../views/customer/Billing.vue';
import CompanyContainers from '../views/company/CompanyContainers.vue';
import CurrentCosts from '../components/billing/CurrentCosts.vue';
import MonthlyStatements from '../components/billing/MonthlyStatements.vue';
import OnDemandInvoices from '../components/billing/OnDemandInvoices.vue';
import { useAuth } from '../composables/useAuth';
import AppLayout from '../components/AppLayout.vue'

export type UserRole = 'admin' | 'customer';

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean;
    title?: string;
    roles?: UserRole[];
  }
}

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('../views/LandingView.vue'),
    meta: { requiresAuth: false, title: 'МТТ - Container Terminal Management' },
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false, title: 'Вход - МТТ' },
  },
  {
    path: '/unauthorized',
    name: 'Unauthorized',
    component: () => import('../views/UnauthorizedView.vue'),
    meta: { requiresAuth: true, title: 'Нет доступа - МТТ' },
  },
  // Standalone test routes (only available in development)
  ...(import.meta.env.DEV ? [
    {
      path: '/yard-test-dev',
      name: 'YardTestDev',
      component: () => import('../views/UnifiedYardView.vue'),
      meta: { requiresAuth: false, title: 'Тест 3D Площадки - МТТ' },
    },
    {
      path: '/gate-test',
      name: 'GateCameraTest',
      component: () => import('../views/GateCameraTestView.vue'),
      meta: { requiresAuth: false, title: 'Тест камеры ворот - МТТ' },
    },
  ] : []),
  {
    path: '/app',
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: Dashboard,
        meta: { title: 'Главная - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/executive',
        name: 'ExecutiveDashboard',
        component: () => import('../views/ExecutiveDashboard.vue'),
        meta: { title: 'Аналитика - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/customer',
        component: CustomerLayout,
        meta: { title: 'Моя компания - МТТ', roles: ['customer', 'admin'] as UserRole[] },
        children: [
          {
            path: '',
            redirect: '/customer/dashboard',
          },
          {
            path: 'dashboard',
            name: 'CustomerDashboard',
            component: CustomerDashboard,
            meta: { title: 'Статистика - МТТ', roles: ['customer'] as UserRole[] },
          },
          {
            path: 'containers',
            name: 'CustomerContainers',
            component: CustomerContainers,
            meta: { title: 'Контейнеры компании - МТТ', roles: ['customer'] as UserRole[] },
          },
          {
            path: 'orders',
            name: 'CustomerOrders',
            component: CustomerPreOrders,
            meta: { title: 'Заказы компании - МТТ', roles: ['customer'] as UserRole[] },
          },
          {
            path: 'users',
            name: 'CustomerUsers',
            component: CustomerUsers,
            meta: { title: 'Пользователи компании - МТТ', roles: ['customer'] as UserRole[] },
          },
          {
            path: 'billing',
            name: 'CustomerBilling',
            component: CustomerBilling,
            meta: { title: 'Биллинг - МТТ', roles: ['customer'] as UserRole[] },
          },
        ],
      },
      {
        path: '/gate',
        name: 'Gate',
        component: Vehicles,
        meta: { title: 'КПП - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/vehicles',
        redirect: '/gate',
      },
      {
        path: '/containers',
        name: 'Containers',
        component: ContainerTable,
        meta: { title: 'Контейнеры - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/yard',
        name: 'Yard',
        component: () => import('../views/UnifiedYardView.vue'),
        meta: { title: 'Площадка 3D - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/placement',
        redirect: '/yard',
      },
      {
        path: '/yard-test',
        redirect: '/yard',
      },
      {
        path: '/tasks',
        name: 'WorkOrders',
        component: () => import('../views/WorkOrdersPage.vue'),
        meta: { title: 'Задания - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/owners',
        name: 'ContainerOwners',
        component: ContainerOwners,
        meta: { title: 'Собственники контейнеров - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/managers',
        name: 'Managers',
        component: Managers,
        meta: { title: 'Менеджеры - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/telegram-bot',
        name: 'TelegramBotSettings',
        component: () => import('../views/TelegramBotSettings.vue'),
        meta: { title: 'Telegram Бот - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/settings/terminal',
        name: 'TerminalSettings',
        component: () => import('../views/TerminalSettings.vue'),
        meta: { title: 'Настройки терминала - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/vehicles-customers',
        name: 'VehiclesCustomers',
        component: VehiclesCustomers,
        meta: { title: 'Клиенты транспорта - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/accounts/companies',
        name: 'Companies',
        component: Companies,
        meta: { title: 'Компании - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/tariffs',
        name: 'Tariffs',
        component: () => import('../views/Tariffs.vue'),
        meta: { title: 'Тарифы - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/terminal-vehicles',
        name: 'TerminalVehicles',
        component: () => import('../views/TerminalVehicles.vue'),
        meta: { title: 'Техника терминала - МТТ', roles: ['admin'] as UserRole[] },
      },
      {
        path: '/accounts/companies/:slug',
        component: CompanyLayout,
        meta: { title: 'Детали компании - МТТ', roles: ['admin', 'customer'] as UserRole[] },
        children: [
          {
            path: '',
            name: 'CompanyInfo',
            component: CompanyInfo,
            meta: { title: 'Информация о компании - МТТ', roles: ['admin', 'customer'] as UserRole[] },
          },
          {
            path: 'users',
            name: 'CompanyUsers',
            component: CompanyUsers,
            meta: { title: 'Пользователи компании - МТТ', roles: ['admin'] as UserRole[] },
          },
          {
            path: 'orders',
            name: 'CompanyOrders',
            component: CompanyOrders,
            meta: { title: 'Заказы компании - МТТ', roles: ['admin', 'customer'] as UserRole[] },
          },
          {
            path: 'containers',
            name: 'CompanyContainers',
            component: CompanyContainers,
            meta: { title: 'Контейнеры компании - МТТ', roles: ['admin', 'customer'] as UserRole[] },
          },
          {
            path: 'billing/current',
            name: 'CompanyBillingCurrent',
            component: CurrentCosts,
            meta: { title: 'Текущие расходы - МТТ', roles: ['admin'] as UserRole[] },
          },
          {
            path: 'billing/statements',
            name: 'CompanyBillingStatements',
            component: MonthlyStatements,
            meta: { title: 'Акты сверки - МТТ', roles: ['admin'] as UserRole[] },
          },
          {
            path: 'billing/invoices',
            name: 'CompanyBillingInvoices',
            component: OnDemandInvoices,
            meta: { title: 'Разовые счета - МТТ', roles: ['admin'] as UserRole[] },
          },
          {
            path: 'settings/telegram',
            name: 'CompanySettingsTelegram',
            component: () => import('../views/company/CompanyTelegramSettings.vue'),
            meta: { title: 'Telegram настройки - МТТ', roles: ['admin'] as UserRole[] },
          },
          {
            path: 'settings/general',
            name: 'CompanySettingsGeneral',
            component: () => import('../views/company/CompanyGeneralSettings.vue'),
            meta: { title: 'Настройки компании - МТТ', roles: ['admin'] as UserRole[] },
          },
        ],
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Global navigation guard
router.beforeEach(async (to, _from, next) => {
  const { isAuthenticated, checkAndRefreshToken, user } = useAuth();

  // Update page title
  const title = to.meta.title || 'МТТ';
  document.title = title;

  // Check if route requires authentication
  const requiresAuth = to.meta.requiresAuth !== false;

  if (requiresAuth) {
    // Check token and refresh if expired
    const isValid = await checkAndRefreshToken();

    if (!isValid) {
      // Redirect to login if not authenticated
      next({ name: 'Login', query: { redirect: to.fullPath } });
      return;
    }

    // Handle app routes redirect based on user type
    if (to.path === '/app' || to.path === '/app/') {
      const redirectPath = user.value?.user_type === 'customer' ? '/customer' : '/containers';
      next({ path: redirectPath });
      return;
    }

    // Check role-based permissions
    const allowedRoles = to.meta.roles;
    if (allowedRoles && allowedRoles.length > 0) {
      const userRole = user.value?.user_type;
      if (!userRole || !allowedRoles.includes(userRole)) {
        // User doesn't have permission, redirect to unauthorized or home
        next({ path: '/unauthorized' });
        return;
      }
    }

    next();
  } else {
    // If going to login page and already authenticated, redirect to app
    if (to.name === 'Login' && isAuthenticated.value) {
      const redirectPath = user.value?.user_type === 'customer' ? '/customer' : '/containers';
      next({ path: redirectPath });
      return;
    }

    // Landing page: redirect based on auth status
    if (to.name === 'Landing') {
      if (isAuthenticated.value) {
        const redirectPath = user.value?.user_type === 'customer' ? '/customer' : '/containers';
        next({ path: redirectPath });
      } else {
        next({ name: 'Login' });
      }
      return;
    }

    next();
  }
});

export default router;
