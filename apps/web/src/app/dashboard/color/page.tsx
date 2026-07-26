"use client";
/**
 * AuraFit — Color Intelligence dashboard page (Stage 5).
 *
 * Layout:
 *   1. Header + compute CTA (or re-compute if profile exists)
 *   2. Season classification card (hero)
 *   3. Personal palette panel
 *   4. Tab group: Makeup · Lipstick · Hair Color · Outfits · Jewellery
 *   5. History strip
 *
 * Data flow:
 *   - On mount, fetch active profile (GET /color/profile)
 *   - If none: show CTA → POST /color/compute → display liveResult
 *   - If profile exists: reconstruct FullColorAnalysisResponse from stored JSONB
 */
import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, RefreshCw, Palette, Brush,
  Scissors, ShirtIcon, Gem, History
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { GoldDivider } from "@/components/shared/GoldDivider";
import { useColorProfile, useColorHistory } from "@/lib/hooks/useColorProfile";
import { SeasonCard } from "@/components/features/color/SeasonCard";
import { PalettePanel } from "@/components/features/color/PalettePanel";
import { MakeupPanel } from "@/components/features/color/MakeupPanel";
import { LipstickPanel } from "@/components/features/color/LipstickPanel";
import {
  HairColorPanel,
  OutfitColorPanel,
  JewelryPanel,
} from "@/components/features/color/ColorRecommendationPanels";
import { SeasonBadge } from "@/components/features/color/SeasonBadge";
import type { FullColorAnalysisResponse } from "@/types/color";
import type { ColorProfileRecord } from "@/types/color";

const anim = (i: number) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: i * 0.07, duration: 0.4, ease: [0.23, 1, 0.32, 1] as const },
});

// Reconstruct a FullColorAnalysisResponse from a persisted ColorProfileRecord
function profileToAnalysis(p: ColorProfileRecord): FullColorAnalysisResponse | null {
  if (!p.palette_best || !p.makeup_recommendations) return null;
  return {
    profile_id:    p.id,
    scan_id:       p.scan_id,
    season: {
      season:              p.season as any,
      confidence:          p.season_confidence,
      description:         p.season_description ?? "",
      key_characteristics: [],
      celebrity_examples:  [],
      season_family:       (p.season.split("_").pop() ?? p.season) as any,
      contrast_level:      "medium" as any,
      chroma_level:        "clear" as any,
      value_level:         "medium" as any,
    },
    palette: {
      best:       p.palette_best ?? [],
      neutrals:   p.palette_neutrals ?? [],
      accents:    p.palette_accents ?? [],
      avoid:      p.palette_avoid ?? [],
      hero_color: p.palette_best?.[0] ?? { hex: "#C9A84C", name: "Gold", category: "accent" },
    },
    makeup:     p.makeup_recommendations ?? {},
    lipstick:   p.lipstick_recommendations ?? [],
    hair_color: p.hair_color_recommendations ?? [],
    outfits:    p.outfit_recommendations ?? {},
    jewelry:    p.jewelry_recommendations ?? { metal_tones: [], gem_colors: [], rationale: "", style_notes: "" },
    computed_at:    p.created_at,
    engine_version: p.engine_version,
  } as FullColorAnalysisResponse;
}

export default function ColorPage() {
  const { profile, liveResult, isLoading, isComputing, computeError, compute } = useColorProfile();
  const { data: history } = useColorHistory();

  // Prefer live result (just computed) → fallback to persisted profile
  const analysis: FullColorAnalysisResponse | null = useMemo(() => {
    if (liveResult) return liveResult;
    if (profile) return profileToAnalysis(profile);
    return null;
  }, [liveResult, profile]);

  const hasResult = !!analysis;

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-16">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <motion.div {...anim(0)} className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-2xs uppercase tracking-widest text-brand-gold/70">
            <Palette className="h-3.5 w-3.5" />
            Color Intelligence
          </div>
          <h1 className="font-display text-display-md font-light tracking-tightest">
            Your Color Season
          </h1>
          <p className="text-sm text-muted-foreground max-w-lg">
            Discover your personal color palette based on your skin tone, undertone, and
            hair colour — derived directly from your facial analysis.
          </p>
        </div>

        <div className="flex gap-3 flex-shrink-0">
          {hasResult && (
            <Button
              variant="ghost-gold"
              onClick={() => compute()}
              loading={isComputing}
              className="gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Recompute
            </Button>
          )}
          {!hasResult && !isLoading && (
            <Button
              variant="gold"
              onClick={() => compute()}
              loading={isComputing}
              className="gap-2"
            >
              <Sparkles className="h-4 w-4" />
              Discover My Colors
            </Button>
          )}
        </div>
      </motion.div>

      <GoldDivider />

      {/* ── Loading skeleton ─────────────────────────────────────────────── */}
      {(isLoading || isComputing) && !hasResult && (
        <motion.div {...anim(1)} className="space-y-6">
          {isComputing && (
            <div className="text-center py-8 space-y-3">
              <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gold-gradient animate-float shadow-gold-glow">
                <Sparkles className="h-6 w-6 text-brand-black" />
              </div>
              <p className="text-sm text-muted-foreground">Analysing your colour season…</p>
              <p className="text-xs text-muted-foreground/40">Matching skin tone, undertone, and contrast level</p>
            </div>
          )}
          <div className="grid gap-6 lg:grid-cols-2">
            <Skeleton className="h-80 rounded-2xl" />
            <Skeleton className="h-80 rounded-2xl" />
          </div>
        </motion.div>
      )}

      {/* ── Empty state ────────────────────────────────────────────────── */}
      {!isLoading && !isComputing && !hasResult && (
        <motion.div {...anim(1)} className="luxury-card p-12 text-center space-y-6">
          <div className="mx-auto h-20 w-20 rounded-3xl bg-gold-gradient flex items-center justify-center shadow-gold-glow animate-float">
            <Palette className="h-9 w-9 text-brand-black" />
          </div>
          <div className="space-y-2">
            <h2 className="font-display text-display-sm font-light">
              No color profile yet
            </h2>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto">
              Complete a facial scan first, then tap <strong>Discover My Colors</strong> to
              generate your personal 12-season color analysis.
            </p>
          </div>
          {computeError && (
            <p className="text-sm text-destructive">{computeError}</p>
          )}
          <Button variant="gold" onClick={() => compute()} loading={isComputing}>
            <Sparkles className="h-4 w-4" /> Discover My Colors
          </Button>
        </motion.div>
      )}

      {/* ── Results ────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {hasResult && analysis && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-8"
          >
            {/* Season + palette */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div {...anim(1)}>
                <SeasonCard season={analysis.season} />
              </motion.div>
              <motion.div {...anim(2)}>
                <PalettePanel palette={analysis.palette} />
              </motion.div>
            </div>

            {/* Recommendation tabs */}
            <motion.div {...anim(3)}>
              <Tabs defaultValue="makeup" className="space-y-6">
                <TabsList className="flex-wrap h-auto gap-1 p-1.5">
                  {[
                    { value: "makeup",   icon: Sparkles,   label: "Makeup"     },
                    { value: "lipstick", icon: Brush,      label: "Lipstick"   },
                    { value: "hair",     icon: Scissors,   label: "Hair Color" },
                    { value: "outfits",  icon: ShirtIcon,  label: "Outfits"    },
                    { value: "jewelry",  icon: Gem,        label: "Jewellery"  },
                  ].map(({ value, icon: Icon, label }) => (
                    <TabsTrigger key={value} value={value} className="gap-2">
                      <Icon className="h-3.5 w-3.5" />
                      <span className="hidden sm:inline">{label}</span>
                    </TabsTrigger>
                  ))}
                </TabsList>

                <TabsContent value="makeup">
                  <MakeupPanel makeup={analysis.makeup as any} />
                </TabsContent>
                <TabsContent value="lipstick">
                  <LipstickPanel shades={analysis.lipstick} />
                </TabsContent>
                <TabsContent value="hair">
                  <HairColorPanel options={analysis.hair_color} />
                </TabsContent>
                <TabsContent value="outfits">
                  <OutfitColorPanel outfits={analysis.outfits} />
                </TabsContent>
                <TabsContent value="jewelry">
                  <JewelryPanel jewelry={analysis.jewelry} />
                </TabsContent>
              </Tabs>
            </motion.div>

            {/* History strip */}
            {history && history.length > 1 && (
              <motion.div {...anim(4)} className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <History className="h-4 w-4" />
                  Previous analyses
                </div>
                <div className="flex gap-3 overflow-x-auto pb-2 hide-scrollbar">
                  {history.slice(1).map((p) => (
                    <div
                      key={p.id}
                      className="flex-shrink-0 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-2 min-w-[160px]"
                    >
                      <SeasonBadge season={p.season as any} size="sm" />
                      <p className="text-2xs text-muted-foreground/40">
                        {new Date(p.created_at).toLocaleDateString(undefined, {
                          month: "short", day: "numeric", year: "numeric",
                        })}
                      </p>
                      <p className="text-2xs text-muted-foreground/40">
                        {Math.round(p.season_confidence * 100)}% confidence
                      </p>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
