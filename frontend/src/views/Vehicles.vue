<template>
  <div>
    <!-- Statistics Card -->
    <a-card title="Статистика КПП" :bordered="false" style="margin-bottom: 16px;">
      <template #extra>
        <a-button size="small" @click="fetchGateStats">
          <template #icon>
            <ReloadOutlined />
          </template>
        </a-button>
      </template>

      <!-- Stats Row 1: Current State -->
      <a-row :gutter="[16, 16]" style="margin-bottom: 16px;">
        <a-col :xs="12" :sm="6">
          <a-statistic title="На терминале" :value="gateStats.total" :loading="statsLoading">
            <template #prefix><CarOutlined /></template>
          </a-statistic>
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic title="Легковых" :value="gateStats.light" :value-style="{ color: '#1890ff' }" :loading="statsLoading">
            <template #prefix><UserOutlined /></template>
          </a-statistic>
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic title="Грузовых" :value="gateStats.cargo" :value-style="{ color: '#faad14' }" :loading="statsLoading">
            <template #prefix><ShoppingOutlined /></template>
          </a-statistic>
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Задержанных (>24ч)"
            :value="gateStats.overstayers"
            :value-style="{ color: gateStats.overstayers > 0 ? '#ff4d4f' : '#52c41a' }"
            :loading="statsLoading"
          >
            <template #prefix>
              <WarningOutlined v-if="gateStats.overstayers > 0" />
              <CheckCircleOutlined v-else />
            </template>
          </a-statistic>
        </a-col>
      </a-row>

      <!-- Stats Row 2: Trends & Extremes -->
      <a-row :gutter="[16, 16]">
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Среднее время (ч)"
            :value="gateStats.avgDwellHours"
            :precision="1"
            :loading="statsLoading"
          >
            <template #prefix><ClockCircleOutlined /></template>
          </a-statistic>
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Въездов (30 дней)"
            :value="gateStats.entriesLast30Days"
            :value-style="{ color: '#52c41a' }"
            :loading="statsLoading"
          >
            <template #prefix><LoginOutlined /></template>
          </a-statistic>
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Выездов (30 дней)"
            :value="gateStats.exitsLast30Days"
            :value-style="{ color: '#1890ff' }"
            :loading="statsLoading"
          >
            <template #prefix><LogoutOutlined /></template>
          </a-statistic>
        </a-col>
        <a-col :xs="12" :sm="6">
          <div class="longest-stay-stat" v-if="!statsLoading">
            <div class="ant-statistic-title">Дольше всех на терминале</div>
            <div class="ant-statistic-content" v-if="gateStats.longestStay.plate">
              <a-tag :color="gateStats.longestStay.hours > 24 ? 'red' : 'blue'">
                {{ gateStats.longestStay.plate }}
              </a-tag>
              <span :style="{ color: gateStats.longestStay.hours > 24 ? '#ff4d4f' : 'inherit', marginLeft: '8px' }">
                {{ gateStats.longestStay.hours }}ч
              </span>
            </div>
            <div class="ant-statistic-content" v-else style="color: #999;">—</div>
          </div>
          <a-skeleton v-else :paragraph="false" active />
        </a-col>
      </a-row>
    </a-card>

    <!-- Table Card -->
    <a-card title="Транспорт" :bordered="false">
      <template #extra>
        <a-space>
          <a-button type="primary" @click="showCreateModal">
            <template #icon>
              <PlusOutlined />
            </template>
            Создать запись
          </a-button>
        </a-space>
      </template>

      <!-- Enhanced Toolbar -->
      <div style="margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">
        <!-- Search -->
        <a-input-search
          v-model:value="searchText"
          placeholder="Поиск по гос. номеру"
          style="width: 220px;"
          @search="handleSearch"
          @pressEnter="handleSearch"
          allow-clear
        />

        <!-- Date Range -->
        <a-range-picker
          v-model:value="dateRange"
          format="DD.MM.YYYY"
          :placeholder="['Дата с', 'Дата по']"
          style="width: 260px;"
          @change="handleDateRangeChange"
          allow-clear
        />

        <div style="flex: 1;" />

        <!-- Column Settings -->
        <a-popover trigger="click" placement="bottomRight">
          <template #content>
            <div style="width: 250px; max-height: 400px; overflow-y: auto;">
              <a-checkbox-group v-model:value="visibleColumns" style="display: flex; flex-direction: column; gap: 8px;">
                <a-checkbox v-for="col in columnOptions" :key="col.value" :value="col.value">
                  {{ col.label }}
                </a-checkbox>
              </a-checkbox-group>
            </div>
          </template>
          <a-button>
            <template #icon>
              <SettingOutlined />
            </template>
            Столбцы
          </a-button>
        </a-popover>

        <!-- Export -->
        <a-button @click="exportToExcel" :loading="exportLoading">
          <template #icon>
            <DownloadOutlined />
          </template>
          Excel
        </a-button>
      </div>

      <a-tabs v-model:activeKey="activeVehicleTypeTab" @change="handleVehicleTypeTabChange" style="margin-bottom: 0px;">
      <a-tab-pane key="all" tab="Все" />
      <a-tab-pane key="LIGHT" tab="Легковой" />
      <a-tab-pane key="CARGO" tab="Грузовой" />
    </a-tabs>

    <a-tabs v-model:activeKey="activeStatusTab" @change="handleStatusTabChange" style="margin-bottom: 6px;">
      <a-tab-pane key="all" tab="Все статусы" />
      <a-tab-pane key="WAITING" tab="Ожидает" />
      <a-tab-pane key="ON_TERMINAL" tab="На терминале" />
      <a-tab-pane key="EXITED" tab="Выехал" />
      <a-tab-pane key="CANCELLED" tab="Отменён" />
    </a-tabs>

    <div style="margin-bottom: 16px;">
      <a-select v-model:value="selectedCustomerFilter" show-search allow-clear placeholder="Фильтр по клиенту"
        style="width: 300px;" :filter-option="filterCustomerOption" @change="handleCustomerFilterChange">
        <a-select-option v-for="cust in customers" :key="cust.id" :value="cust.id">
          {{ cust.first_name }} ({{ cust.phone_number }})
        </a-select-option>
      </a-select>
    </div>

    <a-table :columns="filteredColumns" :data-source="dataSource" :pagination="pagination" :loading="loading"
      @change="handleTableChange" bordered :scroll="{ x: 1500 }" size="small"
      :locale="{ emptyText: 'Нет записей транспорта. Попробуйте изменить фильтры или создайте новую запись.' }">
      <template #bodyCell="{ column, index, record }">
        <template v-if="column.key === 'number'">
          {{ (pagination.current - 1) * pagination.pageSize + index + 1 }}
        </template>
        <template v-else-if="column.key === 'license_plate'">
          <a-tag color="blue">{{ record.license_plate }}</a-tag>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="getStatusColor(record.status)">
            {{ record.status_display }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'customer'">
          <div v-if="record.customer_name !== '—'">
            <router-link v-if="record.customer_company_slug"
              :to="{ path: `/accounts/companies/${record.customer_company_slug}/users`, query: { user: record.customer_id } }">
              {{ record.customer_name }}
            </router-link>
            <div style="font-size: 12px; color: #999;">{{ record.customer_phone }}</div>
          </div>
          <span v-else style="color: #999;">—</span>
        </template>
        <template v-else-if="column.key === 'manager'">
          <div v-if="record.manager_name !== '—'">
            <div>{{ record.manager_name }}</div>
            <div style="font-size: 12px; color: #999;">{{ record.manager_phone }}</div>
          </div>
          <span v-else style="color: #999;">—</span>
        </template>
        <template v-else-if="column.key === 'entry_photos'">
          <a-image-preview-group>
            <a-space>
              <a-image v-for="photo in record.entry_photos.slice(0, 3)" :key="photo.id" :width="36" :height="36"
                :src="photo.file_url" :preview="{ src: photo.file_url }"
                style="object-fit: cover; border-radius: 4px;" />
              <a-tag v-if="record.entry_photos.length > 3" color="blue">
                +{{ record.entry_photos.length - 3 }}
              </a-tag>
            </a-space>
          </a-image-preview-group>
        </template>
        <template v-else-if="column.key === 'exit_photos'">
          <a-image-preview-group v-if="record.exit_photos.length > 0">
            <a-space>
              <a-image v-for="photo in record.exit_photos.slice(0, 3)" :key="photo.id" :width="36" :height="36"
                :src="photo.file_url" :preview="{ src: photo.file_url }"
                style="object-fit: cover; border-radius: 4px;" />
              <a-tag v-if="record.exit_photos.length > 3" color="blue">
                +{{ record.exit_photos.length - 3 }}
              </a-tag>
            </a-space>
          </a-image-preview-group>
          <span v-else style="color: #999;">Нет фото</span>
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
            <!-- Check-In: WAITING → ON_TERMINAL -->
            <a-tooltip title="Въезд (Check-In)" v-if="record.status === 'WAITING'">
              <a-button type="link" size="small" style="color: #52c41a;" @click="handleCheckIn(record)">
                <template #icon>
                  <CheckOutlined />
                </template>
              </a-button>
            </a-tooltip>
            <!-- Cancel: WAITING → CANCELLED -->
            <a-tooltip title="Отменить" v-if="record.status === 'WAITING'">
              <a-button type="link" size="small" style="color: #ff4d4f;" @click="showCancelConfirm(record)">
                <template #icon>
                  <CloseOutlined />
                </template>
              </a-button>
            </a-tooltip>
            <!-- Exit: ON_TERMINAL → EXITED -->
            <a-tooltip title="Выезд" v-if="record.status === 'ON_TERMINAL'">
              <a-button type="link" size="small" style="color: #52c41a;" @click="showExitModal(record)">
                <template #icon>
                  <ExportOutlined />
                </template>
              </a-button>
            </a-tooltip>
            <!-- Revert: EXITED → ON_TERMINAL -->
            <a-button
              v-if="record.status === 'EXITED'"
              type="link"
              size="small"
              style="color: #faad14;"
              @click="showRevertModal(record)"
            >
              <RollbackOutlined /> Вернуть
            </a-button>
            <a-tooltip title="Удалить">
              <a-button type="link" size="small" danger @click="showDeleteConfirm(record)">
                <template #icon>
                  <DeleteOutlined />
                </template>
              </a-button>
            </a-tooltip>
          </a-space>
        </template>
      </template>
    </a-table>
  </a-card>

  <!-- Create Modal -->
  <a-modal v-model:open="createModalVisible" title="Создать запись транспортного средства" @ok="handleCreateSubmit"
    @cancel="handleCreateCancel" :confirm-loading="createLoading" width="800px">
    <a-form ref="createFormRef" :model="createForm" layout="vertical">
      <!-- License Plate and Vehicle Type -->
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item
            label="Гос. номер"
            name="license_plate"
            required
            :validate-status="plateOnTerminal ? 'error' : undefined"
            :help="plateOnTerminal ? `Транспорт ${createForm.license_plate} уже на терминале` : undefined"
          >
            <a-input v-model:value="createForm.license_plate" placeholder="Введите гос. номер">
              <template #suffix>
                <LoadingOutlined v-if="plateCheckLoading" spin />
              </template>
            </a-input>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="Тип ТС" name="vehicle_type" required>
            <a-select v-model:value="createForm.vehicle_type" placeholder="Выберите тип ТС">
              <a-select-option v-for="opt in choices.vehicle_types" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Customer -->
      <a-row :gutter="16">
        <a-col :span="24">
          <a-form-item label="Клиент" name="customer">
            <a-select v-model:value="createForm.customer" show-search allow-clear placeholder="Выберите клиента"
              :filter-option="filterCustomerOption">
              <a-select-option v-for="cust in customers" :key="cust.id" :value="cust.id">
                {{ cust.first_name }} ({{ cust.phone_number }})
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Light Vehicle: Visitor Type -->
      <a-row :gutter="16" v-if="isCreateLightVehicle">
        <a-col :span="12">
          <a-form-item label="Тип посетителя" required>
            <a-select v-model:value="createForm.visitor_type" placeholder="Выберите тип посетителя">
              <a-select-option v-for="opt in choices.visitor_types" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Cargo Vehicle: Transport Type and Load Status -->
      <a-row :gutter="16" v-if="isCreateCargoVehicle">
        <a-col :span="12">
          <a-form-item label="Тип транспорта" required>
            <a-select v-model:value="createForm.transport_type" placeholder="Выберите тип транспорта">
              <a-select-option v-for="opt in choices.transport_types" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="Статус загрузки въезд" required>
            <a-select v-model:value="createForm.entry_load_status" placeholder="Выберите статус">
              <a-select-option v-for="opt in choices.load_statuses" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Cargo Vehicle with Load: Cargo Type -->
      <a-row :gutter="16" v-if="isCreateCargoVehicle && isCreateCargoLoaded">
        <a-col :span="12">
          <a-form-item label="Тип груза" required>
            <a-select v-model:value="createForm.cargo_type" placeholder="Выберите тип груза">
              <a-select-option v-for="opt in choices.cargo_types" :key="opt.value" :value="opt.value"
                :disabled="opt.value === 'CONTAINER' && !isCreateContainerCapableTransport">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Container Cargo: Container Size and Load Status -->
      <a-row :gutter="16" v-if="isCreateCargoVehicle && isCreateCargoLoaded && isCreateContainerCargo">
        <a-col :span="12">
          <a-form-item label="Размер контейнера" required>
            <a-select v-model:value="createForm.container_size" placeholder="Выберите размер">
              <a-select-option v-for="opt in choices.container_sizes" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="Статус загрузки контейнера" required>
            <a-select v-model:value="createForm.container_load_status" placeholder="Выберите статус">
              <a-select-option v-for="opt in choices.load_statuses" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Destination -->
      <a-row :gutter="16" v-if="isCreateCargoVehicle">
        <a-col :span="24">
          <a-form-item label="Назначение" required>
            <a-select v-model:value="createForm.destination" show-search :filter-option="filterOption"
              placeholder="Выберите назначение">
              <a-select-option v-for="dest in destinations" :key="dest.id" :value="dest.id">
                {{ dest.zone }} - {{ dest.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>
    </a-form>
  </a-modal>

  <!-- Edit Modal -->
  <a-modal v-model:open="editModalVisible" title="Редактировать транспортное средство" @ok="handleEditSubmit"
    @cancel="handleEditCancel" :confirm-loading="editLoading" width="800px">
    <a-form ref="editFormRef" :model="editForm" layout="vertical">
      <!-- License Plate and Vehicle Type (Always visible) -->
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="Гос. номер" name="license_plate" required>
            <a-input v-model:value="editForm.license_plate" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="Тип ТС" name="vehicle_type" required>
            <a-select v-model:value="editForm.vehicle_type">
              <a-select-option v-for="opt in choices.vehicle_types" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Customer -->
      <a-row :gutter="16">
        <a-col :span="24">
          <a-form-item label="Клиент" name="customer">
            <a-select v-model:value="editForm.customer" show-search allow-clear placeholder="Выберите клиента"
              :filter-option="filterCustomerOption">
              <a-select-option v-for="cust in customers" :key="cust.id" :value="cust.id">
                {{ cust.first_name }} ({{ cust.phone_number }})
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Light Vehicle: Visitor Type -->
      <a-row :gutter="16" v-if="isLightVehicle">
        <a-col :span="12">
          <a-form-item label="Тип посетителя" required>
            <a-select v-model:value="editForm.visitor_type">
              <a-select-option v-for="opt in choices.visitor_types" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Cargo Vehicle: Transport Type and Load Status -->
      <a-row :gutter="16" v-if="isCargoVehicle">
        <a-col :span="12">
          <a-form-item label="Тип транспорта" required>
            <a-select v-model:value="editForm.transport_type">
              <a-select-option v-for="opt in choices.transport_types" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="Статус загрузки въезд" required>
            <a-select v-model:value="editForm.entry_load_status">
              <a-select-option v-for="opt in choices.load_statuses" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Cargo Vehicle with Load: Cargo Type -->
      <a-row :gutter="16" v-if="isCargoVehicle && isCargoLoaded">
        <a-col :span="12">
          <a-form-item label="Тип груза" required>
            <a-select v-model:value="editForm.cargo_type">
              <a-select-option v-for="opt in choices.cargo_types" :key="opt.value" :value="opt.value"
                :disabled="opt.value === 'CONTAINER' && !isEditContainerCapableTransport">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Container Cargo: Container Size and Load Status -->
      <a-row :gutter="16" v-if="isCargoVehicle && isCargoLoaded && isContainerCargo">
        <a-col :span="12">
          <a-form-item label="Размер контейнера" required>
            <a-select v-model:value="editForm.container_size">
              <a-select-option v-for="opt in choices.container_sizes" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="Статус загрузки контейнера" required>
            <a-select v-model:value="editForm.container_load_status">
              <a-select-option v-for="opt in choices.load_statuses" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Destination (shown for cargo vehicles when needed, or light vehicles if applicable) -->
      <a-row :gutter="16" v-if="isCargoVehicle">
        <a-col :span="24">
          <a-form-item label="Назначение" required>
            <a-select v-model:value="editForm.destination" show-search :filter-option="filterOption">
              <a-select-option v-for="dest in destinations" :key="dest.id" :value="dest.id">
                {{ dest.zone }} - {{ dest.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Exit Load Status (Optional) -->
      <a-row :gutter="16" v-if="isCargoVehicle">
        <a-col :span="12">
          <a-form-item label="Статус загрузки выезд">
            <a-select v-model:value="editForm.exit_load_status" allow-clear>
              <a-select-option v-for="opt in choices.load_statuses" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Exit Time (Optional - for manual exit time setting) -->
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="Время выезда (опционально)">
            <a-date-picker
              v-model:value="editForm.exit_time"
              :show-time="{ format: 'HH:mm' }"
              format="DD.MM.YYYY HH:mm"
              placeholder="Выберите время выезда"
              style="width: 100%;"
              :value-format="undefined"
            />
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Photos Preview Section -->
      <a-divider v-if="editForm.entry_photos.length > 0 || editForm.exit_photos.length > 0">Фотографии</a-divider>

      <a-row :gutter="16" v-if="editForm.entry_photos.length > 0">
        <a-col :span="24">
          <a-form-item label="Фото при въезде">
            <a-image-preview-group>
              <a-space>
                <a-image
                  v-for="photo in editForm.entry_photos"
                  :key="photo.id"
                  :width="80"
                  :height="80"
                  :src="photo.thumbnail_url || photo.image_url"
                  :preview="{ src: photo.image_url }"
                  style="object-fit: cover; border-radius: 4px;"
                />
              </a-space>
            </a-image-preview-group>
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16" v-if="editForm.exit_photos.length > 0">
        <a-col :span="24">
          <a-form-item label="Фото при выезде">
            <a-image-preview-group>
              <a-space>
                <a-image
                  v-for="photo in editForm.exit_photos"
                  :key="photo.id"
                  :width="80"
                  :height="80"
                  :src="photo.thumbnail_url || photo.image_url"
                  :preview="{ src: photo.image_url }"
                  style="object-fit: cover; border-radius: 4px;"
                />
              </a-space>
            </a-image-preview-group>
          </a-form-item>
        </a-col>
      </a-row>
    </a-form>
  </a-modal>

  <!-- Exit Modal - using extracted component -->
  <VehicleExitModal
    ref="exitModalRef"
    v-model:open="exitModalVisible"
    :load-statuses="choices.load_statuses"
    @success="handleExitSuccess"
  />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed, watch } from 'vue';
import { debounce } from 'lodash-es';
import { message, Modal } from 'ant-design-vue';
import type { FormInstance } from 'ant-design-vue';
import { handleFormError } from '../utils/formErrors';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CarOutlined,
  UserOutlined,
  ShoppingOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  LoginOutlined,
  LogoutOutlined,
  ExportOutlined,
  SettingOutlined,
  DownloadOutlined,
  RollbackOutlined,
  CheckOutlined,
  CloseOutlined,
  LoadingOutlined,
} from '@ant-design/icons-vue';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import { http } from '../utils/httpClient';
import { formatDateTime } from '../utils/dateFormat';
import {
  getStatusColor,
  getChoiceLabel,
  isLightVehicle as isLightVehicleType,
  isCargoVehicle as isCargoVehicleType,
  isCargoLoaded as isCargoLoadedStatus,
  isContainerCargo as isContainerCargoType,
  isContainerCapableTransport,
} from '../utils/vehicleHelpers';

// Extracted modules
import type {
  Photo,
  Vehicle,
  VehicleRecord,
  Destination,
  VehicleChoices,
  CustomerOption,
} from '../types/vehicle';
import { VEHICLE_COLUMNS } from '../constants/vehicleColumns';
import { useVehicleStats } from '../composables/useVehicleStats';
import { exportVehiclesToExcel } from '../services/vehicleExportService';
import VehicleExitModal from '../components/VehicleExitModal.vue';

// Use imported types from types/vehicle.ts and constants from vehicleColumns.ts
const columns = VEHICLE_COLUMNS;

const dataSource = ref<VehicleRecord[]>([]);
const loading = ref(false);
const activeVehicleTypeTab = ref('all');
const activeStatusTab = ref('all');
const selectedCustomerFilter = ref<number | null>(null);
const pagination = ref({
  current: 1,
  pageSize: 25,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '25', '50', '100'],
});

// Date range filter
const dateRange = ref<[Dayjs, Dayjs] | null>(null);

// Column visibility
const visibleColumns = ref<string[]>([
  'number', 'license_plate', 'status', 'customer', 'vehicle_type',
  'entry_photos', 'exit_photos', 'entry_time', 'exit_time', 'dwell_time_hours', 'actions'
]);

const columnOptions = [
  { label: '№', value: 'number' },
  { label: 'Гос. номер', value: 'license_plate' },
  { label: 'Статус', value: 'status' },
  { label: 'Клиент', value: 'customer' },
  { label: 'Менеджер', value: 'manager' },
  { label: 'Тип ТС', value: 'vehicle_type' },
  { label: 'Фото въезда', value: 'entry_photos' },
  { label: 'Время въезда', value: 'entry_time' },
  { label: 'Тип посетителя', value: 'visitor_type' },
  { label: 'Тип транспорта', value: 'transport_type' },
  { label: 'Статус загрузки въезд', value: 'entry_load_status' },
  { label: 'Тип груза', value: 'cargo_type' },
  { label: 'Размер контейнера', value: 'container_size' },
  { label: 'Фото выезда', value: 'exit_photos' },
  { label: 'Время выезда', value: 'exit_time' },
  { label: 'Статус загрузки выезд', value: 'exit_load_status' },
  { label: 'Время пребывания', value: 'dwell_time_hours' },
  { label: 'Действия', value: 'actions' },
];

// Computed filtered columns based on visibility
const filteredColumns = computed(() => {
  return columns.filter(col => visibleColumns.value.includes(col.key as string));
});

// License plate search
const searchText = ref('');

// Excel export
const exportLoading = ref(false);

// License plate on-terminal validation state
const plateCheckLoading = ref(false);
const plateOnTerminal = ref(false);
const plateOnTerminalEntry = ref<{ id: number; license_plate: string; entry_time: string } | null>(null);

// Check if license plate is already on terminal
const checkPlateOnTerminal = async (plate: string) => {
  if (!plate || plate.length < 3) {
    plateOnTerminal.value = false;
    plateOnTerminalEntry.value = null;
    return;
  }

  try {
    plateCheckLoading.value = true;
    const data = await http.get<{ on_terminal: boolean; entry?: { id: number; license_plate: string; entry_time: string } }>(
      `/vehicles/entries/check-plate/?license_plate=${encodeURIComponent(plate)}`
    );
    plateOnTerminal.value = data.on_terminal;
    plateOnTerminalEntry.value = data.entry || null;
  } catch (error) {
    console.error('Error checking plate:', error);
    plateOnTerminal.value = false;
    plateOnTerminalEntry.value = null;
  } finally {
    plateCheckLoading.value = false;
  }
};

// Debounced version (400ms delay for responsive UX)
const debouncedCheckPlate = debounce(checkPlateOnTerminal, 400);

// Export using extracted service
const exportToExcel = async () => {
  try {
    exportLoading.value = true;
    const count = await exportVehiclesToExcel({
      vehicleType: activeVehicleTypeTab.value,
      status: activeStatusTab.value,
      searchText: searchText.value,
      dateRange: dateRange.value,
    });
    message.success(`Экспортировано ${count} записей`);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'Не удалось экспортировать данные транспорта. Попробуйте снова.';
    message.error(errorMsg);
    console.error('Export error:', error);
  } finally {
    exportLoading.value = false;
  }
};

// Handle date range change
const handleDateRangeChange = () => {
  pagination.value.current = 1;
  fetchVehicles(1, pagination.value.pageSize);
};

// Handle search
const handleSearch = () => {
  pagination.value.current = 1;
  fetchVehicles(1, pagination.value.pageSize);
};

const fetchVehicles = async (page?: number, pageSize?: number) => {
  try {
    loading.value = true;

    const currentPage = page || pagination.value.current;
    const currentPageSize = pageSize || pagination.value.pageSize;

    const params = new URLSearchParams();
    params.append('page', currentPage.toString());
    params.append('page_size', currentPageSize.toString());

    // Apply vehicle type filter based on active tab
    if (activeVehicleTypeTab.value !== 'all') {
      params.append('vehicle_type', activeVehicleTypeTab.value);
    }

    // Apply status filter based on active status tab
    if (activeStatusTab.value !== 'all') {
      params.append('status', activeStatusTab.value);
    }

    // Apply customer filter
    if (selectedCustomerFilter.value) {
      params.append('customer', selectedCustomerFilter.value.toString());
    }

    // Apply license plate search
    if (searchText.value.trim()) {
      params.append('license_plate', searchText.value.trim());
    }

    // Apply date range filter
    if (dateRange.value) {
      params.append('entry_time_after', dateRange.value[0].format('YYYY-MM-DD'));
      params.append('entry_time_before', dateRange.value[1].format('YYYY-MM-DD'));
    }

    const data = await http.get<{ count: number; results: Vehicle[] }>(`/vehicles/entries/?${params.toString()}`);

    dataSource.value = data.results.map((vehicle) => ({
      key: vehicle.id.toString(),
      id: vehicle.id,
      status: vehicle.status,
      status_display: vehicle.status_display,
      license_plate: vehicle.license_plate,
      entry_photos: vehicle.entry_photos,
      entry_time: vehicle.entry_time ? formatDateTime(vehicle.entry_time) : '—',
      customer_id: vehicle.customer?.id || null,
      customer_name: vehicle.customer?.name || '—',
      customer_phone: vehicle.customer?.phone || '',
      customer_company_slug: vehicle.customer?.company_slug || '',
      manager_name: vehicle.manager?.name || '—',
      manager_phone: vehicle.manager?.phone || '',
      vehicle_type: vehicle.vehicle_type,
      vehicle_type_display: getChoiceLabel(choices.value.vehicle_types, vehicle.vehicle_type),
      visitor_type: vehicle.visitor_type || '—',
      visitor_type_display: getChoiceLabel(choices.value.visitor_types, vehicle.visitor_type),
      transport_type: vehicle.transport_type || '',
      transport_type_display: getChoiceLabel(choices.value.transport_types, vehicle.transport_type),
      entry_load_status: vehicle.entry_load_status || '',
      entry_load_status_display: getChoiceLabel(choices.value.load_statuses, vehicle.entry_load_status),
      cargo_type: vehicle.cargo_type || '',
      cargo_type_display: getChoiceLabel(choices.value.cargo_types, vehicle.cargo_type),
      container_size: vehicle.container_size || '',
      container_size_display: getChoiceLabel(choices.value.container_sizes, vehicle.container_size),
      container_load_status: vehicle.container_load_status || '—',
      container_load_status_display: getChoiceLabel(choices.value.load_statuses, vehicle.container_load_status),
      destination: vehicle.destination,
      exit_photos: vehicle.exit_photos,
      exit_time: vehicle.exit_time ? formatDateTime(vehicle.exit_time) : '—',
      exit_load_status: vehicle.exit_load_status || '—',
      exit_load_status_display: getChoiceLabel(choices.value.load_statuses, vehicle.exit_load_status),
      is_on_terminal: vehicle.is_on_terminal,
      dwell_time_hours: vehicle.dwell_time_hours !== null ? vehicle.dwell_time_hours.toFixed(2) : '—',
    }));

    pagination.value.total = data.count;
    pagination.value.current = currentPage;
    pagination.value.pageSize = currentPageSize;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка загрузки данных');
  } finally {
    loading.value = false;
  }
};

const handleTableChange = (pag: { current: number; pageSize: number }) => {
  fetchVehicles(pag.current, pag.pageSize);
};

const handleVehicleTypeTabChange = () => {
  // Reset to first page when changing vehicle type tab
  pagination.value.current = 1;
  fetchVehicles(1, pagination.value.pageSize);
};

const handleStatusTabChange = () => {
  // Reset to first page when changing status tab
  pagination.value.current = 1;
  fetchVehicles(1, pagination.value.pageSize);
};

const handleCustomerFilterChange = () => {
  // Reset to first page when changing customer filter
  pagination.value.current = 1;
  fetchVehicles(1, pagination.value.pageSize);
};

// getStatusColor is now imported from '../utils/vehicleHelpers'

// Destinations (interface imported from types/vehicle.ts)
const destinations = ref<Destination[]>([]);

const fetchDestinations = async () => {
  try {
    const data = await http.get<{ results: Destination[] } | Destination[]>('/vehicles/destinations/');

    if (Array.isArray(data)) {
      destinations.value = data;
    } else if (data && 'results' in data) {
      destinations.value = data.results;
    }
  } catch (error) {
    console.error('Error fetching destinations:', error);
  }
};

// Ant Design Select filter option - VNode children structure
const filterOption = (input: string, option: { children?: Array<{ children?: string }> }) => {
  const text = option.children?.[0]?.children ?? '';
  return text.toLowerCase().indexOf(input.toLowerCase()) >= 0;
};

// Choices (interfaces imported from types/vehicle.ts)
const choices = ref<VehicleChoices>({
  vehicle_types: [],
  visitor_types: [],
  transport_types: [],
  load_statuses: [],
  cargo_types: [],
  container_sizes: [],
});

// Gate Statistics - using extracted composable
const { gateStats, statsLoading, fetchGateStats } = useVehicleStats();

const fetchChoices = async () => {
  try {
    const data = await http.get<{ data: VehicleChoices }>('/vehicles/choices/');
    choices.value = data.data;
  } catch (error) {
    console.error('Error fetching choices:', error);
  }
};

// getChoiceLabel is now imported from '../utils/vehicleHelpers'

// Customers (interface imported from types/vehicle.ts)
const customers = ref<CustomerOption[]>([]);

const fetchCustomers = async () => {
  try {
    const data = await http.get<{ results: CustomerOption[] }>('/auth/customers/?page_size=1000');
    customers.value = data.results;
  } catch (error) {
    console.error('Error fetching customers:', error);
  }
};

const filterCustomerOption = (input: string, option: { children?: Array<{ children?: string }> }) => {
  const text = option.children?.[0]?.children ?? '';
  return text.toLowerCase().indexOf(input.toLowerCase()) >= 0;
};

// Create modal state
const createModalVisible = ref(false);
const createLoading = ref(false);
const createFormRef = ref<FormInstance>();
const createForm = reactive({
  license_plate: '',
  vehicle_type: '',
  customer: null as number | null,
  visitor_type: null as string | null,
  transport_type: '',
  entry_load_status: '',
  cargo_type: '',
  container_size: '',
  container_load_status: null as string | null,
  destination: 0,
});

// Computed properties for create form conditional field visibility
// Using imported utility functions for consistency with tests
const isCreateLightVehicle = computed(() => isLightVehicleType(createForm.vehicle_type));
const isCreateCargoVehicle = computed(() => isCargoVehicleType(createForm.vehicle_type));
const isCreateCargoLoaded = computed(() => isCargoLoadedStatus(createForm.entry_load_status));
const isCreateContainerCargo = computed(() => isContainerCargoType(createForm.cargo_type));
const isCreateContainerCapableTransport = computed(() =>
  isContainerCapableTransport(createForm.transport_type)
);

// Watch for license plate changes to check if vehicle is on terminal
watch(() => createForm.license_plate, (newPlate) => {
  if (newPlate) {
    debouncedCheckPlate(newPlate);
  } else {
    plateOnTerminal.value = false;
    plateOnTerminalEntry.value = null;
  }
});

// Watchers for create form to reset dependent fields
watch(() => createForm.vehicle_type, (newType, oldType) => {
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
});

watch(() => createForm.transport_type, (newType, oldType) => {
  // Reset cargo type if switching to non-container capable transport
  // Using the utility function to check container-capable transports
  if (oldType && newType !== oldType) {
    if (!isContainerCapableTransport(newType) && createForm.cargo_type === 'CONTAINER') {
      createForm.cargo_type = '';
      createForm.container_size = '';
      createForm.container_load_status = null;
    }
  }
});

watch(() => createForm.entry_load_status, (newStatus, oldStatus) => {
  if (oldStatus && newStatus !== oldStatus) {
    if (newStatus === 'EMPTY') {
      createForm.cargo_type = '';
      createForm.container_size = '';
      createForm.container_load_status = null;
    }
  }
});

watch(() => createForm.cargo_type, (newType, oldType) => {
  if (oldType && newType !== oldType) {
    if (oldType === 'CONTAINER' && newType !== 'CONTAINER') {
      createForm.container_size = '';
      createForm.container_load_status = null;
    }
  }
});

const showCreateModal = () => {
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
  createModalVisible.value = true;
};

const handleCreateCancel = () => {
  createModalVisible.value = false;
};

const handleCreateSubmit = async () => {
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

    const requestBody: Record<string, string | number | null> = {
      license_plate: createForm.license_plate,
      vehicle_type: createForm.vehicle_type,
      customer_id: createForm.customer,  // Backend expects 'customer_id'
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
    fetchVehicles(pagination.value.current, pagination.value.pageSize);
    fetchGateStats(); // Refresh statistics after create
  } catch (error) {
    // Show field-level errors on form, or toast for general errors
    handleFormError(error, createFormRef.value);
  } finally {
    createLoading.value = false;
  }
};

// Edit modal state
const editModalVisible = ref(false);
const editLoading = ref(false);
const editFormRef = ref<FormInstance>();
const editForm = reactive({
  id: 0,
  license_plate: '',
  vehicle_type: '',
  customer: null as number | null,
  visitor_type: null as string | null,
  transport_type: '',
  entry_load_status: '',
  cargo_type: '',
  container_size: '',
  container_load_status: null as string | null,
  destination: 0,
  destination_zone: '',
  exit_load_status: null as string | null,
  exit_time: null as dayjs.Dayjs | null,  // Exit time field (null for DatePicker compatibility)
  entry_photos: [] as Photo[],
  exit_photos: [] as Photo[],
});

// Computed properties for conditional field visibility
// Using imported utility functions for consistency with tests
const isLightVehicle = computed(() => isLightVehicleType(editForm.vehicle_type));
const isCargoVehicle = computed(() => isCargoVehicleType(editForm.vehicle_type));
const isCargoLoaded = computed(() => isCargoLoadedStatus(editForm.entry_load_status));
const isContainerCargo = computed(() => isContainerCargoType(editForm.cargo_type));
// NOTE: Previously had incorrect values ['PLATFORM', 'FURA', 'PRICEP'] - now uses shared constant
const isEditContainerCapableTransport = computed(() =>
  isContainerCapableTransport(editForm.transport_type)
);

// Watchers to reset dependent fields when parent selections change
watch(() => editForm.vehicle_type, (newType, oldType) => {
  if (oldType && newType !== oldType) {
    // Reset all cargo-specific fields when switching from cargo
    if (oldType === 'CARGO') {
      editForm.transport_type = '';
      editForm.entry_load_status = '';
      editForm.cargo_type = '';
      editForm.container_size = '';
      editForm.container_load_status = null;
      editForm.destination = 0;
      editForm.destination_zone = '';
      editForm.exit_load_status = null;
    }
    // Reset visitor type when switching from light
    if (oldType === 'LIGHT') {
      editForm.visitor_type = null;
    }
  }
});

watch(() => editForm.transport_type, (newType, oldType) => {
  // Reset cargo type if switching to non-container capable transport
  // Using the utility function to check container-capable transports
  if (oldType && newType !== oldType) {
    if (!isContainerCapableTransport(newType) && editForm.cargo_type === 'CONTAINER') {
      editForm.cargo_type = '';
      editForm.container_size = '';
      editForm.container_load_status = null;
    }
  }
});

watch(() => editForm.entry_load_status, (newStatus, oldStatus) => {
  if (oldStatus && newStatus !== oldStatus) {
    // Reset cargo fields when switching to empty
    if (newStatus === 'EMPTY') {
      editForm.cargo_type = '';
      editForm.container_size = '';
      editForm.container_load_status = null;
    }
  }
});

watch(() => editForm.cargo_type, (newType, oldType) => {
  if (oldType && newType !== oldType) {
    // Reset container fields when switching away from container
    if (oldType === 'CONTAINER' && newType !== 'CONTAINER') {
      editForm.container_size = '';
      editForm.container_load_status = null;
    }
  }
});

// Automatically set zone when destination is selected
watch(() => editForm.destination, (newDestId) => {
  if (newDestId) {
    const dest = destinations.value.find(d => d.id === newDestId);
    if (dest) {
      editForm.destination_zone = dest.zone;
    }
  } else {
    editForm.destination_zone = '';
  }
});

// Store original record for comparison
let originalRecord: VehicleRecord | null = null;

const showEditModal = (record: VehicleRecord) => {
  // Store original record to detect changes
  originalRecord = { ...record };

  // Reset all fields first
  editForm.id = record.id;
  editForm.license_plate = record.license_plate;
  editForm.vehicle_type = record.vehicle_type;
  editForm.customer = record.customer_id;
  editForm.visitor_type = null;
  editForm.transport_type = record.transport_type || '';
  editForm.entry_load_status = record.entry_load_status || '';
  editForm.cargo_type = record.cargo_type || '';
  editForm.container_size = record.container_size || '';
  editForm.container_load_status = record.container_load_status === '—' ? null : record.container_load_status;

  // Set destination directly from record
  editForm.destination = record.destination || 0;
  // Zone will be set automatically by the watcher
  const destination = destinations.value.find(d => d.id === record.destination);
  editForm.destination_zone = destination?.zone || '';
  editForm.exit_load_status = record.exit_load_status === '—' ? null : record.exit_load_status;

  // NEW: Populate exit_time only if it exists (convert to dayjs, otherwise null)
  if (record.exit_time && record.exit_time !== '—') {
    editForm.exit_time = dayjs(record.exit_time);
  } else {
    editForm.exit_time = null;  // Use null instead of undefined for DatePicker
  }

  // Populate photos for preview
  editForm.entry_photos = record.entry_photos || [];
  editForm.exit_photos = record.exit_photos || [];

  editModalVisible.value = true;
};

const handleEditCancel = () => {
  editModalVisible.value = false;
  editForm.id = 0;
  editForm.license_plate = '';
  editForm.vehicle_type = '';
  editForm.customer = null;
  editForm.visitor_type = null;
  editForm.transport_type = '';
  editForm.entry_load_status = '';
  editForm.cargo_type = '';
  editForm.container_size = '';
  editForm.container_load_status = null;
  editForm.destination = 0;
  editForm.destination_zone = '';
  editForm.exit_load_status = null;
  editForm.exit_time = null;  // Use null instead of undefined for DatePicker
  originalRecord = null;  // Clear original record
};

const handleEditSubmit = async () => {
  // Basic validation
  if (!editForm.license_plate.trim()) {
    message.error('Пожалуйста, введите гос. номер');
    return;
  }

  if (!editForm.vehicle_type) {
    message.error('Пожалуйста, выберите тип ТС');
    return;
  }

  // Light vehicle validation
  if (editForm.vehicle_type === 'LIGHT') {
    if (!editForm.visitor_type) {
      message.error('Пожалуйста, выберите тип посетителя');
      return;
    }
  }

  // Cargo vehicle validation
  if (editForm.vehicle_type === 'CARGO') {
    if (!editForm.transport_type || !editForm.entry_load_status) {
      message.error('Пожалуйста, заполните все обязательные поля');
      return;
    }

    // Validate loaded cargo
    if (editForm.entry_load_status === 'LOADED') {
      if (!editForm.cargo_type) {
        message.error('Пожалуйста, выберите тип груза');
        return;
      }

      // Validate container fields
      if (editForm.cargo_type === 'CONTAINER') {
        if (!editForm.container_size || !editForm.container_load_status) {
          message.error('Пожалуйста, заполните данные контейнера');
          return;
        }
      }
    }

    // Validate destination for cargo
    if (!editForm.destination) {
      message.error('Пожалуйста, выберите назначение');
      return;
    }
  }

  try {
    editLoading.value = true;

    const requestBody: Record<string, string | number | null> = {};

    // Helper function to add field only if changed
    type FieldValue = string | number | null;
    const addField = (key: string, value: FieldValue) => {
      if (originalRecord && key in originalRecord) {
        // Compare with original value
        const originalValue = originalRecord[key as keyof VehicleRecord];
        if (value !== originalValue) {
          requestBody[key] = value;
        }
      } else {
        // New field, always include
        requestBody[key] = value;
      }
    };

    // Only include required fields that are actually changing
    // Always include license_plate (needed for validation)
    if (originalRecord?.license_plate !== editForm.license_plate) {
      requestBody.license_plate = editForm.license_plate;
    }

    // Only include vehicle_type if it's changing
    if (originalRecord?.vehicle_type !== editForm.vehicle_type) {
      requestBody.vehicle_type = editForm.vehicle_type;
    }

    // Add customer if changed (backend expects 'customer_id', not 'customer')
    if (originalRecord?.customer_id !== editForm.customer) {
      requestBody.customer_id = editForm.customer;
    }

    // Add fields based on vehicle type
    if (editForm.vehicle_type === 'LIGHT') {
      addField('visitor_type', editForm.visitor_type);
    } else if (editForm.vehicle_type === 'CARGO') {
      addField('transport_type', editForm.transport_type);
      addField('entry_load_status', editForm.entry_load_status);

      if (editForm.entry_load_status === 'LOADED') {
        addField('cargo_type', editForm.cargo_type);

        if (editForm.cargo_type === 'CONTAINER') {
          addField('container_size', editForm.container_size);
          addField('container_load_status', editForm.container_load_status);
        }
      }

      addField('destination', editForm.destination);
      addField('destination_zone', editForm.destination_zone);

      addField('exit_load_status', editForm.exit_load_status);
    }

    // NEW: Include exit_time if set (for manual exit time setting)
    if (editForm.exit_time != null && editForm.exit_time.isValid()) {
      requestBody.exit_time = editForm.exit_time.toISOString();
    }

    await http.patch(`/vehicles/entries/${editForm.id}/`, requestBody);

    message.success('Транспортное средство успешно обновлено');
    editModalVisible.value = false;
    fetchVehicles(pagination.value.current, pagination.value.pageSize);
    fetchGateStats(); // Refresh statistics after edit (status may change)
  } catch (error) {
    // Show field-level errors on form, or toast for general errors
    console.error('Edit submission error:', error);

    if (editFormRef.value) {
      handleFormError(error, editFormRef.value);
    } else {
      // Fallback: show error message
      const errorMessage = error instanceof Error
        ? error.message
        : 'Произошла ошибка при обновлении';
      message.error(errorMessage);
    }
  } finally {
    editLoading.value = false;
  }
};

// Exit modal - using extracted VehicleExitModal component
const exitModalVisible = ref(false);
const exitModalRef = ref<InstanceType<typeof VehicleExitModal>>();

const showExitModal = (record: VehicleRecord) => {
  exitModalRef.value?.initForm(record);
  exitModalVisible.value = true;
};

// Handle successful exit from the modal
const handleExitSuccess = () => {
  fetchVehicles(pagination.value.current, pagination.value.pageSize);
  fetchGateStats(); // Refresh statistics
};

// Revert exit functionality
const showRevertModal = (record: VehicleRecord) => {
  Modal.confirm({
    title: 'Вернуть транспорт на терминал?',
    content: `Вы уверены, что хотите отменить выезд транспорта "${record.license_plate}" и вернуть его статус "На терминале"?`,
    okText: 'Вернуть',
    okType: 'primary',
    cancelText: 'Отмена',
    maskClosable: true,
    async onOk() {
      await handleRevertExit(record);
    },
  });
};

const handleRevertExit = async (record: VehicleRecord) => {
  try {
    // Update vehicle: set status back to ON_TERMINAL, clear exit_time and exit_load_status
    await http.patch(`/vehicles/entries/${record.id}/`, {
      status: 'ON_TERMINAL',
      exit_time: null,
      exit_load_status: null,
    });

    message.success(`Транспорт ${record.license_plate} возвращён на терминал`);
    fetchVehicles(pagination.value.current, pagination.value.pageSize);
    fetchGateStats(); // Refresh statistics
  } catch (error) {
    message.error(error instanceof Error ? error.message : `Не удалось вернуть ${record.license_plate} на терминал. Попробуйте снова.`);
  }
};

// Check-In functionality (WAITING → ON_TERMINAL)
const handleCheckIn = async (record: VehicleRecord) => {
  try {
    // Use FormData for the check-in endpoint
    const formData = new FormData();
    formData.append('license_plate', record.license_plate);

    await http.upload('/vehicles/entries/check-in/', formData);

    message.success(`Транспорт ${record.license_plate} въехал на терминал`);
    fetchVehicles(pagination.value.current, pagination.value.pageSize);
    fetchGateStats(); // Refresh statistics after check-in
  } catch (error) {
    message.error(error instanceof Error ? error.message : `Не удалось зарегистрировать въезд ${record.license_plate}. Попробуйте снова.`);
  }
};

// Cancel functionality (WAITING → CANCELLED)
const showCancelConfirm = (record: VehicleRecord) => {
  Modal.confirm({
    title: 'Отменить заявку?',
    content: `Вы уверены, что хотите отменить заявку на транспорт "${record.license_plate}"?`,
    okText: 'Отменить заявку',
    okType: 'danger',
    cancelText: 'Назад',
    maskClosable: true,
    async onOk() {
      await handleCancel(record);
    },
  });
};

const handleCancel = async (record: VehicleRecord) => {
  try {
    await http.post(`/vehicles/entries/${record.id}/cancel/`);

    message.success(`Заявка на транспорт ${record.license_plate} отменена`);
    fetchVehicles(pagination.value.current, pagination.value.pageSize);
    fetchGateStats(); // Refresh statistics after cancel
  } catch (error) {
    message.error(error instanceof Error ? error.message : `Не удалось отменить заявку на ${record.license_plate}. Попробуйте снова.`);
  }
};

// Delete functionality
const showDeleteConfirm = (record: VehicleRecord) => {
  Modal.confirm({
    title: 'Удалить запись о транспортном средстве?',
    content: `Вы уверены, что хотите удалить запись о транспортном средстве "${record.license_plate}"?`,
    okText: 'Удалить',
    okType: 'danger',
    cancelText: 'Отмена',
    maskClosable: true,
    async onOk() {
      await handleDelete(record.id);
    },
  });
};

const handleDelete = async (vehicleId: number) => {
  try {
    await http.delete(`/vehicles/entries/${vehicleId}/`);

    message.success('Запись успешно удалена');
    fetchVehicles(pagination.value.current, pagination.value.pageSize);
    fetchGateStats(); // Refresh statistics after delete
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Не удалось удалить запись о транспорте. Попробуйте снова.');
  }
};

onMounted(async () => {
  await fetchChoices();
  fetchGateStats();
  fetchVehicles();
  fetchDestinations();
  fetchCustomers();
});
</script>

<style scoped>
.longest-stay-stat {
  line-height: 1.5;
}

.longest-stay-stat .ant-statistic-title {
  margin-bottom: 4px;
  color: rgba(0, 0, 0, 0.45);
  font-size: 14px;
}

.longest-stay-stat .ant-statistic-content {
  font-size: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  display: flex;
  align-items: center;
}
</style>
