<script setup lang="ts">
/**
 * Storage Cost Modal
 * Displays storage cost calculation for a container with period breakdown.
 * Shows USD and UZS amounts, free days, billable days, and tariff details.
 */

import { ref, watch } from 'vue';
import { DollarOutlined, CloseOutlined, CalendarOutlined, InfoCircleOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import { tariffsService, type StorageCostResult } from '../services/tariffsService';
import { formatDateLocale } from '../utils/dateFormat';
import { formatCurrency } from '../utils/formatters';

interface Props {
  open: boolean;
  entryId: number | null;
  containerNumber: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  'update:open': [value: boolean];
}>();

const loading = ref(false);
const costData = ref<StorageCostResult | null>(null);
const error = ref<string | null>(null);

// Fetch storage cost when modal opens
watch(() => props.open, async (isOpen) => {
  if (isOpen && props.entryId) {
    await fetchStorageCost();
  } else if (!isOpen) {
    costData.value = null;
    error.value = null;
  }
});

async function fetchStorageCost() {
  if (!props.entryId) return;

  loading.value = true;
  error.value = null;

  try {
    const response = await tariffsService.calculateStorageCost(props.entryId);
    if (response.success && response.data) {
      costData.value = response.data;
    } else {
      throw new Error('Ошибка расчёта стоимости');
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Ошибка загрузки данных';
    message.error(error.value);
  } finally {
    loading.value = false;
  }
}

function handleClose() {
  emit('update:open', false);
}

// Format date for display (DD.MM.YYYY)
function formatDate(dateStr: string): string {
  if (!dateStr) return '—';
  return formatDateLocale(dateStr) || '—';
}

// Get tariff type label
function getTariffTypeLabel(type: 'general' | 'special'): string {
  return type === 'special' ? 'Специальный' : 'Общий';
}

// Get tariff type color
function getTariffTypeColor(type: 'general' | 'special'): string {
  return type === 'special' ? 'purple' : 'blue';
}
</script>

<template>
  <a-modal
    :open="open"
    :footer="null"
    :width="700"
    :body-style="{ padding: '16px' }"
    centered
    @update:open="emit('update:open', $event)"
    @cancel="handleClose"
  >
    <template #title>
      <div class="modal-title">
        <DollarOutlined class="title-icon" />
        <span>Стоимость хранения</span>
        <a-tag color="blue" style="margin-left: 12px;">{{ containerNumber }}</a-tag>
      </div>
    </template>

    <template #closeIcon>
      <CloseOutlined />
    </template>

    <a-spin :spinning="loading">
      <!-- Error state -->
      <a-alert
        v-if="error"
        type="error"
        :message="error"
        show-icon
        style="margin-bottom: 16px;"
      />

      <!-- Cost data -->
      <div v-else-if="costData" class="cost-content">
        <!-- Summary section -->
        <div class="summary-section">
          <a-row :gutter="[16, 16]">
            <!-- Total USD -->
            <a-col :span="12">
              <a-statistic
                title="Итого (USD)"
                :value="formatCurrency(costData.total_usd, 'USD')"
                :value-style="{ color: '#3f8600', fontSize: '24px' }"
              />
            </a-col>
            <!-- Total UZS -->
            <a-col :span="12">
              <a-statistic
                title="Итого (UZS)"
                :value="formatCurrency(costData.total_uzs, 'UZS')"
                :value-style="{ color: '#1677ff', fontSize: '24px' }"
              />
            </a-col>
          </a-row>
          <!-- Billed / Unbilled breakdown -->
          <div v-if="costData.billed_usd" class="billed-bar">
            <div class="billed-item">
              <span class="billed-label">Выставлено</span>
              <span class="billed-value billed-green">${{ parseFloat(costData.billed_usd).toFixed(2) }}</span>
            </div>
            <div class="billed-item">
              <span class="billed-label">Не выставлено</span>
              <span class="billed-value" :class="parseFloat(costData.unbilled_usd || '0') > 0 ? 'billed-orange' : 'billed-green'">
                <template v-if="parseFloat(costData.unbilled_usd || '0') > 0">
                  ${{ parseFloat(costData.unbilled_usd!).toFixed(2) }}
                </template>
                <template v-else>✓ Всё выставлено</template>
              </span>
            </div>
          </div>
        </div>

        <!-- Details section -->
        <a-divider style="margin: 16px 0;" />

        <a-descriptions :column="2" size="small" bordered>
          <a-descriptions-item label="Клиент">
            {{ costData.company_name || 'Не указан' }}
          </a-descriptions-item>
          <a-descriptions-item label="Статус">
            <a-tag :color="costData.is_active ? 'green' : 'default'">
              {{ costData.is_active ? 'На терминале' : 'Выехал' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="Размер / Статус">
            {{ costData.container_size }} / {{ costData.container_status }}
          </a-descriptions-item>
          <a-descriptions-item label="Период хранения">
            {{ formatDate(costData.entry_date) }} — {{ formatDate(costData.end_date) }}
          </a-descriptions-item>
          <a-descriptions-item label="Всего дней">
            <a-tag color="blue">{{ costData.total_days }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="Льготных / Оплачиваемых">
            <a-tag color="green">{{ costData.free_days_applied }} льг.</a-tag>
            <a-tag color="orange" style="margin-left: 4px;">{{ costData.billable_days }} опл.</a-tag>
          </a-descriptions-item>
        </a-descriptions>

        <!-- Period breakdown -->
        <a-divider orientation="left" style="margin: 20px 0 12px;">
          <CalendarOutlined style="margin-right: 8px;" />
          Разбивка по периодам
        </a-divider>

        <a-table
          v-if="costData.periods && costData.periods.length > 0"
          :columns="[
            { title: 'Период', dataIndex: 'period', key: 'period', width: 160 },
            { title: 'Тариф', dataIndex: 'tariff_type', key: 'tariff_type', width: 100, align: 'center' },
            { title: 'Дней', dataIndex: 'days', key: 'days', width: 70, align: 'center' },
            { title: 'Льготных', dataIndex: 'free_days_used', key: 'free_days', width: 80, align: 'center' },
            { title: 'К оплате', dataIndex: 'billable_days', key: 'billable', width: 80, align: 'center' },
            { title: 'Тариф/день', dataIndex: 'rate', key: 'rate', width: 100 },
            { title: 'Сумма USD', dataIndex: 'amount_usd', key: 'amount_usd', width: 100, align: 'right' },
            { title: 'Сумма UZS', dataIndex: 'amount_uzs', key: 'amount_uzs', width: 120, align: 'right' },
          ]"
          :data-source="costData.periods.map((p, idx) => ({
            key: idx,
            period: `${formatDate(p.start_date)} — ${formatDate(p.end_date)}`,
            tariff_type: p.tariff_type,
            days: p.days,
            free_days_used: p.free_days_used,
            billable_days: p.billable_days,
            rate: formatCurrency(p.daily_rate_usd, 'USD'),
            amount_usd: formatCurrency(p.amount_usd, 'USD'),
            amount_uzs: formatCurrency(p.amount_uzs, 'UZS'),
          }))"
          :pagination="false"
          size="small"
          bordered
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'tariff_type'">
              <a-tag :color="getTariffTypeColor(record.tariff_type)">
                {{ getTariffTypeLabel(record.tariff_type) }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'free_days'">
              <span :style="{ color: record.free_days_used > 0 ? '#52c41a' : '#bfbfbf' }">
                {{ record.free_days_used }}
              </span>
            </template>
            <template v-else-if="column.key === 'billable'">
              <span :style="{ color: record.billable_days > 0 ? '#fa8c16' : '#bfbfbf' }">
                {{ record.billable_days }}
              </span>
            </template>
          </template>
        </a-table>

        <!-- Calculation note -->
        <div class="calculation-note">
          <InfoCircleOutlined style="margin-right: 6px; color: #1677ff;" />
          Расчёт выполнен: {{ formatDate(costData.calculated_at) }}
        </div>
      </div>

      <!-- Empty state -->
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
  color: #52c41a;
  font-size: 18px;
}

.cost-content {
  min-height: 200px;
}

.summary-section {
  background: linear-gradient(135deg, #f6ffed 0%, #e6f7ff 100%);
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.billed-bar {
  display: flex;
  gap: 24px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.billed-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.billed-label {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}

.billed-value {
  font-size: 16px;
  font-weight: 600;
}

.billed-green {
  color: #52c41a;
}

.billed-orange {
  color: #fa8c16;
}

.calculation-note {
  margin-top: 16px;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}
</style>
