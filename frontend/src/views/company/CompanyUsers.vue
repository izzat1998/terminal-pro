<template>
  <a-card :bordered="false" class="content-card">
    <template #title>
      Пользователи компании
    </template>
    <template #extra>
      <a-button type="primary" @click="handleAddUser">
        <PlusOutlined />
        Добавить пользователя
      </a-button>
    </template>

    <a-empty v-if="!loading && customers.length === 0" description="Пользователи не найдены" />

    <a-table
      v-else
      :columns="columns"
      :data-source="customers"
      :loading="loading"
      :pagination="{ pageSize: 10 }"
      row-key="id"
      :row-class-name="rowClassName"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'first_name'">
          <a-space>
            <a-avatar size="small">
              {{ record.first_name?.charAt(0)?.toUpperCase() || '?' }}
            </a-avatar>
            {{ record.first_name }}
          </a-space>
        </template>
        <template v-if="column.key === 'phone_number'">
          <a :href="'tel:' + record.phone_number">{{ record.phone_number }}</a>
        </template>
        <template v-if="column.key === 'telegram'">
          <template v-if="record.telegram_username">
            <a :href="'https://t.me/' + record.telegram_username" target="_blank">
              @{{ record.telegram_username }}
            </a>
          </template>
          <template v-else>
            <span class="text-muted">—</span>
          </template>
        </template>
        <template v-if="column.key === 'bot_access'">
          <a-tag :color="record.bot_access ? 'green' : 'default'">
            {{ record.bot_access ? 'Да' : 'Нет' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'status'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? 'Активен' : 'Неактивен' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'orders_count'">
          <a-badge
            :count="record.orders_count"
            :show-zero="true"
            :overflow-count="999"
            style="cursor: pointer;"
            @click="handleViewOrders(record)"
          />
        </template>
        <template v-if="column.key === 'created_at'">
          {{ formatDate(record.created_at) }}
        </template>
        <template v-if="column.key === 'actions'">
          <a-space>
            <a-tooltip title="Редактировать">
              <a-button type="link" size="small" @click="handleEdit(record)">
                <EditOutlined />
              </a-button>
            </a-tooltip>
            <a-tooltip title="Удалить">
              <a-button type="link" size="small" danger @click="handleDelete(record)">
                <DeleteOutlined />
              </a-button>
            </a-tooltip>
          </a-space>
        </template>
      </template>
    </a-table>
  </a-card>

  <a-modal
    v-model:open="createModalVisible"
    title="Добавить пользователя"
    @ok="handleCreateSubmit"
    @cancel="handleCreateCancel"
    :confirm-loading="createLoading"
    ok-text="Создать"
    cancel-text="Отмена"
  >
    <a-form :model="createForm" layout="vertical">
      <a-form-item label="Имя" required>
        <a-input v-model:value="createForm.first_name" placeholder="Введите имя" />
      </a-form-item>
      <a-form-item label="Телефон" required>
        <a-input v-model:value="createForm.phone_number" placeholder="+998901234567" />
      </a-form-item>
      <a-form-item label="Доступ к боту">
        <a-switch v-model:checked="createForm.bot_access" />
      </a-form-item>
      <a-form-item label="Активен">
        <a-switch v-model:checked="createForm.is_active" />
      </a-form-item>
    </a-form>
  </a-modal>

  <a-modal
    v-model:open="editModalVisible"
    title="Редактировать пользователя"
    @ok="handleEditSubmit"
    @cancel="handleEditCancel"
    :confirm-loading="editLoading"
    ok-text="Сохранить"
    cancel-text="Отмена"
  >
    <a-form :model="editForm" layout="vertical">
      <a-form-item label="Имя" required>
        <a-input v-model:value="editForm.first_name" placeholder="Введите имя" />
      </a-form-item>
      <a-form-item label="Телефон" required>
        <a-input v-model:value="editForm.phone_number" placeholder="+998901234567" />
      </a-form-item>
      <a-form-item label="Доступ к боту">
        <a-switch v-model:checked="editForm.bot_access" />
      </a-form-item>
      <a-form-item label="Активен">
        <a-switch v-model:checked="editForm.is_active" />
      </a-form-item>
    </a-form>
  </a-modal>

  <a-drawer
    v-model:open="ordersDrawerVisible"
    :title="'Заказы: ' + (viewingCustomer?.first_name || '')"
    placement="right"
    width="700"
    :footer="null"
    @close="handleDrawerClose"
  >
    <a-spin :spinning="ordersLoading">
      <a-empty v-if="!ordersLoading && orderBatches.length === 0" description="Заказы не найдены" />

      <div v-else class="orders-container">
        <a-collapse v-model:activeKey="activeBatchKeys" accordion>
          <a-collapse-panel
            v-for="batch in orderBatches"
            :key="batch.batch_id"
            :header="'Партия от ' + formatDateTime(batch.created_at) + ' (' + batch.orders_count + ' заказов)'"
          >
            <a-table
              :columns="ordersColumns"
              :data-source="batch.orders"
              :pagination="false"
              row-key="id"
              size="small"
            >
              <template #bodyCell="{ column, record: order }">
                <template v-if="column.key === 'plate_number'">
                  <a-tag color="blue">{{ order.plate_number }}</a-tag>
                </template>
                <template v-if="column.key === 'operation_type'">
                  <a-tag :color="order.operation_type === 'LOAD' ? 'green' : 'orange'">
                    {{ order.operation_type_display }}
                  </a-tag>
                </template>
                <template v-if="column.key === 'status'">
                  <a-tag :color="getOrderStatusColor(order.status)">
                    {{ order.status_display }}
                  </a-tag>
                </template>
                <template v-if="column.key === 'matched_at'">
                  {{ order.matched_at ? formatDateTime(order.matched_at) : '—' }}
                </template>
                <template v-if="column.key === 'notes'">
                  <span v-if="order.notes">{{ order.notes }}</span>
                  <span v-else class="text-muted">—</span>
                </template>
              </template>
            </a-table>
          </a-collapse-panel>
        </a-collapse>
      </div>
    </a-spin>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref, watch, reactive, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { message, Modal } from 'ant-design-vue';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import { http } from '../../utils/httpClient';
import { formatDate, formatDateTime } from '../../utils/dateFormat';

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface Customer {
  id: number;
  first_name: string;
  phone_number: string;
  telegram_user_id: number | null;
  telegram_username: string;
  bot_access: boolean;
  is_active: boolean;
  can_use_bot: boolean;
  has_profile: boolean;
  company: Company;
  orders_count: number;
  created_at: string;
  updated_at: string;
}

interface Order {
  id: number;
  customer: number;
  customer_name: string;
  plate_number: string;
  operation_type: 'LOAD' | 'UNLOAD';
  operation_type_display: string;
  status: string;
  status_display: string;
  truck_photo: string | null;
  truck_photo_url: string | null;
  vehicle_entry: number | null;
  matched_entry: number | null;
  matched_at: string | null;
  cancelled_at: string | null;
  notes: string;
  batch_id: string;
  created_at: string;
  updated_at: string;
}

interface OrderBatch {
  batch_id: string;
  created_at: string;
  orders_count: number;
  orders: Order[];
}

const props = defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const route = useRoute();
const highlightedUserId = ref<number | null>(null);

const customers = ref<Customer[]>([]);
const loading = ref(false);

const createModalVisible = ref(false);
const createLoading = ref(false);
const createForm = reactive({
  first_name: '',
  phone_number: '',
  bot_access: true,
  is_active: true,
});

const editModalVisible = ref(false);
const editLoading = ref(false);
const editingCustomerId = ref<number | null>(null);
const editForm = reactive({
  first_name: '',
  phone_number: '',
  bot_access: true,
  is_active: true,
});

const ordersDrawerVisible = ref(false);
const ordersLoading = ref(false);
const viewingCustomer = ref<Customer | null>(null);
const orderBatches = ref<OrderBatch[]>([]);
const activeBatchKeys = ref<string[]>([]);

const columns = [
  {
    title: 'Имя',
    dataIndex: 'first_name',
    key: 'first_name',
  },
  {
    title: 'Телефон',
    dataIndex: 'phone_number',
    key: 'phone_number',
  },
  {
    title: 'Telegram',
    key: 'telegram',
  },
  {
    title: 'Доступ к боту',
    key: 'bot_access',
  },
  {
    title: 'Заказы',
    key: 'orders_count',
  },
  {
    title: 'Статус',
    key: 'status',
  },
  {
    title: 'Создан',
    key: 'created_at',
  },
  {
    title: 'Действия',
    key: 'actions',
  },
];

const ordersColumns = [
  {
    title: 'Гос. номер',
    key: 'plate_number',
    width: 120,
  },
  {
    title: 'Операция',
    key: 'operation_type',
    width: 110,
  },
  {
    title: 'Статус',
    key: 'status',
    width: 120,
  },
  {
    title: 'Сопоставлен',
    key: 'matched_at',
    width: 150,
  },
  {
    title: 'Примечания',
    key: 'notes',
  },
];

const getOrderStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    PENDING: 'default',
    MATCHED: 'green',
    COMPLETED: 'blue',
    CANCELLED: 'red',
  };
  return colors[status] || 'default';
};

const rowClassName = (record: Customer) => {
  return record.id === highlightedUserId.value ? 'highlighted-row' : '';
};

onMounted(() => {
  const userId = route.query.user;
  if (userId) {
    highlightedUserId.value = parseInt(userId as string, 10);
    // Clear highlight after 5 seconds
    setTimeout(() => {
      highlightedUserId.value = null;
    }, 5000);
  }

  // Listen for back button to close drawer
  window.addEventListener('popstate', handlePopState);
});

const fetchCustomers = async (slug: string) => {
  loading.value = true;
  try {
    const result = await http.get<{ success: boolean; data: Customer[] }>(`/auth/companies/${slug}/customers/`);
    if (result.success) {
      customers.value = result.data;
    } else {
      message.error('Ошибка загрузки пользователей');
    }
  } catch (error) {
    console.error('Error fetching customers:', error);
    message.error('Ошибка загрузки пользователей');
  } finally {
    loading.value = false;
  }
};

watch(() => props.company, (newCompany) => {
  if (newCompany?.slug) {
    fetchCustomers(newCompany.slug);
  }
}, { immediate: true });

const resetCreateForm = () => {
  createForm.first_name = '';
  createForm.phone_number = '';
  createForm.bot_access = true;
  createForm.is_active = true;
};

const handleAddUser = () => {
  resetCreateForm();
  createModalVisible.value = true;
};

const handleCreateSubmit = async () => {
  if (!createForm.first_name.trim()) {
    message.warning('Введите имя пользователя');
    return;
  }
  if (!createForm.phone_number.trim()) {
    message.warning('Введите номер телефона');
    return;
  }
  if (!props.company) {
    message.error('Компания не выбрана');
    return;
  }

  createLoading.value = true;
  try {
    const result = await http.post<{ success: boolean; error?: { message: string }; message?: string }>(`/auth/customers/`, {
      first_name: createForm.first_name,
      phone_number: createForm.phone_number,
      company_id: props.company.id,
      bot_access: createForm.bot_access,
      is_active: createForm.is_active,
    });

    if (result.success) {
      message.success('Пользователь успешно создан');
      createModalVisible.value = false;
      fetchCustomers(props.company.slug);
    } else {
      message.error(result.error?.message || result.message || 'Ошибка создания пользователя');
    }
  } catch (error) {
    console.error('Error creating customer:', error);
    message.error('Ошибка создания пользователя');
  } finally {
    createLoading.value = false;
  }
};

const handleCreateCancel = () => {
  createModalVisible.value = false;
};

const handleEdit = (record: Customer) => {
  editingCustomerId.value = record.id;
  editForm.first_name = record.first_name;
  editForm.phone_number = record.phone_number;
  editForm.bot_access = record.bot_access;
  editForm.is_active = record.is_active;
  editModalVisible.value = true;
};

const handleEditSubmit = async () => {
  if (!editForm.first_name.trim()) {
    message.warning('Введите имя пользователя');
    return;
  }
  if (!editForm.phone_number.trim()) {
    message.warning('Введите номер телефона');
    return;
  }
  if (!props.company || !editingCustomerId.value) {
    message.error('Ошибка редактирования');
    return;
  }

  editLoading.value = true;
  try {
    const result = await http.put<{ success: boolean; error?: { message: string }; message?: string }>(`/auth/customers/${editingCustomerId.value}/`, {
      first_name: editForm.first_name,
      phone_number: editForm.phone_number,
      company_id: props.company.id,
      bot_access: editForm.bot_access,
      is_active: editForm.is_active,
    });

    if (result.success) {
      message.success('Пользователь успешно обновлён');
      editModalVisible.value = false;
      fetchCustomers(props.company.slug);
    } else {
      message.error(result.error?.message || result.message || 'Ошибка обновления пользователя');
    }
  } catch (error) {
    console.error('Error updating customer:', error);
    message.error('Ошибка обновления пользователя');
  } finally {
    editLoading.value = false;
  }
};

const handleEditCancel = () => {
  editModalVisible.value = false;
  editingCustomerId.value = null;
};

const handleDelete = (record: Customer) => {
  Modal.confirm({
    title: 'Удалить пользователя?',
    content: `Вы уверены, что хотите удалить пользователя "${record.first_name}"?`,
    okText: 'Удалить',
    okType: 'danger',
    cancelText: 'Отмена',
    async onOk() {
      try {
        await http.delete(`/auth/customers/${record.id}/`);
        message.success('Пользователь успешно удалён');
        if (props.company?.slug) {
          fetchCustomers(props.company.slug);
        }
      } catch (error) {
        console.error('Error deleting customer:', error);
        message.error('Ошибка удаления пользователя');
      }
    },
  });
};

const handleViewOrders = async (record: Customer) => {
  viewingCustomer.value = record;
  ordersDrawerVisible.value = true;
  ordersLoading.value = true;
  orderBatches.value = [];
  activeBatchKeys.value = [];

  // Push state to handle back navigation
  window.history.pushState({ ordersDrawerOpen: true }, '');

  try {
    const result = await http.get<{ success: boolean; results: OrderBatch[] }>(`/auth/customers/${record.id}/orders/`);

    if (result.success) {
      orderBatches.value = result.results || [];
      // Auto-expand the first batch
      const firstBatch = orderBatches.value[0];
      if (firstBatch) {
        activeBatchKeys.value = [firstBatch.batch_id];
      }
    } else {
      message.error('Ошибка загрузки заказов');
    }
  } catch (error) {
    console.error('Error fetching orders:', error);
    message.error('Ошибка загрузки заказов');
  } finally {
    ordersLoading.value = false;
  }
};

const closedByBackButton = ref(false);

const closeOrdersDrawer = () => {
  ordersDrawerVisible.value = false;
  viewingCustomer.value = null;
};

const handleDrawerClose = () => {
  // If closed by UI (not back button), go back in history to remove pushed state
  if (!closedByBackButton.value) {
    window.history.back();
  }
  closedByBackButton.value = false;
  closeOrdersDrawer();
};

const handlePopState = () => {
  if (ordersDrawerVisible.value) {
    closedByBackButton.value = true;
    closeOrdersDrawer();
  }
};

onUnmounted(() => {
  window.removeEventListener('popstate', handlePopState);
});
</script>

<style scoped>
.content-card {
  border-radius: 2px;
}

.text-muted {
  color: #999;
}

:deep(.highlighted-row) {
  background-color: #e6f7ff !important;
  animation: highlight-pulse 1s ease-in-out 3;
}

@keyframes highlight-pulse {
  0%, 100% {
    background-color: #e6f7ff;
  }
  50% {
    background-color: #bae7ff;
  }
}

.orders-container {
  max-height: calc(100vh - 150px);
  overflow-y: auto;
}

.orders-container :deep(.ant-collapse-header) {
  font-weight: 500;
}

.orders-container :deep(.ant-table-small) {
  font-size: 13px;
}
</style>
