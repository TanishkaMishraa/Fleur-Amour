/**
 * AuraFit — UI Zustand store.
 * Controls sidebar state, modals, mobile nav, global loading.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

interface UIState {
  sidebarCollapsed: boolean;
  mobileNavOpen: boolean;
  globalLoading: boolean;
  activeModal: string | null;
}

interface UIActions {
  toggleSidebarCollapsed: () => void;
  setSidebarCollapsed: (v: boolean) => void;
  toggleMobileNav: () => void;
  setMobileNavOpen: (v: boolean) => void;
  setGlobalLoading: (v: boolean) => void;
  openModal: (id: string) => void;
  closeModal: () => void;
}

export const useUIStore = create<UIState & UIActions>()(
  persist(
    immer((set) => ({
      sidebarCollapsed: false,
      mobileNavOpen: false,
      globalLoading: false,
      activeModal: null,

      toggleSidebarCollapsed: () =>
        set((s) => { s.sidebarCollapsed = !s.sidebarCollapsed; }),
      setSidebarCollapsed: (v) =>
        set((s) => { s.sidebarCollapsed = v; }),
      toggleMobileNav: () =>
        set((s) => { s.mobileNavOpen = !s.mobileNavOpen; }),
      setMobileNavOpen: (v) =>
        set((s) => { s.mobileNavOpen = v; }),
      setGlobalLoading: (v) =>
        set((s) => { s.globalLoading = v; }),
      openModal: (id) =>
        set((s) => { s.activeModal = id; }),
      closeModal: () =>
        set((s) => { s.activeModal = null; }),
    })),
    {
      name: "aurafit-ui",
      partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed }),
    }
  )
);
