"use client";
import { Bell, Search } from "lucide-react";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth.store";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { getInitials } from "@/lib/utils";

const ROUTE_LABELS: Record<string, string> = {
  "/dashboard":                  "Overview",
  "/dashboard/wardrobe":         "My Wardrobe",
  "/dashboard/recommendations":  "Recommendations",
  "/dashboard/analysis":         "Skin & Face Analysis",
  "/dashboard/try-on":           "Virtual Try-On",
  "/dashboard/chat":             "Aura AI",
  "/dashboard/reports":          "Reports",
  "/dashboard/profile":          "My Profile",
  "/dashboard/settings":         "Settings",
};

export function DashboardTopbar() {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const label = ROUTE_LABELS[pathname] ?? "Dashboard";

  return (
    <header className="flex h-[72px] items-center justify-between gap-4 border-b border-white/[0.06] bg-background/50 backdrop-blur-sm px-6">
      {/* Page title */}
      <h2 className="font-display text-xl font-light tracking-tight text-foreground">
        {label}
      </h2>

      <div className="flex items-center gap-3">
        {/* Search */}
        <button className="hidden sm:flex items-center gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors min-w-[160px]">
          <Search className="h-3.5 w-3.5" />
          <span>Search…</span>
          <kbd className="ml-auto rounded bg-white/5 px-1.5 py-0.5 text-2xs font-mono text-muted-foreground/30">⌘K</kbd>
        </button>

        {/* Notifications */}
        <button className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-white/[0.06] text-muted-foreground/50 hover:text-foreground hover:bg-white/[0.04] transition-all">
          <Bell className="h-4 w-4" />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-brand-gold" />
        </button>

        {/* Avatar */}
        <Avatar className="h-9 w-9 cursor-pointer ring-1 ring-white/10 hover:ring-brand-gold/30 transition-all">
          <AvatarImage src={user?.avatar_url ?? undefined} alt={user?.full_name} />
          <AvatarFallback className="text-xs">
            {user?.full_name ? getInitials(user.full_name) : "AF"}
          </AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
