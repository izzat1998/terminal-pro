<template>
  <a-modal
    v-model:open="visible"
    title="Регистрация выезда"
    @ok="handleSubmit"
    @cancel="handleCancel"
    :confirm-loading="loading"
    width="500px"
    ok-text="Зарегистрировать выезд"
    cancel-text="Отмена"
  >
    <a-form ref="formRef" :model="form" layout="vertical">
      <!-- Vehicle Info (read-only) -->
      <a-row :gutter="16">
        <a-col :span="24">
          <a-alert type="info" show-icon style="margin-bottom: 16px;">
            <template #message>
              <span>Транспорт: <strong>{{ form.license_plate }}</strong></span>
            </template>
          </a-alert>
        </a-col>
      </a-row>

      <!-- Exit Time -->
      <a-row :gutter="16">
        <a-col :span="24">
          <a-form-item label="Время выезда" required>
            <a-date-picker
              v-model:value="form.exit_time"
              :show-time="{ format: 'HH:mm' }"
              format="DD.MM.YYYY HH:mm"
              placeholder="Выберите дату и время"
              style="width: 100%;"
              :value-format="undefined"
            />
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Exit Load Status (only for cargo vehicles) -->
      <a-row :gutter="16" v-if="form.vehicle_type === 'CARGO'">
        <a-col :span="24">
          <a-form-item label="Статус загрузки при выезде">
            <a-select
              v-model:value="form.exit_load_status"
              allow-clear
              placeholder="Выберите статус загрузки"
            >
              <a-select-option v-for="opt in loadStatuses" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Exit Photos Upload -->
      <a-row :gutter="16">
        <a-col :span="24">
          <a-form-item label="Фото при выезде (опционально)">
            <a-upload
              v-model:file-list="photoFileList"
              :before-upload="beforePhotoUpload"
              :multiple="true"
              accept="image/*"
              list-type="picture-card"
              :max-count="5"
            >
              <div v-if="photoFileList.length < 5">
                <PlusOutlined />
                <div style="margin-top: 8px">Загрузить</div>
              </div>
            </a-upload>
            <div style="font-size: 12px; color: #888;">Максимум 5 фото. Поддерживаются: JPG, PNG</div>
          </a-form-item>
        </a-col>
      </a-row>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { message } from 'ant-design-vue';
import type { FormInstance, UploadFile, UploadProps } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import dayjs from 'dayjs';
import { http } from '../utils/httpClient';
import { handleFormError, isApiError } from '../utils/formErrors';
import { useModalVisibility } from '../composables/useModalVisibility';
import type { VehicleRecord, ChoiceOption } from '../types/vehicle';

interface Props {
  open: boolean;
  loadStatuses: ChoiceOption[];
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'success'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = useModalVisibility(props, emit);
const loading = ref(false);
const formRef = ref<FormInstance>();
const photoFileList = ref<UploadFile[]>([]);

const form = reactive({
  id: 0,
  license_plate: '',
  vehicle_type: '',
  entry_time: '' as string,
  exit_time: null as dayjs.Dayjs | null,
  exit_load_status: null as string | null,
});

// Validate photo before upload
const beforePhotoUpload: UploadProps['beforeUpload'] = (file) => {
  const isImage = file.type.startsWith('image/');
  if (!isImage) {
    message.error('Можно загружать только изображения');
    return false;
  }
  const isLt5M = file.size / 1024 / 1024 < 5;
  if (!isLt5M) {
    message.error('Размер файла не должен превышать 5MB');
    return false;
  }
  return false; // Return false to prevent auto-upload
};

/**
 * Initialize form with vehicle data
 */
function initForm(record: VehicleRecord): void {
  form.id = record.id;
  form.license_plate = record.license_plate;
  form.vehicle_type = record.vehicle_type;
  form.entry_time = record.entry_time;
  form.exit_time = dayjs(); // Default to current time
  form.exit_load_status = null;
  photoFileList.value = [];
}

/**
 * Reset form state
 */
function resetForm(): void {
  form.id = 0;
  form.license_plate = '';
  form.vehicle_type = '';
  form.entry_time = '';
  form.exit_time = null;
  form.exit_load_status = null;
  photoFileList.value = [];
}

function handleCancel(): void {
  visible.value = false;
  resetForm();
}

async function handleSubmit(): Promise<void> {
  if (!form.exit_time || !form.exit_time.isValid()) {
    message.error('Пожалуйста, укажите время выезда');
    return;
  }

  // Validate exit_time > entry_time
  if (form.entry_time && form.entry_time !== '—') {
    const entryTime = dayjs(form.entry_time, 'DD.MM.YYYY HH:mm');
    if (entryTime.isValid() && form.exit_time.isBefore(entryTime)) {
      message.error('Время выезда не может быть раньше времени въезда');
      return;
    }
  }

  try {
    loading.value = true;

    const exitTime = form.exit_time.toISOString();

    // Use FormData for multipart request
    const formData = new FormData();
    formData.append('license_plate', form.license_plate);
    formData.append('exit_time', exitTime);

    if (form.exit_load_status) {
      formData.append('exit_load_status', form.exit_load_status);
    }

    // Add exit photo files
    for (const file of photoFileList.value) {
      if (file.originFileObj) {
        formData.append('exit_photo_files', file.originFileObj);
      }
    }

    await http.upload('/vehicles/entries/exit/', formData);

    message.success(`Транспорт ${form.license_plate} успешно выехал`);
    visible.value = false;
    resetForm();
    emit('success');
  } catch (error) {
    console.error('[Exit] Submission error:', error);
    if (isApiError(error)) {
      console.error('[Exit] Validation errors:', error.fieldErrors);
    }

    if (formRef.value) {
      handleFormError(error, formRef.value);
    } else {
      const errorMessage =
        error instanceof Error ? error.message : 'Произошла ошибка при регистрации выезда';
      message.error(errorMessage);
    }
  } finally {
    loading.value = false;
  }
}

// Expose initForm for parent component
defineExpose({
  initForm,
});
</script>
