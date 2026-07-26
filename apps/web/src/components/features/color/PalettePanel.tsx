"use client";
/**
 * AuraFit — PalettePanel.
 * Renders the user's full personal color palette with hero swatch,
 * best colors, neutrals, accents, and colours to avoid.
 */
import { cn } from "@/lib/utils";
import type { PersonalPalette } from "@/types/color";
import { ColorSwatchRow, HeroSwatch } from "./ColorSwatch";
import { GoldDivider } from "@/components/shared/GoldDivider";

interface PalettePanelProps {
  palette: PersonalPalette;
  className?: string;
}

const SECTION_LABELS: Array<{
  key: keyof Omit<PersonalPalette, "hero_color">;
  label: string;
  subtitle: string;
  bad?: boolean;
}> = [
  { key: "best",     label: "Your Best Colors",  subtitle: "Wear these closest to your face for maximum impact" },
  { key: "neutrals", label: "Core Neutrals",      subtitle: "Build your wardrobe foundation with these" },
  { key: "accents",  label: "Signature Accents",  subtitle: "Statement colours that energise your palette" },
  { key: "avoid",    label: "Colours to Avoid",   subtitle: "These shades can clash with your natural colouring", bad: true },
];

export function PalettePanel({ palette, className }: PalettePanelProps) {
  return (
    <div className={cn("luxury-card p-6 space-y-8", className)}>
      {/* Hero colour */}
      <div className="flex flex-col items-center gap-2 py-4">
        <p className="text-2xs uppercase tracking-widest text-muted-foreground/50">
          Your signature colour
        </p>
        <HeroSwatch color={palette.hero_color} />
        <p className="text-xs text-muted-foreground/40 text-center max-w-xs">
          This is the single most flattering shade for your season.
          Wear it near your face to make your eyes, skin, and hair glow.
        </p>
      </div>

      <GoldDivider />

      {SECTION_LABELS.map(({ key, label, subtitle, bad }) => {
        const colors = palette[key];
        if (!colors || colors.length === 0) return null;
        return (
          <div key={key} className="space-y-3">
            <div>
              <p className={cn(
                "text-sm font-semibold",
                bad ? "text-red-400/80" : "text-foreground/80"
              )}>
                {label}
              </p>
              <p className="text-xs text-muted-foreground/50 mt-0.5">{subtitle}</p>
            </div>
            <ColorSwatchRow
              colors={colors}
              size="md"
              showNames
              maxVisible={10}
              className={bad ? "opacity-60" : ""}
            />
            {bad && (
              <p className="text-2xs text-red-400/50 italic">
                Click any swatch to copy its hex — use these as a reference to avoid.
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
