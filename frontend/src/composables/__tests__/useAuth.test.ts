import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuth } from '../useAuth';
import { userService } from '../../services/userService';
import type { User, LoginResponse } from '../../services/userService';
import * as storage from '../../utils/storage';

// Mock modules
vi.mock('../../services/userService');
vi.mock('../../utils/storage');

describe('useAuth', () => {
  const mockUser: User = {
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
    is_admin: false,
    is_staff: false,
    is_active: true,
    user_type: 'customer',
  };

  const mockLoginResponse: LoginResponse = {
    access: 'mock-access-token',
    refresh: 'mock-refresh-token',
  };

  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks();

    // Reset module-level composable state to avoid cross-test contamination
    const auth = useAuth();
    auth.logout();
    vi.clearAllMocks(); // Clear again after logout to reset removeStorageItem calls

    // Setup default mock implementations
    vi.mocked(storage.getStorageItem).mockReturnValue(null);
    vi.mocked(storage.setStorageItem).mockImplementation(() => {});
    vi.mocked(storage.removeStorageItem).mockImplementation(() => {});
  });

  describe('login', () => {
    it('should successfully login with valid credentials', async () => {
      // Arrange
      vi.mocked(userService.login).mockResolvedValue(mockLoginResponse);
      vi.mocked(userService.verifyToken).mockResolvedValue(mockUser);

      const auth = useAuth();

      // Act
      const result = await auth.login({ username: 'testuser', password: 'password123' });

      // Assert
      expect(result).toBe(true);
      expect(auth.user.value).toEqual(mockUser);
      expect(auth.accessToken.value).toBe('mock-access-token');
      expect(auth.refreshToken.value).toBe('mock-refresh-token');
      expect(auth.isAuthenticated.value).toBe(true);
      expect(storage.setStorageItem).toHaveBeenCalledWith('access_token', 'mock-access-token');
      expect(storage.setStorageItem).toHaveBeenCalledWith('refresh_token', 'mock-refresh-token');
    });

    it('should reject login for inactive user', async () => {
      // Arrange
      const inactiveUser = { ...mockUser, is_active: false };
      vi.mocked(userService.login).mockResolvedValue(mockLoginResponse);
      vi.mocked(userService.verifyToken).mockResolvedValue(inactiveUser);

      const auth = useAuth();

      // Act
      const result = await auth.login({ username: 'testuser', password: 'password123' });

      // Assert
      expect(result).toBe(false);
      expect(auth.error.value).toBe('Ваш аккаунт деактивирован');
      expect(storage.removeStorageItem).toHaveBeenCalledWith('access_token');
      expect(storage.removeStorageItem).toHaveBeenCalledWith('refresh_token');
    });

    it('should handle login failure', async () => {
      // Arrange
      vi.mocked(userService.login).mockRejectedValue(new Error('Invalid credentials'));

      const auth = useAuth();

      // Act
      const result = await auth.login({ username: 'testuser', password: 'wrong' });

      // Assert
      expect(result).toBe(false);
      expect(auth.error.value).toBe('Invalid credentials');
      expect(storage.removeStorageItem).toHaveBeenCalled();
    });

    it('should set loading state during login', async () => {
      // Arrange
      vi.mocked(userService.login).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockLoginResponse), 100))
      );
      vi.mocked(userService.verifyToken).mockResolvedValue(mockUser);

      const auth = useAuth();

      // Act
      const loginPromise = auth.login({ username: 'testuser', password: 'password123' });
      expect(auth.loading.value).toBe(true);

      await loginPromise;

      // Assert
      expect(auth.loading.value).toBe(false);
    });
  });

  describe('logout', () => {
    it('should clear all auth data', () => {
      // Arrange
      const auth = useAuth();

      // Act
      auth.logout();

      // Assert
      expect(storage.removeStorageItem).toHaveBeenCalledWith('access_token');
      expect(storage.removeStorageItem).toHaveBeenCalledWith('refresh_token');
    });
  });

  describe('verifyCurrentToken', () => {
    it('should return false when no token exists', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem).mockReturnValue(null);

      const auth = useAuth();

      // Act
      const result = await auth.verifyCurrentToken();

      // Assert
      expect(result).toBe(false);
    });

    it('should attempt token refresh when verification fails', async () => {
      // Arrange - first login to set internal accessToken.value
      const auth = useAuth();
      vi.mocked(userService.login).mockResolvedValue(mockLoginResponse);
      vi.mocked(userService.verifyToken).mockResolvedValueOnce(mockUser);
      await auth.login({ username: 'testuser', password: 'password123' });
      vi.clearAllMocks();

      // Now set up the verification failure + refresh scenario
      vi.mocked(storage.getStorageItem).mockReturnValue('valid-refresh-token');
      vi.mocked(storage.setStorageItem).mockImplementation(() => {});
      vi.mocked(storage.removeStorageItem).mockImplementation(() => {});

      vi.mocked(userService.verifyToken)
        .mockRejectedValueOnce(new Error('Token expired'))
        .mockResolvedValueOnce(mockUser);

      vi.mocked(userService.refreshToken).mockResolvedValue({
        access: 'new-access-token',
        refresh: 'new-refresh-token',
      });

      // Act
      const result = await auth.verifyCurrentToken();

      // Assert
      expect(result).toBe(true);
      expect(userService.refreshToken).toHaveBeenCalled();
      expect(storage.setStorageItem).toHaveBeenCalledWith('access_token', 'new-access-token');
      expect(storage.setStorageItem).toHaveBeenCalledWith('refresh_token', 'new-refresh-token');
    });
  });

  describe('checkAndRefreshToken', () => {
    it('should return false when no access token exists', async () => {
      // Arrange
      vi.mocked(storage.getStorageItem).mockReturnValue(null);

      const auth = useAuth();

      // Act
      const result = await auth.checkAndRefreshToken();

      // Assert
      expect(result).toBe(false);
    });

    it('should refresh expired token', async () => {
      // Arrange - create an expired token and set it via login
      const pastTimestamp = Math.floor(Date.now() / 1000) - 3600; // 1 hour ago
      const payload = { exp: pastTimestamp };
      const base64Payload = btoa(JSON.stringify(payload));
      const expiredToken = `header.${base64Payload}.signature`;

      // First, login to set internal accessToken.value to the expired token
      const auth = useAuth();
      vi.mocked(userService.login).mockResolvedValue({ access: expiredToken, refresh: 'valid-refresh-token' });
      vi.mocked(userService.verifyToken).mockResolvedValueOnce(mockUser);
      await auth.login({ username: 'test', password: 'test' });
      vi.clearAllMocks();

      // Now set up mocks for the refresh flow
      vi.mocked(storage.getStorageItem).mockReturnValue(null);
      vi.mocked(storage.setStorageItem).mockImplementation(() => {});
      vi.mocked(storage.removeStorageItem).mockImplementation(() => {});
      vi.mocked(userService.refreshToken).mockResolvedValue({
        access: 'new-access-token',
        refresh: 'new-refresh-token',
      });
      vi.mocked(userService.verifyToken).mockResolvedValue(mockUser);

      // Act
      const result = await auth.checkAndRefreshToken();

      // Assert
      expect(result).toBe(true);
      expect(userService.refreshToken).toHaveBeenCalledWith('valid-refresh-token');
    });

    it('should logout when refresh fails', async () => {
      // Arrange - create an expired token and set it via login
      const pastTimestamp = Math.floor(Date.now() / 1000) - 3600;
      const payload = { exp: pastTimestamp };
      const base64Payload = btoa(JSON.stringify(payload));
      const expiredToken = `header.${base64Payload}.signature`;

      // First, login to set internal state
      const auth = useAuth();
      vi.mocked(userService.login).mockResolvedValue({ access: expiredToken, refresh: 'invalid-refresh-token' });
      vi.mocked(userService.verifyToken).mockResolvedValueOnce(mockUser);
      await auth.login({ username: 'test', password: 'test' });
      vi.clearAllMocks();

      // Now set up mocks for the failed refresh flow
      vi.mocked(storage.getStorageItem).mockReturnValue(null);
      vi.mocked(storage.setStorageItem).mockImplementation(() => {});
      vi.mocked(storage.removeStorageItem).mockImplementation(() => {});
      vi.mocked(userService.refreshToken).mockRejectedValue(new Error('Refresh failed'));

      // Act
      const result = await auth.checkAndRefreshToken();

      // Assert
      expect(result).toBe(false);
      expect(storage.removeStorageItem).toHaveBeenCalled();
    });
  });

  describe('isAuthenticated computed', () => {
    it('should be true when user and token exist', async () => {
      // Arrange
      vi.mocked(userService.login).mockResolvedValue(mockLoginResponse);
      vi.mocked(userService.verifyToken).mockResolvedValue(mockUser);

      const auth = useAuth();

      // Act
      await auth.login({ username: 'testuser', password: 'password123' });

      // Assert
      expect(auth.isAuthenticated.value).toBe(true);
    });
  });

  describe('error handling', () => {
    it('should handle non-Error thrown during login', async () => {
      // Arrange - service throws a string instead of Error
      vi.mocked(userService.login).mockRejectedValue('network failure');

      const auth = useAuth();

      // Act
      const result = await auth.login({ username: 'testuser', password: 'wrong' });

      // Assert - should fall back to generic message
      expect(result).toBe(false);
      expect(auth.error.value).toBe('Ошибка входа. Проверьте учётные данные и попробуйте снова.');
      expect(auth.user.value).toBeNull();
    });

    it('should clear tokens when verifyToken fails during login', async () => {
      // Arrange - login succeeds but token verification throws
      vi.mocked(userService.login).mockResolvedValue(mockLoginResponse);
      vi.mocked(userService.verifyToken).mockRejectedValue(new Error('Server error'));

      const auth = useAuth();

      // Act
      const result = await auth.login({ username: 'testuser', password: 'password123' });

      // Assert
      expect(result).toBe(false);
      expect(auth.error.value).toBe('Server error');
      expect(auth.accessToken.value).toBeNull();
      expect(auth.refreshToken.value).toBeNull();
      expect(storage.removeStorageItem).toHaveBeenCalledWith('access_token');
      expect(storage.removeStorageItem).toHaveBeenCalledWith('refresh_token');
    });

    it('should return false from verifyCurrentToken when no internal token is set', async () => {
      // Arrange - state is clean from beforeEach, no login performed
      const auth = useAuth();

      // Act - accessToken.value is null, so returns false immediately
      const result = await auth.verifyCurrentToken();

      // Assert
      expect(result).toBe(false);
    });

    it('should return false from checkAndRefreshToken when no tokens exist', async () => {
      // Arrange - state is clean from beforeEach
      const auth = useAuth();

      // Act - no accessToken.value means immediate false
      const result = await auth.checkAndRefreshToken();

      // Assert
      expect(result).toBe(false);
    });
  });
});
