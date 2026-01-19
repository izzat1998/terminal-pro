<template>
  <a-card title="Техника терминала" :bordered="false">
    <template #extra>
      <a-button type="primary" @click="showCreateModal">
        <template #icon>
          <PlusOutlined />
        </template>
        Добавить технику
      </a-button>
    </template>

    <a-table
      :columns="columns"
      :data-source="dataSource"
      :loading="loading"
      :pagination="false"
      bordered
      :scroll="{ x: 900 }"
      :locale="{ emptyText: undefined }"
    >
      <template #bodyCell="{ column, index, record }">
        <template v-if="column.key === 'number'">
          {{ index + 1 }}
        </template>
        <template v-else-if="column.key === 'operator'">
          <span v-if="record.operator">{{ record.operator.full_name }}</span>
          <span v-else class="text-gray">—</span>
        </template>
        <template v-else-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'default'">
            {{ record.is_active ? 'Активна' : 'Выключена' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-tooltip title="Редактировать">
              <a-button type="link" size="small" @click="showEditModal(record)">
                <template #icon>
                  <EditOutlined />
                </template>
              </a-button>
            </a-tooltip>
            <a-tooltip title="Удалить">
              <a-button type="link" size="small" danger @click="showDeleteModal(record)">
                <template #icon>
                  <DeleteOutlined />
                </template>
              </a-button>
            </a-tooltip>
          </a-space>
        </template>
      </template>
      <template #emptyText>
        <a-empty :image="Empty.PRESENTED_IMAGE_SIMPLE" description="Нет техники">
          <a-button type="primary" @click="showCreateModal">
            <template #icon><PlusOutlined /></template>
            Добавить технику
          </a-button>
        </a-empty>
      </template>
    </a-table>
  </a-card>

  <!-- Create Modal -->
  <a-modal
    v-model:open="createModalVisible"
    title="Добавить технику"
    @ok="handleCreateSubmit"
    @cancel="handleCreateCancel"
    :confirm-loading="createLoading"
  >
    <a-form :model="createForm" layout="vertical">
      <a-form-item label="Название" required>
        <a-input v-model:value="createForm.name" placeholder="Например: RS-01, Погрузчик-3" />
      </a-form-item>
      <a-form-item label="Тип техники" required>
        <a-select v-model:value="createForm.vehicle_type" placeholder="Выберите тип">
          <a-select-option v-for="opt in VEHICLE_TYPE_OPTIONS" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="Госномер">
        <a-input v-model:value="createForm.license_plate" placeholder="Например: 01A123BC" />
      </a-form-item>
      <a-form-item label="Оператор">
        <a-select
          v-model:value="createForm.operator_id"
          placeholder="Выберите оператора"
          allow-clear
          :loading="operatorsLoading"
        >
          <a-select-option v-for="op in operators" :key="op.id" :value="op.id">
            {{ op.full_name }}
          </a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="Статус">
        <a-switch v-model:checked="createForm.is_active" />
        <span style="margin-left: 8px;">{{ createForm.is_active ? 'Активна' : 'Выключена' }}</span>
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- Edit Modal -->
  <TerminalVehicleEditModal
    v-model:open="editModalVisible"
    :vehicle-id="editingVehicle.id"
    :name="editingVehicle.name"
    :vehicle-type="editingVehicle.vehicle_type"
    :license-plate="editingVehicle.license_plate"
    :operator-id="editingVehicle.operator_id"
    :is-active="editingVehicle.is_active"
    :operators="operators"
    @success="handleEditSuccess"
  />

  <!-- Delete Modal -->
  <a-modal
    v-model:open="deleteModalVisible"
    title="Удалить технику"
    @ok="handleDeleteSubmit"
    @cancel="handleDeleteCancel"
    :confirm-loading="deleteLoading"
    okText="Удалить"
    cancelText="Отмена"
    okType="danger"
  >
    <p>Вы уверены, что хотите удалить технику <strong>{{ deletingVehicle.name }}</strong>?</p>
    <p>Это действие невозможно отменить.</p>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { message, Empty } from 'ant-design-vue'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import {
  getTerminalVehicles,
  createTerminalVehicle,
  deleteTerminalVehicle,
  getAvailableOperators,
} from '../services/terminalVehicleService'
import type {
  TerminalVehicle,
  VehicleType,
  VehicleOperator,
} from '../types/terminalVehicles'
import { VEHICLE_TYPE_OPTIONS } from '../types/terminalVehicles'
import TerminalVehicleEditModal from '../components/TerminalVehicleEditModal.vue'

// Table record type (extends TerminalVehicle with key)
interface VehicleRecord extends TerminalVehicle {
  key: string
}

const columns = [
  {
    title: '№',
    key: 'number',
    align: 'center' as const,
    width: 60,
    fixed: 'left' as const,
  },
  {
    title: 'Название',
    dataIndex: 'name',
    key: 'name',
    align: 'center' as const,
    width: 120,
  },
  {
    title: 'Тип',
    dataIndex: 'vehicle_type_display',
    key: 'vehicle_type_display',
    align: 'center' as const,
    width: 150,
  },
  {
    title: 'Госномер',
    dataIndex: 'license_plate',
    key: 'license_plate',
    align: 'center' as const,
    width: 120,
  },
  {
    title: 'Оператор',
    key: 'operator',
    align: 'center' as const,
    width: 150,
  },
  {
    title: 'Статус',
    key: 'is_active',
    align: 'center' as const,
    width: 100,
  },
  {
    title: 'Действия',
    key: 'actions',
    align: 'center' as const,
    width: 100,
    fixed: 'right' as const,
  },
]

// Table data state
const dataSource = ref<VehicleRecord[]>([])
const loading = ref(false)

// Operators list (for assignment)
const operators = ref<VehicleOperator[]>([])
const operatorsLoading = ref(false)

// Fetch data
const fetchData = async () => {
  try {
    loading.value = true
    const vehicles = await getTerminalVehicles()
    dataSource.value = vehicles.map(v => ({
      ...v,
      key: v.id.toString(),
    }))
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Не удалось загрузить данные')
  } finally {
    loading.value = false
  }
}

// Fetch operators
const fetchOperators = async () => {
  try {
    operatorsLoading.value = true
    operators.value = await getAvailableOperators()
  } catch (error) {
    console.error('Failed to load operators:', error)
  } finally {
    operatorsLoading.value = false
  }
}

const refresh = () => {
  fetchData()
}

// Create modal state
const createModalVisible = ref(false)
const createLoading = ref(false)
const createForm = reactive({
  name: '',
  vehicle_type: undefined as VehicleType | undefined,
  license_plate: '',
  operator_id: undefined as number | undefined,
  is_active: true,
})

const showCreateModal = () => {
  createForm.name = ''
  createForm.vehicle_type = undefined
  createForm.license_plate = ''
  createForm.operator_id = undefined
  createForm.is_active = true
  createModalVisible.value = true
}

const handleCreateCancel = () => {
  createModalVisible.value = false
}

const handleCreateSubmit = async () => {
  if (!createForm.name.trim()) {
    message.error('Пожалуйста, введите название')
    return
  }

  if (!createForm.vehicle_type) {
    message.error('Пожалуйста, выберите тип техники')
    return
  }

  try {
    createLoading.value = true
    await createTerminalVehicle({
      name: createForm.name.trim(),
      vehicle_type: createForm.vehicle_type,
      license_plate: createForm.license_plate.trim(),
      operator_id: createForm.operator_id ?? null,
      is_active: createForm.is_active,
    })

    message.success('Техника успешно добавлена')
    createModalVisible.value = false
    refresh()
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка создания техники')
  } finally {
    createLoading.value = false
  }
}

// Edit modal state
const editModalVisible = ref(false)
const editingVehicle = reactive({
  id: undefined as number | undefined,
  name: '',
  vehicle_type: undefined as VehicleType | undefined,
  license_plate: '',
  operator_id: undefined as number | undefined,
  is_active: true,
})

const showEditModal = (record: VehicleRecord) => {
  editingVehicle.id = record.id
  editingVehicle.name = record.name
  editingVehicle.vehicle_type = record.vehicle_type
  editingVehicle.license_plate = record.license_plate
  editingVehicle.operator_id = record.operator?.id
  editingVehicle.is_active = record.is_active
  editModalVisible.value = true
}

const handleEditSuccess = () => {
  refresh()
}

// Delete modal state
const deleteModalVisible = ref(false)
const deleteLoading = ref(false)
const deletingVehicle = reactive({
  id: undefined as number | undefined,
  name: '',
})

const showDeleteModal = (record: VehicleRecord) => {
  deletingVehicle.id = record.id
  deletingVehicle.name = record.name
  deleteModalVisible.value = true
}

const handleDeleteCancel = () => {
  deleteModalVisible.value = false
  deletingVehicle.id = undefined
  deletingVehicle.name = ''
}

const handleDeleteSubmit = async () => {
  if (!deletingVehicle.id) {
    message.error('Ошибка: ID техники не найден')
    return
  }

  try {
    deleteLoading.value = true
    await deleteTerminalVehicle(deletingVehicle.id)

    message.success('Техника успешно удалена')
    deleteModalVisible.value = false
    refresh()
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка удаления техники')
  } finally {
    deleteLoading.value = false
  }
}

onMounted(() => {
  fetchData()
  fetchOperators()
})
</script>

<style scoped>
.text-gray {
  color: #8c8c8c;
}
</style>
