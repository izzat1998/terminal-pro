<script setup lang="ts">
/**
 * Container Location Visualization
 * A simple 2D diagram showing where a container is located in the terminal yard.
 * Shows zone, row, bay, tier in an easy-to-understand visual format.
 */

import { computed } from 'vue';
import {
  EnvironmentOutlined,
  AppstoreOutlined,
  BorderOutlined,
  VerticalAlignTopOutlined,
} from '@ant-design/icons-vue';

interface Props {
  location: string; // Format: "A-R03-B05-T2-A" or "A-R03-B05-T2-B"
  containerNumber: string;
  isoType?: string;
  status?: 'LADEN' | 'EMPTY';
}

const props = defineProps<Props>();

// Parse location string into components
const parsedLocation = computed(() => {
  if (!props.location) return null;

  // Parse format: "A-R03-B05-T2-A" or "A-R07-B03-T1-B"
  const match = props.location.match(/^([A-E])-R(\d{2})-B(\d{2})-T(\d)-([AB])$/);
  if (!match) return null;

  const rowStr = match[2];
  const bayStr = match[3];
  const tierStr = match[4];

  return {
    zone: match[1],
    row: parseInt(rowStr ?? '0', 10),
    bay: parseInt(bayStr ?? '0', 10),
    tier: parseInt(tierStr ?? '0', 10),
    subSlot: match[5] as 'A' | 'B',
  };
});

// Generate row numbers for the grid (1-10)
const rows = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
const bays = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
const tiers = [4, 3, 2, 1]; // Top to bottom for display

// Check if a cell is the selected container's position
function isSelectedCell(row: number, bay: number): boolean {
  if (!parsedLocation.value) return false;
  return parsedLocation.value.row === row && parsedLocation.value.bay === bay;
}

// Get container size from ISO type
const containerSize = computed(() => {
  if (!props.isoType) return '20ft';
  const firstChar = props.isoType.charAt(0);
  return firstChar === '4' || firstChar === 'L' || firstChar === '9' ? '40ft' : '20ft';
});

// Status display
const statusDisplay = computed(() => {
  return props.status === 'LADEN' ? 'Гружёный' : 'Порожний';
});
</script>

<template>
  <div class="location-view">
    <!-- Header with container info -->
    <div class="location-header">
      <div class="container-info">
        <a-tag color="blue" class="container-number">{{ containerNumber }}</a-tag>
        <a-tag v-if="isoType">{{ isoType }}</a-tag>
        <a-tag :color="status === 'LADEN' ? 'green' : 'blue'">{{ statusDisplay }}</a-tag>
      </div>
      <a-tag color="purple" class="location-tag">
        <EnvironmentOutlined /> {{ location }}
      </a-tag>
    </div>

    <template v-if="parsedLocation">
      <!-- Location breakdown cards -->
      <a-row :gutter="[12, 12]" class="location-cards">
        <a-col :span="6">
          <div class="info-card zone-card">
            <div class="info-label">Зона</div>
            <div class="info-value zone-value">{{ parsedLocation.zone }}</div>
          </div>
        </a-col>
        <a-col :span="6">
          <div class="info-card">
            <div class="info-label">Ряд</div>
            <div class="info-value">{{ parsedLocation.row }}</div>
          </div>
        </a-col>
        <a-col :span="6">
          <div class="info-card">
            <div class="info-label">Бэй</div>
            <div class="info-value">{{ parsedLocation.bay }}</div>
          </div>
        </a-col>
        <a-col :span="6">
          <div class="info-card">
            <div class="info-label">Ярус</div>
            <div class="info-value">{{ parsedLocation.tier }} / 4</div>
          </div>
        </a-col>
      </a-row>

      <!-- Visual diagrams -->
      <div class="diagrams-container">
        <!-- Top-down grid view (Row x Bay) -->
        <div class="diagram-section">
          <div class="diagram-title">
            <AppstoreOutlined /> Вид сверху (Ряд × Бэй)
          </div>
          <div class="grid-container">
            <!-- Bay labels (top) -->
            <div class="grid-header">
              <div class="corner-cell"></div>
              <div v-for="bay in bays" :key="`bay-${bay}`" class="header-cell">
                B{{ bay }}
              </div>
            </div>
            <!-- Grid rows -->
            <div v-for="row in rows" :key="`row-${row}`" class="grid-row">
              <div class="row-label">R{{ row }}</div>
              <div
                v-for="bay in bays"
                :key="`cell-${row}-${bay}`"
                class="grid-cell"
                :class="{
                  'cell-selected': isSelectedCell(row, bay),
                  'cell-same-row': parsedLocation?.row === row && !isSelectedCell(row, bay),
                  'cell-same-bay': parsedLocation?.bay === bay && !isSelectedCell(row, bay),
                }"
              >
                <div v-if="isSelectedCell(row, bay)" class="cell-marker">
                  <span class="marker-icon">📦</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Side view (Tier stack) -->
        <div class="diagram-section tier-section">
          <div class="diagram-title">
            <VerticalAlignTopOutlined /> Вид сбоку (Ярусы)
          </div>
          <div class="tier-stack">
            <div
              v-for="tier in tiers"
              :key="`tier-${tier}`"
              class="tier-slot"
              :class="{ 'tier-selected': parsedLocation?.tier === tier }"
            >
              <div class="tier-label">T{{ tier }}</div>
              <div class="tier-box" :class="{ 'tier-box-selected': parsedLocation?.tier === tier }">
                <template v-if="parsedLocation?.tier === tier">
                  <span class="tier-container">📦</span>
                  <span class="tier-text">{{ containerNumber.slice(-4) }}</span>
                </template>
              </div>
            </div>
            <div class="ground-line">
              <BorderOutlined /> Земля
            </div>
          </div>
        </div>
      </div>

      <!-- Sub-slot indicator for 20ft containers -->
      <div v-if="containerSize === '20ft' && parsedLocation" class="subslot-info">
        <a-alert type="info" show-icon>
          <template #message>
            Контейнер 20ft находится в позиции <strong>{{ parsedLocation.subSlot }}</strong>
            ({{ parsedLocation.subSlot === 'A' ? 'левая' : 'правая' }} часть бэя)
          </template>
        </a-alert>
      </div>
    </template>

    <!-- Invalid location format -->
    <div v-else class="invalid-location">
      <a-empty description="Не удалось разобрать координаты позиции" />
    </div>
  </div>
</template>

<style scoped>
.location-view {
  padding: 16px;
}

.location-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.container-info {
  display: flex;
  gap: 8px;
  align-items: center;
}

.container-number {
  font-weight: 600;
  font-size: 14px;
}

.location-tag {
  font-size: 14px;
  font-weight: 500;
}

/* Info cards */
.location-cards {
  margin-bottom: 24px;
}

.info-card {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.zone-card {
  background: linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%);
  border-color: #91d5ff;
}

.info-label {
  font-size: 12px;
  color: #8c8c8c;
  margin-bottom: 4px;
}

.info-value {
  font-size: 24px;
  font-weight: 700;
  color: #262626;
}

.zone-value {
  font-size: 32px;
  color: #1677ff;
}

/* Diagrams container */
.diagrams-container {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.diagram-section {
  flex: 1;
  min-width: 300px;
}

.diagram-title {
  font-size: 14px;
  font-weight: 600;
  color: #595959;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Grid view */
.grid-container {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.grid-header {
  display: flex;
  background: #fafafa;
  border-bottom: 1px solid #d9d9d9;
}

.corner-cell {
  width: 36px;
  height: 28px;
  border-right: 1px solid #d9d9d9;
}

.header-cell {
  flex: 1;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  color: #8c8c8c;
  border-right: 1px solid #f0f0f0;
}

.header-cell:last-child {
  border-right: none;
}

.grid-row {
  display: flex;
  border-bottom: 1px solid #f0f0f0;
}

.grid-row:last-child {
  border-bottom: none;
}

.row-label {
  width: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  color: #8c8c8c;
  background: #fafafa;
  border-right: 1px solid #d9d9d9;
}

.grid-cell {
  flex: 1;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.grid-cell:last-child {
  border-right: none;
}

.cell-same-row {
  background: #fff7e6;
}

.cell-same-bay {
  background: #e6f7ff;
}

.cell-selected {
  background: linear-gradient(135deg, #722ed1 0%, #9254de 100%) !important;
  position: relative;
}

.cell-marker {
  display: flex;
  align-items: center;
  justify-content: center;
}

.marker-icon {
  font-size: 16px;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));
}

/* Tier stack view */
.tier-section {
  max-width: 200px;
}

.tier-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: #fafafa;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
}

.tier-slot {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tier-label {
  width: 28px;
  font-size: 11px;
  font-weight: 600;
  color: #8c8c8c;
}

.tier-box {
  flex: 1;
  height: 40px;
  border: 2px dashed #d9d9d9;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: #fff;
  transition: all 0.2s;
}

.tier-box-selected {
  border: 2px solid #722ed1;
  background: linear-gradient(135deg, #f9f0ff 0%, #efdbff 100%);
  box-shadow: 0 2px 8px rgba(114, 46, 209, 0.25);
}

.tier-container {
  font-size: 18px;
}

.tier-text {
  font-size: 11px;
  font-weight: 600;
  color: #722ed1;
}

.tier-selected .tier-label {
  color: #722ed1;
  font-weight: 700;
}

.ground-line {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 2px solid #8c8c8c;
  font-size: 11px;
  color: #8c8c8c;
  text-align: center;
}

/* Sub-slot info */
.subslot-info {
  margin-top: 20px;
}

/* Invalid location */
.invalid-location {
  padding: 40px;
}
</style>
