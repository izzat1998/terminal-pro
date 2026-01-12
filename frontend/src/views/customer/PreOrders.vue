<template>
    <a-card :bordered="false" class="content-card">
        <template #title>Предзаказы</template>

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

        <!-- Orders Section -->
        <div v-if="filteredOrders.length > 0" class="section">
            <div class="section-header">
                <h3 class="section-title">Список предзаказов</h3>
                <span class="stat-item">Всего: <strong>{{ totalCount }}</strong></span>
            </div>
            <a-table
                :dataSource="filteredOrders"
                :columns="orderColumns"
                :pagination="pagination"
                :loading="ordersLoading"
                :rowKey="(record: Order) => record.id"
                size="small"
                @change="handleTableChange"
            >
                <template #bodyCell="{ column, record }">
                    <template v-if="column.key === 'plate_number'">
                        <a-tag style="font-size: 0.9rem;" :bordered="false" color="blue">{{ record.plate_number }}</a-tag>
                    </template>
                    <template v-else-if="column.key === 'operation_type'">
                        <a-tag :color="record.operation_type === 'LOAD' ? 'green' : 'orange'">
                            {{ getOperationTypeDisplay(record.operation_type) }}
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
        </div>

        <!-- Empty State -->
        <a-empty v-if="!ordersLoading && filteredOrders.length === 0" description="Нет предзаказов" />

        <!-- Loading State -->
        <div v-if="ordersLoading && orders.length === 0" class="loading-container">
            <a-spin size="large" />
        </div>
    </a-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
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
    plate_number: string;
    operation_type: 'LOAD' | 'UNLOAD';
    status: 'PENDING' | 'MATCHED' | 'CANCELLED';
    status_display: string;
    truck_photo: string | null;
    notes: string;
    vehicle_entry: number | null;
    created_at: string;
    matched_at: string | null;
    cancelled_at: string | null;
    batch_id: string | null;
}

interface PaginatedResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: Order[];
}

defineProps<{
    company: Company | null;
    loading: boolean;
}>();

const orders = ref<Order[]>([]);
const totalCount = ref(0);
const ordersLoading = ref(false);
const statusFilter = ref<string | undefined>(undefined);
const operationFilter = ref<string | undefined>(undefined);

const pagination = ref({
    current: 1,
    pageSize: 10,
    total: 0,
    showSizeChanger: true,
    showTotal: (total: number) => `Всего ${total} записей`,
});

const orderColumns = [
    {
        title: 'Гос. номер',
        dataIndex: 'plate_number',
        key: 'plate_number',
        width: 140,
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

const filteredOrders = computed(() => {
    return orders.value.filter(order => {
        if (statusFilter.value && order.status !== statusFilter.value) return false;
        if (operationFilter.value && order.operation_type !== operationFilter.value) return false;
        return true;
    });
});

const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
        PENDING: 'default',
        MATCHED: 'green',
        CANCELLED: 'red',
    };
    return colors[status] || 'default';
};

const getOperationTypeDisplay = (type: string): string => {
    return type === 'LOAD' ? 'Погрузка' : 'Разгрузка';
};

const fetchOrders = async () => {
    try {
        ordersLoading.value = true;

        const result = await http.get<PaginatedResponse>('/customer/preorders/');

        orders.value = result.results || [];
        totalCount.value = result.count || 0;
        pagination.value.total = result.count || 0;
    } catch (error) {
        message.error(error instanceof Error ? error.message : 'Не удалось загрузить предзаказы. Попробуйте обновить страницу.');
    } finally {
        ordersLoading.value = false;
    }
};

const handleTableChange = (pag: { current?: number; pageSize?: number }) => {
    pagination.value.current = pag.current || 1;
    pagination.value.pageSize = pag.pageSize || 10;
    fetchOrders();
};

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

.loading-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 200px;
}
</style>
