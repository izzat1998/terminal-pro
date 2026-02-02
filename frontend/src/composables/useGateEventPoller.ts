/**
 * Gate Event Poller Composable
 *
 * Polls /api/vehicles/entries/ for new vehicle entry/exit events and triggers
 * callbacks for 3D animations. Deduplicates against camera-triggered
 * events to prevent double animations.
 */

import { ref, onUnmounted } from 'vue'
import { http } from '@/utils/httpClient'
import type { VehicleType } from '@/composables/useVehicleModels'

/** Minimal entry data needed for gate animations */
export interface GateEntryEvent {
  id: number
  plateNumber: string
  vehicleType: VehicleType
  entryTime: string | null
  exitTime: string | null
}

/** Raw VehicleEntry from /api/vehicles/entries/ */
interface RawVehicleEntry {
  id: number
  status: string
  license_plate: string
  vehicle_type: string
  vehicle_type_display: string
  transport_type: string | null
  transport_type_display: string | null
  entry_time: string | null
  exit_time: string | null
  is_on_terminal: boolean
}

interface PaginatedResponse {
  results: RawVehicleEntry[]
  count: number
}

/** Map backend transport type to 3D VehicleType */
function mapVehicleType(entry: RawVehicleEntry): VehicleType {
  const transport = entry.transport_type_display ?? entry.transport_type ?? ''
  switch (transport) {
    case 'Платформа':
    case 'Фура':
    case 'Прицеп':
    case 'PLATFORM':
    case 'TRUCK':
    case 'TRAILER':
    case 'ЗИЛ':
    case 'Газель':
    case 'Лабо':
    case 'Мини-грузовик':
    case 'ZIL':
    case 'GAZELLE':
    case 'LABO':
    case 'MINI_TRUCK':
      return 'TRUCK'
    default:
      return entry.vehicle_type === 'LIGHT' ? 'CAR' : 'TRUCK'
  }
}

export interface GateEventPollerOptions {
  /** Poll interval in ms (default: 5000) */
  interval?: number
  /** Called when a new entry is detected */
  onNewEntry: (event: GateEntryEvent) => void
  /** Called when a new exit is detected */
  onNewExit: (event: GateEntryEvent) => void
}

export function useGateEventPoller(options: GateEventPollerOptions) {
  const { interval = 5000, onNewEntry, onNewExit } = options

  const isPolling = ref(false)
  const lastError = ref<string | null>(null)

  // Track what we've already animated to prevent duplicates
  const seenEntryIds = new Set<number>()
  const seenExitIds = new Set<number>()

  // Camera-triggered plates — poller skips these (30s TTL per plate)
  const recentCameraPlates = new Map<string, number>() // plate → expiry timestamp
  const CAMERA_PLATE_TTL = 30_000 // 30 seconds

  let intervalId: ReturnType<typeof setInterval> | null = null
  let lastPollTime = new Date()

  /**
   * Register a plate as camera-handled so the poller skips it.
   * Call this from camera detection handlers.
   */
  function addCameraPlate(plate: string): void {
    recentCameraPlates.set(plate.toUpperCase(), Date.now() + CAMERA_PLATE_TTL)
  }

  /** Check if plate was recently handled by camera */
  function isCameraHandled(plate: string): boolean {
    const expiry = recentCameraPlates.get(plate.toUpperCase())
    if (!expiry) return false
    if (Date.now() > expiry) {
      recentCameraPlates.delete(plate.toUpperCase())
      return false
    }
    return true
  }

  /** Clean up expired camera plates */
  function cleanExpiredPlates(): void {
    const now = Date.now()
    for (const [plate, expiry] of recentCameraPlates) {
      if (now > expiry) recentCameraPlates.delete(plate)
    }
  }

  /** Fetch recent vehicle entries from API */
  async function poll(): Promise<void> {
    try {
      const response = await http.get<PaginatedResponse>(
        '/vehicles/entries/?ordering=-entry_time&page_size=20'
      )

      const entries = response.results ?? []

      for (const entry of entries) {
        const entryTime = entry.entry_time ? new Date(entry.entry_time) : null
        const exitTime = entry.exit_time ? new Date(entry.exit_time) : null

        // Detect new entries: ON_TERMINAL, entry_time after last poll, not seen
        if (
          entry.status === 'ON_TERMINAL' &&
          entryTime &&
          entryTime > lastPollTime &&
          !seenEntryIds.has(entry.id) &&
          !isCameraHandled(entry.license_plate)
        ) {
          seenEntryIds.add(entry.id)
          onNewEntry({
            id: entry.id,
            plateNumber: entry.license_plate,
            vehicleType: mapVehicleType(entry),
            entryTime: entry.entry_time,
            exitTime: null,
          })
        }

        // Detect new exits: EXITED, exit_time after last poll, not seen as exit
        if (
          entry.status === 'EXITED' &&
          exitTime &&
          exitTime > lastPollTime &&
          !seenExitIds.has(entry.id) &&
          !isCameraHandled(entry.license_plate)
        ) {
          seenExitIds.add(entry.id)
          onNewExit({
            id: entry.id,
            plateNumber: entry.license_plate,
            vehicleType: mapVehicleType(entry),
            entryTime: entry.entry_time,
            exitTime: entry.exit_time,
          })
        }
      }

      lastPollTime = new Date()
      lastError.value = null
      cleanExpiredPlates()
    } catch (e) {
      lastError.value = e instanceof Error ? e.message : 'Poll failed'
      if (import.meta.env.DEV) console.warn('[useGateEventPoller] Poll error:', e)
    }
  }

  /** Start polling */
  function start(): void {
    if (isPolling.value) return
    isPolling.value = true
    lastPollTime = new Date() // Only detect events from now on
    intervalId = setInterval(poll, interval)
    // Initial poll after a short delay (let existing data load first)
    setTimeout(poll, 2000)
  }

  /** Stop polling */
  function stop(): void {
    if (intervalId) {
      clearInterval(intervalId)
      intervalId = null
    }
    isPolling.value = false
  }

  // Cleanup on unmount
  onUnmounted(stop)

  return {
    isPolling,
    lastError,
    start,
    stop,
    addCameraPlate,
  }
}
