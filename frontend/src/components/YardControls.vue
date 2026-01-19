<script setup lang="ts">
/**
 * YardControls - Floating control bar for 3D yard view toggles
 *
 * Provides toggle buttons for:
 * - Stats bar visibility (📊)
 * - Company cards visibility (🏢)
 *
 * Position: top-left of 3D canvas, always visible
 * Visual feedback: active state shows when panels are visible
 */

import {
  BarChartOutlined,
  BankOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue';

interface Props {
  showStats: boolean;
  showCompanies: boolean;
  loading?: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  'toggle-stats': [];
  'toggle-companies': [];
  'refresh': [];
}>();
</script>

<template>
  <div class="yard-controls">
    <a-tooltip title="Показать статистику" placement="right">
      <a-button
        :type="showStats ? 'primary' : 'default'"
        class="control-btn"
        :class="{ active: showStats }"
        @click="emit('toggle-stats')"
      >
        <template #icon><BarChartOutlined /></template>
      </a-button>
    </a-tooltip>

    <a-tooltip title="Показать компании" placement="right">
      <a-button
        :type="showCompanies ? 'primary' : 'default'"
        class="control-btn"
        :class="{ active: showCompanies }"
        @click="emit('toggle-companies')"
      >
        <template #icon><BankOutlined /></template>
      </a-button>
    </a-tooltip>

    <div class="control-divider" />

    <a-tooltip title="Обновить данные" placement="right">
      <a-button
        class="control-btn"
        :loading="loading"
        @click="emit('refresh')"
      >
        <template #icon><ReloadOutlined /></template>
      </a-button>
    </a-tooltip>
  </div>
</template>

<style scoped>
.yard-controls {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 15;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.control-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.control-btn:not(.active):hover {
  background: rgba(22, 119, 255, 0.08);
  border-color: rgba(22, 119, 255, 0.3);
}

.control-btn.active {
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.25);
}

.control-divider {
  width: 100%;
  height: 1px;
  background: rgba(0, 0, 0, 0.08);
  margin: 4px 0;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .yard-controls {
    background: rgba(30, 30, 30, 0.9);
    border-color: rgba(255, 255, 255, 0.08);
  }

  .control-divider {
    background: rgba(255, 255, 255, 0.12);
  }
}
</style>
