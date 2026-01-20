<script setup lang="ts">
/**
 * Position Viewer Modal
 * Reusable modal with 2D/3D toggle for viewing container positions.
 * Can be used from Work Orders, Container tables, or anywhere position viewing is needed.
 */

import { ref, watch } from 'vue';
import {
  EnvironmentOutlined,
  CloseOutlined,
  AppstoreOutlined,
  BlockOutlined,
} from '@ant-design/icons-vue';
import ContainerLocationView from './ContainerLocationView.vue';
import PositionViewer3D from './PositionViewer3D.vue';

type ViewMode = '2d' | '3d';

interface Props {
  open: boolean;
  coordinate: string;
  containerNumber?: string;
  isoType?: string;
  status?: 'LADEN' | 'EMPTY';
  defaultMode?: ViewMode;
}

const props = withDefaults(defineProps<Props>(), {
  defaultMode: '2d',
});

const emit = defineEmits<{
  'update:open': [value: boolean];
}>();

// Current view mode
const viewMode = ref<ViewMode>(props.defaultMode);

// Reset to default mode when modal opens
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    viewMode.value = props.defaultMode;
  }
});

function handleClose(): void {
  emit('update:open', false);
}

// Tab items for the mode switcher
const tabItems = [
  { key: '2d', label: '2D', icon: AppstoreOutlined },
  { key: '3d', label: '3D', icon: BlockOutlined },
];
</script>

<template>
  <a-modal
    :open="open"
    :footer="null"
    :width="780"
    :body-style="{ padding: 0 }"
    centered
    destroy-on-close
    @update:open="emit('update:open', $event)"
    @cancel="handleClose"
  >
    <template #title>
      <div class="modal-header">
        <div class="modal-title">
          <EnvironmentOutlined class="title-icon" />
          <span>Position: {{ coordinate }}</span>
        </div>
        <div class="mode-tabs">
          <a-radio-group
            v-model:value="viewMode"
            button-style="solid"
            size="small"
          >
            <a-radio-button
              v-for="tab in tabItems"
              :key="tab.key"
              :value="tab.key"
            >
              <component :is="tab.icon" />
              {{ tab.label }}
            </a-radio-button>
          </a-radio-group>
        </div>
      </div>
    </template>

    <template #closeIcon>
      <CloseOutlined />
    </template>

    <div class="modal-content">
      <!-- 2D View -->
      <div v-show="viewMode === '2d'" class="view-container">
        <ContainerLocationView
          :location="coordinate"
          :container-number="containerNumber || ''"
          :iso-type="isoType"
          :status="status"
        />
      </div>

      <!-- 3D View -->
      <div v-show="viewMode === '3d'" class="view-container view-3d">
        <PositionViewer3D
          v-if="open && viewMode === '3d'"
          :coordinate="coordinate"
          :container-number="containerNumber"
        />
      </div>
    </div>

    <!-- Container info footer (if container provided) -->
    <div v-if="containerNumber" class="modal-footer">
      <div class="container-info">
        <a-tag color="blue" class="container-tag">{{ containerNumber }}</a-tag>
        <a-tag v-if="isoType">{{ isoType }}</a-tag>
        <a-tag v-if="status" :color="status === 'LADEN' ? 'green' : 'blue'">
          {{ status === 'LADEN' ? 'Laden' : 'Empty' }}
        </a-tag>
      </div>
    </div>
  </a-modal>
</template>

<style scoped>
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-right: 40px; /* Space for close button */
}

.modal-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: #722ed1;
  font-size: 18px;
}

.mode-tabs {
  display: flex;
  align-items: center;
}

.modal-content {
  min-height: 400px;
}

.view-container {
  padding: 0;
}

.view-3d {
  height: 450px;
}

.view-3d :deep(.position-viewer-3d) {
  height: 100%;
  border-radius: 0;
}

.modal-footer {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
}

.container-info {
  display: flex;
  gap: 8px;
  align-items: center;
}

.container-tag {
  font-weight: 600;
}

/* Override ContainerLocationView padding in modal context */
:deep(.location-view) {
  padding: 16px;
}
</style>
