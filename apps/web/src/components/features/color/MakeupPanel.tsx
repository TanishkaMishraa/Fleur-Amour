"use client";
/**
 * AuraFit — MakeupPanel.
 * Displays the full makeup colour roadmap: foundation, blush, eyeshadow,
 * liner, highlight, contour. Each section uses ColorSwatchRow.
 */
import { cn } from "@/lib/utils";
import type { MakeupColorRecommendation } from "@/types/color";
import { ColorSwatchRow } from "./ColorSwatch";

interface MakeupPanelProps {
  makeup: MakeupColorRecommendation;
  className?: string;
}

const FINISH_TIPS: Record<string, string> = {
  satin:     "Satin finish — balanced radiance for most skin types",
  luminous:  "Luminous finish — lit-from-within glow for dry skin",
  matte:     "Matte finish — poreless look for oily skin",
  dewy:      "Dewy finish — hydrating for dry and mature skin",
};

export function MakeupPanel({ makeup, className }: MakeupPanelProps) {
  return (
    <div className={cn("luxury-card p-6 space-y-7", className)}>
      <div className="space-y-1">
        <h3 className="font-sans text-base font-semibold text-foreground">Makeup Colour Guide</h3>
        <p className="text-sm text-muted-foreground/60">
          Shades chosen specifically for your season and undertone.
        </p>
      </div>

      {/* Foundation */}
      <Section label="Foundation">
        <div className="flex flex-wrap gap-4 text-sm">
          <Chip label="Undertone" value={makeup.foundation_undertone} />
          <Chip label="Finish"    value={makeup.foundation_finish} />
        </div>
        {FINISH_TIPS[makeup.foundation_finish] && (
          <p className="text-xs text-muted-foreground/50 italic mt-2">
            {FINISH_TIPS[makeup.foundation_finish]}
          </p>
        )}
      </Section>

      {/* Blush */}
      <Section label="Blush">
        <ColorSwatchRow colors={makeup.blush_shades} size="md" showNames />
      </Section>

      {/* Eyeshadow */}
      <Section label="Eyeshadow Palettes">
        <div className="space-y-4">
          {makeup.eyeshadow_palettes.map((pal) => (
            <div key={pal.name} className="space-y-2">
              <div className="flex items-center gap-2">
                <p className="text-xs font-medium text-foreground/70">{pal.name}</p>
                <span className="text-2xs text-muted-foreground/40 capitalize">{pal.finish}</span>
              </div>
              <div className="flex gap-1.5">
                {pal.shades.map((hex: string) => (
                  <div
                    key={hex}
                    className="h-7 w-7 rounded-lg ring-1 ring-white/10 flex-shrink-0"
                    style={{ backgroundColor: hex }}
                    title={hex}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Liner */}
      <Section label="Eye Liner">
        <ColorSwatchRow colors={makeup.eyeliner_colors} size="sm" showNames />
      </Section>

      {/* Highlight + contour side-by-side */}
      <div className="grid grid-cols-2 gap-6">
        <Section label="Highlight">
          <ColorSwatchRow colors={makeup.highlight_shades} size="sm" showNames />
        </Section>
        <Section label="Contour">
          <ColorSwatchRow colors={makeup.contour_shades} size="sm" showNames />
        </Section>
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">{label}</p>
      {children}
    </div>
  );
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-muted-foreground/50">{label}:</span>
      <span className="text-xs font-medium text-foreground/80 capitalize">{value}</span>
    </div>
  );
}
