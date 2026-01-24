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
  /** Gate ID to subscribe to (default: 'main') */
  gateId?: string
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number
  /** Max reconnect attempts (default: 5) */
  maxReconnectAttempts?: number
}

export interface GateWebSocketState {
  /** Connection status */
  status: 'disconnected' | 'connecting' | 'connected' | 'error'
  /** Last error message */
  error: string | null
  /** Number of reconnect attempts */
  reconnectAttempts: number
}

type VehicleDetectedCallback = (detection: VehicleDetectionResult) => void

/**
 * WebSocket composable for gate camera real-time events
 *
 * @example
 * ```ts
 * const { connect, disconnect, onVehicleDetected, state } = useGateWebSocket()
 *
 * onVehicleDetected((detection) => {
 *   console.log('Vehicle detected:', detection.plate_number)
 *   spawnVehicle(detection)
 * })
 *
 * onMounted(() => connect())
 * onUnmounted(() => disconnect())
 * ```
 */
export function useGateWebSocket(config: WebSocketConfig = {}) {
  const {
    gateId = 'main',
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 5,
  } = config

  // State
  const state = ref<GateWebSocketState>({
    status: 'disconnected',
    error: null,
    reconnectAttempts: 0,
  })

  // WebSocket instance
  const socket = shallowRef<WebSocket | null>(null)

  // Event callbacks
  const vehicleDetectedCallbacks: VehicleDetectedCallback[] = []

  // Reconnect timer
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  /**
   * Build WebSocket URL for the gate
   */
  function buildWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_WS_HOST || window.location.host

    // In development, backend runs on different port
    const wsHost = import.meta.env.DEV
      ? host.replace(/:\d+$/, ':8008') // Replace frontend port with backend port
      : host

    return `${protocol}//${wsHost}/ws/gate/${gateId}/`
  }

  /**
   * Connect to WebSocket server
   */
  function connect(): void {
    if (socket.value?.readyState === WebSocket.OPEN) {
      console.warn('[GateWebSocket] Already connected')
      return
    }

    // Clear any pending reconnect
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
        state.value.status = 'connected'
        state.value.error = null
        state.value.reconnectAttempts = 0
      }

      socket.value.onclose = (event) => {
        console.log(`[GateWebSocket] Disconnected (code: ${event.code})`)
        state.value.status = 'disconnected'
        socket.value = null

        // Auto-reconnect if enabled and not a clean close
        if (autoReconnect && event.code !== 1000) {
          scheduleReconnect()
        }
      }

      socket.value.onerror = (error) => {
        console.error('[GateWebSocket] Error:', error)
        state.value.status = 'error'
        state.value.error = 'Ошибка подключения к серверу'
      }

      socket.value.onmessage = (event) => {
        handleMessage(event.data)
      }
    } catch (error) {
      console.error('[GateWebSocket] Failed to create WebSocket:', error)
      state.value.status = 'error'
      state.value.error = 'Не удалось создать подключение'
    }
  }

  /**
   * Disconnect from WebSocket server
   */
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

  /**
   * Schedule a reconnection attempt
   */
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

    reconnectTimer = setTimeout(() => {
      connect()
    }, reconnectDelay)
  }

  /**
   * Handle incoming WebSocket message
   */
  function handleMessage(data: string): void {
    try {
      const message = JSON.parse(data)

      // Vehicle detection event from backend
      // Backend sends: { plate_number, confidence, vehicle_type, ... }
      if (message.plate_number !== undefined) {
        // Map backend snake_case to frontend camelCase format
        const vehicleType = (message.vehicle_type ?? 'UNKNOWN') as VehicleDetectionResult['vehicleType']

        const detection: VehicleDetectionResult = {
          plateNumber: message.plate_number,
          vehicleType: vehicleType,
          confidence: message.plate_confidence ?? message.confidence ?? 0.9,
          timestamp: new Date().toISOString(),
          source: 'api',
        }

        // Notify all registered callbacks
        vehicleDetectedCallbacks.forEach((callback) => {
          try {
            callback(detection)
          } catch (error) {
            console.error('[GateWebSocket] Callback error:', error)
          }
        })
      }
    } catch (error) {
      console.error('[GateWebSocket] Failed to parse message:', error)
    }
  }

  /**
   * Register a callback for vehicle detection events
   *
   * @param callback Function to call when vehicle is detected
   * @returns Unsubscribe function
   */
  function onVehicleDetected(callback: VehicleDetectedCallback): () => void {
    vehicleDetectedCallbacks.push(callback)

    // Return unsubscribe function
    return () => {
      const index = vehicleDetectedCallbacks.indexOf(callback)
      if (index > -1) {
        vehicleDetectedCallbacks.splice(index, 1)
      }
    }
  }

  /**
   * Send a message to the WebSocket server (for future use)
   */
  function send(data: Record<string, unknown>): boolean {
    if (socket.value?.readyState !== WebSocket.OPEN) {
      console.warn('[GateWebSocket] Cannot send - not connected')
      return false
    }

    socket.value.send(JSON.stringify(data))
    return true
  }

  // Cleanup on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    /** Reactive connection state */
    state,
    /** Connect to WebSocket server */
    connect,
    /** Disconnect from WebSocket server */
    disconnect,
    /** Register callback for vehicle detection events */
    onVehicleDetected,
    /** Send message to server */
    send,
    /** Check if currently connected */
    isConnected: () => socket.value?.readyState === WebSocket.OPEN,
  }
}
