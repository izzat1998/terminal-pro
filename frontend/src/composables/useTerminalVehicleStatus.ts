/**
 * Terminal Vehicle Status Composable
 *
 * Provides reactive terminal vehicle status with auto-refresh polling.
 * Uses singleton pattern for shared state across components.
 */

import { ref, onMounted, onUnmounted, computed } from 'vue'
import { getTerminalVehiclesWithStatus } from '../services/terminalVehicleStatusService'
import type { TerminalVehicleWithStatus } from '../types/terminalVehicles'

// Singleton state (shared across all component instances)
const vehicles = ref<TerminalVehicleWithStatus[]>([])
const workingCount = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)
const lastFetched = ref<Date | null>(null)

// Polling configuration
const POLL_INTERVAL_MS = 30000 // 30 seconds
let pollInterval: ReturnType<typeof setInterval> | null = null
let activeSubscribers = 0

/**
 * Fetch vehicle status from API
 */
async function fetchVehicleStatus() {
  // Skip if already loading
  if (loading.value) return

  loading.value = true
  error.value = null

  try {
    const result = await getTerminalVehiclesWithStatus()
    vehicles.value = result.vehicles
    workingCount.value = result.workingCount
    lastFetched.value = new Date()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to fetch vehicle status'
    console.error('Failed to fetch vehicle status:', err)
  } finally {
    loading.value = false
  }
}

/**
 * Start polling for vehicle status updates
 */
function startPolling() {
  if (pollInterval) return // Already polling

  // Initial fetch
  fetchVehicleStatus()

  // Set up interval
  pollInterval = setInterval(fetchVehicleStatus, POLL_INTERVAL_MS)
}

/**
 * Stop polling
 */
function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

/**
 * Composable for terminal vehicle status with auto-refresh
 *
 * Uses singleton pattern - all components share the same state.
 * Polling starts when first subscriber mounts and stops when last unmounts.
 */
export function useTerminalVehicleStatus() {
  // Computed properties
  const availableVehicles = computed(() =>
    vehicles.value.filter((v) => v.status === 'available')
  )

  const workingVehicles = computed(() =>
    vehicles.value.filter((v) => v.status === 'working')
  )

  const offlineVehicles = computed(() =>
    vehicles.value.filter((v) => v.status === 'offline')
  )

  // Lifecycle management
  onMounted(() => {
    activeSubscribers++
    if (activeSubscribers === 1) {
      startPolling()
    }
  })

  onUnmounted(() => {
    activeSubscribers--
    if (activeSubscribers === 0) {
      stopPolling()
    }
  })

  return {
    // State
    vehicles,
    workingCount,
    loading,
    error,
    lastFetched,

    // Computed
    availableVehicles,
    workingVehicles,
    offlineVehicles,

    // Actions
    refresh: fetchVehicleStatus,
  }
}
