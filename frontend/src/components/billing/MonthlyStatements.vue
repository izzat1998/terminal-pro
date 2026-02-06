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

        <template v-if="column.key === 'actions'">
          <a-space :size="4">
            <a-tooltip title="Excel">
              <a-button type="text" size="small" @click.stop="openPreview(record, 'excel')">
                <template #icon><FileExcelOutlined style="color: #52c41a;" /></template>
              </a-button>
            </a-tooltip>
            <a-tooltip title="PDF">
              <a-button type="text" size="small" @click.stop="openPreview(record, 'pdf')">
                <template #icon><FilePdfOutlined style="color: #ff4d4f;" /></template>
              </a-button>
            </a-tooltip>
            <a-tooltip title="Счёт-фактура">
              <a-button type="text" size="small" @click.stop="openPreview(record, 'act')">
                <template #icon><AuditOutlined style="color: #1677ff;" /></template>
              </a-button>
            </a-tooltip>
          </a-space>
        </template>
      </template>

      <!-- Expanded Row: Detail view -->
      <template #expandedRowRender="{ record }">
        <div class="expanded-detail">
          <a-spin v-if="detailLoading[record.id]" style="display: block; text-align: center; padding: 20px;" />

          <template v-else-if="statementDetails[record.id]">
            <!-- Billing Method -->
            <a-alert
              :message="`Метод расчёта: ${statementDetails[record.id]?.billing_method_display}`"
              type="info"
              show-icon
              style="margin-bottom: 12px;"
            >
              <template #icon><InfoCircleOutlined /></template>
            </a-alert>

            <!-- Exchange Rate (editable for drafts, read-only otherwise) -->
            <div v-if="isAdmin" style="margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 13px; color: #666;">Курс ЦБ (USD/UZS):</span>
              <template v-if="record.status === 'draft'">
                <a-input-number
                  v-model:value="exchangeRates[record.id]"
                  :min="0"
                  :step="0.01"
                  :precision="2"
                  size="small"
                  style="width: 150px;"
                  placeholder="Загрузить..."
                />
                <a-button size="small" :loading="fetchingRate[record.id]" @click="fetchCbuRate(record)">
                  <template #icon><CloudDownloadOutlined /></template>
                  ЦБ
                </a-button>
                <a-button
                  v-if="exchangeRates[record.id] && exchangeRates[record.id] !== Number(record.exchange_rate)"
                  type="link"
                  size="small"
                  :loading="savingRate[record.id]"
                  @click="saveExchangeRate(record)"
                >
                  Сохранить
                </a-button>
              </template>
              <template v-else>
                <span style="font-weight: 600;">
                  {{ record.exchange_rate ? Number(record.exchange_rate).toLocaleString('ru-RU', { minimumFractionDigits: 2 }) : '—' }}
                </span>
              </template>
            </div>

            <!-- Admin Action Buttons -->
            <a-space v-if="isAdmin" style="margin-bottom: 12px;" wrap>
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
            </a-space>

            <!-- Storage Line Items -->
            <h4 style="margin: 12px 0 8px;">Хранение</h4>
            <a-table
              :columns="storageColumns"
              :data-source="statementDetails[record.id]?.line_items"
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
                    <strong class="amount-usd">${{ formatNumber(statementDetails[record.id]?.summary?.total_storage_usd ?? '') }}</strong>
                  </a-table-summary-cell>
                  <a-table-summary-cell align="right">
                    <strong class="amount-uzs">{{ formatNumber(statementDetails[record.id]?.summary?.total_storage_uzs ?? '', 0) }} сум</strong>
                  </a-table-summary-cell>
                </a-table-summary-row>
              </template>
            </a-table>

            <!-- Service Items -->
            <template v-if="statementDetails[record.id]?.service_items?.length">
              <h4 style="margin: 16px 0 8px;">Услуги</h4>
              <a-table
                :columns="serviceColumns"
                :data-source="statementDetails[record.id]?.service_items"
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
                      <strong class="amount-usd">${{ formatNumber(statementDetails[record.id]?.summary?.total_services_usd ?? '') }}</strong>
                    </a-table-summary-cell>
                    <a-table-summary-cell align="right">
                      <strong class="amount-uzs">{{ formatNumber(statementDetails[record.id]?.summary?.total_services_uzs ?? '', 0) }} сум</strong>
                    </a-table-summary-cell>
                  </a-table-summary-row>
                </template>
              </a-table>
            </template>

            <!-- Grand Total -->
            <a-card size="small" style="margin-top: 12px;" :body-style="{ display: 'flex', gap: '16px', alignItems: 'center', fontSize: '16px', fontWeight: 600 }">
              <span>Итого:</span>
              <span class="amount-usd">${{ formatNumber(statementDetails[record.id]?.summary?.total_usd ?? '') }}</span>
              <span class="amount-uzs">{{ formatNumber(statementDetails[record.id]?.summary?.total_uzs ?? '', 0) }} сум</span>
            </a-card>

            <!-- Pending Containers (informational) -->
            <template v-if="statementDetails[record.id]?.pending_containers_data?.length">
              <h4 style="margin: 16px 0 8px; color: #999;">Контейнеры на терминале (не включены в итого)</h4>
              <a-table
                :columns="pendingColumns"
                :data-source="statementDetails[record.id]?.pending_containers_data"
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
              Сформировано: {{ formatDateTime(statementDetails[record.id]?.generated_at ?? '') }}
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

    <!-- Document Preview Modal -->
    <DocumentPreviewModal
      v-model:open="previewOpen"
      :record="previewRecord"
      :billing-base-url="billingBaseUrl"
      :initial-tab="previewTab"
    />
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
  AuditOutlined,
  CheckOutlined,
  CloudDownloadOutlined,
} from '@ant-design/icons-vue';
import { http } from '../../utils/httpClient';
import { formatDateLocale, formatDateTime as formatDateTimeTz } from '../../utils/dateFormat';
import DocumentPreviewModal from './DocumentPreviewModal.vue';

defineOptions({ inheritAttrs: false });

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
  exchange_rate: string | null;
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
const previewOpen = ref(false);
const previewRecord = ref<StatementListItem | null>(null);
const previewTab = ref<'excel' | 'pdf' | 'act'>('pdf');
const exchangeRates = reactive<Record<number, number | null>>({});
const fetchingRate = reactive<Record<number, boolean>>({});
const savingRate = reactive<Record<number, boolean>>({});

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
    draft: 'default',
    finalized: 'warning',
    paid: 'success',
    cancelled: 'error',
  };
  return map[status] || 'default';
};

const statusLabel = (status: string): string => {
  const map: Record<string, string> = {
    draft: 'Черновик',
    finalized: 'Проведён',
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
  { title: '', key: 'actions', width: 110, align: 'center' },
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
    // Initialize exchange rate from record data for the input field
    if (record.exchange_rate && exchangeRates[record.id] === undefined) {
      exchangeRates[record.id] = Number(record.exchange_rate);
    }
  } else {
    expandedRowKeys.value = [];
  }
};

const fetchCbuRate = async (record: StatementListItem) => {
  fetchingRate[record.id] = true;
  try {
    // Get last day of the statement month for CBU rate
    const lastDay = new Date(record.year, record.month, 0);
    const dateStr = lastDay.toISOString().split('T')[0];
    const result = await http.get<{ success: boolean; data: { rate: string; date: string } }>(
      `/billing/exchange-rate/?date=${dateStr}`
    );
    exchangeRates[record.id] = Number(result.data.rate);
    message.success(`Курс ЦБ на ${result.data.date}: ${result.data.rate}`);
  } catch {
    message.error('Не удалось получить курс ЦБ');
  } finally {
    fetchingRate[record.id] = false;
  }
};

const saveExchangeRate = async (record: StatementListItem) => {
  const rate = exchangeRates[record.id];
  if (!rate) return;

  savingRate[record.id] = true;
  try {
    await http.post(
      `${billingBaseUrl.value}/statements/${record.id}/set-exchange-rate/`,
      { exchange_rate: rate }
    );
    // Update the record in the list so the "Сохранить" button disappears
    const idx = statements.value.findIndex(s => s.id === record.id);
    if (idx !== -1) {
      statements.value[idx] = { ...statements.value[idx], exchange_rate: String(rate) };
    }
    message.success('Курс сохранён');
  } catch {
    message.error('Не удалось сохранить курс');
  } finally {
    savingRate[record.id] = false;
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

const openPreview = (record: StatementListItem, tab: 'excel' | 'pdf' | 'act') => {
  previewRecord.value = record;
  previewTab.value = tab;
  previewOpen.value = true;
};

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
