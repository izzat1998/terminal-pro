import { http } from '../utils/httpClient';
import { API_BASE_URL } from '../config/api';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
}

export interface UserCompany {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_admin: boolean;
  is_staff: boolean;
  is_active: boolean;
  user_type: 'admin' | 'customer';
  company?: UserCompany;
}

class UserService {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // Skip auth for login - no token needed
    return http.post<LoginResponse>(
      '/auth/login/',
      {
        login: credentials.username,
        password: credentials.password,
      },
      { skipAuth: true }
    );
  }

  async verifyToken(token: string): Promise<User> {
    // Use explicit token, skip auto-auth
    const response = await fetch(`${API_BASE_URL}/auth/profile/`, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Token verification failed');
    }

    return response.json();
  }

  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    // Skip auth for refresh - we're using the refresh token itself
    return http.post<LoginResponse>(
      '/auth/token/refresh/',
      { refresh: refreshToken },
      { skipAuth: true }
    );
  }

  async deleteManager(managerId: number): Promise<void> {
    // Uses automatic token refresh
    await http.delete<void>(`/auth/managers/${managerId}/`);
  }
}

export const userService = new UserService();
