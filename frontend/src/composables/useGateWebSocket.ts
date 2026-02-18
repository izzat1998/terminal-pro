/**
 * useGateWebSocket - WebSocket composable for real-time gate camera events
 *
 * Connects to Django Channels WebSocket endpoint to receive vehicle detection
 * events in real-time. Use this when backend processes IP camera feeds and
 * broadcasts detections to connected clients.
 */

import { ref, shallowRef, onUnmounted } from 'vue'
import type { VehicleDetectionResult } from './useGateDetection'

export interface WebSocketConfig {
  gateId?: string
  autoReconnect?: boolean
  reconnectDelay?: number
  maxReconnectAttempts?: number
}

export interface GateWebSocketState {
  status: 'disconnected' | 'connecting' | 'connected' | 'error'
  error: string | null
  reconnectAttempts: number
}

export interface ANPRDetectionEvent extends VehicleDetectionResult {
  direction: 'approach' | 'depart' | 'unknown'
  matchedEntryId: number | null
  detectionId: number | null
}

type VehicleDetectedCallback = (detection: VehicleDetectionResult) => void
type ANPRDetectionCallback = (detection: ANPRDetectionEvent) => void

/** Safely invoke every callback in a list, logging errors without propagating. */
function notifyCallbacks<T>(callbacks: ((arg: T) => void)[], arg: T): void {
  for (const cb of callbacks) {
    try {
      cb(arg)
    } catch (err) {
      console.error('[GateWebSocket] Callback error:', err)
    }
  }
}

/** Subscribe to a callback list and return an unsubscribe function. */
function subscribe<T>(list: T[], item: T): () => void {
  list.push(item)
  return () => {
    const idx = list.indexOf(item)
    if (idx > -1) list.splice(idx, 1)
  }
}

export function useGateWebSocket(config: WebSocketConfig = {}) {
  const {
    gateId = 'main',
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 5,
  } = config

  const state = ref<GateWebSocketState>({
    status: 'disconnected',
    error: null,
    reconnectAttempts: 0,
  })

  const socket = shallowRef<WebSocket | null>(null)
  const vehicleDetectedCallbacks: VehicleDetectedCallback[] = []
  const anprDetectionCallbacks: ANPRDetectionCallback[] = []
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function buildWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_WS_HOST || window.location.host
    const wsHost = import.meta.env.DEV
      ? host.replace(/:\d+$/, ':8008')
      : host

    const token = localStorage.getItem('access_token')
    const query = token ? `?token=${token}` : ''

    return `${protocol}//${wsHost}/ws/gate/${gateId}/${query}`
  }

  function connect(): void {
    if (socket.value?.readyState === WebSocket.OPEN) return

    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    state.value.status = 'connecting'
    state.value.error = null

    const url = buildWebSocketUrl()
    console.log(`[GateWebSocket] Connecting to ${url}`)

    try {
      socket.value = new WebSocket(url)

      socket.value.onopen = () => {
        console.log('[GateWebSocket] Connected')
        state.value = { status: 'connected', error: null, reconnectAttempts: 0 }
      }

      socket.value.onclose = (event) => {
        console.log(`[GateWebSocket] Disconnected (code: ${event.code})`)
        state.value.status = 'disconnected'
        socket.value = null

        if (autoReconnect && event.code !== 1000) {
          scheduleReconnect()
        }
      }

      socket.value.onerror = (err) => {
        console.error('[GateWebSocket] Error:', err)
        state.value.status = 'error'
        state.value.error = 'Ошибка подключения к серверу'
      }

      socket.value.onmessage = (event) => {
        handleMessage(event.data)
      }
    } catch (err) {
      console.error('[GateWebSocket] Failed to create WebSocket:', err)
      state.value.status = 'error'
      state.value.error = 'Не удалось создать подключение'
    }
  }

  function disconnect(): void {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    if (socket.value) {
      socket.value.close(1000, 'Client disconnect')
      socket.value = null
    }

    state.value.status = 'disconnected'
    state.value.reconnectAttempts = 0
  }

  function scheduleReconnect(): void {
    if (state.value.reconnectAttempts >= maxReconnectAttempts) {
      console.error('[GateWebSocket] Max reconnect attempts reached')
      state.value.error = 'Превышено максимальное число попыток подключения'
      return
    }

    state.value.reconnectAttempts++
    console.log(
      `[GateWebSocket] Reconnecting in ${reconnectDelay}ms (attempt ${state.value.reconnectAttempts}/${maxReconnectAttempts})`
    )

    reconnectTimer = setTimeout(connect, reconnectDelay)
  }

  function handleMessage(raw: string): void {
    let msg: Record<string, unknown>
    try {
      msg = JSON.parse(raw) as Record<string, unknown>
    } catch {
      console.error('[GateWebSocket] Failed to parse message')
      return
    }

    if (msg.plate_number === undefined) return

    // Normalize confidence: camera sends 0-100 int, frontend expects 0-1 float
    const rawConfidence = (msg.plate_confidence ?? msg.confidence ?? 0.9) as number
    const confidence = rawConfidence > 1 ? rawConfidence / 100 : rawConfidence

    const detection: VehicleDetectionResult = {
      plateNumber: msg.plate_number as string,
      vehicleType: ((msg.vehicle_type as string) ?? 'UNKNOWN') as VehicleDetectionResult['vehicleType'],
      confidence,
      timestamp: (msg.timestamp as string) ?? new Date().toISOString(),
      source: 'api',
    }

    notifyCallbacks(vehicleDetectedCallbacks, detection)

    if (msg.event_type === 'anpr') {
      const anprEvent: ANPRDetectionEvent = {
        ...detection,
        direction: ((msg.direction as string) ?? 'unknown') as ANPRDetectionEvent['direction'],
        matchedEntryId: (msg.matched_entry_id as number) ?? null,
        detectionId: (msg.detection_id as number) ?? null,
      }
      notifyCallbacks(anprDetectionCallbacks, anprEvent)
    }
  }

  function onVehicleDetected(callback: VehicleDetectedCallback): () => void {
    return subscribe(vehicleDetectedCallbacks, callback)
  }

  function onANPRDetection(callback: ANPRDetectionCallback): () => void {
    return subscribe(anprDetectionCallbacks, callback)
  }

  function send(data: Record<string, unknown>): boolean {
    if (socket.value?.readyState !== WebSocket.OPEN) {
      console.warn('[GateWebSocket] Cannot send - not connected')
      return false
    }

    socket.value.send(JSON.stringify(data))
    return true
  }

  onUnmounted(() => disconnect())

  return {
    state,
    connect,
    disconnect,
    onVehicleDetected,
    onANPRDetection,
    send,
    isConnected: () => socket.value?.readyState === WebSocket.OPEN,
  }
}
