"use client";
/**
 * AuraFit — SimilarityBar component.
 * Animated progress bar for displaying similarity scores in the alternative cards.
 * Colour-coded: green ≥80%, gold 60–80%, amber 40–60%, muted <40%.
 */
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface SimilarityBarProps {
  score:     number;    // 0–1
  label?:    string;
  size?:     "sm" | "md";
  showPct?:  boolean;
  className?:string;
}

const getColor = (score: number) => {
  if (score >= 0.80) return { bar: "bg-emerald-400",   text: "text-emerald-400",  glow: "shadow-emerald-400/30" };
  if (score >= 0.65) return { bar: "bg-brand-gold",    text: "text-brand-gold",   glow: "shadow-brand-gold/30" };
  if (score >= 0.50) return { bar: "bg-amber-400",     text: "text-amber-400",    glow: "shadow-amber-400/30" };
  return                    { bar: "bg-muted-foreground/40", text: "text-muted-foreground/50", glow: "" };
};

export function SimilarityBar({ score, label, size = "md", showPct = true, className }: SimilarityBarProps) {
  const pct    = Math.round(score * 100);
  const colors = getColor(score);
  const h      = size === "sm" ? "h-1" : "h-1.5";

  return (
    <div className={cn("space-y-1", className)}>
      {(label || showPct) && (
        <div className="flex justify-between items-center">
          {label && <span className="text-2xs text-muted-foreground/50">{label}</span>}
          {showPct && <span className={cn("text-2xs font-semibold tabular-nums", colors.text)}>{pct}%</span>}
        </div>
      )}
      <div className={cn("w-full rounded-full bg-white/[0.05]", h)}>
        <motion.div
          className={cn("rounded-full", h, colors.bar)}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: [0.23, 1, 0.32, 1] }}
        />
      </div>
    </div>
  );
}

/** Circular score ring for the hero similarity display */
export function SimilarityRing({ score, size = 80 }: { score: number; size?: number }) {
  const pct    = Math.round(score * 100);
  const colors = getColor(score);
  const r      = (size / 2) - 6;
  const circ   = 2 * Math.PI * r;
  const dash   = (pct / 100) * circ;

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={5} />
        <motion.circle
          cx={size/2} cy={size/2} r={r} fill="none"
          stroke="currentColor" strokeWidth={5}
          strokeLinecap="round"
          className={colors.text}
          strokeDasharray={`${circ} ${circ}`}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - dash }}
          transition={{ duration: 0.9, ease: [0.23, 1, 0.32, 1] }}
        />
      </svg>
      <div className="absolute text-center">
        <p className={cn("text-sm font-bold tabular-nums leading-none", colors.text)}>{pct}%</p>
        <p className="text-2xs text-muted-foreground/40 mt-0.5">match</p>
      </div>
    </div>
  );
}
