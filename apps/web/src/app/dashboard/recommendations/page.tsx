"use client";
/**
 * AuraFit — Recommendations dashboard page (Stage 6).
 *
 * Layout:
 *   1. Domain tab bar (Makeup · Skincare · Haircare · Fragrance · Fashion · Accessories)
 *   2. For each domain: personalised recommendation grid
 *   3. Context controls: occasion, season, budget filters
 *   4. Cold-start notice if user has < 3 interactions
 */
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, Filter, ChevronDown, RefreshCw, LayoutGrid, Rows3,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { GoldDivider } from "@/components/shared/GoldDivider";
import { RecommendationGrid, DomainSection } from "@/components/features/recommendations/RecommendationGrid";
import { useRecommendations } from "@/lib/hooks/useRecommendations";
import { useAuthStore } from "@/lib/stores/auth.store";
import type { RecDomain } from "@/types/recommendations";
import { DOMAIN_META } from "@/types/recommendations";

const DOMAINS: RecDomain[] = ["makeup", "skincare", "haircare", "fragrance", "fashion", "accessories"];

const OCCASIONS = ["", "work", "evening", "casual", "sport"];
const SEASONS   = ["", "spring", "summer", "autumn", "winter"];

function DomainTab({ domain, active }: { domain: RecDomain; active: boolean }) {
  const meta = DOMAIN_META[domain];
  return (
    <div className="flex items-center gap-2">
      <span>{meta.emoji}</span>
      <span className="hidden sm:inline">{meta.label}</span>
    </div>
  );
}

function DomainPanel({ domain, userId, occasion, season, budgetMax }:
  { domain: RecDomain; userId: string; occasion?: string; season?: string; budgetMax?: number }) {
  const [layout, setLayout] = useState<"grid" | "strip">("grid");
  const { data, isLoading, isError, refetch, isRefetching } = useRecommendations(domain, {
    occasion: occasion || undefined,
    season:   season || undefined,
    budget_max: budgetMax || undefined,
    limit: 20,
  });

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {data?.cold_start && (
            <div className="rounded-xl border border-brand-gold/20 bg-brand-gold/5 px-3 py-1.5 text-xs text-brand-gold/80">
              ✦ Interact with products to personalise your recommendations
            </div>
          )}
          {data && !data.cold_start && (
            <span className="text-xs text-muted-foreground/40">
              {data.total} personalised picks
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => refetch()} loading={isRefetching} className="h-8 w-8 p-0">
            {!isRefetching && <RefreshCw className="h-3.5 w-3.5" />}
          </Button>
          <div className="flex rounded-xl border border-white/[0.08] overflow-hidden">
            <button
              onClick={() => setLayout("grid")}
              className={`h-8 w-8 flex items-center justify-center transition-colors ${
                layout === "grid" ? "bg-white/[0.08] text-foreground" : "text-muted-foreground/40 hover:text-muted-foreground"
              }`}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setLayout("strip")}
              className={`h-8 w-8 flex items-center justify-center transition-colors ${
                layout === "strip" ? "bg-white/[0.08] text-foreground" : "text-muted-foreground/40 hover:text-muted-foreground"
              }`}
            >
              <Rows3 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {isError && (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-6 text-center text-sm text-destructive/70">
          Failed to load recommendations. Please try again.
        </div>
      )}

      <RecommendationGrid
        items={data?.items ?? []}
        loading={isLoading}
        columns={layout === "grid" ? 4 : 2}
      />
    </div>
  );
}

export default function RecommendationsPage() {
  const { user } = useAuthStore();
  const userId = user?.id ?? "";

  const [activeDomain, setActiveDomain] = useState<RecDomain>("makeup");
  const [occasion,  setOccasion]  = useState("");
  const [season,    setSeason]    = useState("");
  const [budgetMax, setBudgetMax] = useState<number | undefined>();
  const [showFilters, setShowFilters] = useState(false);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4"
      >
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-2xs uppercase tracking-widest text-brand-gold/70">
            <Sparkles className="h-3.5 w-3.5" />
            Recommendations
          </div>
          <h1 className="font-display text-display-md font-light tracking-tightest">
            For You
          </h1>
          <p className="text-sm text-muted-foreground max-w-lg">
            Personalised across makeup, skincare, haircare, fragrance, fashion, and accessories —
            powered by your profile, color season, and taste.
          </p>
        </div>
        <Button
          variant="ghost-gold"
          onClick={() => setShowFilters((f) => !f)}
          className="gap-2 self-start"
        >
          <Filter className="h-4 w-4" />
          Filters
          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${showFilters ? "rotate-180" : ""}`} />
        </Button>
      </motion.div>

      {/* Filter bar */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="luxury-card p-5 flex flex-wrap gap-5">
              <div className="flex flex-col gap-1.5 min-w-[140px]">
                <label className="text-2xs uppercase tracking-widest text-muted-foreground/40">Occasion</label>
                <select
                  value={occasion}
                  onChange={(e) => setOccasion(e.target.value)}
                  className="input-luxury text-sm"
                >
                  <option value="">Any occasion</option>
                  {OCCASIONS.filter(Boolean).map((o) => (
                    <option key={o} value={o} className="capitalize">{o}</option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1.5 min-w-[140px]">
                <label className="text-2xs uppercase tracking-widest text-muted-foreground/40">Season</label>
                <select
                  value={season}
                  onChange={(e) => setSeason(e.target.value)}
                  className="input-luxury text-sm"
                >
                  <option value="">Any season</option>
                  {SEASONS.filter(Boolean).map((s) => (
                    <option key={s} value={s} className="capitalize">{s}</option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1.5 min-w-[160px]">
                <label className="text-2xs uppercase tracking-widest text-muted-foreground/40">Budget max</label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    placeholder="No limit"
                    value={budgetMax ?? ""}
                    onChange={(e) => setBudgetMax(e.target.value ? Number(e.target.value) : undefined)}
                    className="input-luxury text-sm w-full"
                  />
                  {budgetMax && (
                    <button onClick={() => setBudgetMax(undefined)} className="text-muted-foreground/40 hover:text-foreground text-sm">×</button>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <GoldDivider />

      {/* Domain tabs */}
      <Tabs value={activeDomain} onValueChange={(v) => setActiveDomain(v as RecDomain)}>
        <TabsList className="flex-wrap h-auto gap-1 p-1.5 w-full">
          {DOMAINS.map((domain) => (
            <TabsTrigger key={domain} value={domain} className="gap-2 flex-1 min-w-[80px]">
              <DomainTab domain={domain} active={activeDomain === domain} />
            </TabsTrigger>
          ))}
        </TabsList>

        {DOMAINS.map((domain) => (
          <TabsContent key={domain} value={domain} className="mt-8">
            <DomainPanel
              domain={domain}
              userId={userId}
              occasion={occasion}
              season={season}
              budgetMax={budgetMax}
            />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
