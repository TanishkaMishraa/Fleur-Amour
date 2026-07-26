/**
 * AuraFit — Users & Profile API client.
 * Covers user account, preferences, sessions, and profile management.
 * All calls use the shared apiClient from Stage 2 with JWT auto-refresh.
 */
import { apiClient } from "./client";
import type {
  User, UserProfile, ApiResponse, PaginatedResponse,
  UserPreferences, UserSession, UserSecurity,
} from "@/types";

/* ── User account ─────────────────────────────────────────────────────────── */

export const usersApi = {
  getMe: () =>
    apiClient.get<ApiResponse<{ user: User; profile: UserProfile | null; preferences: UserPreferences | null }>>(
      "/users/me"
    ),

  updateMe: (data: Partial<Pick<User, "full_name" | "avatar_url">>) =>
    apiClient.patch<ApiResponse<User>>("/users/me", data),

  deleteMe: () =>
    apiClient.delete<void>("/users/me"),

  uploadAvatar: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiClient.post<ApiResponse<{ avatar_url: string }>>("/users/me/avatar", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  removeAvatar: () =>
    apiClient.delete<ApiResponse<null>>("/users/me/avatar"),

  getSecurity: () =>
    apiClient.get<ApiResponse<UserSecurity>>("/users/me/security"),

  requestDataExport: (data: {
    include_interactions?: boolean;
    include_scan_data?: boolean;
    include_chat_history?: boolean;
  }) =>
    apiClient.post<ApiResponse<{ task_id: string }>>("/users/me/export", data),
};

/* ── Beauty Profile ───────────────────────────────────────────────────────── */

export const profileApi = {
  getProfile: () =>
    apiClient.get<ApiResponse<UserProfile>>("/users/me/profile"),

  updateProfile: (data: Partial<UserProfile>) =>
    apiClient.put<ApiResponse<UserProfile>>("/users/me/profile", data),
};

/* ── Preferences ──────────────────────────────────────────────────────────── */

export const preferencesApi = {
  getPreferences: () =>
    apiClient.get<ApiResponse<UserPreferences>>("/users/me/preferences"),

  updatePreferences: (data: Partial<UserPreferences>) =>
    apiClient.patch<ApiResponse<UserPreferences>>("/users/me/preferences", data),
};

/* ── Sessions ─────────────────────────────────────────────────────────────── */

export const sessionsApi = {
  listSessions: () =>
    apiClient.get<ApiResponse<UserSession[]>>("/users/me/sessions"),

  revokeSession: (sessionId: string) =>
    apiClient.delete<ApiResponse<null>>(`/users/me/sessions/${sessionId}`),

  revokeAllOtherSessions: () =>
    apiClient.delete<ApiResponse<{ revoked: number }>>("/users/me/sessions/others"),
};

/* ── Auth (extended) ──────────────────────────────────────────────────────── */

export const authExtendedApi = {
  changePassword: (current_password: string, new_password: string) =>
    apiClient.post<ApiResponse<null>>("/auth/change-password", {
      current_password,
      new_password,
    }),

  verifyEmail: (token: string) =>
    apiClient.post<ApiResponse<null>>(`/auth/verify-email/${token}`),

  resendVerification: (email: string) =>
    apiClient.post<ApiResponse<null>>("/auth/resend-verification", { email }),

  getOAuthUrl: (provider: string) =>
    apiClient.get<ApiResponse<{ authorize_url: string; state: string }>>(`/auth/oauth/${provider}`),

  oauthCallback: (provider: string, code: string, state?: string) =>
    apiClient.post<ApiResponse<{ access_token: string; expires_in: number }>>(
      "/auth/oauth/callback",
      { provider, code, state }
    ),

  setupMFA: () =>
    apiClient.post<ApiResponse<{ secret: string; qr_code_url: string; backup_codes: string[] }>>(
      "/auth/mfa/setup"
    ),

  confirmMFA: (code: string) =>
    apiClient.post<ApiResponse<null>>("/auth/mfa/confirm", { code }),

  disableMFA: (password: string, code: string) =>
    apiClient.post<ApiResponse<null>>("/auth/mfa/disable", { password, code }),
};
