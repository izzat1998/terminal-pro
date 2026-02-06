<template>
  <a-modal v-model:open="visible" :title="modalTitle" :confirm-loading="loading" :ok-text="okText"
    cancel-text="Отмена" :width="1000" @ok="handleSubmit" @cancel="handleCancel">
    <a-form :model="formState" :label-col="{ span: 24 }" :wrapper-col="{ span: 24 }" layout="vertical"
      style="margin-top: 2rem;">
      <a-row :gutter="16">
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item
            label="Номер контейнера"
            name="container_number"
            :rules="[
              { required: true, message: 'Введите номер контейнера' },
              { pattern: /^[A-Z]{4}\d{7}$/, message: 'Формат: 4 буквы + 7 цифр (например, MSKU1234567)' }
            ]"
            :validate-status="containerOnTerminal ? 'error' : undefined"
            :help="containerOnTerminal ? `Контейнер ${formState.container_number} уже на терминале` : undefined"
          >
            <a-input
              :value="formState.container_number"
              placeholder="Например: MSKU1234567"
              style="text-transform: uppercase;"
              maxlength="11"
              @update:value="(val: string) => formState.container_number = val.toUpperCase()"
            >
              <template #suffix>
                <LoadingOutlined v-if="containerCheckLoading" spin />
              </template>
            </a-input>
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="ISO тип" name="container_iso_type"
            :rules="[{ required: true, message: 'Выберите ISO тип' }]">
            <a-select v-model:value="formState.container_iso_type" placeholder="Выберите ISO тип">
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
        </a-col>
        <a-col :xs="24" :sm="24" :md="8">
          <a-form-item label="Статус" name="status" :rules="[{ required: true, message: 'Выберите статус' }]">
            <a-radio-group v-model:value="formState.status" button-style="solid" style="width: 100%; display: flex;">
              <a-radio-button value="Порожний" style="flex: 1; text-align: center;">Порожний</a-radio-button>
              <a-radio-button value="Гружёный" style="flex: 1; text-align: center;">Гружёный</a-radio-button>
            </a-radio-group>
          </a-form-item>
        </a-col>
      </a-row>

      <div
        style="padding: 0.5rem 1rem; background-color: #f6ffed; color: #52c41a; border-radius: 7px; margin-bottom: 1.5rem; text-align: center; display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
        Информация о ЗАВОЗЕ
      </div>

      <a-row :gutter="16">
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Тип транспорта при ЗАВОЗЕ" name="transport_type"
            :rules="[{ required: true, message: 'Выберите тип транспорта' }]">
            <a-radio-group v-model:value="formState.transport_type" button-style="solid"
              style="width: 100%; display: flex;">
              <a-radio-button value="Авто" style="flex: 1; text-align: center;">Авто</a-radio-button>
              <a-radio-button value="Вагон" style="flex: 1; text-align: center;">Вагон</a-radio-button>
            </a-radio-group>
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Номер Поезда при ЗАВОЗЕ" name="entry_train_number">
            <a-input v-model:value="formState.entry_train_number"
              placeholder="Введите номер поезда при завозе (опционально)" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Номер машины/вагона при ЗАВОЗЕ" name="transport_number"
            :rules="[{ required: true, message: 'Введите номер транспорта' }]">
            <a-input v-model:value="formState.transport_number" placeholder="Введите номер транспорта" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Место-ние" name="location">
            <a-input v-model:value="formState.location" placeholder="Введите место-ние (опционально)" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Владелец контейнера" name="container_owner">
            <a-select v-model:value="formState.container_owner"
              placeholder="Выберите владельца контейнера (опционально)"
              :loading="ownersLoading"
              allow-clear>
              <a-select-option v-for="owner in owners" :key="owner.id" :value="owner.id">
                {{ owner.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <div
        style="padding: 0.5rem 1rem; background-color: #ebebeb; color: black; border-radius: 7px; margin-bottom: 1.5rem; text-align: center; display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
        ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ
      </div>

      <a-row :gutter="16">
        <a-col :xs="24" :sm="12" :md="16">
          <a-form-item label="Даты дополнительных крановых операций" name="crane_operation_dates">
            <MultiDateCalendar v-model="formState.crane_operation_dates" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Название груза" name="cargo_name">
            <a-input v-model:value="formState.cargo_name" placeholder="Введите название груза (опционально)" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Имя клиента" name="company_id" :rules="[{ required: true, message: 'Выберите клиента' }]">
            <a-select v-model:value="formState.company_id"
              placeholder="Выберите клиента"
              :loading="companiesLoading"
              allow-clear
              show-search
              :filter-option="(input: string, option: { label?: string; value?: string | number }) => (option.label ?? '').toLowerCase().includes(input.toLowerCase())">
              <a-select-option v-for="company in companies" :key="company.id" :value="company.id" :label="company.name">
                {{ company.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Тоннаж" name="cargo_weight">
            <a-input-number v-model:value="formState.cargo_weight" placeholder="Введите тоннаж (опционально)"
              style="width: 100%;" :min="0" :step="0.1" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item label="Примечание" name="note">
        <a-textarea v-model:value="formState.note" placeholder="Введите примечание (опционально)" :rows="3" />
      </a-form-item>

      <div
        style="padding: 0.5rem 1rem; background-color: #e6f4ff; color: #1677ff; border-radius: 7px; margin-bottom: 1.5rem; text-align: center; display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
        Информация о ВЫВОЗЕ
      </div>

      <a-row :gutter="16">
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Тип транспорта при ВЫВОЗЕ" name="exit_transport_type">
            <a-radio-group v-model:value="formState.exit_transport_type" button-style="solid"
              style="width: 100%; display: flex;">
              <a-radio-button value="Авто" style="flex: 1; text-align: center;">Авто</a-radio-button>
              <a-radio-button value="Вагон" style="flex: 1; text-align: center;">Вагон</a-radio-button>
            </a-radio-group>
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Дата вывоза конт-ра с МТТ" name="exit_date">
            <a-date-picker v-model:value="formState.exit_date" placeholder="Выберите дату вывоза (опционально)"
              style="width: 100%;" format="YYYY-MM-DD" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Номер Поезда при ВЫВОЗЕ" name="exit_train_number">
            <a-input v-model:value="formState.exit_train_number"
              placeholder="Введите номер поезда при вывозе (опционально)" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Номер машины/вагона при ВЫВОЗЕ" name="exit_transport_number">
            <a-input v-model:value="formState.exit_transport_number"
              placeholder="Введите номер машины/вагона при вывозе (опционально)" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8">
          <a-form-item label="Станция назначения" name="destination_station">
            <a-input v-model:value="formState.destination_station"
              placeholder="Введите станцию назначения (опционально)" />
          </a-form-item>
        </a-col>
      </a-row>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { message } from 'ant-design-vue';
import { LoadingOutlined } from '@ant-design/icons-vue';
import { debounce } from 'lodash-es';
import dayjs, { type Dayjs } from 'dayjs';
import { http } from '../utils/httpClient';
import { useModalVisibility } from '../composables/useModalVisibility';
import MultiDateCalendar from './MultiDateCalendar.vue';

interface CraneOperation {
  id: number;
  operation_date: string;
  created_at: string;
}

interface Props {
  open: boolean;
  mode: 'create' | 'edit';
  // Edit mode props (optional, only used when mode === 'edit')
  containerId?: number;
  containerNumber?: string;
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
  craneOperations?: CraneOperation[];
  note?: string;
  cargoWeight?: number;
  cargoName?: string;
  companyId?: number;
  containerOwnerId?: number;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'success'): void;
}

interface Owner {
  id: number;
  name: string;
  slug: string;
}

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
}

interface FormState {
  container_number: string;
  container_iso_type: string;
  status: string;
  transport_type: string;
  entry_train_number?: string;
  transport_number: string;
  exit_date?: Dayjs | null;
  exit_transport_type?: string;
  exit_train_number?: string;
  exit_transport_number?: string;
  destination_station?: string;
  location?: string;
  crane_operation_dates: string[];
  note?: string;
  cargo_weight?: number;
  cargo_name?: string;
  company_id?: number;
  container_owner?: number;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

// Mode-dependent computed values
const modalTitle = computed(() => props.mode === 'create' ? 'Создать контейнер' : 'Редактировать контейнер');
const okText = computed(() => props.mode === 'create' ? 'Создать' : 'Сохранить');

const visible = useModalVisibility(props, emit);

const loading = ref(false);
const owners = ref<Owner[]>([]);
const ownersLoading = ref(false);
const companies = ref<Company[]>([]);
const companiesLoading = ref(false);

// Container on-terminal validation state
const containerCheckLoading = ref(false);
const containerOnTerminal = ref(false);
const containerOnTerminalEntry = ref<{ id: number; container_number: string; entry_time: string } | null>(null);

// Check if container is already on terminal
const checkContainerOnTerminal = async (containerNumber: string) => {
  // Only check in create mode - in edit mode, the container might already be on terminal
  if (props.mode === 'edit') {
    containerOnTerminal.value = false;
    containerOnTerminalEntry.value = null;
    return;
  }

  if (!containerNumber || containerNumber.length < 4) {
    containerOnTerminal.value = false;
    containerOnTerminalEntry.value = null;
    return;
  }

  try {
    containerCheckLoading.value = true;
    const data = await http.get<{ on_terminal: boolean; entry?: { id: number; container_number: string; entry_time: string } }>(
      `/terminal/entries/check-container/?container_number=${encodeURIComponent(containerNumber)}`
    );
    containerOnTerminal.value = data.on_terminal;
    containerOnTerminalEntry.value = data.entry || null;
  } catch (error) {
    console.error('Error checking container:', error);
    containerOnTerminal.value = false;
    containerOnTerminalEntry.value = null;
  } finally {
    containerCheckLoading.value = false;
  }
};

// Debounced version (400ms delay)
const debouncedCheckContainer = debounce(checkContainerOnTerminal, 400);

const formState = reactive<FormState>({
  container_number: '',
  container_iso_type: '',
  status: 'Порожний',
  transport_type: 'Авто',
  entry_train_number: '',
  transport_number: '',
  exit_date: null,
  exit_transport_type: '',
  exit_train_number: '',
  exit_transport_number: '',
  destination_station: '',
  location: '',
  crane_operation_dates: [],
  note: '',
  cargo_weight: undefined,
  cargo_name: '',
  company_id: undefined,
  container_owner: undefined,
});

// Load form data from props (edit mode only)
const loadFormData = () => {
  if (props.containerNumber) formState.container_number = props.containerNumber;
  if (props.containerIsoType) formState.container_iso_type = props.containerIsoType;
  if (props.status) formState.status = props.status;
  if (props.transportType) formState.transport_type = props.transportType;
  if (props.entryTrainNumber) formState.entry_train_number = props.entryTrainNumber;
  if (props.transportNumber) formState.transport_number = props.transportNumber;

  // Parse exit_date - handle formatted date strings (DD.MM.YYYY) from the table
  if (props.exitDate && props.exitDate.trim() !== '') {
    const parsed = dayjs(props.exitDate, ['YYYY-MM-DD', 'DD.MM.YYYY'], true);
    formState.exit_date = parsed.isValid() ? parsed : null;
  } else {
    formState.exit_date = null;
  }

  if (props.exitTransportType) formState.exit_transport_type = props.exitTransportType;
  if (props.exitTrainNumber) formState.exit_train_number = props.exitTrainNumber;
  if (props.exitTransportNumber) formState.exit_transport_number = props.exitTransportNumber;
  if (props.destinationStation) formState.destination_station = props.destinationStation;
  if (props.location) formState.location = props.location;

  // Parse crane operation dates from API response
  if (props.craneOperations && props.craneOperations.length > 0) {
    formState.crane_operation_dates = props.craneOperations
      .map(op => {
        const parsed = dayjs(op.operation_date);
        return parsed.isValid() ? parsed.format('YYYY-MM-DD') : null;
      })
      .filter((date): date is string => date !== null);
  } else if (props.additionalCraneOperationDate && props.additionalCraneOperationDate.trim() !== '') {
    const parsed = dayjs(props.additionalCraneOperationDate, ['YYYY-MM-DD', 'DD.MM.YYYY', 'YYYY-MM-DDTHH:mm:ss'], true);
    if (parsed.isValid()) {
      formState.crane_operation_dates = [parsed.format('YYYY-MM-DD')];
    } else {
      formState.crane_operation_dates = [];
    }
  } else {
    formState.crane_operation_dates = [];
  }

  if (props.note) formState.note = props.note;
  if (props.cargoWeight !== undefined) formState.cargo_weight = props.cargoWeight;
  if (props.cargoName) formState.cargo_name = props.cargoName;
  if (props.companyId !== undefined) formState.company_id = props.companyId;
  if (props.containerOwnerId !== undefined) formState.container_owner = props.containerOwnerId;
};

// Watch for container number changes (only in create mode)
watch(() => formState.container_number, (newNumber) => {
  if (props.mode === 'create' && newNumber) {
    debouncedCheckContainer(newNumber);
  } else {
    containerOnTerminal.value = false;
    containerOnTerminalEntry.value = null;
  }
});

// Reset form to initial state based on mode
const resetForm = () => {
  formState.container_number = '';
  formState.container_iso_type = '';
  formState.status = 'Порожний';
  formState.transport_type = 'Авто';
  formState.entry_train_number = '';
  formState.transport_number = '';
  formState.location = '';
  formState.crane_operation_dates = [];
  formState.note = '';
  formState.cargo_weight = undefined;
  formState.cargo_name = '';
  formState.company_id = undefined;
  formState.container_owner = undefined;

  // Reset container validation state
  containerOnTerminal.value = false;
  containerOnTerminalEntry.value = null;

  // Mode-specific defaults
  if (props.mode === 'create') {
    formState.exit_date = dayjs();
    formState.exit_transport_type = 'Авто';
  } else {
    formState.exit_date = null;
    formState.exit_transport_type = '';
  }
  formState.exit_train_number = '';
  formState.exit_transport_number = '';
  formState.destination_station = '';
};

const handleSubmit = async () => {
  // Block if container is already on terminal (only in create mode)
  if (props.mode === 'create' && containerOnTerminal.value) {
    message.error('Невозможно создать запись: контейнер уже на терминале');
    return;
  }

  // Validate required fields
  if (!formState.container_number || !formState.container_iso_type || !formState.status || !formState.transport_type || !formState.transport_number || !formState.company_id) {
    message.error('Заполните все обязательные поля');
    return;
  }

  // Edit mode requires containerId
  if (props.mode === 'edit' && !props.containerId) {
    message.error('Не указан ID контейнера');
    return;
  }

  loading.value = true;

  try {
    // Convert dayjs objects to strings for API
    const submitData: Record<string, unknown> = {
      ...formState,
      exit_date: formState.exit_date ? formState.exit_date.format('YYYY-MM-DD') : undefined,
    };

    // Remove crane_operation_dates from submitData and add crane_operations_data instead
    delete submitData.crane_operation_dates;

    // Format crane operation dates for API
    if (formState.crane_operation_dates.length > 0) {
      submitData.crane_operations_data = formState.crane_operation_dates
        .map(dateStr => ({
          operation_date: dayjs(dateStr).startOf('day').toISOString()
        }));
    }

    if (props.mode === 'create') {
      await http.post('/terminal/entries/', submitData);
      message.success('Контейнер успешно создан');
    } else {
      await http.patch(`/terminal/entries/${props.containerId}/`, submitData);
      message.success('Контейнер успешно обновлён');
    }

    emit('success');
    visible.value = false;
    resetForm();
  } catch (error) {
    const errorMessage = props.mode === 'create'
      ? 'Ошибка при создании контейнера'
      : 'Ошибка при обновлении контейнера';
    message.error(error instanceof Error ? error.message : errorMessage);
  } finally {
    loading.value = false;
  }
};

const handleCancel = () => {
  resetForm();
  visible.value = false;
};

// Fetch owners list
const fetchOwners = async () => {
  try {
    ownersLoading.value = true;
    const data = await http.get<{ results: Owner[] }>('/terminal/owners/');
    owners.value = data.results;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка загрузки списка владельцев');
  } finally {
    ownersLoading.value = false;
  }
};

// Fetch companies list
const fetchCompanies = async () => {
  try {
    companiesLoading.value = true;
    const data = await http.get<{ count: number; results: Company[] } | Company[]>('/auth/companies/');

    // Handle both paginated and non-paginated responses
    if (Array.isArray(data)) {
      companies.value = data.filter(c => c.is_active);
    } else if (data && 'results' in data) {
      companies.value = data.results.filter(c => c.is_active);
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка загрузки списка компаний');
  } finally {
    companiesLoading.value = false;
  }
};

// Initialize form when modal opens
watch(visible, (newValue) => {
  if (newValue) {
    fetchOwners();
    fetchCompanies();
    if (props.mode === 'edit') {
      loadFormData();
    } else {
      resetForm();
    }
  } else {
    resetForm();
  }
});
</script>
