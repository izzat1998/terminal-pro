import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { httpRequest, http, downloadFile } from '../httpClient';
import * as storage from '../storage';
import { API_BASE_URL } from '../../config/api';

// Mock modules
vi.mock('../storage');

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('httpClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(storage.getStorageItem).mockReturnValue(null);
    vi.mocked(storage.setStorageItem).mockImplementation(() => {});
    vi.mocked(storage.removeStorageItem).mockImplementation(() => {});

    // Mock window.location.href
    delete (window as { location?: unknown }).location;
    window.location = { href: '' } as Location;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('basic requests', () => {
    it('should make GET request with auth token', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem).mockReturnValue('valid-token');
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ data: 'test' }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      // Act
      await http.get('/test');

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/test`,
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            Authorization: 'Bearer valid-token',
          }),
        })
      );
    });

    it('should make POST request with JSON body', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem).mockReturnValue('valid-token');
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const body = { name: 'test' };

      // Act
      await http.post('/test', body);

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/test`,
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(body),
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('should skip auth when skipAuth is true', async () => {
      // Arrange
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ data: 'test' }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      // Act
      await httpRequest('/test', { skipAuth: true });

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/test`,
        expect.objectContaining({
          headers: expect.not.objectContaining({
            Authorization: expect.anything(),
          }),
        })
      );
    });

    it('should handle FormData upload', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem).mockReturnValue('valid-token');
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const formData = new FormData();
      formData.append('file', new Blob(['test']), 'test.txt');

      // Act
      await http.upload('/upload', formData);

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/upload`,
        expect.objectContaining({
          method: 'POST',
          body: formData,
          headers: expect.not.objectContaining({
            'Content-Type': expect.anything(),
          }),
        })
      );
    });
  });

  describe('token refresh logic', () => {
    it('should refresh token on 401 response', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem)
        .mockReturnValueOnce('expired-token') // First call - access token
        .mockReturnValueOnce('valid-refresh-token'); // Second call - refresh token

      // First request fails with 401
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Token expired' }),
        })
        // Token refresh succeeds
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            access: 'new-access-token',
            refresh: 'new-refresh-token',
          }),
          headers: new Headers({ 'content-type': 'application/json' }),
        })
        // Retry original request succeeds
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ data: 'success' }),
          headers: new Headers({ 'content-type': 'application/json' }),
        });

      // Act
      const result = await http.get('/test');

      // Assert
      expect(result).toEqual({ data: 'success' });
      expect(storage.setStorageItem).toHaveBeenCalledWith('access_token', 'new-access-token');
      expect(storage.setStorageItem).toHaveBeenCalledWith('refresh_token', 'new-refresh-token');
      expect(mockFetch).toHaveBeenCalledTimes(3); // Original + refresh + retry
    });

    it('should refresh token on token_not_valid error in response body', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem)
        .mockReturnValueOnce('expired-token')
        .mockReturnValueOnce('valid-refresh-token');

      const errorResponse = {
        ok: false,
        status: 400,
        json: async () => ({
          success: false,
          error: { code: 'token_not_valid', message: 'Token invalid' },
        }),
        clone: function () {
          return {
            ...this,
            json: async () => ({
              success: false,
              error: { code: 'token_not_valid', message: 'Token invalid' },
            }),
          };
        },
      };

      // First request returns 400 with token error
      mockFetch
        .mockResolvedValueOnce(errorResponse)
        // Token refresh succeeds
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            access: 'new-access-token',
            refresh: 'new-refresh-token',
          }),
          headers: new Headers({ 'content-type': 'application/json' }),
        })
        // Retry succeeds
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ data: 'success' }),
          headers: new Headers({ 'content-type': 'application/json' }),
        });

      // Act
      const result = await http.get('/test');

      // Assert
      expect(result).toEqual({ data: 'success' });
      expect(storage.setStorageItem).toHaveBeenCalledWith('access_token', 'new-access-token');
    });

    it('should redirect to login when refresh fails', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem)
        .mockReturnValueOnce('expired-token')
        .mockReturnValueOnce('invalid-refresh-token');

      // First request fails with 401
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Token expired' }),
        })
        // Token refresh fails
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Invalid refresh token' }),
        });

      // Act & Assert
      await expect(http.get('/test')).rejects.toThrow('Сессия истекла. Пожалуйста, войдите снова.');
      expect(storage.removeStorageItem).toHaveBeenCalledWith('access_token');
      expect(storage.removeStorageItem).toHaveBeenCalledWith('refresh_token');
      expect(window.location.href).toContain('/login');
    });

    it('should queue concurrent requests during token refresh', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem)
        .mockReturnValue('expired-token') // access token
        .mockReturnValueOnce('valid-refresh-token'); // refresh token for first call

      let refreshCallCount = 0;
      // Track per-URL call counts so first call returns 401, retry returns success
      const urlCallCounts: Record<string, number> = {};

      mockFetch.mockImplementation((url: string) => {
        urlCallCounts[url] = (urlCallCounts[url] || 0) + 1;

        // Token refresh endpoint
        if (url.includes('/token/refresh/')) {
          refreshCallCount++;
          return Promise.resolve({
            ok: true,
            json: async () => ({
              access: 'new-access-token',
              refresh: 'new-refresh-token',
            }),
            headers: new Headers({ 'content-type': 'application/json' }),
          });
        }

        // For test endpoints: first call returns 401, subsequent calls succeed
        if (urlCallCounts[url] === 1) {
          return Promise.resolve({
            ok: false,
            status: 401,
            json: async () => ({ detail: 'Token expired' }),
          });
        }

        // Successful retry
        return Promise.resolve({
          ok: true,
          json: async () => ({ data: 'success' }),
          headers: new Headers({ 'content-type': 'application/json' }),
        });
      });

      // Act - make two concurrent requests
      const [result1, result2] = await Promise.all([http.get('/test1'), http.get('/test2')]);

      // Assert - should only refresh once
      expect(result1).toEqual({ data: 'success' });
      expect(result2).toEqual({ data: 'success' });
      expect(refreshCallCount).toBe(1); // Only one refresh call despite two concurrent requests
    });

    it('should clear auth and redirect when no refresh token available', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem).mockReturnValue(null); // No refresh token

      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Token expired' }),
      });

      // Act & Assert
      await expect(http.get('/test')).rejects.toThrow();
      expect(storage.removeStorageItem).toHaveBeenCalled();
      expect(window.location.href).toContain('/login');
    });
  });

  describe('error handling', () => {
    it('should throw ApiError for 400 response', async () => {
      // Arrange
      const errorData = {
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Ошибка валидации',
          details: { name: ['Это поле обязательно'] },
        },
        timestamp: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => errorData,
        clone: function () {
          return {
            ...this,
            json: async () => errorData,
          };
        },
      });

      // Act & Assert
      await expect(http.get('/test')).rejects.toThrow('Ошибка валидации');
    });

    it('should provide user-friendly messages for network errors', async () => {
      // Arrange
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Invalid JSON');
        },
        clone: function () {
          return this;
        },
      });

      // Act & Assert
      await expect(http.get('/test')).rejects.toThrow(
        'Ошибка сервера. Попробуйте позже или свяжитесь с поддержкой.'
      );
    });

    it('should handle 404 not found', async () => {
      // Arrange
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => {
          throw new Error('Invalid JSON');
        },
        clone: function () {
          return this;
        },
      });

      // Act & Assert
      await expect(http.get('/test')).rejects.toThrow(
        'Ресурс не найден. Возможно, он был удалён.'
      );
    });
  });

  describe('HTTP methods', () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
    });

    it('should support PUT method', async () => {
      // Act
      await http.put('/test', { data: 'test' });

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: 'PUT' })
      );
    });

    it('should support PATCH method', async () => {
      // Act
      await http.patch('/test', { data: 'test' });

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: 'PATCH' })
      );
    });

    it('should support DELETE method', async () => {
      // Act
      await http.delete('/test');

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });

  describe('response parsing', () => {
    it('should parse JSON response', async () => {
      // Arrange
      const jsonData = { data: 'test', nested: { value: 123 } };
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => jsonData,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      // Act
      const result = await http.get('/test');

      // Assert
      expect(result).toEqual(jsonData);
    });

    it('should handle non-JSON response', async () => {
      // Arrange
      mockFetch.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'text/plain' }),
      });

      // Act
      const result = await http.get('/test');

      // Assert
      expect(result).toBeUndefined();
    });

    it('should handle 204 No Content response gracefully', async () => {
      // Arrange
      mockFetch.mockResolvedValue({
        ok: true,
        status: 204,
        headers: new Headers({}),
      });

      // Act
      const result = await http.delete('/test/1');

      // Assert - 204 has no content-type, should return undefined
      expect(result).toBeUndefined();
    });

    it('should handle empty response body with JSON content-type', async () => {
      // Arrange
      mockFetch.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({}),
      });

      // Act
      const result = await http.get('/test');

      // Assert
      expect(result).toEqual({});
    });
  });

  describe('downloadFile', () => {
    let createElementSpy: ReturnType<typeof vi.spyOn>;
    let appendChildSpy: ReturnType<typeof vi.spyOn>;
    let removeChildSpy: ReturnType<typeof vi.spyOn>;
    let createObjectURLSpy: ReturnType<typeof vi.spyOn>;
    let revokeObjectURLSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn(),
      } as unknown as HTMLAnchorElement;

      createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink);
      appendChildSpy = vi.spyOn(document.body, 'appendChild').mockReturnValue(mockLink);
      removeChildSpy = vi.spyOn(document.body, 'removeChild').mockReturnValue(mockLink);
      createObjectURLSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:http://localhost/fake-blob-url');
      revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    });

    afterEach(() => {
      createElementSpy.mockRestore();
      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
      createObjectURLSpy.mockRestore();
      revokeObjectURLSpy.mockRestore();
    });

    it('should download file with Authorization header', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem).mockReturnValue('valid-token');
      const mockBlob = new Blob(['file content'], { type: 'application/pdf' });
      mockFetch.mockResolvedValue({
        ok: true,
        blob: async () => mockBlob,
      });

      // Act
      await downloadFile('/billing/export/report.pdf', 'report.pdf');

      // Assert - verify Authorization header is set
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/billing/export/report.pdf`,
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer valid-token',
          }),
        })
      );
    });

    it('should create blob URL, click link, and clean up', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem).mockReturnValue('valid-token');
      const mockBlob = new Blob(['file content']);
      mockFetch.mockResolvedValue({
        ok: true,
        blob: async () => mockBlob,
      });

      // Act
      await downloadFile('/export/data.xlsx', 'data.xlsx');

      // Assert - verify download flow
      expect(createObjectURLSpy).toHaveBeenCalledWith(mockBlob);
      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(appendChildSpy).toHaveBeenCalled();
      expect(removeChildSpy).toHaveBeenCalled();
      expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:http://localhost/fake-blob-url');
    });

    it('should throw error for non-ok response', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem).mockReturnValue('valid-token');
      mockFetch.mockResolvedValue({
        ok: false,
        status: 403,
      });

      // Act & Assert
      await expect(downloadFile('/export/secret.pdf', 'secret.pdf')).rejects.toThrow(
        'Ошибка загрузки файла (403)'
      );
    });

    it('should work without auth token', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem).mockReturnValue(null);
      const mockBlob = new Blob(['content']);
      mockFetch.mockResolvedValue({
        ok: true,
        blob: async () => mockBlob,
      });

      // Act
      await downloadFile('/public/file.pdf', 'file.pdf');

      // Assert - no Authorization header
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/public/file.pdf`,
        expect.objectContaining({
          headers: expect.not.objectContaining({
            Authorization: expect.anything(),
          }),
        })
      );
    });
  });
});
