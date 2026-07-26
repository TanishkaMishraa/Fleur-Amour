"use client";
/**
 * AuraFit — Skin concerns card (Stage 4).
 * Aggregates acne, dark circles, and texture into a unified concerns list
 * with severity bars, region tags, and category badges.
 */
import { AlertCircle, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { AcneAnalysisResult, DarkCircleResult, SkinTextureResult, SkinConcernResult } from "@/types";

const CONCERN_LABELS: Record<string, string> = {
  acne: "Acne", dark_circles: "Dark Circles", hyperpigmentation: "Hyperpigmentation",
  fine_lines: "Fine Lines", enlarged_pores: "Enlarged Pores", redness: "Redness",
  dryness: "Dryness", oiliness: "Oiliness", uneven_texture: "Uneven Texture", dark_spots: "Dark Spots",
};

const SEVERITY_COLOR: Record<string, string> = {
  none: "success", mild: "gold", moderate: "rose", severe: "destructive",
};

interface SkinConcernsCardProps {
  acne: AcneAnalysisResult;
  darkCircles: DarkCircleResult;
  texture: SkinTextureResult;
  concerns: SkinConcernResult[];
}

export function SkinConcernsCard({ acne, darkCircles, texture, concerns }: SkinConcernsCardProps) {
  const hasAnyConcern = acne.detected || darkCircles.detected || concerns.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertCircle className="h-4 w-4 text-brand-gold" /> Skin Concerns
        </CardTitle>
        <CardDescription>Detected conditions and areas to focus your routine on</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!hasAnyConcern && (
          <div className="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
            <Sparkles className="h-4 w-4 text-emerald-400 shrink-0" />
            <p className="text-sm text-emerald-300">No significant concerns detected — your skin looks great!</p>
          </div>
        )}

        {/* Acne */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Acne &amp; Blemishes</span>
            <Badge variant={SEVERITY_COLOR[acne.severity] as any}>{acne.severity}</Badge>
          </div>
          {acne.detected && (
            <>
              <Progress value={acne.severity_score * 100} />
              <p className="text-xs text-muted-foreground/60">
                {acne.count} area{acne.count !== 1 ? "s" : ""} detected
                {acne.regions.length > 0 && ` — ${acne.regions.join(", ")}`}
              </p>
            </>
          )}
        </div>

        {/* Dark circles */}
        <div className="space-y-2 pt-3 border-t border-white/[0.06]">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Under-Eye Dark Circles</span>
            <Badge variant={SEVERITY_COLOR[darkCircles.category] as any}>{darkCircles.category}</Badge>
          </div>
          {darkCircles.detected && (
            <>
              <Progress value={darkCircles.severity * 100} />
              <p className="text-xs text-muted-foreground/60">
                ΔL* {darkCircles.lab_delta.toFixed(1)}
                {darkCircles.vascularity && " — vascular (blue/purple) tone detected"}
              </p>
            </>
          )}
        </div>

        {/* Texture */}
        <div className="space-y-2 pt-3 border-t border-white/[0.06]">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Skin Texture</span>
            <span className="text-xs text-muted-foreground">{Math.round(texture.overall_score * 100)}% smooth</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            {[
              { label: "Smoothness", value: texture.overall_score },
              { label: "Evenness",   value: texture.evenness },
              { label: "Pores",      value: 1 - texture.pore_visibility },
            ].map((m) => (
              <div key={m.label} className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-2.5">
                <p className="text-sm font-medium">{Math.round(m.value * 100)}</p>
                <p className="text-2xs text-muted-foreground/50 mt-0.5">{m.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* All concerns list */}
        {concerns.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-3 border-t border-white/[0.06]">
            {concerns.map((c, i) => (
              <Badge key={i} variant="outline">
                {CONCERN_LABELS[c.concern] ?? c.concern} · {c.region.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
