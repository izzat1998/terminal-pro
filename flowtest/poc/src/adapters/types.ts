// ============================================================================
// Adapter Interface Definitions
// ============================================================================
// Adapters are the bridge between FlowTest and real systems. Each adapter
// implements the same interface but targets a different system:
// - BackendAdapter: Django REST API via Axios
// - FrontendAdapter: Vue SPA via Playwright
// - TelegramAdapter: React Mini App via Playwright (mobile viewport)
// - SimulationAdapter: Mock execution for demos
// ============================================================================

import type {
  Action,
  ActionResult,
  AdapterContext,
  Verification,
  VerificationResult,
  SystemType,
  ExecutionMode,
} from '../types';

// ---------------------------------------------------------------------------
// Core Adapter Interface
// ---------------------------------------------------------------------------

/**
 * Base interface that all adapters must implement.
 *
 * Adapters handle the actual execution of actions and verifications
 * against their target system.
 */
export interface Adapter {
  /** System type this adapter handles */
  readonly system: SystemType;

  /** Human-readable adapter name */
  readonly name: string;

  /**
   * Initialize the adapter (e.g., launch browser, authenticate).
   * Called once before the first action.
   */
  initialize(context: AdapterContext): Promise<void>;

  /**
   * Execute a single action against the target system.
   *
   * @param action - The typed action to execute
   * @param context - Execution context with captured data
   * @returns Result including success status, timing, and captured data
   */
  executeAction(action: Action, context: AdapterContext): Promise<ActionResult>;

  /**
   * Verify a condition against the target system.
   *
   * @param verification - The typed verification to perform
   * @param context - Execution context with captured data
   * @returns Result including pass/fail and actual vs expected values
   */
  verify(verification: Verification, context: AdapterContext): Promise<VerificationResult>;

  /**
   * Capture a screenshot of the current state (UI adapters only).
   * Returns null if screenshots are not supported.
   *
   * @param name - Descriptive name for the screenshot
   * @returns Base64 encoded image or file path, null if not supported
   */
  screenshot?(name: string): Promise<string | null>;

  /**
   * Clean up resources (e.g., close browser, clear tokens).
   * Called after all stages complete or on error.
   */
  cleanup(): Promise<void>;

  /**
   * Check if the adapter is ready to execute actions.
   * Can be used to verify connection/authentication status.
   */
  isReady(): boolean;
}

// ---------------------------------------------------------------------------
// Adapter Factory Types
// ---------------------------------------------------------------------------

/**
 * Configuration for creating adapters
 */
export interface AdapterConfig {
  /** Execution mode determines whether adapters execute real operations */
  mode: ExecutionMode;

  /** Backend API configuration */
  backend?: {
    baseUrl: string;
    username: string;
    password: string;
    /** Timeout for API requests in milliseconds */
    timeout?: number;
  };

  /** Frontend configuration */
  frontend?: {
    baseUrl: string;
    /** Run browser in headless mode */
    headless?: boolean;
    /** Slow down execution for debugging (ms between actions) */
    slowMo?: number;
    /** Directory to save screenshots */
    screenshotDir?: string;
  };

  /** Telegram Mini App configuration */
  telegram?: {
    baseUrl: string;
    /** Run browser in headless mode */
    headless?: boolean;
    /** Mobile viewport dimensions */
    viewport?: { width: number; height: number };
    /** Slow down execution for debugging (ms between actions) */
    slowMo?: number;
    /** Directory to save screenshots */
    screenshotDir?: string;
  };

  /** Database configuration (for direct verification) */
  database?: {
    connectionString: string;
  };
}

/**
 * Factory function type for creating adapters
 */
export type AdapterFactory = (config: AdapterConfig) => Adapter;

// ---------------------------------------------------------------------------
// Adapter Registry Types
// ---------------------------------------------------------------------------

/**
 * Registry mapping system types to their adapters
 */
export interface AdapterRegistry {
  backend: Adapter;
  frontend: Adapter;
  telegram: Adapter;
  database: Adapter;
}

/**
 * Get the appropriate adapter for a given system type
 */
export type AdapterGetter = (system: SystemType) => Adapter;

// ---------------------------------------------------------------------------
// Backend Adapter Specific Types
// ---------------------------------------------------------------------------

/**
 * JWT token pair from authentication
 */
export interface JWTTokens {
  access: string;
  refresh: string;
  /** Timestamp when access token expires */
  accessExpiry?: number;
}

/**
 * API response wrapper (MTT standard format)
 */
export interface APIResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

// ---------------------------------------------------------------------------
// Browser Adapter Specific Types
// ---------------------------------------------------------------------------

/**
 * Browser page state for UI adapters
 */
export interface BrowserState {
  /** Current page URL */
  url: string;
  /** Page title */
  title: string;
  /** Whether user is logged in */
  isAuthenticated: boolean;
}

/**
 * Element interaction options
 */
export interface ElementOptions {
  /** Wait timeout in milliseconds */
  timeout?: number;
  /** Force interaction even if element is covered */
  force?: boolean;
  /** Wait for element to be visible before interacting */
  waitForVisible?: boolean;
}

// ---------------------------------------------------------------------------
// Simulation Adapter Specific Types
// ---------------------------------------------------------------------------

/**
 * Simulation configuration for deterministic test results
 */
export interface SimulationConfig {
  /** Fixed delay between actions (ms), or 'random' for variable delays */
  actionDelay: number | 'random';
  /** Probability of verification passing (0-1) */
  verificationPassRate: number;
  /** Predefined captured data for specific stages */
  capturedData?: Record<string, Record<string, unknown>>;
  /** Whether to generate realistic-looking details */
  generateDetails?: boolean;
}

// ---------------------------------------------------------------------------
// Utility Types
// ---------------------------------------------------------------------------

/**
 * Result of interpolating variables in a string
 */
export interface InterpolationResult {
  /** The string with variables replaced */
  value: string;
  /** Variables that couldn't be resolved */
  missingVariables: string[];
}

/**
 * Deep path accessor result
 */
export interface PathAccessResult {
  /** Whether the path exists in the object */
  found: boolean;
  /** The value at the path, or undefined if not found */
  value: unknown;
}

// ---------------------------------------------------------------------------
// Error Types
// ---------------------------------------------------------------------------

/**
 * Base error for adapter failures
 */
export class AdapterError extends Error {
  constructor(
    message: string,
    public readonly adapter: string,
    public readonly action?: string,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = 'AdapterError';
  }
}

/**
 * Error when authentication fails
 */
export class AuthenticationError extends AdapterError {
  constructor(adapter: string, message: string = 'Authentication failed') {
    super(message, adapter, 'authenticate');
    this.name = 'AuthenticationError';
  }
}

/**
 * Error when a required element is not found
 */
export class ElementNotFoundError extends AdapterError {
  constructor(adapter: string, selector: string) {
    super(`Element not found: ${selector}`, adapter, 'findElement');
    this.name = 'ElementNotFoundError';
  }
}

/**
 * Error when an API request fails
 */
export class APIError extends AdapterError {
  constructor(
    adapter: string,
    public readonly statusCode: number,
    public readonly endpoint: string,
    message: string
  ) {
    super(`API error ${statusCode} on ${endpoint}: ${message}`, adapter, 'apiRequest');
    this.name = 'APIError';
  }
}

/**
 * Error when variable interpolation fails
 */
export class InterpolationError extends AdapterError {
  constructor(adapter: string, variable: string) {
    super(`Failed to interpolate variable: ${variable}`, adapter, 'interpolate');
    this.name = 'InterpolationError';
  }
}
