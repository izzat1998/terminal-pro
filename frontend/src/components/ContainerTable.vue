<template>
  <div class="container-page">
    <!-- Statistics Dashboard -->
    <a-spin :spinning="statsLoading">
      <a-row :gutter="[12, 12]" style="margin-bottom: 16px;">
        <!-- On Terminal -->
        <a-col :xs="12" :sm="8" :lg="4">
          <a-card
            hoverable
            size="small"
            :class="{ 'stat-card-active': activeStatFilter === 'onTerminal' }"
            @click="handleStatClick('onTerminal')"
          >
            <a-statistic
              title="На терминале"
              :value="stats.onTerminal"
              :value-style="{ color: '#1677ff' }"
            >
              <template #prefix><ContainerOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>

        <!-- Laden -->
        <a-col :xs="12" :sm="8" :lg="4">
          <a-card
            hoverable
            size="small"
            :class="{ 'stat-card-active': activeStatFilter === 'laden' }"
            @click="handleStatClick('laden')"
          >
            <a-statistic
              title="Гружёные"
              :value="stats.laden"
              :value-style="{ color: '#52c41a' }"
            >
              <template #prefix><InboxOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>

        <!-- Empty -->
        <a-col :xs="12" :sm="8" :lg="4">
          <a-card
            hoverable
            size="small"
            :class="{ 'stat-card-active': activeStatFilter === 'empty' }"
            @click="handleStatClick('empty')"
          >
            <a-statistic
              title="Порожние"
              :value="stats.empty"
              :value-style="{ color: '#faad14' }"
            >
              <template #prefix><BorderOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>

        <!-- Exited Today -->
        <a-col :xs="12" :sm="8" :lg="4">
          <a-card
            hoverable
            size="small"
            :class="{ 'stat-card-active': activeStatFilter === 'exitedToday' }"
            @click="handleStatClick('exitedToday')"
          >
            <a-statistic title="Выехало сегодня" :value="stats.exitedToday">
              <template #prefix><ExportOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>

        <!-- Entered Today -->
        <a-col :xs="12" :sm="8" :lg="4">
          <a-card
            hoverable
            size="small"
            :class="{ 'stat-card-active': activeStatFilter === 'enteredToday' }"
            @click="handleStatClick('enteredToday')"
          >
            <a-statistic title="Завезено сегодня" :value="stats.enteredToday">
              <template #prefix><ImportOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>

        <!-- Total -->
        <a-col :xs="12" :sm="8" :lg="4">
          <a-card
            hoverable
            size="small"
            :class="{ 'stat-card-active': activeStatFilter === 'total' }"
            @click="handleStatClick('total')"
          >
            <a-statistic title="Всего записей" :value="stats.total">
              <template #prefix><DatabaseOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <!-- Company Stats - Using a-space and a-tag -->
    <a-space wrap v-if="companyStats.length > 0 && !statsLoading" style="margin-bottom: 16px;">
      <span style="color: #8c8c8c; font-size: 12px;">По клиентам:</span>
      <a-tooltip v-for="company in companyStats" :key="company.id" placement="bottom">
        <template #title>
          <div style="text-align: center;">
            <div style="font-weight: 500; margin-bottom: 4px;">{{ company.name }}</div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.85);">
              <span style="color: #95de64;">{{ company.laden }} груж.</span>
              <span style="margin: 0 6px;">|</span>
              <span style="color: #ffd666;">{{ company.empty }} пор.</span>
            </div>
          </div>
        </template>
        <a-tag
          :color="activeCompanyFilter === company.id ? 'blue' : 'default'"
          style="cursor: pointer; padding: 4px 8px;"
          @click="handleCompanyChipClick(company.id)"
        >
          {{ company.name }} <strong>{{ company.count }}</strong>
        </a-tag>
      </a-tooltip>
    </a-space>

    <!-- Global Search and Auto-Refresh -->
    <div style="margin-bottom: 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
      <a-input-search
        v-model:value="globalSearch"
        placeholder="🔍 Поиск по номеру контейнера, клиенту, грузу..."
        style="width: 320px;"
        allow-clear
        @search="handleGlobalSearch"
        @change="debouncedSearch"
      />
      <a-tag v-if="globalSearch" color="blue">
        🔍 Найдено: {{ pagination.total }}
      </a-tag>

      <a-divider type="vertical" />

      <a-range-picker
        v-model:value="dateRange"
        format="DD.MM.YYYY"
        placeholder="📅 Период завоза"
        style="width: 240px;"
        @change="handleDateRangeChange"
        allow-clear
      />

      <a-divider type="vertical" />

      <a-switch
        v-model:checked="autoRefreshEnabled"
        checked-children="🔄"
        un-checked-children="⏸"
        size="small"
        title="Автообновление"
      />
      <a-select v-model:value="autoRefreshInterval" style="width: 70px;" size="small" :disabled="!autoRefreshEnabled">
        <a-select-option :value="15">15с</a-select-option>
        <a-select-option :value="30">30с</a-select-option>
        <a-select-option :value="60">1м</a-select-option>
        <a-select-option :value="120">2м</a-select-option>
      </a-select>
      <a-tag v-if="autoRefreshEnabled" color="processing" class="refresh-indicator">
        🔄 {{ autoRefreshInterval }}с
      </a-tag>
    </div>

  <a-card :bordered="false" class="main-table-card">
    <!-- Table Header -->
    <template #title>
      <div class="table-header">
        <span class="table-header__title">Контейнеры</span>
      </div>
    </template>
    <template #extra>
      <a-space size="middle">
        <!-- Column visibility settings -->
        <a-popover trigger="click" placement="bottomRight" :overlayStyle="{ width: '400px' }">
          <template #title>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>Настройка колонок</span>
              <a-space size="small">
                <a-button size="small" @click="applyPreset('basic')">Базовый</a-button>
                <a-button size="small" @click="applyPreset('entry')">Завоз</a-button>
                <a-button size="small" @click="applyPreset('exit')">Вывоз</a-button>
                <a-button size="small" @click="applyPreset('full')">Все</a-button>
                <a-divider type="vertical" />
                <a-button size="small" @click="resetColumnPreferences" title="Сбросить вид таблицы">
                  🔄 Сброс
                </a-button>
              </a-space>
            </div>
          </template>
          <template #content>
            <div style="max-height: 400px; overflow-y: auto;">
              <div v-for="(cols, category) in columnsByCategory" :key="category" style="margin-bottom: 12px;">
                <div style="font-weight: 600; margin-bottom: 6px; color: #666; font-size: 12px; text-transform: uppercase;">
                  {{ categoryLabels[category as ColumnCategory] }}
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                  <a-tag
                    v-for="col in cols"
                    :key="col.key"
                    :color="visibleColumnKeys.includes(col.key) ? 'blue' : 'default'"
                    style="cursor: pointer; margin: 0;"
                    @click="toggleColumn(col.key)"
                  >
                    {{ col.title }}
                  </a-tag>
                </div>
              </div>
            </div>
          </template>
          <a-button>
            <template #icon>
              <SettingOutlined />
            </template>
            Колонки ({{ visibleColumnKeys.length - 2 }})
          </a-button>
        </a-popover>
        <a-button type="default" @click="showExcelUploadModal">
          <template #icon>
            <UploadOutlined />
          </template>
          Импорт Excel
        </a-button>
        <a-button type="default" @click="showExportModal">
          <template #icon>
            <DownloadOutlined />
          </template>
          Экспорт в Excel
        </a-button>
        <a-button type="primary" @click="showCreateModal">
          <template #icon>
            <PlusOutlined />
          </template>
          Создать контейнер
        </a-button>
      </a-space>
    </template>

    <a-tabs v-model:activeKey="activeStatusTab" @change="handleStatusTabChange" style="margin-bottom: 16px;">
      <a-tab-pane key="all" tab="Все" />
      <a-tab-pane key="Порожний" tab="Порожний" />
      <a-tab-pane key="Гружёный" tab="Гружёный" />
    </a-tabs>
    <!-- Selection Info Bar -->
    <div v-if="selectedRowKeys.length > 0" style="margin-bottom: 16px;">
      <a-alert
        type="info"
        show-icon
        :message="`Выбрано ${selectedRowKeys.length} контейнеров`"
        banner
      >
        <template #action>
          <a-space>
            <a-button size="small" type="primary" @click="exportSelected">
              <template #icon><DownloadOutlined /></template>
              Экспорт
            </a-button>
            <a-popconfirm
              title="Удалить выбранные контейнеры?"
              ok-text="Да"
              cancel-text="Нет"
              @confirm="deleteSelected"
            >
              <a-button size="small" danger>
                <template #icon><DeleteOutlined /></template>
                Удалить
              </a-button>
            </a-popconfirm>
            <a-button size="small" @click="clearSelection">
              Сбросить
            </a-button>
          </a-space>
        </template>
      </a-alert>
    </div>

    <a-table
      :columns="columns"
      :data-source="dataSource"
      :pagination="pagination"
      :scroll="{ x: scrollX }"
      :loading="loading"
      :row-selection="rowSelection"
      :expandable="{ expandedRowRender: () => null }"
      @change="handleTableChange"
      class="mb-0"
      bordered
    >
      <!-- Expandable row for secondary details -->
      <template #expandedRowRender="{ record }">
        <div style="padding: 0 16px;">
          <a-descriptions size="small" :column="{ xs: 1, sm: 2, md: 3, lg: 4 }" bordered>
            <a-descriptions-item label="Собственник контейнера">
              {{ record.containerOwner || '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="Поезд при завозе">
              {{ record.entryTrainNumber || '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="№ машины/вагона (завоз)">
              {{ record.transportNumber || '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="Транспорт при вывозе">
              {{ record.exitTransportType || '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="Поезд при вывозе">
              {{ record.exitTrainNumber || '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="№ транспорта (вывоз)">
              {{ record.exitTransportNumber || '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="Станция назначения">
              {{ record.destinationStation || '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="Груз">
              {{ record.cargoName || '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="Тоннаж">
              {{ record.cargoWeight ? `${record.cargoWeight} т` : '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="Доп. крановая операция">
              {{ record.additionalCraneOperationDate || '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="Примечание" :span="2">
              {{ record.note || '—' }}
            </a-descriptions-item>
          </a-descriptions>
        </div>
      </template>

      <template #customFilterDropdown="{ setSelectedKeys, selectedKeys, confirm, clearFilters, column }">
        <!-- Dropdown mode for company filter - simple native select -->
        <div v-if="column.useDropdownFilter" style="padding: 8px; width: 200px;">
          <a-space direction="vertical" style="width: 100%;">
            <a-select
              :value="selectedKeys[0]"
              placeholder="Выберите клиента"
              style="width: 100%;"
              show-search
              :loading="companiesLoading"
              :filter-option="(input: string, option: { label?: string }) => option?.label?.toLowerCase().includes(input.toLowerCase())"
              @change="(value: number | string) => {
                setSelectedKeys(value ? [value] : []);
                confirm();
              }"
            >
              <a-select-option value="">✖ Все (очистить)</a-select-option>
              <a-select-option
                v-for="company in companies"
                :key="company.id"
                :value="company.id"
                :label="company.name"
              >
                {{ company.name }}
              </a-select-option>
            </a-select>
          </a-space>
        </div>

        <!-- Text input mode for other columns -->
        <div v-else style="padding: 8px">
          <a-input
            :placeholder="`Поиск ${column.title}`"
            :value="selectedKeys[0]"
            style="width: 188px; margin-bottom: 8px; display: block"
            @change="(e: Event) => setSelectedKeys((e.target as HTMLInputElement).value ? [(e.target as HTMLInputElement).value] : [])"
            @pressEnter="confirm"
          />
          <a-button
            type="primary"
            size="small"
            style="width: 90px; margin-right: 8px"
            @click="confirm"
          >
            <template #icon><SearchOutlined /></template>
            Поиск
          </a-button>
          <a-button size="small" style="width: 90px" @click="clearFilters">
            Сброс
          </a-button>
        </div>
      </template>
      <template #customFilterIcon="{ filtered }">
        <SearchOutlined :style="{ color: filtered ? '#108ee9' : undefined }" />
      </template>
      <template #bodyCell="{ column, record, index }">
        <template v-if="column.key === 'number'">
          {{ (pagination.current - 1) * pagination.pageSize + index + 1 }}
        </template>
        <template v-else-if="column.key === 'companyName'">
          <a-tooltip v-if="record.companySlug" :title="record.companyName">
            <a
              class="company-link"
              @click.prevent="router.push(`/accounts/companies/${record.companySlug}`)"
            >
              {{ record.companyName }}
            </a>
          </a-tooltip>
          <span v-else class="text-muted">—</span>
        </template>
        <template v-else-if="column.key === 'dwellTimeDays'">
          <a-tag :color="getDwellTimeColor(record.dwellTimeDays)">
            {{ record.dwellTimeDays ?? '—' }} дн.
          </a-tag>
        </template>
        <template v-else-if="column.key === 'files'">
          <a-button type="link" @click="showFiles(record)">
            {{ record.files }}
          </a-button>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-button type="link" size="small" @click="showEditModal(record)">
              <template #icon>
                <EditOutlined />
              </template>
            </a-button>
            <a-button type="link" size="small" danger @click="showDeleteConfirm(record)">
              <template #icon>
                <DeleteOutlined />
              </template>
            </a-button>
          </a-space>
        </template>
      </template>
    </a-table>
  </a-card>

  <FilesDialog v-model:open="filesModalVisible" :files="selectedFiles" :container-number="selectedContainer"
    :container-id="selectedContainerId" :container-iso-type="selectedContainerIsoType" :status="selectedStatus"
    :transport-type="selectedTransportType" :entry-train-number="selectedEntryTrainNumber"
    :transport-number="selectedTransportNumber" :exit-date="selectedExitDate" :exit-transport-type="selectedExitTransportType"
    :exit-train-number="selectedExitTrainNumber" :exit-transport-number="selectedExitTransportNumber"
    :destination-station="selectedDestinationStation" :location="selectedLocation"
    :additional-crane-operation-date="selectedAdditionalCraneOperationDate" :note="selectedNote"
    :cargo-weight="selectedCargoWeight" :cargo-name="selectedCargoName"
    :company-id="selectedCompanyId" :container-owner-id="selectedContainerOwnerId" @upload-success="handleUploadSuccess"
    @refresh-files="handleRefreshFiles" />

  <UpsertContainerModal v-model:open="createModalVisible" mode="create" @success="handleCreateSuccess" />

  <UpsertContainerModal v-model:open="editModalVisible" mode="edit" :container-id="selectedContainerId"
    :container-number="selectedContainer" :container-iso-type="selectedContainerIsoType" :status="selectedStatus"
    :transport-type="selectedTransportType" :entry-train-number="selectedEntryTrainNumber"
    :transport-number="selectedTransportNumber" :exit-date="selectedExitDate" :exit-transport-type="selectedExitTransportType"
    :exit-train-number="selectedExitTrainNumber" :exit-transport-number="selectedExitTransportNumber"
    :destination-station="selectedDestinationStation" :location="selectedLocation"
    :additional-crane-operation-date="selectedAdditionalCraneOperationDate" :crane-operations="selectedCraneOperations"
    :note="selectedNote" :cargo-weight="selectedCargoWeight"
    :cargo-name="selectedCargoName" :company-id="selectedCompanyId" :container-owner-id="selectedContainerOwnerId"
    @success="handleEditSuccess" />

  <ExcelUploadModal v-model:open="excelUploadModalVisible" @upload-success="handleExcelUploadSuccess" />

  <ExcelExportModal v-model:open="excelExportModalVisible" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import type { Dayjs } from 'dayjs';
import { terminalService, type FileAttachment, type CraneOperation } from '../services/terminalService';
import { message, Modal } from 'ant-design-vue';
import {
  SearchOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UploadOutlined,
  DownloadOutlined,
  SettingOutlined,
  ContainerOutlined,
  InboxOutlined,
  BorderOutlined,
  ExportOutlined,
  ImportOutlined,
  DatabaseOutlined,
} from '@ant-design/icons-vue';
import { http } from '../utils/httpClient';
import { debounce } from 'lodash-es';
import { useContainerTransform, type ContainerRecord } from '../composables/useContainerTransform';
import FilesDialog from './FilesDialog.vue';
import UpsertContainerModal from './UpsertContainerModal.vue';
import ExcelUploadModal from './ExcelUploadModal.vue';
import ExcelExportModal from './ExcelExportModal.vue';

// Initialize composable for data transformation
const { transformEntries } = useContainerTransform();

// Column categories for organization
type ColumnCategory = 'core' | 'entry' | 'exit' | 'cargo' | 'other';

interface ColumnConfig {
  title: string;
  key: string;
  dataIndex?: string;
  category: ColumnCategory;
  defaultVisible: boolean;
  width: number;
  align?: 'left' | 'center' | 'right';
  fixed?: 'left' | 'right';
  ellipsis?: boolean;
  sorter?: boolean;
  defaultSortOrder?: 'ascend' | 'descend';
  useDropdownFilter?: boolean;
  customFilterDropdown?: boolean;
  filters?: { text: string; value: string }[];
  filterMultiple?: boolean;
  headerStyle?: Record<string, string>;
}

// Header styles by category
const headerStyles = {
  core: { backgroundColor: '#f6ffed', color: '#52c41a', fontWeight: '600' },
  entry: { backgroundColor: '#f6ffed', color: '#52c41a', fontWeight: '600' },
  exit: { backgroundColor: '#e6f4ff', color: '#1677ff', fontWeight: '600' },
  cargo: { backgroundColor: '#fff7e6', color: '#fa8c16', fontWeight: '600' },
  other: {},
};

// All available columns configuration
const allColumnsConfig: ColumnConfig[] = [
  { title: '№', key: 'number', category: 'core', defaultVisible: true, width: 60, align: 'center', fixed: 'left' },
  { title: 'Номер контейнера', key: 'container', dataIndex: 'container', category: 'core', defaultVisible: true, width: 180, align: 'center', fixed: 'left', ellipsis: true, customFilterDropdown: true, sorter: true },
  { title: 'Тип', key: 'isoType', dataIndex: 'isoType', category: 'core', defaultVisible: true, width: 80, align: 'center', filters: [
    { text: '22G1', value: '22G1' }, { text: '42G1', value: '42G1' }, { text: '45G1', value: '45G1' }, { text: 'L5G1', value: 'L5G1' },
    { text: '22R1', value: '22R1' }, { text: '42R1', value: '42R1' }, { text: '45R1', value: '45R1' }, { text: 'L5R1', value: 'L5R1' },
    { text: '22U1', value: '22U1' }, { text: '42U1', value: '42U1' }, { text: '45U1', value: '45U1' },
    { text: '22P1', value: '22P1' }, { text: '42P1', value: '42P1' }, { text: '45P1', value: '45P1' },
    { text: '22T1', value: '22T1' }, { text: '42T1', value: '42T1' },
  ]},
  { title: 'Статус', key: 'containerStatus', dataIndex: 'containerStatus', category: 'core', defaultVisible: true, width: 100, align: 'center', sorter: true },
  { title: 'Клиент', key: 'companyName', dataIndex: 'companyName', category: 'core', defaultVisible: true, width: 160, align: 'center', ellipsis: true, customFilterDropdown: true, useDropdownFilter: true },
  { title: 'Собственник', key: 'containerOwner', dataIndex: 'containerOwner', category: 'core', defaultVisible: false, width: 140, align: 'center', ellipsis: true, customFilterDropdown: true },
  { title: 'Дата завоза', key: 'entryTime', dataIndex: 'entryTime', category: 'entry', defaultVisible: true, width: 120, align: 'center', customFilterDropdown: true, sorter: true, defaultSortOrder: 'descend' as const },
  { title: 'Транспорт (завоз)', key: 'transportType', dataIndex: 'transportType', category: 'entry', defaultVisible: true, width: 130, align: 'center', filters: [{ text: 'Авто', value: 'Авто' }, { text: 'Вагон', value: 'Вагон' }], filterMultiple: false, sorter: true },
  { title: 'Поезд (завоз)', key: 'entryTrainNumber', dataIndex: 'entryTrainNumber', category: 'entry', defaultVisible: false, width: 130, align: 'center', ellipsis: true, customFilterDropdown: true },
  { title: '№ машины/вагона', key: 'transportNumber', dataIndex: 'transportNumber', category: 'entry', defaultVisible: false, width: 140, align: 'center', customFilterDropdown: true },
  { title: 'Дата вывоза', key: 'exitDate', dataIndex: 'exitDate', category: 'exit', defaultVisible: true, width: 120, align: 'center', customFilterDropdown: true, sorter: true },
  { title: 'Транспорт (вывоз)', key: 'exitTransportType', dataIndex: 'exitTransportType', category: 'exit', defaultVisible: false, width: 140, align: 'center', filters: [{ text: 'Авто', value: 'Авто' }, { text: 'Вагон', value: 'Вагон' }], filterMultiple: false },
  { title: 'Поезд (вывоз)', key: 'exitTrainNumber', dataIndex: 'exitTrainNumber', category: 'exit', defaultVisible: false, width: 130, align: 'center', ellipsis: true, customFilterDropdown: true },
  { title: '№ транспорта (вывоз)', key: 'exitTransportNumber', dataIndex: 'exitTransportNumber', category: 'exit', defaultVisible: false, width: 160, align: 'center', ellipsis: true, customFilterDropdown: true },
  { title: 'Станция назнач.', key: 'destinationStation', dataIndex: 'destinationStation', category: 'exit', defaultVisible: false, width: 140, align: 'center', ellipsis: true, customFilterDropdown: true },
  { title: 'Место', key: 'location', dataIndex: 'location', category: 'core', defaultVisible: true, width: 100, align: 'center', ellipsis: true, customFilterDropdown: true },
  { title: 'Доп. крановая операция', key: 'additionalCraneOperationDate', dataIndex: 'additionalCraneOperationDate', category: 'other', defaultVisible: false, width: 160, align: 'center', customFilterDropdown: true },
  { title: 'Примечание', key: 'note', dataIndex: 'note', category: 'other', defaultVisible: false, width: 150, align: 'center', ellipsis: true, customFilterDropdown: true },
  { title: 'Хранение (дней)', key: 'dwellTimeDays', dataIndex: 'dwellTimeDays', category: 'cargo', defaultVisible: true, width: 130, align: 'center', customFilterDropdown: true, sorter: true },
  { title: 'Груз', key: 'cargoName', dataIndex: 'cargoName', category: 'cargo', defaultVisible: false, width: 140, align: 'center', ellipsis: true, customFilterDropdown: true },
  { title: 'Тоннаж', key: 'cargoWeight', dataIndex: 'cargoWeight', category: 'cargo', defaultVisible: false, width: 100, align: 'center', customFilterDropdown: true, sorter: true },
  { title: 'Файлы', key: 'files', dataIndex: 'files', category: 'other', defaultVisible: true, width: 80, align: 'center' },
  { title: 'Действия', key: 'actions', category: 'other', defaultVisible: true, width: 100, align: 'center', fixed: 'right' },
];

// Preset configurations
const columnPresets = {
  basic: ['number', 'container', 'isoType', 'containerStatus', 'companyName', 'entryTime', 'location', 'dwellTimeDays', 'files', 'actions'],
  entry: ['number', 'container', 'isoType', 'containerStatus', 'companyName', 'entryTime', 'transportType', 'entryTrainNumber', 'transportNumber', 'files', 'actions'],
  exit: ['number', 'container', 'isoType', 'containerStatus', 'exitDate', 'exitTransportType', 'exitTrainNumber', 'exitTransportNumber', 'destinationStation', 'files', 'actions'],
  full: allColumnsConfig.map(c => c.key),
};

// Visible columns state (initialized with default visible columns)
const visibleColumnKeys = ref<string[]>(
  allColumnsConfig.filter(c => c.defaultVisible).map(c => c.key)
);

// Computed columns based on visibility
const columns = computed(() => {
  return allColumnsConfig
    .filter(col => visibleColumnKeys.value.includes(col.key))
    .map(col => ({
      title: col.title,
      key: col.key,
      dataIndex: col.dataIndex,
      width: col.width,
      align: col.align,
      fixed: col.fixed,
      ellipsis: col.ellipsis,
      sorter: col.sorter,
      defaultSortOrder: col.defaultSortOrder,
      useDropdownFilter: col.useDropdownFilter,
      customFilterDropdown: col.customFilterDropdown,
      filters: col.filters,
      filterMultiple: col.filterMultiple,
      customHeaderCell: () => ({
        style: headerStyles[col.category] || {}
      }),
    }));
});

// Computed scroll width based on visible columns
const scrollX = computed(() => {
  return allColumnsConfig
    .filter(col => visibleColumnKeys.value.includes(col.key))
    .reduce((sum, col) => sum + col.width, 0) + 50;
});

// Column visibility helpers
const toggleColumn = (key: string) => {
  const index = visibleColumnKeys.value.indexOf(key);
  if (index > -1) {
    visibleColumnKeys.value.splice(index, 1);
  } else {
    visibleColumnKeys.value.push(key);
  }
  // Save to localStorage
  localStorage.setItem('container_columns_visible', JSON.stringify(visibleColumnKeys.value));
};

const applyPreset = (preset: keyof typeof columnPresets) => {
  visibleColumnKeys.value = [...columnPresets[preset]];
  localStorage.setItem('container_columns_visible', JSON.stringify(visibleColumnKeys.value));
};

// Watch for sort changes and save to localStorage
// Reset column preferences
const resetColumnPreferences = () => {
  localStorage.removeItem('container_columns_visible');
  localStorage.removeItem('container_columns_sort');
  visibleColumnKeys.value = allColumnsConfig.filter(c => c.defaultVisible).map(c => c.key);
  currentSorter.value = { field: 'entryTime', order: 'descend' };
  message.success('Вид таблицы сброшен');
};

// Toggleable columns (excludes fixed columns like number and actions)
const toggleableColumns = computed(() =>
  allColumnsConfig.filter(c => c.key !== 'number' && c.key !== 'actions')
);

// Group columns by category for the settings panel
const columnsByCategory = computed(() => {
  const categories: Record<ColumnCategory, ColumnConfig[]> = {
    core: [],
    entry: [],
    exit: [],
    cargo: [],
    other: [],
  };
  toggleableColumns.value.forEach(col => {
    categories[col.category].push(col);
  });
  return categories;
});

const categoryLabels: Record<ColumnCategory, string> = {
  core: 'Основные',
  entry: 'Завоз',
  exit: 'Вывоз',
  cargo: 'Груз',
  other: 'Прочее',
};

// Dwell time color coding
const getDwellTimeColor = (days?: number): string => {
  if (!days) return 'default';
  if (days <= 3) return 'green';
  if (days <= 7) return 'orange';
  return 'red';
};

const router = useRouter();

// Statistics
interface ContainerStats {
  onTerminal: number;
  laden: number;
  empty: number;
  exitedToday: number;
  enteredToday: number;
  total: number;
}

interface CompanyStat {
  id: number;
  name: string;
  slug: string;
  count: number;
  laden: number;
  empty: number;
}

const stats = ref<ContainerStats>({
  onTerminal: 0,
  laden: 0,
  empty: 0,
  exitedToday: 0,
  enteredToday: 0,
  total: 0,
});
const companyStats = ref<CompanyStat[]>([]);
const statsLoading = ref(true);

// Backend stats response type
interface StatsResponse {
  total: number;
  on_terminal: number;
  laden: number;
  empty: number;
  entered_today: number;
  exited_today: number;
  companies: Array<{
    company__id: number;
    company__name: string;
    company__slug: string;
    count: number;
    laden: number;
    empty: number;
  }>;
}

const fetchStats = async () => {
  try {
    statsLoading.value = true;

    // Single API call for all statistics
    const response = await http.get<{ success: boolean; data: StatsResponse }>('/terminal/entries/stats/');
    const data = response.data;

    stats.value = {
      total: data.total || 0,
      onTerminal: data.on_terminal || 0,
      laden: data.laden || 0,
      empty: data.empty || 0,
      enteredToday: data.entered_today || 0,
      exitedToday: data.exited_today || 0,
    };

    // Map company stats from backend response
    companyStats.value = (data.companies || []).map(c => ({
      id: c.company__id,
      name: c.company__name,
      slug: c.company__slug,
      count: c.count,
      laden: c.laden,
      empty: c.empty,
    }));

  } catch (error) {
    console.error('Failed to fetch stats:', error);
  } finally {
    statsLoading.value = false;
  }
};

const dataSource = ref<ContainerRecord[]>([]);
const loading = ref(false);
const currentFilters = ref<Record<string, any>>({});
const activeStatusTab = ref('all');

// Clickable stat filter state
const activeStatFilter = ref<string | null>(null);
const activeCompanyFilter = ref<number | null>(null);
const statFilters = ref<Record<string, any>>({});

// Sorting state
const currentSorter = ref<{ field: string | null; order: 'ascend' | 'descend' | null }>({
  field: 'entryTime',
  order: 'descend',
});

// Watch for sort changes and save to localStorage
watch(currentSorter, (sorter) => {
  if (sorter.field) {
    localStorage.setItem('container_columns_sort', JSON.stringify(sorter));
  }
}, { deep: true });

// Map frontend column keys to backend field names
const sortFieldMap: Record<string, string> = {
  'container': 'container__container_number',
  'isoType': 'container__iso_type',
  'containerStatus': 'status',
  'entryTime': 'entry_time',
  'exitDate': 'exit_date',
  'transportType': 'transport_type',
  'dwellTimeDays': 'dwell_time_days',
  'cargoWeight': 'cargo_weight',
  'created': 'created_at',
};

// Global Search State
const globalSearch = ref('');

// Row Selection State
const selectedRowKeys = ref<number[]>([]);
const selectedRows = ref<ContainerRecord[]>([]);

// Row Selection Computed
const rowSelection = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys: number[], rows: ContainerRecord[]) => {
    selectedRowKeys.value = keys;
    selectedRows.value = rows;
  },
}));

// Bulk Export Selected
const exportSelected = async () => {
  if (selectedRowKeys.value.length === 0) return;

  try {
    const containerIds = selectedRowKeys.value.join(',');
    window.open(`/api/terminal/entries/export_excel/?container_ids=${containerIds}`);
    message.success(`Экспорт ${selectedRowKeys.value.length} контейнеров`);
  } catch (error) {
    message.error('Ошибка при экспорте');
  }
};

// Bulk Delete Selected
const deleteSelected = async () => {
  if (selectedRowKeys.value.length === 0) return;

  try {
    await Promise.all(
      selectedRowKeys.value.map(id => http.delete(`/terminal/entries/${id}/`))
    );
    message.success(`Удалено ${selectedRowKeys.value.length} контейнеров`);
    selectedRowKeys.value = [];
    fetchStats();
    fetchContainers(currentFilters.value, pagination.value.current, pagination.value.pageSize);
  } catch (error) {
    message.error('Ошибка при удалении');
  }
};

// Clear Selection
const clearSelection = () => {
  selectedRowKeys.value = [];
  selectedRows.value = [];
};

// Keyboard Shortcuts Handler
const handleKeyboardShortcuts = (e: KeyboardEvent) => {
  // Ctrl/Cmd + F - Focus search
  if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
    e.preventDefault();
    // Focus will be handled by ref if we add it
  }

  // Ctrl/Cmd + R - Refresh data
  if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
    e.preventDefault();
    fetchContainers(currentFilters.value, pagination.value.current, pagination.value.pageSize);
    fetchStats();
  }

  // Escape - Clear search and filters
  if (e.key === 'Escape') {
    if (globalSearch.value) {
      globalSearch.value = '';
      handleGlobalSearch();
    }
    if (dateRange.value) {
      dateRange.value = null;
      handleDateRangeChange();
    }
  }
};

// Register keyboard shortcuts
onMounted(() => {
  window.addEventListener('keydown', handleKeyboardShortcuts);

  // Load saved column preferences from localStorage
  try {
    const savedVisibility = localStorage.getItem('container_columns_visible');
    if (savedVisibility) {
      const parsed = JSON.parse(savedVisibility);
      if (Array.isArray(parsed) && parsed.length > 0) {
        visibleColumnKeys.value = parsed;
      }
    }

    const savedSort = localStorage.getItem('container_columns_sort');
    if (savedSort) {
      const parsed = JSON.parse(savedSort);
      if (parsed && parsed.field) {
        currentSorter.value = { field: parsed.field, order: parsed.order };
      }
    }
  } catch (e) {
    console.error('Failed to load column preferences:', e);
  }
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyboardShortcuts);
  stopAutoRefresh();
});

// Auto-Refresh State
const autoRefreshEnabled = ref(false);
const autoRefreshInterval = ref(30);
let refreshTimer: number | null = null;

// Auto-Refresh Handlers
const startAutoRefresh = () => {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = window.setInterval(() => {
    fetchContainers(currentFilters.value, pagination.value.current, pagination.value.pageSize);
    fetchStats();
  }, autoRefreshInterval.value * 1000);
};

const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
};

watch(autoRefreshEnabled, (enabled) => {
  if (enabled) startAutoRefresh();
  else stopAutoRefresh();
});

watch(autoRefreshInterval, () => {
  if (autoRefreshEnabled.value) {
    stopAutoRefresh();
    startAutoRefresh();
  }
});

// Date Range Filter State
const dateRange = ref<[Dayjs, Dayjs] | null>(null);

// Date Range Handler
const handleDateRangeChange = () => {
  if (!dateRange.value || !dateRange.value[0] || !dateRange.value[1]) {
    // Clear date filter
    delete currentFilters.value.entry_date_after;
    delete currentFilters.value.entry_date_before;
  } else {
    currentFilters.value.entry_date_after = dateRange.value[0].format('YYYY-MM-DD');
    currentFilters.value.entry_date_before = dateRange.value[1].format('YYYY-MM-DD');
  }
  pagination.value.current = 1;
  fetchContainers(currentFilters.value, 1, pagination.value.pageSize);
};

// Global Search Handler
const handleGlobalSearch = async () => {
  pagination.value.current = 1;

  if (!globalSearch.value.trim()) {
    // Clear search - reset to normal
    fetchContainers(currentFilters.value, 1, pagination.value.pageSize);
    return;
  }

  loading.value = true;
  try {
    const apiFilters = { ...currentFilters.value, search_text: globalSearch.value };
    const { data, total } = await terminalService.getContainers(apiFilters, 1, pagination.value.pageSize);

    dataSource.value = transformEntries(data);

    pagination.value.total = total;
    pagination.value.current = 1;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка поиска');
  } finally {
    loading.value = false;
  }
};

// Debounced search (300ms delay)
const debouncedSearch = debounce(handleGlobalSearch, 300);

const pagination = ref({
  current: 1,
  pageSize: 25,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '25', '50', '100'],
});

// Companies for dropdown filter
const companies = ref<{ id: number; name: string; slug: string }[]>([]);
const companiesLoading = ref(false);

const fetchCompanies = async () => {
  try {
    companiesLoading.value = true;
    const response = await http.get<{ results: { id: number; name: string; slug: string }[] }>('/auth/companies/');
    companies.value = response.results || [];
  } catch (error) {
    console.error('Failed to fetch companies:', error);
  } finally {
    companiesLoading.value = false;
  }
};

const filesModalVisible = ref(false);
const selectedFiles = ref<FileAttachment[]>([]);
const selectedContainer = ref('');
const selectedContainerId = ref<number>();
const selectedContainerIsoType = ref('');
const selectedStatus = ref('');
const selectedTransportType = ref('');
const selectedEntryTrainNumber = ref('');
const selectedTransportNumber = ref('');
const selectedExitDate = ref('');
const selectedExitTransportType = ref('');
const selectedExitTrainNumber = ref('');
const selectedExitTransportNumber = ref('');
const selectedDestinationStation = ref('');
const selectedLocation = ref('');
const selectedAdditionalCraneOperationDate = ref('');
const selectedCraneOperations = ref<CraneOperation[]>([]);
const selectedNote = ref('');
const selectedCargoWeight = ref<number>();
const selectedCargoName = ref('');
const selectedCompanyId = ref<number>();
const selectedContainerOwner = ref('');
const selectedContainerOwnerId = ref<number>();

const createModalVisible = ref(false);
const editModalVisible = ref(false);
const excelUploadModalVisible = ref(false);
const excelExportModalVisible = ref(false);

const fetchContainers = async (filters?: Record<string, any>, page?: number, pageSize?: number) => {
  try {
    loading.value = true;
    const apiFilters: Record<string, any> = {};

    // Map frontend filter keys to API query parameters
    if (filters?.container && filters.container.length > 0) {
      apiFilters.container_number = filters.container[0];
    }
    
    if (filters?.isoType) {
      apiFilters.container_iso_type = filters.isoType;
    }
    // Apply status filter based on active tab
    if (activeStatusTab.value !== 'all') {
      apiFilters.status = activeStatusTab.value;
    }
    if (filters?.companyName && filters.companyName.length > 0) {
      apiFilters.company_id = filters.companyName[0];
    }
    if (filters?.containerOwner && filters.containerOwner.length > 0) {
      apiFilters.container_owner = filters.containerOwner[0];
    }
    if (filters?.cargoName && filters.cargoName.length > 0) {
      apiFilters.cargo_name = filters.cargoName[0];
    }
    if (filters?.entryTime && filters.entryTime.length > 0) {
      apiFilters.entry_time = filters.entryTime[0];
    }
    if (filters?.transportType) {
      apiFilters.transport_type = filters.transportType[0];
    }
    if (filters?.entryTrainNumber && filters.entryTrainNumber.length > 0) {
      apiFilters.entry_train_number = filters.entryTrainNumber[0];
    }
    if (filters?.transportNumber && filters.transportNumber.length > 0) {
      apiFilters.transport_number = filters.transportNumber[0];
    }
    if (filters?.exitDate && filters.exitDate.length > 0) {
      apiFilters.exit_date = filters.exitDate[0];
    }
    if (filters?.exitTransportType && filters.exitTransportType.length > 0) {
      apiFilters.exit_transport_type = filters.exitTransportType[0];
    }
    if (filters?.exitTrainNumber && filters.exitTrainNumber.length > 0) {
      apiFilters.exit_train_number = filters.exitTrainNumber[0];
    }
    if (filters?.exitTransportNumber && filters.exitTransportNumber.length > 0) {
      apiFilters.exit_transport_number = filters.exitTransportNumber[0];
    }
    if (filters?.destinationStation && filters.destinationStation.length > 0) {
      apiFilters.destination_station = filters.destinationStation[0];
    }
    if (filters?.location && filters.location.length > 0) {
      apiFilters.location = filters.location[0];
    }
    if (filters?.additionalCraneOperationDate && filters.additionalCraneOperationDate.length > 0) {
      apiFilters.additional_crane_operation_date = filters.additionalCraneOperationDate[0];
    }
    if (filters?.note && filters.note.length > 0) {
      apiFilters.note = filters.note[0];
    }
    if (filters?.dwellTimeDays && filters.dwellTimeDays.length > 0) {
      // Use range filter with same min/max for exact match
      const days = filters.dwellTimeDays[0];
      apiFilters.dwell_time_range = `${days}-${days}`;
    }
    if (filters?.cargoWeight && filters.cargoWeight.length > 0) {
      apiFilters.cargo_weight = filters.cargoWeight[0];
    }

    // Apply stat card filters (clickable statistics)
    if (statFilters.value.has_exited !== undefined) {
      apiFilters.has_exited = statFilters.value.has_exited;
    }
    if (statFilters.value.status) {
      apiFilters.status = statFilters.value.status;
    }
    if (statFilters.value.exit_date_after) {
      apiFilters.exit_date_after = statFilters.value.exit_date_after;
    }
    if (statFilters.value.entry_date_after) {
      apiFilters.entry_date_after = statFilters.value.entry_date_after;
    }
    if (statFilters.value.company) {
      apiFilters.company_id = statFilters.value.company;
    }

    // Add sorting parameter
    if (currentSorter.value.field && currentSorter.value.order) {
      const backendField = sortFieldMap[currentSorter.value.field] || currentSorter.value.field;
      const prefix = currentSorter.value.order === 'descend' ? '-' : '';
      apiFilters.ordering = `${prefix}${backendField}`;
    }

    const currentPage = page || pagination.value.current;
    const currentPageSize = pageSize || pagination.value.pageSize;

    const { data, total } = await terminalService.getContainers(apiFilters, currentPage, currentPageSize);

    dataSource.value = transformEntries(data);

    pagination.value.total = total;
    pagination.value.current = currentPage;
    pagination.value.pageSize = currentPageSize;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка загрузки данных');
  } finally {
    loading.value = false;
  }
};

const handleTableChange = (pag: any, filters: any, sorter: any) => {
  currentFilters.value = filters;

  // Handle sorter
  if (!Array.isArray(sorter) && sorter.field) {
    currentSorter.value.field = sorter.field as string;
    currentSorter.value.order = sorter.order || null;
  } else if (!Array.isArray(sorter) && !sorter.field) {
    // Sorter cleared (e.g., clicking different filter)
    currentSorter.value.field = 'entryTime';
    currentSorter.value.order = 'descend';
  }

  fetchContainers(filters, pag.current, pag.pageSize);
};

const handleStatusTabChange = () => {
  // Reset to first page when changing status tab
  pagination.value.current = 1;
  fetchContainers(currentFilters.value, 1, pagination.value.pageSize);
};

// Stat card click handlers
const handleStatClick = (statType: string) => {
  const today = new Date().toISOString().split('T')[0];

  // Toggle off if clicking same filter
  if (activeStatFilter.value === statType) {
    activeStatFilter.value = null;
    activeCompanyFilter.value = null;
    statFilters.value = {};
    fetchContainers(currentFilters.value, 1, pagination.value.pageSize);
    return;
  }

  activeStatFilter.value = statType;
  activeCompanyFilter.value = null;

  const filterMap: Record<string, Record<string, any>> = {
    'onTerminal': { has_exited: false },
    'laden': { status: 'Гружёный', has_exited: false },
    'empty': { status: 'Порожний', has_exited: false },
    'exitedToday': { exit_date_after: today },
    'enteredToday': { entry_date_after: today },
    'total': {}, // Clear all filters
  };

  statFilters.value = filterMap[statType] || {};
  pagination.value.current = 1;
  fetchContainers(currentFilters.value, 1, pagination.value.pageSize);
};

const handleCompanyChipClick = (companyId: number) => {
  // Toggle off if clicking same company
  if (activeCompanyFilter.value === companyId) {
    activeCompanyFilter.value = null;
    activeStatFilter.value = null;
    statFilters.value = {};
    fetchContainers(currentFilters.value, 1, pagination.value.pageSize);
    return;
  }

  activeCompanyFilter.value = companyId;
  activeStatFilter.value = null;
  statFilters.value = { company: companyId, has_exited: false };
  pagination.value.current = 1;
  fetchContainers(currentFilters.value, 1, pagination.value.pageSize);
};

const showFiles = (record: ContainerRecord) => {
  selectedFiles.value = record.filesData;
  selectedContainer.value = record.container;
  selectedContainerId.value = record.containerId;
  selectedContainerIsoType.value = record.isoType;
  selectedStatus.value = record.status;
  selectedTransportType.value = record.transportType;
  selectedEntryTrainNumber.value = record.entryTrainNumber || '';
  selectedTransportNumber.value = record.transportNumber;
  selectedExitDate.value = record.exitDate || '';
  selectedExitTransportType.value = record.exitTransportType || '';
  selectedExitTrainNumber.value = record.exitTrainNumber || '';
  selectedExitTransportNumber.value = record.exitTransportNumber || '';
  selectedDestinationStation.value = record.destinationStation || '';
  selectedLocation.value = record.location || '';
  selectedAdditionalCraneOperationDate.value = record.additionalCraneOperationDate || '';
  selectedCraneOperations.value = record.craneOperations || [];
  selectedNote.value = record.note || '';
  selectedCargoWeight.value = record.cargoWeight;
  selectedCargoName.value = record.cargoName || '';
  selectedCompanyId.value = record.companyId;
  selectedContainerOwner.value = record.containerOwner || '';
  selectedContainerOwnerId.value = record.containerOwnerId;
  filesModalVisible.value = true;
};

const handleUploadSuccess = () => {
  fetchContainers(currentFilters.value, pagination.value.current, pagination.value.pageSize);
};

const handleRefreshFiles = async () => {
  if (!selectedContainerId.value) return;

  try {
    const entry = await terminalService.getContainerById(selectedContainerId.value);
    selectedFiles.value = entry.files;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка обновления файлов');
  }
};

const showCreateModal = () => {
  createModalVisible.value = true;
};

const handleCreateSuccess = () => {
  fetchStats();
  fetchContainers(currentFilters.value, pagination.value.current, pagination.value.pageSize);
};

const showEditModal = (record: ContainerRecord) => {
  selectedContainerId.value = record.containerId;
  selectedContainer.value = record.container;
  selectedContainerIsoType.value = record.isoType;
  selectedStatus.value = record.status;
  selectedTransportType.value = record.transportType;
  selectedEntryTrainNumber.value = record.entryTrainNumber || '';
  selectedTransportNumber.value = record.transportNumber;
  selectedExitDate.value = record.exitDate || '';
  selectedExitTransportType.value = record.exitTransportType || '';
  selectedExitTrainNumber.value = record.exitTrainNumber || '';
  selectedExitTransportNumber.value = record.exitTransportNumber || '';
  selectedDestinationStation.value = record.destinationStation || '';
  selectedLocation.value = record.location || '';
  selectedAdditionalCraneOperationDate.value = record.additionalCraneOperationDate || '';
  selectedCraneOperations.value = record.craneOperations || [];
  selectedNote.value = record.note || '';
  selectedCargoWeight.value = record.cargoWeight;
  selectedCargoName.value = record.cargoName || '';
  selectedCompanyId.value = record.companyId;
  selectedContainerOwner.value = record.containerOwner || '';
  selectedContainerOwnerId.value = record.containerOwnerId;
  editModalVisible.value = true;
};

const handleEditSuccess = () => {
  fetchStats();
  fetchContainers(currentFilters.value, pagination.value.current, pagination.value.pageSize);
};

const showDeleteConfirm = (record: ContainerRecord) => {
  Modal.confirm({
    title: 'Удалить контейнер?',
    content: `Вы уверены, что хотите удалить контейнер ${record.container}?`,
    okText: 'Удалить',
    okType: 'danger',
    cancelText: 'Отмена',
    maskClosable: true,
    async onOk() {
      await handleDelete(record.containerId);
    },
  });
};

const handleDelete = async (containerId: number) => {
  try {
    await http.delete(`/terminal/entries/${containerId}/`);

    message.success('Контейнер успешно удалён');
    fetchStats();
    fetchContainers(currentFilters.value, pagination.value.current, pagination.value.pageSize);
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка при удалении контейнера');
  }
};

const showExcelUploadModal = () => {
  excelUploadModalVisible.value = true;
};

const handleExcelUploadSuccess = () => {
  fetchContainers(currentFilters.value, pagination.value.current, pagination.value.pageSize);
};

const showExportModal = () => {
  excelExportModalVisible.value = true;
};


onMounted(() => {
  fetchStats();
  fetchContainers();
  fetchCompanies();
});
</script>

<style scoped>
/* Container Page */
.container-page {
  width: 100%;
}

/* Active state for clickable stat cards */
.stat-card-active {
  border-color: #1677ff !important;
  background: #f0f7ff !important;
}

/* Main Table Card */
.main-table-card {
  border-radius: 4px;
}

/* Utility Classes */
.text-muted {
  color: #bfbfbf;
}

.company-link {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #1677ff;
  cursor: pointer;
}

.company-link:hover {
  color: #4096ff;
  text-decoration: underline;
}
</style>
