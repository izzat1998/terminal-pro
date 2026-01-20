<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { message } from 'ant-design-vue';
import type { TableProps } from 'ant-design-vue';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue';
import ExpenseTypes from '../components/billing/ExpenseTypes.vue';
import {
  tariffsService,
  type Tariff,
  type TariffCreateInput,
  type TariffRateInput,
  type ContainerSize,
  type ContainerBillingStatus,
} from '../services/tariffsService';
import { isApiError } from '../types/api';
import { http } from '../utils/httpClient';
import { formatDateLocale } from '../utils/dateFormat';

// ============================================================================
// Types
// ============================================================================

interface TariffRecord extends Tariff {
  key: number;
}

// ============================================================================
// State
// ============================================================================

const loading = ref(false);
const tariffs = ref<TariffRecord[]>([]);
const activeTab = ref('tariffs');
const pagination = ref({
  current: 1,
  pageSize: 25,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `Всего: ${total}`,
});

// Create Modal
const createModalVisible = ref(false);
const createLoading = ref(false);
const createForm = ref<{
  company: number | null;
  effective_from: string;
  effective_to: string | null;
  notes: string;
  rates: TariffRateInput[];
}>({
  company: null,
  effective_from: '',
  effective_to: null,
  notes: '',
  rates: [],
});

// Edit Modal
const editModalVisible = ref(false);
const editLoading = ref(false);
const editingTariff = ref<Tariff | null>(null);
const editForm = ref<{
  effective_to: string | null;
  notes: string;
}>({
  effective_to: null,
  notes: '',
});

// Delete Modal
const deleteModalVisible = ref(false);
const deleteLoading = ref(false);
const deletingTariff = ref<Tariff | null>(null);

// Companies for dropdown
interface Company {
  id: number;
  name: string;
  slug: string;
}
const companies = ref<Company[]>([]);
const companiesLoading = ref(false);
const tariffType = ref<'general' | 'special'>('general');

// ============================================================================
// Columns
// ============================================================================

const columns: TableProps<TariffRecord>['columns'] = [
  {
    title: 'ID',
    dataIndex: 'id',
    key: 'id',
    width: 60,
  },
  {
    title: 'Тип тарифа',
    key: 'type',
    width: 200,
  },
  {
    title: 'Действует с',
    dataIndex: 'effective_from',
    key: 'effective_from',
    width: 120,
  },
  {
    title: 'Действует до',
    key: 'effective_to',
    width: 120,
  },
  {
    title: 'Статус',
    key: 'status',
    width: 100,
  },
  {
    title: 'Ставки',
    key: 'rates',
    width: 280,
  },
  {
    title: 'Создан',
    key: 'created',
    width: 150,
  },
  {
    title: 'Действия',
    key: 'actions',
    width: 100,
    fixed: 'right',
  },
];

// ============================================================================
// Computed
// ============================================================================

const isCreateFormValid = computed(() => {
  if (!createForm.value.effective_from) return false;
  if (createForm.value.rates.length !== 4) return false;

  // If special tariff, company must be selected
  if (tariffType.value === 'special' && !createForm.value.company) return false;

  // Check all rates have values
  return createForm.value.rates.every(
    (r) =>
      r.daily_rate_usd &&
      r.daily_rate_uzs &&
      parseFloat(r.daily_rate_usd) >= 0 &&
      parseFloat(r.daily_rate_uzs) >= 0
  );
});

// ============================================================================
// Methods
// ============================================================================

async function fetchTariffs() {
  loading.value = true;
  try {
    const response = await tariffsService.getTariffs({
      page: pagination.value.current,
      page_size: pagination.value.pageSize,
    });

    tariffs.value = response.results.map((t) => ({ ...t, key: t.id }));
    pagination.value.total = response.count;
  } catch (error) {
    if (isApiError(error)) {
      message.error(error.message);
    } else {
      message.error('Ошибка при загрузке тарифов');
    }
  } finally {
    loading.value = false;
  }
}

function handleTableChange(pag: { current?: number; pageSize?: number }) {
  if (pag.current) pagination.value.current = pag.current;
  if (pag.pageSize) pagination.value.pageSize = pag.pageSize;
  fetchTariffs();
}

// Fetch companies for dropdown
async function fetchCompanies() {
  companiesLoading.value = true;
  try {
    const response = await http.get<{ results: Company[] }>('/auth/companies/');
    companies.value = response.results || [];
  } catch (error) {
    console.error('Failed to fetch companies:', error);
  } finally {
    companiesLoading.value = false;
  }
}

// Create Modal
function openCreateModal() {
  // Initialize with default rates for all 4 combinations
  const sizes: ContainerSize[] = ['20ft', '40ft'];
  const statuses: ContainerBillingStatus[] = ['laden', 'empty'];

  tariffType.value = 'general';
  createForm.value = {
    company: null,
    effective_from: new Date().toISOString().split('T')[0] ?? '',
    effective_to: null,
    notes: '',
    rates: sizes.flatMap((size) =>
      statuses.map((status) => ({
        container_size: size,
        container_status: status,
        daily_rate_usd: '',
        daily_rate_uzs: '',
        free_days: 5,
      }))
    ),
  };

  // Fetch companies if not loaded
  if (companies.value.length === 0) {
    fetchCompanies();
  }

  createModalVisible.value = true;
}

// Handle tariff type change
function handleTariffTypeChange(type: 'general' | 'special') {
  tariffType.value = type;
  if (type === 'general') {
    createForm.value.company = null;
  }
}

function closeCreateModal() {
  createModalVisible.value = false;
}

async function handleCreate() {
  if (!isCreateFormValid.value) {
    message.warning('Заполните все обязательные поля');
    return;
  }

  createLoading.value = true;
  try {
    const data: TariffCreateInput = {
      company: createForm.value.company,
      effective_from: createForm.value.effective_from,
      effective_to: createForm.value.effective_to,
      notes: createForm.value.notes,
      rates: createForm.value.rates,
    };

    await tariffsService.createTariff(data);
    message.success('Тариф успешно создан');
    closeCreateModal();
    fetchTariffs();
  } catch (error) {
    if (isApiError(error)) {
      message.error(error.message);
    } else {
      message.error('Ошибка при создании тарифа');
    }
  } finally {
    createLoading.value = false;
  }
}

// Edit Modal
function openEditModal(tariff: Tariff) {
  editingTariff.value = tariff;
  editForm.value = {
    effective_to: tariff.effective_to,
    notes: tariff.notes,
  };
  editModalVisible.value = true;
}

function closeEditModal() {
  editModalVisible.value = false;
  editingTariff.value = null;
}

async function handleEdit() {
  if (!editingTariff.value) return;

  editLoading.value = true;
  try {
    await tariffsService.updateTariff(editingTariff.value.id, {
      effective_to: editForm.value.effective_to,
      notes: editForm.value.notes,
    });
    message.success('Тариф успешно обновлен');
    closeEditModal();
    fetchTariffs();
  } catch (error) {
    if (isApiError(error)) {
      message.error(error.message);
    } else {
      message.error('Ошибка при обновлении тарифа');
    }
  } finally {
    editLoading.value = false;
  }
}

// Delete Modal
function openDeleteModal(tariff: Tariff) {
  deletingTariff.value = tariff;
  deleteModalVisible.value = true;
}

function closeDeleteModal() {
  deleteModalVisible.value = false;
  deletingTariff.value = null;
}

async function handleDelete() {
  if (!deletingTariff.value) return;

  deleteLoading.value = true;
  try {
    await tariffsService.deleteTariff(deletingTariff.value.id);
    message.success('Тариф успешно удален');
    closeDeleteModal();
    fetchTariffs();
  } catch (error) {
    if (isApiError(error)) {
      message.error(error.message);
    } else {
      message.error('Ошибка при удалении тарифа');
    }
  } finally {
    deleteLoading.value = false;
  }
}

// Helpers
function getRateLabel(size: string, status: string): string {
  const sizeLabel = size === '20ft' ? '20фт' : '40фт';
  const statusLabel = status === 'laden' ? 'груж.' : 'пор.';
  return `${sizeLabel} ${statusLabel}`;
}

function formatDate(dateStr: string): string {
  return formatDateLocale(dateStr) || '—';
}

// ============================================================================
// Lifecycle
// ============================================================================

onMounted(() => {
  fetchTariffs();
});
</script>

<template>
  <a-card :bordered="false">
    <a-tabs v-model:activeKey="activeTab">
      <!-- Tariffs Tab -->
      <a-tab-pane key="tariffs">
        <template #tab>
          <span><SettingOutlined /> Тарифы хранения</span>
        </template>

        <div class="tab-header">
          <a-button type="primary" @click="openCreateModal">
            <template #icon><PlusOutlined /></template>
            Создать тариф
          </a-button>
        </div>

        <a-table
      :columns="columns"
      :data-source="tariffs"
      :loading="loading"
      :pagination="pagination"
      :scroll="{ x: 1200 }"
      @change="handleTableChange"
    >
      <!-- Tariff Type -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'type'">
          <a-tag v-if="record.is_general" color="blue">
            Общий тариф
          </a-tag>
          <a-tag v-else color="purple">
            {{ record.company_name }}
          </a-tag>
        </template>

        <!-- Effective To -->
        <template v-else-if="column.key === 'effective_to'">
          <span v-if="record.effective_to">
            {{ formatDate(record.effective_to) }}
          </span>
          <span v-else class="text-gray">—</span>
        </template>

        <!-- Status -->
        <template v-else-if="column.key === 'status'">
          <a-tag v-if="record.is_active" color="success">
            <template #icon><CheckCircleOutlined /></template>
            Активен
          </a-tag>
          <a-tag v-else color="default">
            <template #icon><ClockCircleOutlined /></template>
            Истёк
          </a-tag>
        </template>

        <!-- Rates Summary -->
        <template v-else-if="column.key === 'rates'">
          <div class="rates-summary">
            <template v-for="rate in record.rates" :key="rate.id">
              <a-tooltip>
                <template #title>
                  {{ rate.container_size_display }} {{ rate.container_status_display }}:
                  ${{ rate.daily_rate_usd }}/день, {{ rate.free_days }} дн. бесплатно
                </template>
                <a-tag :color="rate.container_size === '40ft' ? 'orange' : 'cyan'" class="rate-tag">
                  {{ getRateLabel(rate.container_size, rate.container_status) }}:
                  ${{ rate.daily_rate_usd }}
                </a-tag>
              </a-tooltip>
            </template>
          </div>
        </template>

        <!-- Created -->
        <template v-else-if="column.key === 'created'">
          <div>
            <div>{{ formatDate(record.created_at) }}</div>
            <div class="text-small text-gray">{{ record.created_by_name }}</div>
          </div>
        </template>

        <!-- Actions -->
        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-tooltip title="Редактировать">
              <a-button size="small" @click="openEditModal(record)">
                <template #icon><EditOutlined /></template>
              </a-button>
            </a-tooltip>
            <a-tooltip title="Удалить">
              <a-button size="small" danger @click="openDeleteModal(record)">
                <template #icon><DeleteOutlined /></template>
              </a-button>
            </a-tooltip>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- Create Modal -->
    <a-modal
      v-model:open="createModalVisible"
      title="Создать тариф"
      :confirm-loading="createLoading"
      width="700px"
      @ok="handleCreate"
      @cancel="closeCreateModal"
    >
      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Тип тарифа" required>
              <a-radio-group :value="tariffType" @change="(e: { target: { value: 'general' | 'special' } }) => handleTariffTypeChange(e.target.value)">
                <a-radio-button value="general">Общий тариф</a-radio-button>
                <a-radio-button value="special">Для компании</a-radio-button>
              </a-radio-group>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Действует с" required>
              <a-input
                v-model:value="createForm.effective_from"
                type="date"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- Company selector (shown only for special tariff) -->
        <a-form-item v-if="tariffType === 'special'" label="Компания" required>
          <a-select
            v-model:value="createForm.company"
            placeholder="Выберите компанию"
            :loading="companiesLoading"
            show-search
            :filter-option="(input: string, option: { label?: string }) => option?.label?.toLowerCase().includes(input.toLowerCase())"
            style="width: 100%"
          >
            <a-select-option
              v-for="company in companies"
              :key="company.id"
              :value="company.id"
              :label="company.name"
            >
              {{ company.name }}
            </a-select-option>
          </a-select>
          <div class="text-small text-gray" style="margin-top: 4px">
            Этот тариф будет применяться только для контейнеров выбранной компании
          </div>
        </a-form-item>

        <a-form-item label="Примечание">
          <a-textarea
            v-model:value="createForm.notes"
            :rows="2"
            placeholder="Причина создания тарифа"
          />
        </a-form-item>

        <a-divider>Ставки</a-divider>

        <a-table
          :data-source="createForm.rates"
          :pagination="false"
          size="small"
          :row-key="(r: TariffRateInput) => `${r.container_size}-${r.container_status}`"
        >
          <a-table-column title="Размер" data-index="container_size" :width="100">
            <template #default="{ record }">
              {{ record.container_size === '20ft' ? '20 футов' : '40 футов' }}
            </template>
          </a-table-column>
          <a-table-column title="Статус" data-index="container_status" :width="100">
            <template #default="{ record }">
              {{ record.container_status === 'laden' ? 'Груженый' : 'Порожний' }}
            </template>
          </a-table-column>
          <a-table-column title="USD/день" :width="120">
            <template #default="{ record }">
              <a-input-number
                v-model:value="record.daily_rate_usd"
                :min="0"
                :precision="2"
                :step="0.5"
                prefix="$"
                style="width: 100%"
              />
            </template>
          </a-table-column>
          <a-table-column title="UZS/день" :width="150">
            <template #default="{ record }">
              <a-input-number
                v-model:value="record.daily_rate_uzs"
                :min="0"
                :precision="0"
                :step="1000"
                style="width: 100%"
              />
            </template>
          </a-table-column>
          <a-table-column title="Беспл. дни" :width="100">
            <template #default="{ record }">
              <a-input-number
                v-model:value="record.free_days"
                :min="0"
                :max="30"
                :precision="0"
                style="width: 100%"
              />
            </template>
          </a-table-column>
        </a-table>
      </a-form>
    </a-modal>

    <!-- Edit Modal -->
    <a-modal
      v-model:open="editModalVisible"
      title="Редактировать тариф"
      :confirm-loading="editLoading"
      @ok="handleEdit"
      @cancel="closeEditModal"
    >
      <a-form layout="vertical">
        <a-form-item label="Тариф">
          <div>
            <a-tag v-if="editingTariff?.is_general" color="blue">Общий тариф</a-tag>
            <a-tag v-else color="purple">{{ editingTariff?.company_name }}</a-tag>
            <span style="margin-left: 8px">
              с {{ editingTariff ? formatDate(editingTariff.effective_from) : '' }}
            </span>
          </div>
        </a-form-item>

        <a-form-item label="Действует до">
          <a-input
            v-model:value="editForm.effective_to"
            type="date"
            allow-clear
          />
          <div class="text-small text-gray" style="margin-top: 4px">
            Оставьте пустым, если тариф действует бессрочно
          </div>
        </a-form-item>

        <a-form-item label="Примечание">
          <a-textarea
            v-model:value="editForm.notes"
            :rows="3"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Delete Modal -->
    <a-modal
      v-model:open="deleteModalVisible"
      title="Удалить тариф"
      :confirm-loading="deleteLoading"
      ok-text="Удалить"
      ok-type="danger"
      @ok="handleDelete"
      @cancel="closeDeleteModal"
    >
      <p>
        Вы уверены, что хотите удалить тариф
        <template v-if="deletingTariff?.is_general">
          <strong>«Общий»</strong>
        </template>
        <template v-else>
          для компании <strong>«{{ deletingTariff?.company_name }}»</strong>
        </template>
        от {{ deletingTariff ? formatDate(deletingTariff.effective_from) : '' }}?
      </p>
      <p class="text-gray">Это действие нельзя отменить.</p>
    </a-modal>

      </a-tab-pane>

      <!-- Expense Types Tab -->
      <a-tab-pane key="expense-types">
        <template #tab>
          <span><DollarOutlined /> Типы расходов</span>
        </template>

        <ExpenseTypes />
      </a-tab-pane>
    </a-tabs>
  </a-card>
</template>

<style scoped>
.tab-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.rates-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.rate-tag {
  font-size: 11px;
  margin: 0;
}

.text-gray {
  color: #888;
}

.text-small {
  font-size: 12px;
}
</style>
