<script setup lang="ts">
/**
 * YardSettingsDrawer - Centralized settings panel for 3D yard visualization
 *
 * Slide-out drawer containing all visibility toggles, display options,
 * and camera controls organized in collapsible sections.
 */

import { computed } from 'vue'
import { useYardSettings, type ColorMode } from '@/composables/useYardSettings'
import type { YardLayerInfo } from '@/composables/useDxfYard'
import { QUALITY_LABELS, QUALITY_DESCRIPTIONS, type QualityLevel } from '@/utils/qualityPresets'

// Props
interface Props {
  /** Whether the drawer is visible */
  visible: boolean
  /** DXF layers for advanced section */
  dxfLayers?: YardLayerInfo[]
  /** Current graphics quality level */
  qualityLevel?: QualityLevel
}

const props = withDefaults(defineProps<Props>(), {
  dxfLayers: () => [],
  qualityLevel: 'medium',
})

// Emits
const emit = defineEmits<{
  'update:visible': [value: boolean]
  'camera-top': []
  'camera-isometric': []
  'camera-fit': []
  'dxf-layer-toggle': [layer: YardLayerInfo]
  'dxf-show-all': []
  'dxf-hide-all': []
  'quality-change': [level: QualityLevel]
}>()

// Settings composable
const {
  layers,
  labels,
  display,
  setColorMode,
} = useYardSettings()

// Drawer visibility (v-model pattern)
const drawerVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit('update:visible', value),
})

// Color mode options for segmented control
const colorModeOptions = [
  { value: 'visual', label: 'Визуал' },
  { value: 'status', label: 'Статус' },
  { value: 'dwell', label: 'Срок' },
  { value: 'hazmat', label: 'Опасный' },
]

// Quality options for segmented control
const qualityOptions: { value: QualityLevel; label: string }[] = [
  { value: 'low', label: QUALITY_LABELS.low },
  { value: 'medium', label: QUALITY_LABELS.medium },
  { value: 'high', label: QUALITY_LABELS.high },
  { value: 'ultra', label: QUALITY_LABELS.ultra },
]

// Get quality description for tooltip
function getQualityDescription(level: QualityLevel): string {
  return QUALITY_DESCRIPTIONS[level]
}

// Active collapse panels (all open by default except advanced)
const activeKeys = ['layers', 'labels', 'display', 'camera', 'quality']

// Handle color mode change
function onColorModeChange(value: ColorMode): void {
  setColorMode(value)
}

// Handle quality change
function onQualityChange(value: QualityLevel): void {
  emit('quality-change', value)
}

// Camera handlers
function onCameraTop(): void {
  emit('camera-top')
}

function onCameraIsometric(): void {
  emit('camera-isometric')
}

function onCameraFit(): void {
  emit('camera-fit')
}

// DXF layer handlers
function onDxfLayerToggle(layer: YardLayerInfo): void {
  emit('dxf-layer-toggle', layer)
}

function onDxfShowAll(): void {
  emit('dxf-show-all')
}

function onDxfHideAll(): void {
  emit('dxf-hide-all')
}
</script>

<template>
  <a-drawer
    v-model:open="drawerVisible"
    title="⚙️ Настройки"
    placement="right"
    :width="280"
    :mask-style="{ backgroundColor: 'rgba(0, 0, 0, 0.3)' }"
    class="yard-settings-drawer"
  >
    <a-collapse :default-active-key="activeKeys" ghost>
      <!-- Layers Section -->
      <a-collapse-panel key="layers" header="Слои">
        <div class="settings-section">
          <a-checkbox v-model:checked="layers.containers">
            Контейнеры
          </a-checkbox>
          <a-checkbox v-model:checked="layers.buildings">
            Здания
          </a-checkbox>
          <a-checkbox v-model:checked="layers.roads">
            Дороги
          </a-checkbox>
          <a-checkbox v-model:checked="layers.fences">
            Ограждения
          </a-checkbox>
          <a-checkbox v-model:checked="layers.railway">
            Ж/Д пути
          </a-checkbox>
          <a-checkbox v-model:checked="layers.platforms">
            Площадки
          </a-checkbox>
          <a-checkbox v-model:checked="layers.testVehicles">
            Тестовые ТС
          </a-checkbox>
        </div>
      </a-collapse-panel>

      <!-- Labels Section -->
      <a-collapse-panel key="labels" header="Подписи">
        <div class="settings-section">
          <a-checkbox v-model:checked="labels.buildings">
            Названия зданий
          </a-checkbox>
          <a-checkbox v-model:checked="labels.containers">
            Номера контейнеров
          </a-checkbox>
          <a-checkbox v-model:checked="labels.vehicles">
            Номера ТС
          </a-checkbox>
        </div>
      </a-collapse-panel>

      <!-- Display Section -->
      <a-collapse-panel key="display" header="Отображение">
        <div class="settings-section">
          <div class="setting-row">
            <span class="setting-label">Цветовой режим:</span>
            <a-segmented
              :value="display.colorMode"
              :options="colorModeOptions"
              size="small"
              @change="(val: string | number) => onColorModeChange(val as ColorMode)"
            />
          </div>
          <a-checkbox v-model:checked="display.showGrid">
            Сетка
          </a-checkbox>
          <a-checkbox v-model:checked="display.showStats">
            Статистика
          </a-checkbox>
        </div>
      </a-collapse-panel>

      <!-- Camera Section -->
      <a-collapse-panel key="camera" header="Камера">
        <div class="settings-section camera-buttons">
          <a-button size="small" @click="onCameraTop">
            ⬆ Сверху
          </a-button>
          <a-button size="small" @click="onCameraIsometric">
            ◇ Изометрия
          </a-button>
          <a-button size="small" @click="onCameraFit">
            ⊞ Вписать
          </a-button>
        </div>
      </a-collapse-panel>

      <!-- Quality Section -->
      <a-collapse-panel key="quality" header="Качество графики">
        <div class="settings-section">
          <div class="setting-row">
            <a-segmented
              :value="qualityLevel"
              :options="qualityOptions"
              size="small"
              block
              @change="(val: string | number) => onQualityChange(val as QualityLevel)"
            />
          </div>
          <div class="quality-description">
            {{ getQualityDescription(qualityLevel) }}
          </div>
        </div>
      </a-collapse-panel>

      <!-- Advanced DXF Layers Section (collapsed by default) -->
      <a-collapse-panel v-if="dxfLayers.length > 0" key="advanced" header="Расширенные (DXF)">
        <div class="settings-section">
          <div class="dxf-controls">
            <a-button size="small" @click="onDxfShowAll">Все</a-button>
            <a-button size="small" @click="onDxfHideAll">Нет</a-button>
          </div>
          <div class="dxf-layer-list">
            <div
              v-for="layer in dxfLayers"
              :key="layer.name"
              class="dxf-layer-item"
              @click="onDxfLayerToggle(layer)"
            >
              <a-checkbox :checked="layer.visible" />
              <span class="dxf-layer-name">{{ layer.name }}</span>
              <span class="dxf-layer-count">{{ layer.objectCount }}</span>
            </div>
          </div>
        </div>
      </a-collapse-panel>
    </a-collapse>
  </a-drawer>
</template>

<style scoped>
.yard-settings-drawer :deep(.ant-drawer-body) {
  padding: 0;
}

.yard-settings-drawer :deep(.ant-collapse-header) {
  font-weight: 500;
  padding: 12px 16px !important;
}

.yard-settings-drawer :deep(.ant-collapse-content-box) {
  padding: 0 16px 12px !important;
}

.settings-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 4px;
}

.setting-label {
  font-size: 12px;
  color: #666;
}

.camera-buttons {
  flex-direction: row;
  flex-wrap: wrap;
  gap: 8px;
}

.camera-buttons .ant-btn {
  flex: 1;
  min-width: 70px;
}

/* DXF Layers Styles */
.dxf-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.dxf-layer-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}

.dxf-layer-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.dxf-layer-item:hover {
  background: #f5f5f5;
}

.dxf-layer-name {
  flex: 1;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dxf-layer-count {
  font-size: 11px;
  color: #999;
}

/* Quality Section */
.quality-description {
  font-size: 11px;
  color: #666;
  text-align: center;
  padding: 4px 8px;
  background: #f9f9f9;
  border-radius: 4px;
  margin-top: 4px;
}
</style>
