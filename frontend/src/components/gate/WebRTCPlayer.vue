<script setup lang="ts">
/**
 * WebRTCPlayer - Displays a live WebRTC stream from mediamtx
 *
 * Connects to a mediamtx WHEP endpoint and renders the video
 * stream in a <video> element. Handles connection, reconnection,
 * and cleanup automatically.
 */

import { ref, onMounted, onUnmounted, watch } from 'vue'

interface Props {
  /** mediamtx WHEP endpoint URL (e.g., http://localhost:8889/gate-main/whep) */
  url: string
  /** Whether to auto-connect on mount */
  autoConnect?: boolean
  /** Reconnect on failure */
  autoReconnect?: boolean
  /** Max reconnect attempts */
  maxReconnectAttempts?: number
  /** Reconnect interval in ms */
  reconnectInterval?: number
}

const props = withDefaults(defineProps<Props>(), {
  autoConnect: true,
  autoReconnect: true,
  maxReconnectAttempts: 10,
  reconnectInterval: 3000,
})

const emit = defineEmits<{
  connected: []
  disconnected: []
  error: [message: string]
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const status = ref<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected')
const errorMessage = ref<string | null>(null)

let peerConnection: RTCPeerConnection | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectAttempts = 0
let isDisposed = false

/** Create WebRTC connection to mediamtx WHEP endpoint */
async function connect(): Promise<void> {
  if (isDisposed) return

  disconnect()
  status.value = 'connecting'
  errorMessage.value = null

  try {
    peerConnection = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    })

    // Add transceiver for receiving video
    peerConnection.addTransceiver('video', { direction: 'recvonly' })
    peerConnection.addTransceiver('audio', { direction: 'recvonly' })

    // Handle incoming stream
    peerConnection.ontrack = (event: RTCTrackEvent) => {
      if (videoRef.value && event.streams[0]) {
        videoRef.value.srcObject = event.streams[0]
        status.value = 'connected'
        reconnectAttempts = 0
        emit('connected')
      }
    }

    // Handle connection state changes
    peerConnection.onconnectionstatechange = () => {
      if (!peerConnection) return

      if (peerConnection.connectionState === 'failed' ||
          peerConnection.connectionState === 'disconnected') {
        handleDisconnect('Соединение потеряно')
      }
    }

    peerConnection.oniceconnectionstatechange = () => {
      if (!peerConnection) return

      if (peerConnection.iceConnectionState === 'failed') {
        handleDisconnect('ICE соединение не удалось')
      }
    }

    // Create offer
    const offer = await peerConnection.createOffer()
    await peerConnection.setLocalDescription(offer)

    // Wait for ICE gathering to complete (or timeout)
    await waitForIceGathering(peerConnection, 2000)

    // Send offer to mediamtx WHEP endpoint
    const response = await fetch(props.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/sdp' },
      body: peerConnection.localDescription!.sdp,
    })

    if (!response.ok) {
      throw new Error(`WHEP ошибка: ${response.status} ${response.statusText}`)
    }

    const answerSdp = await response.text()
    await peerConnection.setRemoteDescription(
      new RTCSessionDescription({ type: 'answer', sdp: answerSdp })
    )
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Неизвестная ошибка подключения'
    handleDisconnect(msg)
  }
}

/** Wait for ICE gathering to complete or timeout */
function waitForIceGathering(pc: RTCPeerConnection, timeoutMs: number): Promise<void> {
  return new Promise((resolve) => {
    if (pc.iceGatheringState === 'complete') {
      resolve()
      return
    }

    const timeout = setTimeout(resolve, timeoutMs)

    pc.onicegatheringstatechange = () => {
      if (pc.iceGatheringState === 'complete') {
        clearTimeout(timeout)
        resolve()
      }
    }
  })
}

/** Handle disconnection with optional auto-reconnect */
function handleDisconnect(reason: string): void {
  status.value = 'error'
  errorMessage.value = reason
  emit('error', reason)
  emit('disconnected')

  if (props.autoReconnect && reconnectAttempts < props.maxReconnectAttempts && !isDisposed) {
    reconnectAttempts++
    reconnectTimer = setTimeout(() => {
      connect()
    }, props.reconnectInterval)
  }
}

/** Disconnect and cleanup */
function disconnect(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  if (peerConnection) {
    peerConnection.ontrack = null
    peerConnection.onconnectionstatechange = null
    peerConnection.oniceconnectionstatechange = null
    peerConnection.onicegatheringstatechange = null
    peerConnection.close()
    peerConnection = null
  }

  if (videoRef.value) {
    videoRef.value.srcObject = null
  }

  status.value = 'disconnected'
}

/** Retry connection manually */
function retry(): void {
  reconnectAttempts = 0
  connect()
}

// Watch for URL changes
watch(() => props.url, () => {
  if (status.value === 'connected' || status.value === 'connecting') {
    connect()
  }
})

onMounted(() => {
  if (props.autoConnect) {
    connect()
  }
})

onUnmounted(() => {
  isDisposed = true
  disconnect()
})

// Expose methods for parent component
defineExpose({ connect, disconnect, retry, status })
</script>

<template>
  <div class="webrtc-player">
    <video
      ref="videoRef"
      class="webrtc-video"
      autoplay
      playsinline
      muted
    />

    <!-- Connection status overlay -->
    <div v-if="status === 'connecting'" class="status-overlay">
      <a-spin />
      <span class="status-text">Подключение к камере...</span>
      <span v-if="reconnectAttempts > 0" class="reconnect-count">
        Попытка {{ reconnectAttempts }} / {{ maxReconnectAttempts }}
      </span>
    </div>

    <div v-if="status === 'error'" class="status-overlay error">
      <div class="error-icon">!</div>
      <span class="status-text">{{ errorMessage }}</span>
      <a-button size="small" type="primary" @click="retry">
        Переподключить
      </a-button>
    </div>

    <div v-if="status === 'disconnected' && !errorMessage" class="status-overlay">
      <span class="status-text">Камера отключена</span>
      <a-button size="small" type="primary" @click="connect">
        Подключить
      </a-button>
    </div>

    <!-- Connection indicator -->
    <div v-if="status === 'connected'" class="live-indicator">
      <span class="live-dot" />
      LIVE
    </div>
  </div>
</template>

<style scoped>
.webrtc-player {
  position: relative;
  width: 100%;
  height: 100%;
  background: #000;
  overflow: hidden;
}

.webrtc-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.status-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: rgba(0, 0, 0, 0.85);
  color: #fff;
}

.status-overlay.error {
  background: rgba(30, 0, 0, 0.9);
}

.error-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ff4d4f;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
}

.status-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
}

.reconnect-count {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.live-indicator {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff4d4f;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
