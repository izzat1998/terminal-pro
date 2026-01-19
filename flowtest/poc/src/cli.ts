#!/usr/bin/env npx tsx
// ============================================================================
// FlowTest CLI Runner
// ============================================================================
// Node.js CLI for running FlowTest flows with real Playwright automation.
// This is the proper way to execute "real mode" tests - not through the browser.
//
// Usage:
//   npx tsx src/cli.ts                    # Run with defaults
//   npx tsx src/cli.ts --headless=false   # Show browsers
//   npx tsx src/cli.ts --mode=simulation  # Force simulation
//
// Environment variables (from .env):
//   VITE_BACKEND_URL, VITE_FRONTEND_URL, VITE_TELEGRAM_URL, etc.
// ============================================================================

// Load .env file for Node.js environment
import { config as dotenvConfig } from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenvConfig({ path: join(__dirname, '..', '.env') });

// Map VITE_ env vars to process.env (they're already there from dotenv)
// The config.ts getEnv function will now find them

import { containerEntryFlow } from './flowDefinition';
import type {
  FlowDefinition,
  Stage,
  ExecutionState,
  StageResult,
  LogEntry,
  ExecutionMode,
  AdapterContext,
} from './types';
import { AdapterRegistryManager } from './adapters';
import { buildAdapterConfig, updateRuntimeConfig, getRuntimeConfig, logConfig } from './config';

// ANSI color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
  bgRed: '\x1b[41m',
  bgGreen: '\x1b[42m',
  bgBlue: '\x1b[44m',
};

const systemColors: Record<string, string> = {
  backend: colors.blue,
  frontend: colors.green,
  telegram: colors.magenta,
  database: colors.yellow,
};

// ---------------------------------------------------------------------------
// CLI Flow Executor
// ---------------------------------------------------------------------------

class CLIFlowExecutor {
  private flow: FlowDefinition;
  private state: ExecutionState;
  private adapters: AdapterRegistryManager | null = null;
  private startTime: number = 0;

  constructor(flow: FlowDefinition) {
    this.flow = flow;
    this.state = this.createInitialState();
  }

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

  private log(level: LogEntry['level'], message: string, stageId?: string): void {
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
    const levelColors = {
      info: colors.cyan,
      success: colors.green,
      error: colors.red,
      warning: colors.yellow,
    };
    const levelSymbols = {
      info: 'ℹ',
      success: '✓',
      error: '✗',
      warning: '⚠',
    };

    const stagePrefix = stageId ? `${colors.dim}[${stageId}]${colors.reset} ` : '';
    console.log(
      `${colors.dim}${timestamp}${colors.reset} ${levelColors[level]}${levelSymbols[level]}${colors.reset} ${stagePrefix}${message}`
    );

    this.state.logs.push({ timestamp: Date.now(), level, message, stageId });
  }

  async execute(): Promise<boolean> {
    this.startTime = Date.now();
    this.state.status = 'running';
    this.state.startTime = this.startTime;
    this.state.mode = getRuntimeConfig().mode;

    console.log('\n' + '='.repeat(70));
    console.log(`${colors.bright}🔄 FlowTest CLI${colors.reset}`);
    console.log('='.repeat(70));
    console.log(`${colors.dim}Flow:${colors.reset} ${this.flow.name}`);
    console.log(`${colors.dim}Mode:${colors.reset} ${this.state.mode.toUpperCase()}`);
    console.log(`${colors.dim}Stages:${colors.reset} ${this.flow.stages.length}`);
    console.log('='.repeat(70) + '\n');

    try {
      // Initialize adapters
      this.adapters = new AdapterRegistryManager(buildAdapterConfig(this.state.mode));
      const initContext = this.createAdapterContext(null);

      this.log('info', 'Initializing adapters...');
      await this.adapters.initialize(initContext);
      this.log('success', 'All adapters ready');

      // Build execution order
      const order = this.buildExecutionOrder();

      // Execute stages
      for (const stage of order) {
        const success = await this.executeStage(stage);
        if (!success && getRuntimeConfig().stopOnFirstFailure) {
          this.state.status = 'failed';
          break;
        }
      }

      if (this.state.status === 'running') {
        this.state.status = 'passed';
      }
    } catch (error) {
      this.state.status = 'failed';
      this.log('error', `Execution error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      if (this.adapters) {
        await this.adapters.cleanup();
      }

      this.state.endTime = Date.now();
      const duration = ((this.state.endTime - this.startTime) / 1000).toFixed(2);

      console.log('\n' + '='.repeat(70));
      if (this.state.status === 'passed') {
        console.log(`${colors.bgGreen}${colors.white} PASSED ${colors.reset} Flow completed successfully in ${duration}s`);
      } else {
        console.log(`${colors.bgRed}${colors.white} FAILED ${colors.reset} Flow failed after ${duration}s`);
      }
      console.log('='.repeat(70) + '\n');

      // Print summary
      this.printSummary();
    }

    return this.state.status === 'passed';
  }

  private async executeStage(stage: Stage): Promise<boolean> {
    this.state.currentStage = stage.id;
    const systemColor = systemColors[stage.system] || colors.white;

    console.log(`\n${colors.bright}▶ ${stage.name}${colors.reset}`);
    console.log(`  ${colors.dim}${stage.description}${colors.reset}`);
    console.log(`  ${systemColor}[${stage.system}]${colors.reset}`);

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

    const adapter = this.adapters!.get(stage.system);
    const context = this.createAdapterContext(stage);

    try {
      // Execute actions
      for (const action of stage.actions) {
        process.stdout.write(`  ${colors.dim}→${colors.reset} ${action.description}...`);

        const actionResult = await adapter.executeAction(action, context);
        result.actions.push(actionResult);

        if (actionResult.capturedData) {
          result.captured = { ...result.captured, ...actionResult.capturedData };
          this.state.captured = { ...this.state.captured, ...actionResult.capturedData };
        }

        if (actionResult.success) {
          console.log(` ${colors.green}✓${colors.reset}${actionResult.details ? ` ${colors.dim}(${actionResult.details})${colors.reset}` : ''}`);
        } else {
          console.log(` ${colors.red}✗${colors.reset} ${actionResult.error}`);
          result.error = actionResult.error ?? 'Action failed';
          break;
        }
      }

      // Run verifications if actions passed
      const actionsFailed = result.actions.some(a => !a.success);

      if (!actionsFailed) {
        for (const verification of stage.verifications) {
          process.stdout.write(`  ${colors.dim}✓${colors.reset} ${verification.description}...`);

          const verifyResult = await adapter.verify(verification, context);
          result.verifications.push(verifyResult);

          if (verifyResult.passed) {
            console.log(` ${colors.green}✓${colors.reset}`);
          } else {
            console.log(` ${colors.red}✗${colors.reset} ${verifyResult.failureReason}`);
          }
        }
      }

      // Determine status
      const hasFailed = result.actions.some(a => !a.success) ||
                        result.verifications.some(v => !v.passed);
      result.status = hasFailed ? 'failed' : 'passed';

    } catch (error) {
      result.status = 'failed';
      result.error = error instanceof Error ? error.message : String(error);
      console.log(`  ${colors.red}✗ Stage error: ${result.error}${colors.reset}`);
    }

    result.endTime = Date.now();
    const duration = ((result.endTime - result.startTime!) / 1000).toFixed(2);

    if (result.status === 'passed') {
      console.log(`  ${colors.green}Stage passed (${duration}s)${colors.reset}`);
    } else {
      console.log(`  ${colors.red}Stage failed (${duration}s)${colors.reset}`);
    }

    return result.status === 'passed';
  }

  private buildExecutionOrder(): Stage[] {
    const visited = new Set<string>();
    const order: Stage[] = [];

    const visit = (stageId: string) => {
      if (visited.has(stageId)) return;
      visited.add(stageId);

      const stage = this.flow.stages.find(s => s.id === stageId);
      if (!stage) return;

      for (const dep of stage.dependsOn) {
        visit(dep);
      }

      order.push(stage);
    };

    for (const stage of this.flow.stages) {
      visit(stage.id);
    }

    return order;
  }

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
      log: (level, message) => {
        this.log(level, message, stage?.id);
      },
    };
  }

  private printSummary(): void {
    console.log(`${colors.bright}Summary:${colors.reset}`);

    let passed = 0;
    let failed = 0;

    for (const stage of this.flow.stages) {
      const result = this.state.results.get(stage.id);
      if (result?.status === 'passed') {
        passed++;
        console.log(`  ${colors.green}✓${colors.reset} ${stage.name}`);
      } else if (result?.status === 'failed') {
        failed++;
        console.log(`  ${colors.red}✗${colors.reset} ${stage.name}${result.error ? `: ${result.error}` : ''}`);
      } else {
        console.log(`  ${colors.dim}○${colors.reset} ${stage.name} (not run)`);
      }
    }

    console.log(`\n  ${colors.green}${passed} passed${colors.reset}, ${colors.red}${failed} failed${colors.reset}`);

    // Print captured data
    if (Object.keys(this.state.captured).length > 0) {
      console.log(`\n${colors.bright}Captured Data:${colors.reset}`);
      for (const [key, value] of Object.entries(this.state.captured)) {
        const valueStr = typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value);
        console.log(`  ${colors.cyan}${key}${colors.reset}: ${colors.dim}${valueStr.substring(0, 100)}${valueStr.length > 100 ? '...' : ''}${colors.reset}`);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// CLI Entry Point
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  // Parse CLI arguments
  const args = process.argv.slice(2);
  let mode: ExecutionMode = 'real';
  let headless = true;

  for (const arg of args) {
    if (arg.startsWith('--mode=')) {
      mode = arg.split('=')[1] as ExecutionMode;
    }
    if (arg.startsWith('--headless=')) {
      headless = arg.split('=')[1] === 'true';
    }
    if (arg === '--help' || arg === '-h') {
      console.log(`
FlowTest CLI Runner

Usage: npx tsx src/cli.ts [options]

Options:
  --mode=<mode>       Execution mode: 'real' or 'simulation' (default: real)
  --headless=<bool>   Run browsers headless: true or false (default: true)
  --help, -h          Show this help message

Environment Variables:
  VITE_BACKEND_URL      Backend API URL (default: http://localhost:8000/api)
  VITE_FRONTEND_URL     Frontend URL (default: http://localhost:5174)
  VITE_TELEGRAM_URL     Telegram Mini App URL (default: http://localhost:5175)
  VITE_BACKEND_USER     Backend username (default: admin)
  VITE_BACKEND_PASSWORD Backend password (default: admin123)

Examples:
  npx tsx src/cli.ts                      # Run real tests with headless browsers
  npx tsx src/cli.ts --headless=false     # Show browser windows
  npx tsx src/cli.ts --mode=simulation    # Run in simulation mode
`);
      process.exit(0);
    }
  }

  // Update runtime config
  updateRuntimeConfig({
    mode,
    headless,
  });

  // Create and run executor
  const executor = new CLIFlowExecutor(containerEntryFlow);
  const success = await executor.execute();

  process.exit(success ? 0 : 1);
}

// Run
main().catch((error) => {
  console.error(`${colors.red}Fatal error:${colors.reset}`, error);
  process.exit(1);
});
