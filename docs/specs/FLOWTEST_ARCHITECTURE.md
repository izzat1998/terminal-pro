# FlowTest - Business Flow Testing Platform

## MVP Architecture Design

**Version:** 1.0.0
**Date:** 2026-01-18
**Status:** Design Phase

---

## 1. Vision & Goals

### What is FlowTest?

FlowTest is a **Business Flow Testing Platform** that allows you to:
1. Define complex business flows as connected stages
2. Execute real data through the entire flow
3. Watch the data move visually in real-time
4. Verify each stage with assertions
5. Get a complete picture of business process health

### Core Problems Solved

| Problem | Solution |
|---------|----------|
| Tests run in isolation | Tests run as connected flow |
| Can't see data moving through system | Visual real-time flow execution |
| Business flows span multiple systems | Cross-system orchestration |
| Hard to verify end-to-end scenarios | Single flow definition, complete verification |

### Design Principles

1. **Flow-First** - Business flows are first-class citizens
2. **Visual by Default** - Every execution is visualized
3. **Real Data** - No mocks in flow tests (use real systems)
4. **Cross-System** - Orchestrate backend, frontend, mobile seamlessly
5. **Declarative** - Define what, not how

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLOWTEST PLATFORM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        VISUALIZATION LAYER                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │   Flow       │  │   Live       │  │   Results    │              │   │
│  │  │   Designer   │  │   Runner     │  │   Dashboard  │              │   │
│  │  │   (future)   │  │   View       │  │              │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    │ WebSocket                              │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         CORE ENGINE                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │    Flow      │  │   Executor   │  │    State     │              │   │
│  │  │    Parser    │──│    Engine    │──│    Manager   │              │   │
│  │  │              │  │              │  │              │              │   │
│  │  └──────────────┘  └──────┬───────┘  └──────────────┘              │   │
│  └───────────────────────────│──────────────────────────────────────────┘   │
│                              │                                              │
│         ┌────────────────────┼────────────────────┐                        │
│         │                    │                    │                        │
│         ▼                    ▼                    ▼                        │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│  │   Backend    │     │   Frontend   │     │   Telegram   │               │
│  │   Adapter    │     │   Adapter    │     │   Adapter    │               │
│  │              │     │              │     │              │               │
│  │  - API calls │     │  - Playwright│     │  - Playwright│               │
│  │  - DB verify │     │  - Screenshots│    │  - Screenshots│              │
│  │  - Django ORM│     │  - Assertions│     │  - Assertions│               │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘               │
│         │                    │                    │                        │
└─────────│────────────────────│────────────────────│────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
   │   Backend    │     │     Vue      │     │    React     │
   │   Django     │     │   Frontend   │     │  Telegram    │
   │   :8000      │     │   :5174      │     │  Mini App    │
   └──────────────┘     └──────────────┘     │   :5175      │
                                             └──────────────┘
```

---

## 3. Flow Definition DSL

### 3.1 Schema Overview

```typescript
// flowtest/types/flow.ts

interface FlowDefinition {
  name: string;
  description?: string;
  version: string;

  // Input data for the flow
  input: {
    [key: string]: InputDefinition;
  };

  // Stages in execution order (with dependencies)
  stages: Stage[];

  // Global settings
  settings?: {
    timeout?: number;        // Overall flow timeout (ms)
    stopOnFailure?: boolean; // Stop at first failure
    parallel?: boolean;      // Run independent stages in parallel
  };
}

interface InputDefinition {
  type: 'number' | 'string' | 'array' | 'object';
  default?: any;
  description?: string;
}

interface Stage {
  id: string;
  name: string;
  description?: string;

  // Which system executes this stage
  system: 'backend' | 'frontend' | 'telegram' | 'database';

  // Dependencies (stage IDs that must complete first)
  dependsOn?: string[];

  // Actions to perform
  actions: Action[];

  // Assertions to verify
  verify: Assertion[];

  // Data to capture for later stages
  capture?: CaptureDefinition[];

  // Take screenshot after stage
  screenshot?: boolean;

  // Stage-specific timeout
  timeout?: number;
}

interface Action {
  type: 'api' | 'navigate' | 'click' | 'fill' | 'wait' | 'evaluate';
  // Action-specific properties
  [key: string]: any;
}

interface Assertion {
  type: 'equals' | 'contains' | 'exists' | 'count' | 'custom';
  target: string;      // What to check (supports template syntax)
  expected?: any;      // Expected value
  message?: string;    // Custom failure message
}

interface CaptureDefinition {
  name: string;        // Variable name for later use
  source: string;      // Where to get the value (supports JSONPath)
}
```

### 3.2 Example Flow Definition

```yaml
# flowtest/flows/container-entry-to-confirmation.flow.yaml

name: "Container Entry to Confirmation"
description: "Complete flow from container entry to vehicle manager confirmation"
version: "1.0.0"

input:
  containerCount:
    type: number
    default: 2
    description: "Number of containers to process"

  containerNumbers:
    type: array
    default: ["APLU5544332", "TCNU8765432"]
    description: "Container numbers to use"

settings:
  timeout: 120000  # 2 minutes
  stopOnFailure: true
  parallel: false

stages:
  # ═══════════════════════════════════════════════════════════════
  # STAGE 1: Backend - Create containers via API
  # ═══════════════════════════════════════════════════════════════
  - id: api_create_containers
    name: "Create Containers via API"
    description: "POST containers to backend API"
    system: backend

    actions:
      - type: api
        method: POST
        endpoint: /api/containers/
        auth: admin
        body:
          container_number: "{{ input.containerNumbers[0] }}"
          container_type: "42G1"
          status: "laden"

      - type: api
        method: POST
        endpoint: /api/containers/
        auth: admin
        body:
          container_number: "{{ input.containerNumbers[1] }}"
          container_type: "22G1"
          status: "empty"

    verify:
      - type: equals
        target: "responses[0].status"
        expected: 201
        message: "First container should be created"

      - type: equals
        target: "responses[1].status"
        expected: 201
        message: "Second container should be created"

      - type: custom
        target: "database"
        query: "SELECT COUNT(*) FROM containers WHERE container_number IN ('APLU5544332', 'TCNU8765432')"
        expected: 2
        message: "Both containers should exist in database"

    capture:
      - name: container1_id
        source: "responses[0].data.id"
      - name: container2_id
        source: "responses[1].data.id"

    screenshot: false

  # ═══════════════════════════════════════════════════════════════
  # STAGE 2: Frontend - Verify containers appear in 3D view
  # ═══════════════════════════════════════════════════════════════
  - id: frontend_3d_view
    name: "Containers Visible in 3D Map"
    description: "Verify containers render in the 3D terminal view"
    system: frontend
    dependsOn: [api_create_containers]

    actions:
      - type: navigate
        url: /3d-yard
        waitFor: ".terminal-3d-canvas"

      - type: wait
        for: "networkIdle"
        timeout: 5000

    verify:
      - type: exists
        target: "[data-container-id='{{ container1_id }}']"
        message: "Container 1 should be visible in 3D view"

      - type: exists
        target: "[data-container-id='{{ container2_id }}']"
        message: "Container 2 should be visible in 3D view"

      - type: custom
        target: "evaluate"
        script: "window.__3DScene__.getUnplacedContainers().length"
        expected: 2
        message: "Should have 2 unplaced containers"

    screenshot: true

  # ═══════════════════════════════════════════════════════════════
  # STAGE 3: Frontend - Manager places first container
  # ═══════════════════════════════════════════════════════════════
  - id: frontend_place_container1
    name: "Manager Places Container 1"
    description: "Simulate manager placing first container"
    system: frontend
    dependsOn: [frontend_3d_view]

    actions:
      - type: click
        selector: "[data-container-id='{{ container1_id }}']"

      - type: wait
        for: ".placement-panel"

      - type: click
        selector: "[data-slot='A-R01-B02-T1']"

      - type: click
        selector: "button:has-text('Confirm Placement')"

      - type: wait
        for: "networkIdle"

    verify:
      - type: custom
        target: "api"
        method: GET
        endpoint: "/api/containers/{{ container1_id }}/"
        check: "response.data.location == 'A-R01-B02-T1'"
        message: "Container 1 should be placed at A-R01-B02-T1"

    capture:
      - name: placement1_id
        source: "lastApiResponse.data.placement_id"

    screenshot: true

  # ═══════════════════════════════════════════════════════════════
  # STAGE 4: Frontend - Manager places second container
  # ═══════════════════════════════════════════════════════════════
  - id: frontend_place_container2
    name: "Manager Places Container 2"
    description: "Simulate manager placing second container"
    system: frontend
    dependsOn: [frontend_place_container1]

    actions:
      - type: click
        selector: "[data-container-id='{{ container2_id }}']"

      - type: click
        selector: "[data-slot='A-R01-B03-T1']"

      - type: click
        selector: "button:has-text('Confirm Placement')"

      - type: wait
        for: "networkIdle"

    verify:
      - type: custom
        target: "api"
        method: GET
        endpoint: "/api/containers/{{ container2_id }}/"
        check: "response.data.location == 'A-R01-B03-T1'"
        message: "Container 2 should be placed at A-R01-B03-T1"

    capture:
      - name: placement2_id
        source: "lastApiResponse.data.placement_id"

    screenshot: true

  # ═══════════════════════════════════════════════════════════════
  # STAGE 5: Telegram - Work orders appear
  # ═══════════════════════════════════════════════════════════════
  - id: telegram_work_orders
    name: "Work Orders in Telegram"
    description: "Verify work orders appear in Telegram Mini App"
    system: telegram
    dependsOn: [frontend_place_container2]

    actions:
      - type: navigate
        url: /work-orders
        waitFor: ".work-order-list"

    verify:
      - type: count
        target: ".work-order-item"
        expected: 2
        message: "Should have 2 work orders"

      - type: contains
        target: ".work-order-item"
        expected: "APLU5544332"
        message: "Work order for container 1 should exist"

      - type: contains
        target: ".work-order-item"
        expected: "TCNU8765432"
        message: "Work order for container 2 should exist"

    screenshot: true

  # ═══════════════════════════════════════════════════════════════
  # STAGE 6: Telegram - Vehicle manager confirms
  # ═══════════════════════════════════════════════════════════════
  - id: telegram_confirm
    name: "Vehicle Manager Confirms"
    description: "Vehicle manager confirms both placements"
    system: telegram
    dependsOn: [telegram_work_orders]

    actions:
      # Confirm first work order
      - type: click
        selector: ".work-order-item:has-text('APLU5544332')"

      - type: click
        selector: "button:has-text('Confirm')"

      - type: wait
        for: "networkIdle"

      # Confirm second work order
      - type: click
        selector: ".work-order-item:has-text('TCNU8765432')"

      - type: click
        selector: "button:has-text('Confirm')"

      - type: wait
        for: "networkIdle"

    verify:
      - type: count
        target: ".work-order-item[data-status='completed']"
        expected: 2
        message: "Both work orders should be completed"

    screenshot: true

  # ═══════════════════════════════════════════════════════════════
  # STAGE 7: Final Verification
  # ═══════════════════════════════════════════════════════════════
  - id: final_verification
    name: "Final State Verification"
    description: "Verify complete end state across all systems"
    system: backend
    dependsOn: [telegram_confirm]

    actions:
      - type: api
        method: GET
        endpoint: /api/containers/{{ container1_id }}/

      - type: api
        method: GET
        endpoint: /api/containers/{{ container2_id }}/

    verify:
      # Container 1 final state
      - type: equals
        target: "responses[0].data.status"
        expected: "placed"
        message: "Container 1 should have status 'placed'"

      - type: equals
        target: "responses[0].data.location"
        expected: "A-R01-B02-T1"
        message: "Container 1 should be at correct location"

      # Container 2 final state
      - type: equals
        target: "responses[1].data.status"
        expected: "placed"
        message: "Container 2 should have status 'placed'"

      - type: equals
        target: "responses[1].data.location"
        expected: "A-R01-B03-T1"
        message: "Container 2 should be at correct location"

      # Database verification
      - type: custom
        target: "database"
        query: |
          SELECT COUNT(*) FROM work_orders
          WHERE status = 'completed'
          AND container_id IN ({{ container1_id }}, {{ container2_id }})
        expected: 2
        message: "Both work orders should be completed in database"

    screenshot: false
```

---

## 4. Executor Engine

### 4.1 Core Components

```typescript
// flowtest/engine/FlowExecutor.ts

import { EventEmitter } from 'events';
import { FlowDefinition, Stage, ExecutionState, StageResult } from '../types';
import { BackendAdapter } from '../adapters/BackendAdapter';
import { FrontendAdapter } from '../adapters/FrontendAdapter';
import { TelegramAdapter } from '../adapters/TelegramAdapter';

export class FlowExecutor extends EventEmitter {
  private flow: FlowDefinition;
  private state: ExecutionState;
  private adapters: Map<string, SystemAdapter>;

  constructor(flow: FlowDefinition) {
    super();
    this.flow = flow;
    this.state = this.initializeState();
    this.adapters = new Map([
      ['backend', new BackendAdapter()],
      ['frontend', new FrontendAdapter()],
      ['telegram', new TelegramAdapter()],
    ]);
  }

  private initializeState(): ExecutionState {
    return {
      flowId: crypto.randomUUID(),
      status: 'pending',
      startTime: null,
      endTime: null,
      input: {},
      captured: {},           // Data captured from stages
      stages: new Map(),      // Stage ID -> StageResult
      currentStage: null,
      errors: [],
    };
  }

  async execute(input?: Record<string, any>): Promise<ExecutionResult> {
    this.state.input = { ...this.getDefaults(), ...input };
    this.state.status = 'running';
    this.state.startTime = Date.now();

    this.emit('flow:start', { flowId: this.state.flowId, flow: this.flow });

    try {
      // Build execution order from dependencies
      const executionOrder = this.buildExecutionOrder();

      for (const stage of executionOrder) {
        await this.executeStage(stage);

        // Check if we should stop
        if (this.state.status === 'failed' && this.flow.settings?.stopOnFailure) {
          break;
        }
      }

      this.state.status = this.hasFailures() ? 'failed' : 'passed';

    } catch (error) {
      this.state.status = 'error';
      this.state.errors.push(error as Error);
    }

    this.state.endTime = Date.now();
    this.emit('flow:complete', this.getResult());

    return this.getResult();
  }

  private async executeStage(stage: Stage): Promise<void> {
    this.state.currentStage = stage.id;

    const stageResult: StageResult = {
      id: stage.id,
      name: stage.name,
      status: 'running',
      startTime: Date.now(),
      endTime: null,
      actions: [],
      verifications: [],
      captured: {},
      screenshot: null,
      error: null,
    };

    this.state.stages.set(stage.id, stageResult);
    this.emit('stage:start', { stageId: stage.id, stage });

    try {
      const adapter = this.adapters.get(stage.system);
      if (!adapter) {
        throw new Error(`Unknown system: ${stage.system}`);
      }

      // Execute actions
      for (const action of stage.actions) {
        const resolvedAction = this.resolveTemplates(action);
        const actionResult = await adapter.executeAction(resolvedAction);
        stageResult.actions.push(actionResult);

        this.emit('action:complete', {
          stageId: stage.id,
          action: resolvedAction,
          result: actionResult
        });
      }

      // Run verifications
      for (const verification of stage.verify) {
        const resolvedVerification = this.resolveTemplates(verification);
        const verifyResult = await adapter.verify(resolvedVerification, stageResult);
        stageResult.verifications.push(verifyResult);

        this.emit('verify:complete', {
          stageId: stage.id,
          verification: resolvedVerification,
          result: verifyResult,
        });
      }

      // Capture data
      if (stage.capture) {
        for (const capture of stage.capture) {
          const value = this.extractValue(capture.source, stageResult);
          stageResult.captured[capture.name] = value;
          this.state.captured[capture.name] = value;
        }
      }

      // Take screenshot if requested
      if (stage.screenshot && adapter.canScreenshot()) {
        stageResult.screenshot = await adapter.screenshot();
        this.emit('screenshot', { stageId: stage.id, path: stageResult.screenshot });
      }

      // Determine stage status
      const hasFailedVerifications = stageResult.verifications.some(v => !v.passed);
      stageResult.status = hasFailedVerifications ? 'failed' : 'passed';

    } catch (error) {
      stageResult.status = 'error';
      stageResult.error = error as Error;
    }

    stageResult.endTime = Date.now();
    this.emit('stage:complete', { stageId: stage.id, result: stageResult });
  }

  private buildExecutionOrder(): Stage[] {
    // Topological sort based on dependencies
    const visited = new Set<string>();
    const order: Stage[] = [];

    const visit = (stageId: string) => {
      if (visited.has(stageId)) return;
      visited.add(stageId);

      const stage = this.flow.stages.find(s => s.id === stageId);
      if (!stage) throw new Error(`Stage not found: ${stageId}`);

      for (const dep of stage.dependsOn || []) {
        visit(dep);
      }

      order.push(stage);
    };

    for (const stage of this.flow.stages) {
      visit(stage.id);
    }

    return order;
  }

  private resolveTemplates(obj: any): any {
    // Replace {{ variable }} with actual values
    const json = JSON.stringify(obj);
    const resolved = json.replace(/\{\{\s*([^}]+)\s*\}\}/g, (_, path) => {
      return this.resolvePath(path.trim());
    });
    return JSON.parse(resolved);
  }

  private resolvePath(path: string): any {
    // Handle input.*, captured.*, etc.
    const parts = path.split('.');
    let value: any = null;

    if (parts[0] === 'input') {
      value = this.state.input;
      parts.shift();
    } else if (parts[0] === 'captured' || this.state.captured[parts[0]]) {
      value = this.state.captured;
      if (parts[0] !== 'captured') {
        // Direct captured variable access
        return this.state.captured[parts[0]];
      }
      parts.shift();
    }

    for (const part of parts) {
      // Handle array access: [0], [1], etc.
      const arrayMatch = part.match(/^(\w+)\[(\d+)\]$/);
      if (arrayMatch) {
        value = value[arrayMatch[1]][parseInt(arrayMatch[2])];
      } else {
        value = value[part];
      }
    }

    return value;
  }
}
```

### 4.2 System Adapters

```typescript
// flowtest/adapters/types.ts

export interface SystemAdapter {
  initialize(): Promise<void>;
  cleanup(): Promise<void>;
  executeAction(action: Action): Promise<ActionResult>;
  verify(assertion: Assertion, stageResult: StageResult): Promise<VerificationResult>;
  canScreenshot(): boolean;
  screenshot(): Promise<string>;
}

// flowtest/adapters/BackendAdapter.ts

import axios, { AxiosInstance } from 'axios';
import { SystemAdapter, Action, ActionResult, Assertion, VerificationResult } from './types';

export class BackendAdapter implements SystemAdapter {
  private client: AxiosInstance;
  private tokens: Map<string, string> = new Map();

  constructor() {
    this.client = axios.create({
      baseURL: process.env.BACKEND_URL || 'http://localhost:8000',
    });
  }

  async initialize(): Promise<void> {
    // Login as admin and cache token
    const response = await this.client.post('/api/auth/login/', {
      login: 'admin',
      password: 'admin123',
    });
    this.tokens.set('admin', response.data.access);
  }

  async executeAction(action: Action): Promise<ActionResult> {
    if (action.type !== 'api') {
      throw new Error(`Backend adapter only supports 'api' actions, got: ${action.type}`);
    }

    const headers: Record<string, string> = {};
    if (action.auth && this.tokens.has(action.auth)) {
      headers['Authorization'] = `Bearer ${this.tokens.get(action.auth)}`;
    }

    const response = await this.client.request({
      method: action.method,
      url: action.endpoint,
      data: action.body,
      headers,
    });

    return {
      type: 'api',
      success: true,
      status: response.status,
      data: response.data,
      duration: 0, // Would need timing
    };
  }

  async verify(assertion: Assertion, stageResult: StageResult): Promise<VerificationResult> {
    // Implementation for different assertion types
    switch (assertion.type) {
      case 'equals':
        const actual = this.extractValue(assertion.target, stageResult);
        return {
          passed: actual === assertion.expected,
          message: assertion.message || `Expected ${assertion.expected}, got ${actual}`,
          actual,
          expected: assertion.expected,
        };

      case 'custom':
        if (assertion.target === 'database') {
          // Run raw SQL query via management endpoint
          const result = await this.client.post('/api/debug/query/', {
            sql: assertion.query,
          });
          return {
            passed: result.data.result === assertion.expected,
            message: assertion.message,
            actual: result.data.result,
            expected: assertion.expected,
          };
        }
        break;
    }

    return { passed: false, message: 'Unknown assertion type' };
  }

  canScreenshot(): boolean {
    return false;
  }

  async screenshot(): Promise<string> {
    throw new Error('Backend adapter cannot take screenshots');
  }
}

// flowtest/adapters/FrontendAdapter.ts

import { chromium, Browser, Page } from 'playwright';
import { SystemAdapter, Action, ActionResult, Assertion, VerificationResult } from './types';

export class FrontendAdapter implements SystemAdapter {
  private browser: Browser | null = null;
  private page: Page | null = null;

  async initialize(): Promise<void> {
    this.browser = await chromium.launch({ headless: true });
    const context = await this.browser.newContext();
    this.page = await context.newPage();

    // Login
    await this.page.goto(process.env.FRONTEND_URL || 'http://localhost:5174');
    await this.page.fill('input[type="text"]', 'admin');
    await this.page.fill('input[type="password"]', 'admin123');
    await this.page.click('button[type="submit"]');
    await this.page.waitForNavigation();
  }

  async cleanup(): Promise<void> {
    await this.browser?.close();
  }

  async executeAction(action: Action): Promise<ActionResult> {
    if (!this.page) throw new Error('Page not initialized');

    switch (action.type) {
      case 'navigate':
        await this.page.goto(action.url);
        if (action.waitFor) {
          await this.page.waitForSelector(action.waitFor);
        }
        return { type: 'navigate', success: true };

      case 'click':
        await this.page.click(action.selector);
        return { type: 'click', success: true, selector: action.selector };

      case 'fill':
        await this.page.fill(action.selector, action.value);
        return { type: 'fill', success: true, selector: action.selector };

      case 'wait':
        if (action.for === 'networkIdle') {
          await this.page.waitForLoadState('networkidle');
        } else {
          await this.page.waitForSelector(action.for, { timeout: action.timeout });
        }
        return { type: 'wait', success: true };

      case 'evaluate':
        const result = await this.page.evaluate(action.script);
        return { type: 'evaluate', success: true, result };

      default:
        throw new Error(`Unknown action type: ${action.type}`);
    }
  }

  async verify(assertion: Assertion, stageResult: StageResult): Promise<VerificationResult> {
    if (!this.page) throw new Error('Page not initialized');

    switch (assertion.type) {
      case 'exists':
        const exists = await this.page.locator(assertion.target).count() > 0;
        return {
          passed: exists,
          message: assertion.message || `Element ${assertion.target} should exist`,
        };

      case 'count':
        const count = await this.page.locator(assertion.target).count();
        return {
          passed: count === assertion.expected,
          message: assertion.message,
          actual: count,
          expected: assertion.expected,
        };

      case 'contains':
        const text = await this.page.locator(assertion.target).textContent();
        return {
          passed: text?.includes(assertion.expected) || false,
          message: assertion.message,
          actual: text,
          expected: assertion.expected,
        };

      case 'custom':
        if (assertion.target === 'evaluate') {
          const result = await this.page.evaluate(assertion.script);
          return {
            passed: result === assertion.expected,
            message: assertion.message,
            actual: result,
            expected: assertion.expected,
          };
        }
        break;
    }

    return { passed: false, message: 'Unknown assertion type' };
  }

  canScreenshot(): boolean {
    return true;
  }

  async screenshot(): Promise<string> {
    if (!this.page) throw new Error('Page not initialized');
    const path = `/tmp/flowtest-${Date.now()}.png`;
    await this.page.screenshot({ path, fullPage: true });
    return path;
  }
}

// flowtest/adapters/TelegramAdapter.ts
// Similar to FrontendAdapter but targets localhost:5175
```

---

## 5. Visualization UI

### 5.1 Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FLOWTEST UI                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Header                                 │  │
│  │  [Flow: Container Entry to Confirmation] [▶ Run] [⟳ Reset]│  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────┐  ┌────────────────────────────────┐  │
│  │                     │  │                                 │  │
│  │    Flow Graph       │  │      Stage Details              │  │
│  │                     │  │                                 │  │
│  │   [API Entry]       │  │  Stage: Create Containers       │  │
│  │       │             │  │  Status: ✅ Passed               │  │
│  │       ▼             │  │  Duration: 1.2s                 │  │
│  │   [3D Map]          │  │                                 │  │
│  │       │             │  │  Actions:                       │  │
│  │       ▼             │  │  ├─ POST /api/containers/ ✅    │  │
│  │   [Placement 1]     │  │  └─ POST /api/containers/ ✅    │  │
│  │       │             │  │                                 │  │
│  │       ▼             │  │  Verifications:                 │  │
│  │   [Placement 2]     │  │  ├─ Status 201 ✅               │  │
│  │       │             │  │  └─ DB count = 2 ✅             │  │
│  │       ▼             │  │                                 │  │
│  │   [Telegram]        │  │  Captured:                      │  │
│  │       │             │  │  ├─ container1_id: 42           │  │
│  │       ▼             │  │  └─ container2_id: 43           │  │
│  │   [Confirm]         │  │                                 │  │
│  │       │             │  │  ┌─────────────────────────┐   │  │
│  │       ▼             │  │  │     [Screenshot]        │   │  │
│  │   [✅ Final]        │  │  │                         │   │  │
│  │                     │  │  └─────────────────────────┘   │  │
│  └─────────────────────┘  └────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Progress Bar                           │  │
│  │  ████████████░░░░░░░░  5/7 stages  │  Elapsed: 12.4s     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Live Log                               │  │
│  │  [12:34:01] Stage api_create_containers started           │  │
│  │  [12:34:02] POST /api/containers/ → 201                   │  │
│  │  [12:34:02] POST /api/containers/ → 201                   │  │
│  │  [12:34:02] ✅ All verifications passed                   │  │
│  │  [12:34:03] Stage frontend_3d_view started                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 React Components

```typescript
// flowtest/ui/src/components/FlowGraph.tsx

import React from 'react';
import ReactFlow, { Node, Edge } from 'reactflow';
import { FlowDefinition, ExecutionState, StageStatus } from '../types';

interface FlowGraphProps {
  flow: FlowDefinition;
  executionState: ExecutionState;
  onStageClick: (stageId: string) => void;
}

export function FlowGraph({ flow, executionState, onStageClick }: FlowGraphProps) {
  const nodes: Node[] = flow.stages.map((stage, index) => ({
    id: stage.id,
    position: { x: 100, y: index * 120 },
    data: {
      label: stage.name,
      status: executionState.stages.get(stage.id)?.status || 'pending',
      system: stage.system,
    },
    type: 'stageNode',
  }));

  const edges: Edge[] = flow.stages
    .filter(stage => stage.dependsOn?.length)
    .flatMap(stage =>
      stage.dependsOn!.map(dep => ({
        id: `${dep}-${stage.id}`,
        source: dep,
        target: stage.id,
        animated: executionState.currentStage === stage.id,
      }))
    );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={{ stageNode: StageNode }}
      onNodeClick={(_, node) => onStageClick(node.id)}
      fitView
    />
  );
}

// Custom node component
function StageNode({ data }: { data: { label: string; status: StageStatus; system: string } }) {
  const statusColors = {
    pending: 'bg-gray-200',
    running: 'bg-blue-400 animate-pulse',
    passed: 'bg-green-400',
    failed: 'bg-red-400',
    error: 'bg-orange-400',
  };

  const systemIcons = {
    backend: '🖥️',
    frontend: '🌐',
    telegram: '📱',
    database: '🗄️',
  };

  return (
    <div className={`px-4 py-2 rounded-lg border-2 ${statusColors[data.status]}`}>
      <div className="flex items-center gap-2">
        <span>{systemIcons[data.system]}</span>
        <span className="font-medium">{data.label}</span>
        {data.status === 'passed' && <span>✅</span>}
        {data.status === 'failed' && <span>❌</span>}
      </div>
    </div>
  );
}
```

### 5.3 WebSocket Communication

```typescript
// flowtest/ui/src/hooks/useFlowExecution.ts

import { useState, useEffect, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { FlowDefinition, ExecutionState, StageResult } from '../types';

export function useFlowExecution(flowId: string) {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [executionState, setExecutionState] = useState<ExecutionState | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    const s = io('http://localhost:3001');
    setSocket(s);

    s.on('flow:start', (data) => {
      setIsRunning(true);
      setExecutionState(data.state);
    });

    s.on('stage:start', (data) => {
      setExecutionState(prev => ({
        ...prev!,
        currentStage: data.stageId,
      }));
    });

    s.on('stage:complete', (data) => {
      setExecutionState(prev => ({
        ...prev!,
        stages: new Map(prev!.stages).set(data.stageId, data.result),
      }));
    });

    s.on('flow:complete', (data) => {
      setIsRunning(false);
      setExecutionState(data.state);
    });

    return () => { s.disconnect(); };
  }, []);

  const startExecution = useCallback((input?: Record<string, any>) => {
    socket?.emit('flow:execute', { flowId, input });
  }, [socket, flowId]);

  return { executionState, isRunning, startExecution };
}
```

---

## 6. Directory Structure

```
mtt-combined/
├── flowtest/                          # FlowTest platform
│   ├── package.json
│   ├── tsconfig.json
│   │
│   ├── flows/                         # Flow definitions
│   │   ├── container-entry.flow.yaml
│   │   ├── vehicle-exit.flow.yaml
│   │   └── storage-billing.flow.yaml
│   │
│   ├── engine/                        # Core execution engine
│   │   ├── FlowExecutor.ts
│   │   ├── FlowParser.ts
│   │   ├── StateManager.ts
│   │   └── TemplateResolver.ts
│   │
│   ├── adapters/                      # System adapters
│   │   ├── types.ts
│   │   ├── BackendAdapter.ts
│   │   ├── FrontendAdapter.ts
│   │   ├── TelegramAdapter.ts
│   │   └── DatabaseAdapter.ts
│   │
│   ├── server/                        # WebSocket server
│   │   ├── index.ts
│   │   └── FlowController.ts
│   │
│   ├── ui/                            # Visualization UI (React)
│   │   ├── package.json
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── components/
│   │   │   │   ├── FlowGraph.tsx
│   │   │   │   ├── StageDetails.tsx
│   │   │   │   ├── ProgressBar.tsx
│   │   │   │   ├── LiveLog.tsx
│   │   │   │   └── ScreenshotViewer.tsx
│   │   │   ├── hooks/
│   │   │   │   └── useFlowExecution.ts
│   │   │   └── types/
│   │   │       └── index.ts
│   │   └── vite.config.ts
│   │
│   ├── cli/                           # CLI tool
│   │   ├── index.ts
│   │   └── commands/
│   │       ├── run.ts
│   │       ├── list.ts
│   │       └── validate.ts
│   │
│   ├── reports/                       # Generated reports
│   │   └── .gitkeep
│   │
│   └── types/                         # TypeScript types
│       ├── flow.ts
│       ├── execution.ts
│       └── adapters.ts
│
├── backend/                           # Existing Django backend
├── frontend/                          # Existing Vue frontend
└── telegram-miniapp/                  # Existing Telegram app
```

---

## 7. CLI Interface

```bash
# List available flows
$ flowtest list
┌────────────────────────────────────────────────────────────┐
│ Available Flows                                            │
├────────────────────────────────────────────────────────────┤
│ container-entry-to-confirmation   7 stages   ~45s         │
│ vehicle-exit-flow                 4 stages   ~20s         │
│ storage-billing-calculation       3 stages   ~15s         │
└────────────────────────────────────────────────────────────┘

# Run a flow (headless)
$ flowtest run container-entry-to-confirmation
🚀 Starting flow: Container Entry to Confirmation
   Input: { containerCount: 2 }

   [1/7] ✅ Create Containers via API (1.2s)
         └─ Captured: container1_id=42, container2_id=43
   [2/7] ✅ Containers Visible in 3D Map (3.4s)
         └─ Screenshot: reports/stage-2.png
   [3/7] ✅ Manager Places Container 1 (2.1s)
   [4/7] ✅ Manager Places Container 2 (1.8s)
   [5/7] ✅ Work Orders in Telegram (2.5s)
   [6/7] ✅ Vehicle Manager Confirms (3.2s)
   [7/7] ✅ Final State Verification (0.8s)

✅ Flow completed successfully in 15.0s
   Report: reports/container-entry-2026-01-18-14-30.html

# Run with custom input
$ flowtest run container-entry-to-confirmation --input '{"containerCount": 5}'

# Run with UI
$ flowtest run container-entry-to-confirmation --ui
🌐 Opening visualization at http://localhost:3002

# Validate flow definition
$ flowtest validate flows/container-entry.flow.yaml
✅ Flow definition is valid
```

---

## 8. Tech Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| **Engine** | TypeScript + Node.js | Type safety, same as existing frontend |
| **Browser Automation** | Playwright | Already in project, cross-browser |
| **Flow Parser** | js-yaml | Standard YAML parsing |
| **WebSocket** | Socket.io | Real-time updates to UI |
| **UI Framework** | React + Vite | Fast, good ecosystem |
| **Graph Visualization** | React Flow | Beautiful flow diagrams |
| **CLI** | Commander.js | Standard Node CLI |
| **Styling** | Tailwind CSS | Quick, consistent styling |

---

## 9. MVP Implementation Roadmap

### Phase 1: Core Engine (Week 1)
- [ ] Flow parser (YAML → TypeScript objects)
- [ ] Template resolver ({{ variable }} syntax)
- [ ] Backend adapter (API calls)
- [ ] Basic executor (sequential stages)
- [ ] CLI: `flowtest run`

### Phase 2: Browser Adapters (Week 1-2)
- [ ] Frontend adapter (Playwright for Vue)
- [ ] Telegram adapter (Playwright for React)
- [ ] Screenshot capture
- [ ] Login/auth handling

### Phase 3: Visualization UI (Week 2)
- [ ] WebSocket server
- [ ] Flow graph component
- [ ] Stage details panel
- [ ] Live log stream
- [ ] Progress indicator

### Phase 4: Polish & Reports (Week 3)
- [ ] HTML report generation
- [ ] Error handling improvements
- [ ] Parallel stage execution
- [ ] CI/CD integration

---

## 10. Example Usage After MVP

```bash
# Developer workflow
$ cd mtt-combined
$ make dev                                    # Start all services
$ flowtest run container-entry --ui           # Run flow with visualization

# CI/CD workflow (GitHub Actions)
- name: Run business flow tests
  run: |
    flowtest run container-entry-to-confirmation --reporter=junit
    flowtest run vehicle-exit-flow --reporter=junit
```

---

## Next Steps

1. **Review this architecture** - Does it match your vision?
2. **Pick MVP scope** - Which flow to implement first?
3. **Start Phase 1** - Build the core engine

Ready to start implementation?
