<template>
  <div class="telegram-bot-settings">
    <h1 class="page-title">Настройки Telegram Бота</h1>

    <!-- Stats Row -->
    <a-row :gutter="[16, 16]" style="margin-bottom: 24px;">
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card class="stat-card" :loading="statsLoading">
          <a-statistic
            title="Менеджеров с доступом к боту"
            :value="managerStats.managers_with_access"
            :suffix="`/ ${managerStats.total_managers}`"
            :value-style="{ color: 'var(--color-primary)' }"
          >
            <template #prefix>
              <RobotOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card class="stat-card" :loading="statsLoading">
          <a-statistic
            title="Менеджеров с Telegram"
            :value="managerStats.managers_with_telegram"
            :suffix="`/ ${managerStats.total_managers}`"
            :value-style="{ color: 'var(--color-info)' }"
          >
            <template #prefix>
              <SendOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card class="stat-card" :loading="statsLoading">
          <a-statistic
            title="Клиентов с доступом к боту"
            :value="customerStats.customers_with_access"
            :suffix="`/ ${customerStats.total_customers}`"
            :value-style="{ color: 'var(--color-success)' }"
          >
            <template #prefix>
              <UserOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card class="stat-card" :loading="statsLoading">
          <a-statistic
            title="Клиентов с Telegram"
            :value="customerStats.customers_with_telegram"
            :suffix="`/ ${customerStats.total_customers}`"
            :value-style="{ color: 'var(--color-warning)' }"
          >
            <template #prefix>
              <SendOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- Main Content with Tabs -->
    <a-card :bordered="false">
      <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
        <a-tab-pane key="activity" tab="Активность">
          <!-- Activity Filters -->
          <a-space style="margin-bottom: 16px">
            <a-select
              v-model:value="activityFilters.action"
              placeholder="Действие"
              allowClear
              style="width: 200px"
              @change="handleActivityFilterChange"
            >
              <a-select-option value="container_entry_created">Въезд контейнера</a-select-option>
              <a-select-option value="container_exit_recorded">Выезд контейнера</a-select-option>
              <a-select-option value="crane_operation_added">Крановая операция</a-select-option>
              <a-select-option value="preorder_created">Заявка создана</a-select-option>
              <a-select-option value="preorder_cancelled">Заявка отменена</a-select-option>
            </a-select>
            <a-select
              v-model:value="activityFilters.user_type"
              placeholder="Тип пользователя"
              allowClear
              style="width: 150px"
              @change="handleActivityFilterChange"
            >
              <a-select-option value="manager">Менеджер</a-select-option>
              <a-select-option value="customer">Клиент</a-select-option>
            </a-select>
            <a-select
              v-model:value="activityFilters.success"
              placeholder="Статус"
              allowClear
              style="width: 120px"
              @change="handleActivityFilterChange"
            >
              <a-select-option :value="true">Успешно</a-select-option>
              <a-select-option :value="false">Ошибка</a-select-option>
            </a-select>
            <a-button @click="handleActivityRefresh">
              <template #icon><ReloadOutlined /></template>
            </a-button>
          </a-space>

          <!-- Activity Table -->
          <a-table
            :columns="activityColumns"
            :data-source="activityData"
            :pagination="activityPagination"
            :loading="activityLoading"
            @change="handleActivityTableChange"
            bordered
            :scroll="{ x: 1000 }"
            size="middle"
          >
            <template #bodyCell="{ column, record, index }">
              <template v-if="column.key === 'number'">
                {{ (activityPagination.current - 1) * activityPagination.pageSize + index + 1 }}
              </template>
              <template v-else-if="column.key === 'user'">
                <span v-if="record.userFullName">{{ record.userFullName }}</span>
                <span v-else class="text-muted">—</span>
              </template>
              <template v-else-if="column.key === 'userType'">
                <a-tag :color="record.userType === 'manager' ? 'blue' : 'green'">
                  {{ record.userTypeDisplay }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-tooltip :title="record.action">
                  <span>{{ record.actionDisplay }}</span>
                </a-tooltip>
              </template>
              <template v-else-if="column.key === 'details'">
                <a-popover title="Детали" trigger="click" v-if="hasActivityDetails(record.details)">
                  <template #content>
                    <pre style="max-width: 400px; max-height: 300px; overflow: auto; margin: 0">{{
                      JSON.stringify(record.details, null, 2)
                    }}</pre>
                  </template>
                  <a-button type="link" size="small">Показать</a-button>
                </a-popover>
                <span v-else class="text-muted">—</span>
              </template>
              <template v-else-if="column.key === 'success'">
                <a-tag v-if="record.success" color="success">
                  <CheckCircleOutlined /> Успешно
                </a-tag>
                <a-tooltip v-else :title="record.errorMessage">
                  <a-tag color="error">
                    <CloseCircleOutlined /> Ошибка
                  </a-tag>
                </a-tooltip>
              </template>
              <template v-else-if="column.key === 'groupNotification'">
                <span v-if="record.groupNotificationStatus === 'not_applicable'" class="text-muted">—</span>
                <a-tooltip v-else :title="record.groupNotificationError || undefined">
                  <a-tag :color="getGroupNotificationColor(record.groupNotificationStatus)">
                    {{ record.groupNotificationStatusDisplay }}
                  </a-tag>
                </a-tooltip>
              </template>
              <template v-else-if="column.key === 'relatedObject'">
                <span v-if="record.relatedObjectStr">{{ record.relatedObjectStr }}</span>
                <span v-else class="text-muted">—</span>
              </template>
            </template>
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="managers" tab="Менеджеры">
          <a-table
            :columns="managerColumns"
            :data-source="managersData"
            :pagination="managersPagination"
            :loading="managersLoading"
            @change="handleManagersTableChange"
            bordered
            :scroll="{ x: 900 }"
          >
            <template #bodyCell="{ column, index, record }">
              <template v-if="column.key === 'number'">
                {{ (managersPagination.current - 1) * managersPagination.pageSize + index + 1 }}
              </template>
              <template v-else-if="column.key === 'telegram'">
                <span v-if="record.telegram_username">@{{ record.telegram_username }}</span>
                <span v-else class="text-muted">—</span>
              </template>
              <template v-else-if="column.key === 'telegram_linked'">
                <a-tag :color="record.telegram_user_id ? 'green' : 'default'">
                  {{ record.telegram_user_id ? 'Да' : 'Нет' }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'bot_access'">
                <a-switch
                  :checked="record.bot_access"
                  :loading="toggleLoadingId === record.id"
                  @change="(checked: boolean) => handleToggleManagerAccess(record, checked)"
                />
              </template>
            </template>
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="customers" tab="Клиенты">
          <a-table
            :columns="customerColumns"
            :data-source="customersData"
            :pagination="customersPagination"
            :loading="customersLoading"
            @change="handleCustomersTableChange"
            bordered
            :scroll="{ x: 1000 }"
          >
            <template #bodyCell="{ column, index, record }">
              <template v-if="column.key === 'number'">
                {{ (customersPagination.current - 1) * customersPagination.pageSize + index + 1 }}
              </template>
              <template v-else-if="column.key === 'telegram'">
                <span v-if="record.telegram_username">@{{ record.telegram_username }}</span>
                <span v-else class="text-muted">—</span>
              </template>
              <template v-else-if="column.key === 'telegram_linked'">
                <a-tag :color="record.telegram_user_id ? 'green' : 'default'">
                  {{ record.telegram_user_id ? 'Да' : 'Нет' }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'bot_access'">
                <a-switch
                  :checked="record.bot_access"
                  :loading="toggleLoadingId === record.id"
                  @change="(checked: boolean) => handleToggleCustomerAccess(record, checked)"
                />
              </template>
            </template>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import {
  RobotOutlined,
  SendOutlined,
  UserOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons-vue';
import { http } from '../utils/httpClient';
import { formatDateTime } from '../utils/dateFormat';
import {
  telegramActivityService,
  type TelegramActivityLog,
  type ActivityLogFilters,
  type GroupNotificationStatus,
} from '../services/telegramActivityService';

// Types
interface ManagerStats {
  total_managers: number;
  active_managers: number;
  managers_with_access: number;
  managers_with_telegram: number;
}

interface CustomerStats {
  total_customers: number;
  active_customers: number;
  customers_with_access: number;
  customers_with_telegram: number;
}

interface ManagerRecord {
  key: string;
  id: number;
  first_name: string;
  phone_number: string;
  telegram_user_id: number | null;
  telegram_username: string | null;
  bot_access: boolean;
  is_active: boolean;
}

interface CustomerRecord {
  key: string;
  id: number;
  full_name: string;
  phone_number: string;
  telegram_user_id: number | null;
  telegram_username: string | null;
  bot_access: boolean;
  is_active: boolean;
  company_name: string | null;
}

interface ActivityLogRecord {
  key: string;
  id: number;
  userFullName: string | null;
  userType: 'manager' | 'customer';
  userTypeDisplay: string;
  action: string;
  actionDisplay: string;
  details: Record<string, unknown>;
  success: boolean;
  errorMessage: string;
  groupNotificationStatus: GroupNotificationStatus;
  groupNotificationStatusDisplay: string;
  groupNotificationError: string;
  relatedObjectStr: string | null;
  createdAt: string;
}

// Table columns
const managerColumns = [
  { title: '№', key: 'number', align: 'center' as const, width: 60, fixed: 'left' as const },
  { title: 'Имя', dataIndex: 'first_name', key: 'first_name', width: 150 },
  { title: 'Телефон', dataIndex: 'phone_number', key: 'phone_number', width: 150 },
  { title: 'Telegram', key: 'telegram', width: 150 },
  { title: 'Привязан', key: 'telegram_linked', align: 'center' as const, width: 100 },
  { title: 'Доступ к боту', key: 'bot_access', align: 'center' as const, width: 130 },
];

const customerColumns = [
  { title: '№', key: 'number', align: 'center' as const, width: 60, fixed: 'left' as const },
  { title: 'Имя', dataIndex: 'full_name', key: 'full_name', width: 180 },
  { title: 'Компания', dataIndex: 'company_name', key: 'company_name', width: 150 },
  { title: 'Телефон', dataIndex: 'phone_number', key: 'phone_number', width: 150 },
  { title: 'Telegram', key: 'telegram', width: 150 },
  { title: 'Привязан', key: 'telegram_linked', align: 'center' as const, width: 100 },
  { title: 'Доступ к боту', key: 'bot_access', align: 'center' as const, width: 130 },
];

const activityColumns = [
  { title: '№', key: 'number', align: 'center' as const, width: 60, fixed: 'left' as const },
  { title: 'Пользователь', key: 'user', width: 150 },
  { title: 'Тип', key: 'userType', width: 100 },
  { title: 'Действие', key: 'action', width: 180 },
  { title: 'Объект', key: 'relatedObject', width: 150 },
  { title: 'Детали', key: 'details', width: 80, align: 'center' as const },
  { title: 'Статус', key: 'success', width: 100, align: 'center' as const },
  { title: 'Группа', key: 'groupNotification', width: 120, align: 'center' as const },
  { title: 'Дата', dataIndex: 'createdAt', key: 'createdAt', width: 150 },
];

// State
const activeTab = ref('activity');
const statsLoading = ref(true);
const toggleLoadingId = ref<number | null>(null);

// Stats
const managerStats = ref<ManagerStats>({
  total_managers: 0,
  active_managers: 0,
  managers_with_access: 0,
  managers_with_telegram: 0,
});

const customerStats = ref<CustomerStats>({
  total_customers: 0,
  active_customers: 0,
  customers_with_access: 0,
  customers_with_telegram: 0,
});

// Managers table state
const managersData = ref<ManagerRecord[]>([]);
const managersLoading = ref(false);
const managersPagination = ref({
  current: 1,
  pageSize: 25,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '25', '50', '100'],
});

// Customers table state
const customersData = ref<CustomerRecord[]>([]);
const customersLoading = ref(false);
const customersPagination = ref({
  current: 1,
  pageSize: 25,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '25', '50', '100'],
});

// Activity table state
const activityData = ref<ActivityLogRecord[]>([]);
const activityLoading = ref(false);
const activityPagination = ref({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50', '100'],
});
const activityFilters = reactive<ActivityLogFilters>({
  action: undefined,
  user_type: undefined,
  success: undefined,
});

// Fetch stats
const fetchStats = async () => {
  try {
    statsLoading.value = true;
    const [managersRes, customersRes] = await Promise.all([
      http.get<{ data: ManagerStats }>('/auth/managers/stats/'),
      http.get<{ data: CustomerStats }>('/auth/customers/stats/'),
    ]);
    managerStats.value = managersRes.data;
    customerStats.value = customersRes.data;
  } catch (error) {
    console.error('Failed to fetch stats:', error);
  } finally {
    statsLoading.value = false;
  }
};

// Fetch managers
const fetchManagers = async (page?: number, pageSize?: number) => {
  try {
    managersLoading.value = true;
    const currentPage = page || managersPagination.value.current;
    const currentPageSize = pageSize || managersPagination.value.pageSize;

    const params = new URLSearchParams();
    params.append('page', currentPage.toString());
    params.append('page_size', currentPageSize.toString());

    interface ManagerApiResponse {
      id: number;
      first_name: string;
      phone_number: string;
      telegram_user_id: number | null;
      telegram_username: string | null;
      bot_access: boolean;
      is_active: boolean;
    }

    const data = await http.get<{ count: number; results: ManagerApiResponse[] }>(
      `/auth/managers/?${params.toString()}`
    );

    managersData.value = data.results.map((m) => ({
      key: m.id.toString(),
      id: m.id,
      first_name: m.first_name,
      phone_number: m.phone_number,
      telegram_user_id: m.telegram_user_id,
      telegram_username: m.telegram_username,
      bot_access: m.bot_access,
      is_active: m.is_active,
    }));

    managersPagination.value.total = data.count;
    managersPagination.value.current = currentPage;
    managersPagination.value.pageSize = currentPageSize;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка загрузки менеджеров');
  } finally {
    managersLoading.value = false;
  }
};

// Fetch customers
const fetchCustomers = async (page?: number, pageSize?: number) => {
  try {
    customersLoading.value = true;
    const currentPage = page || customersPagination.value.current;
    const currentPageSize = pageSize || customersPagination.value.pageSize;

    const params = new URLSearchParams();
    params.append('page', currentPage.toString());
    params.append('page_size', currentPageSize.toString());

    interface CustomerApiResponse {
      id: number;
      first_name: string;
      last_name: string;
      full_name: string;
      phone_number: string;
      telegram_user_id: number | null;
      telegram_username: string | null;
      bot_access: boolean;
      is_active: boolean;
      company: { id: number; name: string } | null;
    }

    const data = await http.get<{ count: number; results: CustomerApiResponse[] }>(
      `/auth/customers/?${params.toString()}`
    );

    customersData.value = data.results.map((c) => ({
      key: c.id.toString(),
      id: c.id,
      full_name: c.full_name || `${c.first_name} ${c.last_name}`.trim(),
      phone_number: c.phone_number,
      telegram_user_id: c.telegram_user_id,
      telegram_username: c.telegram_username,
      bot_access: c.bot_access,
      is_active: c.is_active,
      company_name: c.company?.name || null,
    }));

    customersPagination.value.total = data.count;
    customersPagination.value.current = currentPage;
    customersPagination.value.pageSize = currentPageSize;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка загрузки клиентов');
  } finally {
    customersLoading.value = false;
  }
};

// Table change handlers
const handleManagersTableChange = (pag: { current: number; pageSize: number }) => {
  fetchManagers(pag.current, pag.pageSize);
};

const handleCustomersTableChange = (pag: { current: number; pageSize: number }) => {
  fetchCustomers(pag.current, pag.pageSize);
};

// Activity functions
function transformActivityLog(log: TelegramActivityLog): ActivityLogRecord {
  return {
    key: log.id.toString(),
    id: log.id,
    userFullName: log.user_full_name,
    userType: log.user_type,
    userTypeDisplay: log.user_type_display,
    action: log.action,
    actionDisplay: log.action_display,
    details: log.details,
    success: log.success,
    errorMessage: log.error_message,
    groupNotificationStatus: log.group_notification_status,
    groupNotificationStatusDisplay: log.group_notification_status_display,
    groupNotificationError: log.group_notification_error,
    relatedObjectStr: log.related_object_str,
    createdAt: formatDateTime(log.created_at),
  };
}

function hasActivityDetails(details: Record<string, unknown>): boolean {
  return Object.keys(details).length > 0;
}

function getGroupNotificationColor(status: GroupNotificationStatus): string {
  switch (status) {
    case 'sent':
      return 'success';
    case 'error':
      return 'error';
    default:
      return 'default';
  }
}

async function fetchActivity(page?: number, pageSize?: number): Promise<void> {
  activityLoading.value = true;
  const currentPage = page ?? activityPagination.value.current;
  const currentPageSize = pageSize ?? activityPagination.value.pageSize;

  try {
    const { data, total } = await telegramActivityService.getActivityLogs(
      activityFilters,
      currentPage,
      currentPageSize
    );

    activityData.value = data.map(transformActivityLog);
    activityPagination.value.total = total;
    activityPagination.value.current = currentPage;
    activityPagination.value.pageSize = currentPageSize;
  } catch (error) {
    message.error('Ошибка загрузки активности');
    console.error('Failed to fetch activity logs:', error);
  } finally {
    activityLoading.value = false;
  }
}

function handleActivityTableChange(pag: { current: number; pageSize: number }): void {
  fetchActivity(pag.current, pag.pageSize);
}

function handleActivityFilterChange(): void {
  activityPagination.value.current = 1;
  fetchActivity();
}

function handleActivityRefresh(): void {
  fetchActivity();
}

// Tab change handler
const handleTabChange = (key: string) => {
  if (key === 'managers' && managersData.value.length === 0) {
    fetchManagers();
  }
  if (key === 'customers' && customersData.value.length === 0) {
    fetchCustomers();
  }
};

// Toggle bot access for manager
const handleToggleManagerAccess = async (record: ManagerRecord, checked: boolean) => {
  toggleLoadingId.value = record.id;
  try {
    const action = checked ? 'grant-access' : 'revoke-access';
    const response = await http.post<{ data: { bot_access: boolean } }>(
      `/auth/managers/${record.id}/${action}/`
    );
    // Use server response instead of assuming success
    record.bot_access = response.data.bot_access;
    await fetchStats();
    message.success(checked ? 'Доступ предоставлен' : 'Доступ отозван');
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка изменения доступа');
  } finally {
    toggleLoadingId.value = null;
  }
};

// Toggle bot access for customer
const handleToggleCustomerAccess = async (record: CustomerRecord, checked: boolean) => {
  toggleLoadingId.value = record.id;
  try {
    const action = checked ? 'grant-access' : 'revoke-access';
    const response = await http.post<{ data: { bot_access: boolean } }>(
      `/auth/customers/${record.id}/${action}/`
    );
    // Use server response instead of assuming success
    record.bot_access = response.data.bot_access;
    await fetchStats();
    message.success(checked ? 'Доступ предоставлен' : 'Доступ отозван');
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка изменения доступа');
  } finally {
    toggleLoadingId.value = null;
  }
};

// Initialize
onMounted(() => {
  fetchStats();
  fetchActivity();
});
</script>

<style scoped>
.telegram-bot-settings {
  padding: 0;
}

.page-title {
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

.text-muted {
  color: #999;
}
</style>
