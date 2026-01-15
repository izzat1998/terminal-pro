/**
 * Composable for vehicle create form state and logic
 * Handles form state, validation, watchers for dependent fields
 */

import { ref, reactive, computed, watch, onUnmounted } from 'vue';
import { message } from 'ant-design-vue';
import type { FormInstance } from 'ant-design-vue';
import { debounce } from 'lodash-es';
import { http } from '../utils/httpClient';
import { handleFormError } from '../utils/formErrors';
import {
  isLightVehicle,
  isCargoVehicle,
  isCargoLoaded,
  isContainerCargo,
  isContainerCapableTransport,
} from '../utils/vehicleHelpers';

/** Create form state interface */
export interface CreateFormState {
  license_plate: string;
  vehicle_type: string;
  customer: number | null;
  visitor_type: string | null;
  transport_type: string;
  entry_load_status: string;
  cargo_type: string;
  container_size: string;
  container_load_status: string | null;
  destination: number;
}

/** Callbacks for external dependencies */
export interface CreateFormCallbacks {
  onSuccess: () => void;
  refreshStats: () => void;
}

/**
 * Composable for vehicle create form
 *
 * @param callbacks - Callback functions for success and stats refresh
 */
export function useVehicleCreateForm(callbacks: CreateFormCallbacks) {
  // Modal state
  const createModalVisible = ref(false);
  const createLoading = ref(false);
  const createFormRef = ref<FormInstance>();

  // Plate validation state
  const plateOnTerminal = ref(false);
  const plateOnTerminalEntry = ref<{ id: number; license_plate: string; entry_time: string } | null>(null);
  const plateCheckLoading = ref(false);

  // Form state
  const createForm = reactive<CreateFormState>({
    license_plate: '',
    vehicle_type: '',
    customer: null,
    visitor_type: null,
    transport_type: '',
    entry_load_status: '',
    cargo_type: '',
    container_size: '',
    container_load_status: null,
    destination: 0,
  });

  // Computed properties for conditional field visibility
  const isCreateLightVehicle = computed(() => isLightVehicle(createForm.vehicle_type));
  const isCreateCargoVehicle = computed(() => isCargoVehicle(createForm.vehicle_type));
  const isCreateCargoLoaded = computed(() => isCargoLoaded(createForm.entry_load_status));
  const isCreateContainerCargo = computed(() => isContainerCargo(createForm.cargo_type));
  const isCreateContainerCapableTransport = computed(() =>
    isContainerCapableTransport(createForm.transport_type)
  );

  // Check if license plate is already on terminal
  async function checkPlateOnTerminal(plate: string): Promise<void> {
    if (!plate || plate.length < 3) {
      plateOnTerminal.value = false;
      plateOnTerminalEntry.value = null;
      return;
    }

    try {
      plateCheckLoading.value = true;
      const data = await http.get<{
        on_terminal: boolean;
        entry?: { id: number; license_plate: string; entry_time: string };
      }>(`/vehicles/entries/check-plate/?license_plate=${encodeURIComponent(plate)}`);
      plateOnTerminal.value = data.on_terminal;
      plateOnTerminalEntry.value = data.entry || null;
    } catch (error) {
      console.error('Error checking plate:', error);
      plateOnTerminal.value = false;
      plateOnTerminalEntry.value = null;
    } finally {
      plateCheckLoading.value = false;
    }
  }

  // Debounced version (400ms delay for responsive UX)
  const debouncedCheckPlate = debounce(checkPlateOnTerminal, 400);

  // Cleanup debounce timer on unmount to prevent memory leaks
  onUnmounted(() => {
    debouncedCheckPlate.cancel();
  });

  // Watch for license plate changes
  watch(
    () => createForm.license_plate,
    (newPlate) => {
      if (newPlate) {
        debouncedCheckPlate(newPlate);
      } else {
        plateOnTerminal.value = false;
        plateOnTerminalEntry.value = null;
      }
    }
  );

  // Watchers for dependent field resets
  watch(
    () => createForm.vehicle_type,
    (newType, oldType) => {
      if (oldType && newType !== oldType) {
        if (oldType === 'CARGO') {
          createForm.transport_type = '';
          createForm.entry_load_status = '';
          createForm.cargo_type = '';
          createForm.container_size = '';
          createForm.container_load_status = null;
          createForm.destination = 0;
        }
        if (oldType === 'LIGHT') {
          createForm.visitor_type = null;
        }
      }
    }
  );

  watch(
    () => createForm.transport_type,
    (newType, oldType) => {
      if (oldType && newType !== oldType) {
        if (!isContainerCapableTransport(newType) && createForm.cargo_type === 'CONTAINER') {
          createForm.cargo_type = '';
          createForm.container_size = '';
          createForm.container_load_status = null;
        }
      }
    }
  );

  watch(
    () => createForm.entry_load_status,
    (newStatus, oldStatus) => {
      if (oldStatus && newStatus !== oldStatus) {
        if (newStatus === 'EMPTY') {
          createForm.cargo_type = '';
          createForm.container_size = '';
          createForm.container_load_status = null;
        }
      }
    }
  );

  watch(
    () => createForm.cargo_type,
    (newType, oldType) => {
      if (oldType && newType !== oldType) {
        if (oldType === 'CONTAINER' && newType !== 'CONTAINER') {
          createForm.container_size = '';
          createForm.container_load_status = null;
        }
      }
    }
  );

  // Reset form to initial state
  function resetForm(): void {
    createForm.license_plate = '';
    createForm.vehicle_type = '';
    createForm.customer = null;
    createForm.visitor_type = null;
    createForm.transport_type = '';
    createForm.entry_load_status = '';
    createForm.cargo_type = '';
    createForm.container_size = '';
    createForm.container_load_status = null;
    createForm.destination = 0;
    // Reset plate validation state
    plateOnTerminal.value = false;
    plateOnTerminalEntry.value = null;
  }

  // Show modal
  function showCreateModal(): void {
    resetForm();
    createModalVisible.value = true;
  }

  // Cancel modal
  function handleCreateCancel(): void {
    createModalVisible.value = false;
  }

  // Validate and submit
  async function handleCreateSubmit(): Promise<void> {
    // Block if vehicle is already on terminal
    if (plateOnTerminal.value) {
      message.error('Невозможно создать запись: транспорт уже на терминале');
      return;
    }

    // Basic validation
    if (!createForm.license_plate.trim()) {
      message.error('Пожалуйста, введите гос. номер');
      return;
    }

    if (!createForm.vehicle_type) {
      message.error('Пожалуйста, выберите тип ТС');
      return;
    }

    // Light vehicle validation
    if (createForm.vehicle_type === 'LIGHT') {
      if (!createForm.visitor_type) {
        message.error('Пожалуйста, выберите тип посетителя');
        return;
      }
    }

    // Cargo vehicle validation
    if (createForm.vehicle_type === 'CARGO') {
      if (!createForm.transport_type || !createForm.entry_load_status) {
        message.error('Пожалуйста, заполните все обязательные поля');
        return;
      }

      if (createForm.entry_load_status === 'LOADED') {
        if (!createForm.cargo_type) {
          message.error('Пожалуйста, выберите тип груза');
          return;
        }

        if (createForm.cargo_type === 'CONTAINER') {
          if (!createForm.container_size || !createForm.container_load_status) {
            message.error('Пожалуйста, заполните данные контейнера');
            return;
          }
        }
      }

      if (!createForm.destination) {
        message.error('Пожалуйста, выберите назначение');
        return;
      }
    }

    try {
      createLoading.value = true;

      const requestBody: Record<string, unknown> = {
        license_plate: createForm.license_plate,
        vehicle_type: createForm.vehicle_type,
        customer_id: createForm.customer,
      };

      if (createForm.vehicle_type === 'LIGHT') {
        if (createForm.visitor_type) {
          requestBody.visitor_type = createForm.visitor_type;
        }
      } else if (createForm.vehicle_type === 'CARGO') {
        requestBody.transport_type = createForm.transport_type;
        requestBody.entry_load_status = createForm.entry_load_status;

        if (createForm.entry_load_status === 'LOADED') {
          requestBody.cargo_type = createForm.cargo_type;

          if (createForm.cargo_type === 'CONTAINER') {
            requestBody.container_size = createForm.container_size;
            if (createForm.container_load_status) {
              requestBody.container_load_status = createForm.container_load_status;
            }
          }
        }

        requestBody.destination = createForm.destination;
      }

      await http.post('/vehicles/entries/', requestBody);

      message.success('Запись успешно создана');
      createModalVisible.value = false;
      callbacks.onSuccess();
      callbacks.refreshStats();
    } catch (error) {
      handleFormError(error, createFormRef.value);
    } finally {
      createLoading.value = false;
    }
  }

  return {
    // Modal state
    createModalVisible,
    createLoading,
    createFormRef,

    // Plate validation state
    plateOnTerminal,
    plateOnTerminalEntry,
    plateCheckLoading,

    // Form state
    createForm,

    // Computed visibility
    isCreateLightVehicle,
    isCreateCargoVehicle,
    isCreateCargoLoaded,
    isCreateContainerCargo,
    isCreateContainerCapableTransport,

    // Actions
    showCreateModal,
    handleCreateCancel,
    handleCreateSubmit,
  };
}
