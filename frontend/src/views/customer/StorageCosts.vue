<template>
  <a-card :bordered="false" class="content-card">
    <template #title>
      <div class="card-title">
        <DollarOutlined style="color: #52c41a; margin-right: 8px;" />
        Стоимость хранения
      </div>
    </template>

    <template #extra>
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
    </template>

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
        placeholder="Период завоза"
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
      :scroll="{ x: 1200 }"
      size="small"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'container'">
          <a-tag color="blue">{{ record.container_number }}</a-tag>
          <div style="font-size: 11px; color: #999; margin-top: 2px;">
            {{ record.container_size }} / {{ record.container_status }}
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

    <!-- Storage Cost Detail Modal -->
    <StorageCostModal
      v-model:open="detailModalVisible"
      :entry-id="selectedEntryId"
      :container-number="selectedContainerNumber"
    />
  </a-card>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';
import { message } from 'ant-design-vue';
import type { TableProps } from 'ant-design-vue';
import type { Dayjs } from 'dayjs';
import {
  DollarOutlined,
  DownloadOutlined,
  ContainerOutlined,
  CalendarOutlined,
  EyeOutlined,
} from '@ant-design/icons-vue';
import { http } from '../../utils/httpClient';
import type { PaginatedResponse } from '../../types/api';
import StorageCostModal from '../../components/StorageCostModal.vue';

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
}

interface CostSummary {
  total_containers: number;
  total_billable_days: number;
  total_usd: string;
  total_uzs: string;
}

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

defineProps<{
  company: Company | null;
  loading: boolean;
}>();

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
  const date = new Date(dateStr);
  return date.toLocaleDateString('ru-RU');
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

    const url = `/customer/storage-costs/?${params.toString()}`;
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
    window.open(`/api/customer/storage-costs/export/${query ? '?' + query : ''}`, '_blank');
    message.success('Экспорт начат');
  } catch (error) {
    message.error('Ошибка при экспорте');
  } finally {
    exportLoading.value = false;
  }
};

// Initial fetch
fetchStorageCosts();
</script>

<style scoped>
.content-card {
  border-radius: 2px;
}

.card-title {
  display: flex;
  align-items: center;
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
  color: #52c41a;
}

.amount-uzs {
  font-weight: 500;
  color: #722ed1;
}
</style>
