<script setup lang="ts">
/**
 * Container Placement Page - 3D Terminal View with Table Integration
 */

import { ref, onMounted } from 'vue';
import { ReloadOutlined } from '@ant-design/icons-vue';
import { usePlacementState } from '../composables/usePlacementState';
import TerminalLayout3D from '../components/TerminalLayout3D.vue';
import PlacementPanel from '../components/PlacementPanel.vue';
import CompanyCards from '../components/CompanyCards.vue';
import type { ContainerPlacement, UnplacedContainer } from '../types/placement';

// View mode: table or 3d
const viewMode = ref<'table' | '3d'>('3d');

// State
const {
  positionedContainers,
  unplacedContainers,
  stats,
  loading,
  selectedContainerId,
  selectContainer,
  refreshAll,
  // Company filtering
  companyStats,
  selectedCompanyName,
  selectCompany,
  filteredPositionedContainers,
  filteredUnplacedContainers,
} = usePlacementState();

// Selected unplaced container for placement
const selectedUnplaced = ref<UnplacedContainer | null>(null);

// Placement modal
const showPlacementModal = ref(false);

// Initialize data
onMounted(async () => {
  await refreshAll();
});

// Table columns for positioned containers
const positionedColumns = [
  { title: 'Номер контейнера', dataIndex: 'container_number', key: 'container_number' },
  { title: 'Тип', dataIndex: 'iso_type', key: 'iso_type', width: 80 },
  { title: 'Статус', dataIndex: 'status', key: 'status', width: 100 },
  { title: 'Позиция', dataIndex: ['position', 'coordinate'], key: 'position', width: 140 },
  { title: 'Дни на терминале', dataIndex: 'dwell_time_days', key: 'dwell_time_days', width: 120 },
  { title: 'Компания', dataIndex: 'company_name', key: 'company_name' },
];

// Table columns for unplaced containers
const unplacedColumns = [
  { title: 'Номер контейнера', dataIndex: 'container_number', key: 'container_number' },
  { title: 'Тип', dataIndex: 'iso_type', key: 'iso_type', width: 80 },
  { title: 'Статус', dataIndex: 'status', key: 'status', width: 100 },
  { title: 'Дни на терминале', dataIndex: 'dwell_time_days', key: 'dwell_time_days', width: 120 },
  { title: 'Компания', dataIndex: 'company_name', key: 'company_name' },
  { title: 'Действие', key: 'action', width: 120 },
];

// Handle 3D container click
function handle3DContainerClick(container: ContainerPlacement): void {
  selectContainer(container.id);
}

// Open placement modal for unplaced container
function openPlacement(container: UnplacedContainer): void {
  selectedUnplaced.value = container;
  showPlacementModal.value = true;
}

// Handle placement complete
async function onPlacementComplete(): Promise<void> {
  showPlacementModal.value = false;
  selectedUnplaced.value = null;
  await refreshAll();
}

// Table row click (positioned)
function onPositionedRowClick(record: ContainerPlacement): void {
  selectContainer(record.id);
}

// Compute row class for highlighting
function getRowClassName(record: ContainerPlacement): string {
  return record.id === selectedContainerId.value ? 'selected-row' : '';
}
</script>

<template>
  <div class="container-placement-page">
    <!-- Header with stats and view toggle -->
    <a-card class="header-card" :bordered="false">
      <a-row :gutter="16" align="middle">
        <a-col :span="16">
          <a-space size="large">
            <a-statistic
              title="На терминале"
              :value="stats?.occupied ?? 0"
              :value-style="{ color: '#1677ff' }"
            />
            <a-statistic
              title="Свободных позиций"
              :value="stats?.available ?? 0"
              :value-style="{ color: '#52c41a' }"
            />
            <a-statistic
              title="Без позиции"
              :value="unplacedContainers.length"
              :value-style="{ color: unplacedContainers.length > 0 ? '#fa8c16' : '#52c41a' }"
            />
          </a-space>
        </a-col>
        <a-col :span="8" style="text-align: right">
          <a-space>
            <a-button @click="refreshAll" :loading="loading">
              <template #icon><ReloadOutlined /></template>
              Обновить
            </a-button>
            <a-radio-group v-model:value="viewMode" button-style="solid">
              <a-radio-button value="3d">3D вид</a-radio-button>
              <a-radio-button value="table">Таблица</a-radio-button>
            </a-radio-group>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- Company filter cards -->
    <CompanyCards
      :companies="companyStats"
      :selected-company="selectedCompanyName"
      :total-count="positionedContainers.length"
      @select="selectCompany"
    />

    <!-- Main content -->
    <a-row :gutter="16" class="main-content">
      <!-- 3D View or Table -->
      <a-col :span="showPlacementModal ? 16 : 24">
        <a-card :bordered="false">
          <!-- 3D View -->
          <TerminalLayout3D
            v-if="viewMode === '3d'"
            @container-click="handle3DContainerClick"
          />

          <!-- Table View -->
          <template v-else>
            <!-- Positioned containers -->
            <a-typography-title :level="5" class="mb-3">
              Размещённые контейнеры ({{ filteredPositionedContainers.length }}{{ selectedCompanyName ? ` из ${positionedContainers.length}` : '' }})
            </a-typography-title>
            <a-table
              :columns="positionedColumns"
              :data-source="filteredPositionedContainers"
              :row-key="(record: ContainerPlacement) => record.id"
              :row-class-name="getRowClassName"
              :pagination="{ pageSize: 10, showSizeChanger: true }"
              :loading="loading"
              size="small"
              :custom-row="(record: ContainerPlacement) => ({
                onClick: () => onPositionedRowClick(record),
                style: { cursor: 'pointer' }
              })"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <a-tag :color="record.status === 'LADEN' ? 'green' : 'blue'">
                    {{ record.status === 'LADEN' ? 'Гружёный' : 'Порожний' }}
                  </a-tag>
                </template>
              </template>
            </a-table>

            <!-- Unplaced containers -->
            <a-divider />
            <a-typography-title :level="5" class="mb-3">
              <a-badge :count="filteredUnplacedContainers.length" :number-style="{ backgroundColor: '#fa8c16' }">
                <span style="padding-right: 10px">Требуют размещения{{ selectedCompanyName ? ` (${filteredUnplacedContainers.length} из ${unplacedContainers.length})` : '' }}</span>
              </a-badge>
            </a-typography-title>
            <a-table
              :columns="unplacedColumns"
              :data-source="filteredUnplacedContainers"
              :row-key="(record: UnplacedContainer) => record.id"
              :pagination="{ pageSize: 10 }"
              :loading="loading"
              size="small"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <a-tag :color="record.status === 'LADEN' ? 'green' : 'blue'">
                    {{ record.status === 'LADEN' ? 'Гружёный' : 'Порожний' }}
                  </a-tag>
                </template>
                <template v-if="column.key === 'action'">
                  <a-button type="link" size="small" @click="openPlacement(record)">
                    Разместить
                  </a-button>
                </template>
              </template>
            </a-table>
          </template>
        </a-card>
      </a-col>

      <!-- Placement Panel (sidebar) -->
      <a-col v-if="showPlacementModal" :span="8">
        <PlacementPanel
          :selected-container="selectedUnplaced"
          @close="showPlacementModal = false"
          @placed="onPlacementComplete"
        />
      </a-col>
    </a-row>
  </div>
</template>

<style scoped>
.container-placement-page {
  padding: 0;
}

.header-card {
  margin-bottom: 16px;
}

.main-content {
  min-height: 600px;
}

.mb-3 {
  margin-bottom: 12px;
}

:deep(.selected-row) {
  background-color: rgba(22, 119, 255, 0.1) !important;
}

:deep(.selected-row:hover td) {
  background-color: rgba(22, 119, 255, 0.15) !important;
}
</style>
