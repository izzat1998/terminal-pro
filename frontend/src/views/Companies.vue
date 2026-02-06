<template>
  <div class="companies-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-row">
        <h2 class="page-title">Компании</h2>
        <a-button type="primary" @click="showCreateModal">
          <template #icon><PlusOutlined /></template>
          Создать компанию
        </a-button>
      </div>

      <!-- Filters -->
      <div class="filters-row">
        <a-input-search
          v-model:value="searchText"
          placeholder="Поиск по названию..."
          style="width: 260px"
          allow-clear
          @search="handleSearch"
          @input="handleSearchChange"
        />
        <a-select
          v-model:value="statusFilter"
          placeholder="Статус"
          style="width: 150px"
          allow-clear
          @change="handleFilterChange"
        >
          <a-select-option value="true">Активные</a-select-option>
          <a-select-option value="false">Неактивные</a-select-option>
        </a-select>
      </div>

      <!-- Stats Bar -->
      <div v-if="stats" class="stats-summary">
        <span>Всего: <strong>{{ stats.total }}</strong></span>
        <span class="stats-dot">&middot;</span>
        <span>Активных: <strong class="stats-active">{{ stats.active }}</strong></span>
        <span class="stats-dot">&middot;</span>
        <span>Неактивных: <strong class="stats-inactive">{{ stats.inactive }}</strong></span>
      </div>
    </div>

    <!-- Table -->
    <a-table
      :columns="columns"
      :data-source="dataSource"
      :pagination="pagination"
      :loading="loading"
      :row-class-name="() => 'clickable-row'"
      :custom-row="customRow"
      @change="handleTableChange"
      bordered
      :scroll="{ x: 900 }"
      :locale="{ emptyText: 'Нет компаний. Создайте первую компанию.' }"
    >
      <template #bodyCell="{ column, index, record }">
        <template v-if="column.key === 'number'">
          {{ (pagination.current - 1) * pagination.pageSize + index + 1 }}
        </template>
        <template v-else-if="column.key === 'name'">
          <span class="company-name-cell">{{ record.name }}</span>
        </template>
        <template v-else-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? 'Активна' : 'Неактивна' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'balance'">
          <span :class="{ 'balance-negative': Number(record.balance_usd) > 0 }">
            {{ Number(record.balance_usd) > 0 ? `-$${formatMoney(record.balance_usd)}` : '$0' }}
          </span>
          <a-tooltip v-if="Number(record.balance_uzs) > 0" :title="`${formatMoney(record.balance_uzs)} сум`">
            <span class="balance-uzs-hint">UZS</span>
          </a-tooltip>
        </template>
      </template>
    </a-table>

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
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import { formatDateTime } from '../utils/dateFormat';
import { http } from '../utils/httpClient';
import { useCrudTable } from '../composables/useCrudTable';
import type { Company } from '../types/company';

interface CompanyRecord {
  key: string;
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  customers_count: number;
  entries_count: number;
  balance_usd: string;
  balance_uzs: string;
  created: string;
}

interface CompanyStats {
  total: number;
  active: number;
  inactive: number;
}

const router = useRouter();

const columns = [
  {
    title: '№',
    key: 'number',
    align: 'center' as const,
    width: 60,
    fixed: 'left' as const,
  },
  {
    title: 'Компания',
    dataIndex: 'name',
    key: 'name',
    width: 220,
  },
  {
    title: 'Статус',
    key: 'is_active',
    align: 'center' as const,
    width: 110,
  },
  {
    title: 'Клиенты',
    dataIndex: 'customers_count',
    key: 'customers_count',
    align: 'center' as const,
    width: 90,
  },
  {
    title: 'Контейнеры',
    dataIndex: 'entries_count',
    key: 'entries_count',
    align: 'center' as const,
    width: 100,
  },
  {
    title: 'Баланс',
    key: 'balance',
    align: 'right' as const,
    width: 140,
  },
  {
    title: 'Создана',
    dataIndex: 'created',
    key: 'created',
    align: 'center' as const,
    width: 130,
  },
];

const formatMoney = (value: string): string => {
  const num = Number(value);
  if (isNaN(num) || num === 0) return '0';
  return num.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
};

// Table data
const { dataSource, loading, pagination, searchText, fetchData, handleTableChange, handleSearch, refresh } = useCrudTable<Company, CompanyRecord>(
  '/auth/companies/',
  (company) => ({
    key: company.id.toString(),
    id: company.id,
    name: company.name,
    slug: company.slug,
    is_active: company.is_active,
    customers_count: company.customers_count,
    entries_count: company.entries_count,
    balance_usd: company.balance_usd,
    balance_uzs: company.balance_uzs,
    created: formatDateTime(company.created_at),
  }),
  { searchEnabled: true },
);

// Stats
const stats = ref<CompanyStats | null>(null);

const fetchStats = async () => {
  try {
    const result = await http.get<{ data: CompanyStats }>('/auth/companies/stats/');
    stats.value = result.data;
  } catch {
    // Stats are non-critical, fail silently
  }
};

// Filter
const statusFilter = ref<string | undefined>(undefined);
let searchTimeout: ReturnType<typeof setTimeout> | null = null;

const handleSearchChange = () => {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    handleSearch();
  }, 400);
};

const handleFilterChange = () => {
  // Status filter not supported by useCrudTable natively,
  // so we refetch and let the backend handle it via URL
  handleSearch();
};

// Row click → navigate to company detail
const customRow = (record: CompanyRecord) => ({
  onClick: () => {
    router.push(`/accounts/companies/${record.slug}`);
  },
});

// Create modal
const createModalVisible = ref(false);
const createLoading = ref(false);
const createForm = reactive({ name: '' });

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
    await http.post('/auth/companies/', { name: createForm.name });
    message.success('Компания успешно создана');
    createModalVisible.value = false;
    refresh();
    fetchStats();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка создания компании');
  } finally {
    createLoading.value = false;
  }
};

onMounted(() => {
  fetchData();
  fetchStats();
});
</script>

<style scoped>
.companies-page {
  min-height: 100%;
}

.page-header {
  background: #fff;
  border-radius: 6px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.filters-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.stats-summary {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.stats-dot {
  margin: 0 8px;
  color: #d9d9d9;
}

.stats-active {
  color: #52c41a;
}

.stats-inactive {
  color: #ff4d4f;
}

.company-name-cell {
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
}

.balance-negative {
  color: #cf1322;
  font-weight: 600;
}

.balance-uzs-hint {
  font-size: 11px;
  color: #1890ff;
  margin-left: 6px;
  cursor: help;
  border-bottom: 1px dotted #1890ff;
}

:deep(.clickable-row) {
  cursor: pointer;
}

:deep(.clickable-row:hover td) {
  background: #e6f7ff !important;
}
</style>
