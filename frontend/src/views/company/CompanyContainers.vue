<template>
  <a-card :bordered="false" class="content-card">
    <template #title>
      Контейнеры компании
    </template>

    <a-empty v-if="!loading && entries.length === 0" description="Контейнеры не найдены" />

    <a-table
      v-else
      :columns="columns"
      :data-source="entries"
      :loading="loading"
      :pagination="{ pageSize: 10 }"
      row-key="id"
      :scroll="{ x: 1400 }"
      size="small"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'container_number'">
          <a-tag color="blue">{{ record.container.container_number }}</a-tag>
          <a-tag v-if="record.container.iso_type" style="margin-left: 4px;">
            {{ record.container.iso_type }}
          </a-tag>
        </template>
        <template v-if="column.key === 'status'">
          <a-tag :color="getStatusColor(record.status)">
            {{ record.status }}
          </a-tag>
        </template>
        <template v-if="column.key === 'transport'">
          <div>
            <span class="transport-type">{{ record.transport_type }}</span>
            <span v-if="record.transport_number" class="transport-number">
              {{ record.transport_number }}
            </span>
          </div>
          <div v-if="record.entry_train_number" class="train-number">
            Поезд: {{ record.entry_train_number }}
          </div>
        </template>
        <template v-if="column.key === 'entry_time'">
          {{ formatDateTime(record.entry_time) }}
        </template>
        <template v-if="column.key === 'container_owner'">
          <span v-if="record.container_owner">{{ record.container_owner.name }}</span>
          <span v-else class="text-muted">—</span>
        </template>
        <template v-if="column.key === 'client_name'">
          {{ record.client_name || '—' }}
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
              {{ record.exit_transport_type }}
              <span v-if="record.exit_transport_number">{{ record.exit_transport_number }}</span>
            </div>
          </template>
          <span v-else class="text-muted">—</span>
        </template>
        <template v-if="column.key === 'recorded_by'">
          {{ record.recorded_by?.full_name || '—' }}
        </template>
      </template>
    </a-table>
  </a-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { message } from 'ant-design-vue';
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

interface ContainerOwner {
  id: number;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

interface CraneOperation {
  id: number;
  operation_date: string;
  created_at: string;
}

interface Container {
  id: number;
  container_number: string;
  iso_type: string;
}

interface RecordedBy {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
}

interface ContainerEntry {
  id: number;
  container: Container;
  status: string;
  transport_type: string;
  transport_number: string;
  entry_train_number: string;
  entry_time: string;
  recorded_by: RecordedBy | null;
  client_name: string;
  company: unknown;
  container_owner: ContainerOwner | null;
  cargo_name: string;
  exit_date: string | null;
  exit_transport_type: string | null;
  exit_train_number: string;
  exit_transport_number: string;
  destination_station: string;
  location: string;
  additional_crane_operation_date: string | null;
  crane_operations: CraneOperation[];
  note: string;
  dwell_time_days: number;
  cargo_weight: string;
  created_at: string;
  updated_at: string;
  files: unknown[];
  file_count: number;
  main_file: unknown;
}

const props = defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const entries = ref<ContainerEntry[]>([]);
const loading = ref(false);

const columns = [
  {
    title: 'Контейнер',
    key: 'container_number',
    width: 180,
    fixed: 'left' as const,
  },
  {
    title: 'Статус',
    key: 'status',
    width: 110,
  },
  {
    title: 'Транспорт',
    key: 'transport',
    width: 140,
  },
  {
    title: 'Время въезда',
    key: 'entry_time',
    width: 150,
  },
  {
    title: 'Владелец',
    key: 'container_owner',
    width: 120,
  },
  {
    title: 'Клиент',
    key: 'client_name',
    width: 150,
  },
  {
    title: 'Груз',
    key: 'cargo',
    width: 130,
  },
  {
    title: 'Локация',
    key: 'location',
    width: 90,
  },
  {
    title: 'Простой',
    key: 'dwell_time',
    width: 90,
  },
  {
    title: 'Выезд',
    key: 'exit',
    width: 150,
  },
  {
    title: 'Записал',
    key: 'recorded_by',
    width: 100,
  },
];

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
    'Порожний': 'orange',
    'Гружёный': 'green',
  };
  return colors[status] || 'default';
};

const getDwellTimeColor = (days: number): string => {
  if (days <= 3) return 'green';
  if (days <= 7) return 'orange';
  return 'red';
};

const fetchEntries = async (slug: string) => {
  loading.value = true;
  try {
    const result = await http.get<{ results: ContainerEntry[] }>(`/auth/companies/${slug}/entries/`);
    entries.value = result.results || [];
  } catch (error) {
    console.error('Error fetching entries:', error);
    message.error('Ошибка загрузки контейнеров');
  } finally {
    loading.value = false;
  }
};

watch(() => props.company, (newCompany) => {
  if (newCompany?.slug) {
    fetchEntries(newCompany.slug);
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

.train-number {
  font-size: 12px;
  color: #666;
}

.cargo-weight {
  font-size: 12px;
  color: #666;
}

.exit-transport {
  font-size: 12px;
  color: #666;
}
</style>
