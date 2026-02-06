<template>
  <a-modal
    v-model:open="visible"
    :title="containerNumber"
    :footer="null"
    :width="900"
    :style="{ top: '20px' }"
    @cancel="handleClose"
  >
    <div style="margin-bottom: 16px;">
      <a-upload
        :file-list="fileList"
        :before-upload="beforeUpload"
        :custom-request="handleUpload"
        :show-upload-list="false"
        accept="image/*"
      >
        <a-button type="primary">
          <template #icon><UploadOutlined /></template>
          Загрузить изображение
        </a-button>
      </a-upload>
    </div>
    <a-table
      v-if="files.length > 0"
      :columns="fileColumns"
      :data-source="files"
      :pagination="false"
      :row-key="(record: FileAttachment) => record.attachment_id"
      :scroll="{ x: 600 }"
      bordered
      :row-class-name="(_record: FileAttachment, index: number) => index % 2 === 1 ? 'table-striped' : ''"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'preview'">
          <img
            v-if="record.file.mime_type?.startsWith('image/')"
            :src="record.file.file_url"
            :alt="record.file.original_filename"
            style="width: 80px; height: 80px; object-fit: cover; cursor: pointer;"
            @click="openFile(record.file.file_url)"
          />
          <div v-else style="width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; background: #f0f0f0;">
            <FileOutlined style="font-size: 32px; color: #999;" />
          </div>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-button type="primary" size="small" @click="downloadFile(record.file.file_url, record.file.original_filename)">
              <template #icon><DownloadOutlined /></template>
            </a-button>
            <a-button type="primary" size="small" danger @click="showDeleteFileConfirm(record)">
              <template #icon><DeleteOutlined /></template>
            </a-button>
          </a-space>
        </template>
      </template>
    </a-table>
    <a-empty v-else description="Нет файлов" />
  </a-modal>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { message, Modal } from 'ant-design-vue';
import { FileOutlined, DownloadOutlined, UploadOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import type { FileAttachment } from '../services/terminalService';
import { http } from '../utils/httpClient';
import { downloadBlob } from '../utils/download';
import { getStorageItem } from '../utils/storage';
import { useModalVisibility } from '../composables/useModalVisibility';

interface Props {
  open: boolean;
  files: FileAttachment[];
  containerNumber: string;
  containerId?: number;
  containerIsoType?: string;
  status?: string;
  transportType?: string;
  entryTrainNumber?: string;
  transportNumber?: string;
  exitDate?: string;
  exitTransportType?: string;
  exitTrainNumber?: string;
  exitTransportNumber?: string;
  destinationStation?: string;
  location?: string;
  additionalCraneOperationDate?: string;
  note?: string;
  cargoWeight?: number;
  cargoName?: string;
  companyId?: number;
  containerOwnerId?: number;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'upload-success'): void;
  (e: 'refresh-files'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const fileList = ref([]);

const visible = useModalVisibility(props, emit);

const fileColumns = [
  {
    title: 'Предпросмотр',
    key: 'preview',
    width: 160,
    align: 'center' as const,
    fixed: 'left' as const,
  },
  {
    title: 'Имя файла',
    dataIndex: ['file', 'original_filename'],
    key: 'filename',
    width: 400,
    ellipsis: true,
    align: 'center' as const,
  },
  {
    title: 'Размер',
    dataIndex: ['file', 'size_mb'],
    key: 'size',
    width: 100,
    customRender: ({ text }: { text: number }) => `${text} MB`,
    responsive: ['md'] as any,
    align: 'center' as const, 
  },
  {
    title: 'Действия',
    key: 'actions',
    width: 100,
    align: 'center' as const,
    fixed: 'right' as const,
  },
];

const handleClose = () => {
  visible.value = false;
};

const authenticatedFetch = async (url: string): Promise<Response> => {
  const token = getStorageItem('access_token');
  const response = await fetch(url, {
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response;
};

const openFile = async (url: string) => {
  try {
    const response = await authenticatedFetch(url);
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    window.open(objectUrl, '_blank');
    // Revoke after a delay to allow the new tab to load
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
  } catch {
    message.error('Ошибка при открытии файла');
  }
};

const downloadFile = async (url: string, filename: string) => {
  try {
    const response = await authenticatedFetch(url);
    const blob = await response.blob();
    downloadBlob(blob, filename);
  } catch {
    message.error('Ошибка при скачивании файла');
  }
};

const beforeUpload = (file: File) => {
  const isImage = file.type.startsWith('image/');
  if (!isImage) {
    message.error('Можно загружать только изображения!');
    return false;
  }
  const isLt5M = file.size / 1024 / 1024 < 5;
  if (!isLt5M) {
    message.error('Размер изображения не должен превышать 5MB!');
    return false;
  }
  return true;
};

const handleUpload = async (options: { file: File; onSuccess?: (body: unknown) => void; onError?: (err: Error) => void }) => {
  const { file, onSuccess, onError } = options;

  if (!props.containerId) {
    message.error('Не указан ID контейнера');
    onError(new Error('Container ID not provided'));
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('container_number', props.containerNumber);
  formData.append('container_iso_type', props.containerIsoType || '');
  formData.append('status', props.status || '');
  formData.append('transport_type', props.transportType || '');
  formData.append('entry_train_number', props.entryTrainNumber || '');
  formData.append('transport_number', props.transportNumber || '');
  formData.append('exit_date', props.exitDate || '');
  formData.append('exit_transport_type', props.exitTransportType || '');
  formData.append('exit_train_number', props.exitTrainNumber || '');
  formData.append('exit_transport_number', props.exitTransportNumber || '');
  formData.append('destination_station', props.destinationStation || '');
  formData.append('location', props.location || '');
  formData.append('additional_crane_operation_date', props.additionalCraneOperationDate || '');
  formData.append('note', props.note || '');
  formData.append('cargo_weight', props.cargoWeight?.toString() || '');
  formData.append('cargo_name', props.cargoName || '');
  formData.append('company_id', props.companyId?.toString() || '');
  formData.append('container_owner', props.containerOwnerId?.toString() || '');

  try {
    await http.upload(`/terminal/entries/${props.containerId}/upload-file/`, formData);

    message.success('Изображение успешно загружено');
    onSuccess({});
    emit('upload-success');
    emit('refresh-files');
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка при загрузке файла');
    onError(error);
  }
};

const showDeleteFileConfirm = (record: FileAttachment) => {
  Modal.confirm({
    title: 'Удалить файл?',
    content: `Вы уверены, что хотите удалить файл ...${record.file.original_filename.slice(-15)}?`,
    okText: 'Удалить',
    okType: 'danger',
    cancelText: 'Отмена',
    maskClosable: true,
    async onOk() {
      await handleDeleteFile(record.attachment_id);
    },
  });
};

const handleDeleteFile = async (attachmentId: number) => {
  if (!props.containerId) {
    message.error('Не указан ID контейнера');
    return;
  }

  try {
    await http.delete(`/terminal/entries/${props.containerId}/remove-file/${attachmentId}/`);

    message.success('Файл успешно удалён');
    emit('upload-success');
    emit('refresh-files');
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка при удалении файла');
  }
};
</script>

<style scoped>
:deep(.ant-modal) {
  max-width: calc(100vw - 32px);
}

@media (max-width: 768px) {
  :deep(.ant-modal) {
    max-width: 100vw;
    margin: 0;
  }
}
</style>
