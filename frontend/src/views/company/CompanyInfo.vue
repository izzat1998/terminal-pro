<template>
  <a-card :bordered="false" class="content-card" :loading="loading">
    <template #title>
      <a-space>
        <a-button type="link" @click="goBack" class="back-button">
          <ArrowLeftOutlined />
          Назад к списку
        </a-button>
      </a-space>
    </template>
    <template #extra>
      <a-space>
        <a-button type="primary" @click="handleEdit">
          <EditOutlined />
          Редактировать
        </a-button>
      </a-space>
    </template>

    <a-descriptions bordered :column="{ xxl: 2, xl: 2, lg: 2, md: 1, sm: 1, xs: 1 }">
      <a-descriptions-item label="ID">{{ company?.id }}</a-descriptions-item>
      <a-descriptions-item label="Название">{{ company?.name }}</a-descriptions-item>
      <a-descriptions-item label="Slug">{{ company?.slug }}</a-descriptions-item>
      <a-descriptions-item label="Статус">
        <a-tag :color="company?.is_active ? 'green' : 'red'">
          {{ company?.is_active ? 'Активна' : 'Неактивна' }}
        </a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="Дата создания">
        {{ company?.created_at ? formatDateTime(company.created_at) : '' }}
      </a-descriptions-item>
      <a-descriptions-item label="Дата обновления">
        {{ company?.updated_at ? formatDateTime(company.updated_at) : '' }}
      </a-descriptions-item>
    </a-descriptions>
  </a-card>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import { ArrowLeftOutlined, EditOutlined } from '@ant-design/icons-vue';
import { formatDateTime } from '../../utils/dateFormat';

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const router = useRouter();

const goBack = () => {
  router.push('/accounts/companies');
};

const handleEdit = () => {
  message.info('Функция редактирования в разработке');
};
</script>

<style scoped>
.content-card {
  border-radius: 2px;
}

.back-button {
  padding-left: 0;
  color: rgba(0, 0, 0, 0.65);
}

.back-button:hover {
  color: #1890ff;
}
</style>
