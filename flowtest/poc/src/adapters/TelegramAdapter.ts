// ============================================================================
// Telegram Mini App Adapter
// ============================================================================
// Executes mobile browser automation against the React Telegram Mini App
// using Playwright with mobile viewport (iPhone 14 Pro).
//
// Key interactions:
//   - Work order list and cards (antd-mobile)
//   - Task completion flow
//   - Pull-to-refresh and mobile gestures
//
// NOTE: This adapter runs in Node.js context (like FrontendAdapter).
// ============================================================================

import type { Browser, BrowserContext, Page } from 'playwright';
import type {
  Action,
  ActionResult,
  AdapterContext,
  TelegramAction,
  Verification,
  VerificationResult,
  UIVerification,
} from '../types';
import type { Adapter, AdapterConfig, BrowserState } from './types';
import { AdapterError } from './types';
import { interpolate } from './utils';

// ---------------------------------------------------------------------------
// Telegram Adapter Implementation
// ---------------------------------------------------------------------------

export class TelegramAdapter implements Adapter {
  readonly system = 'telegram' as const;
  readonly name = 'Telegram Mini App (Playwright Mobile)';

  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private config: NonNullable<AdapterConfig['telegram']>;
  private ready = false;

  constructor(config: AdapterConfig) {
    if (!config.telegram) {
      throw new AdapterError('Telegram configuration is required', this.name);
    }
    this.config = config.telegram;
  }

  // ---------------------------------------------------------------------------
  // Adapter Interface Implementation
  // ---------------------------------------------------------------------------

  async initialize(context: AdapterContext): Promise<void> {
    context.log('info', `Initializing ${this.name}...`);

    try {
      // Dynamic import of Playwright (only available in Node.js)
      const { chromium, devices } = await import('playwright');

      // Use iPhone 14 Pro as base device
      const iPhone = devices['iPhone 14 Pro'];

      this.browser = await chromium.launch({
        headless: this.config.headless ?? true,
        slowMo: this.config.slowMo ?? 0,
      });

      // Create mobile context with custom viewport
      this.context = await this.browser.newContext({
        ...iPhone,
        viewport: this.config.viewport ?? { width: 390, height: 844 },
        locale: 'ru-RU',
        // Telegram Mini App specific headers
        extraHTTPHeaders: {
          'X-Telegram-Mini-App': 'true',
        },
      });

      this.page = await this.context.newPage();

      // Navigate to the app with mock Telegram environment
      await this.page.goto(this.config.baseUrl, { waitUntil: 'networkidle' });

      this.ready = true;
      context.log('success', `${this.name} initialized with mobile viewport`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      context.log('error', `${this.name} initialization failed: ${message}`);
      throw new AdapterError(message, this.name, 'initialize');
    }
  }

  async executeAction(action: Action, context: AdapterContext): Promise<ActionResult> {
    if (action.type !== 'telegram') {
      return {
        description: action.description,
        success: false,
        duration: 0,
        error: `TelegramAdapter cannot execute ${action.type} actions`,
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
    const telegramAction = action as TelegramAction;

    try {
      const result = await this.executeTelegramAction(telegramAction, context);
      const duration = Date.now() - startTime;

      return {
        ...result,
        duration,
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      const message = error instanceof Error ? error.message : 'Unknown error';

      context.log('error', `Telegram action failed: ${message}`, {
        action: telegramAction.action,
        selector: telegramAction.selector,
      });

      return {
        description: telegramAction.description,
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
    if (verification.type !== 'ui') {
      return {
        description: verification.description,
        passed: false,
        failureReason: `TelegramAdapter cannot handle ${verification.type} verifications`,
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

  async screenshot(name: string): Promise<string | null> {
    if (!this.page) return null;

    try {
      const path = `${this.config.screenshotDir ?? './screenshots'}/${name}-mobile-${Date.now()}.png`;
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
  }

  isReady(): boolean {
    return this.ready && this.page !== null;
  }

  // ---------------------------------------------------------------------------
  // Telegram Action Execution
  // ---------------------------------------------------------------------------

  private async executeTelegramAction(
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const page = this.page!;

    switch (action.action) {
      case 'navigate':
        return this.actionNavigate(page, action, context);

      case 'tap':
        return this.actionTap(page, action, context);

      case 'swipe':
        return this.actionSwipe(page, action, context);

      case 'pullToRefresh':
        return this.actionPullToRefresh(page, action, context);

      case 'waitForElement':
        return this.actionWaitForElement(page, action, context);

      case 'screenshot':
        return this.actionScreenshot(page, action, context);

      case 'fillInput':
        return this.actionFillInput(page, action, context);

      case 'confirmDialog':
        return this.actionConfirmDialog(page, action, context);

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
    action: TelegramAction,
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

  private async actionTap(
    page: Page,
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    if (!action.selector) {
      return {
        description: action.description,
        success: false,
        error: 'No selector specified for tap action',
      };
    }

    const selector = interpolate(action.selector, context.captured);
    context.log('info', `Tapping ${selector}`);

    await page.waitForSelector(selector, { state: 'visible', timeout: 10000 });
    await page.tap(selector);

    // Small delay after tap for mobile feel
    await page.waitForTimeout(100);

    return {
      description: action.description,
      success: true,
      details: `Tapped ${selector}`,
    };
  }

  private async actionSwipe(
    page: Page,
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const direction = action.direction ?? 'up';
    const selector = action.selector;

    context.log('info', `Swiping ${direction}${selector ? ` on ${selector}` : ''}`);

    // Get swipe target
    let targetElement;
    if (selector) {
      targetElement = await page.$(interpolate(selector, context.captured));
    }

    const box = targetElement
      ? await targetElement.boundingBox()
      : { x: 195, y: 422, width: 390, height: 400 }; // Center of iPhone screen

    if (!box) {
      return {
        description: action.description,
        success: false,
        error: 'Could not determine swipe area',
      };
    }

    // Calculate swipe coordinates
    const centerX = box.x + box.width / 2;
    const centerY = box.y + box.height / 2;
    const swipeDistance = 200;

    let startX = centerX, startY = centerY, endX = centerX, endY = centerY;

    switch (direction) {
      case 'up':
        startY = centerY + swipeDistance / 2;
        endY = centerY - swipeDistance / 2;
        break;
      case 'down':
        startY = centerY - swipeDistance / 2;
        endY = centerY + swipeDistance / 2;
        break;
      case 'left':
        startX = centerX + swipeDistance / 2;
        endX = centerX - swipeDistance / 2;
        break;
      case 'right':
        startX = centerX - swipeDistance / 2;
        endX = centerX + swipeDistance / 2;
        break;
    }

    // Perform swipe gesture
    await page.mouse.move(startX, startY);
    await page.mouse.down();
    await page.mouse.move(endX, endY, { steps: 10 });
    await page.mouse.up();

    return {
      description: action.description,
      success: true,
      details: `Swiped ${direction}`,
    };
  }

  private async actionPullToRefresh(
    page: Page,
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    context.log('info', 'Performing pull-to-refresh');

    // Pull-to-refresh gesture: swipe down from top
    const viewport = page.viewportSize() ?? { width: 390, height: 844 };
    const centerX = viewport.width / 2;

    await page.mouse.move(centerX, 100);
    await page.mouse.down();
    await page.mouse.move(centerX, 400, { steps: 20 });
    await page.mouse.up();

    // Wait for refresh animation and network
    await page.waitForTimeout(500);
    await page.waitForLoadState('networkidle');

    return {
      description: action.description,
      success: true,
      details: 'Pull-to-refresh completed',
    };
  }

  private async actionWaitForElement(
    page: Page,
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    if (!action.selector) {
      return {
        description: action.description,
        success: false,
        error: 'No selector specified for waitForElement action',
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

  private async actionScreenshot(
    _page: Page,
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const name = action.value ?? 'telegram-screenshot';
    const path = await this.screenshot(name);

    if (!path) {
      return {
        description: action.description,
        success: false,
        error: 'Screenshot capture failed',
      };
    }

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

  private async actionFillInput(
    page: Page,
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    if (!action.selector || action.value === undefined) {
      return {
        description: action.description,
        success: false,
        error: 'Selector and value required for fillInput action',
      };
    }

    const selector = interpolate(action.selector, context.captured);
    const value = interpolate(action.value, context.captured);
    context.log('info', `Filling "${value}" into ${selector}`);

    await page.waitForSelector(selector, { state: 'visible', timeout: 10000 });
    await page.fill(selector, value);

    return {
      description: action.description,
      success: true,
      details: `Filled ${selector}`,
    };
  }

  private async actionConfirmDialog(
    page: Page,
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    context.log('info', 'Confirming dialog...');

    // Look for antd-mobile dialog confirm button
    const confirmButton = await page.$(
      '.adm-dialog-confirm .adm-dialog-button-primary, .adm-dialog .adm-button-primary'
    );

    if (confirmButton) {
      await confirmButton.tap();
    } else {
      // Try generic confirm button
      await page.tap('button:has-text("Confirm"), button:has-text("OK"), button:has-text("Да")');
    }

    // Wait for dialog to close
    await page.waitForTimeout(300);

    return {
      description: action.description,
      success: true,
      details: 'Dialog confirmed',
    };
  }

  private async actionCustom(
    page: Page,
    action: TelegramAction,
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
      case 'selectWorkOrder':
        return this.custom_selectWorkOrder(page, action, context);

      case 'completeWorkOrder':
        return this.custom_completeWorkOrder(page, action, context);

      case 'navigateToWorkOrders':
        return this.custom_navigateToWorkOrders(page, action, context);

      default:
        return {
          description: action.description,
          success: false,
          error: `Unknown custom action: ${customAction}`,
        };
    }
  }

  // ---------------------------------------------------------------------------
  // Custom Actions for Work Orders
  // ---------------------------------------------------------------------------

  private async custom_selectWorkOrder(
    page: Page,
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const containerNumber = interpolate(
      (action.params?.containerNumber as string) ?? '',
      context.captured
    );

    context.log('info', `Selecting work order for ${containerNumber}`);

    // Find and tap the work order card
    const cardSelector = `.adm-card:has-text("${containerNumber}")`;
    await page.waitForSelector(cardSelector, { timeout: 10000 });
    await page.tap(cardSelector);

    return {
      description: action.description,
      success: true,
      details: `Selected work order for ${containerNumber}`,
    };
  }

  private async custom_completeWorkOrder(
    page: Page,
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    const containerNumber = interpolate(
      (action.params?.containerNumber as string) ?? '',
      context.captured
    );

    context.log('info', `Completing work order for ${containerNumber}`);

    // Check for empty state or loading error first
    const emptyState = await page.$('.adm-empty, :has-text("Вазифалар йўқ")');
    const errorToast = await page.$('.adm-toast:has-text("хатолик")');

    if (emptyState || errorToast) {
      return {
        description: action.description,
        success: false,
        error: 'No work orders available - API returned empty or error (likely missing Telegram auth in dev mode)',
      };
    }

    // Select the work order first if not already on detail page
    if (containerNumber) {
      const cardSelector = `.adm-card:has-text("${containerNumber}")`;
      const card = await page.$(cardSelector);
      if (!card) {
        return {
          description: action.description,
          success: false,
          error: `Work order card for ${containerNumber} not found - work orders may not be assigned to this operator`,
        };
      }
      await card.tap();
      await page.waitForTimeout(300);
    }

    // Tap complete/confirm button (Uzbek: Бажарилди, Russian: Завершить)
    const completeButton = await page.$(
      '.adm-button:has-text("Бажарилди"), .adm-button:has-text("Complete"), .adm-button:has-text("Confirm"), .adm-button:has-text("Завершить")'
    );

    if (!completeButton) {
      return {
        description: action.description,
        success: false,
        error: 'Complete button not found - ensure work order card is visible',
      };
    }

    await completeButton.tap();

    // Wait for confirmation dialog if it appears
    await page.waitForTimeout(500);
    const confirmDialog = await page.$('.adm-dialog');
    if (confirmDialog) {
      await page.tap('.adm-dialog-button-primary, .adm-button-primary');
      await page.waitForTimeout(300);
    }

    // Wait for success toast or navigation
    await page.waitForTimeout(500);

    // Capture completion info
    let capturedData: Record<string, unknown> | undefined;
    if (action.capture) {
      capturedData = {
        [action.capture]: {
          containerNumber,
          completedAt: new Date().toISOString(),
          status: 'completed',
        },
      };
      Object.assign(context.captured, capturedData);
    }

    return {
      description: action.description,
      success: true,
      details: `Completed work order${containerNumber ? ` for ${containerNumber}` : ''}`,
      capturedData,
    };
  }

  private async custom_navigateToWorkOrders(
    page: Page,
    action: TelegramAction,
    context: AdapterContext
  ): Promise<Omit<ActionResult, 'duration'>> {
    context.log('info', 'Navigating to work orders page');

    // Try navigation tab or direct URL
    const workOrdersTab = await page.$('a[href*="work-orders"], .tab-bar-item:has-text("Задачи")');

    if (workOrdersTab) {
      await workOrdersTab.tap();
    } else {
      await page.goto(`${this.config.baseUrl}/work-orders`, { waitUntil: 'networkidle' });
    }

    // Wait for work orders list to load
    await page.waitForSelector('.adm-card, .work-order-list', { timeout: 10000 });

    return {
      description: action.description,
      success: true,
      details: 'Navigated to work orders',
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
        case 'visible': {
          const element = await page.$(selector);
          const isVisible = element ? await element.isVisible() : false;
          return {
            description: verification.description,
            passed: isVisible,
            actual: isVisible,
            expected: true,
            failureReason: isVisible ? undefined : `Element ${selector} not visible`,
          };
        }

        case 'exists': {
          const element = await page.$(selector);
          return {
            description: verification.description,
            passed: element !== null,
            actual: element !== null,
            expected: true,
            failureReason: element ? undefined : `Element ${selector} not found`,
          };
        }

        case 'hasText': {
          const element = await page.$(selector);
          const text = element ? await element.textContent() : null;
          const expectedText = String(verification.expected);
          const hasText = text?.includes(expectedText) ?? false;
          return {
            description: verification.description,
            passed: hasText,
            actual: text,
            expected: expectedText,
            failureReason: hasText ? undefined : `Text "${expectedText}" not found`,
          };
        }

        case 'count': {
          const elements = await page.$$(selector);
          const count = elements.length;
          const expectedCount = Number(verification.expected);
          return {
            description: verification.description,
            passed: count === expectedCount,
            actual: count,
            expected: expectedCount,
            failureReason: count === expectedCount ? undefined : `Expected ${expectedCount}, found ${count}`,
          };
        }

        case 'count_gte': {
          const elements = await page.$$(selector);
          const count = elements.length;
          const expectedMin = Number(verification.expected);
          return {
            description: verification.description,
            passed: count >= expectedMin,
            actual: count,
            expected: `>= ${expectedMin}`,
            failureReason: count >= expectedMin ? undefined : `Expected at least ${expectedMin}, found ${count}`,
          };
        }

        case 'count_lte': {
          const elements = await page.$$(selector);
          const count = elements.length;
          const expectedMax = Number(verification.expected);
          return {
            description: verification.description,
            passed: count <= expectedMax,
            actual: count,
            expected: `<= ${expectedMax}`,
            failureReason: count <= expectedMax ? undefined : `Expected at most ${expectedMax}, found ${count}`,
          };
        }

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

  /**
   * Get current browser state for debugging
   */
  async getBrowserState(): Promise<BrowserState | null> {
    if (!this.page) return null;

    return {
      url: this.page.url(),
      title: await this.page.title(),
      isAuthenticated: true, // Telegram Mini App doesn't have traditional auth
    };
  }
}

// ---------------------------------------------------------------------------
// Factory Function
// ---------------------------------------------------------------------------

export function createTelegramAdapter(config: AdapterConfig): TelegramAdapter {
  return new TelegramAdapter(config);
}
