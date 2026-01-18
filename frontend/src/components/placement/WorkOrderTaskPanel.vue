<script setup lang="ts">
/**
 * WorkOrderTaskPanel - Collapsible side panel for pending work order tasks
 *
 * Overlays the 3D view on the right side, showing tasks awaiting completion.
 * Clicking a task focuses the camera on the target position in 3D.
 * Auto-refreshes every 30 seconds.
 */

import { ref, onMounted, onUnmounted } from 'vue';
import {
  UnorderedListOutlined,
  CheckCircleOutlined,
  RightOutlined,
  LeftOutlined,
} from '@ant-design/icons-vue';
import { useWorkOrderTasks } from '../../composables/useWorkOrderTasks';
import WorkOrderTaskCard from './WorkOrderTaskCard.vue';
import type { WorkOrder } from '../../types/placement';

const emit = defineEmits<{
  focusTask: [task: WorkOrder];
}>();

// State from composable
const {
  pendingTasks,
  activeVehicles,
  loading,
  taskCount,
  selectedTaskId,
  initialize,
  cleanup,
  selectTask,
  assignVehicle,
} = useWorkOrderTasks();

// Panel expanded state (default: expanded)
const isExpanded = ref(true);

// Toggle panel
function togglePanel(): void {
  isExpanded.value = !isExpanded.value;
}

// Handle task click - focus camera on position
function handleTaskClick(task: WorkOrder): void {
  selectTask(task.id);
  emit('focusTask', task);
}

// Handle vehicle assignment
async function handleAssign(taskId: number, vehicleId: number): Promise<void> {
  await assignVehicle(taskId, vehicleId);
}

// Initialize on mount
onMounted(async () => {
  await initialize();
});

// Cleanup on unmount
onUnmounted(() => {
  cleanup();
});
</script>

<template>
  <div :class="['task-panel-container', { 'is-collapsed': !isExpanded }]">
    <!-- Collapsed state: just a badge -->
    <div v-if="!isExpanded" class="collapsed-toggle" @click="togglePanel">
      <UnorderedListOutlined class="toggle-icon" />
      <a-badge
        :count="taskCount"
        :number-style="{
          backgroundColor: taskCount > 0 ? '#fa8c16' : '#52c41a',
          fontSize: '11px',
          minWidth: '18px',
          height: '18px',
          lineHeight: '18px',
        }"
      />
      <LeftOutlined class="arrow-icon" />
    </div>

    <!-- Expanded panel -->
    <div v-else class="task-panel">
      <!-- Header -->
      <div class="panel-header">
        <div class="header-title">
          <UnorderedListOutlined class="header-icon" />
          <span>Задания</span>
          <a-badge
            :count="taskCount"
            :number-style="{
              backgroundColor: taskCount > 0 ? '#fa8c16' : '#52c41a',
            }"
          />
        </div>
        <a-button type="text" size="small" @click="togglePanel">
          <template #icon><RightOutlined /></template>
        </a-button>
      </div>

      <!-- Loading state -->
      <div v-if="loading && pendingTasks.length === 0" class="panel-loading">
        <a-spin size="small" />
      </div>

      <!-- Empty state -->
      <div v-else-if="pendingTasks.length === 0" class="panel-empty">
        <div class="empty-content">
          <CheckCircleOutlined class="empty-icon" />
          <span class="empty-text">Нет активных заданий</span>
        </div>
      </div>

      <!-- Task list -->
      <div v-else class="panel-content">
        <WorkOrderTaskCard
          v-for="task in pendingTasks"
          :key="task.id"
          :task="task"
          :vehicles="activeVehicles"
          :is-selected="selectedTaskId === task.id"
          @click="handleTaskClick"
          @assign="handleAssign"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Container positioning - below the 3D view controls */
.task-panel-container {
  position: absolute;
  top: 56px;
  right: 12px;
  z-index: 10;
  transition: all 0.3s ease;
}

.task-panel-container.is-collapsed {
  width: auto;
}

/* Collapsed toggle button */
.collapsed-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  backdrop-filter: blur(8px);
  transition: all 0.2s ease;
}

.collapsed-toggle:hover {
  background: #fff;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
}

.toggle-icon {
  font-size: 16px;
  color: #fa8c16;
}

.arrow-icon {
  font-size: 12px;
  color: #8c8c8c;
}

/* Expanded panel */
.task-panel {
  width: 340px;
  max-height: calc(100vh - 200px);
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(8px);
}

/* Header */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
  color: #262626;
}

.header-icon {
  font-size: 16px;
  color: #fa8c16;
}

/* Loading */
.panel-loading {
  padding: 32px;
  text-align: center;
}

/* Empty state */
.panel-empty {
  padding: 32px 16px;
  text-align: center;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.empty-icon {
  font-size: 32px;
  color: #52c41a;
}

.empty-text {
  font-size: 13px;
  color: #8c8c8c;
}

/* Content list */
.panel-content {
  overflow-y: auto;
  flex: 1;
}

/* Scrollbar styling */
.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: #f0f0f0;
}

.panel-content::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb:hover {
  background: #bfbfbf;
}
</style>
