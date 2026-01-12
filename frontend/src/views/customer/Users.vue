<template>
  <a-card :bordered="false" class="content-card">
    <template #title>
      Пользователи компании
    </template>

    <a-empty v-if="!loading && customers.length === 0" description="Пользователи не найдены" />

    <a-table
      v-else
      :columns="columns"
      :data-source="customers"
      :loading="loading"
      :pagination="{ pageSize: 10 }"
      row-key="id"
      :row-class-name="rowClassName"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'full_name'">
          <a-space>
            <a-avatar size="small">
              {{ record.first_name?.charAt(0)?.toUpperCase() || '?' }}
            </a-avatar>
            {{ record.full_name }}
          </a-space>
        </template>
        <template v-if="column.key === 'phone_number'">
          <a :href="'tel:' + record.phone_number">{{ record.phone_number }}</a>
        </template>
        <template v-if="column.key === 'status'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? 'Активен' : 'Неактивен' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'created_at'">
          {{ formatDate(record.created_at) }}
        </template>
      </template>
    </a-table>
  </a-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { message } from 'ant-design-vue';
import { http } from '../../utils/httpClient';
import { formatDate } from '../../utils/dateFormat';

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface Customer {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone_number: string;
  user_type: string;
  is_active: boolean;
  created_at: string;
}

interface CustomersResponse {
  success: boolean;
  count: number;
  company: {
    id: number;
    name: string;
    slug: string;
  };
  data: Customer[];
}

const props = defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const route = useRoute();
const highlightedUserId = ref<number | null>(null);

const customers = ref<Customer[]>([]);
const loading = ref(false);

const columns = [
  {
    title: 'Имя',
    dataIndex: 'full_name',
    key: 'full_name',
  },
  {
    title: 'Телефон',
    dataIndex: 'phone_number',
    key: 'phone_number',
  },
  {
    title: 'Статус',
    key: 'status',
  },
  {
    title: 'Создан',
    key: 'created_at',
  },
];

const rowClassName = (record: Customer) => {
  return record.id === highlightedUserId.value ? 'highlighted-row' : '';
};

onMounted(() => {
  const userId = route.query.user;
  if (userId) {
    highlightedUserId.value = parseInt(userId as string, 10);
    setTimeout(() => {
      highlightedUserId.value = null;
    }, 5000);
  }
});

const fetchCustomers = async () => {
  loading.value = true;
  try {
    const result = await http.get<CustomersResponse>('/customer/profile/company_members/');
    if (result.success) {
      customers.value = result.data || [];
    } else {
      message.error('Ошибка загрузки пользователей');
    }
  } catch (error) {
    console.error('Error fetching customers:', error);
    message.error('Ошибка загрузки пользователей');
  } finally {
    loading.value = false;
  }
};

watch(() => props.company, (newCompany) => {
  if (newCompany?.slug) {
    fetchCustomers();
  }
}, { immediate: true });
</script>

<style scoped>
.content-card {
  border-radius: 2px;
}

:deep(.highlighted-row) {
  background-color: #e6f7ff !important;
  animation: highlight-pulse 1s ease-in-out 3;
}

@keyframes highlight-pulse {
  0%, 100% {
    background-color: #e6f7ff;
  }
  50% {
    background-color: #bae7ff;
  }
}
</style>
