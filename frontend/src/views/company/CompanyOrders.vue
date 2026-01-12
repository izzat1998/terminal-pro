<template>
  <a-card :bordered="false" class="content-card">
    <template #title>Заказы</template>

    <!-- Filters -->
    <a-row :gutter="16" class="filters-row">
      <a-col :xs="24" :sm="8" :md="6">
        <a-select v-model:value="statusFilter" placeholder="Фильтр по статусу" allowClear style="width: 100%">
          <a-select-option value="PENDING">Ожидает</a-select-option>
          <a-select-option value="MATCHED">Сопоставлен</a-select-option>
          <a-select-option value="CANCELLED">Отменен</a-select-option>
        </a-select>
      </a-col>
      <a-col :xs="24" :sm="8" :md="6">
        <a-select v-model:value="operationFilter" placeholder="Тип операции" allowClear style="width: 100%">
          <a-select-option value="LOAD">Погрузка</a-select-option>
          <a-select-option value="UNLOAD">Разгрузка</a-select-option>
        </a-select>
      </a-col>
      <a-col :xs="24" :sm="8" :md="6">
        <a-button @click="fetchOrders" :loading="ordersLoading">
          <ReloadOutlined />
          Обновить
        </a-button>
      </a-col>
    </a-row>

    <!-- Batches Section -->
    <div v-if="filteredBatches.length > 0" class="section">
      <div class="section-header">
        <h3 class="section-title">Партии заказов</h3>
        <a-space :size="12">
          <span class="stat-item">Всего заказов: <strong>{{ totalOrdersCount }}</strong></span>
          <a-divider type="vertical" />
          <span class="stat-item">Партий: <strong>{{ batches.length }}</strong></span>
        </a-space>
      </div>
      <a-collapse v-model:activeKey="expandedBatches" class="batches-collapse">
        <a-collapse-panel v-for="batch in filteredBatches" :key="batch.batch_id" :header="getBatchHeader(batch)">
          <template #extra>
            <a-tag style="font-size: 0.9rem;" color="blue">{{ batch.orders_count }} заказов</a-tag>
          </template>
          <a-table :dataSource="getFilteredBatchOrders(batch.orders)" :columns="orderColumns" :pagination="false"
            :rowKey="(record: Order) => record.id" size="small">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'plate_number'">
                <a-tag style="font-size: 0.9rem;" :bordered="false" color="blue">{{ record.plate_number }}</a-tag>
              </template>
              <template v-else-if="column.key === 'operation_type'">
                <a-tag :color="record.operation_type === 'LOAD' ? 'green' : 'orange'">
                  {{ record.operation_type_display }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'status'">
                <a-tag :color="getStatusColor(record.status)">
                  {{ record.status_display }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'matched_at'">
                {{ record.matched_at ? formatDateTime(record.matched_at) : '-' }}
              </template>
              <template v-else-if="column.key === 'created_at'">
                {{ formatDateTime(record.created_at) }}
              </template>
            </template>
          </a-table>
        </a-collapse-panel>
      </a-collapse>
    </div>

    <!-- Empty State -->
    <a-empty v-if="!ordersLoading && filteredBatches.length === 0" description="Нет заказов" />

    <!-- Loading State -->
    <div v-if="ordersLoading" class="loading-container">
      <a-spin size="large" />
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { message } from 'ant-design-vue';
import { ReloadOutlined } from '@ant-design/icons-vue';
import { formatDateTime } from '../../utils/dateFormat';
import { http } from '../../utils/httpClient';

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface Order {
  id: number;
  customer: number;
  customer_name: string;
  plate_number: string;
  operation_type: 'LOAD' | 'UNLOAD';
  operation_type_display: string;
  status: 'PENDING' | 'MATCHED' | 'CANCELLED';
  status_display: string;
  truck_photo: string | null;
  truck_photo_url: string | null;
  vehicle_entry: number | null;
  matched_entry: number | null;
  matched_at: string | null;
  cancelled_at: string | null;
  notes: string;
  batch_id: string;
  created_at: string;
  updated_at: string;
}

interface Batch {
  batch_id: string;
  created_at: string;
  customer_id: number;
  customer_name: string;
  orders_count: number;
  orders: Order[];
}

defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const route = useRoute();

const batches = ref<Batch[]>([]);
const ordersLoading = ref(false);
const expandedBatches = ref<string[]>([]);
const statusFilter = ref<string | undefined>(undefined);
const operationFilter = ref<string | undefined>(undefined);

const orderColumns = [
  {
    title: 'Гос. номер',
    dataIndex: 'plate_number',
    key: 'plate_number',
    width: 120,
  },
  {
    title: 'Клиент',
    dataIndex: 'customer_name',
    key: 'customer_name',
    width: 150,
  },
  {
    title: 'Тип операции',
    dataIndex: 'operation_type',
    key: 'operation_type',
    width: 120,
  },
  {
    title: 'Статус',
    dataIndex: 'status',
    key: 'status',
    width: 120,
  },
  {
    title: 'Сопоставлен',
    dataIndex: 'matched_at',
    key: 'matched_at',
    width: 150,
  },
  {
    title: 'Создан',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 150,
  },
  {
    title: 'Примечание',
    dataIndex: 'notes',
    key: 'notes',
    ellipsis: true,
  },
];

const totalOrdersCount = computed(() => {
  return batches.value.reduce((sum, batch) => sum + batch.orders_count, 0);
});

const filterOrder = (order: Order): boolean => {
  if (statusFilter.value && order.status !== statusFilter.value) return false;
  if (operationFilter.value && order.operation_type !== operationFilter.value) return false;
  return true;
};

const filteredBatches = computed(() => {
  return batches.value.filter(batch => {
    const filteredOrders = batch.orders.filter(filterOrder);
    return filteredOrders.length > 0;
  });
});

const getFilteredBatchOrders = (orders: Order[]): Order[] => {
  return orders.filter(filterOrder);
};

const getStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    PENDING: 'default',
    MATCHED: 'green',
    CANCELLED: 'red',
  };
  return colors[status] || 'default';
};

const getBatchHeader = (batch: Batch): string => {
  return `${batch.customer_name} - ${formatDateTime(batch.created_at)}`;
};

const fetchOrders = async () => {
  try {
    ordersLoading.value = true;
    const slug = route.params.slug;

    const result = await http.get<{ success: boolean; results: Batch[]; message?: string }>(`/auth/companies/${slug}/orders/`);

    if (result.success) {
      batches.value = result.results || [];
      // Expand all batches by default
      expandedBatches.value = batches.value.map((b: Batch) => b.batch_id);
    } else {
      throw new Error(result.message || 'Ошибка загрузки заказов');
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка загрузки заказов');
  } finally {
    ordersLoading.value = false;
  }
};

watch(() => route.params.slug, (newSlug) => {
  if (newSlug) {
    fetchOrders();
  }
});

onMounted(() => {
  fetchOrders();
});
</script>

<style scoped>
.content-card {
  border-radius: 2px;
}

.stat-item {
  color: rgba(0, 0, 0, 0.65);
  font-size: 14px;
}

.filters-row {
  margin-bottom: 24px;
}

.filters-row .ant-col {
  margin-bottom: 8px;
}

.section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  margin: 0;
  color: rgba(0, 0, 0, 0.85);
}

.batches-collapse {
  background: transparent;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}
</style>
