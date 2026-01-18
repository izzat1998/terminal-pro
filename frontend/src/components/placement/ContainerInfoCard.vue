<script setup lang="ts">
/**
 * ContainerInfoCard - Displays container details in placement workflow
 *
 * Shows container number, ISO type, status, and dwell time in a compact card format.
 */

import type { UnplacedContainer } from '../../types/placement';

defineProps<{
  container: UnplacedContainer;
}>();

function getStatusColor(status: 'LADEN' | 'EMPTY'): string {
  return status === 'LADEN' ? 'green' : 'blue';
}

function getStatusLabel(status: 'LADEN' | 'EMPTY'): string {
  return status === 'LADEN' ? 'Гружёный' : 'Порожний';
}

function getDwellClass(days: number): string {
  if (days <= 3) return 'fresh';
  if (days <= 7) return 'normal';
  if (days <= 14) return 'aging';
  return 'overdue';
}
</script>

<template>
  <div class="container-info-card">
    <div class="card-header">
      <span class="container-number">{{ container.container_number }}</span>
      <a-tag :color="getStatusColor(container.status)" size="small">
        {{ getStatusLabel(container.status) }}
      </a-tag>
    </div>
    <div class="card-body">
      <div class="info-grid">
        <div class="info-item">
          <span class="label">Тип</span>
          <span class="value">{{ container.iso_type }}</span>
        </div>
        <div class="info-item">
          <span class="label">Компания</span>
          <span class="value">{{ container.company_name || 'Не указана' }}</span>
        </div>
        <div class="info-item">
          <span class="label">На терминале</span>
          <span class="value dwell" :class="getDwellClass(container.dwell_time_days)">
            {{ container.dwell_time_days }} дней
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container-info-card {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.container-number {
  font-weight: 600;
  font-size: 15px;
  font-family: monospace;
  color: #262626;
}

.card-body {
  /* Body content styling */
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-item .label {
  font-size: 11px;
  color: #8c8c8c;
  text-transform: uppercase;
}

.info-item .value {
  font-size: 13px;
  color: #262626;
  font-weight: 500;
}

/* Dwell time coloring */
.dwell.fresh {
  color: #52c41a;
}

.dwell.normal {
  color: #fadb14;
}

.dwell.aging {
  color: #fa8c16;
}

.dwell.overdue {
  color: #f5222d;
}
</style>
