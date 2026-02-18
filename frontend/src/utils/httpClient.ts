import { API_BASE_URL } from '../config/api';
import { getStorageItem, setStorageItem, removeStorageItem } from './storage';
import { ApiError, parseApiErrorResponse } from '../types/api';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function subscribeTokenRefresh(callback: (token: string) => void) {
  refreshSubscribers.push(callback);
}

function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
}

function onRefreshFailed() {
  refreshSubscribers = [];
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getStorageItem(REFRESH_TOKEN_KEY);

  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();

    setStorageItem(ACCESS_TOKEN_KEY, data.access);
    if (data.refresh) {
      setStorageItem(REFRESH_TOKEN_KEY, data.refresh);
    }

    return data.access;
  } catch {
    return null;
  }
}

function clearAuthAndRedirect() {
  removeStorageItem(ACCESS_TOKEN_KEY);
  removeStorageItem(REFRESH_TOKEN_KEY);

  // Redirect to login with current path as redirect query
  const currentPath = window.location.pathname + window.location.search;
  window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
}

export interface RequestConfig extends RequestInit {
  skipAuth?: boolean;
  isFormData?: boolean;
}

function isTokenError(errorData: unknown): boolean {
  if (!errorData || typeof errorData !== 'object') return false;
  const data = errorData as Record<string, unknown>;
  const error = data.error as Record<string, unknown> | undefined;
  const details = error?.details as Record<string, unknown> | undefined;
  // Check various token error formats
  if (data.code === 'token_not_valid') return true;
  if (error?.code === 'token_not_valid') return true;
  if (Array.isArray(details?.code) && details.code.includes('token_not_valid')) return true;
  if (data.detail === 'Данный токен недействителен для любого типа токена') return true;
  const detailStr = details?.detail;
  if (typeof detailStr === 'string' && detailStr.includes('Данный токен недействителен для любого типа токена')) return true;
  return false;
}

export async function httpRequest<T>(
  endpoint: string,
  options: RequestConfig = {}
): Promise<T> {
  const { skipAuth = false, isFormData = false, ...fetchOptions } = options;

  const token = getStorageItem(ACCESS_TOKEN_KEY);

  const headers: Record<string, string> = {};
  if (options.headers) {
    if (options.headers instanceof Headers) {
      options.headers.forEach((value, key) => { headers[key] = value; });
    } else if (Array.isArray(options.headers)) {
      options.headers.forEach(([key, value]) => { headers[key] = value; });
    } else {
      Object.assign(headers, options.headers);
    }
  }

  // Don't set Content-Type for FormData - browser will set it with boundary
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  if (!skipAuth && token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  });

  // Check if we need to handle token refresh
  // Either 401 status OR token error in response body
  let needsTokenRefresh = response.status === 401 && !skipAuth;

  // For non-401 errors, check if response body contains token error
  if (!response.ok && !needsTokenRefresh && !skipAuth) {
    const clonedResponse = response.clone();
    try {
      const errorData = await clonedResponse.json();
      if (isTokenError(errorData)) {
        needsTokenRefresh = true;
      }
    } catch {
      // Ignore JSON parse errors
    }
  }

  if (needsTokenRefresh) {
    if (isRefreshing) {
      // Wait for the ongoing refresh to complete
      return new Promise<T>((resolve, reject) => {
        subscribeTokenRefresh(async (newToken: string) => {
          try {
            headers['Authorization'] = `Bearer ${newToken}`;
            const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
              ...fetchOptions,
              headers,
            });

            if (!retryResponse.ok) {
              const apiError = await handleErrorResponse(retryResponse);
              reject(apiError);
            }

            resolve(await parseResponse<T>(retryResponse));
          } catch (error) {
            reject(error);
          }
        });
      });
    }

    isRefreshing = true;

    try {
      const newToken = await refreshAccessToken();

      if (newToken) {
        isRefreshing = false;
        onTokenRefreshed(newToken);

        // Retry original request with new token
        headers['Authorization'] = `Bearer ${newToken}`;
        const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
          ...fetchOptions,
          headers,
        });

        if (!retryResponse.ok) {
          const apiError = await handleErrorResponse(retryResponse);
          throw apiError;
        }

        return parseResponse<T>(retryResponse);
      } else {
        // Refresh failed - clear auth and redirect to login
        isRefreshing = false;
        onRefreshFailed();
        clearAuthAndRedirect();
        throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
      }
    } catch (error) {
      isRefreshing = false;
      onRefreshFailed();
      clearAuthAndRedirect();
      throw error;
    }
  }

  if (!response.ok) {
    const apiError = await handleErrorResponse(response);
    throw apiError;
  }

  return parseResponse<T>(response);
}

async function handleErrorResponse(response: Response): Promise<ApiError> {
  try {
    const errorData = await response.json();
    return parseApiErrorResponse(errorData, response.status);
  } catch {
    // Create user-friendly error messages based on HTTP status
    const statusMessages: Record<number, string> = {
      400: 'Неверный запрос. Проверьте введённые данные.',
      401: 'Требуется авторизация. Войдите в систему.',
      403: 'Доступ запрещён. У вас нет прав для этого действия.',
      404: 'Ресурс не найден. Возможно, он был удалён.',
      408: 'Время ожидания истекло. Попробуйте снова.',
      429: 'Слишком много запросов. Подождите немного.',
      500: 'Ошибка сервера. Попробуйте позже или свяжитесь с поддержкой.',
      502: 'Сервер временно недоступен. Попробуйте позже.',
      503: 'Сервер на обслуживании. Попробуйте позже.',
      504: 'Сервер не отвечает. Проверьте подключение к сети.',
    };

    const message = statusMessages[response.status] ||
      `Ошибка соединения (код ${response.status}). Попробуйте позже.`;

    return new ApiError(
      message,
      'UNKNOWN_ERROR',
      null,
      new Date().toISOString(),
      response.status
    );
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type');

  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }

  // Non-JSON responses (e.g. 204 No Content) — return empty object as T
  // This is safe for our API where non-JSON success responses are empty
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return {} as T;
  }

  throw new ApiError(
    `Неожиданный формат ответа: ${contentType || 'unknown'}`,
    'UNKNOWN_ERROR',
    null,
    new Date().toISOString(),
    response.status,
  );
}

// Convenience methods
export const http = {
  get<T>(endpoint: string, options?: RequestConfig): Promise<T> {
    return httpRequest<T>(endpoint, { ...options, method: 'GET' });
  },

  post<T>(endpoint: string, body?: unknown, options?: RequestConfig): Promise<T> {
    return httpRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  put<T>(endpoint: string, body?: unknown, options?: RequestConfig): Promise<T> {
    return httpRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  patch<T>(endpoint: string, body?: unknown, options?: RequestConfig): Promise<T> {
    return httpRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  delete<T>(endpoint: string, options?: RequestConfig): Promise<T> {
    return httpRequest<T>(endpoint, { ...options, method: 'DELETE' });
  },

  // Upload FormData (for file uploads)
  upload<T>(endpoint: string, formData: FormData, options?: RequestConfig): Promise<T> {
    return httpRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: formData,
      isFormData: true,
    });
  },
};

/**
 * Download a file from an authenticated API endpoint.
 * Uses fetch with JWT Authorization header, then triggers a browser download
 * via a temporary Blob URL + anchor element click.
 */
export async function downloadFile(endpoint: string, filename: string): Promise<void> {
  const token = getStorageItem(ACCESS_TOKEN_KEY);

  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, { headers });

  if (!response.ok) {
    throw new Error(`Ошибка загрузки файла (${response.status})`);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(objectUrl);
}
