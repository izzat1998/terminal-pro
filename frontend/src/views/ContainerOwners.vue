<template>
  <a-card title="Собственники контейнеров" :bordered="false">
    <template #extra>
      <a-space>
        <a-input-search
          v-model:value="searchText"
          placeholder="Поиск по названию..."
          style="width: 250px;"
          allow-clear
          @search="handleSearch"
          @pressEnter="handleSearch"
          @change="(e: Event) => { if (!(e.target as HTMLInputElement).value) handleSearch() }"
        />
        <a-button type="primary" @click="showCreateModal">
          <template #icon>
            <PlusOutlined />
          </template>
          Создать собственника
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
      :locale="{ emptyText: undefined }"
    >
      <template #bodyCell="{ column, index, record }">
        <template v-if="column.key === 'number'">
          {{ (pagination.current - 1) * pagination.pageSize + index + 1 }}
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
              <a-button type="link" size="small" danger @click="showDeleteConfirm(record)">
                <template #icon>
                  <DeleteOutlined />
                </template>
              </a-button>
            </a-tooltip>
          </a-space>
        </template>
      </template>
      <template #emptyText>
        <a-empty :image="Empty.PRESENTED_IMAGE_SIMPLE" description="Нет собственников">
          <a-button type="primary" @click="showCreateModal">
            <template #icon><PlusOutlined /></template>
            Создать собственника
          </a-button>
        </a-empty>
      </template>
    </a-table>
  </a-card>

  <!-- Create Modal -->
  <a-modal
    v-model:open="createModalVisible"
    title="Создать собственника"
    @ok="handleCreateSubmit"
    @cancel="handleCreateCancel"
    :confirm-loading="createLoading"
  >
    <a-form :model="createForm" layout="vertical">
      <a-form-item label="Название" required>
        <a-input v-model:value="createForm.name" />
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- Edit Modal -->
  <a-modal
    v-model:open="editModalVisible"
    title="Редактировать собственника"
    @ok="handleEditSubmit"
    @cancel="handleEditCancel"
    :confirm-loading="editLoading"
  >
    <a-form :model="editForm" layout="vertical">
      <a-form-item label="Название" required>
        <a-input v-model:value="editForm.name" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { message, Modal, Empty } from 'ant-design-vue';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import { http } from '../utils/httpClient';
import { formatDateTime } from '../utils/dateFormat';

interface Owner {
  id: number;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

interface OwnerRecord {
  key: string;
  id: number;
  name: string;
  slug: string;
  created: string;
  updated: string;
}

// Search state
const searchText = ref('');

const columns = [
  {
    title: '№',
    key: 'number',
    align: 'center' as const,
    width: 80,
  },
  {
    title: 'Название',
    dataIndex: 'name',
    key: 'name',
    align: 'center' as const,
    width: 300,
  },
  {
    title: 'Дата обновления',
    dataIndex: 'updated',
    key: 'updated',
    align: 'center' as const,
    width: 200,
  },
  {
    title: 'Действия',
    key: 'actions',
    align: 'center' as const,
    width: 150,
  },
];

// Table data state
const dataSource = ref<OwnerRecord[]>([]);
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

    const data = await http.get<{ count: number; results: Owner[] }>(`/terminal/owners/?${params.toString()}`);

    dataSource.value = data.results.map(owner => ({
      key: owner.id.toString(),
      id: owner.id,
      name: owner.name,
      slug: owner.slug,
      created: formatDateTime(owner.created_at),
      updated: formatDateTime(owner.updated_at),
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
    message.error('Пожалуйста, введите название');
    return;
  }

  try {
    createLoading.value = true;

    await http.post('/terminal/owners/', { name: createForm.name });

    message.success('Собственник успешно создан');
    createModalVisible.value = false;
    refresh();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка создания собственника');
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
});

const showEditModal = (record: OwnerRecord) => {
  editForm.id = record.id;
  editForm.name = record.name;
  editModalVisible.value = true;
};

const handleEditCancel = () => {
  editModalVisible.value = false;
  editForm.id = 0;
  editForm.name = '';
};

const handleEditSubmit = async () => {
  if (!editForm.name.trim()) {
    message.error('Пожалуйста, введите название');
    return;
  }

  try {
    editLoading.value = true;

    await http.patch(`/terminal/owners/${editForm.id}/`, { name: editForm.name });

    message.success('Собственник успешно обновлён');
    editModalVisible.value = false;
    refresh();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка обновления собственника');
  } finally {
    editLoading.value = false;
  }
};

// Delete functionality
const showDeleteConfirm = (record: OwnerRecord) => {
  Modal.confirm({
    title: 'Удалить собственника?',
    content: `Вы уверены, что хотите удалить собственника "${record.name}"? Это действие невозможно отменить.`,
    okText: 'Удалить',
    okType: 'danger',
    cancelText: 'Отмена',
    maskClosable: true,
    async onOk() {
      await handleDelete(record.id);
    },
  });
};

const handleDelete = async (ownerId: number) => {
  try {
    await http.delete(`/terminal/owners/${ownerId}/`);

    message.success('Собственник успешно удалён');
    refresh();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка при удалении собственника');
  }
};

onMounted(() => {
  fetchData();
});
</script>
