<template>
  <div class="monthly-statements">
    <!-- Period Selectors -->
    <a-space wrap style="margin-bottom: 16px;">
      <a-select
        v-model:value="selectedYear"
        placeholder="Год"
        style="width: 120px"
        :loading="periodsLoading"
        @change="handlePeriodChange"
      >
        <a-select-option v-for="year in availableYears" :key="year" :value="year">
          {{ year }}
        </a-select-option>
      </a-select>

      <a-select
        v-model:value="selectedMonth"
        placeholder="Месяц"
        style="width: 160px"
        :loading="periodsLoading"
        @change="handlePeriodChange"
      >
        <a-select-option
          v-for="period in filteredMonths"
          :key="`${period.year}-${period.month}`"
          :value="period.month"
        >
          {{ period.label }}
          <a-tag v-if="period.has_statement" color="green" size="small" style="margin-left: 8px;">
            Сформирован
          </a-tag>
        </a-select-option>
      </a-select>

      <a-button
        type="primary"
        :loading="loading"
        :disabled="!selectedYear || !selectedMonth"
        @click="fetchStatement(false)"
      >
        <template #icon><SearchOutlined /></template>
        Показать
      </a-button>

      <a-button
        v-if="statement"
        :loading="regenerating"
        @click="regenerateStatement"
      >
        <template #icon><ReloadOutlined /></template>
        Пересчитать
      </a-button>
    </a-space>

    <!-- Statement Content -->
    <template v-if="statement">
      <!-- Billing Method Badge -->
      <a-alert
        :message="`Метод расчёта: ${statement.billing_method_display}`"
        type="info"
        show-icon
        style="margin-bottom: 16px;"
      >
        <template #icon><InfoCircleOutlined /></template>
      </a-alert>

      <!-- Summary Statistics -->
      <a-row :gutter="[16, 16]" style="margin-bottom: 20px;">
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Всего контейнеров"
            :value="statement.summary.total_containers"
            :value-style="{ color: '#1677ff' }"
          >
            <template #prefix><ContainerOutlined /></template>
          </a-statistic>
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Оплачиваемых дней"
            :value="statement.summary.total_billable_days"
            :value-style="{ color: '#fa8c16' }"
          >
            <template #prefix><CalendarOutlined /></template>
          </a-statistic>
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Итого (USD)"
            :value="formatCurrency(statement.summary.total_usd, 'USD')"
            :value-style="{ color: '#52c41a' }"
          />
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Итого (UZS)"
            :value="formatCurrency(statement.summary.total_uzs, 'UZS')"
            :value-style="{ color: '#722ed1' }"
          />
        </a-col>
      </a-row>

      <a-divider style="margin: 12px 0;" />

      <!-- Export Buttons -->
      <a-space style="margin-bottom: 16px;">
        <a-button type="primary" @click="exportExcel">
          <template #icon><FileExcelOutlined /></template>
          Excel
        </a-button>
        <a-button @click="exportPdf">
          <template #icon><FilePdfOutlined /></template>
          PDF
        </a-button>
      </a-space>

      <!-- Line Items Table -->
      <a-table
        :columns="columns"
        :data-source="statement.line_items"
        :pagination="false"
        row-key="id"
        :scroll="{ x: 1200 }"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'container'">
            <a-tag color="blue">{{ record.container_number }}</a-tag>
            <div style="font-size: 11px; color: #999; margin-top: 2px;">
              {{ record.container_size_display }} / {{ record.container_status_display }}
            </div>
          </template>
          <template v-if="column.key === 'period'">
            <div>{{ formatDate(record.period_start) }}</div>
            <div class="period-end">
              <template v-if="record.is_still_on_terminal">
                <a-tag color="green" size="small">На терминале</a-tag>
              </template>
              <template v-else>
                {{ formatDate(record.period_end) }}
              </template>
            </div>
          </template>
          <template v-if="column.key === 'days'">
            <div class="days-breakdown">
              <a-tag color="blue">{{ record.total_days }} всего</a-tag>
              <a-tag color="green">{{ record.free_days }} льгот.</a-tag>
              <a-tag color="orange">{{ record.billable_days }} опл.</a-tag>
            </div>
          </template>
          <template v-if="column.key === 'rate'">
            <span>${{ parseFloat(record.daily_rate_usd).toFixed(2) }}/день</span>
          </template>
          <template v-if="column.key === 'amount_usd'">
            <span class="amount-usd">${{ parseFloat(record.amount_usd).toFixed(2) }}</span>
          </template>
          <template v-if="column.key === 'amount_uzs'">
            <span class="amount-uzs">{{ formatUzs(record.amount_uzs) }}</span>
          </template>
        </template>
      </a-table>

      <!-- Generation Info -->
      <div style="margin-top: 16px; color: #999; font-size: 12px;">
        Сформировано: {{ formatDateTime(statement.generated_at) }}
      </div>
    </template>

    <!-- Empty State -->
    <a-empty
      v-else-if="!loading && selectedYear && selectedMonth"
      description="Выберите период и нажмите 'Показать'"
    />
    <a-empty
      v-else-if="!loading"
      description="Выберите год и месяц для просмотра выписки"
    />

    <!-- Loading -->
    <a-spin v-if="loading" style="display: block; text-align: center; padding: 40px;" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import type { TableProps } from 'ant-design-vue';
import {
  SearchOutlined,
  ReloadOutlined,
  ContainerOutlined,
  CalendarOutlined,
  InfoCircleOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
} from '@ant-design/icons-vue';
import { http } from '../../utils/httpClient';

interface StatementLineItem {
  id: number;
  container_number: string;
  container_size: string;
  container_size_display: string;
  container_status: string;
  container_status_display: string;
  period_start: string;
  period_end: string;
  is_still_on_terminal: boolean;
  total_days: number;
  free_days: number;
  billable_days: number;
  daily_rate_usd: string;
  daily_rate_uzs: string;
  amount_usd: string;
  amount_uzs: string;
}

interface StatementSummary {
  total_containers: number;
  total_billable_days: number;
  total_usd: string;
  total_uzs: string;
}

interface MonthlyStatement {
  id: number;
  year: number;
  month: number;
  month_name: string;
  billing_method: string;
  billing_method_display: string;
  summary: StatementSummary;
  line_items: StatementLineItem[];
  generated_at: string;
}

interface AvailablePeriod {
  year: number;
  month: number;
  label: string;
  has_statement: boolean;
}

const loading = ref(false);
const regenerating = ref(false);
const periodsLoading = ref(false);
const statement = ref<MonthlyStatement | null>(null);
const availablePeriods = ref<AvailablePeriod[]>([]);
const selectedYear = ref<number | null>(null);
const selectedMonth = ref<number | null>(null);

const availableYears = computed(() => {
  const years = new Set(availablePeriods.value.map(p => p.year));
  return Array.from(years).sort((a, b) => b - a);
});

const filteredMonths = computed(() => {
  if (!selectedYear.value) return availablePeriods.value;
  return availablePeriods.value.filter(p => p.year === selectedYear.value);
});

const columns: TableProps['columns'] = [
  { title: 'Контейнер', key: 'container', width: 150, fixed: 'left' },
  { title: 'Период', key: 'period', width: 140 },
  { title: 'Дни', key: 'days', width: 200 },
  { title: 'Ставка', key: 'rate', width: 100, align: 'right' },
  { title: 'Сумма USD', key: 'amount_usd', width: 120, align: 'right' },
  { title: 'Сумма UZS', key: 'amount_uzs', width: 150, align: 'right' },
];

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('ru-RU');
};

const formatDateTime = (dateStr: string): string => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('ru-RU');
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

const fetchAvailablePeriods = async () => {
  periodsLoading.value = true;
  try {
    const result = await http.get<{ success: boolean; data: AvailablePeriod[] }>(
      '/customer/billing/available-periods/'
    );
    availablePeriods.value = result.data || [];

    // Auto-select most recent period
    const first = availablePeriods.value[0];
    if (first) {
      selectedYear.value = first.year;
      selectedMonth.value = first.month;
    }
  } catch (error) {
    console.error('Error fetching periods:', error);
    message.error('Не удалось загрузить доступные периоды');
  } finally {
    periodsLoading.value = false;
  }
};

const handlePeriodChange = () => {
  statement.value = null;
};

const fetchStatement = async (regenerate = false) => {
  if (!selectedYear.value || !selectedMonth.value) return;

  loading.value = true;
  if (regenerate) regenerating.value = true;

  try {
    const url = `/customer/billing/statements/${selectedYear.value}/${selectedMonth.value}/${regenerate ? '?regenerate=true' : ''}`;
    const result = await http.get<{ success: boolean; data: MonthlyStatement }>(url);
    statement.value = result.data;

    if (regenerate) {
      message.success('Выписка пересчитана');
    }

    // Update available periods to show has_statement
    await fetchAvailablePeriods();
  } catch (error) {
    console.error('Error fetching statement:', error);
    message.error('Не удалось загрузить выписку');
  } finally {
    loading.value = false;
    regenerating.value = false;
  }
};

const regenerateStatement = () => fetchStatement(true);

const exportExcel = () => {
  if (!selectedYear.value || !selectedMonth.value) return;
  window.open(
    `/api/customer/billing/statements/${selectedYear.value}/${selectedMonth.value}/export/excel/`,
    '_blank'
  );
  message.success('Загрузка Excel начата');
};

const exportPdf = () => {
  if (!selectedYear.value || !selectedMonth.value) return;
  window.open(
    `/api/customer/billing/statements/${selectedYear.value}/${selectedMonth.value}/export/pdf/`,
    '_blank'
  );
  message.success('Загрузка PDF начата');
};

onMounted(() => {
  fetchAvailablePeriods();
});
</script>

<style scoped>
.monthly-statements {
  padding: 8px 0;
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
