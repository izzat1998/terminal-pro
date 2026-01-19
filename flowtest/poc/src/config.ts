// ============================================================================
// FlowTest Configuration
// ============================================================================
// Central configuration management with environment-based switching between
// simulation and real execution modes.
//
// Environment Variables:
//   VITE_FLOWTEST_MODE    - 'simulation' or 'real' (default: simulation)
//   VITE_BACKEND_URL      - Backend API URL (default: http://localhost:8000/api)
//   VITE_BACKEND_USER     - Backend username (default: admin)
//   VITE_BACKEND_PASSWORD - Backend password (default: admin123)
//   VITE_FRONTEND_URL     - Frontend URL (default: http://localhost:5174)
//   VITE_TELEGRAM_URL     - Telegram Mini App URL (default: http://localhost:5175)
//   VITE_HEADLESS         - Run browsers headless (default: true)
// ============================================================================

import type { ExecutionMode } from './types';
import type { AdapterConfig, SimulationConfig } from './adapters/types';

// ---------------------------------------------------------------------------
// Environment Variable Helpers
// ---------------------------------------------------------------------------

/**
 * Get environment variable with type safety
 * Works in both Vite (browser) and Node environments
 */
function getEnv(key: string, defaultValue: string): string {
  // Vite environment (browser)
  if (typeof import.meta !== 'undefined' && import.meta.env) {
    return (import.meta.env[key] as string) ?? defaultValue;
  }
  // Node environment (for future CLI support)
  if (typeof process !== 'undefined' && process.env) {
    return process.env[key] ?? defaultValue;
  }
  return defaultValue;
}

/**
 * Parse boolean from environment variable
 */
function getBoolEnv(key: string, defaultValue: boolean): boolean {
  const value = getEnv(key, String(defaultValue));
  return value.toLowerCase() === 'true' || value === '1';
}

/**
 * Parse number from environment variable
 */
function getNumberEnv(key: string, defaultValue: number): number {
  const value = getEnv(key, String(defaultValue));
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
}

// ---------------------------------------------------------------------------
// Configuration Values
// ---------------------------------------------------------------------------

/**
 * Current execution mode
 */
export const EXECUTION_MODE: ExecutionMode = getEnv(
  'VITE_FLOWTEST_MODE',
  'simulation'
) as ExecutionMode;

/**
 * Backend API configuration
 */
export const BACKEND_CONFIG = {
  baseUrl: getEnv('VITE_BACKEND_URL', 'http://localhost:8000/api'),
  username: getEnv('VITE_BACKEND_USER', 'admin'),
  password: getEnv('VITE_BACKEND_PASSWORD', 'admin123'),
  timeout: getNumberEnv('VITE_BACKEND_TIMEOUT', 30000),
} as const;

/**
 * Frontend (Vue SPA) configuration
 */
export const FRONTEND_CONFIG = {
  baseUrl: getEnv('VITE_FRONTEND_URL', 'http://localhost:5174'),
  headless: getBoolEnv('VITE_HEADLESS', true),
  slowMo: getNumberEnv('VITE_SLOW_MO', 0),
  screenshotDir: getEnv('VITE_SCREENSHOT_DIR', './screenshots'),
  // Login selectors
  selectors: {
    usernameInput: 'input[placeholder="Имя пользователя"]',
    passwordInput: 'input[placeholder="Пароль"]',
    loginButton: 'button[type="submit"]',
    // 3D scene (matched to actual Vue component classes)
    terminalCanvas: '.terminal-canvas',
    unplacedList: '.unplaced-list-container',
    containerItem: '.container-item',
    placeButton: '.place-btn',
    // Table
    containerTable: '.container-table',
    tableRow: '.ant-table-row',
  },
} as const;

/**
 * Telegram Mini App configuration
 */
export const TELEGRAM_CONFIG = {
  baseUrl: getEnv('VITE_TELEGRAM_URL', 'http://localhost:5175'),
  headless: getBoolEnv('VITE_HEADLESS', true),
  slowMo: getNumberEnv('VITE_SLOW_MO', 0),
  screenshotDir: getEnv('VITE_SCREENSHOT_DIR', './screenshots'),
  // Mobile viewport (iPhone 14 Pro)
  viewport: {
    width: 390,
    height: 844,
  },
  // Telegram-specific selectors (antd-mobile)
  selectors: {
    workOrderCard: '.adm-card',
    completeButton: '.adm-button:has-text("Confirm")',
    pageContainer: '.adm-page',
    pullToRefresh: '.adm-pull-to-refresh',
    taskList: '.work-order-list',
    taskItem: '.work-order-item',
  },
} as const;

/**
 * Database configuration (for direct verification)
 */
export const DATABASE_CONFIG = {
  connectionString: getEnv('VITE_DATABASE_URL', ''),
} as const;

/**
 * Simulation configuration
 */
export const SIMULATION_CONFIG: SimulationConfig = {
  actionDelay: 'random',
  verificationPassRate: 0.95,
  generateDetails: true,
  capturedData: {
    api_create: {
      container1_id: 42,
      container2_id: 43,
      container1_number: 'APLU5544332',
      container2_number: 'TCNU8765432',
    },
    place_container_1: {
      placement1_location: 'A-R01-B02-T1',
    },
    place_container_2: {
      placement2_location: 'A-R01-B03-T1',
    },
  },
};

// ---------------------------------------------------------------------------
// Configuration Builder
// ---------------------------------------------------------------------------

/**
 * Build complete adapter configuration from environment
 */
export function buildAdapterConfig(mode?: ExecutionMode): AdapterConfig {
  return {
    mode: mode ?? EXECUTION_MODE,
    backend: {
      baseUrl: BACKEND_CONFIG.baseUrl,
      username: BACKEND_CONFIG.username,
      password: BACKEND_CONFIG.password,
      timeout: BACKEND_CONFIG.timeout,
    },
    frontend: {
      baseUrl: FRONTEND_CONFIG.baseUrl,
      headless: FRONTEND_CONFIG.headless,
      slowMo: FRONTEND_CONFIG.slowMo,
      screenshotDir: FRONTEND_CONFIG.screenshotDir,
    },
    telegram: {
      baseUrl: TELEGRAM_CONFIG.baseUrl,
      headless: TELEGRAM_CONFIG.headless,
      viewport: TELEGRAM_CONFIG.viewport,
      slowMo: TELEGRAM_CONFIG.slowMo,
      screenshotDir: TELEGRAM_CONFIG.screenshotDir,
    },
    database: {
      connectionString: DATABASE_CONFIG.connectionString,
    },
  };
}

// ---------------------------------------------------------------------------
// Runtime Configuration
// ---------------------------------------------------------------------------

/**
 * Mutable runtime configuration that can be changed without env restart
 */
export interface RuntimeConfig {
  mode: ExecutionMode;
  headless: boolean;
  slowMo: number;
  captureScreenshots: boolean;
  stopOnFirstFailure: boolean;
  maxRetries: number;
  retryDelay: number;
}

/**
 * Default runtime configuration
 */
export const defaultRuntimeConfig: RuntimeConfig = {
  mode: EXECUTION_MODE,
  headless: getBoolEnv('VITE_HEADLESS', true),
  slowMo: getNumberEnv('VITE_SLOW_MO', 0),
  captureScreenshots: true,
  stopOnFirstFailure: true,
  maxRetries: 2,
  retryDelay: 1000,
};

/**
 * Current runtime configuration (can be modified at runtime)
 */
let runtimeConfig: RuntimeConfig = { ...defaultRuntimeConfig };

/**
 * Get current runtime configuration
 */
export function getRuntimeConfig(): Readonly<RuntimeConfig> {
  return runtimeConfig;
}

/**
 * Update runtime configuration
 */
export function updateRuntimeConfig(updates: Partial<RuntimeConfig>): void {
  runtimeConfig = { ...runtimeConfig, ...updates };
}

/**
 * Reset runtime configuration to defaults
 */
export function resetRuntimeConfig(): void {
  runtimeConfig = { ...defaultRuntimeConfig };
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/**
 * Validate configuration for real execution mode
 */
export function validateConfig(): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (EXECUTION_MODE === 'real') {
    // Backend validation
    if (!BACKEND_CONFIG.baseUrl) {
      errors.push('VITE_BACKEND_URL is required for real mode');
    }
    if (!BACKEND_CONFIG.username || !BACKEND_CONFIG.password) {
      errors.push('Backend credentials are required for real mode');
    }

    // Frontend validation
    if (!FRONTEND_CONFIG.baseUrl) {
      errors.push('VITE_FRONTEND_URL is required for real mode');
    }

    // Telegram validation
    if (!TELEGRAM_CONFIG.baseUrl) {
      errors.push('VITE_TELEGRAM_URL is required for real mode');
    }
  }

  return { valid: errors.length === 0, errors };
}

// ---------------------------------------------------------------------------
// Debug Output
// ---------------------------------------------------------------------------

/**
 * Log current configuration (for debugging)
 */
export function logConfig(): void {
  console.group('FlowTest Configuration');
  console.log('Mode:', EXECUTION_MODE);
  console.log('Backend:', {
    url: BACKEND_CONFIG.baseUrl,
    user: BACKEND_CONFIG.username,
    timeout: BACKEND_CONFIG.timeout,
  });
  console.log('Frontend:', {
    url: FRONTEND_CONFIG.baseUrl,
    headless: FRONTEND_CONFIG.headless,
  });
  console.log('Telegram:', {
    url: TELEGRAM_CONFIG.baseUrl,
    headless: TELEGRAM_CONFIG.headless,
    viewport: TELEGRAM_CONFIG.viewport,
  });
  console.log('Runtime:', runtimeConfig);
  console.groupEnd();
}
