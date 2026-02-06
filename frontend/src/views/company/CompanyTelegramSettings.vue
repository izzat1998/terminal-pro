<template>
  <a-card :bordered="false" :loading="loading">
    <template #title>Настройки Telegram</template>

    <a-form
      v-if="company"
      :model="formState"
      :label-col="{ span: 6 }"
      :wrapper-col="{ span: 14 }"
      layout="horizontal"
    >
      <a-form-item label="Уведомления">
        <a-switch
          v-model:checked="formState.notifications_enabled"
          checked-children="Вкл"
          un-checked-children="Выкл"
        />
      </a-form-item>

      <a-form-item label="Telegram группа" :required="formState.notifications_enabled">
        <a-input
          v-model:value="formState.telegram_group_id"
          placeholder="@mygroup или -1001234567890"
          :disabled="!formState.notifications_enabled"
        />
        <div class="field-hint">
          <div><b>Вариант 1:</b> Username публичной группы (например: @mygroup)</div>
          <div><b>Вариант 2:</b> ID группы (для приватных групп). Добавьте @RawDataBot в группу чтобы узнать ID</div>
        </div>
      </a-form-item>

      <a-form-item label="Название группы">
        <a-input
          v-model:value="formState.telegram_group_name"
          placeholder="Название для отображения"
          :disabled="!formState.notifications_enabled"
        />
      </a-form-item>

      <a-form-item :wrapper-col="{ offset: 6, span: 14 }">
        <a-space>
          <a-button type="primary" :loading="saveLoading" @click="handleSave">
            <SaveOutlined />
            Сохранить
          </a-button>
          <a-button @click="handleReset">Сбросить</a-button>
        </a-space>
      </a-form-item>
    </a-form>
  </a-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { message } from 'ant-design-vue';
import { SaveOutlined } from '@ant-design/icons-vue';
import { http } from '../../utils/httpClient';
import type { Company } from '../../types/company';

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  updated: [company: Company];
}>();

const formState = ref({
  notifications_enabled: false,
  telegram_group_id: '',
  telegram_group_name: '',
});

const saveLoading = ref(false);

watch(() => props.company, (c) => {
  if (c) {
    formState.value = {
      notifications_enabled: c.notifications_enabled,
      telegram_group_id: c.telegram_group_id || '',
      telegram_group_name: c.telegram_group_name || '',
    };
  }
}, { immediate: true });

const handleSave = async () => {
  if (formState.value.notifications_enabled && !formState.value.telegram_group_id.trim()) {
    message.error('Введите Telegram Group ID для включения уведомлений');
    return;
  }
  if (!props.company) return;

  saveLoading.value = true;
  try {
    const result = await http.patch<{ success: boolean; data: Company; error?: { message: string } }>(
      `/auth/companies/${props.company.slug}/`,
      {
        notifications_enabled: formState.value.notifications_enabled,
        telegram_group_id: formState.value.telegram_group_id.trim() || null,
        telegram_group_name: formState.value.telegram_group_name.trim(),
      },
    );
    if (result.success) {
      message.success('Настройки Telegram сохранены');
      emit('updated', result.data);
    } else {
      message.error(result.error?.message || 'Ошибка сохранения');
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка сохранения');
  } finally {
    saveLoading.value = false;
  }
};

const handleReset = () => {
  if (props.company) {
    formState.value = {
      notifications_enabled: props.company.notifications_enabled,
      telegram_group_id: props.company.telegram_group_id || '',
      telegram_group_name: props.company.telegram_group_name || '',
    };
  }
};
</script>

<style scoped>
.field-hint {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}
</style>
