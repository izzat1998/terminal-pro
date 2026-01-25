<script setup lang="ts">
/**
 * GateCameraWidget - Floating camera widget for vehicle detection
 *
 * Opens when user clicks on 3D gate camera.
 * Provides camera feed display and vehicle detection controls.
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useGateDetection, type VehicleDetectionResult } from '@/composables/useGateDetection'
import type { VehicleType } from '@/composables/useVehicleModels'

type CameraSource = 'webcam' | 'mock'

interface Props {
  /** Show/hide the widget */
  visible: boolean
  /** Screen position { x, y } */
  position: { x: number; y: number }
  /** Initial camera source */
  initialSource?: CameraSource
}

const props = withDefaults(defineProps<Props>(), {
  initialSource: 'mock',
})

const emit = defineEmits<{
  close: []
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

// Dragging state
const isDragging = ref(false)
const dragOffset = ref({ x: 0, y: 0 })
const widgetPosition = ref({ x: props.position.x, y: props.position.y })

// Detection
const { isDetecting, lastResult, error: detectionError, useMockDetection, detectVehicle, clearError } = useGateDetection()

// Computed
const canCapture = computed(() => {
  if (currentSource.value === 'mock') return true
  if (currentSource.value === 'webcam') return isWebcamActive.value
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

// Watch for position changes
watch(() => props.position, (newPos) => {
  if (!isDragging.value) {
    widgetPosition.value = { x: newPos.x, y: newPos.y }
  }
}, { immediate: true })

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

// Close handlers
function handleClose(): void {
  stopWebcam()
  emit('close')
}

function handleKeyDown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && props.visible) {
    handleClose()
  }
}

// Drag handlers
function startDrag(event: MouseEvent): void {
  isDragging.value = true
  dragOffset.value = {
    x: event.clientX - widgetPosition.value.x,
    y: event.clientY - widgetPosition.value.y,
  }

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

function onDrag(event: MouseEvent): void {
  if (!isDragging.value) return

  widgetPosition.value = {
    x: event.clientX - dragOffset.value.x,
    y: event.clientY - dragOffset.value.y,
  }
}

function stopDrag(): void {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}

// Lifecycle
onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)

  if (props.visible && currentSource.value === 'webcam') {
    startWebcam()
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
  stopWebcam()
})
</script>

<template>
  <Teleport to="body">
    <Transition name="widget-fade">
      <div
        v-if="visible"
        ref="widgetRef"
        class="gate-camera-widget"
        :style="{
          left: `${widgetPosition.x}px`,
          top: `${widgetPosition.y}px`,
        }"
      >
        <!-- Header (draggable) -->
        <div class="widget-header" @mousedown="startDrag">
          <span class="widget-title">
            <span class="camera-icon">📷</span>
            Камера ворот
          </span>
          <button class="close-btn" @click="handleClose" @mousedown.stop>
            ✕
          </button>
        </div>

        <!-- Video area -->
        <div class="video-container">
          <video
            ref="videoRef"
            class="video-element"
            playsinline
            muted
            :class="{ hidden: currentSource === 'mock' }"
          />

          <!-- Mock placeholder -->
          <div v-if="currentSource === 'mock'" class="mock-placeholder">
            <span class="mock-icon">📷</span>
            <span class="mock-text">Тестовый режим</span>
          </div>

          <!-- Webcam error -->
          <div v-if="currentSource === 'webcam' && webcamError" class="webcam-error">
            <span class="error-icon">⚠️</span>
            <span class="error-text">{{ webcamError }}</span>
            <a-button size="small" @click="startWebcam">Повторить</a-button>
          </div>

          <!-- Hidden canvas -->
          <canvas ref="canvasRef" class="capture-canvas" />
        </div>

        <!-- Source toggle -->
        <div class="source-toggle">
          <a-radio-group
            :value="currentSource"
            size="small"
            button-style="solid"
            @change="(e: Event) => onSourceChange((e.target as HTMLInputElement).value as CameraSource)"
          >
            <a-radio-button value="mock">Тест</a-radio-button>
            <a-radio-button value="webcam">Камера</a-radio-button>
          </a-radio-group>
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

        <!-- Last result -->
        <div v-if="lastResult" class="last-result">
          <div class="result-plate">{{ lastResult.plateNumber }}</div>
          <div class="result-details">
            <a-tag :color="vehicleTypeColors[lastResult.vehicleType]" size="small">
              {{ vehicleTypeLabels[lastResult.vehicleType] }}
            </a-tag>
            <span class="result-confidence">
              {{ Math.round(lastResult.confidence * 100) }}%
            </span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.gate-camera-widget {
  position: fixed;
  width: 300px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  z-index: 1000;
  overflow: hidden;
  user-select: none;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  cursor: move;
}

.widget-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}

.camera-icon {
  font-size: 16px;
}

.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: #fff;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.video-container {
  position: relative;
  height: 180px;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-element.hidden {
  display: none;
}

.mock-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #888;
}

.mock-icon {
  font-size: 32px;
  opacity: 0.5;
  filter: grayscale(100%);
}

.mock-text {
  font-size: 12px;
}

.webcam-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
}

.error-icon {
  font-size: 24px;
}

.error-text {
  font-size: 12px;
  color: #ff4d4f;
  text-align: center;
}

.capture-canvas {
  display: none;
}

.source-toggle {
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: center;
}

.capture-section {
  padding: 12px 16px;
}

.last-result {
  padding: 12px 16px;
  background: #f6ffed;
  border-top: 1px solid #b7eb8f;
}

.result-plate {
  font-size: 20px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: #52c41a;
  text-align: center;
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

/* Transition */
.widget-fade-enter-active,
.widget-fade-leave-active {
  transition: all 0.2s ease;
}

.widget-fade-enter-from,
.widget-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
