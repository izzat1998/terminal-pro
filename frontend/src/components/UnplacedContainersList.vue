<script setup lang="ts">
/**
 * UnplacedContainersList - Floating panel showing containers awaiting placement
 *
 * Overlays the 3D view and provides quick access to place containers.
 * When "Разместить" is clicked, it enters placement mode directly
 * showing recommendation markers in 3D for the user to click.
 */

import { computed } from 'vue';
import { EnvironmentOutlined, InboxOutlined } from '@ant-design/icons-vue';
import { usePlacementState } from '../composables/usePlacementState';
import type { UnplacedContainer } from '../types/placement';

const {
  unplacedContainers,
  loading,
  selectedCompanyName,
  isPlacementMode,
  placementModeLoading,
  placingContainerId,
  enterPlacementMode,
  exitPlacementMode,
} = usePlacementState();

// Filtered by selected company (if any)
const displayedContainers = computed(() => {
  if (!selectedCompanyName.value) return unplacedContainers.value;
  return unplacedContainers.value.filter(
    c => c.company_name === selectedCompanyName.value
  );
});

// Show badge with count
const badgeCount = computed(() => displayedContainers.value.length);

// Get status color
function getStatusColor(status: string): string {
  return status === 'LADEN' ? 'green' : 'blue';
}

// Get status label
function getStatusLabel(status: string): string {
  return status === 'LADEN' ? 'Гружёный' : 'Порожний';
}

// Check if container is currently being placed
function isBeingPlaced(containerId: number): boolean {
  return placingContainerId.value === containerId;
}

// Check if this container's button should show loading
function isButtonLoading(containerId: number): boolean {
  return placementModeLoading.value && placingContainerId.value === containerId;
}

// Handle place/cancel button click
async function handlePlaceClick(container: UnplacedContainer): Promise<void> {
  if (isBeingPlaced(container.id)) {
    // Already in placement mode for this container - cancel
    exitPlacementMode();
  } else {
    // Enter placement mode for this container
    await enterPlacementMode(container.id);
  }
}
</script>

<template>
  <div class="unplaced-list-container">
    <!-- Header with badge -->
    <div class="list-header">
      <div class="header-title">
        <InboxOutlined class="header-icon" />
        <span>Требуют размещения</span>
        <a-badge
          :count="badgeCount"
          :number-style="{ backgroundColor: badgeCount > 0 ? '#fa8c16' : '#52c41a' }"
        />
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="list-loading">
      <a-spin size="small" />
    </div>

    <!-- Empty state -->
    <div v-else-if="displayedContainers.length === 0" class="list-empty">
      <div class="empty-content">
        <EnvironmentOutlined class="empty-icon" />
        <span class="empty-text">Все контейнеры размещены</span>
      </div>
    </div>

    <!-- Container list -->
    <div v-else class="list-content">
      <div
        v-for="container in displayedContainers"
        :key="container.id"
        :class="['container-item', { 'is-active': isBeingPlaced(container.id) }]"
      >
        <div class="container-info">
          <div class="container-number">{{ container.container_number }}</div>
          <div class="container-meta">
            <a-tag :color="getStatusColor(container.status)" size="small">
              {{ getStatusLabel(container.status) }}
            </a-tag>
            <span class="iso-type">{{ container.iso_type }}</span>
            <span v-if="container.dwell_time_days" class="dwell-days">
              {{ container.dwell_time_days }}д
            </span>
          </div>
        </div>
        <a-button
          :type="isBeingPlaced(container.id) ? 'default' : 'primary'"
          :danger="isBeingPlaced(container.id)"
          size="small"
          class="place-btn"
          :loading="isButtonLoading(container.id)"
          :disabled="isPlacementMode && !isBeingPlaced(container.id)"
          @click="handlePlaceClick(container)"
        >
          {{ isBeingPlaced(container.id) ? 'Отмена' : 'Разместить' }}
        </a-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.unplaced-list-container {
  position: absolute;
  top: 12px;
  left: 12px;
  width: 320px;
  max-height: calc(100% - 80px);
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  z-index: 10;
  backdrop-filter: blur(8px);
}

/* Header */
.list-header {
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
.list-loading {
  padding: 24px;
  text-align: center;
}

/* Empty state */
.list-empty {
  padding: 24px 16px;
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

/* Content */
.list-content {
  overflow-y: auto;
  max-height: 400px;
}

/* Container item */
.container-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s ease;
}

.container-item:hover {
  background: #f5f5f5;
}

/* Active container being placed */
.container-item.is-active {
  background: #e6f4ff;
  border-left: 3px solid #1677ff;
  padding-left: 13px;
}

.container-item.is-active:hover {
  background: #d6e8fa;
}

.container-item:last-child {
  border-bottom: none;
}

.container-info {
  flex: 1;
  min-width: 0;
}

.container-number {
  font-family: monospace;
  font-size: 13px;
  font-weight: 600;
  color: #262626;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.container-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.iso-type {
  font-size: 11px;
  color: #8c8c8c;
}

.dwell-days {
  font-size: 11px;
  color: #fa8c16;
  font-weight: 500;
}

/* Place button */
.place-btn {
  flex-shrink: 0;
  margin-left: 12px;
}

/* Scrollbar styling */
.list-content::-webkit-scrollbar {
  width: 6px;
}

.list-content::-webkit-scrollbar-track {
  background: #f0f0f0;
}

.list-content::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 3px;
}

.list-content::-webkit-scrollbar-thumb:hover {
  background: #bfbfbf;
}
</style>
