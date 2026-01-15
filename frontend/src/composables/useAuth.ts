import { ref, computed } from 'vue';
import { userService, type User, type LoginRequest } from '../services/userService';
import { getCookie, setCookie, deleteCookie } from '../utils/storage';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

const user = ref<User | null>(null);
const accessToken = ref<string | null>(getCookie(ACCESS_TOKEN_KEY));
const refreshToken = ref<string | null>(getCookie(REFRESH_TOKEN_KEY));
const loading = ref(false);
const error = ref<string | null>(null);

function parseJwt(token: string): { exp?: number } | null {
  try {
    const base64Url = token.split('.')[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function isTokenExpired(token: string, bufferSeconds = 60): boolean {
  const payload = parseJwt(token);
  if (!payload || !payload.exp) return true;
  const now = Math.floor(Date.now() / 1000);
  return payload.exp < now + bufferSeconds;
}

export function useAuth() {
  const isAuthenticated = computed(() => !!user.value && !!accessToken.value);

  async function login(credentials: LoginRequest) {
    try {
      loading.value = true;
      error.value = null;

      const response = await userService.login(credentials);
      accessToken.value = response.access;
      refreshToken.value = response.refresh;
      setCookie(ACCESS_TOKEN_KEY, response.access);
      setCookie(REFRESH_TOKEN_KEY, response.refresh);

      // Verify token and get user data
      const userData = await userService.verifyToken(response.access);

      // Check if user is active
      if (!userData.is_active) {
        error.value = 'Ваш аккаунт деактивирован';
        accessToken.value = null;
        refreshToken.value = null;
        user.value = null;
        deleteCookie(ACCESS_TOKEN_KEY);
        deleteCookie(REFRESH_TOKEN_KEY);
        return false;
      }

      user.value = userData;

      return true;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Ошибка входа. Проверьте учётные данные и попробуйте снова.';
      accessToken.value = null;
      refreshToken.value = null;
      user.value = null;
      deleteCookie(ACCESS_TOKEN_KEY);
      deleteCookie(REFRESH_TOKEN_KEY);
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function verifyCurrentToken() {
    if (!accessToken.value) {
      user.value = null;
      return false;
    }

    try {
      loading.value = true;
      const userData = await userService.verifyToken(accessToken.value);

      // Check if user is active
      if (!userData.is_active) {
        // User is not active, logout immediately
        accessToken.value = null;
        refreshToken.value = null;
        user.value = null;
        deleteCookie(ACCESS_TOKEN_KEY);
        deleteCookie(REFRESH_TOKEN_KEY);
        return false;
      }

      user.value = userData;
      return true;
    } catch (err) {
      // Token verification failed, try to refresh it
      if (refreshToken.value) {
        try {
          const response = await userService.refreshToken(refreshToken.value);

          // Update tokens
          accessToken.value = response.access;
          refreshToken.value = response.refresh;
          setCookie(ACCESS_TOKEN_KEY, response.access);
          setCookie(REFRESH_TOKEN_KEY, response.refresh);

          // Verify the new token and get user data
          const userData = await userService.verifyToken(response.access);

          // Check if user is active
          if (!userData.is_active) {
            accessToken.value = null;
            refreshToken.value = null;
            user.value = null;
            deleteCookie(ACCESS_TOKEN_KEY);
            deleteCookie(REFRESH_TOKEN_KEY);
            return false;
          }

          user.value = userData;
          return true;
        } catch (refreshErr) {
          // Refresh failed, clear all tokens
          accessToken.value = null;
          refreshToken.value = null;
          user.value = null;
          deleteCookie(ACCESS_TOKEN_KEY);
          deleteCookie(REFRESH_TOKEN_KEY);
          return false;
        }
      }

      // No refresh token available, clear all tokens
      accessToken.value = null;
      refreshToken.value = null;
      user.value = null;
      deleteCookie(ACCESS_TOKEN_KEY);
      deleteCookie(REFRESH_TOKEN_KEY);
      return false;
    } finally {
      loading.value = false;
    }
  }

  function logout() {
    user.value = null;
    accessToken.value = null;
    refreshToken.value = null;
    deleteCookie(ACCESS_TOKEN_KEY);
    deleteCookie(REFRESH_TOKEN_KEY);
  }

  async function checkAndRefreshToken(): Promise<boolean> {
    if (!accessToken.value) {
      return false;
    }

    // If token is not expired, return true
    if (!isTokenExpired(accessToken.value)) {
      // If we have token but no user data, fetch it
      if (!user.value) {
        return verifyCurrentToken();
      }
      return true;
    }

    // Token is expired, try to refresh
    if (!refreshToken.value) {
      logout();
      return false;
    }

    try {
      const response = await userService.refreshToken(refreshToken.value);

      accessToken.value = response.access;
      refreshToken.value = response.refresh;
      setCookie(ACCESS_TOKEN_KEY, response.access);
      setCookie(REFRESH_TOKEN_KEY, response.refresh);

      // Fetch user data with new token
      const userData = await userService.verifyToken(response.access);

      if (!userData.is_active) {
        logout();
        return false;
      }

      user.value = userData;
      return true;
    } catch {
      logout();
      return false;
    }
  }

  return {
    user: computed(() => user.value),
    accessToken: computed(() => accessToken.value),
    refreshToken: computed(() => refreshToken.value),
    loading: computed(() => loading.value),
    error: computed(() => error.value),
    isAuthenticated,
    login,
    logout,
    verifyCurrentToken,
    checkAndRefreshToken,
  };
}
