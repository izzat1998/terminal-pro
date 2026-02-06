<template>
  <div class="current-costs">
    <!-- Header with search and export -->
    <div class="header-actions">
      <a-space>
        <a-input-search
          v-model:value="searchText"
          placeholder="Поиск по номеру контейнера"
          style="width: 250px"
          allow-clear
        />
        <a-button type="primary" :loading="exportLoading" @click="exportToExcel">
          <template #icon><DownloadOutlined /></template>
          Экспорт
        </a-button>
      </a-space>
    </div>

    <!-- Summary Statistics -->
    <a-row :gutter="[16, 16]" style="margin-bottom: 20px;">
      <a-col :xs="12" :sm="6">
        <a-statistic
          title="Всего контейнеров"
          :value="summary.total_containers"
          :value-style="{ color: '#1677ff' }"
        >
          <template #prefix><ContainerOutlined /></template>
        </a-statistic>
      </a-col>
      <a-col :xs="12" :sm="6">
        <a-statistic
          title="Оплачиваемых дней"
          :value="summary.total_billable_days"
          :value-style="{ color: '#fa8c16' }"
        >
          <template #prefix><CalendarOutlined /></template>
        </a-statistic>
      </a-col>
      <a-col :xs="12" :sm="6">
        <a-statistic
          title="Итого (USD)"
          :value="formatCurrency(summary.total_usd, 'USD')"
          :value-style="{ color: '#52c41a' }"
        />
      </a-col>
      <a-col :xs="12" :sm="6">
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
      <a-select
        v-model:value="statusFilter"
        placeholder="Статус"
        style="width: 140px"
        allow-clear
        @change="fetchStorageCosts"
      >
        <a-select-option value="active">На терминале</a-select-option>
        <a-select-option value="exited">Выехавшие</a-select-option>
        <a-select-option value="all">Все</a-select-option>
      </a-select>

      <a-range-picker
        v-model:value="dateRange"
        format="DD.MM.YYYY"
        :placeholder="['Дата от', 'Дата до']"
        style="width: 240px"
        @change="fetchStorageCosts"
        allow-clear
      />
    </a-space>

    <a-empty v-if="!loading && costs.length === 0" description="Данные о хранении не найдены" />

    <a-table
      v-else
      :columns="columns"
      :data-source="costs"
      :loading="loading"
      :pagination="{
        current: pagination.current,
        pageSize: pagination.pageSize,
        total: pagination.total,
        showSizeChanger: true,
        showTotal: (total: number) => `Всего: ${total}`,
        pageSizeOptions: ['10', '20', '50', '100'],
      }"
      row-key="container_entry_id"
      :row-selection="rowSelection"
      :scroll="{ x: 1200 }"
      size="small"
      :custom-row="(record: StorageCostItem) => ({
        onDblclick: () => handleRowDoubleClick(record),
        style: isAdmin ? 'cursor: pointer;' : '',
      })"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'container'">
          <a-tag color="blue">{{ record.container_number }}</a-tag>
          <div style="font-size: 11px; color: #999; margin-top: 2px;">
            {{ record.container_size }} / {{ record.container_status }}
            <a-tag v-if="record.is_on_demand_invoiced" color="orange" size="small" style="margin-left: 4px;">
              Счёт
            </a-tag>
          </div>
        </template>
        <template v-if="column.key === 'period'">
          <div>{{ formatDate(record.entry_date) }}</div>
          <div class="period-end">
            <template v-if="record.is_active">
              <a-tag color="green" size="small">На терминале</a-tag>
            </template>
            <template v-else>
              {{ formatDate(record.end_date) }}
            </template>
          </div>
        </template>
        <template v-if="column.key === 'days'">
          <div class="days-breakdown">
            <a-tag color="blue">{{ record.total_days }} всего</a-tag>
            <a-tag color="green">{{ record.free_days_applied }} льгот.</a-tag>
            <a-tag color="orange">{{ record.billable_days }} опл.</a-tag>
          </div>
        </template>
        <template v-if="column.key === 'total_usd'">
          <span class="amount-usd">${{ parseFloat(record.total_usd).toFixed(2) }}</span>
        </template>
        <template v-if="column.key === 'total_uzs'">
          <span class="amount-uzs">{{ formatUzs(record.total_uzs) }}</span>
        </template>
        <template v-if="column.key === 'actions'">
          <a-tooltip title="Подробности расчёта">
            <a-button type="link" size="small" @click="showCostDetails(record)">
              <template #icon><EyeOutlined /></template>
            </a-button>
          </a-tooltip>
        </template>
      </template>
    </a-table>

    <!-- Selection Summary Bar (admin only) -->
    <transition name="slide-up">
      <div v-if="isAdmin && selectionSummary.count > 0" class="selection-bar">
        <div class="selection-info">
          <FileTextOutlined style="font-size: 18px; margin-right: 8px;" />
          <span>
            Выбрано: <strong>{{ selectionSummary.count }}</strong> конт.
            &nbsp;·&nbsp;
            <span class="amount-usd">${{ selectionSummary.totalUsd.toLocaleString('ru-RU', { minimumFractionDigits: 2 }) }}</span>
            &nbsp;·&nbsp;
            <span class="amount-uzs">{{ selectionSummary.totalUzs.toLocaleString('ru-RU', { minimumFractionDigits: 0 }) }} сум</span>
          </span>
        </div>
        <a-space>
          <a-button @click="selectedRowKeys = []" size="small">Сбросить</a-button>
          <a-button
            type="primary"
            @click="invoiceModalVisible = true"
            size="small"
          >
            <template #icon><FileTextOutlined /></template>
            Создать разовый счёт
          </a-button>
        </a-space>
      </div>
    </transition>

    <!-- Invoice Preview Modal -->
    <a-modal
      v-model:open="invoiceModalVisible"
      title="Создание разового счёта"
      width="850px"
      :ok-text="'Создать счёт'"
      :ok-button-props="{ loading: creatingInvoice }"
      cancel-text="Отмена"
      @ok="createOnDemandInvoice"
    >
      <!-- Grand Total -->
      <a-row :gutter="16" style="margin-bottom: 16px;">
        <a-col :span="8">
          <a-statistic title="Контейнеров" :value="selectionSummary.count" :value-style="{ color: '#1677ff' }" />
        </a-col>
        <a-col :span="8">
          <a-statistic title="Итого USD" :value-style="{ color: '#52c41a', fontSize: '20px' }">
            <template #formatter>
              ${{ grandTotal.usd.toLocaleString('ru-RU', { minimumFractionDigits: 2 }) }}
            </template>
          </a-statistic>
        </a-col>
        <a-col :span="8">
          <a-statistic title="Итого UZS" :value-style="{ color: '#722ed1', fontSize: '20px' }">
            <template #formatter>
              {{ grandTotal.uzs.toLocaleString('ru-RU', { minimumFractionDigits: 0 }) }} сум
            </template>
          </a-statistic>
        </a-col>
      </a-row>

      <a-divider style="margin: 12px 0;" />

      <!-- Active containers warning -->
      <a-alert
        v-if="selectionSummary.activeCount > 0"
        type="warning"
        show-icon
        style="margin-bottom: 12px;"
        :message="`${selectionSummary.activeCount} конт. ещё на терминале — расчёт по сегодняшний день`"
        description="После выставления счёта эти контейнеры должны покинуть терминал. Дальнейшее хранение не будет включено в ежемесячную выписку."
      />

      <!-- Storage costs -->
      <h4 style="margin: 0 0 8px;">Хранение</h4>
      <a-table
        :columns="invoicePreviewColumns"
        :data-source="selectedItems"
        :pagination="false"
        row-key="container_entry_id"
        size="small"
        :scroll="{ y: 240 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'container'">
            <a-tag color="blue">{{ record.container_number }}</a-tag>
            <span style="font-size: 11px; color: #999; margin-left: 4px;">
              {{ record.container_size }} / {{ record.container_status }}
            </span>
          </template>
          <template v-if="column.key === 'period'">
            {{ formatDate(record.entry_date) }} →
            <template v-if="record.is_active">
              <a-tag color="green" size="small">сегодня</a-tag>
            </template>
            <template v-else>
              {{ formatDate(record.end_date) }}
            </template>
          </template>
          <template v-if="column.key === 'days'">
            <span>{{ record.billable_days }} опл.</span>
            <span style="color: #999; margin-left: 4px;">({{ record.free_days_applied }} льгот.)</span>
          </template>
          <template v-if="column.key === 'amount_usd'">
            <span class="amount-usd">${{ parseFloat(record.total_usd).toFixed(2) }}</span>
          </template>
          <template v-if="column.key === 'amount_uzs'">
            <span class="amount-uzs">{{ formatUzs(record.total_uzs) }}</span>
          </template>
        </template>
      </a-table>

      <!-- Additional charges -->
      <template v-if="modalCharges.length > 0">
        <h4 style="margin: 16px 0 8px;">Дополнительные начисления</h4>
        <a-table
          :columns="chargesPreviewColumns"
          :data-source="modalCharges"
          :pagination="false"
          row-key="id"
          size="small"
          :scroll="{ y: 200 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'container'">
              <a-tag color="blue">{{ record.container_number }}</a-tag>
            </template>
            <template v-if="column.key === 'date'">
              {{ formatDate(record.charge_date) }}
            </template>
            <template v-if="column.key === 'amount_usd'">
              <span class="amount-usd">${{ parseFloat(record.amount_usd).toFixed(2) }}</span>
            </template>
            <template v-if="column.key === 'amount_uzs'">
              <span class="amount-uzs">{{ formatUzs(record.amount_uzs) }}</span>
            </template>
          </template>
        </a-table>
      </template>
      <a-spin v-else-if="chargesLoading" size="small" style="display: block; text-align: center; margin: 16px 0;" />

      <!-- Notes -->
      <div style="margin-top: 16px;">
        <label style="font-weight: 500; display: block; margin-bottom: 4px;">Примечание</label>
        <a-textarea
          v-model:value="invoiceNotes"
          placeholder="Причина выставления разового счёта (необязательно)"
          :rows="2"
          :maxlength="500"
          show-count
        />
      </div>
    </a-modal>

    <!-- Storage Cost Detail Modal -->
    <StorageCostModal
      v-model:open="detailModalVisible"
      :entry-id="selectedEntryId"
      :container-number="selectedContainerNumber"
    />

    <!-- Additional Charges Section -->
    <a-divider style="margin: 24px 0;">Дополнительные начисления</a-divider>

    <AdditionalCharges
      ref="additionalChargesRef"
      :company-slug="companySlug"
      :is-admin="isAdmin"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue';
import { message } from 'ant-design-vue';
import type { TableProps } from 'ant-design-vue';
import type { Dayjs } from 'dayjs';
import {
  DownloadOutlined,
  ContainerOutlined,
  CalendarOutlined,
  EyeOutlined,
  FileTextOutlined,
} from '@ant-design/icons-vue';
import { useRouter } from 'vue-router';
import { http, downloadFile } from '../../utils/httpClient';
import type { PaginatedResponse } from '../../types/api';
import { formatDateLocale } from '../../utils/dateFormat';
import StorageCostModal from '../StorageCostModal.vue';
import AdditionalCharges from './AdditionalCharges.vue';

defineOptions({ inheritAttrs: false });

// Props for admin mode (viewing company billing)
interface Props {
  companySlug?: string;
}

const props = defineProps<Props>();

// Admin mode detection and ref
const isAdmin = computed(() => !!props.companySlug);
const additionalChargesRef = ref<InstanceType<typeof AdditionalCharges>>();
const router = useRouter();

// Compute base URL based on whether we're in admin or customer mode
const baseUrl = computed(() => {
  if (props.companySlug) {
    return `/auth/companies/${props.companySlug}/storage-costs`;
  }
  return '/customer/storage-costs';
});

// --- Selection for on-demand invoicing (admin only) ---
const selectedRowKeys = ref<number[]>([]);
const creatingInvoice = ref(false);
const invoiceNotes = ref('');
const invoiceModalVisible = ref(false);
const chargesLoading = ref(false);

interface ChargeItem {
  id: number;
  container_number: string;
  description: string;
  charge_date: string;
  amount_usd: string;
  amount_uzs: string;
}

const modalCharges = ref<ChargeItem[]>([]);

const selectedItems = computed(() =>
  costs.value.filter(c => selectedRowKeys.value.includes(c.container_entry_id))
);

const selectionSummary = computed(() => {
  const items = selectedItems.value;
  const totalUsd = items.reduce((sum, i) => sum + parseFloat(i.total_usd || '0'), 0);
  const totalUzs = items.reduce((sum, i) => sum + parseFloat(i.total_uzs || '0'), 0);
  const activeCount = items.filter(i => i.is_active).length;
  return { count: items.length, totalUsd, totalUzs, activeCount };
});

const chargesTotals = computed(() => {
  const usd = modalCharges.value.reduce((sum, c) => sum + parseFloat(c.amount_usd || '0'), 0);
  const uzs = modalCharges.value.reduce((sum, c) => sum + parseFloat(c.amount_uzs || '0'), 0);
  return { usd, uzs };
});

const grandTotal = computed(() => ({
  usd: selectionSummary.value.totalUsd + chargesTotals.value.usd,
  uzs: selectionSummary.value.totalUzs + chargesTotals.value.uzs,
}));

// Row selection config: block already-invoiced containers only
const rowSelection = computed(() => {
  if (!isAdmin.value) return undefined;
  return {
    selectedRowKeys: selectedRowKeys.value,
    onChange: (keys: number[]) => { selectedRowKeys.value = keys; },
    getCheckboxProps: (record: StorageCostItem) => ({
      disabled: record.is_on_demand_invoiced === true,
    }),
  };
});

const createOnDemandInvoice = async () => {
  if (selectedRowKeys.value.length === 0) return;
  creatingInvoice.value = true;
  try {
    await http.post(`/auth/companies/${props.companySlug}/on-demand-invoices/`, {
      container_entry_ids: selectedRowKeys.value,
      notes: invoiceNotes.value,
    });
    message.success('Разовый счёт создан');
    invoiceModalVisible.value = false;
    selectedRowKeys.value = [];
    invoiceNotes.value = '';
    router.replace({ query: { tab: 'on-demand' } });
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Не удалось создать счёт');
  } finally {
    creatingInvoice.value = false;
  }
};

// Fetch additional charges when modal opens
watch(invoiceModalVisible, async (visible) => {
  if (!visible || selectedRowKeys.value.length === 0) {
    modalCharges.value = [];
    return;
  }
  chargesLoading.value = true;
  try {
    const entryIds = selectedRowKeys.value.join(',');
    const result = await http.get<{ success: boolean; data: ChargeItem[] }>(
      `/billing/additional-charges/?container_entry_ids=${entryIds}`
    );
    modalCharges.value = result.data || [];
  } catch {
    modalCharges.value = [];
  } finally {
    chargesLoading.value = false;
  }
});

const invoicePreviewColumns: TableProps['columns'] = [
  { title: 'Контейнер', key: 'container', width: 180 },
  { title: 'Период', key: 'period', width: 180 },
  { title: 'Дни', key: 'days', width: 120 },
  { title: 'USD', key: 'amount_usd', width: 100, align: 'right' },
  { title: 'UZS', key: 'amount_uzs', width: 130, align: 'right' },
];

const chargesPreviewColumns: TableProps['columns'] = [
  { title: 'Контейнер', key: 'container', width: 150 },
  { title: 'Описание', dataIndex: 'description', width: 200 },
  { title: 'Дата', key: 'date', width: 100 },
  { title: 'USD', key: 'amount_usd', width: 100, align: 'right' },
  { title: 'UZS', key: 'amount_uzs', width: 130, align: 'right' },
];

interface StorageCostItem {
  container_entry_id: number;
  container_number: string;
  company_name: string | null;
  container_size: string;
  container_status: string;
  entry_date: string;
  end_date: string;
  is_active: boolean;
  total_days: number;
  free_days_applied: number;
  billable_days: number;
  total_usd: string;
  total_uzs: string;
  calculated_at: string;
  is_on_demand_invoiced?: boolean;
}

interface CostSummary {
  total_containers: number;
  total_billable_days: number;
  total_usd: string;
  total_uzs: string;
}

const costs = ref<StorageCostItem[]>([]);
const loading = ref(false);
const searchText = ref('');
const statusFilter = ref<string>('active');
const dateRange = ref<[Dayjs, Dayjs] | null>(null);
const exportLoading = ref(false);

const summary = ref<CostSummary>({
  total_containers: 0,
  total_billable_days: 0,
  total_usd: '0.00',
  total_uzs: '0',
});

// Detail modal state
const detailModalVisible = ref(false);
const selectedEntryId = ref<number | null>(null);
const selectedContainerNumber = ref('');

// Server-side pagination
const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0,
});

// Debounce for search
let searchTimeout: ReturnType<typeof setTimeout> | null = null;

const debouncedFetch = () => {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    pagination.value.current = 1;
    fetchStorageCosts();
  }, 400);
};

onUnmounted(() => {
  if (searchTimeout) clearTimeout(searchTimeout);
});

watch(searchText, debouncedFetch);

const columns: TableProps['columns'] = [
  {
    title: 'Контейнер',
    key: 'container',
    width: 150,
    fixed: 'left',
  },
  {
    title: 'Период хранения',
    key: 'period',
    width: 140,
  },
  {
    title: 'Дни',
    key: 'days',
    width: 200,
  },
  {
    title: 'Сумма USD',
    key: 'total_usd',
    width: 120,
    align: 'right',
    sorter: true,
  },
  {
    title: 'Сумма UZS',
    key: 'total_uzs',
    width: 150,
    align: 'right',
    sorter: true,
  },
  {
    title: '',
    key: 'actions',
    width: 60,
    align: 'center',
    fixed: 'right',
  },
];

const handleTableChange: TableProps['onChange'] = (pag, _filters, sorter) => {
  pagination.value.current = pag.current || 1;
  pagination.value.pageSize = pag.pageSize || 20;

  // Handle sorting (if implemented on backend)
  if (!Array.isArray(sorter) && sorter.field) {
    // Sorting would be handled here if backend supports it
  }

  fetchStorageCosts();
};

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '—';
  return formatDateLocale(dateStr) || '—';
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

const showCostDetails = (record: StorageCostItem) => {
  selectedEntryId.value = record.container_entry_id;
  selectedContainerNumber.value = record.container_number;
  detailModalVisible.value = true;
};

const handleRowDoubleClick = (record: StorageCostItem) => {
  if (isAdmin.value && additionalChargesRef.value) {
    additionalChargesRef.value.openAddModalForContainer(
      record.container_entry_id,
      record.container_number
    );
  }
};

const fetchStorageCosts = async () => {
  loading.value = true;
  try {
    const params = new URLSearchParams();

    params.append('page', pagination.value.current.toString());
    params.append('page_size', pagination.value.pageSize.toString());

    if (searchText.value.trim()) {
      params.append('search', searchText.value.trim());
    }

    if (statusFilter.value && statusFilter.value !== 'all') {
      params.append('status', statusFilter.value);
    }

    if (dateRange.value && dateRange.value[0] && dateRange.value[1]) {
      params.append('entry_date_from', dateRange.value[0].format('YYYY-MM-DD'));
      params.append('entry_date_to', dateRange.value[1].format('YYYY-MM-DD'));
    }

    const url = `${baseUrl.value}/?${params.toString()}`;
    const result = await http.get<PaginatedResponse<StorageCostItem> & { summary: CostSummary }>(url);

    costs.value = result.results || [];
    pagination.value.total = result.count;

    if (result.summary) {
      summary.value = result.summary;
    }
  } catch (error) {
    console.error('Error fetching storage costs:', error);
    message.error(error instanceof Error ? error.message : 'Не удалось загрузить данные о хранении');
  } finally {
    loading.value = false;
  }
};

const exportToExcel = async () => {
  exportLoading.value = true;
  try {
    const params = new URLSearchParams();

    if (statusFilter.value && statusFilter.value !== 'all') {
      params.append('status', statusFilter.value);
    }

    if (dateRange.value && dateRange.value[0] && dateRange.value[1]) {
      params.append('entry_date_from', dateRange.value[0].format('YYYY-MM-DD'));
      params.append('entry_date_to', dateRange.value[1].format('YYYY-MM-DD'));
    }

    const query = params.toString();
    const exportEndpoint = props.companySlug
      ? `/auth/companies/${props.companySlug}/storage-costs/export/`
      : '/customer/storage-costs/export/';
    await downloadFile(
      `${exportEndpoint}${query ? '?' + query : ''}`,
      'storage-costs-export.xlsx'
    );
    message.success('Экспорт завершён');
  } catch (error) {
    message.error('Ошибка при экспорте');
  } finally {
    exportLoading.value = false;
  }
};

// Initial fetch
onMounted(() => {
  fetchStorageCosts();
});
</script>

<style scoped>
.current-costs {
  padding: 8px 0;
}

.header-actions {
  margin-bottom: 16px;
}

.period-end {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}

.days-breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.amount-usd {
  font-weight: 600;
  color: var(--ant-color-success, #52c41a);
}

.amount-uzs {
  font-weight: 500;
  color: #722ed1;
}

.selection-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  margin-top: 12px;
  background: #e6f4ff;
  border: 1px solid #91caff;
  border-radius: 6px;
}

.selection-info {
  display: flex;
  align-items: center;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.2s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
