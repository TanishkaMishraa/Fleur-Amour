"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, Shirt, Sparkles, Camera, Wand2,
  MessageCircle, User, BarChart3, Settings, LogOut,
  ChevronLeft, ChevronRight, Dna, TrendingDown, Star
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/stores/ui.store";
import { useAuth } from "@/lib/hooks/useAuth";

const NAV = [
  { label: "Overview",       href: "/dashboard",               icon: LayoutDashboard },
  { label: "Wardrobe",       href: "/dashboard/wardrobe",      icon: Shirt },
  { label: "Recommendations",href: "/dashboard/recommendations",icon: Sparkles },
  { label: "Alternatives",    href: "/dashboard/alternatives",  icon: TrendingDown },
  { label: "Try-On AR",       href: "/dashboard/try-on",        icon: Wand2 },
  { label: "Wardrobe AI",     href: "/dashboard/wardrobe",      icon: Shirt },
  { label: "Celebrity Match", href: "/dashboard/celebrity",     icon: Star },
  { label: "Style DNA",       href: "/dashboard/style-dna",     icon: Dna },
  { label: "Skin Analysis",  href: "/dashboard/analysis",      icon: Camera },
  { label: "Virtual Try-On", href: "/dashboard/try-on",        icon: Wand2 },
  { label: "Aura AI",        href: "/dashboard/chat",          icon: MessageCircle },
  { label: "Reports",        href: "/dashboard/reports",       icon: BarChart3 },
];

const BOTTOM_NAV = [
  { label: "Profile",  href: "/dashboard/profile",  icon: User },
  { label: "Settings", href: "/dashboard/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebarCollapsed } = useUIStore();
  const { user, logout } = useAuth();

  const isActive = (href: string) =>
    href === "/dashboard" ? pathname === href : pathname.startsWith(href);

  return (
    <motion.aside
      animate={{ width: sidebarCollapsed ? 72 : 240 }}
      transition={{ duration: 0.35, ease: [0.23, 1, 0.32, 1] }}
      className="relative flex h-screen flex-col overflow-hidden border-r border-white/[0.06] bg-sidebar"
      style={{ backgroundImage: "linear-gradient(180deg, #09090B 0%, #0D0D0F 100%)" }}
    >
      {/* Logo */}
      <div className={cn("flex h-[72px] items-center border-b border-white/[0.06] px-4", sidebarCollapsed ? "justify-center" : "gap-3 px-5")}>
        <div className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gold-gradient">
          <Sparkles className="h-4 w-4 text-brand-black" />
        </div>
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.span
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.2 }}
              className="font-display text-lg font-medium tracking-tight text-sidebar-foreground"
            >
              Aura<span className="text-gold-gradient">Fit</span>
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Main nav */}
      <nav className="flex-1 overflow-y-auto py-4 hide-scrollbar">
        <ul className="space-y-0.5 px-2">
          {NAV.map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  title={sidebarCollapsed ? item.label : undefined}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-sans font-medium transition-all duration-200",
                    active
                      ? "bg-brand-gold/10 text-brand-gold"
                      : "text-sidebar-foreground/50 hover:bg-white/[0.04] hover:text-sidebar-foreground"
                  )}
                >
                  {active && (
                    <motion.div
                      layoutId="sidebar-active"
                      className="absolute inset-0 rounded-xl bg-brand-gold/10"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.4 }}
                    />
                  )}
                  <Icon className={cn("relative z-10 h-4.5 w-4.5 shrink-0", active && "text-brand-gold")} />
                  <AnimatePresence>
                    {!sidebarCollapsed && (
                      <motion.span
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="relative z-10 truncate"
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                  {active && !sidebarCollapsed && (
                    <motion.div
                      layoutId="sidebar-indicator"
                      className="absolute right-3 h-1.5 w-1.5 rounded-full bg-brand-gold"
                    />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Bottom nav */}
      <div className="border-t border-white/[0.06] p-2 space-y-0.5">
        {BOTTOM_NAV.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.href);
          return (
            <Link key={item.href} href={item.href}
              className={cn("flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all",
                active ? "text-brand-gold bg-brand-gold/10" : "text-sidebar-foreground/40 hover:text-sidebar-foreground hover:bg-white/[0.04]"
              )}>
              <Icon className="h-4 w-4 shrink-0" />
              <AnimatePresence>
                {!sidebarCollapsed && (
                  <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="text-sm font-medium">{item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );
        })}

        {/* User + logout */}
        <div className={cn("flex items-center gap-2.5 rounded-xl px-3 py-2.5 mt-1 border border-white/[0.05]",
          sidebarCollapsed ? "justify-center" : "")}>
          <div className="h-7 w-7 shrink-0 rounded-full bg-gold-gradient flex items-center justify-center text-xs font-bold text-brand-black">
            {user?.full_name?.[0] ?? "A"}
          </div>
          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex-1 min-w-0">
                <p className="text-xs font-medium text-sidebar-foreground truncate">{user?.full_name}</p>
                <p className="text-2xs text-sidebar-foreground/40 truncate">{user?.email}</p>
              </motion.div>
            )}
          </AnimatePresence>
          {!sidebarCollapsed && (
            <button onClick={logout}
              className="p-1 rounded-lg text-sidebar-foreground/30 hover:text-destructive transition-colors" title="Log out">
              <LogOut className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={toggleSidebarCollapsed}
        className="absolute -right-3 top-20 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-brand-graphite text-foreground/50 hover:text-foreground transition-all hover:scale-110 shadow-luxury-sm"
      >
        {sidebarCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
      </button>
    </motion.aside>
  );
}
