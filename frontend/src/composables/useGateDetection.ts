/**
 * Gate Detection Composable
 *
 * Handles vehicle detection via plate recognition API
 * and provides mock detection for development testing.
 */

import { ref } from 'vue'
import { http } from '@/utils/httpClient'
import type { VehicleType } from './useVehicleModels'

/** Result from plate recognition API or mock detection */
export interface VehicleDetectionResult {
  plateNumber: string
  vehicleType: VehicleType
  confidence: number
  timestamp: string
  source: 'api' | 'mock'
}

/** API response structure from plate-recognizer endpoint */
interface PlateRecognizerResponse {
  success: boolean
  data: {
    plate_number: string
    vehicle_type: string
    confidence: number
  }
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
 * Generate a random vehicle type with weighted distribution
 * TRUCK: 60%, CAR: 30%, WAGON: 10%
 */
function generateRandomVehicleType(): VehicleType {
  const roll = Math.random()
  if (roll < 0.6) return 'TRUCK'
  if (roll < 0.9) return 'CAR'
  return 'WAGON'
}

/**
 * Map API vehicle type string to VehicleType enum
 */
function mapVehicleType(apiType: string): VehicleType {
  const typeMap: Record<string, VehicleType> = {
    truck: 'TRUCK',
    TRUCK: 'TRUCK',
    car: 'CAR',
    CAR: 'CAR',
    wagon: 'WAGON',
    WAGON: 'WAGON',
  }
  return typeMap[apiType] ?? 'UNKNOWN'
}

/**
 * useGateDetection composable
 *
 * Provides vehicle detection functionality for gate camera integration.
 * Supports both API-based plate recognition and mock detection for testing.
 */
export function useGateDetection() {
  const isDetecting = ref(false)
  const lastResult = ref<VehicleDetectionResult | null>(null)
  const error = ref<string | null>(null)

  /**
   * Detect vehicle from image using plate recognition API
   *
   * @param imageBlob - Image data as Blob (from camera capture or video frame)
   * @returns Detection result or null if detection failed
   */
  async function detectVehicle(imageBlob: Blob): Promise<VehicleDetectionResult | null> {
    isDetecting.value = true
    error.value = null

    const formData = new FormData()
    formData.append('image', imageBlob, 'capture.jpg')

    const response = await http.upload<PlateRecognizerResponse>(
      '/terminal/plate-recognizer/detect-vehicle/',
      formData
    )

    isDetecting.value = false

    if (!response.success || !response.data) {
      error.value = 'Не удалось распознать номер'
      return null
    }

    const result: VehicleDetectionResult = {
      plateNumber: response.data.plate_number,
      vehicleType: mapVehicleType(response.data.vehicle_type),
      confidence: response.data.confidence,
      timestamp: new Date().toISOString(),
      source: 'api',
    }

    lastResult.value = result
    return result
  }

  /**
   * Generate mock detection result for UI testing
   *
   * Useful when API is unavailable or for testing animation flows.
   * Returns fake data with random plate number and vehicle type.
   */
  function useMockDetection(): VehicleDetectionResult {
    const result: VehicleDetectionResult = {
      plateNumber: generateRandomPlate(),
      vehicleType: generateRandomVehicleType(),
      confidence: 0.85 + Math.random() * 0.14, // 85-99% confidence
      timestamp: new Date().toISOString(),
      source: 'mock',
    }

    lastResult.value = result
    return result
  }

  /**
   * Clear any previous error state
   */
  function clearError(): void {
    error.value = null
  }

  /**
   * Reset the composable state
   */
  function reset(): void {
    isDetecting.value = false
    lastResult.value = null
    error.value = null
  }

  return {
    // State
    isDetecting,
    lastResult,
    error,

    // Methods
    detectVehicle,
    useMockDetection,
    clearError,
    reset,
  }
}
