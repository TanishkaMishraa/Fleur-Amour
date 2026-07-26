/**
 * AuraFit — Auth API calls (Stage 3).
 * Thin wrappers over apiClient. Typed with Stage 3 response envelopes.
 * Covers: register, login (+ MFA), OAuth, token refresh, password reset.
 */
import { apiClient } from "./client";
import type { User, UserProfile, UserPreferences, ApiResponse } from "@/types";

interface TokenResponse   { access_token: string; token_type: string; expires_in: number; }
interface MeResponse      { user: User; profile: UserProfile | null; preferences: UserPreferences | null; }
interface RegisterRequest { email: string; password: string; full_name: string; }
interface LoginRequest    { email: string; password: string; mfa_code?: string; }

export const authApi = {
  register: (data: RegisterRequest) =>
    apiClient.post<ApiResponse<User>>("/auth/register", data),

  login: (data: LoginRequest) =>
    apiClient.post<ApiResponse<TokenResponse>>("/auth/login", data),

  logout: () =>
    apiClient.post<void>("/auth/logout"),

  refresh: () =>
    apiClient.post<ApiResponse<TokenResponse & { new_refresh_token?: string }>>("/auth/refresh"),

  getMe: () =>
    apiClient.get<ApiResponse<MeResponse>>("/users/me"),

  updateMe: (data: Partial<Pick<User, "full_name" | "avatar_url">>) =>
    apiClient.patch<ApiResponse<User>>("/users/me", data),

  forgotPassword: (email: string) =>
    apiClient.post<ApiResponse<null>>("/auth/forgot-password", { email }),

  // Stage 3: token + new_password in body (not URL param)
  resetPassword: (token: string, new_password: string) =>
    apiClient.post<ApiResponse<null>>("/auth/reset-password", { token, new_password }),
};

