"use client";
/**
 * AuraFit — Hair, age estimation, and facial symmetry card (Stage 4).
 * Three compact sub-sections grouped to keep the results grid tidy.
 */
import { Wand2, CalendarDays, Scale } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreRing } from "./ScoreRing";
import type { AgeEstimationResult, HairAnalysisResult, SymmetryResult } from "@/types";

interface Props {
  age: AgeEstimationResult;
  hair: HairAnalysisResult;
  symmetry: SymmetryResult;
}

export function HairAgeSymmetryCard({ age, hair, symmetry }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Wand2 className="h-4 w-4 text-brand-gold" /> Hair, Age &amp; Symmetry
        </CardTitle>
        <CardDescription>Additional attributes detected from your photo</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Age estimation */}
        <div className="flex items-center justify-between rounded-xl bg-white/[0.02] border border-white/[0.05] px-4 py-3">
          <div className="flex items-center gap-3">
            <CalendarDays className="h-4 w-4 text-brand-gold/70" />
            <div>
              <p className="text-sm font-medium">Estimated Age</p>
              <p className="text-2xs text-muted-foreground/50">{age.model}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="font-display text-xl font-light">{age.age_range}</p>
            <p className="text-2xs text-muted-foreground/50">{Math.round(age.confidence * 100)}% confidence</p>
          </div>
        </div>

        {/* Hair */}
        {hair.hair_detected ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl border border-white/10 shrink-0" style={{ backgroundColor: hair.dominant_color }} />
              <div>
                <p className="text-sm font-medium capitalize">{hair.hair_type} hair</p>
                <div className="flex gap-1.5 mt-1 flex-wrap">
                  {hair.color_names.map((c) => (
                    <Badge key={c} variant="outline" className="capitalize">{c}</Badge>
                  ))}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              {[
                { label: "Texture", value: hair.texture_score },
                { label: "Shine",   value: hair.shine_score },
                { label: "Volume",  value: hair.volume_score },
              ].map((m) => (
                <div key={m.label} className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-2.5">
                  <p className="text-sm font-medium">{m.value != null ? Math.round(m.value * 100) : "—"}</p>
                  <p className="text-2xs text-muted-foreground/50 mt-0.5">{m.label}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground/50">Hair not clearly visible in this photo.</p>
        )}

        {/* Symmetry */}
        <div className="flex items-center gap-5 pt-3 border-t border-white/[0.06]">
          <ScoreRing value={symmetry.overall_score} size={72} label="Symmetry" />
          <div className="flex-1 space-y-1.5">
            {[
              { label: "Eyes",     value: symmetry.eye_symmetry },
              { label: "Mouth",    value: symmetry.mouth_symmetry },
              { label: "Nostrils", value: symmetry.nostril_symmetry },
              { label: "Jaw",      value: symmetry.jaw_symmetry },
            ].map((m) => (
              <div key={m.label} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{m.label}</span>
                <span className="font-mono text-foreground/70">{Math.round(m.value * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-muted-foreground/50 flex items-center gap-1.5">
          <Scale className="h-3 w-3" /> {symmetry.deviation_summary}
        </p>
      </CardContent>
    </Card>
  );
}
