<template>
  <div>
    <a-card :bordered="false" :loading="loading">
      <template #title>Общая информация</template>

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

    <a-card :bordered="false" :loading="loading" style="margin-top: 16px">
      <template #title>Юридические реквизиты</template>
      <template #extra>
        <a-tag v-if="hasCredentials" color="green">Заполнены</a-tag>
        <a-tag v-else color="orange">Не заполнены</a-tag>
      </template>

      <a-descriptions bordered :column="1">
        <a-descriptions-item label="Юридический адрес">
          {{ company?.legal_address || '—' }}
        </a-descriptions-item>
        <a-descriptions-item label="ИНН">
          {{ company?.inn || '—' }}
        </a-descriptions-item>
        <a-descriptions-item label="МФО">
          {{ company?.mfo || '—' }}
        </a-descriptions-item>
        <a-descriptions-item label="Расчётный счёт">
          {{ company?.bank_account || '—' }}
        </a-descriptions-item>
        <a-descriptions-item label="Банк">
          {{ company?.bank_name || '—' }}
        </a-descriptions-item>
      </a-descriptions>

      <div style="margin-top: 12px; color: rgba(0,0,0,0.45); font-size: 12px;">
        Эти реквизиты отображаются в счёт-фактурах как данные покупателя.
        Редактировать можно в разделе «Настройки → Общие».
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { formatDateTime } from '../../utils/dateFormat';
import type { Company } from '../../types/company';

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const hasCredentials = computed(() => {
  const c = props.company;
  if (!c) return false;
  return !!(c.legal_address || c.inn || c.bank_account);
});
</script>
