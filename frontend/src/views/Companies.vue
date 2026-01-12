<template>
  <a-card title="Компании" :bordered="false">
    <template #extra>
      <a-button type="primary" @click="showCreateModal">
        <template #icon>
          <PlusOutlined />
        </template>
        Создать компанию
      </a-button>
    </template>

    <a-table
      :columns="columns"
      :data-source="dataSource"
      :pagination="pagination"
      :loading="loading"
      @change="handleTableChange"
      bordered
      :scroll="{ x: 1200 }"
    >
      <template #bodyCell="{ column, index, record }">
        <template v-if="column.key === 'number'">
          {{ (pagination.current - 1) * pagination.pageSize + index + 1 }}
        </template>
        <template v-else-if="column.key === 'name'">
          <router-link :to="`/accounts/companies/${record.slug}/users`">{{ record.name }}</router-link>
        </template>
        <template v-else-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? 'Активна' : 'Неактивна' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'notifications'">
          <a-tag :color="record.notifications_enabled ? 'green' : 'default'">
            {{ record.notifications_enabled ? 'Вкл' : 'Выкл' }}
          </a-tag>
          <div v-if="record.telegram_group_name" style="font-size: 12px; color: #888;">
            {{ record.telegram_group_name }}
          </div>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-button type="link" size="small" @click="showEditModal(record)">
            Настройки
          </a-button>
        </template>
      </template>
    </a-table>
  </a-card>

  <!-- Create Modal -->
  <a-modal
    v-model:open="createModalVisible"
    title="Создать компанию"
    @ok="handleCreateSubmit"
    @cancel="handleCreateCancel"
    :confirm-loading="createLoading"
  >
    <a-form :model="createForm" layout="vertical">
      <a-form-item label="Название" required>
        <a-input v-model:value="createForm.name" placeholder="Введите название компании" />
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- Edit Notification Settings Modal -->
  <a-modal
    v-model:open="editModalVisible"
    title="Настройки уведомлений"
    @ok="handleEditSubmit"
    @cancel="handleEditCancel"
    :confirm-loading="editLoading"
  >
    <a-form :model="editForm" layout="vertical">
      <a-form-item label="Компания">
        <a-input :value="editForm.name" disabled />
      </a-form-item>
      <a-form-item label="Уведомления в Telegram">
        <a-switch v-model:checked="editForm.notifications_enabled" />
        <span style="margin-left: 8px; color: #666;">
          {{ editForm.notifications_enabled ? 'Включены' : 'Выключены' }}
        </span>
      </a-form-item>
      <a-form-item label="Telegram группа" :required="editForm.notifications_enabled">
        <a-input
          v-model:value="editForm.telegram_group_id"
          placeholder="@mygroup или -1001234567890"
          :disabled="!editForm.notifications_enabled"
        />
        <div style="font-size: 12px; color: #888; margin-top: 4px;">
          <div><b>Вариант 1:</b> Username публичной группы (например: @mygroup)</div>
          <div><b>Вариант 2:</b> ID группы (для приватных групп). Добавьте @RawDataBot в группу чтобы узнать ID</div>
        </div>
      </a-form-item>
      <a-form-item label="Название группы">
        <a-input
          v-model:value="editForm.telegram_group_name"
          placeholder="Название для отображения"
          :disabled="!editForm.notifications_enabled"
        />
      </a-form-item>
    </a-form>
  </a-modal>

</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { message } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import { formatDateTime } from '../utils/dateFormat';
import { http } from '../utils/httpClient';
import { useCrudTable } from '../composables/useCrudTable';

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  telegram_group_id: string | null;
  telegram_group_name: string;
  notifications_enabled: boolean;
  customers_count: number;
  entries_count: number;
  created_at: string;
  updated_at: string;
}

interface CompanyRecord {
  key: string;
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  telegram_group_id: string | null;
  telegram_group_name: string;
  notifications_enabled: boolean;
  customers_count: number;
  entries_count: number;
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
    title: 'Название',
    dataIndex: 'name',
    key: 'name',
    align: 'center' as const,
    width: 200,
  },
  {
    title: 'Статус',
    key: 'is_active',
    align: 'center' as const,
    width: 100,
  },
  {
    title: 'Клиенты',
    dataIndex: 'customers_count',
    key: 'customers_count',
    align: 'center' as const,
    width: 100,
  },
  {
    title: 'Контейнеры',
    dataIndex: 'entries_count',
    key: 'entries_count',
    align: 'center' as const,
    width: 110,
  },
  {
    title: 'Telegram',
    key: 'notifications',
    align: 'center' as const,
    width: 150,
  },
  {
    title: 'Создана',
    dataIndex: 'created',
    key: 'created',
    align: 'center' as const,
    width: 140,
  },
  {
    title: 'Действия',
    key: 'actions',
    align: 'center' as const,
    width: 120,
  },
];

// Use composable for table data management
const { dataSource, loading, pagination, fetchData, handleTableChange, refresh } = useCrudTable<Company, CompanyRecord>(
  '/auth/companies/',
  (company) => ({
    key: company.id.toString(),
    id: company.id,
    name: company.name,
    slug: company.slug,
    is_active: company.is_active,
    telegram_group_id: company.telegram_group_id,
    telegram_group_name: company.telegram_group_name,
    notifications_enabled: company.notifications_enabled,
    customers_count: company.customers_count,
    entries_count: company.entries_count,
    created: formatDateTime(company.created_at),
    updated: formatDateTime(company.updated_at),
  })
);

// Create modal state
const createModalVisible = ref(false);
const createLoading = ref(false);
const createForm = reactive({
  name: '',
});

const showCreateModal = () => {
  createForm.name = '';
  createModalVisible.value = true;
};

const handleCreateCancel = () => {
  createModalVisible.value = false;
  createForm.name = '';
};

const handleCreateSubmit = async () => {
  if (!createForm.name.trim()) {
    message.error('Пожалуйста, введите название компании');
    return;
  }

  try {
    createLoading.value = true;

    await http.post('/auth/companies/', {
      name: createForm.name,
    });

    message.success('Компания успешно создана');
    createModalVisible.value = false;
    refresh();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка создания компании');
  } finally {
    createLoading.value = false;
  }
};

// Edit modal state
const editModalVisible = ref(false);
const editLoading = ref(false);
const editForm = reactive({
  id: 0,
  name: '',
  slug: '',
  notifications_enabled: false,
  telegram_group_id: '',
  telegram_group_name: '',
});

const showEditModal = (record: CompanyRecord) => {
  editForm.id = record.id;
  editForm.name = record.name;
  editForm.slug = record.slug;
  editForm.notifications_enabled = record.notifications_enabled;
  editForm.telegram_group_id = record.telegram_group_id || '';
  editForm.telegram_group_name = record.telegram_group_name || '';
  editModalVisible.value = true;
};

const handleEditCancel = () => {
  editModalVisible.value = false;
  editForm.id = 0;
  editForm.name = '';
  editForm.slug = '';
  editForm.notifications_enabled = false;
  editForm.telegram_group_id = '';
  editForm.telegram_group_name = '';
};

const handleEditSubmit = async () => {
  // Validate if notifications enabled but no group ID
  if (editForm.notifications_enabled && !editForm.telegram_group_id.trim()) {
    message.error('Введите Telegram Group ID для включения уведомлений');
    return;
  }

  try {
    editLoading.value = true;

    await http.patch(`/auth/companies/${editForm.slug}/`, {
      notifications_enabled: editForm.notifications_enabled,
      telegram_group_id: editForm.telegram_group_id.trim() || null,
      telegram_group_name: editForm.telegram_group_name.trim(),
    });

    message.success('Настройки сохранены');
    editModalVisible.value = false;
    refresh();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка сохранения настроек');
  } finally {
    editLoading.value = false;
  }
};

onMounted(() => {
  fetchData();
});
</script>
