/**
 * Centralized API response and error types
 * Matches backend apps/core/exceptions.py format
 */

// Standard success response wrapper
export interface ApiResponse<T> {
  success: true;
  data: T;
  message?: string;
}

// Standard paginated response from DRF
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Standard error response from backend
export interface ApiErrorResponse {
  success: false;
  error: {
    code: ApiErrorCode;
    message: string;
    details?: FieldErrors;
  };
  timestamp: string;
}

// Field-level validation errors: { field_name: ["error1", "error2"] }
export interface FieldErrors {
  [fieldName: string]: string[];
}

// Error codes from backend (apps/core/exceptions.py)
export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'PERMISSION_DENIED'
  | 'AUTHENTICATION_REQUIRED'
  | 'AUTHENTICATION_FAILED'
  | 'NOT_FOUND'
  | 'METHOD_NOT_ALLOWED'
  | 'PARSE_ERROR'
  | 'UNSUPPORTED_MEDIA_TYPE'
  | 'RATE_LIMIT_EXCEEDED'
  | 'BUSINESS_ERROR'
  | 'CONTAINER_NOT_FOUND'
  | 'DUPLICATE_ENTRY'
  | 'INVALID_CONTAINER_STATE'
  | 'INTERNAL_ERROR'
  | 'UNKNOWN_ERROR';

/**
 * Custom API error class that preserves field-level errors
 *
 * Usage:
 * ```ts
 * try {
 *   await http.post('/api/...', data);
 * } catch (error) {
 *   if (error instanceof ApiError) {
 *     // Access field errors for form integration
 *     console.log(error.fieldErrors); // { license_plate: ["Уже существует"] }
 *     console.log(error.code);        // "VALIDATION_ERROR"
 *     console.log(error.message);     // "Ошибка валидации"
 *   }
 * }
 * ```
 */
export class ApiError extends Error {
  public readonly code: ApiErrorCode;
  public readonly fieldErrors: FieldErrors | null;
  public readonly timestamp: string;
  public readonly statusCode: number;

  constructor(
    message: string,
    code: ApiErrorCode,
    fieldErrors: FieldErrors | null = null,
    timestamp: string = new Date().toISOString(),
    statusCode: number = 400
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.fieldErrors = fieldErrors;
    this.timestamp = timestamp;
    this.statusCode = statusCode;
  }

  /**
   * Check if this is a validation error with field-specific errors
   */
  hasFieldErrors(): boolean {
    return this.code === 'VALIDATION_ERROR' && this.fieldErrors !== null;
  }

  /**
   * Get errors for a specific field
   */
  getFieldError(fieldName: string): string | null {
    if (!this.fieldErrors || !this.fieldErrors[fieldName]) {
      return null;
    }
    return this.fieldErrors[fieldName][0] ?? null;
  }

  /**
   * Get all field errors as a flat object (first error per field)
   * Useful for Ant Design form.setFields()
   */
  getFieldErrorsFlat(): Record<string, string> {
    if (!this.fieldErrors) return {};

    const flat: Record<string, string> = {};
    for (const [field, errors] of Object.entries(this.fieldErrors)) {
      const firstError = errors[0];
      if (firstError) {
        flat[field] = firstError;
      }
    }
    return flat;
  }
}

/**
 * Type guard to check if an error is an ApiError
 */
export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

/**
 * Parse raw API error response into ApiError
 */
export function parseApiErrorResponse(
  responseData: unknown,
  statusCode: number = 400
): ApiError {
  // Handle our standard error format
  if (
    typeof responseData === 'object' &&
    responseData !== null &&
    'success' in responseData &&
    (responseData as ApiErrorResponse).success === false
  ) {
    const errorResponse = responseData as ApiErrorResponse;
    return new ApiError(
      errorResponse.error.message,
      errorResponse.error.code,
      errorResponse.error.details || null,
      errorResponse.timestamp,
      statusCode
    );
  }

  // Handle DRF default format (non_field_errors, detail)
  if (typeof responseData === 'object' && responseData !== null) {
    const data = responseData as Record<string, unknown>;

    if ('non_field_errors' in data) {
      const errors = data.non_field_errors as string[];
      const firstError = errors[0] ?? 'Ошибка валидации';
      return new ApiError(
        firstError,
        'VALIDATION_ERROR',
        { non_field_errors: errors },
        new Date().toISOString(),
        statusCode
      );
    }

    if ('detail' in data && typeof data.detail === 'string') {
      return new ApiError(
        data.detail,
        'UNKNOWN_ERROR',
        null,
        new Date().toISOString(),
        statusCode
      );
    }

    // Assume it's field errors: { field: ["error"] }
    const fieldErrors: FieldErrors = {};
    let firstMessage = 'Произошла ошибка';

    for (const [key, value] of Object.entries(data)) {
      if (Array.isArray(value)) {
        fieldErrors[key] = value.map(String);
        if (firstMessage === 'Произошла ошибка' && value.length > 0) {
          firstMessage = String(value[0]);
        }
      }
    }

    if (Object.keys(fieldErrors).length > 0) {
      return new ApiError(
        firstMessage,
        'VALIDATION_ERROR',
        fieldErrors,
        new Date().toISOString(),
        statusCode
      );
    }
  }

  // Fallback
  return new ApiError(
    'Произошла неизвестная ошибка',
    'UNKNOWN_ERROR',
    null,
    new Date().toISOString(),
    statusCode
  );
}
