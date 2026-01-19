// ============================================================================
// Flow Executor
// ============================================================================
// Orchestrates flow execution using the adapter system. Supports both
// simulation and real execution modes.
//
// Key features:
//   - Topological stage ordering via dependency graph
//   - Adapter delegation based on system type
//   - Global captured data accessible to all stages
//   - Stop-on-failure with detailed error reporting
// ============================================================================

import type {
  FlowDefinition,
  Stage,
  StageResult,
  ExecutionState,
  LogEntry,
  ExecutionMode,
  AdapterContext,
} from './types';
import { AdapterRegistryManager, createAdapterRegistry, supportsScreenshots } from './adapters';
import { getRuntimeConfig, updateRuntimeConfig } from './config';

type Listener = (state: ExecutionState) => void;

// ---------------------------------------------------------------------------
// Flow Executor
// ---------------------------------------------------------------------------

export class FlowExecutor {
  private flow: FlowDefinition;
  private state: ExecutionState;
  private listeners: Listener[] = [];
  private aborted = false;
  private adapters: AdapterRegistryManager | null = null;

  constructor(flow: FlowDefinition) {
    this.flow = flow;
    this.state = this.createInitialState();
  }

  // ---------------------------------------------------------------------------
  // State Management
  // ---------------------------------------------------------------------------

  private createInitialState(): ExecutionState {
    return {
      status: 'idle',
      mode: getRuntimeConfig().mode,
      currentStage: null,
      startTime: null,
      endTime: null,
      results: new Map(),
      captured: {},
      logs: [],
    };
  }

  subscribe(listener: Listener): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private emit(): void {
    const stateCopy = { ...this.state };
    this.listeners.forEach(l => l(stateCopy));
  }

  private log(level: LogEntry['level'], message: string, stageId?: string, data?: Record<string, unknown>): void {
    this.state.logs.push({
      timestamp: Date.now(),
      level,
      message,
      stageId,
      data,
    });
    this.emit();
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Reset the executor to initial state
   */
  reset(): void {
    this.aborted = false;
    this.state = this.createInitialState();
    this.emit();
  }

  /**
   * Abort the current execution
   */
  abort(): void {
    this.aborted = true;
    this.log('warning', 'Execution aborted by user');
  }

  /**
   * Set the execution mode
   */
  setMode(mode: ExecutionMode): void {
    updateRuntimeConfig({ mode });
    this.state.mode = mode;
    this.emit();
  }

  /**
   * Get the current execution mode
   */
  getMode(): ExecutionMode {
    return this.state.mode;
  }

  /**
   * Get the current state
   */
  getState(): ExecutionState {
    return this.state;
  }

  /**
   * Execute the flow
   */
  async execute(): Promise<void> {
    this.aborted = false;
    this.state.status = 'running';
    this.state.startTime = Date.now();
    this.state.mode = getRuntimeConfig().mode;

    this.log('info', `Starting flow: ${this.flow.name}`);
    this.log('info', `Mode: ${this.state.mode.toUpperCase()}`);

    // Log initial context
    const containerInfo = this.extractContainerInfo();
    if (containerInfo) {
      this.log('info', `Input: ${containerInfo}`);
    }

    this.emit();

    try {
      // Initialize adapters
      this.adapters = createAdapterRegistry(this.state.mode);
      const adapterContext = this.createAdapterContext(null);
      await this.adapters.initialize(adapterContext);

      // Build execution order (topological sort)
      const order = this.buildExecutionOrder();

      // Execute stages in order
      for (const stage of order) {
        if (this.aborted) {
          this.state.status = 'failed';
          break;
        }

        await this.executeStage(stage);

        // Check if stage failed
        const result = this.state.results.get(stage.id);
        if (result?.status === 'failed') {
          if (getRuntimeConfig().stopOnFirstFailure) {
            this.state.status = 'failed';
            break;
          }
        }
      }

      if (this.state.status === 'running') {
        this.state.status = 'passed';
      }
    } catch (error) {
      this.state.status = 'failed';
      this.log('error', `Execution error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      // Cleanup adapters
      if (this.adapters) {
        await this.adapters.cleanup();
        this.adapters = null;
      }

      this.state.endTime = Date.now();
      this.state.currentStage = null;

      const duration = ((this.state.endTime - this.state.startTime!) / 1000).toFixed(1);
      if (this.state.status === 'passed') {
        this.log('success', `Flow completed successfully in ${duration}s`);
      } else {
        this.log('error', `Flow failed after ${duration}s`);
      }

      this.emit();
    }
  }

  // ---------------------------------------------------------------------------
  // Stage Execution
  // ---------------------------------------------------------------------------

  private async executeStage(stage: Stage): Promise<void> {
    this.state.currentStage = stage.id;

    const result: StageResult = {
      id: stage.id,
      status: 'running',
      startTime: Date.now(),
      endTime: null,
      actions: [],
      verifications: [],
      captured: {},
      screenshot: null,
      error: null,
    };

    this.state.results.set(stage.id, result);
    this.log('info', `Stage "${stage.name}" started`, stage.id);
    this.emit();

    const adapter = this.adapters!.get(stage.system);
    const context = this.createAdapterContext(stage);

    try {
      // Execute all actions
      for (const action of stage.actions) {
        if (this.aborted) break;

        const actionResult = await adapter.executeAction(action, context);
        result.actions.push(actionResult);

        // Update captured data from action
        if (actionResult.capturedData) {
          result.captured = { ...result.captured, ...actionResult.capturedData };
          this.state.captured = { ...this.state.captured, ...actionResult.capturedData };
        }

        // Log action result
        if (actionResult.success) {
          this.log('info', `  → ${action.description}`, stage.id, {
            details: actionResult.details,
          });
        } else {
          this.log('error', `  ✗ ${action.description}: ${actionResult.error}`, stage.id);
        }

        this.emit();

        // Stop if action failed
        if (!actionResult.success) {
          result.error = actionResult.error ?? 'Action failed';
          break;
        }
      }

      // Only run verifications if all actions succeeded
      const actionsFailed = result.actions.some(a => !a.success);

      if (!actionsFailed && !this.aborted) {
        // Execute all verifications
        for (const verification of stage.verifications) {
          if (this.aborted) break;

          const verifyResult = await adapter.verify(verification, context);
          result.verifications.push(verifyResult);

          // Log verification result
          if (verifyResult.passed) {
            this.log('success', `  ✓ ${verification.description}`, stage.id);
          } else {
            this.log('error', `  ✗ ${verification.description}`, stage.id, {
              actual: verifyResult.actual,
              expected: verifyResult.expected,
              reason: verifyResult.failureReason,
            });
          }

          this.emit();
        }
      }

      // Capture screenshot for UI stages
      if ((stage.system === 'frontend' || stage.system === 'telegram') && supportsScreenshots(adapter)) {
        const screenshotPath = await adapter.screenshot(stage.id);
        if (screenshotPath) {
          result.screenshot = screenshotPath;
        }
      }

      // Determine final status
      const hasFailed = result.actions.some(a => !a.success) ||
                        result.verifications.some(v => !v.passed);
      result.status = hasFailed ? 'failed' : 'passed';

    } catch (error) {
      result.status = 'failed';
      result.error = error instanceof Error ? error.message : String(error);
      this.log('error', `Stage error: ${result.error}`, stage.id);
    }

    result.endTime = Date.now();
    const duration = ((result.endTime - result.startTime!) / 1000).toFixed(1);

    if (result.status === 'passed') {
      this.log('success', `Stage "${stage.name}" completed (${duration}s)`, stage.id);
    } else {
      this.log('error', `Stage "${stage.name}" failed (${duration}s)`, stage.id);
    }

    this.emit();
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /**
   * Build execution order using topological sort
   */
  private buildExecutionOrder(): Stage[] {
    const visited = new Set<string>();
    const order: Stage[] = [];

    const visit = (stageId: string) => {
      if (visited.has(stageId)) return;
      visited.add(stageId);

      const stage = this.flow.stages.find(s => s.id === stageId);
      if (!stage) return;

      // Visit dependencies first
      for (const dep of stage.dependsOn) {
        visit(dep);
      }

      order.push(stage);
    };

    // Visit all stages
    for (const stage of this.flow.stages) {
      visit(stage.id);
    }

    return order;
  }

  /**
   * Create adapter context for a stage
   */
  private createAdapterContext(stage: Stage | null): AdapterContext {
    return {
      mode: this.state.mode,
      captured: this.state.captured,
      currentStage: stage ?? ({
        id: '_init',
        name: 'Initialization',
        description: 'Adapter initialization',
        system: 'backend',
        dependsOn: [],
        actions: [],
        verifications: [],
        estimatedDuration: 0,
      } as Stage),
      log: (level, message, data) => {
        this.log(level, message, stage?.id, data);
      },
    };
  }

  /**
   * Extract container info from flow definition for logging
   */
  private extractContainerInfo(): string | null {
    // Look for container numbers in the first stage's actions
    const firstStage = this.flow.stages[0];
    if (!firstStage) return null;

    const containerNumbers: string[] = [];

    for (const action of firstStage.actions) {
      if (action.type === 'backend' && action.body?.container_number) {
        containerNumbers.push(String(action.body.container_number));
      }
    }

    if (containerNumbers.length > 0) {
      return `${containerNumbers.length} container(s) (${containerNumbers.join(', ')})`;
    }

    return null;
  }
}

// ---------------------------------------------------------------------------
// Factory Function
// ---------------------------------------------------------------------------

/**
 * Create a new flow executor
 */
export function createFlowExecutor(flow: FlowDefinition): FlowExecutor {
  return new FlowExecutor(flow);
}
