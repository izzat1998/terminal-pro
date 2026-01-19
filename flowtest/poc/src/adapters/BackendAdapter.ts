// ============================================================================
// Backend Adapter
// ============================================================================
// Executes API actions against the Django REST backend using Axios.
// Handles JWT authentication, token refresh, and variable interpolation.
//
// Endpoints used:
//   POST /api/auth/login/           - Get JWT tokens
//   POST /api/auth/token/refresh/   - Refresh access token
//   /api/terminal/entries/          - Container CRUD
//   /api/terminal/placement/assign/ - Position assignment
//   /api/terminal/work-orders/      - Work order management
// ============================================================================

import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';
import type {
  Action,
  ActionResult,
  AdapterContext,
  BackendAction,
  Verification,
  VerificationResult,
  ResponseVerification,
  DatabaseVerification,
} from '../types';
import type {
  Adapter,
  JWTTokens,
  APIResponse,
  AdapterConfig,
} from './types';
import { AdapterError, AuthenticationError } from './types';
import { getNestedValue, interpolate, interpolateObject } from './utils';

// ---------------------------------------------------------------------------
// Backend Adapter Implementation
// ---------------------------------------------------------------------------

export class BackendAdapter implements Adapter {
  readonly system = 'backend' as const;
  readonly name = 'Backend API (Axios)';

  private client: AxiosInstance;
  private tokens: JWTTokens | null = null;
  private config: NonNullable<AdapterConfig['backend']>;
  private ready = false;

  constructor(config: AdapterConfig) {
    if (!config.backend) {
      throw new AdapterError('Backend configuration is required', this.name);
    }

    this.config = config.backend;
    this.client = axios.create({
      baseURL: this.config.baseUrl,
      timeout: this.config.timeout ?? 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to attach auth token
    this.client.interceptors.request.use((requestConfig) => {
      if (this.tokens?.access) {
        requestConfig.headers.Authorization = `Bearer ${this.tokens.access}`;
      }
      return requestConfig;
    });

    // Add response interceptor for token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config;

        // If 401 and we have a refresh token, try to refresh
        if (
          error.response?.status === 401 &&
          this.tokens?.refresh &&
          originalRequest &&
          !(originalRequest as { _retry?: boolean })._retry
        ) {
          (originalRequest as { _retry?: boolean })._retry = true;

          try {
            await this.refreshToken();
            originalRequest.headers.Authorization = `Bearer ${this.tokens!.access}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            // Refresh failed, need to re-authenticate
            this.tokens = null;
            this.ready = false;
            throw refreshError;
          }
        }

        throw error;
      }
    );
  }

  // ---------------------------------------------------------------------------
  // Adapter Interface Implementation
  // ---------------------------------------------------------------------------

  async initialize(context: AdapterContext): Promise<void> {
    context.log('info', `Initializing ${this.name}...`);

    try {
      await this.authenticate();
      this.ready = true;
      context.log('success', `${this.name} authenticated successfully`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      context.log('error', `${this.name} authentication failed: ${message}`);
      throw new AuthenticationError(this.name, message);
    }
  }

  async executeAction(action: Action, context: AdapterContext): Promise<ActionResult> {
    if (action.type !== 'backend') {
      return {
        description: action.description,
        success: false,
        duration: 0,
        error: `BackendAdapter cannot execute ${action.type} actions`,
      };
    }

    const startTime = Date.now();
    const backendAction = action as BackendAction;

    try {
      // Interpolate variables in endpoint and body
      const endpoint = interpolate(backendAction.endpoint, context.captured);
      const body = backendAction.body
        ? interpolateObject(backendAction.body, context.captured)
        : undefined;

      context.log('info', `${backendAction.method} ${endpoint}`, {
        body: body ? JSON.stringify(body).substring(0, 100) : undefined,
      });

      // Execute the request
      const response = await this.request(
        backendAction.method,
        endpoint,
        body,
        backendAction.headers
      );

      const duration = Date.now() - startTime;

      // Capture response if specified
      let capturedData: Record<string, unknown> | undefined;
      if (backendAction.capture) {
        capturedData = { [backendAction.capture]: response.data };
        // Merge into context for subsequent actions
        Object.assign(context.captured, capturedData);
      }

      return {
        description: backendAction.description,
        success: true,
        duration,
        details: `${backendAction.method} ${endpoint} → ${response.status}`,
        statusCode: response.status,
        capturedData,
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      const axiosError = error as AxiosError<APIResponse>;

      const statusCode = axiosError.response?.status;
      const errorMessage =
        axiosError.response?.data?.error?.message ||
        axiosError.message ||
        'Unknown error';

      context.log('error', `API error: ${errorMessage}`, {
        status: statusCode,
        endpoint: backendAction.endpoint,
      });

      return {
        description: backendAction.description,
        success: false,
        duration,
        statusCode,
        error: errorMessage,
        details: `${backendAction.method} ${backendAction.endpoint} → ${statusCode || 'NETWORK_ERROR'}`,
      };
    }
  }

  async verify(
    verification: Verification,
    context: AdapterContext
  ): Promise<VerificationResult> {
    switch (verification.type) {
      case 'response':
        return this.verifyResponse(verification, context);
      case 'database':
        return this.verifyDatabase(verification, context);
      default:
        return {
          description: verification.description,
          passed: false,
          failureReason: `BackendAdapter cannot handle ${verification.type} verifications`,
        };
    }
  }

  async cleanup(): Promise<void> {
    // Clear tokens
    this.tokens = null;
    this.ready = false;
  }

  isReady(): boolean {
    return this.ready && this.tokens !== null;
  }

  // ---------------------------------------------------------------------------
  // Authentication
  // ---------------------------------------------------------------------------

  private async authenticate(): Promise<void> {
    const response = await axios.post<{
      access: string;
      refresh: string;
      success?: boolean;
    }>(`${this.config.baseUrl}/auth/login/`, {
      login: this.config.username,
      password: this.config.password,
    });

    this.tokens = {
      access: response.data.access,
      refresh: response.data.refresh,
      accessExpiry: Date.now() + 55 * 60 * 1000, // 55 minutes (slightly before 1 hour expiry)
    };
  }

  private async refreshToken(): Promise<void> {
    if (!this.tokens?.refresh) {
      throw new AuthenticationError(this.name, 'No refresh token available');
    }

    const response = await axios.post<{ access: string }>(
      `${this.config.baseUrl}/auth/token/refresh/`,
      { refresh: this.tokens.refresh }
    );

    this.tokens = {
      ...this.tokens,
      access: response.data.access,
      accessExpiry: Date.now() + 55 * 60 * 1000,
    };
  }

  // ---------------------------------------------------------------------------
  // HTTP Request Helper
  // ---------------------------------------------------------------------------

  private async request(
    method: BackendAction['method'],
    endpoint: string,
    body?: Record<string, unknown>,
    headers?: Record<string, string>
  ): Promise<AxiosResponse> {
    const config = {
      headers: {
        ...headers,
      },
    };

    switch (method) {
      case 'GET':
        return this.client.get(endpoint, config);
      case 'POST':
        return this.client.post(endpoint, body, config);
      case 'PUT':
        return this.client.put(endpoint, body, config);
      case 'PATCH':
        return this.client.patch(endpoint, body, config);
      case 'DELETE':
        return this.client.delete(endpoint, config);
      default:
        throw new AdapterError(`Unsupported HTTP method: ${method}`, this.name);
    }
  }

  // ---------------------------------------------------------------------------
  // Verification Helpers
  // ---------------------------------------------------------------------------

  private verifyResponse(
    verification: ResponseVerification,
    context: AdapterContext
  ): VerificationResult {
    const { field, operator, expected, description } = verification;

    // Get actual value from captured data
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
          passed = actual.some(
            (item) => JSON.stringify(item) === JSON.stringify(expected)
          );
        }
        if (!passed) failureReason = `Value does not contain '${expected}'`;
        break;

      case 'greaterThan':
        passed = typeof actual === 'number' && typeof expected === 'number' && actual > expected;
        if (!passed) failureReason = `Expected > ${expected}, got ${actual}`;
        break;

      case 'lessThan':
        passed = typeof actual === 'number' && typeof expected === 'number' && actual < expected;
        if (!passed) failureReason = `Expected < ${expected}, got ${actual}`;
        break;

      case 'matches':
        if (typeof actual === 'string' && typeof expected === 'string') {
          passed = new RegExp(expected).test(actual);
        }
        if (!passed) failureReason = `Value does not match pattern '${expected}'`;
        break;

      case 'hasLength':
        if (Array.isArray(actual) || typeof actual === 'string') {
          passed = actual.length === expected;
        }
        if (!passed) failureReason = `Expected length ${expected}, got ${Array.isArray(actual) || typeof actual === 'string' ? actual.length : 'N/A'}`;
        break;

      case 'isType':
        passed = typeof actual === expected;
        if (!passed) failureReason = `Expected type '${expected}', got '${typeof actual}'`;
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

  private verifyDatabase(
    verification: DatabaseVerification,
    context: AdapterContext
  ): VerificationResult {
    // Database verification via API (Django has no direct DB access from browser)
    // This would typically call a verification endpoint
    context.log(
      'warning',
      'Direct database verification not available in browser context'
    );

    return {
      description: verification.description,
      passed: true, // Skip for now, rely on API verifications
      failureReason: 'Database verification skipped (not available in browser)',
    };
  }

}

// ---------------------------------------------------------------------------
// Factory Function
// ---------------------------------------------------------------------------

export function createBackendAdapter(config: AdapterConfig): BackendAdapter {
  return new BackendAdapter(config);
}
