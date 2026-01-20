<template>
  <div class="additional-charges">
    <!-- Header with search and add button -->
    <div class="header-actions">
      <a-space>
        <a-input-search
          v-model:value="searchText"
          placeholder="Поиск по номеру контейнера"
          style="width: 250px"
          allow-clear
        />
        <a-button v-if="isAdmin" type="primary" @click="openAddModal">
          <template #icon><PlusOutlined /></template>
          Добавить
        </a-button>
      </a-space>
    </div>

    <!-- Summary Statistics -->
    <a-row :gutter="[16, 16]" style="margin-bottom: 20px;">
      <a-col :xs="12" :sm="8">
        <a-statistic
          title="Всего начислений"
          :value="summary.total_charges"
          :value-style="{ color: '#1677ff' }"
        >
          <template #prefix><FileTextOutlined /></template>
        </a-statistic>
      </a-col>
      <a-col :xs="12" :sm="8">
        <a-statistic
          title="Итого (USD)"
          :value="formatCurrency(summary.total_usd, 'USD')"
          :value-style="{ color: '#52c41a' }"
        />
      </a-col>
      <a-col :xs="12" :sm="8">
        <a-statistic
          title="Итого (UZS)"
          :value="formatCurrency(summary.total_uzs, 'UZS')"
          :value-style="{ color: '#722ed1' }"
        />
      </a-col>
    </a-row>

    <a-divider style="margin: 12px 0;" />

    <!-- Filters -->
    <a-space wrap style="margin-bottom: 16px;">
      <a-range-picker
        v-model:value="dateRange"
        format="DD.MM.YYYY"
        :placeholder="['Дата с', 'Дата по']"
        style="width: 240px"
        @change="fetchCharges"
        allow-clear
      />
    </a-space>

    <a-empty v-if="!loading && charges.length === 0" description="Дополнительные начисления не найдены" />

    <a-table
      v-else
      :columns="columns"
      :data-source="charges"
      :loading="loading"
      row-key="id"
      :scroll="{ x: 1000 }"
      size="small"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'container'">
          <a-tag color="blue">{{ record.container_number }}</a-tag>
        </template>
        <template v-if="column.key === 'company'">
          <span>{{ record.company_name || '—' }}</span>
        </template>
        <template v-if="column.key === 'charge_date'">
          {{ formatDate(record.charge_date) }}
        </template>
        <template v-if="column.key === 'amount_usd'">
          <span class="amount-usd">${{ parseFloat(record.amount_usd).toFixed(2) }}</span>
        </template>
        <template v-if="column.key === 'amount_uzs'">
          <span class="amount-uzs">{{ formatUzs(record.amount_uzs) }}</span>
        </template>
        <template v-if="column.key === 'actions'">
          <a-space v-if="isAdmin">
            <a-tooltip title="Редактировать">
              <a-button type="link" size="small" @click="openEditModal(record)">
                <template #icon><EditOutlined /></template>
              </a-button>
            </a-tooltip>
            <a-popconfirm
              title="Удалить начисление?"
              ok-text="Да"
              cancel-text="Нет"
              @confirm="deleteCharge(record.id)"
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
      :title="editingCharge ? 'Редактировать начисление' : 'Добавить начисление'"
      :confirm-loading="saving"
      @ok="handleSave"
      @cancel="closeModal"
    >
      <a-form ref="formRef" :model="formState" :rules="formRules" layout="vertical">
        <a-form-item v-if="!editingCharge" label="Контейнер" name="container_entry">
          <a-select
            v-model:value="formState.container_entry"
            show-search
            placeholder="Выберите контейнер"
            :filter-option="filterContainer"
            :options="containerOptions"
            :loading="loadingContainers"
          />
        </a-form-item>
        <a-form-item v-else label="Контейнер">
          <a-input :value="editingCharge.container_number" disabled />
        </a-form-item>
        <a-form-item label="Описание" name="description">
          <a-input
            v-model:value="formState.description"
            placeholder="Например: Использование крана, Досмотр"
          />
        </a-form-item>
        <a-form-item label="Дата начисления" name="charge_date">
          <a-date-picker
            v-model:value="formState.charge_date"
            format="DD.MM.YYYY"
            style="width: 100%"
          />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Сумма USD" name="amount_usd">
              <a-input-number
                v-model:value="formState.amount_usd"
                :min="0.01"
                :precision="2"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Сумма UZS" name="amount_uzs">
              <a-input-number
                v-model:value="formState.amount_uzs"
                :min="1"
                :precision="0"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>

    <!-- Expense Type Selection Modal -->
    <a-modal
      v-model:open="expenseTypeModalVisible"
      title="Добавить расходы"
      width="500px"
      :confirm-loading="savingMultiple"
      @ok="addSelectedExpenses"
      ok-text="Добавить"
      cancel-text="Отмена"
    >
      <div class="expense-type-header">
        <a-tag color="blue" style="font-size: 14px; padding: 4px 12px;">
          {{ pendingContainerNumber }}
        </a-tag>
      </div>

      <!-- Existing Expenses Section -->
      <div v-if="containerExpenses.length > 0" class="existing-expenses-section">
        <a-divider orientation="left" style="margin: 12px 0 8px 0; font-size: 13px;">
          Уже добавленные расходы ({{ containerExpenses.length }})
        </a-divider>
        <a-spin :spinning="loadingContainerExpenses">
          <div class="existing-expenses-list">
            <a-tag
              v-for="expense in containerExpenses"
              :key="expense.id"
              color="green"
              class="existing-expense-tag"
            >
              {{ expense.description }}
              <span class="existing-expense-amount">${{ parseFloat(expense.amount_usd).toFixed(2) }}</span>
            </a-tag>
          </div>
        </a-spin>
      </div>

      <!-- Select Expense Types Section -->
      <a-divider orientation="left" style="margin: 16px 0 8px 0; font-size: 13px;">
        Выберите типы расходов
      </a-divider>
      <a-spin :spinning="loadingExpenseTypes">
        <div v-if="expenseTypes.length > 0" class="expense-types-grid">
          <div
            v-for="item in expenseTypes"
            :key="item.id"
            :class="['expense-type-card', { 'expense-type-card-selected': isExpenseTypeSelected(item.id) }]"
            @click="toggleExpenseType(item.id)"
          >
            <a-checkbox :checked="isExpenseTypeSelected(item.id)" class="expense-type-checkbox" />
            <div class="expense-type-info">
              <div class="expense-type-name">{{ item.name }}</div>
              <div class="expense-type-rates">
                <span class="rate-usd">${{ parseFloat(item.default_rate_usd).toFixed(2) }}</span>
                <span class="rate-separator">•</span>
                <span class="rate-uzs">{{ formatUzs(item.default_rate_uzs) }}</span>
              </div>
            </div>
          </div>
        </div>
        <a-empty v-else description="Нет доступных типов расходов" />
      </a-spin>

      <!-- Selection Summary -->
      <div v-if="selectedExpenseTypeIds.length > 0" class="selection-summary">
        <a-alert
          type="info"
          :message="`Выбрано: ${selectedExpenseTypeIds.length} тип(ов) расходов`"
          show-icon
        />
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, computed } from 'vue';
import { message } from 'ant-design-vue';
import type { FormInstance, TableProps } from 'ant-design-vue';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
} from '@ant-design/icons-vue';
import {
  additionalChargesService,
  type AdditionalCharge,
  type AdditionalChargeSummary,
} from '../../services/additionalChargesService';
import { expenseTypesService, type ExpenseType } from '../../services/expenseTypesService';
import { http } from '../../utils/httpClient';

interface Props {
  companySlug?: string;
  isAdmin?: boolean;
  showAllCompanies?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isAdmin: false,
  showAllCompanies: false,
});

const emit = defineEmits<{
  chargesAdded: [containerId: number];
}>();

const charges = ref<AdditionalCharge[]>([]);
const loading = ref(false);
const searchText = ref('');
const dateRange = ref<[Dayjs, Dayjs] | null>(null);
const summary = ref<AdditionalChargeSummary>({
  total_charges: 0,
  total_usd: '0',
  total_uzs: '0',
});

// Modal state
const modalVisible = ref(false);
const saving = ref(false);
const editingCharge = ref<AdditionalCharge | null>(null);
const formRef = ref<FormInstance>();
const loadingContainers = ref(false);

// Expense type selection modal state
const expenseTypeModalVisible = ref(false);
const expenseTypes = ref<ExpenseType[]>([]);
const loadingExpenseTypes = ref(false);
const pendingContainerId = ref<number | null>(null);
const pendingContainerNumber = ref('');
const selectedExpenseTypeIds = ref<number[]>([]);
const savingMultiple = ref(false);

// Existing expenses for container
const containerExpenses = ref<AdditionalCharge[]>([]);
const loadingContainerExpenses = ref(false);

interface FormState {
  container_entry: number | null;
  description: string;
  amount_usd: number | null;
  amount_uzs: number | null;
  charge_date: Dayjs | null;
}

const formState = reactive<FormState>({
  container_entry: null,
  description: '',
  amount_usd: null,
  amount_uzs: null,
  charge_date: dayjs(),
});

const formRules = {
  container_entry: [{ required: true, message: 'Выберите контейнер' }],
  description: [{ required: true, message: 'Введите описание' }],
  amount_usd: [{ required: true, message: 'Введите сумму USD' }],
  amount_uzs: [{ required: true, message: 'Введите сумму UZS' }],
  charge_date: [{ required: true, message: 'Выберите дату' }],
};

const containerOptions = ref<{ label: string; value: number }[]>([]);

const columns = computed<TableProps['columns']>(() => {
  const cols: TableProps['columns'] = [
    { title: 'Дата', key: 'charge_date', width: 100 },
    { title: 'Контейнер', key: 'container', width: 140 },
  ];

  if (props.showAllCompanies) {
    cols.push({ title: 'Компания', key: 'company', width: 150 });
  }

  cols.push(
    { title: 'Описание', dataIndex: 'description', key: 'description', width: 200 },
    { title: 'Сумма USD', key: 'amount_usd', width: 120, align: 'right' },
    { title: 'Сумма UZS', key: 'amount_uzs', width: 150, align: 'right' },
    { title: '', key: 'actions', width: 80, align: 'center' }
  );

  return cols;
});

let searchTimeout: ReturnType<typeof setTimeout> | null = null;
watch(searchText, () => {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(fetchCharges, 400);
});

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('ru-RU');
};

const formatCurrency = (value: string, currency: 'USD' | 'UZS'): string => {
  const num = parseFloat(value);
  if (isNaN(num)) return '—';
  if (currency === 'USD') {
    return `$${num.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}`;
  }
  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 0 })} сум`;
};

const formatUzs = (value: string): string => {
  const num = parseFloat(value);
  if (isNaN(num)) return '—';
  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 0 })} сум`;
};

const filterContainer = (input: string, option: { label: string }) => {
  return option.label.toLowerCase().includes(input.toLowerCase());
};

const fetchCharges = async () => {
  loading.value = true;
  try {
    const params: { date_from?: string; date_to?: string; search?: string } = {};

    if (dateRange.value && dateRange.value[0] && dateRange.value[1]) {
      params.date_from = dateRange.value[0].format('YYYY-MM-DD');
      params.date_to = dateRange.value[1].format('YYYY-MM-DD');
    }

    if (searchText.value.trim()) {
      params.search = searchText.value.trim();
    }

    let response;
    if (props.showAllCompanies) {
      response = await additionalChargesService.getAllCharges(params);
    } else if (props.companySlug) {
      response = await additionalChargesService.getCompanyCharges(props.companySlug, params);
    } else {
      response = await additionalChargesService.getCustomerCharges(params);
    }

    charges.value = response.data;
    summary.value = response.summary;
  } catch (error) {
    console.error('Error fetching charges:', error);
    message.error('Не удалось загрузить начисления');
  } finally {
    loading.value = false;
  }
};

const fetchContainers = async () => {
  if (!props.isAdmin) return;

  loadingContainers.value = true;
  try {
    let url: string;
    if (props.showAllCompanies) {
      url = '/terminal/entries/?page_size=500';
    } else if (props.companySlug) {
      url = `/auth/companies/${props.companySlug}/entries/?page_size=500`;
    } else {
      url = '/terminal/entries/?page_size=500';
    }

    interface ContainerResponse {
      results: Array<{ id: number; container_number?: string; container?: { container_number: string } }>;
    }

    const response = await http.get<ContainerResponse>(url);
    containerOptions.value = response.results.map((c) => ({
      label: c.container_number || c.container?.container_number || `Entry ${c.id}`,
      value: c.id,
    }));
  } catch (error) {
    console.error('Error fetching containers:', error);
  } finally {
    loadingContainers.value = false;
  }
};

const openAddModal = () => {
  editingCharge.value = null;
  formState.container_entry = null;
  formState.description = '';
  formState.amount_usd = null;
  formState.amount_uzs = null;
  formState.charge_date = dayjs();
  modalVisible.value = true;
  fetchContainers();
};

const openEditModal = (charge: AdditionalCharge) => {
  editingCharge.value = charge;
  formState.container_entry = charge.container_entry;
  formState.description = charge.description;
  formState.amount_usd = parseFloat(charge.amount_usd);
  formState.amount_uzs = parseFloat(charge.amount_uzs);
  formState.charge_date = dayjs(charge.charge_date);
  modalVisible.value = true;
};

const closeModal = () => {
  modalVisible.value = false;
  editingCharge.value = null;
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
    const data = {
      container_entry: formState.container_entry!,
      description: formState.description,
      amount_usd: formState.amount_usd!,
      amount_uzs: formState.amount_uzs!,
      charge_date: formState.charge_date!.format('YYYY-MM-DD'),
    };

    if (editingCharge.value) {
      await additionalChargesService.update(editingCharge.value.id, data);
      message.success('Начисление обновлено');
    } else {
      await additionalChargesService.create(data);
      message.success('Начисление добавлено');
    }

    closeModal();
    fetchCharges();
  } catch (error) {
    console.error('Error saving charge:', error);
    message.error('Не удалось сохранить начисление');
  } finally {
    saving.value = false;
  }
};

const deleteCharge = async (id: number) => {
  try {
    await additionalChargesService.delete(id);
    message.success('Начисление удалено');
    fetchCharges();
  } catch (error) {
    console.error('Error deleting charge:', error);
    message.error('Не удалось удалить начисление');
  }
};

const fetchExpenseTypes = async () => {
  loadingExpenseTypes.value = true;
  try {
    expenseTypes.value = await expenseTypesService.getAll(true); // Only active
  } catch (error) {
    console.error('Error fetching expense types:', error);
    message.error('Не удалось загрузить типы расходов');
  } finally {
    loadingExpenseTypes.value = false;
  }
};

const fetchContainerExpenses = async (containerId: number) => {
  loadingContainerExpenses.value = true;
  try {
    const response = await http.get<{ data: AdditionalCharge[] }>(
      `/billing/additional-charges/?container_entry_id=${containerId}`
    );
    containerExpenses.value = response.data || [];
  } catch (error) {
    console.error('Error fetching container expenses:', error);
    containerExpenses.value = [];
  } finally {
    loadingContainerExpenses.value = false;
  }
};

const toggleExpenseType = (id: number) => {
  const index = selectedExpenseTypeIds.value.indexOf(id);
  if (index > -1) {
    selectedExpenseTypeIds.value.splice(index, 1);
  } else {
    selectedExpenseTypeIds.value.push(id);
  }
};

const isExpenseTypeSelected = (id: number) => {
  return selectedExpenseTypeIds.value.includes(id);
};

const addSelectedExpenses = async () => {
  if (selectedExpenseTypeIds.value.length === 0) {
    message.warning('Выберите хотя бы один тип расхода');
    return;
  }

  savingMultiple.value = true;
  try {
    const today = dayjs().format('YYYY-MM-DD');
    const selectedTypes = expenseTypes.value.filter(et =>
      selectedExpenseTypeIds.value.includes(et.id)
    );

    // Create all charges in parallel
    await Promise.all(
      selectedTypes.map(expenseType =>
        additionalChargesService.create({
          container_entry: pendingContainerId.value!,
          description: expenseType.name,
          amount_usd: parseFloat(expenseType.default_rate_usd),
          amount_uzs: parseFloat(expenseType.default_rate_uzs),
          charge_date: today,
        })
      )
    );

    message.success(`Добавлено ${selectedTypes.length} начислений`);
    expenseTypeModalVisible.value = false;
    selectedExpenseTypeIds.value = [];
    emit('chargesAdded', pendingContainerId.value!);
    fetchCharges();
  } catch (error) {
    console.error('Error adding expenses:', error);
    message.error('Не удалось добавить начисления');
  } finally {
    savingMultiple.value = false;
  }
};

onMounted(fetchCharges);

// Expose method for parent to trigger charge creation with pre-selected container
defineExpose({
  openAddModalForContainer: async (containerId: number, containerNumber: string) => {
    pendingContainerId.value = containerId;
    pendingContainerNumber.value = containerNumber;
    selectedExpenseTypeIds.value = [];
    expenseTypeModalVisible.value = true;
    // Fetch both expense types and existing container expenses in parallel
    await Promise.all([
      fetchExpenseTypes(),
      fetchContainerExpenses(containerId),
    ]);
  },
});
</script>

<style scoped>
.additional-charges {
  padding: 8px 0;
}

.header-actions {
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

.expense-type-header {
  margin-bottom: 8px;
  text-align: center;
}

/* Existing expenses section */
.existing-expenses-section {
  background: #f6ffed;
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 8px;
}

.existing-expenses-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.existing-expense-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.existing-expense-amount {
  font-weight: 600;
  opacity: 0.8;
}

/* Expense types grid */
.expense-types-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.expense-type-card {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}

.expense-type-card:hover {
  border-color: #1677ff;
  background: #f0f7ff;
}

.expense-type-card-selected {
  border-color: #1677ff;
  background: #e6f4ff;
}

.expense-type-checkbox {
  margin-right: 10px;
}

.expense-type-info {
  flex: 1;
  min-width: 0;
}

.expense-type-name {
  font-weight: 500;
  font-size: 13px;
  color: #262626;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.expense-type-rates {
  font-size: 12px;
  margin-top: 2px;
}

.rate-usd {
  color: #52c41a;
  font-weight: 500;
}

.rate-separator {
  margin: 0 6px;
  color: #d9d9d9;
}

.rate-uzs {
  color: #722ed1;
}

.selection-summary {
  margin-top: 16px;
}
</style>
