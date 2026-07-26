"use client";
/**
 * AuraFit — RouteGuard.
 * Client-side auth guard. Wraps dashboard routes.
 * Redirects unauthenticated users to /auth/login.
 * Shows a loading state while the Zustand store is hydrating from localStorage.
 */
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth.store";
import { FullPageLoader } from "@/components/shared/LoadingSpinner";

interface RouteGuardProps {
  children:  React.ReactNode;
  roles?:    string[];          // If set, restrict to these roles (RBAC)
}

export function RouteGuard({ children, roles }: RouteGuardProps) {
  const { isAuthenticated, hydrated, user } = useAuthStore();
  const router   = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!hydrated) return;

    if (!isAuthenticated) {
      const returnTo = encodeURIComponent(pathname);
      router.replace(`/auth/login?returnTo=${returnTo}`);
      return;
    }

    // RBAC: redirect if role not permitted
    if (roles && user && !roles.includes(user.role)) {
      router.replace("/dashboard");
    }
  }, [hydrated, isAuthenticated, user, roles, router, pathname]);

  // While Zustand rehydrates from localStorage, show loader
  if (!hydrated) return <FullPageLoader />;

  // Not authenticated — render nothing (redirect in progress)
  if (!isAuthenticated) return <FullPageLoader />;

  // Role check failed
  if (roles && user && !roles.includes(user.role)) return <FullPageLoader />;

  return <>{children}</>;
}

/**
 * GuestGuard — for auth pages.
 * Redirects authenticated users to /dashboard.
 */
export function GuestGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, hydrated } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (hydrated && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [hydrated, isAuthenticated, router]);

  if (!hydrated) return null;
  if (isAuthenticated) return null;
  return <>{children}</>;
}
