"use client";
/**
 * AuraFit — Beauty recommendations card (Stage 4).
 * Displays the makeup, skincare, and hairstyle recommendations generated
 * by the pipeline's postprocessing stage.
 */
import { Gem, Brush, Scissors, Heart } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { GoldDivider } from "@/components/shared/GoldDivider";
import type { MakeupRecommendations, SkincareRecommendations } from "@/types";

interface Props {
  makeup: MakeupRecommendations;
  skincare: SkincareRecommendations;
  hairstyles: string[];
}

export function RecommendationsCard({ makeup, skincare, hairstyles }: Props) {
  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Gem className="h-4 w-4 text-brand-gold" /> Your Personalised Recommendations
        </CardTitle>
        <CardDescription>Generated from your unique facial analysis profile</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-6 sm:grid-cols-3">
          {/* Makeup */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-brand-gold">
              <Brush className="h-4 w-4" /> Makeup
            </div>
            <div className="space-y-2 text-sm">
              {makeup.foundation && (
                <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-3 space-y-1">
                  <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">Foundation</p>
                  <p className="capitalize">{makeup.foundation.shade_category} · {makeup.foundation.undertone}</p>
                  <p className="text-xs text-muted-foreground/60 capitalize">
                    {makeup.foundation.finish} finish, {makeup.foundation.coverage} coverage
                  </p>
                </div>
              )}
              {makeup.blush && (
                <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-3 space-y-1">
                  <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">Blush</p>
                  <p className="capitalize">{makeup.blush.tone} tone</p>
                  <p className="text-xs text-muted-foreground/60 capitalize">{makeup.blush.placement} placement</p>
                </div>
              )}
            </div>
          </div>

          <GoldDivider className="sm:hidden" />

          {/* Skincare */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-brand-gold">
              <Heart className="h-4 w-4" /> Skincare Focus
            </div>
            <div className="space-y-2">
              {skincare.priority_concerns?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {skincare.priority_concerns.map((c) => (
                    <Badge key={c} variant="rose" className="capitalize">{c.replace(/_/g, " ")}</Badge>
                  ))}
                </div>
              )}
              {skincare.routine_focus?.length > 0 && (
                <ul className="space-y-1.5 text-sm text-muted-foreground">
                  {skincare.routine_focus.map((f, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1 w-1 rounded-full bg-brand-gold shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <GoldDivider className="sm:hidden" />

          {/* Hairstyles */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-brand-gold">
              <Scissors className="h-4 w-4" /> Hairstyle Ideas
            </div>
            {hairstyles.length > 0 ? (
              <ul className="space-y-1.5 text-sm text-muted-foreground">
                {hairstyles.map((h, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-1.5 h-1 w-1 rounded-full bg-brand-gold shrink-0" />
                    {h}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground/50">No suggestions available for this scan.</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
