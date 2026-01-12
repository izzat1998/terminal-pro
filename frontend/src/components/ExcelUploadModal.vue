<template>
  <a-modal
    v-model:open="visible"
    title="Импорт данных из Excel"
    :footer="null"
    :width="500"
    @cancel="handleClose"
  >
    <div style="padding: 16px 0;">
      <a-upload
        v-model:file-list="fileList"
        :before-upload="beforeUpload"
        accept=".xlsx,.xls"
        :max-count="1"
        @remove="handleRemove"
      >
        <a-button type="default" block size="large" :disabled="fileList.length >= 1">
          <template #icon><UploadOutlined /></template>
          Выбрать Excel файл
        </a-button>
      </a-upload>
      <div style="margin-top: 16px; color: #666; font-size: 12px;">
        Поддерживаемые форматы: .xlsx, .xls
      </div>
      <div v-if="fileList.length > 0" style="margin-top: 24px;">
        <a-button
          type="primary"
          block
          size="large"
          @click="handleSubmit"
          :loading="uploading"
        >
          Загрузить
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { message } from 'ant-design-vue';
import { UploadOutlined } from '@ant-design/icons-vue';
import { http } from '../utils/httpClient';

interface Props {
  open: boolean;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'upload-success'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const fileList = ref<any[]>([]);
const uploading = ref(false);

const visible = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value),
});

const handleClose = () => {
  visible.value = false;
  fileList.value = [];
  uploading.value = false;
};

const beforeUpload = (file: File) => {
  const isExcel = file.name.endsWith('.xlsx') || file.name.endsWith('.xls');
  if (!isExcel) {
    message.error('Можно загружать только Excel файлы (.xlsx, .xls)!');
    return false;
  }
  const isLt10M = file.size / 1024 / 1024 < 10;
  if (!isLt10M) {
    message.error('Размер файла не должен превышать 10MB!');
    return false;
  }

  // Add file to list but don't upload yet
  fileList.value = [file];
  return false; // Prevent auto upload
};

const handleRemove = () => {
  fileList.value = [];
};

const handleSubmit = async () => {
  if (fileList.value.length === 0) {
    message.error('Выберите файл для загрузки');
    return;
  }

  // Extract the actual File object from Ant Design's file wrapper
  const fileWrapper = fileList.value[0];
  const file = fileWrapper.originFileObj || fileWrapper;

  if (!(file instanceof File)) {
    message.error('Неверный формат файла');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  uploading.value = true;

  try {
    await http.upload('/terminal/entries/import_excel/', formData);

    message.success('Excel файл успешно загружен и обработан');
    emit('upload-success');
    handleClose();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка при загрузке файла');
  } finally {
    uploading.value = false;
  }
};
</script>
