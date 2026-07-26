"use client";
/**
 * AuraFit — Skin tone & undertone result card (Stage 4).
 * Displays the detected hex swatch, Fitzpatrick scale, ITA° angle,
 * and undertone classification with a visual gradient indicator.
 */
import { motion } from "framer-motion";
import { Droplet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SkinToneResult } from "@/types";

const UNDERTONE_COPY: Record<string, { label: string; gradient: string; desc: string }> = {
  warm:    { label: "Warm",    gradient: "from-amber-400 to-orange-500",  desc: "Golden, peachy, or yellow hues" },
  cool:    { label: "Cool",    gradient: "from-rose-300 to-blue-400",     desc: "Pink, red, or bluish hues" },
  neutral: { label: "Neutral", gradient: "from-amber-200 to-rose-200",    desc: "A balanced mix of warm and cool" },
};

const FITZPATRICK_LABELS: Record<number, string> = {
  1: "Type I — Very fair",
  2: "Type II — Fair",
  3: "Type III — Medium",
  4: "Type IV — Olive",
  5: "Type V — Brown",
  6: "Type VI — Deep",
};

export function SkinToneCard({ data }: { data: SkinToneResult }) {
  const undertone = UNDERTONE_COPY[data.undertone] ?? UNDERTONE_COPY.neutral;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Droplet className="h-4 w-4 text-brand-gold" /> Skin Tone &amp; Undertone
        </CardTitle>
        <CardDescription>Detected from multiple facial regions using CIELAB analysis</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center gap-4">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            className="h-16 w-16 rounded-2xl shadow-luxury border border-white/10"
            style={{ backgroundColor: data.hex_color }}
          />
          <div className="space-y-1">
            <p className="font-display text-xl font-light capitalize">{data.tone}</p>
            <p className="text-xs text-muted-foreground font-mono">{data.hex_color}</p>
            <Badge variant="gold">{FITZPATRICK_LABELS[data.fitzpatrick] ?? `Type ${data.fitzpatrick}`}</Badge>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Undertone</span>
            <span className="font-medium text-foreground">{undertone.label}</span>
          </div>
          <div className={`h-2 w-full rounded-full bg-gradient-to-r ${undertone.gradient} opacity-80`} />
          <p className="text-xs text-muted-foreground/60">{undertone.desc}</p>
        </div>

        <div className="grid grid-cols-3 gap-3 pt-2 border-t border-white/[0.06]">
          <div>
            <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">ITA°</p>
            <p className="text-sm font-medium mt-0.5">{data.ita_angle.toFixed(1)}°</p>
          </div>
          <div>
            <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">L*</p>
            <p className="text-sm font-medium mt-0.5">{data.lab_values.L.toFixed(1)}</p>
          </div>
          <div>
            <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">Confidence</p>
            <p className="text-sm font-medium mt-0.5">{Math.round(data.confidence * 100)}%</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
