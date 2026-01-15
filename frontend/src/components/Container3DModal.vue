<script setup lang="ts">
/**
 * Container Location Modal
 * Displays a visual diagram showing where a container is located in the terminal yard.
 * Uses a simple 2D visualization for reliability and clarity.
 */

import { EnvironmentOutlined, CloseOutlined } from '@ant-design/icons-vue';
import ContainerLocationView from './ContainerLocationView.vue';

interface ContainerInfo {
  id: number;
  containerNumber: string;
  location: string;
  isoType?: string;
  status?: 'LADEN' | 'EMPTY';
}

defineProps<{
  open: boolean;
  container: ContainerInfo | null;
}>();

const emit = defineEmits<{
  'update:open': [value: boolean];
}>();

function handleClose() {
  emit('update:open', false);
}
</script>

<template>
  <a-modal
    :open="open"
    :footer="null"
    :width="750"
    :body-style="{ padding: 0 }"
    centered
    @update:open="emit('update:open', $event)"
    @cancel="handleClose"
  >
    <template #title>
      <div class="modal-title">
        <EnvironmentOutlined class="title-icon" />
        <span>Расположение контейнера</span>
      </div>
    </template>

    <template #closeIcon>
      <CloseOutlined />
    </template>

    <div class="modal-content">
      <ContainerLocationView
        v-if="container"
        :location="container.location"
        :container-number="container.containerNumber"
        :iso-type="container.isoType"
        :status="container.status"
      />
      <div v-else class="no-container">
        <a-empty description="Контейнер не выбран" />
      </div>
    </div>
  </a-modal>
</template>

<style scoped>
.modal-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: #722ed1;
  font-size: 18px;
}

.modal-content {
  max-height: 80vh;
  overflow-y: auto;
}

.no-container {
  padding: 40px;
}
</style>
