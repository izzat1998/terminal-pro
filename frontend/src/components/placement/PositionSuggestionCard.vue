<script setup lang="ts">
/**
 * PositionSuggestionCard - Primary recommendation card with position grid layout
 *
 * Displays the recommended position in a visual grid (Zone/Row/Bay/Tier)
 * with "Показать в 3D" button for camera focus.
 */

import { EyeOutlined } from '@ant-design/icons-vue';
import type { Position } from '../../types/placement';

const props = defineProps<{
  position: Position;
  reason: string;
  selected: boolean;
}>();

const emit = defineEmits<{
  select: [];
  preview: [position: Position];
}>();

// Format numbers with leading zeros for display
function formatNumber(num: number, digits: number = 2): string {
  return num.toString().padStart(digits, '0');
}
</script>

<template>
  <div
    class="position-suggestion-card"
    :class="{ selected }"
    @click="emit('select')"
  >
    <!-- Header -->
    <div class="card-header">
      <div class="header-left">
        <span class="star-icon">★</span>
        <span class="header-title">Рекомендуемая</span>
      </div>
      <a-button
        size="small"
        type="link"
        class="show-3d-btn"
        @click.stop="emit('preview', props.position)"
      >
        <template #icon><EyeOutlined /></template>
        Показать в 3D
      </a-button>
    </div>

    <!-- Position Grid -->
    <div class="position-grid">
      <div class="position-cell">
        <span class="cell-value">{{ position.zone }}</span>
        <span class="cell-label">Зона</span>
      </div>
      <div class="position-cell">
        <span class="cell-value">{{ formatNumber(position.row) }}</span>
        <span class="cell-label">Ряд</span>
      </div>
      <div class="position-cell">
        <span class="cell-value">{{ formatNumber(position.bay) }}</span>
        <span class="cell-label">Отсек</span>
      </div>
      <div class="position-cell">
        <span class="cell-value">{{ position.tier }}</span>
        <span class="cell-label">Ярус</span>
      </div>
    </div>

    <!-- Full Coordinate -->
    <div class="coordinate-display">
      {{ position.coordinate || `${position.zone}-R${formatNumber(position.row)}-B${formatNumber(position.bay)}-T${position.tier}-${position.sub_slot}` }}
    </div>

    <!-- Reason Footer -->
    <div class="reason-footer">
      <span class="reason-icon">ℹ️</span>
      <span class="reason-text">{{ reason }}</span>
    </div>

    <!-- Selection Indicator -->
    <a-tag v-if="selected" color="purple" style="position: absolute; top: 8px; right: 8px; margin: 0; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; padding: 0;">
      ✓
    </a-tag>
  </div>
</template>

<style scoped>
.position-suggestion-card {
  background: var(--ant-green-1, #f6ffed);
  border: 2px solid var(--ant-green-3, #b7eb8f);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  margin-bottom: 12px;
}

.position-suggestion-card:hover {
  border-color: var(--ant-color-success, #52c41a);
  box-shadow: 0 2px 8px rgba(82, 196, 26, 0.15);
}

.position-suggestion-card.selected {
  border-color: var(--ant-purple-6, #722ed1);
  background: var(--ant-purple-1, #f9f0ff);
}

/* Header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.star-icon {
  color: var(--ant-color-success, #52c41a);
  font-size: 16px;
}

.header-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--ant-green-7, #389e0d);
}

.show-3d-btn {
  font-size: 12px;
  padding: 0 8px;
  height: 24px;
}

/* Position Grid */
.position-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 10px;
}

.position-cell {
  background: white;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 8px 4px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cell-value {
  font-size: 18px;
  font-weight: 700;
  color: #262626;
  font-family: monospace;
}

.cell-label {
  font-size: 10px;
  color: #8c8c8c;
  text-transform: uppercase;
}

/* Coordinate Display */
.coordinate-display {
  font-family: monospace;
  font-size: 12px;
  color: #595959;
  text-align: center;
  margin-bottom: 10px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 4px;
}

/* Reason Footer */
.reason-footer {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px solid rgba(82, 196, 26, 0.2);
}

.reason-icon {
  font-size: 12px;
  flex-shrink: 0;
}

.reason-text {
  font-size: 12px;
  color: #595959;
  line-height: 1.4;
}


</style>
