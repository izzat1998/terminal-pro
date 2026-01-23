<script setup lang="ts">
/**
 * Yard Test View
 * Test page for the YardView3D component
 */

import { ref } from 'vue'
import YardView3D from '@/components/YardView3D.vue'
import type { ContainerPosition, ContainerData } from '@/composables/useContainers3D'

// Mock container data for testing
const mockContainerData = ref<ContainerData[]>([
  { id: 1, container_number: 'HDMU6565958', status: 'LADEN', container_type: '40GP', dwell_days: 5 },
  { id: 2, container_number: 'TCLU7894521', status: 'EMPTY', container_type: '40GP', dwell_days: 12 },
  { id: 3, container_number: 'MSKU9876543', status: 'LADEN', container_type: '40GP', dwell_days: 3 },
  { id: 4, container_number: 'TEMU1234567', status: 'LADEN', container_type: '40GP', dwell_days: 18 },
  { id: 5, container_number: 'CSQU4567890', status: 'EMPTY', container_type: '40GP', dwell_days: 7 },
])

// Event handlers
function onContainerClick(container: ContainerPosition & { data?: ContainerData }): void {
  console.log('Container clicked:', container)
}

function onContainerHover(container: ContainerPosition & { data?: ContainerData } | null): void {
  if (container) {
    console.log('Hovering:', container.id)
  }
}

function onLoaded(stats: { entityCount: number; containerCount: number }): void {
  console.log('Yard loaded:', stats)
}

function onError(message: string): void {
  console.error('Yard error:', message)
}
</script>

<template>
  <div class="yard-test-page">
    <div class="page-header">
      <h1>3D Yard Visualization Test</h1>
      <p>Testing DXF-based terminal rendering with interactive containers</p>
    </div>

    <div class="yard-container">
      <YardView3D
        dxf-url="/yard.dxf"
        :container-data="mockContainerData"
        height="calc(100vh - 150px)"
        :show-layer-panel="true"
        :show-stats="true"
        color-mode="status"
        :interactive="true"
        @container-click="onContainerClick"
        @container-hover="onContainerHover"
        @loaded="onLoaded"
        @error="onError"
      />
    </div>
  </div>
</template>

<style scoped>
.yard-test-page {
  padding: 16px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-header {
  margin-bottom: 16px;
}

.page-header h1 {
  margin: 0 0 4px 0;
  font-size: 20px;
}

.page-header p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.yard-container {
  flex: 1;
  min-height: 0;
}
</style>
