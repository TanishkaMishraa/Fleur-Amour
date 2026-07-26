/**
 * AuraFit — Auth route group layout.
 * Wraps all /auth/* pages with GuestGuard.
 * Authenticated users are redirected to /dashboard.
 * (Callback page is excluded via its own early-return logic.)
 */
import { GuestGuard } from "@/components/shared/RouteGuard";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <GuestGuard>{children}</GuestGuard>;
}
