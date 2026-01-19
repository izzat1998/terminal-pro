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

  // Work order endpoints
  workOrders: {
    myOrders: `${API_BASE_URL}/terminal/work-orders/my-orders/`,
    complete: (id: number) => `${API_BASE_URL}/terminal/work-orders/${id}/complete/`,
  },
} as const;

// Color mappings
export const STATUS_COLORS: Record<string, string> = {
  ON_TERMINAL: '#00b578',
  WAITING: '#ff8f1f',
  EXITED: '#999999',
};

export const VEHICLE_TYPE_COLORS: Record<string, string> = {
  LIGHT: '#1677ff',
  CARGO: '#722ed1',
};

export const PRIORITY_COLORS: Record<string, string> = {
  LOW: '#00b578',
  MEDIUM: '#1677ff',
  HIGH: '#ff8f1f',
  URGENT: '#ff3141',
};

const DEFAULT_COLOR = '#999999';

/**
 * Generic color lookup from a color map
 */
function getColorFromMap(colorMap: Record<string, string>, key: string): string {
  return colorMap[key] ?? DEFAULT_COLOR;
}

/**
 * Get color for a vehicle status
 */
export function getStatusColor(status: string): string {
  return getColorFromMap(STATUS_COLORS, status);
}

/**
 * Get color for a vehicle type
 */
export function getVehicleTypeColor(type: string): string {
  return getColorFromMap(VEHICLE_TYPE_COLORS, type);
}

/**
 * Get color for work order priority
 */
export function getPriorityColor(priority: string): string {
  return getColorFromMap(PRIORITY_COLORS, priority);
}
