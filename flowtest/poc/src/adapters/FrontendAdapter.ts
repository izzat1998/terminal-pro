// ============================================================================
// Frontend Adapter
// ============================================================================
// Executes browser automation actions against the Vue SPA using Playwright.
// Handles login, navigation, Ant Design component interactions, and 3D scene.
//
// NOTE: This adapter requires Node.js runtime (not browser). The FlowTest
// POC UI uses SimulationAdapter in browser context, while this adapter runs
// via CLI or test runner (e.g., `npm run test:flow`).
//
// Key interactions:
//   - Login flow via /login page
//   - Ant Design Vue components (Select, Modal, Table, etc.)
//   - 3D Terminal scene for container placement
// ============================================================================

import type { Browser, BrowserContext, Page } from 'playwright';
import type {
  Action,
  ActionResult,
  AdapterContext,
  FrontendAction,
  Verification,
  VerificationResult,
  UIVerification,
  ResponseVerification,
} from '../types';
import type { Adapter, AdapterConfig, BrowserState } from './types';
import { AdapterError } from './types';
import { FRONTEND_CONFIG } from '../config';
import { interpolate, getNestedValue } from './utils';

// ---------------------------------------------------------------------------
// Frontend Adapter Implementation
// ---------------------------------------------------------------------------

export class FrontendAdapter implements Adapter {
  readonly system = 'frontend' as const;
  readonly name = 'Frontend Vue SPA (Playwright)';

  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private config: NonNullable<AdapterConfig['frontend']>;
  private ready = false;
  private authenticated = false;

  constructor(config: AdapterConfig) {
    if (!config.frontend) {
      throw new AdapterError('Frontend configuration is required', this.name);
    }
    this.config = config.frontend;
  }

  // ---------------------------------------------------------------------------
  // Adapter Interface Implementation
  // ---------------------------------------------------------------------------

  async initialize(context: AdapterContext): Promise<void> {
    context.log('info', `Initializing ${this.name}...`);

    try {
      // Dynamic import of Playwright (only available in Node.js)
      const { chromium } = await import('playwright');

      this.browser = await chromium.launch({
        headless: this.config.headless ?? true,
        slowMo: this.config.slowMo ?? 0,
      });

      this.context = await this.browser.newContext({
        viewport: { width: 1920, height: 1080 },
        locale: 'ru-RU',
      });

      this.page = await this.context.newPage();

      // Navigate to the app
      await this.page.goto(this.config.baseUrl);
      this.ready = true;

      context.log('success', `${this.name} initialized successfully`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      context.log('error', `${this.name} initialization failed: ${message}`);
      throw new AdapterError(message, this.name, 'initialize');
    }
  }

  async executeAction(action: Action, context: AdapterContext): Promise<ActionResult> {
    if (action.type !== 'frontend') {
      return {
        description: action.description,
        success: false,
        duration: 0,
        error: `FrontendAdapter cannot execute ${action.type} actions`,
      };
    }

    if (!this.page) {
      return {
        description: action.description,
        success: false,
        duration: 0,
        error: 'Browser not initialized',
      };
    }

    const startTime = Date.now();
    const frontendAction = action as FrontendAction;

    try {
      const result = await this.executeUIAction(frontendAction, context);
      const duration = Date.now() - startTime;

      return {
        ...result,
        duration,
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      const message = error instanceof Error ? error.message : 'Unknown error';

      context.log('error', `UI action failed: ${message}`, {
        action: frontendAction.action,
        selector: frontendAction.selector,
      });

      return {
        description: frontendAction.description,
        success: false,
        duration,
        error: message,
      };
    }
  }

  async verify(
    verification: Verification,
    context: AdapterContext
  ): Promise<VerificationResult> {
    // Handle response verifications (checking captured data)
    if (verification.type === 'response') {
      return this.verifyResponse(verification, context);
    }

    if (verification.type !== 'ui') {
      return {
        description: verification.description,
        passed: false,
        failureReason: `FrontendAdapter cannot handle ${verification.type} verifications`,
      };
    }

    if (!this.page) {
      return {
        description: verification.description,
        passed: false,
        failureReason: 'Browser not initialized',
      };
    }

    return this.verifyUI(verification, context);
  }

  private verifyResponse(
    verification: ResponseVerification,
    context: AdapterContext
  ): VerificationResult {
    const { field, operator, expected, description } = verification;
    const actual = getNestedValue(context.captured, field);

    let passed = false;
    let failureReason: string | undefined;

    switch (operator) {
      case 'exists':
        passed = actual !== undefined && actual !== null;
        if (!passed) failureReason = `Field '${field}' does not exist`;
        break;

      case 'notExists':
        passed = actual === undefined || actual === null;
        if (!passed) failureReason = `Field '${field}' exists but should not`;
        break;

      case 'equals':
        passed = JSON.stringify(actual) === JSON.stringify(expected);
        if (!passed) failureReason = `Expected '${expected}', got '${actual}'`;
        break;

      case 'notEquals':
        passed = JSON.stringify(actual) !== JSON.stringify(expected);
        if (!passed) failureReason = `Value should not equal '${expected}'`;
        break;

      case 'contains':
        if (typeof actual === 'string' && typeof expected === 'string') {
          passed = actual.includes(expected);
        } else if (Array.isArray(actual)) {
          passed = actual.some((item) => JSON.stringify(item) === JSON.stringify(expected));
        }
        if (!passed) failureReason = `Value does not contain '${expected}'`;
        break;

      default:
        failureReason = `Unknown operator: ${operator}`;
    }

    return {
      description,
      passed,
      actual,
      expected,
      failureReason,
    };
  }

  async screenshot(name: string): Promise<string | null> {
    if (!this.page) return null;

    try {
      const path = `${this.config.screenshotDir ?? './screenshots'}/${name}-${Date.now()}.png`;
      await this.page.screenshot({ path, fullPage: true });
      return path;
    } catch (error) {
      console.error('Screenshot failed:', error);
      return null;
    }
  }

  async cleanup(): Promise<void> {
    if (this.context) {
      await this.context.close();
      this.context = null;
    }
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
    }
    this.page = null;
    this.ready = false;
    this.authenticated = false;
  }

  isReady(): boolean {
    return this.ready && this.page !== null;
  }

  // ---------------------------------------------------------------------------
  // UI Action Execution
  // ---------------------------------------------------------------------------

  private async executeUIAction(
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const page = this.page!;

    switch (action.action) {
      case 'navigate':
        return this.actionNavigate(page, action, context);

      case 'login':
        return this.actionLogin(page, action, context);

      case 'click':
        return this.actionClick(page, action, context);

      case 'type':
        return this.actionType(page, action, context);

      case 'select':
        return this.actionSelect(page, action, context);

      case 'waitForSelector':
        return this.actionWaitForSelector(page, action, context);

      case 'waitForNetwork':
        return this.actionWaitForNetwork(page, action, context);

      case 'screenshot':
        return this.actionScreenshot(page, action, context);

      case 'dragAndDrop':
        return this.actionDragAndDrop(page, action, context);

      case 'custom':
        return this.actionCustom(page, action, context);

      default:
        return {
          description: action.description,
          success: false,
          error: `Unknown action: ${action.action}`,
        };
    }
  }

  // ---------------------------------------------------------------------------
  // Individual Action Implementations
  // ---------------------------------------------------------------------------

  private async actionNavigate(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const url = action.url ?? action.selector;
    if (!url) {
      return {
        description: action.description,
        success: false,
        error: 'No URL specified for navigate action',
      };
    }

    const fullUrl = url.startsWith('http') ? url : `${this.config.baseUrl}${url}`;
    context.log('info', `Navigating to ${fullUrl}`);

    await page.goto(fullUrl, { waitUntil: 'networkidle' });

    return {
      description: action.description,
      success: true,
      details: `Navigated to ${fullUrl}`,
    };
  }

  private async actionLogin(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const credentials = action.credentials ?? {
      username: 'admin',
      password: 'admin123',
    };

    context.log('info', `Logging in as ${credentials.username}...`);

    // Navigate to login if not already there
    if (!page.url().includes('/login')) {
      await page.goto(`${this.config.baseUrl}/login`);
    }

    // Wait for form
    await page.waitForSelector(FRONTEND_CONFIG.selectors.usernameInput, {
      state: 'visible',
      timeout: 10000,
    });

    // Fill credentials
    await page.fill(FRONTEND_CONFIG.selectors.usernameInput, credentials.username);
    await page.fill(FRONTEND_CONFIG.selectors.passwordInput, credentials.password);

    // Submit
    await page.click(FRONTEND_CONFIG.selectors.loginButton);

    // Wait for redirect (dashboard or main page)
    await page.waitForURL(/\/(dashboard|containers|vehicles)?$/, { timeout: 15000 });

    this.authenticated = true;
    context.log('success', `Logged in as ${credentials.username}`);

    return {
      description: action.description,
      success: true,
      details: `Authenticated as ${credentials.username}`,
    };
  }

  private async actionClick(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    if (!action.selector) {
      return {
        description: action.description,
        success: false,
        error: 'No selector specified for click action',
      };
    }

    const selector = interpolate(action.selector, context.captured);
    context.log('info', `Clicking ${selector}`);

    await page.waitForSelector(selector, { state: 'visible', timeout: 10000 });
    await page.click(selector);

    return {
      description: action.description,
      success: true,
      details: `Clicked ${selector}`,
    };
  }

  private async actionType(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    if (!action.selector || action.value === undefined) {
      return {
        description: action.description,
        success: false,
        error: 'Selector and value required for type action',
      };
    }

    const selector = interpolate(action.selector, context.captured);
    const value = interpolate(action.value, context.captured);
    context.log('info', `Typing "${value}" into ${selector}`);

    await page.waitForSelector(selector, { state: 'visible', timeout: 10000 });
    await page.fill(selector, value);

    return {
      description: action.description,
      success: true,
      details: `Typed into ${selector}`,
    };
  }

  private async actionSelect(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    if (!action.selector || action.value === undefined) {
      return {
        description: action.description,
        success: false,
        error: 'Selector and value required for select action',
      };
    }

    const selector = interpolate(action.selector, context.captured);
    const value = interpolate(action.value, context.captured);
    context.log('info', `Selecting "${value}" in ${selector}`);

    // Ant Design Select pattern
    await page.click(selector);
    await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
    await page.click(`.ant-select-item-option:has-text("${value}")`);

    return {
      description: action.description,
      success: true,
      details: `Selected "${value}" in ${selector}`,
    };
  }

  private async actionWaitForSelector(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    if (!action.selector) {
      return {
        description: action.description,
        success: false,
        error: 'No selector specified for waitForSelector action',
      };
    }

    const selector = interpolate(action.selector, context.captured);
    const timeout = (action.params?.timeout as number) ?? 30000;
    context.log('info', `Waiting for ${selector}`);

    await page.waitForSelector(selector, { state: 'visible', timeout });

    return {
      description: action.description,
      success: true,
      details: `Found ${selector}`,
    };
  }

  private async actionWaitForNetwork(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    context.log('info', 'Waiting for network idle...');
    await page.waitForLoadState('networkidle');

    return {
      description: action.description,
      success: true,
      details: 'Network idle',
    };
  }

  private async actionScreenshot(
    _page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const name = action.value ?? 'screenshot';
    const path = await this.screenshot(name);

    if (!path) {
      return {
        description: action.description,
        success: false,
        error: 'Screenshot capture failed',
      };
    }

    // Capture path if requested
    let capturedData: Record<string, unknown> | undefined;
    if (action.capture) {
      capturedData = { [action.capture]: path };
      Object.assign(context.captured, capturedData);
    }

    return {
      description: action.description,
      success: true,
      details: `Screenshot saved: ${path}`,
      capturedData,
    };
  }

  private async actionDragAndDrop(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const source = action.selector;
    const target = action.params?.target as string;

    if (!source || !target) {
      return {
        description: action.description,
        success: false,
        error: 'Source and target selectors required for dragAndDrop',
      };
    }

    context.log('info', `Dragging ${source} to ${target}`);

    await page.dragAndDrop(
      interpolate(source, context.captured),
      interpolate(target, context.captured)
    );

    return {
      description: action.description,
      success: true,
      details: `Dragged ${source} to ${target}`,
    };
  }

  private async actionCustom(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const customAction = action.customAction;
    if (!customAction) {
      return {
        description: action.description,
        success: false,
        error: 'No customAction specified',
      };
    }

    switch (customAction) {
      case 'place3DContainer':
        return this.custom_place3DContainer(page, action, context);

      case 'confirmPlacement':
        return this.custom_confirmPlacement(page, action, context);

      case 'selectUnplacedContainer':
        return this.custom_selectUnplacedContainer(page, action, context);

      default:
        return {
          description: action.description,
          success: false,
          error: `Unknown custom action: ${customAction}`,
        };
    }
  }

  // ---------------------------------------------------------------------------
  // Custom Actions for 3D Terminal Scene
  // ---------------------------------------------------------------------------

  private async custom_place3DContainer(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const containerNumber = action.params?.containerNumber as string;
    const position = action.params?.position as { row: number; bay: number; tier: number };

    if (!containerNumber || !position) {
      return {
        description: action.description,
        success: false,
        error: 'containerNumber and position required for place3DContainer',
      };
    }

    context.log('info', `Placing ${containerNumber} at R${position.row}-B${position.bay}-T${position.tier}`);

    // Container should already be selected (placement mode active from selectUnplacedContainer)
    // Wait for placement mode to be active (markers should appear)
    await page.waitForTimeout(500);

    // Click on the target position in the 3D grid
    // This might need adjustment based on actual 3D scene implementation
    const canvas = await page.waitForSelector(FRONTEND_CONFIG.selectors.terminalCanvas);

    // Calculate click position based on grid coordinates
    // This is simplified - real implementation would need proper 3D coordinate mapping
    const canvasBox = await canvas.boundingBox();
    if (canvasBox) {
      // Click at a position within the canvas
      // Actual position calculation would depend on 3D scene implementation
      await page.mouse.click(
        canvasBox.x + canvasBox.width * 0.5,
        canvasBox.y + canvasBox.height * 0.5
      );
    }

    // Wait for placement to register
    await page.waitForTimeout(500);

    // Capture placement info
    let capturedData: Record<string, unknown> | undefined;
    if (action.capture) {
      capturedData = {
        [action.capture]: {
          containerNumber,
          position,
          location: `A-R${String(position.row).padStart(2, '0')}-B${String(position.bay).padStart(2, '0')}-T${position.tier}`,
        },
      };
      Object.assign(context.captured, capturedData);
    }

    return {
      description: action.description,
      success: true,
      details: `Placed ${containerNumber} at position`,
      capturedData,
    };
  }

  private async custom_confirmPlacement(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    context.log('info', 'Confirming placement...');

    // Wait for the placement confirmation modal to appear
    await page.waitForSelector('.ant-modal-content', { timeout: 10000 });

    // Click the "Создать задачу" (Create task) button
    await page.click('.ant-btn-primary:has-text("Создать задачу")');

    // Wait for success message
    await page.waitForSelector('.ant-message-success', { timeout: 10000 });

    return {
      description: action.description,
      success: true,
      details: 'Placement confirmed',
    };
  }

  private async custom_selectUnplacedContainer(
    page: Page,
    action: FrontendAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const containerNumber = interpolate(
      (action.params?.containerNumber as string) ?? '',
      context.captured
    );

    context.log('info', `Selecting unplaced container ${containerNumber}`);

    // Find the container item with matching number and click its "Разместить" button
    const containerItem = page.locator(`${FRONTEND_CONFIG.selectors.containerItem}:has-text("${containerNumber}")`);
    await containerItem.locator(FRONTEND_CONFIG.selectors.placeButton).click();

    return {
      description: action.description,
      success: true,
      details: `Selected ${containerNumber}`,
    };
  }

  // ---------------------------------------------------------------------------
  // UI Verification
  // ---------------------------------------------------------------------------

  private async verifyUI(
    verification: UIVerification,
    context: AdapterContext
  ): Promise<VerificationResult> {
    const page = this.page!;
    const selector = interpolate(verification.selector, context.captured);

    try {
      switch (verification.check) {
        case 'visible':
          return this.verifyVisible(page, selector, verification);

        case 'hidden':
          return this.verifyHidden(page, selector, verification);

        case 'exists':
          return this.verifyExists(page, selector, verification);

        case 'hasText':
          return this.verifyHasText(page, selector, verification);

        case 'hasValue':
          return this.verifyHasValue(page, selector, verification);

        case 'count':
          return this.verifyCount(page, selector, verification);

        case 'count_gte':
          return this.verifyCountGte(page, selector, verification);

        case 'count_lte':
          return this.verifyCountLte(page, selector, verification);

        case 'enabled':
          return this.verifyEnabled(page, selector, verification);

        case 'disabled':
          return this.verifyDisabled(page, selector, verification);

        default:
          return {
            description: verification.description,
            passed: false,
            failureReason: `Unknown check: ${verification.check}`,
          };
      }
    } catch (error) {
      return {
        description: verification.description,
        passed: false,
        failureReason: error instanceof Error ? error.message : 'Verification failed',
      };
    }
  }

  private async verifyVisible(
    page: Page,
    selector: string,
    verification: UIVerification
  ): Promise<VerificationResult> {
    const element = await page.$(selector);
    const isVisible = element ? await element.isVisible() : false;

    return {
      description: verification.description,
      passed: isVisible === true,
      actual: isVisible,
      expected: true,
      failureReason: isVisible ? undefined : `Element ${selector} is not visible`,
    };
  }

  private async verifyHidden(
    page: Page,
    selector: string,
    verification: UIVerification
  ): Promise<VerificationResult> {
    const element = await page.$(selector);
    const isHidden = !element || !(await element.isVisible());

    return {
      description: verification.description,
      passed: isHidden === true,
      actual: isHidden,
      expected: true,
      failureReason: isHidden ? undefined : `Element ${selector} is visible`,
    };
  }

  private async verifyExists(
    page: Page,
    selector: string,
    verification: UIVerification
  ): Promise<VerificationResult> {
    const element = await page.$(selector);

    return {
      description: verification.description,
      passed: element !== null,
      actual: element !== null,
      expected: true,
      failureReason: element ? undefined : `Element ${selector} does not exist`,
    };
  }

  private async verifyHasText(
    page: Page,
    selector: string,
    verification: UIVerification
  ): Promise<VerificationResult> {
    const element = await page.$(selector);
    const text = element ? await element.textContent() : null;
    const expectedText = String(verification.expected);
    const hasText = text?.includes(expectedText) ?? false;

    return {
      description: verification.description,
      passed: hasText,
      actual: text,
      expected: expectedText,
      failureReason: hasText ? undefined : `Element does not contain "${expectedText}"`,
    };
  }

  private async verifyHasValue(
    page: Page,
    selector: string,
    verification: UIVerification
  ): Promise<VerificationResult> {
    const value = await page.inputValue(selector);
    const expectedValue = String(verification.expected);
    const matches = value === expectedValue;

    return {
      description: verification.description,
      passed: matches,
      actual: value,
      expected: expectedValue,
      failureReason: matches ? undefined : `Value mismatch`,
    };
  }

  private async verifyCount(
    page: Page,
    selector: string,
    verification: UIVerification
  ): Promise<VerificationResult> {
    const elements = await page.$$(selector);
    const count = elements.length;
    const expectedCount = Number(verification.expected);
    const matches = count === expectedCount;

    return {
      description: verification.description,
      passed: matches,
      actual: count,
      expected: expectedCount,
      failureReason: matches ? undefined : `Expected ${expectedCount} elements, found ${count}`,
    };
  }

  private async verifyCountGte(
    page: Page,
    selector: string,
    verification: UIVerification
  ): Promise<VerificationResult> {
    const elements = await page.$$(selector);
    const count = elements.length;
    const expectedMin = Number(verification.expected);
    const matches = count >= expectedMin;

    return {
      description: verification.description,
      passed: matches,
      actual: count,
      expected: `>= ${expectedMin}`,
      failureReason: matches ? undefined : `Expected at least ${expectedMin} elements, found ${count}`,
    };
  }

  private async verifyCountLte(
    page: Page,
    selector: string,
    verification: UIVerification
  ): Promise<VerificationResult> {
    const elements = await page.$$(selector);
    const count = elements.length;
    const expectedMax = Number(verification.expected);
    const matches = count <= expectedMax;

    return {
      description: verification.description,
      passed: matches,
      actual: count,
      expected: `<= ${expectedMax}`,
      failureReason: matches ? undefined : `Expected at most ${expectedMax} elements, found ${count}`,
    };
  }

  private async verifyEnabled(
    page: Page,
    selector: string,
    verification: UIVerification
  ): Promise<VerificationResult> {
    const element = await page.$(selector);
    const isEnabled = element ? await element.isEnabled() : false;

    return {
      description: verification.description,
      passed: isEnabled === true,
      actual: isEnabled,
      expected: true,
      failureReason: isEnabled ? undefined : `Element ${selector} is disabled`,
    };
  }

  private async verifyDisabled(
    page: Page,
    selector: string,
    verification: UIVerification
  ): Promise<VerificationResult> {
    const element = await page.$(selector);
    const isDisabled = element ? !(await element.isEnabled()) : true;

    return {
      description: verification.description,
      passed: isDisabled === true,
      actual: isDisabled,
      expected: true,
      failureReason: isDisabled ? undefined : `Element ${selector} is enabled`,
    };
  }

  /**
   * Get current browser state for debugging
   */
  async getBrowserState(): Promise<BrowserState | null> {
    if (!this.page) return null;

    return {
      url: this.page.url(),
      title: await this.page.title(),
      isAuthenticated: this.authenticated,
    };
  }
}

// ---------------------------------------------------------------------------
// Factory Function
// ---------------------------------------------------------------------------

export function createFrontendAdapter(config: AdapterConfig): FrontendAdapter {
  return new FrontendAdapter(config);
}
