"use client";
/**
 * AuraFit — SeasonCard.
 * Hero card showing the user's season, confidence, key traits,
 * celebrity examples, and the 3 color axes (contrast/chroma/value).
 */
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { SeasonClassification } from "@/types/color";
import { SEASON_DISPLAY, SEASON_FAMILY_COLORS } from "@/types/color";
import { SeasonBadge } from "./SeasonBadge";
import { Progress } from "@/components/ui/progress";

interface SeasonCardProps {
  season: SeasonClassification;
  className?: string;
}

const CONTRAST_LABELS = { low: "Soft contrast", medium: "Medium contrast", high: "High contrast" };
const CHROMA_LABELS   = { muted: "Muted / dusty", soft: "Soft / gentle", clear: "Clear / bright", bright: "Vivid / saturated" };
const VALUE_LABELS    = { light: "Light value", medium: "Medium value", deep: "Deep value" };
const CONTRAST_PCT    = { low: 25, medium: 55, high: 90 };
const CHROMA_PCT      = { muted: 15, soft: 35, clear: 65, bright: 95 };
const VALUE_PCT       = { light: 20, medium: 55, deep: 90 };

export function SeasonCard({ season, className }: SeasonCardProps) {
  const display = SEASON_DISPLAY[season.season] ?? SEASON_DISPLAY["true_spring"];
  const family  = SEASON_FAMILY_COLORS[season.season_family];

  return (
    <div className={cn("luxury-card overflow-hidden", className)}>
      {/* Gradient header */}
      <div className={cn(
        "relative p-8 bg-gradient-to-br",
        display.gradient,
        "noise"
      )}>
        <div className="absolute inset-0 bg-black/10" />
        <div className="relative z-10 flex flex-col gap-4">
          <SeasonBadge season={season.season} size="lg" />
          <div>
            <p className={cn("text-sm font-sans leading-relaxed max-w-md", display.textColor, "opacity-80")}>
              {season.description}
            </p>
          </div>
          {/* Confidence */}
          <div className="flex items-center gap-3">
            <span className={cn("text-2xs font-medium opacity-70", display.textColor)}>
              Match confidence
            </span>
            <div className="flex-1 max-w-[160px]">
              <div className="h-1.5 rounded-full bg-black/20 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-white/70"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.round(season.confidence * 100)}%` }}
                  transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] }}
                />
              </div>
            </div>
            <span className={cn("text-xs font-semibold", display.textColor)}>
              {Math.round(season.confidence * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-6 space-y-6">
        {/* Color axes */}
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Contrast",  value: CONTRAST_LABELS[season.contrast_level], pct: CONTRAST_PCT[season.contrast_level] },
            { label: "Chroma",    value: CHROMA_LABELS[season.chroma_level],     pct: CHROMA_PCT[season.chroma_level] },
            { label: "Value",     value: VALUE_LABELS[season.value_level],        pct: VALUE_PCT[season.value_level] },
          ].map(({ label, value, pct }) => (
            <div key={label} className="space-y-2">
              <p className="text-2xs uppercase tracking-widest text-muted-foreground/50">{label}</p>
              <Progress value={pct} gold className="h-1" />
              <p className="text-xs text-foreground/70">{value}</p>
            </div>
          ))}
        </div>

        {/* Key characteristics */}
        <div>
          <p className="text-2xs uppercase tracking-widest text-muted-foreground/50 mb-3">
            Key characteristics
          </p>
          <ul className="space-y-2">
            {season.key_characteristics.map((trait, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-foreground/70">
                <span className={cn("mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full", family.text.replace("text-", "bg-"))} />
                {trait}
              </li>
            ))}
          </ul>
        </div>

        {/* Celebrity examples */}
        {season.celebrity_examples.length > 0 && (
          <div>
            <p className="text-2xs uppercase tracking-widest text-muted-foreground/50 mb-2">
              Season icons
            </p>
            <div className="flex flex-wrap gap-2">
              {season.celebrity_examples.map((name) => (
                <span
                  key={name}
                  className={cn(
                    "inline-flex items-center rounded-full px-3 py-1 text-2xs font-medium",
                    family.bg, family.text, family.border, "border"
                  )}
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
