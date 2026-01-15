<template>
  <a-card title="Менеджеры" :bordered="false">
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
          Создать менеджера
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
      :scroll="{ x: 1200 }"
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
        <template v-else-if="column.key === 'gate_access'">
          <a-tag :color="record.gate_access ? 'green' : 'red'">
            {{ record.gate_access ? 'Да' : 'Нет' }}
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
        <a-empty :image="Empty.PRESENTED_IMAGE_SIMPLE" description="Нет менеджеров">
          <a-button type="primary" @click="showCreateModal">
            <template #icon><PlusOutlined /></template>
            Создать менеджера
          </a-button>
        </a-empty>
      </template>
    </a-table>
  </a-card>

  <!-- Create Modal -->
  <a-modal
    v-model:open="createModalVisible"
    title="Создать менеджера"
    @ok="handleCreateSubmit"
    @cancel="handleCreateCancel"
    :confirm-loading="createLoading"
  >
    <a-form :model="createForm" layout="vertical">
      <a-form-item label="Имя" required>
        <a-input v-model:value="createForm.first_name" placeholder="Введите имя" />
      </a-form-item>
      <a-form-item label="Телефон" required extra="Формат: +998XXXXXXXXX (9 цифр после +998)">
        <a-input v-model:value="createForm.phone_number" placeholder="+998901234567" />
      </a-form-item>
      <a-form-item label="Пароль" required extra="Минимум 8 символов">
        <a-input-password v-model:value="createForm.password" placeholder="Введите пароль" />
      </a-form-item>
      <a-form-item label="Доступ к боту">
        <a-switch v-model:checked="createForm.bot_access" />
      </a-form-item>
      <a-form-item label="Доступ к воротам">
        <a-switch v-model:checked="createForm.gate_access" />
      </a-form-item>
      <a-form-item label="Доступ к системе">
        <a-switch v-model:checked="createForm.is_active" />
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- Edit Modal -->
  <ManagerEditModal
    v-model:open="editModalVisible"
    :manager-id="editingManager.id"
    :first-name="editingManager.first_name"
    :phone-number="editingManager.phone_number"
    :bot-access="editingManager.bot_access"
    :gate-access="editingManager.gate_access"
    :is-active="editingManager.is_active"
    @success="handleEditSuccess"
  />

  <!-- Delete Modal -->
  <a-modal
    v-model:open="deleteModalVisible"
    title="Удалить менеджера"
    @ok="handleDeleteSubmit"
    @cancel="handleDeleteCancel"
    :confirm-loading="deleteLoading"
    okText="Удалить"
    cancelText="Отмена"
    okType="danger"
  >
    <p>Вы уверены, что хотите удалить менеджера <strong>{{ deletingManager.first_name }}</strong>?</p>
    <p>Это действие невозможно отменить.</p>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue';
import { message, Empty } from 'ant-design-vue';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import { http } from '../utils/httpClient';
import { formatDateTime } from '../utils/dateFormat';
import ManagerEditModal from '../components/ManagerEditModal.vue';
import { userService } from '../services/userService';

interface Manager {
  id: number;
  first_name: string;
  phone_number: string;
  bot_access: boolean;
  gate_access: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ManagerRecord {
  key: string;
  id: number;
  first_name: string;
  phone_number: string;
  bot_access: boolean;
  gate_access: boolean;
  is_active: boolean;
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
  },
  {
    title: 'Телефон',
    dataIndex: 'phone_number',
    key: 'phone_number',
    align: 'center' as const,
    width: 150,
  },
  {
    title: 'Доступ к боту',
    key: 'bot_access',
    align: 'center' as const,
    width: 120,
  },
  {
    title: 'Доступ к воротам',
    key: 'gate_access',
    align: 'center' as const,
    width: 140,
  },
  {
    title: 'Доступ к системе',
    key: 'is_active',
    align: 'center' as const,
    width: 130,
  },
  {
    title: 'Дата создания',
    dataIndex: 'created',
    key: 'created',
    align: 'center' as const,
    width: 180,
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
const dataSource = ref<ManagerRecord[]>([]);
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

    const data = await http.get<{ count: number; results: Manager[] }>(`/auth/managers/?${params.toString()}`);

    dataSource.value = data.results.map(manager => ({
      key: manager.id.toString(),
      id: manager.id,
      first_name: manager.first_name,
      phone_number: manager.phone_number,
      bot_access: manager.bot_access,
      gate_access: manager.gate_access,
      is_active: manager.is_active,
      created: formatDateTime(manager.created_at),
      updated: formatDateTime(manager.updated_at),
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
  phone_number: '',
  password: '',
  bot_access: true,
  gate_access: true,
  is_active: true,
});

const showCreateModal = () => {
  createForm.first_name = '';
  createForm.phone_number = '';
  createForm.password = '';
  createForm.bot_access = true;
  createForm.gate_access = true;
  createForm.is_active = true;
  createModalVisible.value = true;
};

const handleCreateCancel = () => {
  createModalVisible.value = false;
  createForm.first_name = '';
  createForm.phone_number = '';
  createForm.password = '';
  createForm.bot_access = true;
  createForm.gate_access = true;
  createForm.is_active = true;
};

const handleCreateSubmit = async () => {
  if (!createForm.first_name.trim()) {
    message.error('Пожалуйста, введите имя');
    return;
  }

  if (!createForm.phone_number.trim()) {
    message.error('Пожалуйста, введите телефон');
    return;
  }

  // Validate phone number format (Uzbekistan format: +998XXXXXXXXX)
  const phoneRegex = /^\+998\d{9}$/;
  if (!phoneRegex.test(createForm.phone_number)) {
    message.error('Неверный формат телефона. Используйте формат: +998XXXXXXXXX');
    return;
  }

  if (!createForm.password.trim()) {
    message.error('Пожалуйста, введите пароль');
    return;
  }

  if (createForm.password.length < 8) {
    message.error('Пароль должен содержать минимум 8 символов');
    return;
  }

  try {
    createLoading.value = true;

    await http.post('/auth/managers/', {
      first_name: createForm.first_name,
      phone_number: createForm.phone_number,
      password: createForm.password,
      bot_access: createForm.bot_access,
      gate_access: createForm.gate_access,
      is_active: createForm.is_active,
    });

    message.success('Менеджер успешно создан');
    createModalVisible.value = false;
    refresh();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка создания менеджера');
  } finally {
    createLoading.value = false;
  }
};

// Edit modal state
const editModalVisible = ref(false);
const editingManager = reactive({
  id: undefined as number | undefined,
  first_name: '',
  phone_number: '',
  bot_access: true,
  gate_access: true,
  is_active: true,
});

const showEditModal = (record: ManagerRecord) => {
  editingManager.id = record.id;
  editingManager.first_name = record.first_name;
  editingManager.phone_number = record.phone_number;
  editingManager.bot_access = record.bot_access;
  editingManager.gate_access = record.gate_access;
  editingManager.is_active = record.is_active;
  editModalVisible.value = true;
};

const handleEditSuccess = () => {
  refresh();
};

// Delete modal state
const deleteModalVisible = ref(false);
const deleteLoading = ref(false);
const deletingManager = reactive({
  id: undefined as number | undefined,
  first_name: '',
});

const showDeleteModal = (record: ManagerRecord) => {
  deletingManager.id = record.id;
  deletingManager.first_name = record.first_name;
  deleteModalVisible.value = true;
};

const handleDeleteCancel = () => {
  deleteModalVisible.value = false;
  deletingManager.id = undefined;
  deletingManager.first_name = '';
};

const handleDeleteSubmit = async () => {
  if (!deletingManager.id) {
    message.error('Ошибка: ID менеджера не найден');
    return;
  }

  try {
    deleteLoading.value = true;
    await userService.deleteManager(deletingManager.id);

    message.success('Менеджер успешно удален');
    deleteModalVisible.value = false;
    refreshAfterDelete();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка удаления менеджера');
  } finally {
    deleteLoading.value = false;
  }
};

onMounted(() => {
  fetchData();
});
</script>
