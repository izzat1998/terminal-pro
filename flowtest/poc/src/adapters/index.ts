// ============================================================================
// Adapter Registry
// ============================================================================
// Central registry for all adapters. Handles creation and management of
// adapters based on execution mode (simulation vs real).
//
// Usage:
//   import { createAdapterRegistry } from './adapters';
//   const adapters = await createAdapterRegistry(config);
//   const result = await adapters.get('backend').executeAction(action, context);
// ============================================================================

import type { SystemType, ExecutionMode, AdapterContext } from '../types';
import type { Adapter, AdapterConfig } from './types';
import { buildAdapterConfig } from '../config';

// Import adapters (only browser-safe ones statically)
import { SimulationAdapter, createAllSimulationAdapters } from './SimulationAdapter';
import { BackendAdapter } from './BackendAdapter';
// NOTE: FrontendAdapter and TelegramAdapter use Playwright (Node.js only)
// They are dynamically imported only when needed in Node.js environment

// Re-export adapter types and classes
export type { Adapter, AdapterConfig, AdapterRegistry } from './types';
export { SimulationAdapter, createSimulationAdapter, createAllSimulationAdapters } from './SimulationAdapter';
export { BackendAdapter, createBackendAdapter } from './BackendAdapter';
// Playwright adapters are not exported - they're loaded dynamically
export * from './types';
export { getNestedValue, interpolate, interpolateObject, delay } from './utils';

// ---------------------------------------------------------------------------
// Adapter Registry Class
// ---------------------------------------------------------------------------

/**
 * Registry that manages adapters for all system types.
 * Handles initialization, execution delegation, and cleanup.
 */
export class AdapterRegistryManager {
  private adapters: Map<SystemType, Adapter> = new Map();
  private config: AdapterConfig;
  private initialized = false;

  constructor(config?: AdapterConfig) {
    this.config = config ?? buildAdapterConfig();
  }

  /**
   * Get the current execution mode
   */
  get mode(): ExecutionMode {
    return this.config.mode;
  }

  /**
   * Initialize all adapters for the current mode
   */
  async initialize(context: AdapterContext): Promise<void> {
    if (this.initialized) {
      return;
    }

    context.log('info', `Initializing adapters in ${this.config.mode} mode...`);

    if (this.config.mode === 'simulation') {
      // Create simulation adapters (work in browser)
      const simAdapters = createAllSimulationAdapters();
      for (const [system, adapter] of Object.entries(simAdapters)) {
        this.adapters.set(system as SystemType, adapter);
      }
    } else {
      // Create real adapters
      // Note: Backend uses Axios (works in browser), but Frontend/Telegram
      // use Playwright (Node.js only). For browser context, we fall back
      // to simulation for UI adapters.
      this.adapters.set('backend', new BackendAdapter(this.config));
      this.adapters.set('database', new SimulationAdapter('database'));

      // Check if we're in Node.js (Playwright available)
      const isNodeJS = typeof process !== 'undefined' && process.versions?.node;

      if (isNodeJS) {
        // Try to dynamically import Playwright adapters (Node.js only)
        try {
          const [{ FrontendAdapter }, { TelegramAdapter }] = await Promise.all([
            import('./FrontendAdapter'),
            import('./TelegramAdapter'),
          ]);
          this.adapters.set('frontend', new FrontendAdapter(this.config));
          this.adapters.set('telegram', new TelegramAdapter(this.config));
        } catch (err) {
          // Playwright not available - fall back to simulation
          context.log(
            'warning',
            `Playwright import failed: ${err instanceof Error ? err.message : 'unknown error'}`
          );
          this.adapters.set('frontend', new SimulationAdapter('frontend'));
          this.adapters.set('telegram', new SimulationAdapter('telegram'));
        }
      } else {
        // Browser context: use simulation for UI adapters
        context.log(
          'warning',
          'Playwright not available in browser - using simulation for UI adapters'
        );
        this.adapters.set('frontend', new SimulationAdapter('frontend'));
        this.adapters.set('telegram', new SimulationAdapter('telegram'));
      }
    }

    // Initialize all adapters
    for (const adapter of this.adapters.values()) {
      await adapter.initialize(context);
    }

    this.initialized = true;
    context.log('success', `All adapters initialized`);
  }

  /**
   * Get adapter for a specific system type
   */
  get(system: SystemType): Adapter {
    const adapter = this.adapters.get(system);
    if (!adapter) {
      throw new Error(`No adapter registered for system: ${system}`);
    }
    return adapter;
  }

  /**
   * Check if a specific adapter is ready
   */
  isReady(system: SystemType): boolean {
    return this.adapters.get(system)?.isReady() ?? false;
  }

  /**
   * Check if all adapters are ready
   */
  allReady(): boolean {
    for (const adapter of this.adapters.values()) {
      if (!adapter.isReady()) {
        return false;
      }
    }
    return true;
  }

  /**
   * Cleanup all adapters
   */
  async cleanup(): Promise<void> {
    for (const adapter of this.adapters.values()) {
      await adapter.cleanup();
    }
    this.adapters.clear();
    this.initialized = false;
  }

  /**
   * Get all registered adapters
   */
  getAll(): Map<SystemType, Adapter> {
    return new Map(this.adapters);
  }
}

// ---------------------------------------------------------------------------
// Factory Functions
// ---------------------------------------------------------------------------

/**
 * Create an adapter registry with the specified mode
 */
export function createAdapterRegistry(mode?: ExecutionMode): AdapterRegistryManager {
  const config = buildAdapterConfig(mode);
  return new AdapterRegistryManager(config);
}

// ---------------------------------------------------------------------------
// Helper Functions
// ---------------------------------------------------------------------------

/**
 * Type guard to check if an adapter supports screenshots
 */
export function supportsScreenshots(adapter: Adapter): adapter is Adapter & {
  screenshot: (name: string) => Promise<string | null>;
} {
  return typeof adapter.screenshot === 'function';
}
