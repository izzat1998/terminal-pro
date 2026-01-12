import { describe, it, expect } from 'vitest'
import {
  getStatusColor,
  getChoiceLabel,
  isLightVehicle,
  isCargoVehicle,
  isCargoLoaded,
  isContainerCargo,
  isContainerCapableTransport,
  getCargoFieldVisibility,
  canExitVehicle,
  canRevertVehicle,
  canCancelVehicle,
  formatDwellTime,
} from './vehicleHelpers'

// ============================================================================
// Status Color Tests
// ============================================================================

describe('getStatusColor', () => {
  it('returns orange for WAITING', () => {
    expect(getStatusColor('WAITING')).toBe('orange')
  })

  it('returns success for ON_TERMINAL', () => {
    expect(getStatusColor('ON_TERMINAL')).toBe('success')
  })

  it('returns blue for EXITED', () => {
    expect(getStatusColor('EXITED')).toBe('blue')
  })

  it('returns red for CANCELLED', () => {
    expect(getStatusColor('CANCELLED')).toBe('red')
  })

  it('returns default for unknown status', () => {
    expect(getStatusColor('UNKNOWN')).toBe('default')
  })
})

// ============================================================================
// Choice Label Tests
// ============================================================================

describe('getChoiceLabel', () => {
  const choices = [
    { value: 'TRUCK', label: 'Фура' },
    { value: 'PLATFORM', label: 'Платформа' },
  ]

  it('returns label for matching value', () => {
    expect(getChoiceLabel(choices, 'TRUCK')).toBe('Фура')
  })

  it('returns dash for null value', () => {
    expect(getChoiceLabel(choices, null)).toBe('—')
  })

  it('returns value itself if not found', () => {
    expect(getChoiceLabel(choices, 'UNKNOWN')).toBe('UNKNOWN')
  })

  it('handles empty choice list', () => {
    expect(getChoiceLabel([], 'TRUCK')).toBe('TRUCK')
  })
})

// ============================================================================
// Vehicle Type Detection Tests
// ============================================================================

describe('vehicle type detection', () => {
  describe('isLightVehicle', () => {
    it('returns true for LIGHT', () => {
      expect(isLightVehicle('LIGHT')).toBe(true)
    })

    it('returns false for CARGO', () => {
      expect(isLightVehicle('CARGO')).toBe(false)
    })

    it('returns false for null', () => {
      expect(isLightVehicle(null)).toBe(false)
    })
  })

  describe('isCargoVehicle', () => {
    it('returns true for CARGO', () => {
      expect(isCargoVehicle('CARGO')).toBe(true)
    })

    it('returns false for LIGHT', () => {
      expect(isCargoVehicle('LIGHT')).toBe(false)
    })
  })
})

// ============================================================================
// Cargo Field Logic Tests (Business Logic - Important!)
// ============================================================================

describe('cargo field logic', () => {
  describe('isCargoLoaded', () => {
    it('returns true for LOADED', () => {
      expect(isCargoLoaded('LOADED')).toBe(true)
    })

    it('returns false for EMPTY', () => {
      expect(isCargoLoaded('EMPTY')).toBe(false)
    })
  })

  describe('isContainerCargo', () => {
    it('returns true for CONTAINER', () => {
      expect(isContainerCargo('CONTAINER')).toBe(true)
    })

    it('returns false for other cargo types', () => {
      expect(isContainerCargo('METAL')).toBe(false)
      expect(isContainerCargo('FOOD')).toBe(false)
    })
  })

  describe('isContainerCapableTransport', () => {
    it('returns true for PLATFORM, TRUCK, TRAILER', () => {
      expect(isContainerCapableTransport('PLATFORM')).toBe(true)
      expect(isContainerCapableTransport('TRUCK')).toBe(true)
      expect(isContainerCapableTransport('TRAILER')).toBe(true)
    })

    it('returns false for GAZELLE, LABO, etc.', () => {
      expect(isContainerCapableTransport('GAZELLE')).toBe(false)
      expect(isContainerCapableTransport('LABO')).toBe(false)
      expect(isContainerCapableTransport('ZIL')).toBe(false)
    })

    it('returns false for null', () => {
      expect(isContainerCapableTransport(null)).toBe(false)
    })
  })
})

// ============================================================================
// Form Field Visibility Tests (Complex Business Logic - Most Valuable!)
// ============================================================================

describe('getCargoFieldVisibility', () => {
  it('shows only visitorType for LIGHT vehicle', () => {
    const result = getCargoFieldVisibility({
      vehicleType: 'LIGHT',
      loadStatus: null,
      cargoType: null,
      transportType: null,
    })

    expect(result.showVisitorType).toBe(true)
    expect(result.showTransportType).toBe(false)
    expect(result.showLoadStatus).toBe(false)
    expect(result.showCargoType).toBe(false)
    expect(result.showContainerFields).toBe(false)
    expect(result.showDestination).toBe(false)
  })

  it('shows transport and load status for CARGO vehicle', () => {
    const result = getCargoFieldVisibility({
      vehicleType: 'CARGO',
      loadStatus: 'EMPTY',
      cargoType: null,
      transportType: 'TRUCK',
    })

    expect(result.showVisitorType).toBe(false)
    expect(result.showTransportType).toBe(true)
    expect(result.showLoadStatus).toBe(true)
    expect(result.showCargoType).toBe(false) // Empty = no cargo type
    expect(result.showDestination).toBe(true)
  })

  it('shows cargo type when CARGO is LOADED', () => {
    const result = getCargoFieldVisibility({
      vehicleType: 'CARGO',
      loadStatus: 'LOADED',
      cargoType: 'METAL',
      transportType: 'TRUCK',
    })

    expect(result.showCargoType).toBe(true)
    expect(result.showContainerFields).toBe(false) // METAL, not CONTAINER
  })

  it('shows container fields only for CONTAINER cargo on capable transport', () => {
    const result = getCargoFieldVisibility({
      vehicleType: 'CARGO',
      loadStatus: 'LOADED',
      cargoType: 'CONTAINER',
      transportType: 'TRUCK', // Can carry containers
    })

    expect(result.showContainerFields).toBe(true)
  })

  it('hides container fields for CONTAINER cargo on incapable transport', () => {
    const result = getCargoFieldVisibility({
      vehicleType: 'CARGO',
      loadStatus: 'LOADED',
      cargoType: 'CONTAINER',
      transportType: 'GAZELLE', // Cannot carry containers
    })

    expect(result.showContainerFields).toBe(false)
  })
})

// ============================================================================
// Action Permission Tests
// ============================================================================

describe('action permissions', () => {
  describe('canExitVehicle', () => {
    it('returns true only for ON_TERMINAL', () => {
      expect(canExitVehicle('ON_TERMINAL')).toBe(true)
      expect(canExitVehicle('WAITING')).toBe(false)
      expect(canExitVehicle('EXITED')).toBe(false)
      expect(canExitVehicle('CANCELLED')).toBe(false)
    })
  })

  describe('canRevertVehicle', () => {
    it('returns true only for EXITED', () => {
      expect(canRevertVehicle('EXITED')).toBe(true)
      expect(canRevertVehicle('ON_TERMINAL')).toBe(false)
      expect(canRevertVehicle('WAITING')).toBe(false)
    })
  })

  describe('canCancelVehicle', () => {
    it('returns true only for WAITING', () => {
      expect(canCancelVehicle('WAITING')).toBe(true)
      expect(canCancelVehicle('ON_TERMINAL')).toBe(false)
      expect(canCancelVehicle('EXITED')).toBe(false)
    })
  })
})

// ============================================================================
// Formatting Tests
// ============================================================================

describe('formatDwellTime', () => {
  it('formats number with one decimal', () => {
    expect(formatDwellTime(2.5)).toBe('2.5')
    expect(formatDwellTime(10)).toBe('10.0')
  })

  it('returns dash for null', () => {
    expect(formatDwellTime(null)).toBe('—')
  })
})
