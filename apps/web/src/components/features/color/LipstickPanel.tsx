"use client";
/**
 * AuraFit — LipstickPanel.
 * Displays recommended lipstick shades as scrollable cards.
 * Each card shows the swatch, shade name, finish, occasion tag, rationale,
 * and brand suggestions.
 */
import { cn } from "@/lib/utils";
import type { LipstickShade } from "@/types/color";
import { Badge } from "@/components/ui/badge";

interface LipstickPanelProps {
  shades: LipstickShade[];
  className?: string;
}

const OCCASION_VARIANT: Record<string, "gold" | "default" | "rose"> = {
  everyday:     "default",
  professional: "default",
  evening:      "gold",
  special:      "rose",
};

const INTENSITY_DOT: Record<string, string> = {
  light:  "opacity-40",
  medium: "opacity-70",
  bold:   "opacity-100",
};

export function LipstickPanel({ shades, className }: LipstickPanelProps) {
  return (
    <div className={cn("luxury-card p-6 space-y-5", className)}>
      <div className="space-y-1">
        <h3 className="font-sans text-base font-semibold text-foreground">Lipstick Shades</h3>
        <p className="text-sm text-muted-foreground/60">
          Curated shades that harmonise perfectly with your season.
        </p>
      </div>

      <div className="space-y-3">
        {shades.map((shade, i) => (
          <div
            key={i}
            className="flex gap-4 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 hover:border-white/[0.12] transition-colors"
          >
            {/* Colour swatch */}
            <div
              className="h-14 w-14 flex-shrink-0 rounded-xl shadow-lg ring-1 ring-white/10"
              style={{ backgroundColor: shade.hex }}
            />

            {/* Content */}
            <div className="flex-1 min-w-0 space-y-1.5">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-foreground leading-tight">{shade.shade}</p>
                <Badge
                  variant={OCCASION_VARIANT[shade.occasion] as any ?? "default"}
                  className="text-2xs flex-shrink-0 capitalize"
                >
                  {shade.occasion}
                </Badge>
              </div>

              <div className="flex items-center gap-3 text-2xs text-muted-foreground/50">
                <span className="capitalize">{shade.finish}</span>
                <span>·</span>
                <span className="flex items-center gap-1">
                  Intensity:
                  {["light", "medium", "bold"].map((level) => (
                    <span
                      key={level}
                      className={cn(
                        "inline-block h-1.5 w-1.5 rounded-full",
                        "bg-foreground",
                        INTENSITY_DOT[level],
                        level === shade.intensity ? "ring-1 ring-foreground/30" : ""
                      )}
                    />
                  ))}
                </span>
                <span className="font-mono">{shade.hex}</span>
              </div>

              <p className="text-xs text-muted-foreground/60 leading-relaxed">{shade.rationale}</p>

              {shade.brands.length > 0 && (
                <p className="text-2xs text-muted-foreground/40">
                  Try: {shade.brands.join(" · ")}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
