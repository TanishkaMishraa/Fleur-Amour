// ── Color Intelligence Types (Stage 5) ──────────────────────────────────────
// Mirrors the backend Pydantic schemas in app/schemas/color.py

export type ColorSeasonFamily = "spring" | "summer" | "autumn" | "winter";

export type ColorSeason =
  | "spring" | "summer" | "autumn" | "winter"
  | "light_spring" | "true_spring" | "bright_spring"
  | "light_summer" | "true_summer" | "soft_summer"
  | "soft_autumn" | "true_autumn" | "deep_autumn"
  | "deep_winter" | "true_winter" | "bright_winter";

export type ContrastLevel = "low" | "medium" | "high";
export type ChromaLevel   = "muted" | "soft" | "clear" | "bright";
export type ValueLevel    = "light" | "medium" | "deep";

export interface ColorEntry {
  hex:        string;
  name:       string;
  category:   "neutral" | "accent" | "base" | "statement";
  season_fit?: "best" | "good" | "avoid";
}

export interface SeasonClassification {
  season:              ColorSeason;
  confidence:          number;      // 0–1
  description:         string;
  key_characteristics: string[];
  celebrity_examples:  string[];
  season_family:       ColorSeasonFamily;
  contrast_level:      ContrastLevel;
  chroma_level:        ChromaLevel;
  value_level:         ValueLevel;
}

export interface PersonalPalette {
  best:       ColorEntry[];
  neutrals:   ColorEntry[];
  accents:    ColorEntry[];
  avoid:      ColorEntry[];
  hero_color: ColorEntry;
}

export interface LipstickShade {
  shade:     string;
  hex:       string;
  finish:    "matte" | "satin" | "gloss" | "sheer" | "metallic";
  intensity: "light" | "medium" | "bold";
  occasion:  "everyday" | "evening" | "professional" | "special";
  brands:    string[];
  rationale: string;
}

export interface HairColorOption {
  name:        string;
  hex:         string;
  technique:   "all-over" | "highlights" | "balayage" | "ombre" | "gloss";
  commitment:  "permanent" | "semi-permanent" | "temporary";
  rationale:   string;
  maintenance: "Low" | "Medium" | "High";
}

export interface OutfitPalette {
  base_colors:   ColorEntry[];
  accent_colors: ColorEntry[];
  avoid_colors:  ColorEntry[];
  styling_tip:   string;
}

export interface JewelryRecommendation {
  metal_tones: string[];
  gem_colors:  ColorEntry[];
  rationale:   string;
  style_notes: string;
}

export interface MakeupColorRecommendation {
  foundation_undertone: string;
  foundation_finish:    string;
  blush_shades:         ColorEntry[];
  eyeshadow_palettes:   Array<{ name: string; shades: string[]; finish: string }>;
  eyeliner_colors:      ColorEntry[];
  highlight_shades:     ColorEntry[];
  contour_shades:       ColorEntry[];
}

export interface FullColorAnalysisResponse {
  profile_id:    string;
  scan_id:       string | null;
  season:        SeasonClassification;
  palette:       PersonalPalette;
  makeup:        MakeupColorRecommendation;
  lipstick:      LipstickShade[];
  hair_color:    HairColorOption[];
  outfits:       Record<string, OutfitPalette>;  // work|evening|casual|sport
  jewelry:       JewelryRecommendation;
  computed_at:   string;
  engine_version:string;
}

export interface ColorProfileRecord {
  id:              string;
  user_id:         string;
  scan_id:         string | null;
  season:          ColorSeason;
  season_confidence: number;
  season_description: string | null;
  skin_tone:       string | null;
  undertone:       string | null;
  skin_hex:        string | null;
  ita_angle:       number | null;
  fitzpatrick:     number | null;
  hair_color_hex:  string | null;
  palette_best:    Array<{ hex: string; name: string; category: string }> | null;
  palette_avoid:   Array<{ hex: string; name: string; category: string }> | null;
  palette_neutrals:Array<{ hex: string; name: string; category: string }> | null;
  palette_accents: Array<{ hex: string; name: string; category: string }> | null;
  makeup_recommendations:     MakeupColorRecommendation | null;
  lipstick_recommendations:   LipstickShade[] | null;
  hair_color_recommendations: HairColorOption[] | null;
  outfit_recommendations:     Record<string, OutfitPalette> | null;
  jewelry_recommendations:    JewelryRecommendation | null;
  engine_version:  string;
  is_active:       boolean;
  created_at:      string;
  updated_at:      string;
}

// Season UI metadata (used for theming / display)
export const SEASON_DISPLAY: Record<string, {
  label: string;
  family: ColorSeasonFamily;
  gradient: string;
  textColor: string;
  borderColor: string;
  emoji: string;
}> = {
  // Spring family
  true_spring:   { label: "True Spring",   family: "spring", gradient: "from-amber-400 to-orange-300",  textColor: "text-amber-900",  borderColor: "border-amber-400/40", emoji: "🌸" },
  light_spring:  { label: "Light Spring",  family: "spring", gradient: "from-yellow-300 to-pink-200",   textColor: "text-yellow-900", borderColor: "border-yellow-300/40",emoji: "🌷" },
  bright_spring: { label: "Bright Spring", family: "spring", gradient: "from-orange-400 to-yellow-300", textColor: "text-orange-900", borderColor: "border-orange-400/40",emoji: "✨" },
  spring:        { label: "Spring",        family: "spring", gradient: "from-amber-400 to-orange-300",  textColor: "text-amber-900",  borderColor: "border-amber-400/40", emoji: "🌸" },
  // Summer family
  true_summer:   { label: "True Summer",   family: "summer", gradient: "from-purple-400 to-pink-300",   textColor: "text-purple-900", borderColor: "border-purple-400/40",emoji: "🌿" },
  light_summer:  { label: "Light Summer",  family: "summer", gradient: "from-blue-300 to-purple-200",   textColor: "text-blue-900",   borderColor: "border-blue-300/40",  emoji: "💐" },
  soft_summer:   { label: "Soft Summer",   family: "summer", gradient: "from-slate-400 to-purple-300",  textColor: "text-slate-900",  borderColor: "border-slate-400/40", emoji: "🌫️" },
  summer:        { label: "Summer",        family: "summer", gradient: "from-purple-400 to-pink-300",   textColor: "text-purple-900", borderColor: "border-purple-400/40",emoji: "🌿" },
  // Autumn family
  true_autumn:   { label: "True Autumn",   family: "autumn", gradient: "from-orange-600 to-amber-500",  textColor: "text-orange-100", borderColor: "border-orange-500/40",emoji: "🍂" },
  soft_autumn:   { label: "Soft Autumn",   family: "autumn", gradient: "from-stone-500 to-amber-400",   textColor: "text-stone-100",  borderColor: "border-stone-400/40", emoji: "🍁" },
  deep_autumn:   { label: "Deep Autumn",   family: "autumn", gradient: "from-red-800 to-orange-700",    textColor: "text-red-100",    borderColor: "border-red-700/40",   emoji: "🌰" },
  autumn:        { label: "Autumn",        family: "autumn", gradient: "from-orange-600 to-amber-500",  textColor: "text-orange-100", borderColor: "border-orange-500/40",emoji: "🍂" },
  // Winter family
  true_winter:   { label: "True Winter",   family: "winter", gradient: "from-indigo-700 to-blue-600",   textColor: "text-indigo-100", borderColor: "border-indigo-500/40",emoji: "❄️" },
  bright_winter: { label: "Bright Winter", family: "winter", gradient: "from-blue-700 to-fuchsia-600",  textColor: "text-blue-100",   borderColor: "border-blue-500/40",  emoji: "💎" },
  deep_winter:   { label: "Deep Winter",   family: "winter", gradient: "from-slate-800 to-indigo-700",  textColor: "text-slate-100",  borderColor: "border-slate-600/40", emoji: "🌑" },
  winter:        { label: "Winter",        family: "winter", gradient: "from-indigo-700 to-blue-600",   textColor: "text-indigo-100", borderColor: "border-indigo-500/40",emoji: "❄️" },
};

export const SEASON_FAMILY_COLORS: Record<ColorSeasonFamily, { bg: string; text: string; border: string }> = {
  spring: { bg: "bg-amber-500/10",   text: "text-amber-400",  border: "border-amber-500/20"  },
  summer: { bg: "bg-purple-500/10",  text: "text-purple-400", border: "border-purple-500/20" },
  autumn: { bg: "bg-orange-500/10",  text: "text-orange-400", border: "border-orange-500/20" },
  winter: { bg: "bg-blue-500/10",    text: "text-blue-400",   border: "border-blue-500/20"   },
};
