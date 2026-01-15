<template>
  <a-card title="Клиенты транспорта" :bordered="false">
    <template #extra>
      <a-space>
        <a-input-search
          v-model:value="searchText"
          placeholder="Поиск по имени или телефону..."
          style="width: 280px;"
          allow-clear
          @search="handleSearch"
          @pressEnter="handleSearch"
          @change="(e: Event) => { if (!(e.target as HTMLInputElement).value) handleSearch() }"
        />
        <a-button type="primary" @click="showCreateModal">
          <template #icon>
            <PlusOutlined />
          </template>
          Создать клиента
        </a-button>
      </a-space>
    </template>

    <a-table
      :columns="columns"
      :data-source="dataSource"
      :pagination="pagination"
      :loading="loading"
      @change="handleTableChange"
      bordered
      :scroll="{ x: 1000 }"
      :locale="{ emptyText: undefined }"
    >
      <template #bodyCell="{ column, index, record }">
        <template v-if="column.key === 'number'">
          {{ (pagination.current - 1) * pagination.pageSize + index + 1 }}
        </template>
        <template v-else-if="column.key === 'bot_access'">
          <a-tag :color="record.bot_access ? 'green' : 'red'">
            {{ record.bot_access ? 'Да' : 'Нет' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? 'Да' : 'Нет' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-tooltip title="Редактировать">
              <a-button type="link" size="small" @click="showEditModal(record)">
                <template #icon>
                  <EditOutlined />
                </template>
              </a-button>
            </a-tooltip>
            <a-tooltip title="Удалить">
              <a-button type="link" size="small" danger @click="showDeleteModal(record)">
                <template #icon>
                  <DeleteOutlined />
                </template>
              </a-button>
            </a-tooltip>
          </a-space>
        </template>
      </template>
      <template #emptyText>
        <a-empty :image="Empty.PRESENTED_IMAGE_SIMPLE" description="Нет клиентов">
          <a-button type="primary" @click="showCreateModal">
            <template #icon><PlusOutlined /></template>
            Создать клиента
          </a-button>
        </a-empty>
      </template>
    </a-table>
  </a-card>

  <!-- Create Modal -->
  <a-modal
    v-model:open="createModalVisible"
    title="Создать клиента"
    @ok="handleCreateSubmit"
    @cancel="handleCreateCancel"
    :confirm-loading="createLoading"
  >
    <a-form :model="createForm" layout="vertical">
      <a-form-item label="Имя" required>
        <a-input v-model:value="createForm.first_name" placeholder="Введите имя" />
      </a-form-item>
      <a-form-item label="Телефон" required extra="Формат: +998XXXXXXXXX (9 цифр после +998)">
        <a-input
          v-model:value="createForm.phone_number"
          placeholder="+998901234567"
          @input="handlePhoneInput"
        />
      </a-form-item>
      <a-form-item label="Доступ к боту">
        <a-switch v-model:checked="createForm.bot_access" />
      </a-form-item>
      <a-form-item label="Доступ к системе">
        <a-switch v-model:checked="createForm.is_active" />
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- Edit Modal -->
  <a-modal
    v-model:open="editModalVisible"
    title="Редактировать клиента"
    @ok="handleEditSubmit"
    @cancel="handleEditCancel"
    :confirm-loading="editLoading"
  >
    <a-form :model="editForm" layout="vertical">
      <a-form-item label="Имя" required>
        <a-input v-model:value="editForm.first_name" placeholder="Введите имя" />
      </a-form-item>
      <a-form-item label="Телефон" required extra="Формат: +998XXXXXXXXX (9 цифр после +998)">
        <a-input
          v-model:value="editForm.phone_number"
          placeholder="+998901234567"
          @input="handleEditPhoneInput"
        />
      </a-form-item>
      <a-form-item label="Доступ к боту">
        <a-switch v-model:checked="editForm.bot_access" />
      </a-form-item>
      <a-form-item label="Доступ к системе">
        <a-switch v-model:checked="editForm.is_active" />
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- Delete Modal -->
  <a-modal
    v-model:open="deleteModalVisible"
    title="Удалить клиента"
    @ok="handleDeleteSubmit"
    @cancel="handleDeleteCancel"
    :confirm-loading="deleteLoading"
    okText="Удалить"
    cancelText="Отмена"
    okType="danger"
  >
    <p>Вы уверены, что хотите удалить клиента <strong>{{ deletingCustomer.first_name }}</strong>?</p>
    <p>Это действие невозможно отменить.</p>
  </a-modal>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { message, Empty } from 'ant-design-vue';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import { http } from '../utils/httpClient';
import { formatDateTime } from '../utils/dateFormat';

interface Customer {
  id: number;
  first_name: string;
  phone_number: string;
  telegram_user_id: number;
  telegram_username: string;
  bot_access: boolean;
  is_active: boolean;
  can_use_bot: boolean;
  orders_count: number;
  created_at: string;
  updated_at: string;
}

interface CustomerRecord {
  key: string;
  id: number;
  first_name: string;
  phone_number: string;
  telegram_username: string;
  bot_access: boolean;
  is_active: boolean;
  can_use_bot: boolean;
  orders_count: number;
  created: string;
  updated: string;
}

const columns = [
  {
    title: '№',
    key: 'number',
    align: 'center' as const,
    width: 60,
    fixed: 'left' as const,
  },
  {
    title: 'Имя',
    dataIndex: 'first_name',
    key: 'first_name',
    align: 'center' as const,
    width: 150,
    fixed: 'left' as const,
  },
  {
    title: 'Телефон',
    dataIndex: 'phone_number',
    key: 'phone_number',
    align: 'center' as const,
    width: 150,
  },
  {
    title: 'Telegram',
    dataIndex: 'telegram_username',
    key: 'telegram_username',
    align: 'center' as const,
    width: 140,
  },
  {
    title: 'Заказы',
    dataIndex: 'orders_count',
    key: 'orders_count',
    align: 'center' as const,
    width: 80,
  },
  {
    title: 'Доступ к боту',
    key: 'bot_access',
    align: 'center' as const,
    width: 120,
  },
  {
    title: 'Доступ к системе',
    key: 'is_active',
    align: 'center' as const,
    width: 140,
  },
  {
    title: 'Дата создания',
    dataIndex: 'created',
    key: 'created',
    align: 'center' as const,
    width: 160,
  },
  {
    title: 'Действия',
    key: 'actions',
    align: 'center' as const,
    width: 100,
    fixed: 'right' as const,
  },
];

// Search state
const searchText = ref('');

// Table data state
const dataSource = ref<CustomerRecord[]>([]);
const loading = ref(false);
const pagination = ref({
  current: 1,
  pageSize: 25,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '25', '50', '100'],
});

// Fetch data with search support
const fetchData = async (page?: number, pageSize?: number) => {
  try {
    loading.value = true;
    const currentPage = page ?? pagination.value.current;
    const currentPageSize = pageSize ?? pagination.value.pageSize;

    const params = new URLSearchParams();
    params.append('page', currentPage.toString());
    params.append('page_size', currentPageSize.toString());
    if (searchText.value.trim()) {
      params.append('search', searchText.value.trim());
    }

    const data = await http.get<{ count: number; results: Customer[] }>(`/auth/customers/?${params.toString()}`);

    dataSource.value = data.results.map(customer => ({
      key: customer.id.toString(),
      id: customer.id,
      first_name: customer.first_name,
      phone_number: customer.phone_number,
      telegram_username: customer.telegram_username ? `@${customer.telegram_username}` : '—',
      bot_access: customer.bot_access,
      is_active: customer.is_active,
      can_use_bot: customer.can_use_bot,
      orders_count: customer.orders_count,
      created: formatDateTime(customer.created_at),
      updated: formatDateTime(customer.updated_at),
    }));
    pagination.value.total = data.count;
    pagination.value.current = currentPage;
    pagination.value.pageSize = currentPageSize;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Не удалось загрузить данные');
  } finally {
    loading.value = false;
  }
};

const handleTableChange = (pag: { current: number; pageSize: number }) => {
  fetchData(pag.current, pag.pageSize);
};

const handleSearch = () => {
  fetchData(1, pagination.value.pageSize); // Reset to page 1 on search
};

const refresh = () => {
  fetchData(pagination.value.current, pagination.value.pageSize);
};

const refreshAfterDelete = () => {
  const isLastItemOnPage = dataSource.value.length === 1 && pagination.value.current > 1;
  const newPage = isLastItemOnPage ? pagination.value.current - 1 : pagination.value.current;
  fetchData(newPage, pagination.value.pageSize);
};

// Create modal state
const createModalVisible = ref(false);
const createLoading = ref(false);
const createForm = reactive({
  first_name: '',
  phone_number: '+998',
  bot_access: true,
  is_active: true,
});

const handlePhoneInput = () => {
  // Ensure it starts with +998
  if (!createForm.phone_number.startsWith('+998')) {
    createForm.phone_number = '+998';
  }
  // Remove any non-digit characters except the leading +
  const prefix = '+998';
  const rest = createForm.phone_number.slice(4).replace(/\D/g, '');
  createForm.phone_number = prefix + rest;
};

const showCreateModal = () => {
  createForm.first_name = '';
  createForm.phone_number = '+998';
  createForm.bot_access = true;
  createForm.is_active = true;
  createModalVisible.value = true;
};

const handleCreateCancel = () => {
  createModalVisible.value = false;
  createForm.first_name = '';
  createForm.phone_number = '+998';
  createForm.bot_access = true;
  createForm.is_active = true;
};

const handleCreateSubmit = async () => {
  if (!createForm.first_name.trim()) {
    message.error('Пожалуйста, введите имя');
    return;
  }

  if (!createForm.phone_number.trim() || createForm.phone_number.length < 13) {
    message.error('Пожалуйста, введите корректный номер телефона');
    return;
  }

  try {
    createLoading.value = true;

    await http.post('/auth/customers/', {
      first_name: createForm.first_name,
      phone_number: createForm.phone_number,
      bot_access: createForm.bot_access,
      is_active: createForm.is_active,
    });

    message.success('Клиент успешно создан');
    createModalVisible.value = false;
    refresh();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка создания клиента');
  } finally {
    createLoading.value = false;
  }
};

// Edit modal state
const editModalVisible = ref(false);
const editLoading = ref(false);
const editForm = reactive({
  id: 0,
  first_name: '',
  phone_number: '+998',
  bot_access: true,
  is_active: true,
});

const handleEditPhoneInput = () => {
  if (!editForm.phone_number.startsWith('+998')) {
    editForm.phone_number = '+998';
  }
  const prefix = '+998';
  const rest = editForm.phone_number.slice(4).replace(/\D/g, '');
  editForm.phone_number = prefix + rest;
};

const showEditModal = (record: CustomerRecord) => {
  editForm.id = record.id;
  editForm.first_name = record.first_name;
  editForm.phone_number = record.phone_number;
  editForm.bot_access = record.bot_access;
  editForm.is_active = record.is_active;
  editModalVisible.value = true;
};

const handleEditCancel = () => {
  editModalVisible.value = false;
  editForm.id = 0;
  editForm.first_name = '';
  editForm.phone_number = '+998';
  editForm.bot_access = true;
  editForm.is_active = true;
};

const handleEditSubmit = async () => {
  if (!editForm.first_name.trim()) {
    message.error('Пожалуйста, введите имя');
    return;
  }

  if (!editForm.phone_number.trim() || editForm.phone_number.length < 13) {
    message.error('Пожалуйста, введите корректный номер телефона');
    return;
  }

  try {
    editLoading.value = true;

    await http.patch(`/auth/customers/${editForm.id}/`, {
      first_name: editForm.first_name,
      phone_number: editForm.phone_number,
      bot_access: editForm.bot_access,
      is_active: editForm.is_active,
    });

    message.success('Клиент успешно обновлён');
    editModalVisible.value = false;
    refresh();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка обновления клиента');
  } finally {
    editLoading.value = false;
  }
};

// Delete modal state
const deleteModalVisible = ref(false);
const deleteLoading = ref(false);
const deletingCustomer = reactive({
  id: 0,
  first_name: '',
});

const showDeleteModal = (record: CustomerRecord) => {
  deletingCustomer.id = record.id;
  deletingCustomer.first_name = record.first_name;
  deleteModalVisible.value = true;
};

const handleDeleteCancel = () => {
  deleteModalVisible.value = false;
  deletingCustomer.id = 0;
  deletingCustomer.first_name = '';
};

const handleDeleteSubmit = async () => {
  if (!deletingCustomer.id) {
    message.error('Ошибка: ID клиента не найден');
    return;
  }

  try {
    deleteLoading.value = true;

    await http.delete(`/auth/customers/${deletingCustomer.id}/`);

    message.success('Клиент успешно удалён');
    deleteModalVisible.value = false;
    refreshAfterDelete();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка удаления клиента');
  } finally {
    deleteLoading.value = false;
  }
};

onMounted(() => {
  fetchData();
});
</script>
