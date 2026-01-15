<template>
  <a-modal v-model:open="visible" title="Экспорт в Excel" width="600px" :footer="null" @cancel="handleCancel">
    <a-form :model="formState" layout="vertical" @finish="handleExport">
      <a-form-item label="Тип контейнера">
        <a-select v-model:value="formState.isoType" placeholder="Выберите тип контейнера" allow-clear mode="multiple">
          <a-select-option value="22G1">22G1</a-select-option>
          <a-select-option value="42G1">42G1</a-select-option>
          <a-select-option value="45G1">45G1</a-select-option>
          <a-select-option value="L5G1">L5G1</a-select-option>
          <a-select-option value="22R1">22R1</a-select-option>
          <a-select-option value="42R1">42R1</a-select-option>
          <a-select-option value="45R1">45R1</a-select-option>
          <a-select-option value="L5R1">L5R1</a-select-option>
          <a-select-option value="22U1">22U1</a-select-option>
          <a-select-option value="42U1">42U1</a-select-option>
          <a-select-option value="45U1">45U1</a-select-option>
          <a-select-option value="22P1">22P1</a-select-option>
          <a-select-option value="42P1">42P1</a-select-option>
          <a-select-option value="45P1">45P1</a-select-option>
          <a-select-option value="22T1">22T1</a-select-option>
          <a-select-option value="42T1">42T1</a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="Статус">
        <a-select v-model:value="formState.status" placeholder="Выберите статус" allow-clear>
          <a-select-option value="Порожний">Порожний</a-select-option>
          <a-select-option value="Гружёный">Гружёный</a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="Транспорт при ЗАВОЗЕ">
        <a-select v-model:value="formState.transportType" placeholder="Выберите тип транспорта" allow-clear>
          <a-select-option value="Авто">Авто</a-select-option>
          <a-select-option value="Вагон">Вагон</a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="Собственник контейнера">
        <a-select v-model:value="formState.containerOwnerId" placeholder="Выберите собственника" allow-clear
          :loading="ownersLoading">
          <a-select-option v-for="owner in containerOwners" :key="owner.id" :value="owner.id">
            {{ owner.name }}
          </a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="Клиент">
        <a-select v-model:value="formState.clientName" placeholder="Выберите клиента" allow-clear
          :loading="customersLoading">
          <a-select-option v-for="customer in customerNames" :key="customer" :value="customer">
            {{ customer }}
          </a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item>
        <a-space>
          <a-button type="primary" html-type="submit" :loading="loading">
            <template #icon>
              <DownloadOutlined />
            </template>
            Скачать
          </a-button>
          <a-button @click="handleCancel">Отмена</a-button>
        </a-space>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { message } from 'ant-design-vue';
import { DownloadOutlined } from '@ant-design/icons-vue';
import { getCookie } from '../utils/storage';
import { API_BASE_URL } from '../config/api';
import { downloadBlob } from '../utils/download';

interface Owner {
  id: number;
  name: string;
  slug: string;
}

interface Props {
  open: boolean;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(props.open);
const loading = ref(false);
const ownersLoading = ref(false);
const containerOwners = ref<Owner[]>([]);
const customersLoading = ref(false);
const customerNames = ref<string[]>([]);

const formState = ref({
  isoType: [] as string[],
  status: undefined as string | undefined,
  transportType: undefined as string | undefined,
  containerOwnerId: undefined as number | undefined,
  clientName: undefined as string | undefined,
});

watch(() => props.open, (newVal) => {
  visible.value = newVal;
  if (newVal) {
    fetchContainerOwners();
    fetchCustomerNames();
  }
});

watch(visible, (newVal) => {
  if (!newVal) {
    emit('update:open', false);
  }
});

const fetchContainerOwners = async () => {
  try {
    ownersLoading.value = true;
    const token = getCookie('access_token');

    const response = await fetch(`${API_BASE_URL}/terminal/owners/?page=1&page_size=1000`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });

    if (!response.ok) {
      throw new Error('Ошибка загрузки собственников');
    }

    const data: { count: number; results: Owner[] } = await response.json();
    containerOwners.value = data.results;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка загрузки собственников');
  } finally {
    ownersLoading.value = false;
  }
};

const fetchCustomerNames = async () => {
  try {
    customersLoading.value = true;
    const token = getCookie('access_token');

    const response = await fetch(`${API_BASE_URL}/terminal/entries/customer-names/`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });

    if (!response.ok) {
      throw new Error('Ошибка загрузки клиентов');
    }

    const data: string[] = await response.json();
    customerNames.value = data;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка загрузки клиентов');
  } finally {
    customersLoading.value = false;
  }
};

const handleCancel = () => {
  visible.value = false;
  // Reset form
  formState.value = {
    isoType: [],
    status: undefined,
    transportType: undefined,
    containerOwnerId: undefined,
    clientName: undefined,
  };
};

const handleExport = async () => {
  try {
    loading.value = true;
    const token = getCookie('access_token');

    // Build query parameters from form filters
    const queryParams = new URLSearchParams();

    // Map form filter keys to API query parameters
    if (formState.value.isoType && formState.value.isoType.length > 0) {
      formState.value.isoType.forEach(type => {
        queryParams.append('container_iso_type', type);
      });
    }
    if (formState.value.status) {
      queryParams.append('status', formState.value.status);
    }
    if (formState.value.transportType) {
      queryParams.append('transport_type', formState.value.transportType);
    }
    if (formState.value.containerOwnerId) {
      queryParams.append('container_owner_id', formState.value.containerOwnerId.toString());
    }

    const queryString = queryParams.toString();
    const apiUrl = `${API_BASE_URL}/terminal/entries/export-excel/${queryString ? '?' + queryString : ''}`;

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });

    if (!response.ok) {
      throw new Error('Ошибка при экспорте данных');
    }

    const blob = await response.blob();

    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'containers_export.xlsx';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\\n]*=((['"]).*?\\2|[^;\\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }

    downloadBlob(blob, filename);

    message.success('Данные успешно экспортированы');
    handleCancel();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка при экспорте данных');
  } finally {
    loading.value = false;
  }
};
</script>
