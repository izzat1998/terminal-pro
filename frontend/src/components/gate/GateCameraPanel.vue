<script setup lang="ts">
/**
 * GateCameraPanel - Development Testing UI for Gate Camera
 *
 * Displays camera feed (webcam, video file, or placeholder)
 * and allows capturing frames for vehicle detection.
 */

import { ref, onMounted, onUnmounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { http } from '@/utils/httpClient'
import { useGateDetection, type VehicleDetectionResult } from '@/composables/useGateDetection'
import { useGateWebSocket, type ANPRDetectionEvent } from '@/composables/useGateWebSocket'
import type { VehicleType } from '@/composables/useVehicleModels'
import WebRTCPlayer from './WebRTCPlayer.vue'

type CameraSource = 'webcam' | 'video' | 'mock' | 'rtsp'

interface Props {
  /** Initial camera source mode */
  initialSource?: CameraSource
  /** WebRTC stream URL from mediamtx (for rtsp source) */
  streamUrl?: string
}

const props = withDefaults(defineProps<Props>(), {
  initialSource: 'mock',
  streamUrl: '',
})

// Resolve stream URL: prop > env > default
const resolvedStreamUrl = computed(() =>
  props.streamUrl || import.meta.env.VITE_GATE_CAMERA_WEBRTC_URL || 'http://localhost:8889/gate-sub/whep'
)

const emit = defineEmits<{
  vehicleDetected: [result: VehicleDetectionResult]
}>()

// Camera state
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

const currentSource = ref<CameraSource>(props.initialSource)
const isMockMode = ref(true)
const isWebcamActive = ref(false)
const videoFileName = ref<string | null>(null)
const webcamError = ref<string | null>(null)
const mediaStream = ref<MediaStream | null>(null)

// Detection state
const { isDetecting, lastResult, error: detectionError, detectVehicle, useMockDetection, clearError } = useGateDetection()

// Detection history for display
const detectionHistory = ref<VehicleDetectionResult[]>([])
const MAX_HISTORY = 10

// WebRTC player ref
const webrtcPlayerRef = ref<InstanceType<typeof WebRTCPlayer> | null>(null)

// ANPR WebSocket for real-time detections on RTSP mode
const { connect: wsConnect, disconnect: wsDisconnect, onANPRDetection, state: wsState } = useGateWebSocket()

// ANPR overlay toast state
interface ANPRToast {
  id: number
  plateNumber: string
  confidence: number
  direction: 'approach' | 'depart' | 'unknown'
  matched: boolean
  timestamp: string
}
const anprToasts = ref<ANPRToast[]>([])
const MAX_TOASTS = 3
let toastIdCounter = 0

// Computed
const sourceOptions = [
  { value: 'rtsp', label: 'IP Камера' },
  { value: 'webcam', label: 'Веб-камера' },
  { value: 'video', label: 'Видео файл' },
  { value: 'mock', label: 'Тест (Mock)' },
]

const isVideoPlaying = computed(() => {
  const video = videoRef.value
  return video && !video.paused && !video.ended
})

const canCapture = computed(() => {
  if (currentSource.value === 'mock') return true
  if (currentSource.value === 'rtsp') return webrtcPlayerRef.value?.status === 'connected'
  if (currentSource.value === 'webcam') return isWebcamActive.value
  if (currentSource.value === 'video') return videoFileName.value !== null
  return false
})

const vehicleTypeLabels: Record<VehicleType, string> = {
  TRUCK: 'Грузовик',
  CAR: 'Легковой',
  WAGON: 'Вагон',
  UNKNOWN: 'Неизвестно',
}

const vehicleTypeColors: Record<VehicleType, string> = {
  TRUCK: 'blue',
  CAR: 'green',
  WAGON: 'orange',
  UNKNOWN: 'default',
}

const directionLabels: Record<string, string> = {
  approach: 'Въезд',
  depart: 'Выезд',
  unknown: '',
}

const directionIcons: Record<string, string> = {
  approach: '>>',
  depart: '<<',
  unknown: '--',
}

/**
 * Handle incoming ANPR detection from WebSocket.
 * Shows overlay toast and adds to detection history.
 */
function handleANPRDetection(event: ANPRDetectionEvent): void {
  // Show overlay toast
  const toast: ANPRToast = {
    id: ++toastIdCounter,
    plateNumber: event.plateNumber,
    confidence: Math.round(event.confidence * 100),
    direction: event.direction,
    matched: event.matchedEntryId !== null,
    timestamp: event.timestamp,
  }

  anprToasts.value.unshift(toast)
  if (anprToasts.value.length > MAX_TOASTS) {
    anprToasts.value.pop()
  }

  // Auto-remove toast after 8 seconds
  const toastId = toast.id
  setTimeout(() => {
    anprToasts.value = anprToasts.value.filter(t => t.id !== toastId)
  }, 8000)

  // Add to detection history
  const detection: VehicleDetectionResult = {
    plateNumber: event.plateNumber,
    vehicleType: (event.vehicleType || 'UNKNOWN') as VehicleType,
    confidence: event.confidence,
    timestamp: event.timestamp,
    source: 'api',
  }

  detectionHistory.value.unshift(detection)
  if (detectionHistory.value.length > MAX_HISTORY) {
    detectionHistory.value.pop()
  }

  // Emit to parent
  emit('vehicleDetected', detection)

  if (toast.matched) {
    message.success(`Автоматический въезд: ${event.plateNumber}`)
  }
}

// Methods
async function startWebcam(): Promise<void> {
  webcamError.value = null

  if (!navigator.mediaDevices?.getUserMedia) {
    webcamError.value = 'Веб-камера не поддерживается в этом браузере'
    message.error(webcamError.value)
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
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
      webcamError.value = 'Доступ к камере запрещен. Разрешите доступ в настройках браузера.'
    } else if (errorMessage.includes('NotFoundError')) {
      webcamError.value = 'Камера не найдена. Проверьте подключение.'
    } else {
      webcamError.value = `Ошибка камеры: ${errorMessage}`
    }
    message.error(webcamError.value)
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
  // Cleanup previous source
  if (currentSource.value === 'webcam') {
    stopWebcam()
  }
  if (currentSource.value === 'video' && videoRef.value) {
    videoRef.value.src = ''
    videoFileName.value = null
  }
  if (currentSource.value === 'rtsp') {
    webrtcPlayerRef.value?.disconnect()
    wsDisconnect()
  }

  currentSource.value = source
  clearError()

  // Initialize new source
  if (source === 'webcam') {
    startWebcam()
  }
  if (source === 'rtsp') {
    // Connect WebSocket for real-time ANPR events
    wsConnect()
  }
  // WebRTCPlayer auto-connects via autoConnect prop
}

function onFileSelect(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) return

  if (!file.type.startsWith('video/')) {
    message.error('Выберите видео файл (.mp4, .webm)')
    return
  }

  const url = URL.createObjectURL(file)

  if (videoRef.value) {
    videoRef.value.src = url
    videoRef.value.loop = true
    videoFileName.value = file.name
    videoRef.value.play()
  }
}

function openFilePicker(): void {
  fileInputRef.value?.click()
}

function toggleVideoPlayback(): void {
  if (!videoRef.value) return

  if (videoRef.value.paused) {
    videoRef.value.play()
  } else {
    videoRef.value.pause()
  }
}

async function captureFrame(): Promise<Blob | null> {
  const video = videoRef.value
  const canvas = canvasRef.value

  if (!video || !canvas) return null

  const context = canvas.getContext('2d')
  if (!context) return null

  // Set canvas size to match video
  canvas.width = video.videoWidth || 640
  canvas.height = video.videoHeight || 480

  // Draw video frame to canvas
  context.drawImage(video, 0, 0, canvas.width, canvas.height)

  // Convert to blob
  return new Promise<Blob | null>((resolve) => {
    canvas.toBlob(
      (blob) => resolve(blob),
      'image/jpeg',
      0.85
    )
  })
}

async function handleCapture(): Promise<void> {
  if (!canCapture.value) return

  let result: VehicleDetectionResult | null = null

  if (isMockMode.value || currentSource.value === 'mock') {
    // Use mock detection
    result = useMockDetection()
    message.info(`Тестовое распознавание: ${result.plateNumber}`)
  } else {
    // Capture frame and detect
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
    // Add to history
    detectionHistory.value.unshift(result)
    if (detectionHistory.value.length > MAX_HISTORY) {
      detectionHistory.value.pop()
    }

    // Emit to parent
    emit('vehicleDetected', result)
  }
}

function clearHistory(): void {
  detectionHistory.value = []
}

function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString('ru-RU')
}

// PTZ zoom control
const isZooming = ref(false)

function startZoom(action: 'zoom_in' | 'zoom_out'): void {
  isZooming.value = true
  http.post('/gate/camera/ptz/', { action, speed: 50 }).catch(() => {
    message.error('Ошибка управления камерой')
  })
}

function stopZoom(): void {
  if (!isZooming.value) return
  isZooming.value = false
  http.post('/gate/camera/ptz/', { action: 'zoom_stop' }).catch(() => {
    // Silent — stop failure is non-critical, motor auto-stops
  })
}

// Lifecycle
onMounted(() => {
  // Register ANPR detection callback
  onANPRDetection(handleANPRDetection)

  if (props.initialSource === 'webcam') {
    startWebcam()
  }
  if (props.initialSource === 'rtsp') {
    wsConnect()
  }
})

onUnmounted(() => {
  stopWebcam()
  wsDisconnect()

  // Revoke video URL if loaded from file
  if (videoRef.value?.src.startsWith('blob:')) {
    URL.revokeObjectURL(videoRef.value.src)
  }
})
</script>

<template>
  <div class="gate-camera-panel">
    <!-- Header -->
    <div class="panel-header">
      <h3>Камера ворот</h3>
      <a-space>
        <a-tooltip title="Тестовый режим (без API)">
          <a-switch
            v-model:checked="isMockMode"
            checked-children="Тест"
            un-checked-children="API"
          />
        </a-tooltip>
      </a-space>
    </div>

    <!-- Source selector -->
    <div class="source-selector">
      <a-segmented
        :value="currentSource"
        :options="sourceOptions"
        @change="(val: string) => onSourceChange(val as CameraSource)"
      />
    </div>

    <!-- Video display area -->
    <div class="video-container">
      <!-- RTSP/IP Camera via WebRTC -->
      <WebRTCPlayer
        v-if="currentSource === 'rtsp'"
        ref="webrtcPlayerRef"
        :url="resolvedStreamUrl"
        auto-connect
        auto-reconnect
      />

      <!-- Webcam / Video file -->
      <video
        v-show="currentSource === 'webcam' || currentSource === 'video'"
        ref="videoRef"
        class="video-element"
        playsinline
        muted
      />

      <!-- Mock mode placeholder -->
      <div v-if="currentSource === 'mock'" class="mock-placeholder">
        <div class="mock-icon">
          <span class="icon">📷</span>
        </div>
        <p>Тестовый режим</p>
        <p class="mock-hint">Нажмите "Захват" для генерации тестовых данных</p>
      </div>

      <!-- Webcam error -->
      <div v-if="currentSource === 'webcam' && webcamError" class="webcam-error">
        <a-result status="error" :title="webcamError">
          <template #extra>
            <a-button @click="startWebcam">Повторить</a-button>
          </template>
        </a-result>
      </div>

      <!-- Video file prompt -->
      <div v-if="currentSource === 'video' && !videoFileName" class="video-prompt">
        <a-button type="dashed" size="large" @click="openFilePicker">
          <template #icon><span>📁</span></template>
          Выбрать видео файл
        </a-button>
        <input
          ref="fileInputRef"
          type="file"
          accept="video/mp4,video/webm,video/ogg"
          style="display: none"
          @change="onFileSelect"
        >
      </div>

      <!-- ANPR detection overlay toasts -->
      <div v-if="currentSource === 'rtsp' && anprToasts.length > 0" class="anpr-overlay">
        <transition-group name="anpr-toast">
          <div
            v-for="toast in anprToasts"
            :key="toast.id"
            class="anpr-toast"
            :class="{ 'anpr-toast--matched': toast.matched }"
          >
            <div class="anpr-toast-plate">{{ toast.plateNumber }}</div>
            <div class="anpr-toast-meta">
              <span v-if="directionLabels[toast.direction]" class="anpr-toast-direction">
                {{ directionIcons[toast.direction] }} {{ directionLabels[toast.direction] }}
              </span>
              <span class="anpr-toast-confidence">{{ toast.confidence }}%</span>
              <a-tag v-if="toast.matched" color="green" size="small">Сопоставлен</a-tag>
            </div>
          </div>
        </transition-group>
      </div>

      <!-- WebSocket connection status indicator for RTSP mode -->
      <div v-if="currentSource === 'rtsp'" class="ws-status-indicator">
        <span
          class="ws-status-dot"
          :class="{
            'ws-status-dot--connected': wsState.status === 'connected',
            'ws-status-dot--connecting': wsState.status === 'connecting',
            'ws-status-dot--error': wsState.status === 'error',
          }"
        />
        <span class="ws-status-label">ANPR</span>
      </div>

      <!-- Zoom controls for IP camera -->
      <div v-if="currentSource === 'rtsp'" class="zoom-controls">
        <button
          class="zoom-btn zoom-btn--in"
          @mousedown="startZoom('zoom_in')"
          @mouseup="stopZoom"
          @mouseleave="stopZoom"
          @touchstart.prevent="startZoom('zoom_in')"
          @touchend.prevent="stopZoom"
        >+</button>
        <button
          class="zoom-btn zoom-btn--out"
          @mousedown="startZoom('zoom_out')"
          @mouseup="stopZoom"
          @mouseleave="stopZoom"
          @touchstart.prevent="startZoom('zoom_out')"
          @touchend.prevent="stopZoom"
        >&minus;</button>
      </div>

      <!-- Hidden canvas for frame capture -->
      <canvas ref="canvasRef" class="capture-canvas" />
    </div>

    <!-- Video controls -->
    <div v-if="currentSource === 'video' && videoFileName" class="video-controls">
      <a-space>
        <a-button @click="toggleVideoPlayback">
          {{ isVideoPlaying ? 'Пауза' : 'Воспроизвести' }}
        </a-button>
        <span class="video-filename">{{ videoFileName }}</span>
        <a-button type="link" danger @click="() => { videoFileName = null; if (videoRef) videoRef.src = '' }">
          Убрать
        </a-button>
      </a-space>
    </div>

    <!-- Capture button -->
    <div class="capture-section">
      <a-button
        type="primary"
        size="large"
        block
        :loading="isDetecting"
        :disabled="!canCapture"
        @click="handleCapture"
      >
        {{ isDetecting ? 'Распознавание...' : 'Захват' }}
      </a-button>
    </div>

    <!-- Last detection result -->
    <div v-if="lastResult" class="last-result">
      <a-divider>Последний результат</a-divider>
      <div class="result-card">
        <div class="result-plate">{{ lastResult.plateNumber }}</div>
        <div class="result-details">
          <a-tag :color="vehicleTypeColors[lastResult.vehicleType]">
            {{ vehicleTypeLabels[lastResult.vehicleType] }}
          </a-tag>
          <span class="result-confidence">
            {{ Math.round(lastResult.confidence * 100) }}%
          </span>
          <a-tag v-if="lastResult.source === 'mock'" color="orange">Тест</a-tag>
        </div>
      </div>
    </div>

    <!-- Detection history -->
    <div v-if="detectionHistory.length > 0" class="detection-history">
      <div class="history-header">
        <span>История распознаваний</span>
        <a-button type="link" size="small" @click="clearHistory">Очистить</a-button>
      </div>
      <div class="history-list">
        <div
          v-for="(item, index) in detectionHistory"
          :key="index"
          class="history-item"
        >
          <span class="history-plate">{{ item.plateNumber }}</span>
          <a-tag :color="vehicleTypeColors[item.vehicleType]" size="small">
            {{ vehicleTypeLabels[item.vehicleType] }}
          </a-tag>
          <span class="history-time">{{ formatTime(item.timestamp) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gate-camera-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.source-selector {
  padding: 12px 16px;
  background: #fafafa;
}

.video-container {
  position: relative;
  flex: 1;
  min-height: 200px;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-element.hidden {
  display: none;
}

.mock-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  text-align: center;
}

.mock-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.mock-icon .icon {
  filter: grayscale(100%);
}

.mock-placeholder p {
  margin: 4px 0;
}

.mock-hint {
  font-size: 12px;
  opacity: 0.6;
}

.webcam-error {
  padding: 24px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
}

.video-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.capture-canvas {
  display: none;
}

.video-controls {
  padding: 8px 16px;
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
}

.video-filename {
  color: #666;
  font-size: 12px;
}

.capture-section {
  padding: 16px;
}

.last-result {
  padding: 0 16px 16px;
}

.result-card {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.result-plate {
  font-size: 24px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: #52c41a;
  margin-bottom: 8px;
}

.result-details {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.result-confidence {
  color: #888;
  font-size: 12px;
}

.detection-history {
  border-top: 1px solid #f0f0f0;
  padding: 12px 16px;
  max-height: 200px;
  overflow-y: auto;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  color: #888;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: #fafafa;
  border-radius: 4px;
  font-size: 12px;
}

.history-plate {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
}

.history-time {
  margin-left: auto;
  color: #999;
}

/* ANPR overlay toasts */
.anpr-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.anpr-toast {
  background: rgba(0, 0, 0, 0.85);
  border-left: 3px solid #1890ff;
  border-radius: 6px;
  padding: 10px 14px;
  min-width: 200px;
  backdrop-filter: blur(8px);
}

.anpr-toast--matched {
  border-left-color: #52c41a;
}

.anpr-toast-plate {
  font-size: 18px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: #fff;
  letter-spacing: 1px;
}

.anpr-toast-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
}

.anpr-toast-direction {
  font-weight: 600;
}

.anpr-toast-confidence {
  opacity: 0.6;
}

/* Toast transition */
.anpr-toast-enter-active {
  transition: all 0.3s ease-out;
}

.anpr-toast-leave-active {
  transition: all 0.4s ease-in;
}

.anpr-toast-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.anpr-toast-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

/* WebSocket connection status indicator */
.ws-status-indicator {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 12px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.8);
  pointer-events: none;
}

.ws-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
}

.ws-status-dot--connected {
  background: #52c41a;
  box-shadow: 0 0 4px #52c41a;
}

.ws-status-dot--connecting {
  background: #faad14;
  animation: pulse 1s infinite;
}

.ws-status-dot--error {
  background: #ff4d4f;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Zoom controls */
.zoom-controls {
  position: absolute;
  bottom: 12px;
  right: 12px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.zoom-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  -webkit-user-select: none;
  transition: background 0.15s;
}

.zoom-btn:hover {
  background: rgba(0, 0, 0, 0.8);
}

.zoom-btn:active {
  background: rgba(24, 144, 255, 0.8);
}
</style>
