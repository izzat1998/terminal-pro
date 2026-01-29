<script setup lang="ts">
/**
 * DXF Viewer Component
 * Renders DXF files in an interactive Three.js scene
 */

import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useDxfScene } from '@/composables/useDxfScene'

interface Props {
  /** DXF file content as string */
  dxfContent?: string
  /** URL to load DXF from */
  dxfUrl?: string
  /** Height of the viewer (default: 600px) */
  height?: string | number
  /** Show grid helper (default: true) */
  showGrid?: boolean
  /** Background color (default: 0xfafafa) */
  backgroundColor?: number
  /** Scale factor for the DXF (default: 1) */
  scale?: number
}

const props = withDefaults(defineProps<Props>(), {
  height: 600,
  showGrid: true,
  backgroundColor: 0xfafafa,
  scale: 1,
})

const emit = defineEmits<{
  loaded: [stats: { entityCount: number; layerCount: number }]
  error: [message: string]
}>()

const canvasRef = ref<HTMLCanvasElement>()
const containerRef = ref<HTMLDivElement>()

const {
  isInitialized,
  isLoading,
  error,
  dxfStats,
  initScene,
  loadDxfContent,
  loadDxfUrl,
  handleResize,
  setTopView,
  setIsometricView,
  zoomToFit,
  dispose,
} = useDxfScene(canvasRef)

// Handle file upload
async function handleFileUpload(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const content = await file.text()
  loadDxfContent(content, { scale: props.scale })
}

// Load content when props change
function loadFromProps(): void {
  if (props.dxfContent) {
    loadDxfContent(props.dxfContent, { scale: props.scale })
  } else if (props.dxfUrl) {
    loadDxfUrl(props.dxfUrl, { scale: props.scale })
  }
}

// Watch for error changes and emit
watch(error, (newError) => {
  if (newError) {
    emit('error', newError)
  }
})

// Watch for stats changes and emit
watch(dxfStats, (newStats) => {
  if (newStats) {
    emit('loaded', {
      entityCount: newStats.entityCount.total,
      layerCount: newStats.layerCount,
    })
  }
})

onMounted(() => {
  initScene({
    showGrid: props.showGrid,
    backgroundColor: props.backgroundColor,
  })

  // Load initial content
  loadFromProps()

  // Handle window resize
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  dispose()
})

// Computed height style
const heightStyle = typeof props.height === 'number' ? `${props.height}px` : props.height
</script>

<template>
  <div ref="containerRef" class="dxf-viewer" :style="{ height: heightStyle }">
    <!-- Canvas -->
    <canvas ref="canvasRef" class="dxf-canvas" />

    <!-- Loading overlay -->
    <div v-if="isLoading" class="dxf-overlay">
      <a-spin size="large" />
      <span class="loading-text">Загрузка DXF...</span>
    </div>

    <!-- Error overlay -->
    <div v-if="error" class="dxf-overlay error">
      <a-result status="error" :title="error" />
    </div>

    <!-- Controls -->
    <div v-if="isInitialized && !isLoading" class="dxf-controls">
      <a-space direction="vertical" size="small">
        <a-tooltip title="Вид сверху" placement="left">
          <a-button shape="circle" @click="setTopView">
            <template #icon><span>⬆</span></template>
          </a-button>
        </a-tooltip>
        <a-tooltip title="Изометрия" placement="left">
          <a-button shape="circle" @click="setIsometricView">
            <template #icon><span>◇</span></template>
          </a-button>
        </a-tooltip>
        <a-tooltip title="Вписать в окно" placement="left">
          <a-button shape="circle" @click="zoomToFit">
            <template #icon><span>⊞</span></template>
          </a-button>
        </a-tooltip>
      </a-space>
    </div>

    <!-- Stats panel -->
    <div v-if="dxfStats" class="dxf-stats">
      <div class="stat">
        <span class="label">Объектов:</span>
        <span class="value">{{ dxfStats.entityCount.total.toLocaleString() }}</span>
      </div>
      <div class="stat">
        <span class="label">Слоёв:</span>
        <span class="value">{{ dxfStats.layerCount }}</span>
      </div>
      <div class="stat">
        <span class="label">Размер:</span>
        <span class="value">
          {{ dxfStats.bounds.width.toFixed(1) }} × {{ dxfStats.bounds.height.toFixed(1) }}
        </span>
      </div>
    </div>

    <!-- File upload (if no content provided) -->
    <div v-if="!dxfContent && !dxfUrl && !dxfStats" class="dxf-upload">
      <a-upload
        accept=".dxf"
        :show-upload-list="false"
        :before-upload="() => false"
        @change="handleFileUpload"
      >
        <a-button type="primary" size="large">
          <template #icon><span>📁</span></template>
          Загрузить DXF файл
        </a-button>
      </a-upload>
      <p class="upload-hint">Перетащите файл или нажмите для выбора</p>
    </div>
  </div>
</template>

<style scoped>
.dxf-viewer {
  position: relative;
  width: 100%;
  background: #fafafa;
  border-radius: 8px;
  overflow: hidden;
}

.dxf-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.dxf-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 10;
}

.dxf-overlay.error {
  background: rgba(255, 240, 240, 0.95);
}

.loading-text {
  margin-top: 16px;
  color: #666;
  font-size: 14px;
}

.dxf-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 5;
}

.dxf-stats {
  position: absolute;
  bottom: 16px;
  left: 16px;
  background: rgba(255, 255, 255, 0.9);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  z-index: 5;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.dxf-stats .stat {
  display: flex;
  gap: 8px;
}

.dxf-stats .label {
  color: #888;
}

.dxf-stats .value {
  color: #333;
  font-weight: 500;
}

.dxf-upload {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 5;
}

.upload-hint {
  margin-top: 12px;
  color: #999;
  font-size: 13px;
}
</style>
