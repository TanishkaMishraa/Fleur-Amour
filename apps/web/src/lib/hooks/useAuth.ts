/**
 * AuraFit — useAuth hook (Stage 3: complete auth system).
 * Wraps auth store + all API calls. Used by all auth-aware components.
 */
import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth.store";
import { authApi } from "@/lib/api/auth";
import { authExtendedApi, usersApi } from "@/lib/api/users";
import { clearAccessToken, setAccessToken } from "@/lib/api/client";

export function useAuth() {
  const store = useAuthStore();
  const router = useRouter();

  const login = useCallback(
    async (email: string, password: string, mfa_code?: string) => {
      store.setLoading(true);
      try {
        const { data } = await authApi.login({ email, password, mfa_code });
        if (data.success && data.data) {
          setAccessToken(data.data.access_token);
          // Fetch full user data after token set
          const meRes = await usersApi.getMe();
          if (meRes.data.success && meRes.data.data) {
            store.setUser(meRes.data.data.user);
            store.setProfile(meRes.data.data.profile ?? null);
            store.setPreferences(meRes.data.data.preferences ?? null);
          }
          router.push("/dashboard");
          return { success: true };
        }
        return { success: false, error: data.errors?.[0]?.message ?? "Login failed" };
      } catch (err: any) {
        const code = err?.response?.data?.errors?.[0]?.code;
        const msg  = err?.response?.data?.errors?.[0]?.message ?? "Login failed";
        return { success: false, error: msg, code };
      } finally {
        store.setLoading(false);
      }
    },
    [store, router]
  );

  const register = useCallback(
    async (data: { email: string; password: string; full_name: string }) => {
      store.setLoading(true);
      try {
        const { data: res } = await authApi.register(data);
        if (res.success) return { success: true };
        return { success: false, error: res.errors?.[0]?.message };
      } catch (err: any) {
        return {
          success: false,
          error: err?.response?.data?.errors?.[0]?.message ?? "Registration failed",
        };
      } finally {
        store.setLoading(false);
      }
    },
    [store]
  );

  const logout = useCallback(async () => {
    try { await authApi.logout(); } catch {}
    clearAccessToken();
    store.logout();
    router.push("/");
  }, [store, router]);

  const refreshUser = useCallback(async () => {
    try {
      const { data } = await usersApi.getMe();
      if (data.success && data.data) {
        store.setUser(data.data.user);
        store.setProfile(data.data.profile ?? null);
        store.setPreferences(data.data.preferences ?? null);
      }
    } catch {}
  }, [store]);

  const loginWithGoogle = useCallback(async () => {
    try {
      const { data } = await authExtendedApi.getOAuthUrl("google");
      if (data.success && data.data) {
        window.location.href = data.data.authorize_url;
      }
    } catch {}
  }, []);

  return {
    user:            store.user,
    profile:         store.profile,
    preferences:     store.preferences,
    isAuthenticated: store.isAuthenticated,
    isLoading:       store.isLoading,
    hydrated:        store.hydrated,
    login,
    register,
    logout,
    refreshUser,
    loginWithGoogle,
  };
}
