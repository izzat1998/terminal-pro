<template>
  <a-card :bordered="false" class="content-card" :loading="loading">
    <template #title>
      Настройки компании
    </template>

    <a-form
      :model="formState"
      :label-col="{ span: 6 }"
      :wrapper-col="{ span: 14 }"
      layout="vertical"
    >
      <a-form-item label="Название компании">
        <a-input v-model:value="formState.name" placeholder="Введите название" />
      </a-form-item>

      <a-form-item label="Статус">
        <a-switch v-model:checked="formState.is_active" checked-children="Активна" un-checked-children="Неактивна" />
      </a-form-item>

      <a-form-item :wrapper-col="{ offset: 6, span: 14 }">
        <a-space>
          <a-button type="primary" :loading="saveLoading" @click="handleSave">
            <SaveOutlined />
            Сохранить
          </a-button>
          <a-button @click="handleReset">
            Сбросить
          </a-button>
        </a-space>
      </a-form-item>
    </a-form>

    <a-divider />

    <a-typography-title :level="5" type="danger">Опасная зона</a-typography-title>
    <a-space direction="vertical" style="width: 100%">
      <a-alert
        message="Удаление компании"
        description="После удаления компании все данные будут безвозвратно утеряны. Это действие нельзя отменить."
        type="error"
        show-icon
      />
      <a-button danger :loading="deleteLoading" @click="handleDelete">
        <DeleteOutlined />
        Удалить компанию
      </a-button>
    </a-space>
  </a-card>
</template>

<script setup lang="ts">
import { ref, watch, createVNode } from 'vue';
import { useRouter } from 'vue-router';
import { message, Modal } from 'ant-design-vue';
import { SaveOutlined, DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue';
import { http } from '../../utils/httpClient';

const router = useRouter();

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const props = defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'updated', company: Company): void;
}>();

const formState = ref({
  name: '',
  is_active: false,
});

const saveLoading = ref(false);
const deleteLoading = ref(false);

// Update form when company data changes
watch(() => props.company, (newCompany) => {
  if (newCompany) {
    formState.value = {
      name: newCompany.name,
      is_active: newCompany.is_active,
    };
  }
}, { immediate: true });

const handleSave = async () => {
  if (!formState.value.name.trim()) {
    message.warning('Введите название компании');
    return;
  }
  if (!props.company) {
    message.error('Компания не найдена');
    return;
  }

  saveLoading.value = true;
  try {
    const result = await http.put<{ success: boolean; data: Company; error?: { message: string }; message?: string }>(`/auth/companies/${props.company.slug}/`, {
      name: formState.value.name,
      is_active: formState.value.is_active,
    });

    if (result.success) {
      message.success('Компания успешно обновлена');
      emit('updated', result.data);
    } else {
      message.error(result.error?.message || result.message || 'Ошибка обновления компании');
    }
  } catch (error) {
    console.error('Error updating company:', error);
    message.error('Ошибка обновления компании');
  } finally {
    saveLoading.value = false;
  }
};

const handleReset = () => {
  if (props.company) {
    formState.value = {
      name: props.company.name,
      is_active: props.company.is_active,
    };
  }
};

const handleDelete = () => {
  if (!props.company) {
    message.error('Компания не найдена');
    return;
  }

  Modal.confirm({
    title: 'Вы уверены, что хотите удалить компанию?',
    icon: createVNode(ExclamationCircleOutlined),
    content: `Компания "${props.company.name}" будет удалена безвозвратно. Это действие нельзя отменить.`,
    okText: 'Удалить',
    okType: 'danger',
    cancelText: 'Отмена',
    async onOk() {
      deleteLoading.value = true;
      try {
        const result = await http.delete<{ success: boolean; error?: { message: string }; message?: string }>(`/auth/companies/${props.company!.slug}/`);

        if (result.success) {
          message.success('Компания успешно удалена');
          router.push({ name: 'Companies' });
        } else {
          message.error(result.error?.message || result.message || 'Ошибка удаления компании');
        }
      } catch (error) {
        console.error('Error deleting company:', error);
        message.error('Ошибка удаления компании');
      } finally {
        deleteLoading.value = false;
      }
    },
  });
};
</script>

<style scoped>
.content-card {
  border-radius: 2px;
}
</style>
