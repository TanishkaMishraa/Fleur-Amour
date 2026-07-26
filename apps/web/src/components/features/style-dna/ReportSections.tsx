"use client";
/**
 * AuraFit — Style DNA Report Section components (Stage 8).
 * Individual section renderers: Skin, Color, Fashion, Fragrance, Hairstyle,
 * Personality, Occasion Guide, Recommendations.
 */
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { ColorSwatchRow } from "@/components/features/color/ColorSwatch";
import type {
  SkinProfile, ColorProfileSection, FashionProfile,
  FragranceProfileSection, HairstyleProfile, PersonalitySection, OccasionData,
} from "@/types/style-dna";

// ── Shared primitives ──────────────────────────────────────────────────────────

function SectionCard({ title, emoji, color, children, className }: {
  title: string; emoji: string; color: string; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={cn("luxury-card p-6 space-y-5", className)}>
      <div className="flex items-center gap-2.5">
        <span className="text-xl">{emoji}</span>
        <h3 className={cn("font-sans text-base font-semibold", color)}>{title}</h3>
      </div>
      {children}
    </div>
  );
}

function BulletList({ items, className }: { items: string[]; className?: string }) {
  return (
    <ul className={cn("space-y-1.5", className)}>
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-foreground/70">
          <span className="mt-1.5 h-1 w-1 rounded-full bg-brand-gold/60 flex-shrink-0" />
          {item}
        </li>
      ))}
    </ul>
  );
}

function SectionLabel({ label }: { label: string }) {
  return <p className="text-2xs uppercase tracking-widest text-muted-foreground/40 mb-2">{label}</p>;
}

// ── Skin Profile ───────────────────────────────────────────────────────────────

export function SkinProfileCard({ data }: { data: SkinProfile }) {
  return (
    <SectionCard title="Skin Profile" emoji="✨" color="text-emerald-400">
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: "Skin Tone",  value: data.tone },
          { label: "Skin Type",  value: data.type },
          { label: "Undertone",  value: data.undertone },
        ].map(({ label, value }) => value && (
          <div key={label} className="space-y-1">
            <p className="text-2xs text-muted-foreground/40 uppercase tracking-widest">{label}</p>
            <p className="text-sm font-semibold capitalize text-foreground">{value}</p>
          </div>
        ))}
      </div>

      {data.concerns.length > 0 && (
        <div>
          <SectionLabel label="Skin Concerns" />
          <div className="flex flex-wrap gap-2">
            {data.concerns.map((c) => (
              <Badge key={c} variant="default" className="text-2xs capitalize">
                {c.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {data.key_actives.length > 0 && (
        <div>
          <SectionLabel label="Recommended Actives" />
          <div className="flex flex-wrap gap-2">
            {data.key_actives.slice(0, 6).map((a) => (
              <Badge key={a} variant="gold" className="text-2xs">{a}</Badge>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {data.routine.morning.length > 0 && (
          <div>
            <SectionLabel label="Morning Routine" />
            <BulletList items={data.routine.morning.slice(0, 5)} />
          </div>
        )}
        {data.routine.evening.length > 0 && (
          <div>
            <SectionLabel label="Evening Routine" />
            <BulletList items={data.routine.evening.slice(0, 5)} />
          </div>
        )}
      </div>
    </SectionCard>
  );
}

// ── Color Profile ───────────────────────────────────────────────────────────────

export function ColorProfileCard({ data }: { data: ColorProfileSection }) {
  return (
    <SectionCard title="Color Profile" emoji="🎨" color="text-amber-400">
      <div className="flex items-start gap-4">
        <div>
          <p className="text-2xs text-muted-foreground/40 uppercase tracking-widest">Season</p>
          <p className="text-lg font-display font-light text-foreground mt-0.5">{data.season}</p>
          <p className="text-xs text-muted-foreground/60 mt-1 max-w-sm">{data.description}</p>
        </div>
      </div>

      {data.palette.best.length > 0 && (
        <div>
          <SectionLabel label="Your Best Colors" />
          <ColorSwatchRow colors={data.palette.best} size="md" showNames maxVisible={8} />
        </div>
      )}

      {data.palette.neutrals.length > 0 && (
        <div>
          <SectionLabel label="Core Neutrals" />
          <ColorSwatchRow colors={data.palette.neutrals} size="sm" showNames maxVisible={6} />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {data.dos.length > 0 && (
          <div>
            <SectionLabel label="Colors to Embrace" />
            <BulletList items={data.dos} />
          </div>
        )}
        {data.donts.length > 0 && (
          <div>
            <SectionLabel label="Colors to Avoid" />
            <BulletList items={data.donts} />
          </div>
        )}
      </div>

      {data.metal_tones.length > 0 && (
        <p className="text-sm text-foreground/70">
          <span className="text-muted-foreground/40 text-2xs uppercase tracking-widest mr-2">Best metals</span>
          {data.metal_tones.join("  ·  ")}
        </p>
      )}
    </SectionCard>
  );
}

// ── Fashion Profile ────────────────────────────────────────────────────────────

export function FashionProfileCard({ data }: { data: FashionProfile }) {
  return (
    <SectionCard title="Fashion Profile" emoji="👗" color="text-blue-400">
      <div className="space-y-1">
        <p className="text-2xs text-muted-foreground/40 uppercase tracking-widest">Your Archetype</p>
        <p className="text-lg font-display font-light text-foreground">{data.primary_archetype}</p>
        <p className="text-xs text-muted-foreground/50">
          with {data.secondary_archetype} tendencies
        </p>
        <p className="text-sm text-foreground/70 mt-2 leading-relaxed">
          {data.archetype_description}
        </p>
      </div>

      {data.body_guide && (
        <div>
          <SectionLabel label="Body Shape Guide" />
          <p className="text-sm text-foreground/70 mb-3">{data.body_guide.summary}</p>
          <div className="grid gap-4 sm:grid-cols-2">
            {data.body_guide.flatter.length > 0 && (
              <div>
                <p className="text-2xs text-emerald-400/60 uppercase tracking-widest mb-2">Flatter</p>
                <BulletList items={data.body_guide.flatter.slice(0, 4)} />
              </div>
            )}
            {data.body_guide.avoid.length > 0 && (
              <div>
                <p className="text-2xs text-red-400/60 uppercase tracking-widest mb-2">Avoid</p>
                <BulletList items={data.body_guide.avoid.slice(0, 3)} />
              </div>
            )}
          </div>
        </div>
      )}

      {data.capsule_wardrobe.length > 0 && (
        <div>
          <SectionLabel label="Your Capsule Wardrobe" />
          <div className="space-y-2">
            {data.capsule_wardrobe.slice(0, 6).map((item, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <span className="text-brand-gold/60 mt-0.5">✦</span>
                <div>
                  <span className="font-medium text-foreground">{item.item}</span>
                  {item.note && <span className="text-muted-foreground/50 ml-2 text-xs">— {item.note}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </SectionCard>
  );
}

// ── Fragrance Profile ─────────────────────────────────────────────────────────

export function FragranceProfileCard({ data }: { data: FragranceProfileSection }) {
  return (
    <SectionCard title="Fragrance Profile" emoji="🌸" color="text-purple-400">
      {data.personality && (
        <blockquote className="border-l-2 border-brand-gold/30 pl-4 italic text-sm text-foreground/70">
          "{data.personality}"
        </blockquote>
      )}

      <div className="flex flex-wrap gap-2">
        {data.families.map((f) => (
          <Badge key={f} variant="rose" className="text-xs capitalize">{f}</Badge>
        ))}
      </div>

      {data.preferred_notes.length > 0 && (
        <div>
          <SectionLabel label="Your Notes" />
          <div className="flex flex-wrap gap-1.5">
            {data.preferred_notes.slice(0, 8).map((n) => (
              <span key={n} className="text-2xs rounded-full border border-purple-400/20 bg-purple-400/5 px-2.5 py-1 text-purple-400 capitalize">
                {n}
              </span>
            ))}
          </div>
        </div>
      )}

      {Object.keys(data.occasion_guide).length > 0 && (
        <div>
          <SectionLabel label="Fragrance by Occasion" />
          <div className="space-y-2">
            {Object.entries(data.occasion_guide).map(([occ, rec]) => (
              <div key={occ} className="flex gap-3 text-sm">
                <span className="text-muted-foreground/50 capitalize flex-shrink-0 w-16">{occ}</span>
                <span className="text-foreground/70">{rec}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.layering_tip && (
        <p className="text-xs text-brand-gold/60 italic">{data.layering_tip}</p>
      )}
    </SectionCard>
  );
}

// ── Hairstyle Profile ─────────────────────────────────────────────────────────

export function HairstyleProfileCard({ data }: { data: HairstyleProfile }) {
  return (
    <SectionCard title="Hairstyle Profile" emoji="💇" color="text-rose-400">
      {data.face_shape && (
        <div className="flex gap-4 items-start">
          <div>
            <p className="text-2xs text-muted-foreground/40 uppercase tracking-widest">Face Shape</p>
            <p className="text-base font-semibold capitalize text-foreground mt-0.5">{data.face_shape}</p>
            <p className="text-sm text-foreground/60 mt-1 max-w-md">{data.face_shape_summary}</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {data.recommended_styles.length > 0 && (
          <div>
            <SectionLabel label="Recommended Styles" />
            <BulletList items={data.recommended_styles} />
          </div>
        )}
        {data.avoid_styles.length > 0 && (
          <div>
            <SectionLabel label="Avoid" />
            <BulletList items={data.avoid_styles} />
          </div>
        )}
      </div>

      {data.styling_tip && (
        <div className="rounded-xl border border-brand-gold/20 bg-brand-gold/5 px-4 py-3">
          <p className="text-sm text-brand-gold/80">💡 {data.styling_tip}</p>
        </div>
      )}

      {data.color_recommendations.length > 0 && (
        <div>
          <SectionLabel label="Hair Color Recommendations" />
          <div className="flex flex-wrap gap-2">
            {data.color_recommendations.map((c, i) => (
              <Badge key={i} variant="rose" className="text-2xs">{c}</Badge>
            ))}
          </div>
        </div>
      )}
    </SectionCard>
  );
}

// ── Occasion Guide ─────────────────────────────────────────────────────────────

export function OccasionGuideCard({ data }: { data: Record<string, OccasionData> }) {
  const OCCASION_ICONS: Record<string, string> = {
    work: "💼", casual: "☀️", evening: "🌙", special: "⭐",
  };
  return (
    <SectionCard title="Occasion Guide" emoji="📅" color="text-indigo-400">
      <div className="grid gap-5 sm:grid-cols-2">
        {Object.entries(data).map(([occ, occ_data]) => (
          <div key={occ} className="space-y-2.5 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
            <div className="flex items-center gap-2">
              <span className="text-lg">{OCCASION_ICONS[occ] ?? "✦"}</span>
              <p className="text-sm font-semibold text-foreground capitalize">{occ}</p>
            </div>
            <div className="space-y-1.5 text-xs">
              <p><span className="text-muted-foreground/40">Outfit: </span><span className="text-foreground/70">{occ_data.outfit_formula}</span></p>
              <p><span className="text-muted-foreground/40">Beauty: </span><span className="text-foreground/70">{occ_data.beauty_look}</span></p>
              <p><span className="text-muted-foreground/40">Scent: </span><span className="text-foreground/70">{occ_data.fragrance}</span></p>
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

// ── Personality ────────────────────────────────────────────────────────────────

export function PersonalityCard({ data }: { data: PersonalitySection }) {
  const dims = data.dimensions || {};
  const axes = [
    { label: "Classic ↔ Avant-Garde", value: dims.style_axis ?? 0.5 },
    { label: "Understated ↔ Bold",    value: dims.energy_axis ?? 0.5 },
    { label: "Relaxed ↔ Tailored",    value: dims.structure_axis ?? 0.5 },
    { label: "Minimalist ↔ Romantic", value: dims.romance_axis ?? 0.5 },
  ];
  return (
    <SectionCard title="Your Style Personality" emoji="🧭" color="text-brand-gold">
      <div className="space-y-1">
        <p className="text-base font-semibold text-foreground">{data.archetype_blend}</p>
        {data.lifestyle_summary && <p className="text-sm text-foreground/60">{data.lifestyle_summary}</p>}
      </div>

      <div className="space-y-4">
        {axes.map(({ label, value }) => (
          <div key={label} className="space-y-1.5">
            <div className="flex justify-between text-2xs text-muted-foreground/50">
              <span>{label}</span>
              <span className="text-brand-gold">{Math.round(value * 100)}%</span>
            </div>
            <div className="h-1 rounded-full bg-white/[0.05]">
              <motion.div
                className="h-full rounded-full bg-gold-gradient"
                initial={{ width: 0 }}
                animate={{ width: `${value * 100}%` }}
                transition={{ duration: 0.7, ease: [0.23, 1, 0.32, 1] }}
              />
            </div>
          </div>
        ))}
      </div>

      {data.beauty_philosophy && (
        <blockquote className="border-l-2 border-brand-gold/30 pl-4 text-sm italic text-foreground/70">
          "{data.beauty_philosophy}"
        </blockquote>
      )}
    </SectionCard>
  );
}
