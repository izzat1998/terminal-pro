<script setup lang="ts">
/**
 * PositionAlternativeGrid - Clickable alternative position cards
 *
 * Displays a grid of alternative positions for the user to choose from.
 * Each card shows the position coordinate and can be selected.
 */

import { EyeOutlined } from '@ant-design/icons-vue';
import type { Position } from '../../types/placement';

defineProps<{
  alternatives: Position[];
  selectedIndex: number;
}>();

const emit = defineEmits<{
  select: [index: number];
  preview: [position: Position];
}>();

// Format coordinate for display
function formatCoordinate(position: Position): string {
  return position.coordinate ||
    `${position.zone}-R${position.row.toString().padStart(2, '0')}-B${position.bay.toString().padStart(2, '0')}-T${position.tier}`;
}

// Get short format for compact display
function getShortCoordinate(position: Position): { zone: string; row: string; bay: string; tier: string } {
  return {
    zone: position.zone,
    row: position.row.toString().padStart(2, '0'),
    bay: position.bay.toString().padStart(2, '0'),
    tier: position.tier.toString(),
  };
}
</script>

<template>
  <div class="alternatives-section">
    <div class="section-header">
      <span class="section-title">Альтернативные позиции</span>
      <span class="section-hint">(нажмите для выбора)</span>
    </div>

    <div class="alternatives-grid">
      <div
        v-for="(alt, index) in alternatives"
        :key="formatCoordinate(alt)"
        class="alternative-card"
        :class="{ selected: selectedIndex === index }"
        @click="emit('select', index)"
      >
        <div class="card-content">
          <div class="position-mini-grid">
            <span class="mini-cell zone">{{ getShortCoordinate(alt).zone }}</span>
            <span class="mini-cell">{{ getShortCoordinate(alt).row }}</span>
            <span class="mini-cell">{{ getShortCoordinate(alt).bay }}</span>
            <span class="mini-cell tier">{{ getShortCoordinate(alt).tier }}</span>
          </div>
          <div class="coordinate-text">{{ formatCoordinate(alt) }}</div>
        </div>

        <a-button
          size="small"
          type="text"
          class="preview-btn"
          @click.stop="emit('preview', alt)"
        >
          <template #icon><EyeOutlined /></template>
        </a-button>

        <a-tag v-if="selectedIndex === index" color="purple" style="position: absolute; top: -6px; right: -6px; margin: 0; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; padding: 0; font-size: 10px; font-weight: bold;">
          ✓
        </a-tag>
      </div>
    </div>
  </div>
</template>

<style scoped>
.alternatives-section {
  margin-bottom: 12px;
}

.section-header {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 8px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #595959;
}

.section-hint {
  font-size: 11px;
  color: #8c8c8c;
}

/* Grid of alternative cards */
.alternatives-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

/* Individual alternative card */
.alternative-card {
  background: var(--ant-blue-1, #e6f4ff);
  border: 2px solid var(--ant-blue-3, #91caff);
  border-radius: 8px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alternative-card:hover {
  border-color: var(--ant-color-primary, #1677ff);
  box-shadow: 0 2px 6px rgba(22, 119, 255, 0.15);
}

.alternative-card.selected {
  border-color: var(--ant-purple-6, #722ed1);
  background: var(--ant-purple-1, #f9f0ff);
}

.card-content {
  flex: 1;
}

/* Mini position grid */
.position-mini-grid {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
}

.mini-cell {
  background: white;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 2px 6px;
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
  color: #262626;
}

.mini-cell.zone {
  background: var(--ant-color-primary, #1677ff);
  color: white;
  border-color: var(--ant-color-primary, #1677ff);
}

.mini-cell.tier {
  background: #f0f0f0;
}

.coordinate-text {
  font-family: monospace;
  font-size: 10px;
  color: #8c8c8c;
}

/* Preview button */
.preview-btn {
  padding: 2px 6px;
  height: 24px;
  color: #1677ff;
}

.preview-btn:hover {
  color: #4096ff;
  background: rgba(22, 119, 255, 0.1);
}


</style>
