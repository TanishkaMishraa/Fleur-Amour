"use client";
import { motion } from "framer-motion";
import { Sparkles, Camera, Shirt, Wind, TrendingUp, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useAuthStore } from "@/lib/stores/auth.store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmailVerificationBanner } from "@/components/shared/EmailVerificationBanner";

const QUICK_ACTIONS = [
  { label: "Skin Analysis", desc: "Scan your face", icon: Camera, href: "/dashboard/analysis", color: "from-amber-500/20 to-orange-500/5", iconColor: "text-amber-400" },
  { label: "Wardrobe",      desc: "Manage items",   icon: Shirt,  href: "/dashboard/wardrobe",  color: "from-violet-500/20 to-purple-500/5", iconColor: "text-violet-400" },
  { label: "Style Picks",   desc: "View recs",      icon: Sparkles, href: "/dashboard/recommendations", color: "from-brand-gold/20 to-amber-500/5", iconColor: "text-brand-gold" },
  { label: "Fragrance",     desc: "Find your scent",icon: Wind,   href: "/dashboard/recommendations?type=fragrance", color: "from-sky-500/20 to-blue-500/5", iconColor: "text-sky-400" },
];

const STATS = [
  { label: "Recommendations", value: "—",  sub: "style picks" },
  { label: "Wardrobe Items",  value: "—",  sub: "pieces tracked" },
  { label: "Outfits Built",   value: "—",  sub: "combinations" },
  { label: "Style Score",     value: "—",  sub: "percentile" },
];

const anim = (i: number) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: i * 0.07, duration: 0.45, ease: [0.23, 1, 0.32, 1] as const },
});

export default function DashboardPage() {
  const { user, profile } = useAuthStore();
  const isOnboarded = profile?.onboarding_complete;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <EmailVerificationBanner />

      {/* Welcome */}
      <motion.div {...anim(0)} className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-display-md font-light tracking-tightest text-foreground">
            Welcome back,{" "}
            <span className="italic text-gold-gradient">
              {user?.full_name?.split(" ")[0] ?? "there"}
            </span>
          </h1>
          <p className="mt-1.5 text-muted-foreground">
            {isOnboarded
              ? "Your personalised recommendations are ready."
              : "Complete your profile to unlock personalised recommendations."}
          </p>
        </div>
        {!isOnboarded && (
          <Badge variant="gold" className="shrink-0">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-gold animate-gold-pulse" />
            Complete Profile
          </Badge>
        )}
      </motion.div>

      {/* Onboarding CTA */}
      {!isOnboarded && (
        <motion.div {...anim(1)}
          className="rounded-2xl border border-brand-gold/20 bg-brand-gold/5 p-5 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="font-medium text-foreground">Set up your beauty profile</p>
            <p className="text-sm text-muted-foreground mt-0.5">Takes 2 minutes · Unlocks all AI features</p>
          </div>
          <Button variant="gold" size="sm" asChild>
            <Link href="/dashboard/profile">Start <ArrowRight className="h-4 w-4" /></Link>
          </Button>
        </motion.div>
      )}

      {/* Stats */}
      <motion.div {...anim(2)} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STATS.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-5">
              <p className="text-2xs font-medium uppercase tracking-widest text-muted-foreground/60">{stat.label}</p>
              <p className="mt-2 font-display text-3xl font-light text-gold-gradient">{stat.value}</p>
              <p className="mt-0.5 text-xs text-muted-foreground/50">{stat.sub}</p>
            </CardContent>
          </Card>
        ))}
      </motion.div>

      {/* Quick actions */}
      <motion.div {...anim(3)}>
        <h2 className="font-sans text-sm font-semibold uppercase tracking-widest text-muted-foreground/60 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {QUICK_ACTIONS.map((action, i) => {
            const Icon = action.icon;
            return (
              <motion.div key={action.label} {...anim(4 + i)}>
                <Link href={action.href}
                  className={`luxury-card group flex flex-col gap-4 p-5 bg-gradient-to-br ${action.color}`}>
                  <Icon className={`h-5 w-5 ${action.iconColor}`} />
                  <div>
                    <p className="font-medium text-foreground text-sm">{action.label}</p>
                    <p className="text-xs text-muted-foreground/60 mt-0.5">{action.desc}</p>
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/30 group-hover:text-brand-gold group-hover:translate-x-1 transition-all" />
                </Link>
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      {/* Recent recommendations placeholder */}
      <motion.div {...anim(8)}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-sans text-sm font-semibold uppercase tracking-widest text-muted-foreground/60">Recent Picks</h2>
          <Link href="/dashboard/recommendations"
            className="text-xs text-brand-gold/70 hover:text-brand-gold transition-colors flex items-center gap-1">
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="luxury-card p-4 space-y-3">
              <Skeleton className="h-36 w-full rounded-xl" />
              <Skeleton className="h-3 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
