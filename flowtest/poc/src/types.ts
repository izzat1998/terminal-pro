// ============================================================================
// FlowTest Type System
// ============================================================================
// This type system defines executable actions and verifications that can be
// run against real systems (backend API, frontend UI, Telegram mini app) or
// simulated for demo purposes.
// ============================================================================

// ---------------------------------------------------------------------------
// Core Enums
// ---------------------------------------------------------------------------

export type StageStatus = 'pending' | 'running' | 'passed' | 'failed' | 'skipped';

export type SystemType = 'backend' | 'frontend' | 'telegram' | 'database';

export type ExecutionMode = 'simulation' | 'real';

// ---------------------------------------------------------------------------
// Action Types (Discriminated Union)
// ---------------------------------------------------------------------------

/**
 * Backend API action - executes HTTP requests via Axios
 */
export interface BackendAction {
  type: 'backend';
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  endpoint: string;
  body?: Record<string, unknown>;
  headers?: Record<string, string>;
  /** Variable name to store response data (e.g., 'container1') */
  capture?: string;
  description: string;
}

/**
 * Frontend UI action - executes browser automation via Playwright
 */
export interface FrontendAction {
  type: 'frontend';
  action:
    | 'navigate'
    | 'login'
    | 'click'
    | 'type'
    | 'select'
    | 'waitForSelector'
    | 'waitForNetwork'
    | 'screenshot'
    | 'dragAndDrop'
    | 'custom';
  /** Target selector (CSS or data-testid) */
  selector?: string;
  /** URL for navigate action */
  url?: string;
  /** Value for type/select actions */
  value?: string;
  /** Credentials for login action */
  credentials?: { username: string; password: string };
  /** Custom function name for complex interactions */
  customAction?: string;
  /** Parameters for custom action */
  params?: Record<string, unknown>;
  /** Variable name to store captured data */
  capture?: string;
  description: string;
}

/**
 * Telegram Mini App action - executes mobile browser automation
 */
export interface TelegramAction {
  type: 'telegram';
  action:
    | 'navigate'
    | 'tap'
    | 'swipe'
    | 'pullToRefresh'
    | 'waitForElement'
    | 'screenshot'
    | 'fillInput'
    | 'confirmDialog'
    | 'custom';
  /** Target selector */
  selector?: string;
  /** URL for navigate action */
  url?: string;
  /** Value for input actions */
  value?: string;
  /** Swipe direction */
  direction?: 'up' | 'down' | 'left' | 'right';
  /** Custom action name */
  customAction?: string;
  /** Parameters for custom action */
  params?: Record<string, unknown>;
  /** Variable name to store captured data */
  capture?: string;
  description: string;
}

/**
 * Database verification action - executes direct DB queries
 */
export interface DatabaseAction {
  type: 'database';
  action: 'query' | 'count' | 'exists';
  table: string;
  where?: Record<string, unknown>;
  /** SQL query for complex checks */
  rawQuery?: string;
  /** Variable name to store result */
  capture?: string;
  description: string;
}

/**
 * Union type for all possible actions
 */
export type Action = BackendAction | FrontendAction | TelegramAction | DatabaseAction;

// ---------------------------------------------------------------------------
// Verification Types
// ---------------------------------------------------------------------------

export type VerificationOperator =
  | 'exists'
  | 'notExists'
  | 'equals'
  | 'notEquals'
  | 'contains'
  | 'notContains'
  | 'greaterThan'
  | 'lessThan'
  | 'matches' // regex
  | 'hasLength'
  | 'isType';

/**
 * Response verification - checks captured API response data
 */
export interface ResponseVerification {
  type: 'response';
  /** Path to value in captured data (e.g., 'container1.data.id') */
  field: string;
  operator: VerificationOperator;
  expected?: unknown;
  description: string;
}

/**
 * UI verification - checks element state in browser
 */
export interface UIVerification {
  type: 'ui';
  /** CSS selector or data-testid */
  selector: string;
  check:
    | 'visible'
    | 'hidden'
    | 'enabled'
    | 'disabled'
    | 'hasText'
    | 'hasValue'
    | 'hasClass'
    | 'hasAttribute'
    | 'exists'
    | 'count';
  expected?: unknown;
  description: string;
}

/**
 * Database verification - checks database state directly
 */
export interface DatabaseVerification {
  type: 'database';
  table: string;
  where?: Record<string, unknown>;
  check: 'exists' | 'notExists' | 'count' | 'fieldEquals';
  field?: string;
  expected?: unknown;
  description: string;
}

/**
 * Custom verification - runs a custom check function
 */
export interface CustomVerification {
  type: 'custom';
  /** Name of the custom verification function */
  checkName: string;
  params?: Record<string, unknown>;
  description: string;
}

/**
 * Union type for all possible verifications
 */
export type Verification =
  | ResponseVerification
  | UIVerification
  | DatabaseVerification
  | CustomVerification;

// ---------------------------------------------------------------------------
// Stage Definition
// ---------------------------------------------------------------------------

export interface Stage {
  id: string;
  name: string;
  description: string;
  system: SystemType;
  dependsOn: string[];
  actions: Action[];
  verifications: Verification[];
  estimatedDuration: number; // ms
}

// ---------------------------------------------------------------------------
// Execution Results
// ---------------------------------------------------------------------------

export interface ActionResult {
  description: string;
  success: boolean;
  duration: number;
  details?: string;
  /** Captured response data */
  capturedData?: Record<string, unknown>;
  /** HTTP status code for API actions */
  statusCode?: number;
  /** Error message if failed */
  error?: string;
}

export interface VerificationResult {
  description: string;
  passed: boolean;
  actual?: unknown;
  expected?: unknown;
  /** Detailed failure reason */
  failureReason?: string;
}

export interface StageResult {
  id: string;
  status: StageStatus;
  startTime: number | null;
  endTime: number | null;
  actions: ActionResult[];
  verifications: VerificationResult[];
  captured: Record<string, unknown>;
  screenshot: string | null;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

export interface LogEntry {
  timestamp: number;
  level: 'info' | 'success' | 'error' | 'warning';
  message: string;
  stageId?: string;
  /** Additional context data */
  data?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Flow Definition
// ---------------------------------------------------------------------------

export interface FlowDefinition {
  name: string;
  description: string;
  stages: Stage[];
  /** Default execution mode */
  defaultMode?: ExecutionMode;
}

// ---------------------------------------------------------------------------
// Execution State
// ---------------------------------------------------------------------------

export interface ExecutionState {
  status: 'idle' | 'running' | 'passed' | 'failed';
  mode: ExecutionMode;
  currentStage: string | null;
  startTime: number | null;
  endTime: number | null;
  results: Map<string, StageResult>;
  /** Global captured data accessible to all stages */
  captured: Record<string, unknown>;
  logs: LogEntry[];
}

// ---------------------------------------------------------------------------
// Adapter Context
// ---------------------------------------------------------------------------

/**
 * Context passed to adapters during execution
 */
export interface AdapterContext {
  /** Execution mode (simulation or real) */
  mode: ExecutionMode;
  /** Global captured data from previous stages */
  captured: Record<string, unknown>;
  /** Current stage being executed */
  currentStage: Stage;
  /** Logger function */
  log: (level: LogEntry['level'], message: string, data?: Record<string, unknown>) => void;
}

