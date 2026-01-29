/**
 * Exit Detection Composable
 *
 * Handles vehicle exit detection at gate cameras:
 * - Matches detected plates against parked vehicles
 * - Triggers exit animations for matched vehicles
 * - Debounces rapid detections
 * - Provides mock exit for development testing
 */

import { ref, type Ref } from 'vue'
import type { ActiveVehicle } from './useVehicles3D'
import type { VehicleType } from './useVehicleModels'
import { http } from '@/utils/httpClient'

/** Debounce window for same-plate detections (5 seconds) */
const DEBOUNCE_MS = 5000

/** Result from exit detection processing */
export interface ExitDetectionResult {
  plateNumber: string
  vehicleType: VehicleType
  confidence: number
  timestamp: string
  source: 'api' | 'mock'
  /** The matched vehicle from registry, null if unknown */
  matchedVehicle: ActiveVehicle | null
}

/** Options for configuring exit detection */
export interface ExitDetectionOptions {
  /** Reference to the vehicle registry from useVehicles3D */
  vehicleRegistry: Ref<Map<string, ActiveVehicle>>
  /** Callback when a vehicle is matched and will exit */
  onVehicleMatched?: (vehicle: ActiveVehicle, result: ExitDetectionResult) => void
  /** Callback when an unknown vehicle is detected (not in registry) */
  onUnknownVehicle?: (plateNumber: string, result: ExitDetectionResult) => void
}

/** Uzbekistan license plate format: 01A123BC */
const PLATE_LETTERS = 'ABCDEFGHJKLMNOPQRSTUVWXYZ'
const PLATE_REGIONS = ['01', '10', '20', '25', '30', '40', '50', '60', '70', '75', '80', '90', '95']

/**
 * Generate a random Uzbekistan-style license plate number
 */
function generateRandomPlate(): string {
  const region = PLATE_REGIONS[Math.floor(Math.random() * PLATE_REGIONS.length)]
  const letter1 = PLATE_LETTERS[Math.floor(Math.random() * PLATE_LETTERS.length)]
  const digits = String(Math.floor(Math.random() * 1000)).padStart(3, '0')
  const letter2 = PLATE_LETTERS[Math.floor(Math.random() * PLATE_LETTERS.length)]
  const letter3 = PLATE_LETTERS[Math.floor(Math.random() * PLATE_LETTERS.length)]
  return `${region}${letter1}${digits}${letter2}${letter3}`
}

/**
 * useExitDetection composable
 *
 * Provides exit detection functionality for gate camera integration.
 * Matches detected vehicles against the registry and triggers exit sequences.
 */
export function useExitDetection(options: ExitDetectionOptions) {
  const { vehicleRegistry, onVehicleMatched, onUnknownVehicle } = options

  // State
  const isProcessing = ref(false)
  const lastResult = ref<ExitDetectionResult | null>(null)
  const error = ref<string | null>(null)

  // Debounce tracking: plate -> last detection timestamp
  const recentDetections = new Map<string, number>()

  /**
   * Check if a detection should be processed (debounce logic)
   */
  function shouldProcessDetection(plateNumber: string): boolean {
    const now = Date.now()
    const lastSeen = recentDetections.get(plateNumber)

    if (lastSeen && (now - lastSeen) < DEBOUNCE_MS) {
      if (import.meta.env.DEV) {
        console.log(`[useExitDetection] Debounced: ${plateNumber} (${now - lastSeen}ms since last)`)
      }
      return false
    }

    recentDetections.set(plateNumber, now)
    return true
  }

  /**
   * Find a vehicle in the registry by plate number
   * Excludes vehicles already in 'exiting' or 'fading' state
   */
  function matchVehicle(plateNumber: string): ActiveVehicle | null {
    for (const vehicle of vehicleRegistry.value.values()) {
      if (
        vehicle.plateNumber === plateNumber &&
        vehicle.state !== 'exiting' &&
        vehicle.state !== 'fading'
      ) {
        return vehicle
      }
    }
    return null
  }

  /**
   * Process an exit detection event
   *
   * @param plateNumber - Detected license plate
   * @param vehicleType - Detected vehicle type
   * @param confidence - Detection confidence (0-1)
   * @param source - Detection source ('api' or 'mock')
   * @returns The detection result with matched vehicle info
   */
  function processExitDetection(
    plateNumber: string,
    vehicleType: VehicleType,
    confidence: number,
    source: 'api' | 'mock' = 'api'
  ): ExitDetectionResult | null {
    // Check debounce
    if (!shouldProcessDetection(plateNumber)) {
      return null
    }

    isProcessing.value = true

    // Try to match vehicle in registry
    const matchedVehicle = matchVehicle(plateNumber)

    const result: ExitDetectionResult = {
      plateNumber,
      vehicleType,
      confidence,
      timestamp: new Date().toISOString(),
      source,
      matchedVehicle,
    }

    lastResult.value = result

    if (matchedVehicle) {
      if (import.meta.env.DEV) {
        console.log(`[useExitDetection] Matched vehicle: ${plateNumber} in zone ${matchedVehicle.targetZone}`)
      }
      onVehicleMatched?.(matchedVehicle, result)
    } else {
      if (import.meta.env.DEV) {
        console.log(`[useExitDetection] Unknown vehicle: ${plateNumber} (not in registry)`)
      }
      onUnknownVehicle?.(plateNumber, result)
    }

    isProcessing.value = false
    return result
  }

  /**
   * Trigger a mock exit detection for testing
   *
   * Picks a random parked vehicle from the registry and simulates exit detection.
   * If no parked vehicles exist, generates a random unknown vehicle.
   *
   * @returns The mock detection result
   */
  function triggerMockExit(): ExitDetectionResult | null {
    // Find parked vehicles
    const parkedVehicles = Array.from(vehicleRegistry.value.values()).filter(
      (v) => v.state === 'parked'
    )

    let plateNumber: string
    let vehicleType: VehicleType

    if (parkedVehicles.length > 0) {
      // Pick random parked vehicle
      const randomIndex = Math.floor(Math.random() * parkedVehicles.length)
      const randomVehicle = parkedVehicles[randomIndex]!
      plateNumber = randomVehicle.plateNumber
      vehicleType = randomVehicle.vehicleType
    } else {
      // No parked vehicles - generate random unknown vehicle
      plateNumber = generateRandomPlate()
      vehicleType = Math.random() > 0.5 ? 'TRUCK' : 'CAR'
    }

    const confidence = 0.85 + Math.random() * 0.14 // 85-99%

    return processExitDetection(plateNumber, vehicleType, confidence, 'mock')
  }

  /**
   * Notify backend about vehicle exit
   *
   * Non-blocking - errors are logged but don't interrupt the UI flow.
   *
   * @param vehicleId - Backend vehicle ID (if known)
   * @param plateNumber - License plate number
   * @param confidence - Detection confidence
   */
  async function notifyBackendExit(
    vehicleId: string | number | null,
    plateNumber: string,
    confidence: number
  ): Promise<void> {
    try {
      const payload = {
        exit_time: new Date().toISOString(),
        exit_gate: 'main',
        detected_plate: plateNumber,
        confidence,
        source: 'camera',
      }

      if (vehicleId) {
        await http.post(`/terminal/vehicles/${vehicleId}/exit/`, payload)
      } else {
        // Log unknown exit to audit endpoint
        await http.post('/terminal/gate-events/', {
          event_type: 'unknown_exit',
          ...payload,
        })
      }

      if (import.meta.env.DEV) {
        console.log(`[useExitDetection] Backend notified: ${plateNumber}`)
      }
    } catch (err) {
      // Don't throw - backend failure shouldn't block UI
      console.error('[useExitDetection] Failed to notify backend:', err)
      error.value = 'Не удалось уведомить сервер о выезде'
    }
  }

  /**
   * Clear recent detections cache (useful for testing)
   */
  function clearDebounceCache(): void {
    recentDetections.clear()
  }

  /**
   * Reset the composable state
   */
  function reset(): void {
    isProcessing.value = false
    lastResult.value = null
    error.value = null
    recentDetections.clear()
  }

  return {
    // State
    isProcessing,
    lastResult,
    error,

    // Core methods
    processExitDetection,
    matchVehicle,
    triggerMockExit,

    // Backend integration
    notifyBackendExit,

    // Utilities
    clearDebounceCache,
    reset,
  }
}
