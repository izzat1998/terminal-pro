<script setup lang="ts">
/**
 * GateCameraWidget - Professional Gate Camera Control Panel
 *
 * Corporate-grade camera widget for vehicle detection at terminal gates.
 * Clean, efficient interface focused on operational clarity.
 * Designed to be embedded in CSS3DRenderer for 3D yard canvas integration.
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { ToolOutlined, CameraOutlined, ScanOutlined, DownOutlined, UpOutlined } from '@ant-design/icons-vue'
import { useGateDetection, type VehicleDetectionResult } from '@/composables/useGateDetection'
import type { VehicleType } from '@/composables/useVehicleModels'

type CameraSource = 'webcam' | 'mock'

interface Props {
  /** Show/hide the widget */
  visible: boolean
  /** Initial camera source */
  initialSource?: CameraSource
  /** Gate identifier for display */
  gateId?: string
}

const props = withDefaults(defineProps<Props>(), {
  initialSource: 'mock',
  gateId: 'Gate 01',
})

const emit = defineEmits<{
  vehicleDetected: [result: VehicleDetectionResult]
}>()

// Refs
const widgetRef = ref<HTMLDivElement>()
const videoRef = ref<HTMLVideoElement>()
const canvasRef = ref<HTMLCanvasElement>()

// Camera state
const currentSource = ref<CameraSource>(props.initialSource)
const isWebcamActive = ref(false)
const webcamError = ref<string | null>(null)
const mediaStream = ref<MediaStream | null>(null)

// Minimize state
const isMinimized = ref(false)

// Detection
const { isDetecting, lastResult, error: detectionError, useMockDetection, detectVehicle, clearError } = useGateDetection()

// Computed
const canCapture = computed(() => {
  if (currentSource.value === 'mock') return true
  if (currentSource.value === 'webcam') return isWebcamActive.value
  return false
})

const statusText = computed(() => {
  if (isDetecting.value) return 'Сканирование...'
  if (currentSource.value === 'mock') return 'Тестовый режим'
  if (isWebcamActive.value) return 'Камера активна'
  if (webcamError.value) return 'Ошибка камеры'
  return 'Камера отключена'
})

const statusType = computed(() => {
  if (isDetecting.value) return 'processing'
  if (currentSource.value === 'mock') return 'test'
  if (isWebcamActive.value) return 'online'
  if (webcamError.value) return 'error'
  return 'offline'
})

const vehicleTypeLabels: Record<VehicleType, string> = {
  TRUCK: 'Грузовик',
  CAR: 'Легковой',
  WAGON: 'Вагон',
  UNKNOWN: 'Не определен',
}

const vehicleTypeIcons: Record<VehicleType, string> = {
  TRUCK: '🚛',
  CAR: '🚗',
  WAGON: '🚃',
  UNKNOWN: '❓',
}

// Watch for visibility changes
watch(() => props.visible, (visible) => {
  if (visible && currentSource.value === 'webcam') {
    startWebcam()
  } else if (!visible) {
    stopWebcam()
  }
})

// Webcam methods
async function startWebcam(): Promise<void> {
  webcamError.value = null

  if (!navigator.mediaDevices?.getUserMedia) {
    webcamError.value = 'Веб-камера не поддерживается'
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: 'environment',
      },
      audio: false,
    })

    mediaStream.value = stream

    if (videoRef.value) {
      videoRef.value.srcObject = stream
      await videoRef.value.play()
      isWebcamActive.value = true
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Неизвестная ошибка'
    if (errorMessage.includes('Permission denied') || errorMessage.includes('NotAllowedError')) {
      webcamError.value = 'Доступ к камере запрещен'
    } else if (errorMessage.includes('NotFoundError')) {
      webcamError.value = 'Камера не найдена'
    } else {
      webcamError.value = `Ошибка: ${errorMessage}`
    }
  }
}

function stopWebcam(): void {
  if (mediaStream.value) {
    mediaStream.value.getTracks().forEach(track => track.stop())
    mediaStream.value = null
  }

  if (videoRef.value) {
    videoRef.value.srcObject = null
  }

  isWebcamActive.value = false
}

function onSourceChange(source: CameraSource): void {
  if (currentSource.value === 'webcam') {
    stopWebcam()
  }

  currentSource.value = source
  clearError()

  if (source === 'webcam') {
    startWebcam()
  }
}

// Capture and detection
async function captureFrame(): Promise<Blob | null> {
  const video = videoRef.value
  const canvas = canvasRef.value

  if (!video || !canvas) return null

  const context = canvas.getContext('2d')
  if (!context) return null

  canvas.width = video.videoWidth || 640
  canvas.height = video.videoHeight || 480

  context.drawImage(video, 0, 0, canvas.width, canvas.height)

  return new Promise<Blob | null>((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.85)
  })
}

async function handleCapture(): Promise<void> {
  if (!canCapture.value) return

  let result: VehicleDetectionResult | null = null

  if (currentSource.value === 'mock') {
    result = useMockDetection()
    message.info(`Тест: ${result.plateNumber}`)
  } else {
    const imageBlob = await captureFrame()

    if (!imageBlob) {
      message.error('Не удалось захватить кадр')
      return
    }

    result = await detectVehicle(imageBlob)

    if (result) {
      message.success(`Распознан: ${result.plateNumber}`)
    } else if (detectionError.value) {
      message.error(detectionError.value)
    }
  }

  if (result) {
    emit('vehicleDetected', result)
  }
}

// Minimize/Expand toggle
function toggleMinimize(): void {
  isMinimized.value = !isMinimized.value
}

// Lifecycle
onMounted(() => {
  if (props.visible && currentSource.value === 'webcam') {
    startWebcam()
  }
})

onUnmounted(() => {
  stopWebcam()
})
</script>

<template>
  <Transition name="widget-slide">
    <div
      v-if="visible"
      ref="widgetRef"
      class="gate-camera-widget"
      :class="{ 'gate-widget--minimized': isMinimized }"
    >
      <!-- Header -->
      <header class="widget-header" @click="toggleMinimize">
        <div class="header-left">
          <div class="gate-badge">
            <svg class="gate-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
              <circle cx="12" cy="13" r="4"/>
            </svg>
            <span class="gate-label">{{ gateId }}</span>
          </div>
        </div>

        <div class="header-center">
          <div class="status-indicator" :class="statusType">
            <span class="status-dot"></span>
            <span class="status-label">{{ statusText }}</span>
          </div>
        </div>

        <div class="header-right">
          <button class="btn-icon btn-toggle" :title="isMinimized ? 'Развернуть' : 'Свернуть'">
            <UpOutlined v-if="isMinimized" />
            <DownOutlined v-else />
          </button>
        </div>
      </header>

      <!-- Video Feed -->
      <div v-show="!isMinimized" class="video-container">
          <video
            ref="videoRef"
            class="video-feed"
            playsinline
            muted
            :class="{ hidden: currentSource === 'mock' }"
          />

          <!-- Mock Feed -->
          <div v-if="currentSource === 'mock'" class="mock-feed">
            <div class="mock-pattern"></div>
            <div class="mock-content">
              <svg class="mock-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
              <span class="mock-text">Тестовый режим</span>
              <span class="mock-hint">Нажмите "Сканировать" для симуляции</span>
            </div>
          </div>

          <!-- Webcam Error -->
          <div v-if="currentSource === 'webcam' && webcamError" class="feed-error">
            <svg class="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span class="error-text">{{ webcamError }}</span>
            <button class="btn-retry" @click="startWebcam">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
              Повторить
            </button>
          </div>

          <!-- Scan Overlay -->
          <div v-if="isDetecting" class="scan-overlay">
            <div class="scan-frame">
              <span class="corner tl"></span>
              <span class="corner tr"></span>
              <span class="corner bl"></span>
              <span class="corner br"></span>
            </div>
            <div class="scan-progress">
              <div class="scan-bar"></div>
            </div>
          </div>

          <!-- Hidden canvas -->
          <canvas ref="canvasRef" class="capture-canvas" />
        </div>

      <!-- Detection Result -->
      <Transition name="result-slide">
        <div v-if="lastResult && !isMinimized" class="result-panel">
            <div class="result-header">
              <svg class="result-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span class="result-title">Распознано</span>
              <span class="result-time">{{ new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) }}</span>
            </div>

            <div class="result-plate">
              <span class="plate-number">{{ lastResult.plateNumber }}</span>
            </div>

            <div class="result-details">
              <div class="detail-item">
                <span class="detail-icon">{{ vehicleTypeIcons[lastResult.vehicleType] }}</span>
                <span class="detail-label">Тип</span>
                <span class="detail-value">{{ vehicleTypeLabels[lastResult.vehicleType] }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-icon">📊</span>
                <span class="detail-label">Точность</span>
                <span class="detail-value confidence" :class="{ high: lastResult.confidence >= 0.9 }">
                  {{ Math.round(lastResult.confidence * 100) }}%
                </span>
              </div>
            </div>
          </div>
        </Transition>

      <!-- Controls -->
      <div v-show="!isMinimized" class="controls-panel">
        <a-segmented
          :value="currentSource"
          :options="[
            { value: 'mock', label: 'Тест', icon: ToolOutlined },
            { value: 'webcam', label: 'Камера', icon: CameraOutlined },
          ]"
          block
          size="small"
          @change="(val: string | number) => onSourceChange(val as CameraSource)"
        />

        <a-button
          type="primary"
          block
          size="small"
          :loading="isDetecting"
          :disabled="!canCapture"
          class="scan-btn"
          @click.stop="handleCapture"
        >
          <template v-if="!isDetecting" #icon><ScanOutlined /></template>
          {{ isDetecting ? 'Анализ...' : 'Сканировать' }}
        </a-button>
      </div>

      <!-- Footer -->
      <footer v-show="!isMinimized" class="widget-footer">
        <span class="footer-hint">Нажмите на заголовок для сворачивания</span>
      </footer>
    </div>
  </Transition>
</template>

<style scoped>
/* ============================================
   GATE CAMERA WIDGET - Corporate Professional
   ============================================ */

/* Design Tokens - Using MTT Global Variables */
.gate-camera-widget {
  --widget-bg: var(--color-bg-card, #ffffff);
  --widget-border: var(--color-border, #e2e8f0);
  --widget-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
  --widget-shadow-lg: var(--shadow-xl, 0 20px 25px -5px rgba(0, 0, 0, 0.1));

  /* 3D Depth Effects */
  --widget-shadow-3d:
    0 2px 4px rgba(0, 0, 0, 0.1),
    0 8px 16px rgba(0, 0, 0, 0.1),
    0 16px 32px rgba(0, 0, 0, 0.15),
    0 32px 64px rgba(0, 0, 0, 0.1);
  --widget-border-glow: 0 0 0 1px rgba(255, 255, 255, 0.1);

  --text-primary: var(--color-text, #1e293b);
  --text-secondary: var(--color-text-secondary, #64748b);
  --text-muted: var(--color-text-muted, #94a3b8);

  --accent-primary: var(--color-primary, #3b82f6);
  --accent-success: var(--color-success, #10b981);
  --accent-warning: var(--color-warning, #f59e0b);
  --accent-error: var(--color-danger, #ef4444);

  --surface-1: var(--color-bg-page, #f8fafc);
  --surface-2: var(--color-bg-subtle, #f1f5f9);
  --surface-3: var(--color-bg-muted, #e2e8f0);

  --radius-sm: var(--radius-sm, 4px);
  --radius-md: var(--radius-md, 8px);
  --radius-lg: 16px;

  --transition-fast: 150ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;

  width: 260px;
  background: var(--widget-bg);
  border: 1px solid var(--widget-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  user-select: none;

  /* 3D Depth Styling */
  box-shadow:
    var(--widget-shadow-3d),
    var(--widget-border-glow),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  transform: perspective(1000px) rotateX(1deg);
  transform-origin: center bottom;
  transition:
    transform var(--transition-base),
    box-shadow var(--transition-base),
    height var(--transition-slow);
}

/* Hover effect for subtle 3D lift */
.gate-camera-widget:hover {
  transform: perspective(1000px) rotateX(0.5deg) translateY(-2px);
  box-shadow:
    0 4px 8px rgba(0, 0, 0, 0.12),
    0 12px 24px rgba(0, 0, 0, 0.12),
    0 24px 48px rgba(0, 0, 0, 0.15),
    0 48px 96px rgba(0, 0, 0, 0.1),
    var(--widget-border-glow),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

/* Minimized State */
.gate-camera-widget.gate-widget--minimized {
  height: auto;
  transform: perspective(1000px) rotateX(0deg);
  box-shadow:
    0 2px 4px rgba(0, 0, 0, 0.08),
    0 4px 8px rgba(0, 0, 0, 0.08),
    var(--widget-border-glow);
}

.gate-camera-widget.gate-widget--minimized:hover {
  transform: perspective(1000px) rotateX(0deg) translateY(-1px);
}

.gate-camera-widget.gate-widget--minimized .widget-header {
  border-bottom: none;
}

/* ============ HEADER ============ */
.widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--surface-1);
  border-bottom: 1px solid var(--widget-border);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.widget-header:hover {
  background: var(--surface-2);
}

.header-left,
.header-right {
  flex-shrink: 0;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.gate-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  background: var(--text-primary);
  border-radius: var(--radius-sm);
}

.gate-icon {
  width: 12px;
  height: 12px;
  color: white;
}

.gate-label {
  font-size: 10px;
  font-weight: 600;
  color: white;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Status Indicator */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: 100px;
  background: var(--surface-2);
  transition: background var(--transition-base);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: background var(--transition-base);
}

.status-indicator.online .status-dot {
  background: var(--accent-success);
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
}

.status-indicator.processing .status-dot {
  background: var(--accent-primary);
  animation: pulse 1s ease-in-out infinite;
}

.status-indicator.test .status-dot {
  background: var(--accent-warning);
}

.status-indicator.error .status-dot {
  background: var(--accent-error);
}

.status-indicator.offline .status-dot {
  background: var(--text-muted);
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.7; }
}

.status-label {
  font-size: 10px;
  font-weight: 500;
  color: var(--text-secondary);
}

/* Toggle Button */
.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-icon:hover {
  background: var(--surface-3);
  color: var(--text-primary);
}

.btn-icon svg,
.btn-icon :deep(svg) {
  width: 14px;
  height: 14px;
}

.btn-toggle {
  pointer-events: none;
}

/* ============ VIDEO CONTAINER ============ */
.video-container {
  position: relative;
  height: 130px;
  background: var(--text-primary);
  overflow: hidden;
  /* Inset shadow for depth - video appears recessed */
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.3);
}

.video-feed {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-feed.hidden {
  display: none;
}

/* Mock Feed */
.mock-feed {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
}

.mock-pattern {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 24px 24px;
}

.mock-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  z-index: 1;
}

.mock-icon {
  width: 32px;
  height: 32px;
  color: var(--text-muted);
  opacity: 0.5;
}

.mock-text {
  font-size: 12px;
  font-weight: 500;
  color: rgba(255,255,255,0.7);
}

.mock-hint {
  font-size: 10px;
  color: rgba(255,255,255,0.4);
}

/* Feed Error */
.feed-error {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
}

.error-icon {
  width: 40px;
  height: 40px;
  color: var(--accent-error);
  opacity: 0.8;
}

.error-text {
  font-size: 13px;
  color: rgba(255,255,255,0.8);
  text-align: center;
  max-width: 80%;
}

.btn-retry {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: var(--radius-sm);
  color: white;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-retry:hover {
  background: rgba(255,255,255,0.15);
  border-color: rgba(255,255,255,0.3);
}

.btn-retry svg {
  width: 14px;
  height: 14px;
}

/* Scan Overlay */
.scan-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(1px);
}

.scan-frame {
  position: relative;
  width: 70%;
  height: 60%;
}

.corner {
  position: absolute;
  width: 24px;
  height: 24px;
  border-color: var(--accent-primary);
  border-style: solid;
  border-width: 0;
}

.corner.tl { top: 0; left: 0; border-top-width: 3px; border-left-width: 3px; }
.corner.tr { top: 0; right: 0; border-top-width: 3px; border-right-width: 3px; }
.corner.bl { bottom: 0; left: 0; border-bottom-width: 3px; border-left-width: 3px; }
.corner.br { bottom: 0; right: 0; border-bottom-width: 3px; border-right-width: 3px; }

.scan-progress {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: 120px;
  height: 4px;
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
  overflow: hidden;
}

.scan-bar {
  height: 100%;
  background: var(--accent-primary);
  border-radius: 2px;
  animation: scan-progress 1.5s ease-in-out infinite;
}

@keyframes scan-progress {
  0% { width: 0%; }
  50% { width: 100%; }
  100% { width: 0%; }
}

.capture-canvas {
  display: none;
}

/* ============ RESULT PANEL ============ */
.result-panel {
  padding: 12px;
  background: linear-gradient(to bottom, rgba(16, 185, 129, 0.05), transparent);
  border-top: 1px solid rgba(16, 185, 129, 0.2);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.result-check {
  width: 18px;
  height: 18px;
  color: var(--accent-success);
}

.result-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-success);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.result-time {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.result-plate {
  display: flex;
  justify-content: center;
  margin-bottom: 10px;
}

.plate-number {
  display: inline-block;
  padding: 8px 16px;
  background: var(--text-primary);
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 700;
  color: white;
  letter-spacing: 1.5px;
  font-family: 'SF Mono', 'Consolas', 'Liberation Mono', monospace;
}

.result-details {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.detail-icon {
  font-size: 14px;
}

.detail-label {
  font-size: 11px;
  color: var(--text-muted);
}

.detail-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.detail-value.confidence.high {
  color: var(--accent-success);
}

/* ============ CONTROLS ============ */
.controls-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  background: var(--surface-1);
  border-top: 1px solid var(--widget-border);
}

.scan-btn {
  margin-top: 2px;
}

/* ============ FOOTER ============ */
.widget-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--surface-2);
  border-top: 1px solid var(--widget-border);
}

.footer-hint {
  font-size: 10px;
  color: var(--text-muted);
}

.footer-divider {
  color: var(--surface-3);
}

/* ============ TRANSITIONS ============ */
.widget-slide-enter-active,
.widget-slide-leave-active {
  transition: all 400ms cubic-bezier(0.16, 1, 0.3, 1);
}

.widget-slide-enter-from,
.widget-slide-leave-to {
  opacity: 0;
  transform: perspective(1000px) rotateX(10deg) translateY(24px) scale(0.95);
}

.result-slide-enter-active,
.result-slide-leave-active {
  transition: all var(--transition-base);
}

.result-slide-enter-from,
.result-slide-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  overflow: hidden;
}

.result-slide-enter-to,
.result-slide-leave-from {
  max-height: 200px;
}
</style>
