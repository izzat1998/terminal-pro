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

    <a-card :bordered="false" :loading="loading" style="margin-top: 16px">
      <template #title>Договор</template>
      <template #extra>
        <a-tag v-if="hasContract" color="green">Есть</a-tag>
        <a-tag v-else color="default">Не указан</a-tag>
      </template>

      <a-descriptions bordered :column="1">
        <a-descriptions-item label="Номер договора">
          {{ company?.contract_number || '—' }}
        </a-descriptions-item>
        <a-descriptions-item label="Дата договора">
          {{ company?.contract_date ? formatDate(company.contract_date) : '—' }}
        </a-descriptions-item>
        <a-descriptions-item label="Срок действия">
          <template v-if="company?.contract_expires">
            {{ formatDate(company.contract_expires) }}
            <a-tag v-if="isExpired" color="red" style="margin-left: 8px">Истёк</a-tag>
            <a-tag v-else color="green" style="margin-left: 8px">Действует</a-tag>
          </template>
          <template v-else>Бессрочный</template>
        </a-descriptions-item>
        <a-descriptions-item label="Файл договора">
          <a v-if="company?.contract_file" :href="company.contract_file" target="_blank" rel="noopener">
            Скачать
          </a>
          <span v-else style="color: rgba(0,0,0,0.25)">Не загружен</span>
        </a-descriptions-item>
      </a-descriptions>
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

const hasContract = computed(() => !!props.company?.contract_number);

const isExpired = computed(() => {
  if (!props.company?.contract_expires) return false;
  return new Date(props.company.contract_expires) < new Date();
});

const formatDate = (dateStr: string): string => {
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
};
</script>
