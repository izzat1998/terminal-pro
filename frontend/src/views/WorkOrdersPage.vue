<script setup lang="ts">
/**
 * WorkOrdersPage - Full-page work orders (tasks) management
 *
 * Features:
 * - Table with all work orders
 * - Filters: Status, Vehicle, Search
 * - Click row to open position viewer modal (2D/3D)
 * - Auto-refresh every 30 seconds
 *
 * Table columns:
 * - # (order_number)
 * - Контейнер (container_number)
 * - Позиция (target_coordinate)
 * - Статус (status with badge) - PENDING or COMPLETED
 * - Техника (assigned_to_vehicle)
 * - Создано (created_at)
 */

import { computed, ref } from 'vue';
import {
  ReloadOutlined,
  FilterOutlined,
  ClearOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons-vue';
import type { ColumnsType } from 'ant-design-vue/es/table';
import { useWorkOrdersPage } from '../composables/useWorkOrdersPage';
import type { WorkOrder, WorkOrderStatus } from '../types/placement';
import { formatRelativeTime } from '../utils/dateFormat';
import PositionViewerModal from '../components/PositionViewerModal.vue';

// Position viewer modal state
const showPositionModal = ref(false);
const selectedWorkOrder = ref<WorkOrder | null>(null);

const {
  workOrders,
  vehicles,
  loading,
  filters,
  pagination,
  handlePageChange,
  refresh,
  resetFilters,
} = useWorkOrdersPage();

// Status options for filter (simplified 2-status workflow)
const statusOptions: { value: WorkOrderStatus | ''; label: string }[] = [
  { value: '', label: 'Все статусы' },
  { value: 'PENDING', label: 'Ожидает' },
  { value: 'COMPLETED', label: 'Завершено' },
];

// Status badge colors
const statusColors: Record<WorkOrderStatus, string> = {
  PENDING: 'processing',
  COMPLETED: 'success',
};

// Status display text
const statusText: Record<WorkOrderStatus, string> = {
  PENDING: 'Ожидает',
  COMPLETED: 'Завершено',
};


// Table columns definition
const columns = computed<ColumnsType<WorkOrder>>(() => [
  {
    title: '#',
    dataIndex: 'order_number',
    key: 'order_number',
    width: 100,
    fixed: 'left',
  },
  {
    title: 'Контейнер',
    dataIndex: 'container_number',
    key: 'container_number',
    width: 150,
  },
  {
    title: 'Позиция',
    dataIndex: 'target_coordinate',
    key: 'target_coordinate',
    width: 140,
  },
  {
    title: 'Статус',
    dataIndex: 'status',
    key: 'status',
    width: 120,
  },
  {
    title: 'Техника',
    key: 'vehicle',
    width: 160,
  },
  {
    title: 'Создано',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 120,
  },
  {
    title: '',
    key: 'actions',
    width: 60,
    fixed: 'right',
  },
]);

// Open position viewer modal
function openPositionModal(record: WorkOrder): void {
  selectedWorkOrder.value = record;
  showPositionModal.value = true;
}

// Vehicle select options - use 0 as "all" since Ant Design doesn't handle null well
const vehicleOptions = computed(() => [
  { value: 0, label: 'Вся техника' },
  ...vehicles.value.map(v => ({
    value: v.id,
    label: `${v.name} (${v.vehicle_type_display})`,
  })),
]);

// Check if filters are active
const hasActiveFilters = computed(() =>
  filters.status !== '' ||
  filters.vehicleId !== 0 ||
  filters.search !== ''
);
</script>

<template>
  <div class="work-orders-page">
    <!-- Header -->
    <a-card class="header-card" :bordered="false">
      <a-row :gutter="16" align="middle">
        <a-col :flex="1">
          <h1 class="page-title">Задания</h1>
          <p class="page-subtitle">Управление заданиями на перемещение контейнеров</p>
        </a-col>
        <a-col>
          <a-button @click="refresh" :loading="loading">
            <template #icon><ReloadOutlined /></template>
            Обновить
          </a-button>
        </a-col>
      </a-row>
    </a-card>

    <!-- Filters -->
    <a-card class="filters-card" :bordered="false">
      <a-row :gutter="[16, 16]" align="middle">
        <a-col :xs="24" :sm="12" :md="6">
          <a-input
            v-model:value="filters.search"
            placeholder="Поиск по номеру..."
            allow-clear
          >
            <template #prefix>
              <FilterOutlined style="color: rgba(0, 0, 0, 0.25)" />
            </template>
          </a-input>
        </a-col>

        <a-col :xs="12" :sm="12" :md="4">
          <a-select
            v-model:value="filters.status"
            :options="statusOptions"
            style="width: 100%"
            placeholder="Статус"
          />
        </a-col>

        <a-col :xs="12" :sm="12" :md="5">
          <a-select
            v-model:value="filters.vehicleId"
            :options="vehicleOptions"
            style="width: 100%"
            placeholder="Техника"
          />
        </a-col>

        <a-col :xs="12" :sm="12" :md="5" style="text-align: right">
          <a-button
            v-if="hasActiveFilters"
            type="link"
            @click="resetFilters"
          >
            <template #icon><ClearOutlined /></template>
            Сбросить
          </a-button>
        </a-col>
      </a-row>
    </a-card>

    <!-- Table -->
    <a-card class="table-card" :bordered="false">
      <a-table
        :columns="columns"
        :data-source="workOrders"
        :loading="loading"
        :pagination="{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (total: number) => `Всего: ${total}`,
          onChange: handlePageChange,
        }"
        :scroll="{ x: 1000 }"
        row-key="id"
        size="middle"
        :custom-row="(record: WorkOrder) => ({
          class: 'clickable-row',
          onClick: () => openPositionModal(record),
        })"
      >
        <!-- Container number with ISO type -->
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'container_number'">
            <div>
              <strong>{{ record.container_number }}</strong>
              <div class="cell-secondary">{{ record.iso_type }}</div>
            </div>
          </template>

          <!-- Position coordinate -->
          <template v-else-if="column.key === 'target_coordinate'">
            <a-tag color="geekblue">
              {{ record.target_coordinate }}
            </a-tag>
          </template>

          <!-- Status badge -->
          <template v-else-if="column.key === 'status'">
            <a-badge
              :status="statusColors[record.status as WorkOrderStatus]"
              :text="statusText[record.status as WorkOrderStatus]"
            />
          </template>

          <!-- Vehicle -->
          <template v-else-if="column.key === 'vehicle'">
            <template v-if="record.assigned_to_vehicle">
              {{ record.assigned_to_vehicle.name }}
              <div class="cell-secondary">
                {{ record.assigned_to_vehicle.vehicle_type_display }}
              </div>
            </template>
            <span v-else class="cell-secondary">—</span>
          </template>

          <!-- Created at -->
          <template v-else-if="column.key === 'created_at'">
            {{ formatRelativeTime(record.created_at) }}
          </template>

          <!-- Actions -->
          <template v-else-if="column.key === 'actions'">
            <a-tooltip title="Показать на площадке">
              <a-button
                type="text"
                size="small"
                @click.stop="openPositionModal(record)"
              >
                <template #icon><EnvironmentOutlined /></template>
              </a-button>
            </a-tooltip>
          </template>
        </template>

        <!-- Empty state -->
        <template #emptyText>
          <a-empty description="Нет заданий">
            <template #image>
              <div style="font-size: 48px; color: #d9d9d9">📋</div>
            </template>
          </a-empty>
        </template>
      </a-table>
    </a-card>

    <!-- Position Viewer Modal -->
    <PositionViewerModal
      v-model:open="showPositionModal"
      :coordinate="selectedWorkOrder?.target_coordinate ?? ''"
      :container-number="selectedWorkOrder?.container_number"
      :iso-type="selectedWorkOrder?.iso_type"
      default-mode="3d"
    />
  </div>
</template>

<style scoped>
.work-orders-page {
  padding: 0;
}

.header-card {
  margin-bottom: 16px;
}

.page-title {
  margin: 0 0 4px 0;
  font-size: 24px;
  font-weight: 600;
  color: #262626;
}

.page-subtitle {
  margin: 0;
  font-size: 14px;
  color: #8c8c8c;
}

.filters-card {
  margin-bottom: 16px;
}

.table-card {
  /* Fill remaining space */
}

.cell-secondary {
  font-size: 12px;
  color: #8c8c8c;
}

/* Clickable row styling */
:deep(.clickable-row) {
  cursor: pointer;
  transition: background 0.2s ease;
}

:deep(.clickable-row:hover) {
  background: #fafafa;
}

:deep(.clickable-row td) {
  transition: background 0.2s ease;
}
</style>
