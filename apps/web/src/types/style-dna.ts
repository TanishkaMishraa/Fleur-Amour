// AuraFit — Style DNA System types (Stage 8)

import type { ColorEntry } from "./color";

// ── Quiz types ────────────────────────────────────────────────────────────────

export type QuestionType = "single" | "multi" | "scale" | "image_grid" | "text";

export interface QuizOption {
  id:     string;
  label:  string;
  image?: string | null;
}

export interface QuizQuestion {
  id:           string;
  section:      string;
  index:        number;
  type:         QuestionType;
  question:     string;
  subtitle:     string | null;
  options:      QuizOption[];
  scale_min?:   number;
  scale_max?:   number;
  scale_labels?:[string, string];
  max_select?:  number;
}

export interface QuizSection {
  [key: string]: QuizQuestion[];
}

export interface QuizDefinition {
  version:       string;
  total:         number;
  sections:      QuizSection;
  section_order: string[];
}

export interface QuizSessionState {
  session_id:   string;
  current_step: number;
  total_steps:  number;
  status:       "in_progress" | "completed" | "abandoned";
  quiz_version: string;
}

export interface QuizCompletionResult {
  session_id:          string;
  primary_archetype:   string;
  secondary_archetype: string;
  budget_tier:         string;
  lifestyle_tags:      string[];
  style_axes:          { style: number; energy: number; structure: number };
  occasion_mix:        { work: number; casual: number; evening: number };
}

// ── Report types ──────────────────────────────────────────────────────────────

export interface SkinProfile {
  tone:            string | null;
  type:            string | null;
  undertone:       string | null;
  concerns:        string[];
  key_actives:     string[];
  routine:         { morning: string[]; evening: string[]; weekly: string[] };
  acne_severity:   string;
  dark_circles:    boolean;
}

export interface ColorProfileSection {
  season:          string;
  season_family:   string;
  description:     string;
  palette: {
    best:          ColorEntry[];
    neutrals:      ColorEntry[];
    accents:       ColorEntry[];
  };
  dos:             string[];
  donts:           string[];
  metal_tones:     string[];
  wardrobe_neutrals:string[];
}

export interface BodyGuide {
  summary:  string;
  flatter:  string[];
  avoid:    string[];
  tips:     string;
}

export interface CapsuleItem {
  item: string;
  note: string;
}

export interface FashionProfile {
  primary_archetype:    string;
  secondary_archetype:  string;
  archetype_description:string;
  body_shape:           string | null;
  body_guide:           BodyGuide;
  capsule_wardrobe:     CapsuleItem[];
  signature_pieces:     string[];
  style_axes:           Record<string, number>;
  occasion_split:       Record<string, number>;
  budget_tier:          string;
  lifestyle_tags:       string[];
}

export interface FragranceProfileSection {
  families:         string[];
  preferred_notes:  string[];
  avoided_notes:    string[];
  intensity:        string | null;
  longevity:        string | null;
  personality:      string;
  occasion_guide:   Record<string, string>;
  layering_tip:     string;
}

export interface HairstyleProfile {
  face_shape:             string | null;
  hair_type:              string | null;
  current_color:          string | null;
  recommended_styles:     string[];
  avoid_styles:           string[];
  face_shape_summary:     string;
  styling_tip:            string;
  color_recommendations:  string[];
  care_routine:           { wash: string; treatments: string[]; styling: string };
  symmetry_score:         number | null;
}

export interface PersonalitySection {
  primary_archetype:   string;
  secondary_archetype: string;
  archetype_blend:     string;
  dimensions:          Record<string, number>;
  lifestyle_summary:   string;
  shopping_persona:    string;
  beauty_philosophy:   string;
}

export interface OccasionData {
  outfit_formula:  string;
  colour_palette?: string[];
  beauty_look:     string;
  fragrance:       string;
}

export interface StyleDNAReport {
  id:                        string;
  status:                    "queued" | "generating" | "ready" | "failed";
  headline:                  string | null;
  narrative:                 string | null;
  beauty_profile:            Record<string, unknown> | null;
  skin_profile:              SkinProfile | null;
  color_profile_section:     ColorProfileSection | null;
  fashion_profile:           FashionProfile | null;
  fragrance_profile_section: FragranceProfileSection | null;
  hairstyle_profile:         HairstyleProfile | null;
  recommendations:           Record<string, unknown[]> | null;
  personality:               PersonalitySection | null;
  occasion_guide:            Record<string, OccasionData> | null;
  pdf_url:                   string | null;
  pdf_size_kb:               number | null;
  is_current:                boolean;
  created_at:                string;
}

// ── Archetype display metadata ─────────────────────────────────────────────────

export const ARCHETYPE_META: Record<string, {
  emoji:      string;
  color:      string;
  gradient:   string;
  tagline:    string;
}> = {
  "The Classic":       { emoji: "👑",  color: "text-amber-400",   gradient: "from-amber-500 to-yellow-400",   tagline: "Timeless. Always right." },
  "The Minimalist":    { emoji: "◻️",  color: "text-slate-400",   gradient: "from-slate-500 to-zinc-400",     tagline: "Less, but perfectly so." },
  "The Romantic":      { emoji: "🌸",  color: "text-rose-400",    gradient: "from-rose-500 to-pink-400",      tagline: "Beauty in the details." },
  "The Bohemian":      { emoji: "🌿",  color: "text-emerald-400", gradient: "from-emerald-500 to-teal-400",   tagline: "Free-spirited and free." },
  "The Edgy":          { emoji: "⚡",  color: "text-violet-400",  gradient: "from-violet-600 to-purple-400",  tagline: "Rules are suggestions." },
  "The Athletic":      { emoji: "💪",  color: "text-blue-400",    gradient: "from-blue-500 to-cyan-400",      tagline: "Function is the new fashion." },
  "The Glamorous":     { emoji: "✨",  color: "text-brand-gold",  gradient: "from-brand-gold to-amber-400",   tagline: "Life is a stage." },
  "The Preppy":        { emoji: "🎀",  color: "text-indigo-400",  gradient: "from-indigo-500 to-blue-400",    tagline: "Polished by instinct." },
  "The Creative":      { emoji: "🎨",  color: "text-orange-400",  gradient: "from-orange-500 to-amber-400",   tagline: "Self-expression, always." },
  "The Sophisticated": { emoji: "🖤",  color: "text-zinc-300",    gradient: "from-zinc-600 to-slate-500",     tagline: "Authority through subtlety." },
  "The Casual":        { emoji: "☀️",  color: "text-yellow-400",  gradient: "from-yellow-500 to-amber-400",   tagline: "Effortless is the goal." },
  "The Eclectic":      { emoji: "🌈",  color: "text-fuchsia-400", gradient: "from-fuchsia-500 to-pink-400",   tagline: "Beautifully uncategorisable." },
};

export const SECTION_META: Array<{
  key:    string;
  label:  string;
  emoji:  string;
  color:  string;
}> = [
  { key: "skin_profile",             label: "Skin Profile",     emoji: "✨", color: "text-emerald-400" },
  { key: "color_profile_section",    label: "Color Profile",    emoji: "🎨", color: "text-amber-400"   },
  { key: "fashion_profile",          label: "Fashion Profile",  emoji: "👗", color: "text-blue-400"    },
  { key: "fragrance_profile_section",label: "Fragrance",        emoji: "🌸", color: "text-purple-400"  },
  { key: "hairstyle_profile",        label: "Hairstyle",        emoji: "💇", color: "text-rose-400"    },
  { key: "personality",              label: "Personality",      emoji: "🧭", color: "text-brand-gold"  },
  { key: "occasion_guide",           label: "Occasion Guide",   emoji: "📅", color: "text-indigo-400"  },
  { key: "recommendations",          label: "Recommendations",  emoji: "🛍️", color: "text-brand-gold"  },
];
