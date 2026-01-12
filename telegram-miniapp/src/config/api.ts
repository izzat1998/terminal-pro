/**
 * API Configuration
 * Centralized API endpoints and base URL configuration
 */

// Base URL - uses Vite proxy in development, environment variable in production
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

// API Endpoints
export const API_ENDPOINTS = {
  // Vehicle endpoints
  vehicles: {
    statistics: `${API_BASE_URL}/vehicles/statistics/`,
    entries: `${API_BASE_URL}/vehicles/entries/`,
    entry: (id: number) => `${API_BASE_URL}/vehicles/entries/${id}/`,
    choices: `${API_BASE_URL}/vehicles/choices/`,
    destinations: `${API_BASE_URL}/vehicles/destinations/`,
  },

  // Terminal endpoints
  terminal: {
    plateRecognizer: `${API_BASE_URL}/terminal/plate-recognizer/recognize/`,
  },

  // Auth endpoints
  auth: {
    gateAccess: `${API_BASE_URL}/auth/managers/gate_access/`,
  },
} as const;

// Status colors for vehicle entries
export const STATUS_COLORS: Record<string, string> = {
  ON_TERMINAL: '#00b578',
  WAITING: '#ff8f1f',
  EXITED: '#999999',
};

/**
 * Get color for a vehicle status
 */
export function getStatusColor(status: string): string {
  return STATUS_COLORS[status] ?? '#999999';
}

// Vehicle type colors
export const VEHICLE_TYPE_COLORS: Record<string, string> = {
  LIGHT: '#1677ff',
  CARGO: '#722ed1',
};

/**
 * Get color for a vehicle type
 */
export function getVehicleTypeColor(type: string): string {
  return VEHICLE_TYPE_COLORS[type] ?? '#999999';
}
