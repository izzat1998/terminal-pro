<template>
  <a-card :bordered="false" class="content-card">
    <template #title>
      Контейнеры компании
    </template>

    <template #extra>
      <a-space>
        <a-input-search
          v-model:value="searchText"
          placeholder="Поиск по номеру контейнера"
          style="width: 250px"
          allow-clear
        />
      </a-space>
    </template>

    <a-empty v-if="!loading && entries.length === 0 && pagination.total === 0" description="Контейнеры не найдены" />

    <a-table
      v-else
      :columns="columns"
      :data-source="entries"
      :loading="loading"
      :pagination="{
        current: pagination.current,
        pageSize: pagination.pageSize,
        total: pagination.total,
        showSizeChanger: true,
        showTotal: (total: number) => `Всего: ${total}`,
        pageSizeOptions: ['10', '20', '50', '100'],
      }"
      row-key="id"
      :scroll="{ x: 1200 }"
      size="small"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'images'">
          <div v-if="record.images && record.images.length > 0" class="image-cell">
            <a-image-preview-group>
              <a-image
                :src="record.images[0].file_url"
                :width="40"
                :height="40"
                class="thumbnail"
              />
              <template v-for="img in record.images.slice(1)" :key="img.id">
                <a-image
                  :src="img.file_url"
                  :style="{ display: 'none' }"
                />
              </template>
            </a-image-preview-group>
            <a-badge
              v-if="record.images.length > 1"
              :count="record.images.length"
              :number-style="{ backgroundColor: '#1890ff', fontSize: '10px' }"
              class="image-count-badge"
            />
          </div>
          <span v-else class="text-muted">—</span>
        </template>
        <template v-if="column.key === 'container_number'">
          <a-tag color="blue">{{ record.container.container_number }}</a-tag>
          <a-tag v-if="record.container.iso_type" style="margin-left: 4px;">
            {{ record.container.iso_type }}
          </a-tag>
        </template>
        <template v-if="column.key === 'status'">
          <a-tag :color="getStatusColor(record.status)">
            {{ getStatusDisplay(record.status) }}
          </a-tag>
        </template>
        <template v-if="column.key === 'transport'">
          <div>
            <span class="transport-type">{{ getTransportTypeDisplay(record.transport_type) }}</span>
            <span v-if="record.transport_number" class="transport-number">
              {{ record.transport_number }}
            </span>
          </div>
        </template>
        <template v-if="column.key === 'entry_time'">
          {{ formatDateTime(record.entry_time) }}
        </template>
        <template v-if="column.key === 'cargo'">
          <div v-if="record.cargo_name">{{ record.cargo_name }}</div>
          <div v-if="record.cargo_weight" class="cargo-weight">
            {{ formatWeight(record.cargo_weight) }}
          </div>
          <span v-if="!record.cargo_name && !record.cargo_weight" class="text-muted">—</span>
        </template>
        <template v-if="column.key === 'location'">
          <a-tag v-if="record.location" color="purple">{{ record.location }}</a-tag>
          <span v-else class="text-muted">—</span>
        </template>
        <template v-if="column.key === 'dwell_time'">
          <a-tag :color="getDwellTimeColor(record.dwell_time_days)">
            {{ record.dwell_time_days }} дн.
          </a-tag>
        </template>
        <template v-if="column.key === 'exit'">
          <template v-if="record.exit_date">
            <div>{{ formatDateTime(record.exit_date) }}</div>
            <div v-if="record.exit_transport_type" class="exit-transport">
              {{ getTransportTypeDisplay(record.exit_transport_type) }}
              <span v-if="record.exit_transport_number">{{ record.exit_transport_number }}</span>
            </div>
          </template>
          <span v-else class="text-muted">На терминале</span>
        </template>
      </template>
    </a-table>
  </a-card>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';
import { message } from 'ant-design-vue';
import type { TableProps } from 'ant-design-vue';
import { http } from '../../utils/httpClient';
import { formatDateTime } from '../../utils/dateFormat';

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface Container {
  id: number;
  container_number: string;
  iso_type: string;
}

interface CompanyInfo {
  id: number;
  name: string;
  slug: string;
}

interface ContainerImage {
  id: string;
  file_url: string;
  original_filename: string;
  width: number | null;
  height: number | null;
}

interface ContainerEntry {
  id: number;
  container: Container;
  status: 'EMPTY' | 'LADEN';
  transport_type: 'TRUCK' | 'WAGON';
  transport_number: string;
  entry_time: string;
  company: CompanyInfo;
  cargo_name: string;
  exit_date: string | null;
  exit_transport_type: string | null;
  exit_transport_number: string;
  location: string;
  dwell_time_days: number;
  cargo_weight: string | null;
  images: ContainerImage[];
  image_count: number;
}

interface PaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ContainerEntry[];
}

const props = defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const entries = ref<ContainerEntry[]>([]);
const loading = ref(false);
const searchText = ref('');

// Server-side pagination state
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
});

// Server-side filter state
const currentFilters = ref<{
  status: string | null;
  transport_type: string | null;
}>({
  status: null,
  transport_type: null,
});

// Server-side sorter state
const currentSorter = ref<{
  field: string | null;
  order: 'ascend' | 'descend' | null;
}>({
  field: 'entry_time',
  order: 'descend',
});

// Map frontend column keys to backend field names
const sortFieldMap: Record<string, string> = {
  'container_number': 'container__container_number',
  'entry_time': 'entry_time',
  'dwell_time': 'dwell_time_days',
};

// Debounce for search input
let searchTimeout: ReturnType<typeof setTimeout> | null = null;

const debouncedFetch = () => {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    pagination.value.current = 1; // Reset to first page on search
    fetchEntries();
  }, 400);
};

// Cleanup timeout on unmount
onUnmounted(() => {
  if (searchTimeout) clearTimeout(searchTimeout);
});

// Watch search text for debounced server-side search
watch(searchText, debouncedFetch);

const columns: TableProps['columns'] = [
  {
    title: 'Фото',
    key: 'images',
    width: 80,
    fixed: 'left',
  },
  {
    title: 'Контейнер',
    key: 'container_number',
    width: 180,
    sorter: true, // Server-side sorting
  },
  {
    title: 'Статус',
    key: 'status',
    width: 120,
    filters: [
      { text: 'Гружёный', value: 'LADEN' },
      { text: 'Порожний', value: 'EMPTY' },
    ],
  },
  {
    title: 'Транспорт',
    key: 'transport',
    width: 130,
    filters: [
      { text: 'Авто', value: 'TRUCK' },
      { text: 'Ж/Д', value: 'WAGON' },
    ],
  },
  {
    title: 'Въезд',
    key: 'entry_time',
    width: 140,
    sorter: true, // Server-side sorting
    defaultSortOrder: 'descend',
  },
  {
    title: 'Груз',
    key: 'cargo',
    width: 140,
  },
  {
    title: 'Локация',
    key: 'location',
    width: 100,
  },
  {
    title: 'Простой',
    key: 'dwell_time',
    width: 90,
    sorter: true, // Server-side sorting
  },
  {
    title: 'Выезд',
    key: 'exit',
    width: 140,
  },
];

const handleTableChange: TableProps['onChange'] = (pag, filters, sorter) => {
  // Update pagination
  pagination.value.current = pag.current || 1;
  pagination.value.pageSize = pag.pageSize || 10;

  // Update filters
  currentFilters.value.status = (filters.status?.[0] as string) || null;
  currentFilters.value.transport_type = (filters.transport?.[0] as string) || null;

  // Update sorter
  if (!Array.isArray(sorter) && sorter.field) {
    currentSorter.value.field = sorter.field as string;
    currentSorter.value.order = sorter.order || null;
  } else if (!Array.isArray(sorter) && !sorter.field) {
    // Sorter cleared
    currentSorter.value.field = null;
    currentSorter.value.order = null;
  }

  fetchEntries();
};

const formatWeight = (weight: string | number) => {
  const numWeight = typeof weight === 'string' ? parseFloat(weight) : weight;
  if (isNaN(numWeight)) return '—';
  if (numWeight >= 1000) {
    return `${(numWeight / 1000).toFixed(1)} т`;
  }
  return `${numWeight} кг`;
};

const getStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    'EMPTY': 'orange',
    'LADEN': 'green',
  };
  return colors[status] || 'default';
};

const getStatusDisplay = (status: string): string => {
  const display: Record<string, string> = {
    'EMPTY': 'Порожний',
    'LADEN': 'Гружёный',
  };
  return display[status] || status;
};

const getTransportTypeDisplay = (type: string): string => {
  const display: Record<string, string> = {
    'TRUCK': 'Авто',
    'WAGON': 'Ж/Д',
  };
  return display[type] || type;
};

const getDwellTimeColor = (days: number): string => {
  if (days <= 3) return 'green';
  if (days <= 7) return 'orange';
  return 'red';
};

const fetchEntries = async () => {
  loading.value = true;
  try {
    const params = new URLSearchParams();

    // Pagination
    params.append('page', pagination.value.current.toString());
    params.append('page_size', pagination.value.pageSize.toString());

    // Search
    if (searchText.value.trim()) {
      params.append('search_text', searchText.value.trim());
    }

    // Filters
    if (currentFilters.value.status) {
      params.append('status', currentFilters.value.status);
    }
    if (currentFilters.value.transport_type) {
      params.append('transport_type', currentFilters.value.transport_type);
    }

    // Sorting
    if (currentSorter.value.field && currentSorter.value.order) {
      const backendField = sortFieldMap[currentSorter.value.field] || currentSorter.value.field;
      const prefix = currentSorter.value.order === 'descend' ? '-' : '';
      params.append('ordering', prefix + backendField);
    }

    const url = `/customer/containers/?${params.toString()}`;
    const result = await http.get<PaginatedResponse>(url);

    entries.value = result.results || [];
    pagination.value.total = result.count;
  } catch (error) {
    console.error('Error fetching entries:', error);
    message.error(error instanceof Error ? error.message : 'Не удалось загрузить список контейнеров. Попробуйте обновить страницу.');
  } finally {
    loading.value = false;
  }
};

watch(() => props.company, (newCompany) => {
  if (newCompany?.slug) {
    fetchEntries();
  }
}, { immediate: true });
</script>

<style scoped>
.content-card {
  border-radius: 2px;
}

.text-muted {
  color: #999;
}

.transport-type {
  font-weight: 500;
}

.transport-number {
  margin-left: 8px;
  color: #1890ff;
}

.cargo-weight {
  font-size: 12px;
  color: #666;
}

.exit-transport {
  font-size: 12px;
  color: #666;
}

.image-cell {
  display: inline-flex;
  align-items: center;
  position: relative;
}

.thumbnail {
  border-radius: 4px;
  object-fit: cover;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  transition: all 0.2s;
}

.thumbnail:hover {
  border-color: #1890ff;
  transform: scale(1.05);
}

.image-count-badge {
  position: absolute;
  top: -4px;
  right: -8px;
}
</style>
