"use client";
/**
 * AuraFit — SeasonBadge component.
 * Displays the color season with its gradient, emoji, and label.
 * Used in the header, history cards, and dashboard.
 */
import { cn } from "@/lib/utils";
import type { ColorSeason } from "@/types/color";
import { SEASON_DISPLAY } from "@/types/color";

interface SeasonBadgeProps {
  season: ColorSeason;
  size?: "sm" | "md" | "lg";
  showFamily?: boolean;
  className?: string;
}

const sizeMap = {
  sm: "px-3 py-1.5 text-2xs gap-1.5",
  md: "px-4 py-2   text-xs  gap-2",
  lg: "px-5 py-2.5 text-sm  gap-2.5",
};

const emojiSize = { sm: "text-sm", md: "text-base", lg: "text-lg" };

export function SeasonBadge({ season, size = "md", showFamily, className }: SeasonBadgeProps) {
  const display = SEASON_DISPLAY[season] ?? SEASON_DISPLAY["true_spring"];
  const label = display.label;

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full font-sans font-semibold tracking-wide",
        "bg-gradient-to-r shadow-sm",
        display.gradient,
        display.textColor,
        sizeMap[size],
        className
      )}
    >
      <span className={emojiSize[size]}>{display.emoji}</span>
      <span>{label}</span>
    </div>
  );
}

/** Minimal dot indicator for lists / small spaces */
export function SeasonDot({ season, className }: { season: ColorSeason; className?: string }) {
  const display = SEASON_DISPLAY[season] ?? SEASON_DISPLAY["true_spring"];
  return (
    <span
      className={cn("inline-block h-2.5 w-2.5 rounded-full bg-gradient-to-br", display.gradient, className)}
      title={display.label}
    />
  );
}
