<template>
  <div class="on-demand-invoices">
    <!-- Pending exit warning -->
    <a-alert
      v-if="pendingExitCount > 0"
      type="warning"
      show-icon
      style="margin-bottom: 16px;"
      :message="`${pendingExitCount} конт. ожидают выезда`"
      description="Контейнеры включены в разовый счёт, но ещё не покинули терминал."
    />

    <!-- Header -->
    <a-space wrap :size="12" style="margin-bottom: 16px;">
      <a-select
        v-model:value="statusFilter"
        placeholder="Статус"
        style="width: 160px"
        allow-clear
        @change="fetchInvoices"
      >
        <a-select-option value="draft">Черновик</a-select-option>
        <a-select-option value="finalized">Проведён</a-select-option>
        <a-select-option value="paid">Оплачен</a-select-option>
        <a-select-option value="cancelled">Отменён</a-select-option>
      </a-select>

      <a-button @click="fetchInvoices" :loading="loading">
        <template #icon><ReloadOutlined /></template>
        Обновить
      </a-button>
    </a-space>

    <!-- Master Table -->
    <a-table
      :columns="masterColumns"
      :data-source="invoices"
      :loading="loading"
      :pagination="false"
      row-key="id"
      v-model:expandedRowKeys="expandedRowKeys"
      size="middle"
      class="invoices-table"
      @expand="handleExpand"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'invoice_number'">
          <span v-if="record.invoice_number" class="invoice-number">{{ record.invoice_number }}</span>
          <span v-else class="draft-label">OD-ЧЕРНОВИК-{{ record.id }}</span>
        </template>

        <template v-if="column.key === 'containers'">
          <span>{{ record.total_containers }}</span>
          <a-tooltip v-if="record.pending_exit_count > 0" :title="`${record.pending_exit_count} конт. ещё на терминале`">
            <a-badge
              :count="record.pending_exit_count"
              :number-style="{ backgroundColor: '#faad14', marginLeft: '6px' }"
            />
          </a-tooltip>
        </template>

        <template v-if="column.key === 'total_usd'">
          <span class="amount-usd">${{ formatNumber(record.total_usd) }}</span>
        </template>

        <template v-if="column.key === 'total_uzs'">
          <span class="amount-uzs">{{ formatNumber(record.total_uzs, 0) }} сум</span>
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

        <template v-if="column.key === 'created_at'">
          {{ formatDateTime(record.created_at) }}
        </template>
      </template>

      <!-- Expanded Row: Detail view with items + actions -->
      <template #expandedRowRender="{ record }">
        <div class="expanded-detail">
          <a-spin v-if="detailLoading[record.id]" style="display: block; text-align: center; padding: 20px;" />

          <template v-else-if="invoiceDetails[record.id]">
            <!-- Notes -->
            <a-alert
              v-if="invoiceDetails[record.id]?.notes"
              :message="invoiceDetails[record.id]?.notes"
              type="info"
              show-icon
              style="margin-bottom: 12px;"
            >
              <template #icon><InfoCircleOutlined /></template>
            </a-alert>

            <!-- Action Buttons -->
            <a-space style="margin-bottom: 12px;" wrap v-if="isAdmin">
              <!-- Draft actions -->
              <template v-if="record.status === 'draft'">
                <a-popconfirm title="Утвердить счёт? После утверждения изменение невозможно." @confirm="finalizeInvoice(record)">
                  <a-button type="primary" size="small" :loading="finalizingId === record.id">
                    <template #icon><CheckOutlined /></template>
                    Утвердить
                  </a-button>
                </a-popconfirm>
                <a-button danger size="small" :loading="cancellingId === record.id" @click="openCancelModal(record)">
                  <template #icon><CloseOutlined /></template>
                  Удалить
                </a-button>
              </template>

              <!-- Finalized actions -->
              <template v-if="record.status === 'finalized'">
                <a-button danger size="small" :loading="cancellingId === record.id" @click="openCancelModal(record)">
                  <template #icon><CloseOutlined /></template>
                  Отменить
                </a-button>
              </template>

              <!-- Export actions (for non-cancelled invoices) -->
              <template v-if="record.status !== 'cancelled'">
                <a-button size="small" @click="exportExcel(record)">
                  <template #icon><FileExcelOutlined /></template>
                  Excel
                </a-button>
                <a-button size="small" @click="exportPdf(record)">
                  <template #icon><FilePdfOutlined /></template>
                  PDF
                </a-button>
              </template>
            </a-space>

            <!-- Line Items Table -->
            <h4 style="margin: 12px 0 8px;">Позиции</h4>
            <a-table
              :columns="itemColumns"
              :data-source="invoiceDetails[record.id]?.items"
              :pagination="false"
              row-key="id"
              :scroll="{ x: 1000 }"
              size="small"
            >
              <template #bodyCell="{ column, record: item }">
                <template v-if="column.key === 'container'">
                  <a-tag color="blue">{{ item.container_number }}</a-tag>
                  <div style="font-size: 11px; color: #999; margin-top: 2px;">
                    {{ item.container_size }} / {{ item.container_status }}
                  </div>
                </template>
                <template v-if="column.key === 'period'">
                  <div>{{ formatDate(item.entry_date) }}</div>
                  <div class="period-end">
                    <template v-if="!item.exit_date">
                      <a-tag color="green" size="small">На терминале</a-tag>
                    </template>
                    <template v-else>
                      {{ formatDate(item.exit_date) }}
                    </template>
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
            </a-table>

            <!-- Service Items -->
            <template v-if="invoiceDetails[record.id]?.service_items?.length">
              <h4 style="margin: 16px 0 8px;">Доп. начисления</h4>
              <a-table
                :columns="serviceColumns"
                :data-source="invoiceDetails[record.id]?.service_items"
                :pagination="false"
                row-key="id"
                size="small"
              >
                <template #bodyCell="{ column, record: svc }">
                  <template v-if="column.key === 'container'">
                    <a-tag color="blue">{{ svc.container_number }}</a-tag>
                  </template>
                  <template v-if="column.key === 'date'">
                    {{ formatDate(svc.charge_date) }}
                  </template>
                  <template v-if="column.key === 'amount_usd'">
                    <span class="amount-usd">${{ parseFloat(svc.amount_usd).toFixed(2) }}</span>
                  </template>
                  <template v-if="column.key === 'amount_uzs'">
                    <span class="amount-uzs">{{ formatNumber(svc.amount_uzs, 0) }} сум</span>
                  </template>
                </template>
              </a-table>
            </template>

            <!-- Grand Total -->
            <a-card size="small" style="margin-top: 12px;" :body-style="{ display: 'flex', gap: '16px', alignItems: 'center', fontSize: '16px', fontWeight: 600 }">
              <span>Итого:</span>
              <span class="amount-usd">${{ formatNumber(invoiceDetails[record.id]?.total_usd ?? '') }}</span>
              <span class="amount-uzs">{{ formatNumber(invoiceDetails[record.id]?.total_uzs ?? '', 0) }} сум</span>
            </a-card>

            <!-- Audit Info -->
            <div style="margin-top: 8px; color: #999; font-size: 12px;">
              Создано: {{ formatDateTime(invoiceDetails[record.id]?.created_at ?? '') }}
              <template v-if="invoiceDetails[record.id]?.created_by_name">
                ({{ invoiceDetails[record.id]?.created_by_name }})
              </template>
              <template v-if="record.finalized_at">
                &nbsp;·&nbsp; Утверждено: {{ formatDateTime(record.finalized_at) }}
                <template v-if="record.finalized_by_name"> ({{ record.finalized_by_name }})</template>
              </template>
              <template v-if="record.paid_at">
                &nbsp;·&nbsp; Оплачено: {{ formatDateTime(record.paid_at) }}
                <template v-if="record.paid_marked_by_name"> ({{ record.paid_marked_by_name }})</template>
                <template v-if="record.payment_reference">
                  <br />Референс: {{ record.payment_reference }}
                </template>
                <template v-if="record.payment_date">
                  &nbsp;·&nbsp; Дата платежа: {{ formatDate(record.payment_date) }}
                </template>
              </template>
              <template v-if="record.cancelled_at">
                &nbsp;·&nbsp; <span style="color: #ff4d4f;">Отменён: {{ formatDateTime(record.cancelled_at) }}</span>
                <template v-if="record.cancelled_by_name"> ({{ record.cancelled_by_name }})</template>
                <template v-if="record.cancellation_reason">
                  <br /><span style="color: #ff4d4f;">Причина: {{ record.cancellation_reason }}</span>
                </template>
              </template>
            </div>
          </template>
        </div>
      </template>

      <!-- Empty state -->
      <template #emptyText>
        <a-empty description="Нет разовых счетов" />
      </template>
    </a-table>

    <!-- Cancel/Delete Modal -->
    <a-modal
      v-model:open="cancelModalVisible"
      :title="cancelModalInvoice?.status === 'draft' ? 'Удалить черновик' : 'Отменить счёт'"
      :ok-text="cancelModalInvoice?.status === 'draft' ? 'Удалить' : 'Отменить'"
      :ok-button-props="{ danger: true, loading: !!cancellingId, disabled: cancelOkDisabled }"
      cancel-text="Назад"
      @ok="confirmCancel"
    >
      <template v-if="cancelModalInvoice?.status === 'draft'">
        <p>Удалить черновик? Это действие нельзя отменить.</p>
      </template>
      <template v-else>
        <p>Отменить счёт <strong>{{ cancelModalInvoice?.invoice_number }}</strong>?</p>
        <p style="color: #666; margin-bottom: 12px;">Контейнеры вернутся в пул ежемесячного расчёта.</p>
        <a-form-item label="Причина отмены" required>
          <a-textarea
            v-model:value="cancellationReason"
            placeholder="Укажите причину отмены счёта"
            :rows="3"
            :maxlength="500"
            show-count
          />
        </a-form-item>
      </template>
    </a-modal>

    <!-- Payment Modal -->
    <a-modal
      v-model:open="paymentModalVisible"
      title="Отметить оплату"
      ok-text="Отметить оплаченным"
      cancel-text="Отмена"
      @ok="confirmMarkPaid"
    >
      <p>Отметить счёт <strong>{{ paymentModalInvoice?.invoice_number }}</strong> как оплаченный?</p>
      <a-form layout="vertical" style="margin-top: 16px;">
        <a-form-item label="Референс платежа">
          <a-input
            v-model:value="paymentReference"
            placeholder="Номер банковской транзакции, чека и т.д."
          />
        </a-form-item>
        <a-form-item label="Дата платежа">
          <a-input
            v-model:value="paymentDate"
            type="date"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import type { TableProps } from 'ant-design-vue';
import {
  ReloadOutlined,
  InfoCircleOutlined,
  CheckOutlined,
  CloseOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
} from '@ant-design/icons-vue';
import { http, downloadFile } from '../../utils/httpClient';
import { formatDateLocale, formatDateTime as formatDateTimeTz } from '../../utils/dateFormat';

defineOptions({ inheritAttrs: false });

interface Props {
  companySlug?: string;
}

const props = defineProps<Props>();

const isAdmin = computed(() => !!props.companySlug);

const baseUrl = computed(() => {
  if (props.companySlug) {
    return `/auth/companies/${props.companySlug}/on-demand-invoices`;
  }
  return '/customer/on-demand-invoices';
});

// --- Types ---

interface OnDemandInvoiceItem {
  id: number;
  container_number: string;
  container_size: string;
  container_status: string;
  entry_date: string;
  exit_date: string | null;
  total_days: number;
  free_days: number;
  billable_days: number;
  daily_rate_usd: string;
  daily_rate_uzs: string;
  amount_usd: string;
  amount_uzs: string;
}

interface OnDemandInvoiceListItem {
  id: number;
  invoice_number: string | null;
  status: 'draft' | 'finalized' | 'paid' | 'cancelled';
  status_display: string;
  notes: string;
  total_containers: number;
  pending_exit_count: number;
  total_usd: string;
  total_uzs: string;
  company_name: string;
  created_by_name: string;
  finalized_at: string | null;
  finalized_by_name: string;
  paid_at: string | null;
  paid_marked_by_name: string;
  payment_reference: string;
  payment_date: string | null;
  cancelled_at: string | null;
  cancelled_by_name: string;
  cancellation_reason: string;
  created_at: string;
}

interface OnDemandServiceItem {
  id: number;
  container_number: string;
  description: string;
  charge_date: string;
  amount_usd: string;
  amount_uzs: string;
}

interface OnDemandInvoiceDetail extends OnDemandInvoiceListItem {
  items: OnDemandInvoiceItem[];
  service_items: OnDemandServiceItem[];
}

// --- State ---

const loading = ref(false);
const finalizingId = ref<number | null>(null);
const cancellingId = ref<number | null>(null);
const invoices = ref<OnDemandInvoiceListItem[]>([]);
const invoiceDetails = reactive<Record<number, OnDemandInvoiceDetail>>({});
const detailLoading = reactive<Record<number, boolean>>({});
const expandedRowKeys = ref<number[]>([]);
const statusFilter = ref<string | undefined>(undefined);
const pendingExitCount = ref(0);

// Cancel modal state
const cancelModalVisible = ref(false);
const cancelModalInvoice = ref<OnDemandInvoiceListItem | null>(null);
const cancellationReason = ref('');

// Payment modal state
const paymentModalVisible = ref(false);
const paymentModalInvoice = ref<OnDemandInvoiceListItem | null>(null);
const paymentReference = ref('');
const paymentDate = ref<string>('');

// Computed: Cancel OK button disabled state
const cancelOkDisabled = computed(() => {
  if (!cancelModalInvoice.value) return true;
  if (cancelModalInvoice.value.status === 'draft') return false;
  // Finalized requires reason
  return !cancellationReason.value.trim();
});

const emit = defineEmits<{
  pendingExitCount: [count: number];
}>();

// --- Status helpers ---

const statusColor = (s: string): string => {
  const map: Record<string, string> = {
    draft: 'default',
    finalized: 'warning',
    paid: 'success',
    cancelled: 'error',
  };
  return map[s] || 'default';
};

const statusLabel = (s: string): string => {
  const map: Record<string, string> = {
    draft: 'Черновик',
    finalized: 'Проведён',
    paid: 'Оплачен',
    cancelled: 'Отменён',
  };
  return map[s] || s;
};

// --- Table columns ---

const masterColumns: TableProps['columns'] = [
  { title: '№ документа', key: 'invoice_number', width: 180 },
  { title: 'Контейнеры', key: 'containers', width: 120, align: 'center' },
  { title: 'Итого USD', key: 'total_usd', width: 150, align: 'right' },
  { title: 'Итого UZS', key: 'total_uzs', width: 180, align: 'right' },
  { title: 'Статус', key: 'status', width: 130, align: 'center' },
  { title: 'Дата создания', key: 'created_at', width: 160 },
];

const itemColumns: TableProps['columns'] = [
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

const fetchInvoices = async () => {
  loading.value = true;
  expandedRowKeys.value = [];

  try {
    const params = new URLSearchParams();
    if (statusFilter.value) {
      params.append('status', statusFilter.value);
    }

    const query = params.toString();
    const url = `${baseUrl.value}/list/${query ? '?' + query : ''}`;
    const result = await http.get<{ success: boolean; data: OnDemandInvoiceListItem[]; pending_exit_count?: number }>(url);
    invoices.value = result.data || [];
    pendingExitCount.value = result.pending_exit_count ?? 0;
    emit('pendingExitCount', pendingExitCount.value);
  } catch {
    message.error('Не удалось загрузить разовые счета');
  } finally {
    loading.value = false;
  }
};

const fetchInvoiceDetail = async (record: OnDemandInvoiceListItem) => {
  if (invoiceDetails[record.id]) return;

  detailLoading[record.id] = true;
  try {
    const result = await http.get<{ success: boolean; data: OnDemandInvoiceDetail }>(
      `${baseUrl.value}/${record.id}/`
    );
    invoiceDetails[record.id] = result.data;
  } catch {
    message.error('Не удалось загрузить детали счёта');
  } finally {
    detailLoading[record.id] = false;
  }
};

const handleExpand = (expanded: boolean, record: OnDemandInvoiceListItem) => {
  if (expanded) {
    expandedRowKeys.value = [record.id];
    fetchInvoiceDetail(record);
  } else {
    expandedRowKeys.value = [];
  }
};

const finalizeInvoice = async (record: OnDemandInvoiceListItem) => {
  finalizingId.value = record.id;
  try {
    await http.post<{ success: boolean; data: OnDemandInvoiceListItem }>(
      `${baseUrl.value}/${record.id}/finalize/`
    );
    message.success('Счёт утверждён');
    delete invoiceDetails[record.id];
    await fetchInvoices();
  } catch {
    message.error('Не удалось утвердить счёт');
  } finally {
    finalizingId.value = null;
  }
};

const togglePaymentStatus = async (record: OnDemandInvoiceListItem) => {
  // If currently paid, just toggle back (unmark)
  if (record.status === 'paid') {
    try {
      const result = await http.post<{ success: boolean; data: OnDemandInvoiceListItem }>(
        `${baseUrl.value}/${record.id}/mark-paid/`
      );
      const idx = invoices.value.findIndex(i => i.id === record.id);
      if (idx !== -1 && result.data) {
        invoices.value[idx] = result.data;
      }
      message.success('Статус оплаты снят');
    } catch {
      message.error('Не удалось обновить статус оплаты');
    }
    return;
  }

  // If finalized, open modal to enter payment details
  paymentModalInvoice.value = record;
  paymentReference.value = '';
  paymentDate.value = new Date().toISOString().split('T')[0] ?? ''; // Today
  paymentModalVisible.value = true;
};

const confirmMarkPaid = async () => {
  if (!paymentModalInvoice.value) return;

  try {
    const result = await http.post<{ success: boolean; data: OnDemandInvoiceListItem }>(
      `${baseUrl.value}/${paymentModalInvoice.value.id}/mark-paid/`,
      {
        payment_reference: paymentReference.value || undefined,
        payment_date: paymentDate.value || undefined,
      }
    );
    const idx = invoices.value.findIndex(i => i.id === paymentModalInvoice.value?.id);
    if (idx !== -1 && result.data) {
      invoices.value[idx] = result.data;
    }
    message.success('Отмечено как оплачено');
    paymentModalVisible.value = false;
  } catch {
    message.error('Не удалось обновить статус оплаты');
  }
};

const openCancelModal = (record: OnDemandInvoiceListItem) => {
  cancelModalInvoice.value = record;
  cancellationReason.value = '';
  cancelModalVisible.value = true;
};

const confirmCancel = async () => {
  if (!cancelModalInvoice.value) return;

  const record = cancelModalInvoice.value;
  const isDraft = record.status === 'draft';

  cancellingId.value = record.id;
  try {
    if (isDraft) {
      // Delete draft instead of cancel
      await http.delete(`${baseUrl.value}/${record.id}/`);
      message.success('Черновик удалён');
    } else {
      // Cancel finalized - requires reason
      await http.post<{ success: boolean; data: OnDemandInvoiceListItem }>(
        `${baseUrl.value}/${record.id}/cancel/`,
        { reason: cancellationReason.value }
      );
      message.success('Счёт отменён');
    }
    delete invoiceDetails[record.id];
    cancelModalVisible.value = false;
    await fetchInvoices();
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : 'Не удалось отменить счёт';
    message.error(errorMsg);
  } finally {
    cancellingId.value = null;
  }
};

const exportExcel = async (record: OnDemandInvoiceListItem) => {
  try {
    const invoiceName = record.invoice_number || `draft-${record.id}`;
    await downloadFile(
      `${baseUrl.value}/${record.id}/export/excel/`,
      `invoice-${invoiceName}.xlsx`
    );
  } catch {
    message.error('Ошибка при экспорте Excel');
  }
};

const exportPdf = async (record: OnDemandInvoiceListItem) => {
  try {
    const invoiceName = record.invoice_number || `draft-${record.id}`;
    await downloadFile(
      `${baseUrl.value}/${record.id}/export/pdf/`,
      `invoice-${invoiceName}.pdf`
    );
  } catch {
    message.error('Ошибка при экспорте PDF');
  }
};

// Initial fetch
onMounted(() => {
  fetchInvoices();
});
</script>

<style scoped>
.on-demand-invoices {
  padding: 8px 0;
}

.invoices-table :deep(.ant-table-row) {
  cursor: pointer;
}

.invoice-number {
  font-family: monospace;
  font-size: 13px;
}

.draft-label {
  color: #999;
  font-family: monospace;
  font-size: 13px;
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
</style>
