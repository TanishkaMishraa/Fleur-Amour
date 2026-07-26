"use client";
/**
 * AuraFit — HairColorPanel, OutfitColorPanel, JewelryPanel.
 * Hair colour, outfit palette, and jewellery recommendation components.
 */
import { cn } from "@/lib/utils";
import type { HairColorOption, OutfitPalette, JewelryRecommendation } from "@/types/color";
import { ColorSwatchRow } from "./ColorSwatch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// ── Hair Color Panel ──────────────────────────────────────────────────────────

const COMMITMENT_BADGE: Record<string, "gold" | "default"> = {
  permanent:       "gold",
  "semi-permanent": "default",
  temporary:        "default",
};

const MAINTENANCE_COLORS: Record<string, string> = {
  Low:    "text-emerald-400",
  Medium: "text-amber-400",
  High:   "text-rose-400",
};

interface HairColorPanelProps {
  options: HairColorOption[];
  className?: string;
}

export function HairColorPanel({ options, className }: HairColorPanelProps) {
  return (
    <div className={cn("luxury-card p-6 space-y-5", className)}>
      <div className="space-y-1">
        <h3 className="font-sans text-base font-semibold">Hair Color Recommendations</h3>
        <p className="text-sm text-muted-foreground/60">
          Shades and techniques that amplify your seasonal colouring.
        </p>
      </div>

      <div className="space-y-3">
        {options.map((opt, i) => (
          <div
            key={i}
            className="flex gap-4 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 hover:border-white/[0.12] transition-colors"
          >
            {/* Colour preview */}
            <div className="flex-shrink-0 space-y-1 flex flex-col items-center">
              <div
                className="h-12 w-12 rounded-xl ring-1 ring-white/10 shadow-lg"
                style={{ backgroundColor: opt.hex }}
              />
              <p className="text-2xs font-mono text-muted-foreground/40">{opt.hex}</p>
            </div>

            <div className="flex-1 min-w-0 space-y-1.5">
              <div className="flex items-start justify-between gap-2 flex-wrap">
                <p className="text-sm font-semibold">{opt.name}</p>
                <div className="flex gap-1.5 flex-wrap">
                  <Badge variant={COMMITMENT_BADGE[opt.commitment] ?? "default"} className="text-2xs capitalize">
                    {opt.commitment}
                  </Badge>
                  <Badge variant="default" className="text-2xs capitalize">{opt.technique}</Badge>
                </div>
              </div>

              <p className="text-xs text-muted-foreground/60 leading-relaxed">{opt.rationale}</p>

              <p className="text-2xs">
                Maintenance:
                <span className={cn("ml-1 font-semibold", MAINTENANCE_COLORS[opt.maintenance])}>
                  {opt.maintenance}
                </span>
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Outfit Color Panel ────────────────────────────────────────────────────────

interface OutfitColorPanelProps {
  outfits: Record<string, OutfitPalette>;
  className?: string;
}

const OCCASION_LABELS: Record<string, { label: string; emoji: string }> = {
  work:    { label: "Work",    emoji: "💼" },
  evening: { label: "Evening", emoji: "🌙" },
  casual:  { label: "Casual",  emoji: "☀️" },
  sport:   { label: "Sport",   emoji: "🏃" },
};

export function OutfitColorPanel({ outfits, className }: OutfitColorPanelProps) {
  const occasions = Object.keys(outfits);

  return (
    <div className={cn("luxury-card p-6 space-y-5", className)}>
      <div className="space-y-1">
        <h3 className="font-sans text-base font-semibold">Outfit Color Palettes</h3>
        <p className="text-sm text-muted-foreground/60">
          Colour combinations by occasion, tailored to your season.
        </p>
      </div>

      <Tabs defaultValue={occasions[0]}>
        <TabsList className="w-full">
          {occasions.map((occ) => {
            const meta = OCCASION_LABELS[occ] ?? { label: occ, emoji: "✨" };
            return (
              <TabsTrigger key={occ} value={occ} className="flex-1 gap-1.5">
                <span>{meta.emoji}</span>
                <span className="hidden sm:inline">{meta.label}</span>
              </TabsTrigger>
            );
          })}
        </TabsList>

        {occasions.map((occ) => {
          const palette = outfits[occ];
          return (
            <TabsContent key={occ} value={occ} className="mt-5 space-y-5">
              {/* Styling tip */}
              <div className="rounded-xl border border-brand-gold/20 bg-brand-gold/5 px-4 py-3">
                <p className="text-sm text-brand-gold/80 leading-relaxed">
                  💡 {palette.styling_tip}
                </p>
              </div>

              <div className="grid gap-5 sm:grid-cols-2">
                <div className="space-y-3">
                  <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">
                    Base colours
                  </p>
                  <ColorSwatchRow colors={palette.base_colors} size="md" showNames />
                </div>
                <div className="space-y-3">
                  <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">
                    Accent colours
                  </p>
                  <ColorSwatchRow colors={palette.accent_colors} size="md" showNames />
                </div>
              </div>
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}

// ── Jewelry Panel ─────────────────────────────────────────────────────────────

const METAL_DISPLAY: Record<string, { label: string; hex: string }> = {
  gold:        { label: "Gold",       hex: "#CFB53B" },
  "rose-gold": { label: "Rose Gold",  hex: "#B76E79" },
  silver:      { label: "Silver",     hex: "#C0C0C0" },
  platinum:    { label: "Platinum",   hex: "#E5E4E2" },
  "white-gold":{ label: "White Gold", hex: "#D4D4D4" },
  bronze:      { label: "Bronze",     hex: "#CD7F32" },
  copper:      { label: "Copper",     hex: "#B87333" },
  "antique-gold":{ label: "Antique Gold", hex: "#B8860B" },
};

interface JewelryPanelProps {
  jewelry: JewelryRecommendation;
  className?: string;
}

export function JewelryPanel({ jewelry, className }: JewelryPanelProps) {
  return (
    <div className={cn("luxury-card p-6 space-y-6", className)}>
      <div className="space-y-1">
        <h3 className="font-sans text-base font-semibold">Jewellery Guide</h3>
        <p className="text-sm text-muted-foreground/60">{jewelry.rationale}</p>
      </div>

      {/* Metals */}
      <div className="space-y-3">
        <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">Metals</p>
        <div className="flex flex-wrap gap-3">
          {jewelry.metal_tones.map((metal) => {
            const meta = METAL_DISPLAY[metal] ?? { label: metal, hex: "#C0C0C0" };
            return (
              <div key={metal} className="flex items-center gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2">
                <div
                  className="h-4 w-4 rounded-full ring-1 ring-white/20"
                  style={{ backgroundColor: meta.hex }}
                />
                <span className="text-xs font-medium text-foreground/70">{meta.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Gemstones */}
      <div className="space-y-3">
        <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">Gemstones</p>
        <ColorSwatchRow colors={jewelry.gem_colors} size="md" showNames />
      </div>

      {/* Style notes */}
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
        <p className="text-xs text-muted-foreground/70 leading-relaxed">
          ✨ {jewelry.style_notes}
        </p>
      </div>
    </div>
  );
}
