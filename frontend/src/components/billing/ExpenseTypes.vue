<template>
  <div class="expense-types">
    <!-- Header with add button -->
    <div class="header-actions">
      <a-button type="primary" @click="openAddModal">
        <template #icon><PlusOutlined /></template>
        Добавить тип расхода
      </a-button>
    </div>

    <a-empty v-if="!loading && expenseTypes.length === 0" description="Типы расходов не найдены" />

    <a-table
      v-else
      :columns="columns"
      :data-source="expenseTypes"
      :loading="loading"
      row-key="id"
      size="small"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <span>{{ record.name }}</span>
        </template>
        <template v-if="column.key === 'default_rate_usd'">
          <span class="amount-usd">${{ parseFloat(record.default_rate_usd).toFixed(2) }}</span>
        </template>
        <template v-if="column.key === 'default_rate_uzs'">
          <span class="amount-uzs">{{ formatUzs(record.default_rate_uzs) }}</span>
        </template>
        <template v-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'default'">
            {{ record.is_active ? 'Активен' : 'Неактивен' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'actions'">
          <a-space>
            <a-tooltip title="Редактировать">
              <a-button type="link" size="small" @click="openEditModal(record)">
                <template #icon><EditOutlined /></template>
              </a-button>
            </a-tooltip>
            <a-popconfirm
              title="Удалить тип расхода?"
              ok-text="Да"
              cancel-text="Нет"
              @confirm="handleDelete(record.id)"
            >
              <a-tooltip title="Удалить">
                <a-button type="link" size="small" danger>
                  <template #icon><DeleteOutlined /></template>
                </a-button>
              </a-tooltip>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- Add/Edit Modal -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingType ? 'Редактировать тип расхода' : 'Добавить тип расхода'"
      :confirm-loading="saving"
      @ok="handleSave"
      @cancel="closeModal"
    >
      <a-form ref="formRef" :model="formState" :rules="formRules" layout="vertical">
        <a-form-item label="Название" name="name">
          <a-input v-model:value="formState.name" placeholder="Например: Кран, Досмотр" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Ставка USD" name="default_rate_usd">
              <a-input-number
                v-model:value="formState.default_rate_usd"
                :min="0"
                :precision="2"
                prefix="$"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Ставка UZS" name="default_rate_uzs">
              <a-input-number
                v-model:value="formState.default_rate_uzs"
                :min="0"
                :precision="0"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="Статус" name="is_active">
          <a-switch v-model:checked="formState.is_active" checked-children="Активен" un-checked-children="Неактивен" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import type { FormInstance, TableProps } from 'ant-design-vue';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import {
  expenseTypesService,
  type ExpenseType,
  type ExpenseTypeCreateData,
} from '../../services/expenseTypesService';

const expenseTypes = ref<ExpenseType[]>([]);
const loading = ref(false);

// Modal state
const modalVisible = ref(false);
const saving = ref(false);
const editingType = ref<ExpenseType | null>(null);
const formRef = ref<FormInstance>();

interface FormState {
  name: string;
  default_rate_usd: number | null;
  default_rate_uzs: number | null;
  is_active: boolean;
}

const formState = reactive<FormState>({
  name: '',
  default_rate_usd: null,
  default_rate_uzs: null,
  is_active: true,
});

const formRules = {
  name: [{ required: true, message: 'Введите название' }],
  default_rate_usd: [{ required: true, message: 'Введите ставку USD' }],
  default_rate_uzs: [{ required: true, message: 'Введите ставку UZS' }],
};

const columns: TableProps['columns'] = [
  { title: 'Название', key: 'name', dataIndex: 'name', width: 200 },
  { title: 'Ставка USD', key: 'default_rate_usd', width: 120, align: 'right' },
  { title: 'Ставка UZS', key: 'default_rate_uzs', width: 150, align: 'right' },
  { title: 'Статус', key: 'is_active', width: 100 },
  { title: '', key: 'actions', width: 100, align: 'center' },
];

const formatUzs = (value: string): string => {
  const num = parseFloat(value);
  if (isNaN(num)) return '—';
  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 0 })} сум`;
};

const fetchExpenseTypes = async () => {
  loading.value = true;
  try {
    expenseTypes.value = await expenseTypesService.getAll();
  } catch (error) {
    console.error('Error fetching expense types:', error);
    message.error('Не удалось загрузить типы расходов');
  } finally {
    loading.value = false;
  }
};

const openAddModal = () => {
  editingType.value = null;
  formState.name = '';
  formState.default_rate_usd = null;
  formState.default_rate_uzs = null;
  formState.is_active = true;
  modalVisible.value = true;
};

const openEditModal = (expenseType: ExpenseType) => {
  editingType.value = expenseType;
  formState.name = expenseType.name;
  formState.default_rate_usd = parseFloat(expenseType.default_rate_usd);
  formState.default_rate_uzs = parseFloat(expenseType.default_rate_uzs);
  formState.is_active = expenseType.is_active;
  modalVisible.value = true;
};

const closeModal = () => {
  modalVisible.value = false;
  editingType.value = null;
  formRef.value?.resetFields();
};

const handleSave = async () => {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  saving.value = true;
  try {
    const data: ExpenseTypeCreateData = {
      name: formState.name,
      default_rate_usd: formState.default_rate_usd!,
      default_rate_uzs: formState.default_rate_uzs!,
      is_active: formState.is_active,
    };

    if (editingType.value) {
      await expenseTypesService.update(editingType.value.id, data);
      message.success('Тип расхода обновлен');
    } else {
      await expenseTypesService.create(data);
      message.success('Тип расхода добавлен');
    }

    closeModal();
    fetchExpenseTypes();
  } catch (error) {
    console.error('Error saving expense type:', error);
    message.error('Не удалось сохранить тип расхода');
  } finally {
    saving.value = false;
  }
};

const handleDelete = async (id: number) => {
  try {
    await expenseTypesService.delete(id);
    message.success('Тип расхода удален');
    fetchExpenseTypes();
  } catch (error) {
    console.error('Error deleting expense type:', error);
    message.error('Не удалось удалить тип расхода');
  }
};

onMounted(fetchExpenseTypes);
</script>

<style scoped>
.expense-types {
  padding: 8px 0;
}

.header-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.amount-usd {
  font-weight: 600;
  color: #52c41a;
}

.amount-uzs {
  font-weight: 500;
  color: #722ed1;
}
</style>
