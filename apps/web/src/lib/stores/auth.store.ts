/**
 * AuraFit — Auth Zustand store (Stage 3).
 * Persists user + isAuthenticated across page refreshes.
 * Separate session + MFA state not persisted (fetched fresh).
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import type { User, UserProfile, UserPreferences } from "@/types";

interface AuthState {
  user:            User | null;
  profile:         UserProfile | null;
  preferences:     UserPreferences | null;
  isAuthenticated: boolean;
  isLoading:       boolean;
  hydrated:        boolean;
}

interface AuthActions {
  setUser:         (u: User | null) => void;
  setProfile:      (p: UserProfile | null) => void;
  setPreferences:  (p: UserPreferences | null) => void;
  setLoading:      (v: boolean) => void;
  setHydrated:     () => void;
  logout:          () => void;
  patchUser:       (partial: Partial<User>) => void;
  patchPreferences:(partial: Partial<UserPreferences>) => void;
}

export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    immer((set) => ({
      user:            null,
      profile:         null,
      preferences:     null,
      isAuthenticated: false,
      isLoading:       false,
      hydrated:        false,

      setUser: (user) => set((s) => {
        s.user            = user;
        s.isAuthenticated = !!user;
      }),
      setProfile: (profile) => set((s) => { s.profile = profile; }),
      setPreferences: (prefs) => set((s) => { s.preferences = prefs; }),
      setLoading: (v) => set((s) => { s.isLoading = v; }),
      setHydrated: () => set((s) => { s.hydrated = true; }),

      logout: () => set((s) => {
        s.user            = null;
        s.profile         = null;
        s.preferences     = null;
        s.isAuthenticated = false;
      }),

      patchUser: (partial) => set((s) => {
        if (s.user) Object.assign(s.user, partial);
      }),

      patchPreferences: (partial) => set((s) => {
        if (s.preferences) Object.assign(s.preferences, partial);
      }),
    })),
    {
      name: "aurafit-auth",
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? localStorage : ({} as Storage)
      ),
      partialize: (s) => ({
        user:            s.user,
        isAuthenticated: s.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated();
      },
    }
  )
);
