<template>
  <a-card :bordered="false" :loading="loading">
    <template #title>Общие настройки</template>

    <a-form
      v-if="company"
      :model="formState"
      :label-col="{ span: 6 }"
      :wrapper-col="{ span: 14 }"
      layout="horizontal"
    >
      <a-form-item label="Название компании">
        <a-input v-model:value="formState.name" placeholder="Введите название" />
      </a-form-item>

      <a-form-item label="Статус">
        <a-switch
          v-model:checked="formState.is_active"
          checked-children="Активна"
          un-checked-children="Неактивна"
        />
      </a-form-item>

      <a-divider>Юридические реквизиты</a-divider>

      <a-form-item label="Юр. адрес">
        <a-input v-model:value="formState.legal_address" placeholder="Юридический адрес компании" />
      </a-form-item>

      <a-form-item label="ИНН">
        <a-input v-model:value="formState.inn" placeholder="Идентификационный номер" />
      </a-form-item>

      <a-form-item label="МФО">
        <a-input v-model:value="formState.mfo" placeholder="Код банка (МФО)" />
      </a-form-item>

      <a-form-item label="Расчётный счёт">
        <a-input v-model:value="formState.bank_account" placeholder="Номер расчётного счёта" />
      </a-form-item>

      <a-form-item label="Банк">
        <a-input v-model:value="formState.bank_name" placeholder="Название банка и филиала" />
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
import type { Company } from '../../types/company';

defineOptions({ inheritAttrs: false });

const router = useRouter();

const props = defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  updated: [company: Company];
}>();

const formState = ref({
  name: '',
  is_active: false,
  legal_address: '',
  inn: '',
  mfo: '',
  bank_account: '',
  bank_name: '',
});

const saveLoading = ref(false);
const deleteLoading = ref(false);

const populateForm = (c: Company) => {
  formState.value = {
    name: c.name,
    is_active: c.is_active,
    legal_address: c.legal_address || '',
    inn: c.inn || '',
    mfo: c.mfo || '',
    bank_account: c.bank_account || '',
    bank_name: c.bank_name || '',
  };
};

watch(() => props.company, (c) => {
  if (c) populateForm(c);
}, { immediate: true });

const handleSave = async () => {
  if (!formState.value.name.trim()) {
    message.warning('Введите название компании');
    return;
  }
  if (!props.company) return;

  saveLoading.value = true;
  try {
    const result = await http.put<{ success: boolean; data: Company; error?: { message: string }; message?: string }>(
      `/auth/companies/${props.company.slug}/`,
      formState.value,
    );
    if (result.success) {
      message.success('Компания успешно обновлена');
      emit('updated', result.data);
    } else {
      message.error(result.error?.message || result.message || 'Ошибка обновления компании');
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка обновления компании');
  } finally {
    saveLoading.value = false;
  }
};

const handleReset = () => {
  if (props.company) populateForm(props.company);
};

const handleDelete = () => {
  if (!props.company) return;

  Modal.confirm({
    title: 'Вы уверены, что хотите удалить компанию?',
    icon: createVNode(ExclamationCircleOutlined),
    content: `Компания "${props.company.name}" будет удалена безвозвратно.`,
    okText: 'Удалить',
    okType: 'danger',
    cancelText: 'Отмена',
    async onOk() {
      deleteLoading.value = true;
      try {
        const result = await http.delete<{ success: boolean; error?: { message: string } }>(
          `/auth/companies/${props.company!.slug}/`,
        );
        if (result.success) {
          message.success('Компания успешно удалена');
          router.push({ name: 'Companies' });
        } else {
          message.error(result.error?.message || 'Ошибка удаления компании');
        }
      } catch (error) {
        message.error(error instanceof Error ? error.message : 'Ошибка удаления компании');
      } finally {
        deleteLoading.value = false;
      }
    },
  });
};
</script>
