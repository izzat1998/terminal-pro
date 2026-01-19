<template>
  <a-modal
    v-model:open="visible"
    title="Редактировать технику"
    :confirm-loading="loading"
    ok-text="Сохранить"
    cancel-text="Отмена"
    @ok="handleSubmit"
    @cancel="handleCancel"
  >
    <a-form :model="formState" layout="vertical" style="margin-top: 1rem;">
      <a-form-item
        label="Название"
        name="name"
        :rules="[{ required: true, message: 'Введите название' }]"
      >
        <a-input v-model:value="formState.name" placeholder="Например: RS-01, Погрузчик-3" />
      </a-form-item>

      <a-form-item
        label="Тип техники"
        name="vehicle_type"
        :rules="[{ required: true, message: 'Выберите тип техники' }]"
      >
        <a-select v-model:value="formState.vehicle_type" placeholder="Выберите тип">
          <a-select-option v-for="opt in VEHICLE_TYPE_OPTIONS" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="Госномер" name="license_plate">
        <a-input v-model:value="formState.license_plate" placeholder="Например: 01A123BC" />
      </a-form-item>

      <a-form-item label="Оператор" name="operator_id">
        <a-select
          v-model:value="formState.operator_id"
          placeholder="Выберите оператора"
          allow-clear
        >
          <a-select-option v-for="op in operators" :key="op.id" :value="op.id">
            {{ op.full_name }}
          </a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="Статус" name="is_active">
        <a-switch v-model:checked="formState.is_active" />
        <span style="margin-left: 8px;">{{ formState.is_active ? 'Активна' : 'Выключена' }}</span>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { updateTerminalVehicle } from '../services/terminalVehicleService'
import { useModalVisibility } from '../composables/useModalVisibility'
import type { VehicleType, VehicleOperator } from '../types/terminalVehicles'
import { VEHICLE_TYPE_OPTIONS } from '../types/terminalVehicles'

interface Props {
  open: boolean
  vehicleId?: number
  name?: string
  vehicleType?: VehicleType
  licensePlate?: string
  operatorId?: number
  isActive?: boolean
  operators: VehicleOperator[]
}

interface Emits {
  (e: 'update:open', value: boolean): void
  (e: 'success'): void
}

interface FormState {
  name: string
  vehicle_type: VehicleType | undefined
  license_plate: string
  operator_id: number | undefined
  is_active: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const visible = useModalVisibility(props, emit)

const loading = ref(false)

const formState = reactive<FormState>({
  name: '',
  vehicle_type: undefined,
  license_plate: '',
  operator_id: undefined,
  is_active: true,
})

const loadFormData = () => {
  if (props.name) formState.name = props.name
  if (props.vehicleType) formState.vehicle_type = props.vehicleType
  formState.license_plate = props.licensePlate ?? ''
  formState.operator_id = props.operatorId
  if (props.isActive !== undefined) formState.is_active = props.isActive
}

const resetForm = () => {
  formState.name = ''
  formState.vehicle_type = undefined
  formState.license_plate = ''
  formState.operator_id = undefined
  formState.is_active = true
}

const handleSubmit = async () => {
  // Validate required fields
  if (!formState.name.trim()) {
    message.error('Пожалуйста, введите название')
    return
  }

  if (!formState.vehicle_type) {
    message.error('Пожалуйста, выберите тип техники')
    return
  }

  if (!props.vehicleId) {
    message.error('Не указан ID техники')
    return
  }

  loading.value = true

  try {
    await updateTerminalVehicle(props.vehicleId, {
      name: formState.name.trim(),
      vehicle_type: formState.vehicle_type,
      license_plate: formState.license_plate.trim(),
      operator_id: formState.operator_id ?? null,
      is_active: formState.is_active,
    })

    message.success('Техника успешно обновлена')
    emit('success')
    visible.value = false
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка обновления техники')
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  resetForm()
  visible.value = false
}

// Load form data when modal opens
watch(visible, (newValue) => {
  if (newValue) {
    loadFormData()
  } else {
    resetForm()
  }
})
</script>
