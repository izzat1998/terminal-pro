// ============================================================================
// Simulation Adapter
// ============================================================================
// Mock adapter that simulates execution without calling real systems.
// Used for demos, development, and testing the flow structure.
//
// Features:
//   - Configurable delays and success rates
//   - Predefined captured data for specific stages
//   - Realistic-looking action details
//   - Works in browser context (no Node.js dependencies)
// ============================================================================

import type {
  Action,
  ActionResult,
  AdapterContext,
  BackendAction,
  FrontendAction,
  TelegramAction,
  DatabaseAction,
  Verification,
  VerificationResult,
  ResponseVerification,
  UIVerification,
  DatabaseVerification,
  CustomVerification,
  SystemType,
} from '../types';
import type { Adapter, SimulationConfig } from './types';
import { SIMULATION_CONFIG } from '../config';
import { getNestedValue, delay } from './utils';

// ---------------------------------------------------------------------------
// Simulation Adapter Implementation
// ---------------------------------------------------------------------------

export class SimulationAdapter implements Adapter {
  readonly system: SystemType;
  readonly name: string;

  private config: SimulationConfig;
  private ready = false;

  /**
   * Create a simulation adapter for a specific system type.
   * Use createSimulationAdapters() to create all four at once.
   */
  constructor(system: SystemType, config?: Partial<SimulationConfig>) {
    this.system = system;
    this.name = `Simulation (${system})`;
    this.config = { ...SIMULATION_CONFIG, ...config };
  }

  // ---------------------------------------------------------------------------
  // Adapter Interface Implementation
  // ---------------------------------------------------------------------------

  async initialize(context: AdapterContext): Promise<void> {
    context.log('info', `Initializing ${this.name}...`);

    // Simulate initialization delay
    await delay(200 + Math.random() * 300);

    this.ready = true;
    context.log('success', `${this.name} ready (simulation mode)`);
  }

  async executeAction(action: Action, context: AdapterContext): Promise<ActionResult> {
    const startTime = Date.now();

    // Simulate network/processing delay
    const delayMs = this.config.actionDelay === 'random'
      ? 300 + Math.random() * 400
      : this.config.actionDelay;
    await delay(delayMs);

    // Generate realistic result based on action type
    const result = this.simulateAction(action, context);
    const duration = Date.now() - startTime;

    // Log the action
    context.log('info', `  → ${action.description}`, { system: action.type });

    // Handle captured data
    if ('capture' in action && action.capture && result.capturedData) {
      Object.assign(context.captured, result.capturedData);
    }

    return {
      ...result,
      duration,
    };
  }

  async verify(
    verification: Verification,
    context: AdapterContext
  ): Promise<VerificationResult> {
    // Simulate verification delay
    await delay(200 + Math.random() * 300);

    // Use configured pass rate
    const passed = Math.random() <= this.config.verificationPassRate;

    const result = this.simulateVerification(verification, passed, context);

    // Log verification result
    if (passed) {
      context.log('success', `  ✓ ${verification.description}`);
    } else {
      context.log('error', `  ✗ ${verification.description}`);
    }

    return result;
  }

  async screenshot(name: string): Promise<string | null> {
    // Return a simulated screenshot path
    return `/screenshots/${name}-simulated.png`;
  }

  async cleanup(): Promise<void> {
    this.ready = false;
  }

  isReady(): boolean {
    return this.ready;
  }

  // ---------------------------------------------------------------------------
  // Simulation Logic
  // ---------------------------------------------------------------------------

  private simulateAction(
    action: Action,
    context: AdapterContext
  ): Omit<ActionResult, 'duration'> {
    switch (action.type) {
      case 'backend':
        return this.simulateBackendAction(action, context);
      case 'frontend':
        return this.simulateFrontendAction(action, context);
      case 'telegram':
        return this.simulateTelegramAction(action, context);
      case 'database':
        return this.simulateDatabaseAction(action, context);
      default:
        return {
          description: (action as Action).description,
          success: true,
          details: 'Simulated action completed',
        };
    }
  }

  private simulateBackendAction(
    action: BackendAction,
    context: AdapterContext
  ): Omit<ActionResult, 'duration'> {
    // Generate realistic HTTP response details
    let statusCode = 200;
    let details = '';

    switch (action.method) {
      case 'POST':
        statusCode = 201;
        details = `${action.method} ${action.endpoint} → 201 Created`;
        break;
      case 'DELETE':
        statusCode = 204;
        details = `${action.method} ${action.endpoint} → 204 No Content`;
        break;
      default:
        details = `${action.method} ${action.endpoint} → 200 OK`;
    }

    // Generate captured data for specific endpoints
    let capturedData: Record<string, unknown> | undefined;
    if (action.capture) {
      capturedData = this.generateCapturedData(action, context);
    }

    return {
      description: action.description,
      success: true,
      details,
      statusCode,
      capturedData,
    };
  }

  private simulateFrontendAction(
    action: FrontendAction,
    context: AdapterContext
  ): Omit<ActionResult, 'duration'> {
    let details = '';

    switch (action.action) {
      case 'navigate':
        details = `Navigated to ${action.url || action.selector}`;
        break;
      case 'login':
        details = `Authenticated as ${action.credentials?.username || 'admin'}`;
        break;
      case 'click':
        details = `Clicked ${action.selector}`;
        break;
      case 'type':
        details = `Typed into ${action.selector}`;
        break;
      case 'select':
        details = `Selected "${action.value}" in ${action.selector}`;
        break;
      case 'waitForSelector':
        details = `Found ${action.selector}`;
        break;
      case 'screenshot':
        details = `Screenshot captured`;
        break;
      case 'custom':
        details = this.simulateCustomFrontendAction(action, context);
        break;
      default:
        details = 'Action completed';
    }

    let capturedData: Record<string, unknown> | undefined;
    if (action.capture) {
      capturedData = this.generateFrontendCapturedData(action, context);
    }

    return {
      description: action.description,
      success: true,
      details,
      capturedData,
    };
  }

  private simulateTelegramAction(
    action: TelegramAction,
    context: AdapterContext
  ): Omit<ActionResult, 'duration'> {
    let details = '';

    switch (action.action) {
      case 'navigate':
        details = `Navigated to ${action.url || action.selector}`;
        break;
      case 'tap':
        details = `Tapped ${action.selector}`;
        break;
      case 'swipe':
        details = `Swiped ${action.direction || 'up'}`;
        break;
      case 'pullToRefresh':
        details = 'Pull-to-refresh completed';
        break;
      case 'waitForElement':
        details = `Found ${action.selector}`;
        break;
      case 'screenshot':
        details = 'Mobile screenshot captured';
        break;
      case 'custom':
        details = this.simulateCustomTelegramAction(action, context);
        break;
      default:
        details = 'Action completed';
    }

    let capturedData: Record<string, unknown> | undefined;
    if (action.capture) {
      capturedData = this.generateTelegramCapturedData(action, context);
    }

    return {
      description: action.description,
      success: true,
      details,
      capturedData,
    };
  }

  private simulateDatabaseAction(
    action: DatabaseAction,
    _context: AdapterContext
  ): Omit<ActionResult, 'duration'> {
    let details = '';

    switch (action.action) {
      case 'query':
        details = `Queried ${action.table}`;
        break;
      case 'count':
        details = `Counted ${action.table}: 42 rows`;
        break;
      case 'exists':
        details = `Checked existence in ${action.table}: true`;
        break;
      default:
        details = 'Database action completed';
    }

    return {
      description: action.description,
      success: true,
      details,
    };
  }

  private simulateCustomFrontendAction(
    action: FrontendAction,
    _context: AdapterContext
  ): string {
    switch (action.customAction) {
      case 'place3DContainer':
        return `Placed container at position`;
      case 'confirmPlacement':
        return 'Placement confirmed';
      case 'selectUnplacedContainer':
        return `Selected unplaced container`;
      default:
        return `Custom action: ${action.customAction}`;
    }
  }

  private simulateCustomTelegramAction(
    action: TelegramAction,
    _context: AdapterContext
  ): string {
    switch (action.customAction) {
      case 'selectWorkOrder':
        return 'Work order selected';
      case 'completeWorkOrder':
        return 'Work order completed';
      case 'navigateToWorkOrders':
        return 'Navigated to work orders';
      default:
        return `Custom action: ${action.customAction}`;
    }
  }

  // ---------------------------------------------------------------------------
  // Captured Data Generation
  // ---------------------------------------------------------------------------

  private generateCapturedData(
    action: BackendAction,
    context: AdapterContext
  ): Record<string, unknown> {
    if (!action.capture) return {};

    // Use predefined data from config if available
    const stageId = context.currentStage?.id;
    if (stageId && this.config.capturedData?.[stageId]) {
      return { [action.capture]: this.config.capturedData[stageId] };
    }

    // Generate data based on endpoint pattern
    if (action.endpoint.includes('/entries')) {
      return {
        [action.capture]: {
          success: true,
          data: {
            id: Math.floor(40 + Math.random() * 10),
            container_number: action.body?.container_number || 'SIMU1234567',
            status: action.body?.status || 'LADEN',
            created_at: new Date().toISOString(),
          },
        },
      };
    }

    if (action.endpoint.includes('/placement')) {
      return {
        [action.capture]: {
          success: true,
          data: {
            location: `A-R${String(Math.floor(1 + Math.random() * 10)).padStart(2, '0')}-B${String(Math.floor(1 + Math.random() * 5)).padStart(2, '0')}-T1`,
            placed_at: new Date().toISOString(),
          },
        },
      };
    }

    if (action.endpoint.includes('/work-orders')) {
      return {
        [action.capture]: {
          success: true,
          data: {
            id: Math.floor(100 + Math.random() * 100),
            status: 'PENDING',
            created_at: new Date().toISOString(),
          },
        },
      };
    }

    // Default captured data
    return {
      [action.capture]: {
        success: true,
        data: { id: Math.floor(Math.random() * 1000) },
      },
    };
  }

  private generateFrontendCapturedData(
    action: FrontendAction,
    _context: AdapterContext
  ): Record<string, unknown> {
    if (!action.capture) return {};

    if (action.customAction === 'place3DContainer') {
      const pos = action.params?.position as { row: number; bay: number; tier: number } | undefined;
      return {
        [action.capture]: {
          containerNumber: action.params?.containerNumber,
          position: pos,
          location: pos
            ? `A-R${String(pos.row).padStart(2, '0')}-B${String(pos.bay).padStart(2, '0')}-T${pos.tier}`
            : 'A-R01-B02-T1',
        },
      };
    }

    if (action.action === 'screenshot') {
      return {
        [action.capture]: `/screenshots/${action.value || 'screenshot'}-simulated.png`,
      };
    }

    return {};
  }

  private generateTelegramCapturedData(
    action: TelegramAction,
    _context: AdapterContext
  ): Record<string, unknown> {
    if (!action.capture) return {};

    if (action.customAction === 'completeWorkOrder') {
      return {
        [action.capture]: {
          containerNumber: action.params?.containerNumber,
          completedAt: new Date().toISOString(),
          status: 'completed',
        },
      };
    }

    if (action.action === 'screenshot') {
      return {
        [action.capture]: `/screenshots/${action.value || 'telegram'}-mobile-simulated.png`,
      };
    }

    return {};
  }

  // ---------------------------------------------------------------------------
  // Verification Simulation
  // ---------------------------------------------------------------------------

  private simulateVerification(
    verification: Verification,
    passed: boolean,
    context: AdapterContext
  ): VerificationResult {
    switch (verification.type) {
      case 'response':
        return this.simulateResponseVerification(verification, passed, context);
      case 'ui':
        return this.simulateUIVerification(verification, passed);
      case 'database':
        return this.simulateDatabaseVerification(verification, passed);
      case 'custom':
        return this.simulateCustomVerification(verification, passed);
      default:
        return {
          description: (verification as Verification).description,
          passed,
          failureReason: passed ? undefined : 'Verification failed (simulated)',
        };
    }
  }

  private simulateResponseVerification(
    verification: ResponseVerification,
    passed: boolean,
    context: AdapterContext
  ): VerificationResult {
    // Try to get actual value from captured data
    const actual = getNestedValue(context.captured, verification.field);

    return {
      description: verification.description,
      passed,
      actual: actual ?? (passed ? verification.expected : 'undefined'),
      expected: verification.expected,
      failureReason: passed ? undefined : `Field '${verification.field}' check failed`,
    };
  }

  private simulateUIVerification(
    verification: UIVerification,
    passed: boolean
  ): VerificationResult {
    let actual: unknown;

    switch (verification.check) {
      case 'visible':
      case 'exists':
      case 'enabled':
        actual = passed;
        break;
      case 'hidden':
      case 'disabled':
        actual = passed;
        break;
      case 'count':
        actual = passed ? verification.expected : 0;
        break;
      case 'hasText':
        actual = passed ? verification.expected : '';
        break;
      default:
        actual = passed ? 'matches' : 'no match';
    }

    return {
      description: verification.description,
      passed,
      actual,
      expected: verification.expected ?? true,
      failureReason: passed ? undefined : `Element check '${verification.check}' failed`,
    };
  }

  private simulateDatabaseVerification(
    verification: DatabaseVerification,
    passed: boolean
  ): VerificationResult {
    let actual: unknown;

    switch (verification.check) {
      case 'exists':
        actual = passed;
        break;
      case 'notExists':
        actual = !passed;
        break;
      case 'count':
        actual = passed ? verification.expected : 0;
        break;
      case 'fieldEquals':
        actual = passed ? verification.expected : 'different_value';
        break;
      default:
        actual = passed;
    }

    return {
      description: verification.description,
      passed,
      actual,
      expected: verification.expected ?? true,
      failureReason: passed ? undefined : `Database check '${verification.check}' on ${verification.table} failed`,
    };
  }

  private simulateCustomVerification(
    verification: CustomVerification,
    passed: boolean
  ): VerificationResult {
    return {
      description: verification.description,
      passed,
      actual: passed ? 'passed' : 'failed',
      expected: 'passed',
      failureReason: passed ? undefined : `Custom check '${verification.checkName}' failed`,
    };
  }

}

// ---------------------------------------------------------------------------
// Factory Functions
// ---------------------------------------------------------------------------

/**
 * Create a single simulation adapter for a specific system
 */
export function createSimulationAdapter(
  system: SystemType,
  config?: Partial<SimulationConfig>
): SimulationAdapter {
  return new SimulationAdapter(system, config);
}

/**
 * Create all simulation adapters at once
 */
export function createAllSimulationAdapters(
  config?: Partial<SimulationConfig>
): Record<SystemType, SimulationAdapter> {
  return {
    backend: new SimulationAdapter('backend', config),
    frontend: new SimulationAdapter('frontend', config),
    telegram: new SimulationAdapter('telegram', config),
    database: new SimulationAdapter('database', config),
  };
}
