<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import {
  DollarOutlined,
  CloseOutlined,
  FileTextOutlined,
  EyeOutlined,
} from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import type { TableProps } from 'ant-design-vue';
import { http } from '../../utils/httpClient';
import { formatCurrency } from '../../utils/formatters';
import { API_BASE_URL } from '../../config/api';
import { getStorageItem } from '../../utils/storage';

interface Props {
  open: boolean;
  entryId: number | null;
  containerNumber: string;
  companySlug?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  'update:open': [value: boolean];
}>();

interface BillingDocument {
  type: 'statement' | 'on_demand_invoice';
  id: number;
  number: string;
  period: string;
  status: 'draft' | 'finalized' | 'paid';
  amount_usd: string;
  amount_uzs: string;
  act_preview_url: string | null;
}

interface BillingDetailData {
  container_entry_id: number;
  container_number: string;
  total_billed_usd: string;
  total_billed_uzs: string;
  total_paid_usd: string;
  total_paid_uzs: string;
  documents: BillingDocument[];
}

const loading = ref(false);
const data = ref<BillingDetailData | null>(null);
const error = ref<string | null>(null);

const actHtml = ref<string | null>(null);
const actLoading = ref(false);
const actDocId = ref<number | null>(null);

const totalUnpaid = computed(() => {
  if (!data.value) return '0';
  const billed = parseFloat(data.value.total_billed_usd);
  const paid = parseFloat(data.value.total_paid_usd);
  return (billed - paid).toFixed(2);
});

watch(() => props.open, async (isOpen) => {
  if (isOpen && props.entryId) {
    await fetchBillingDetail();
  } else if (!isOpen) {
    data.value = null;
    error.value = null;
    actHtml.value = null;
    actDocId.value = null;
  }
});

async function fetchBillingDetail() {
  if (!props.entryId) return;

  loading.value = true;
  error.value = null;

  try {
    const baseUrl = props.companySlug
      ? '/billing'
      : '/customer';
    const response = await http.get<{ success: boolean; data: BillingDetailData }>(
      `${baseUrl}/container-entry/${props.entryId}/billing-detail/`
    );
    if (response.success && response.data) {
      data.value = response.data;
    } else {
      throw new Error('Ошибка загрузки данных');
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Ошибка загрузки данных';
    message.error(error.value);
  } finally {
    loading.value = false;
  }
}

async function fetchActPreview(doc: BillingDocument) {
  if (!doc.act_preview_url) return;

  if (actDocId.value === doc.id) {
    actHtml.value = null;
    actDocId.value = null;
    return;
  }

  actLoading.value = true;
  actDocId.value = doc.id;
  actHtml.value = null;

  try {
    const token = getStorageItem('access_token');
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${doc.act_preview_url}`, { headers });
    if (!response.ok) {
      throw new Error(`Ошибка загрузки акта (${response.status})`);
    }
    actHtml.value = await response.text();
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Ошибка загрузки акта');
    actHtml.value = null;
    actDocId.value = null;
  } finally {
    actLoading.value = false;
  }
}

function handleClose() {
  emit('update:open', false);
}

function getTypeLabel(type: BillingDocument['type']): string {
  return type === 'statement' ? 'Выписка' : 'Разовый счёт';
}

function getTypeColor(type: BillingDocument['type']): string {
  return type === 'statement' ? 'blue' : 'orange';
}

function getStatusLabel(status: BillingDocument['status']): string {
  const labels: Record<BillingDocument['status'], string> = {
    draft: 'Черновик',
    finalized: 'Выставлен',
    paid: 'Оплачен',
  };
  return labels[status];
}

function getStatusColor(status: BillingDocument['status']): string {
  const colors: Record<BillingDocument['status'], string> = {
    draft: 'default',
    finalized: 'processing',
    paid: 'success',
  };
  return colors[status];
}

const columns: TableProps['columns'] = [
  { title: 'Тип', key: 'type', width: 110 },
  { title: 'Номер', dataIndex: 'number', key: 'number', width: 150 },
  { title: 'Период', dataIndex: 'period', key: 'period', width: 120 },
  { title: 'Сумма USD', key: 'amount_usd', width: 110, align: 'right' },
  { title: 'Статус', key: 'status', width: 100, align: 'center' },
  { title: '', key: 'action', width: 70, align: 'center' },
];
</script>

<template>
  <a-modal
    :open="open"
    :footer="null"
    :width="750"
    :body-style="{ padding: '16px' }"
    centered
    @update:open="emit('update:open', $event)"
    @cancel="handleClose"
  >
    <template #title>
      <div class="modal-title">
        <DollarOutlined class="title-icon" />
        <span>Детализация выставленных сумм</span>
        <a-tag color="blue" style="margin-left: 12px;">{{ containerNumber }}</a-tag>
      </div>
    </template>

    <template #closeIcon>
      <CloseOutlined />
    </template>

    <a-spin :spinning="loading">
      <a-alert
        v-if="error"
        type="error"
        :message="error"
        show-icon
        style="margin-bottom: 16px;"
      />

      <div v-else-if="data" class="detail-content">
        <div class="summary-section">
          <a-row :gutter="[16, 16]">
            <a-col :span="8">
              <a-statistic
                title="Выставлено"
                :value="formatCurrency(data.total_billed_usd, 'USD')"
                :value-style="{ color: '#1677ff', fontSize: '20px' }"
              />
            </a-col>
            <a-col :span="8">
              <a-statistic
                title="Оплачено"
                :value="formatCurrency(data.total_paid_usd, 'USD')"
                :value-style="{ color: '#52c41a', fontSize: '20px' }"
              />
            </a-col>
            <a-col :span="8">
              <a-statistic
                title="Не оплачено"
                :value="formatCurrency(totalUnpaid, 'USD')"
                :value-style="{ color: parseFloat(totalUnpaid) > 0 ? '#fa8c16' : '#52c41a', fontSize: '20px' }"
              />
            </a-col>
          </a-row>
        </div>

        <a-divider style="margin: 16px 0;" />

        <a-table
          :columns="columns"
          :data-source="data.documents"
          :pagination="false"
          row-key="id"
          size="small"
          bordered
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'type'">
              <a-tag :color="getTypeColor(record.type)">
                {{ getTypeLabel(record.type) }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'amount_usd'">
              <span class="amount-usd">{{ formatCurrency(record.amount_usd, 'USD') }}</span>
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="getStatusColor(record.status)">
                {{ getStatusLabel(record.status) }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-tooltip
                :title="record.act_preview_url ? 'Предпросмотр акта' : 'Предпросмотр акта недоступен для разовых счетов'"
              >
                <a-button
                  type="link"
                  size="small"
                  :disabled="!record.act_preview_url"
                  :loading="actLoading && actDocId === record.id"
                  @click="fetchActPreview(record)"
                >
                  <template #icon>
                    <EyeOutlined v-if="!(actDocId === record.id && actHtml)" />
                    <FileTextOutlined v-else />
                  </template>
                </a-button>
              </a-tooltip>
            </template>
          </template>
        </a-table>

        <a-empty
          v-if="data.documents.length === 0"
          description="Нет выставленных документов"
          style="margin: 24px 0;"
        />

        <div v-if="actHtml" class="act-preview-section">
          <a-divider orientation="left" style="margin: 16px 0 12px;">
            <FileTextOutlined style="margin-right: 8px;" />
            Предпросмотр акта
          </a-divider>
          <div class="act-preview-wrapper">
            <iframe
              :srcdoc="actHtml"
              class="act-iframe"
              sandbox="allow-same-origin"
            />
          </div>
        </div>
      </div>

      <a-empty v-else description="Нет данных для отображения" />
    </a-spin>
  </a-modal>
</template>

<style scoped>
.modal-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: #1677ff;
  font-size: 18px;
}

.detail-content {
  min-height: 200px;
}

.summary-section {
  background: linear-gradient(135deg, #e6f7ff 0%, #f6ffed 100%);
  padding: 20px;
  border-radius: 8px;
}

.amount-usd {
  font-weight: 600;
  color: #1677ff;
}

.act-preview-section {
  margin-top: 8px;
}

.act-preview-wrapper {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  overflow: hidden;
}

.act-iframe {
  width: 100%;
  min-height: 500px;
  border: none;
  background: #fff;
}
</style>
