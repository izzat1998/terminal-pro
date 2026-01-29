<template>
  <div class="monthly-statements">
    <!-- Header: Year filter + Generate button -->
    <a-space wrap :size="12" style="margin-bottom: 16px;" class="statements-header">
      <a-select
        v-model:value="selectedYear"
        placeholder="Год"
        style="width: 120px"
        @change="fetchStatements"
      >
        <a-select-option v-for="year in availableYears" :key="year" :value="year">
          {{ year }}
        </a-select-option>
      </a-select>

      <template v-if="isAdmin">
        <a-select
          v-model:value="selectedMonth"
          placeholder="Месяц"
          style="width: 160px"
          allow-clear
        >
          <a-select-option v-for="m in 12" :key="m" :value="m">
            {{ monthNames[m - 1] }}
          </a-select-option>
        </a-select>

        <a-button
          type="primary"
          :disabled="!selectedYear || !selectedMonth"
          :loading="generating"
          @click="generateStatement"
        >
          <template #icon><PlusOutlined /></template>
          Сформировать
        </a-button>
      </template>
    </a-space>

    <!-- Master Table -->
    <a-table
      :columns="masterColumns"
      :data-source="statements"
      :loading="loading"
      :pagination="false"
      row-key="id"
      v-model:expandedRowKeys="expandedRowKeys"
      size="middle"
      class="statements-table"
      @expand="handleExpand"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'period'">
          <div class="period-cell">
            <span class="period-label">{{ record.month_name }} {{ record.year }}</span>
            <a-tag v-if="record.statement_type === 'credit_note'" color="orange" style="margin-left: 6px;">
              Корректировка
            </a-tag>
          </div>
        </template>

        <template v-if="column.key === 'invoice_number'">
          <span v-if="record.invoice_number" class="invoice-number">{{ record.invoice_number }}</span>
          <span v-else class="draft-label">—</span>
        </template>

        <template v-if="column.key === 'containers'">
          {{ record.summary.total_containers }}
        </template>

        <template v-if="column.key === 'total_usd'">
          <span class="amount-usd">${{ formatNumber(record.summary.total_usd) }}</span>
        </template>

        <template v-if="column.key === 'total_uzs'">
          <span class="amount-uzs">{{ formatNumber(record.summary.total_uzs, 0) }} сум</span>
        </template>

        <template v-if="column.key === 'status'">
          <template v-if="isAdmin && (record.status === 'finalized' || record.status === 'paid')">
            <a-tag
              :color="statusColor(record.status)"
              style="cursor: pointer;"
              @click.stop="togglePaymentStatus(record)"
            >
              {{ statusLabel(record.status) }}
            </a-tag>
          </template>
          <a-tag v-else :color="statusColor(record.status)">
            {{ statusLabel(record.status) }}
          </a-tag>
        </template>
      </template>

      <!-- Expanded Row: Detail view -->
      <template #expandedRowRender="{ record }">
        <div class="expanded-detail">
          <a-spin v-if="detailLoading[record.id]" style="display: block; text-align: center; padding: 20px;" />

          <template v-else-if="statementDetails[record.id]">
            <!-- Billing Method -->
            <a-alert
              :message="`Метод расчёта: ${statementDetails[record.id].billing_method_display}`"
              type="info"
              show-icon
              style="margin-bottom: 12px;"
            >
              <template #icon><InfoCircleOutlined /></template>
            </a-alert>

            <!-- Action Buttons -->
            <a-space style="margin-bottom: 12px;" wrap>
              <a-button type="primary" size="small" @click="exportExcel(record)">
                <template #icon><FileExcelOutlined /></template>
                Excel
              </a-button>
              <a-button size="small" @click="exportPdf(record)">
                <template #icon><FilePdfOutlined /></template>
                PDF
              </a-button>

              <template v-if="isAdmin">
                <!-- Draft actions -->
                <template v-if="record.status === 'draft'">
                  <a-button size="small" :loading="regeneratingId === record.id" @click="regenerateStatement(record)">
                    <template #icon><ReloadOutlined /></template>
                    Пересчитать
                  </a-button>
                  <a-popconfirm title="Утвердить выписку? После утверждения изменение невозможно." @confirm="finalizeStatement(record)">
                    <a-button type="primary" size="small" :loading="finalizingId === record.id">
                      <template #icon><CheckOutlined /></template>
                      Утвердить
                    </a-button>
                  </a-popconfirm>
                </template>

                <!-- Finalized/Paid actions -->
                <template v-if="record.status === 'finalized' || record.status === 'paid'">
                  <a-popconfirm title="Создать корректировку? Исходный документ будет отменён." @confirm="createCreditNote(record)">
                    <a-button danger size="small" :loading="creditNoteId === record.id">
                      Корректировка
                    </a-button>
                  </a-popconfirm>
                </template>
              </template>
            </a-space>

            <!-- Storage Line Items -->
            <h4 style="margin: 12px 0 8px;">Хранение</h4>
            <a-table
              :columns="storageColumns"
              :data-source="statementDetails[record.id].line_items"
              :pagination="false"
              row-key="id"
              :scroll="{ x: 1000 }"
              size="small"
            >
              <template #bodyCell="{ column, record: item }">
                <template v-if="column.key === 'container'">
                  <a-tag color="blue">{{ item.container_number }}</a-tag>
                  <div style="font-size: 11px; color: #999; margin-top: 2px;">
                    {{ item.container_size_display }} / {{ item.container_status_display }}
                  </div>
                </template>
                <template v-if="column.key === 'period'">
                  <div>{{ formatDate(item.period_start) }}</div>
                  <div class="period-end">
                    <a-tag v-if="item.is_still_on_terminal" color="green" size="small">На терминале</a-tag>
                    <template v-else>{{ formatDate(item.period_end) }}</template>
                  </div>
                </template>
                <template v-if="column.key === 'days'">
                  <div class="days-breakdown">
                    <a-tag color="blue">{{ item.total_days }} всего</a-tag>
                    <a-tag color="green">{{ item.free_days }} льгот.</a-tag>
                    <a-tag color="orange">{{ item.billable_days }} опл.</a-tag>
                  </div>
                </template>
                <template v-if="column.key === 'rate'">
                  ${{ parseFloat(item.daily_rate_usd).toFixed(2) }}/день
                </template>
                <template v-if="column.key === 'amount_usd'">
                  <span class="amount-usd">${{ parseFloat(item.amount_usd).toFixed(2) }}</span>
                </template>
                <template v-if="column.key === 'amount_uzs'">
                  <span class="amount-uzs">{{ formatNumber(item.amount_uzs, 0) }} сум</span>
                </template>
              </template>
              <template #summary>
                <a-table-summary-row>
                  <a-table-summary-cell :col-span="4"><strong>Итого хранение</strong></a-table-summary-cell>
                  <a-table-summary-cell align="right">
                    <strong class="amount-usd">${{ formatNumber(statementDetails[record.id].summary.total_storage_usd) }}</strong>
                  </a-table-summary-cell>
                  <a-table-summary-cell align="right">
                    <strong class="amount-uzs">{{ formatNumber(statementDetails[record.id].summary.total_storage_uzs, 0) }} сум</strong>
                  </a-table-summary-cell>
                </a-table-summary-row>
              </template>
            </a-table>

            <!-- Service Items -->
            <template v-if="statementDetails[record.id].service_items?.length">
              <h4 style="margin: 16px 0 8px;">Услуги</h4>
              <a-table
                :columns="serviceColumns"
                :data-source="statementDetails[record.id].service_items"
                :pagination="false"
                row-key="id"
                size="small"
              >
                <template #bodyCell="{ column, record: item }">
                  <template v-if="column.key === 'container'">
                    <a-tag color="blue">{{ item.container_number }}</a-tag>
                  </template>
                  <template v-if="column.key === 'date'">
                    {{ formatDate(item.charge_date) }}
                  </template>
                  <template v-if="column.key === 'amount_usd'">
                    <span class="amount-usd">${{ parseFloat(item.amount_usd).toFixed(2) }}</span>
                  </template>
                  <template v-if="column.key === 'amount_uzs'">
                    <span class="amount-uzs">{{ formatNumber(item.amount_uzs, 0) }} сум</span>
                  </template>
                </template>
                <template #summary>
                  <a-table-summary-row>
                    <a-table-summary-cell :col-span="3"><strong>Итого услуги</strong></a-table-summary-cell>
                    <a-table-summary-cell align="right">
                      <strong class="amount-usd">${{ formatNumber(statementDetails[record.id].summary.total_services_usd) }}</strong>
                    </a-table-summary-cell>
                    <a-table-summary-cell align="right">
                      <strong class="amount-uzs">{{ formatNumber(statementDetails[record.id].summary.total_services_uzs, 0) }} сум</strong>
                    </a-table-summary-cell>
                  </a-table-summary-row>
                </template>
              </a-table>
            </template>

            <!-- Grand Total -->
            <a-card size="small" style="margin-top: 12px;" :body-style="{ display: 'flex', gap: '16px', alignItems: 'center', fontSize: '16px', fontWeight: 600 }">
              <span>Итого:</span>
              <span class="amount-usd">${{ formatNumber(statementDetails[record.id].summary.total_usd) }}</span>
              <span class="amount-uzs">{{ formatNumber(statementDetails[record.id].summary.total_uzs, 0) }} сум</span>
            </a-card>

            <!-- Pending Containers (informational) -->
            <template v-if="statementDetails[record.id].pending_containers_data?.length">
              <h4 style="margin: 16px 0 8px; color: #999;">Контейнеры на терминале (не включены в итого)</h4>
              <a-table
                :columns="pendingColumns"
                :data-source="statementDetails[record.id].pending_containers_data"
                :pagination="false"
                row-key="container_number"
                size="small"
                class="pending-table"
              >
                <template #bodyCell="{ column, record: item }">
                  <template v-if="column.key === 'container'">
                    <a-tag>{{ item.container_number }}</a-tag>
                    <span style="margin-left: 4px; font-size: 11px; color: #999;">{{ item.container_size }}</span>
                  </template>
                  <template v-if="column.key === 'entry_date'">
                    {{ formatDate(item.entry_date) }}
                  </template>
                  <template v-if="column.key === 'estimated_usd'">
                    <span style="color: #999;">${{ formatNumber(item.estimated_usd) }}</span>
                  </template>
                </template>
              </a-table>
            </template>

            <!-- Generation Info -->
            <div style="margin-top: 8px; color: #999; font-size: 12px;">
              Сформировано: {{ formatDateTime(statementDetails[record.id].generated_at) }}
              <template v-if="record.finalized_at">
                &nbsp;·&nbsp; Утверждено: {{ formatDateTime(record.finalized_at) }}
                <template v-if="record.finalized_by_name"> ({{ record.finalized_by_name }})</template>
              </template>
              <template v-if="record.paid_at">
                &nbsp;·&nbsp; Оплачено: {{ formatDateTime(record.paid_at) }}
                <template v-if="record.paid_marked_by_name"> ({{ record.paid_marked_by_name }})</template>
              </template>
            </div>
          </template>
        </div>
      </template>

      <!-- Empty state -->
      <template #emptyText>
        <a-empty :description="selectedYear ? 'Нет сформированных выписок за этот год' : 'Выберите год'" />
      </template>
    </a-table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue';
import { message } from 'ant-design-vue';
import type { TableProps } from 'ant-design-vue';
import {
  PlusOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  CheckOutlined,
} from '@ant-design/icons-vue';
import { http } from '../../utils/httpClient';
import { formatDateLocale, formatDateTime as formatDateTimeTz } from '../../utils/dateFormat';
import { downloadBlob } from '../../utils/download';
import { getCookie } from '../../utils/storage';
import { API_BASE_URL } from '../../config/api';

interface Props {
  companySlug?: string;
}

const props = defineProps<Props>();

const isAdmin = computed(() => !!props.companySlug);

const billingBaseUrl = computed(() => {
  if (props.companySlug) {
    return `/auth/companies/${props.companySlug}/billing`;
  }
  return '/customer/billing';
});

const monthNames = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
];

// --- Types ---

interface StatementSummary {
  total_containers: number;
  total_billable_days: number;
  total_storage_usd: string;
  total_storage_uzs: string;
  total_services_usd: string;
  total_services_uzs: string;
  total_usd: string;
  total_uzs: string;
}

interface StatementListItem {
  id: number;
  year: number;
  month: number;
  month_name: string;
  billing_method: string;
  billing_method_display: string;
  statement_type: 'invoice' | 'credit_note';
  statement_type_display: string;
  invoice_number: string | null;
  original_statement_id: number | null;
  status: 'draft' | 'finalized' | 'paid' | 'cancelled';
  status_display: string;
  finalized_at: string | null;
  finalized_by_name: string;
  paid_at: string | null;
  paid_marked_by_name: string;
  company_name: string;
  summary: StatementSummary;
  generated_at: string;
}

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

interface ServiceItem {
  id: number;
  container_number: string;
  description: string;
  charge_date: string;
  amount_usd: string;
  amount_uzs: string;
}

interface PendingContainer {
  container_number: string;
  container_size: string;
  entry_date: string;
  days_so_far: number;
  estimated_usd: string;
  estimated_uzs: string;
}

interface StatementDetail {
  id: number;
  billing_method_display: string;
  line_items: StatementLineItem[];
  service_items: ServiceItem[];
  pending_containers_data: PendingContainer[] | null;
  summary: StatementSummary;
  generated_at: string;
}

// --- State ---

const loading = ref(false);
const generating = ref(false);
const regeneratingId = ref<number | null>(null);
const finalizingId = ref<number | null>(null);
const creditNoteId = ref<number | null>(null);
const statements = ref<StatementListItem[]>([]);
const statementDetails = reactive<Record<number, StatementDetail>>({});
const detailLoading = reactive<Record<number, boolean>>({});
const expandedRowKeys = ref<number[]>([]);
const selectedYear = ref<number | null>(null);
const selectedMonth = ref<number | null>(null);

const availableYears = computed(() => {
  const currentYear = new Date().getFullYear();
  const years: number[] = [];
  for (let y = currentYear; y >= currentYear - 5; y--) {
    years.push(y);
  }
  return years;
});

// --- Status helpers ---

const statusColor = (status: string): string => {
  const map: Record<string, string> = {
    draft: 'blue',
    finalized: 'green',
    paid: 'gold',
    cancelled: 'red',
  };
  return map[status] || 'default';
};

const statusLabel = (status: string): string => {
  const map: Record<string, string> = {
    draft: 'Черновик',
    finalized: 'Выставлен',
    paid: 'Оплачен',
    cancelled: 'Отменён',
  };
  return map[status] || status;
};

// --- Table columns ---

const masterColumns: TableProps['columns'] = [
  { title: 'Период', key: 'period', width: 200 },
  { title: '№ документа', key: 'invoice_number', width: 160 },
  { title: 'Контейнеры', key: 'containers', width: 120, align: 'center' },
  { title: 'Итого USD', key: 'total_usd', width: 150, align: 'right' },
  { title: 'Итого UZS', key: 'total_uzs', width: 180, align: 'right' },
  { title: 'Статус', key: 'status', width: 130, align: 'center' },
];

const storageColumns: TableProps['columns'] = [
  { title: 'Контейнер', key: 'container', width: 150, fixed: 'left' },
  { title: 'Период', key: 'period', width: 140 },
  { title: 'Дни', key: 'days', width: 200 },
  { title: 'Ставка', key: 'rate', width: 100, align: 'right' },
  { title: 'Сумма USD', key: 'amount_usd', width: 120, align: 'right' },
  { title: 'Сумма UZS', key: 'amount_uzs', width: 150, align: 'right' },
];

const serviceColumns: TableProps['columns'] = [
  { title: 'Контейнер', key: 'container', width: 150 },
  { title: 'Описание', dataIndex: 'description', width: 250 },
  { title: 'Дата', key: 'date', width: 120 },
  { title: 'Сумма USD', key: 'amount_usd', width: 120, align: 'right' },
  { title: 'Сумма UZS', key: 'amount_uzs', width: 150, align: 'right' },
];

const pendingColumns: TableProps['columns'] = [
  { title: 'Контейнер', key: 'container', width: 180 },
  { title: 'Дата въезда', key: 'entry_date', width: 120 },
  { title: 'Дней', dataIndex: 'days_so_far', width: 80, align: 'center' },
  { title: '~USD', key: 'estimated_usd', width: 120, align: 'right' },
];

// --- Helpers ---

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '—';
  return formatDateLocale(dateStr) || '—';
};

const formatDateTime = (dateStr: string): string => {
  if (!dateStr) return '—';
  return formatDateTimeTz(dateStr) || '—';
};

const formatNumber = (value: string, fractionDigits = 2): string => {
  const num = parseFloat(value);
  if (isNaN(num)) return '—';
  return num.toLocaleString('ru-RU', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
};

// --- API calls ---

const fetchStatements = async () => {
  if (!selectedYear.value) return;

  loading.value = true;
  expandedRowKeys.value = [];

  try {
    const result = await http.get<{ success: boolean; data: StatementListItem[] }>(
      `${billingBaseUrl.value}/statements/?year=${selectedYear.value}`
    );
    statements.value = result.data || [];
  } catch {
    message.error('Не удалось загрузить выписки');
  } finally {
    loading.value = false;
  }
};

const fetchStatementDetail = async (record: StatementListItem) => {
  if (statementDetails[record.id]) return;

  detailLoading[record.id] = true;
  try {
    const result = await http.get<{ success: boolean; data: StatementDetail }>(
      `${billingBaseUrl.value}/statements/${record.year}/${record.month}/`
    );
    statementDetails[record.id] = result.data;
  } catch {
    message.error('Не удалось загрузить детали выписки');
  } finally {
    detailLoading[record.id] = false;
  }
};

const handleExpand = (expanded: boolean, record: StatementListItem) => {
  if (expanded) {
    expandedRowKeys.value = [record.id];
    fetchStatementDetail(record);
  } else {
    expandedRowKeys.value = [];
  }
};

const generateStatement = async () => {
  if (!selectedYear.value || !selectedMonth.value) return;

  generating.value = true;
  try {
    await http.get<{ success: boolean; data: StatementDetail }>(
      `${billingBaseUrl.value}/statements/${selectedYear.value}/${selectedMonth.value}/`
    );
    message.success('Выписка сформирована');
    await fetchStatements();
  } catch {
    message.error('Не удалось сформировать выписку');
  } finally {
    generating.value = false;
  }
};

const regenerateStatement = async (record: StatementListItem) => {
  regeneratingId.value = record.id;
  try {
    const result = await http.get<{ success: boolean; data: StatementDetail }>(
      `${billingBaseUrl.value}/statements/${record.year}/${record.month}/?regenerate=true`
    );
    statementDetails[record.id] = result.data;
    message.success('Выписка пересчитана');
    await fetchStatements();
  } catch {
    message.error('Не удалось пересчитать выписку');
  } finally {
    regeneratingId.value = null;
  }
};

const finalizeStatement = async (record: StatementListItem) => {
  finalizingId.value = record.id;
  try {
    await http.post<{ success: boolean; data: StatementListItem }>(
      `${billingBaseUrl.value}/statements/${record.id}/finalize/`
    );
    message.success('Выписка утверждена');
    delete statementDetails[record.id];
    await fetchStatements();
  } catch {
    message.error('Не удалось утвердить выписку');
  } finally {
    finalizingId.value = null;
  }
};

const togglePaymentStatus = async (record: StatementListItem) => {
  try {
    const result = await http.post<{ success: boolean; data: StatementListItem }>(
      `${billingBaseUrl.value}/statements/${record.id}/mark-paid/`
    );
    const idx = statements.value.findIndex(s => s.id === record.id);
    if (idx !== -1 && result.data) {
      statements.value[idx] = result.data;
    }
    message.success(
      result.data.status === 'paid' ? 'Отмечено как оплачено' : 'Статус оплаты снят'
    );
  } catch {
    message.error('Не удалось обновить статус оплаты');
  }
};

const createCreditNote = async (record: StatementListItem) => {
  creditNoteId.value = record.id;
  try {
    await http.post<{ success: boolean; data: StatementListItem }>(
      `${billingBaseUrl.value}/statements/${record.id}/credit-note/`
    );
    message.success('Корректировка создана');
    delete statementDetails[record.id];
    await fetchStatements();
  } catch {
    message.error('Не удалось создать корректировку');
  } finally {
    creditNoteId.value = null;
  }
};

const exportFile = async (record: StatementListItem, format: 'excel' | 'pdf') => {
  const token = getCookie('access_token');
  const url = `${API_BASE_URL}${billingBaseUrl.value}/statements/${record.year}/${record.month}/export/${format}/`;

  try {
    const response = await fetch(url, {
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const blob = await response.blob();
    const ext = format === 'excel' ? 'xlsx' : 'pdf';
    const filename = `statement_${record.year}_${String(record.month).padStart(2, '0')}.${ext}`;
    downloadBlob(blob, filename);
    message.success('Файл скачан');
  } catch {
    message.error('Не удалось скачать файл');
  }
};

const exportExcel = (record: StatementListItem) => exportFile(record, 'excel');
const exportPdf = (record: StatementListItem) => exportFile(record, 'pdf');

// --- Init ---

onMounted(() => {
  selectedYear.value = new Date().getFullYear();
  fetchStatements();
});
</script>

<style scoped>
.monthly-statements {
  padding: 8px 0;
}

.statements-table :deep(.ant-table-row) {
  cursor: pointer;
}

.period-cell {
  display: flex;
  align-items: center;
}

.period-label {
  font-weight: 500;
}

.invoice-number {
  font-family: monospace;
  font-size: 13px;
}

.draft-label {
  color: #ccc;
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

.expanded-detail {
  padding: 8px 16px;
}

.pending-table :deep(.ant-table) {
  opacity: 0.6;
}
</style>
