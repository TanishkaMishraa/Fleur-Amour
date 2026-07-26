// AuraFit — Stage 9 Types: Virtual Try-On, Wardrobe AI, Celebrity Matching

// ── Virtual Try-On ─────────────────────────────────────────────────────────────

export type TryOnType = "lipstick" | "foundation" | "eyeshadow" | "hair_color";

export interface TryOnPreset {
  name:      string;
  hex:       string;
  type:      TryOnType;
  finish?:   string;
  intensity?:number;
}

export interface TryOnResult {
  success:       boolean;
  try_on_type:   TryOnType;
  applied_hex:   string;
  result_b64?:   string | null;     // Base64 JPEG — data:image/jpeg;base64,...
  result_url?:   string | null;     // S3 CDN URL (production)
  processing_ms: number;
  face_detected: boolean;
  error?:        string | null;
}

// Makeup presets sourced from Stage 5 ColorProfile
export const LIPSTICK_PRESETS: TryOnPreset[] = [
  { name: "Classic Red",     hex: "#C41E3A", type: "lipstick", finish: "matte",   intensity: 0.9 },
  { name: "Nude Blush",      hex: "#C8917A", type: "lipstick", finish: "satin",   intensity: 0.8 },
  { name: "Berry Rose",      hex: "#9B3A5A", type: "lipstick", finish: "matte",   intensity: 0.85 },
  { name: "Coral Pop",       hex: "#E8694B", type: "lipstick", finish: "gloss",   intensity: 0.8 },
  { name: "Deep Burgundy",   hex: "#6D1F36", type: "lipstick", finish: "matte",   intensity: 0.9 },
  { name: "Rose Gold Gloss", hex: "#B76E79", type: "lipstick", finish: "metallic",intensity: 0.7 },
  { name: "Mauve Nude",      hex: "#A67B6F", type: "lipstick", finish: "satin",   intensity: 0.75},
  { name: "Hot Pink",        hex: "#D94F8A", type: "lipstick", finish: "gloss",   intensity: 0.85},
];

export const EYESHADOW_PRESETS: TryOnPreset[] = [
  { name: "Smoky Grey",      hex: "#5A5A6A", type: "eyeshadow", intensity: 0.7 },
  { name: "Rose Gold",       hex: "#B08060", type: "eyeshadow", intensity: 0.65},
  { name: "Champagne",       hex: "#D4B896", type: "eyeshadow", intensity: 0.6 },
  { name: "Navy Smoke",      hex: "#1A3050", type: "eyeshadow", intensity: 0.7 },
  { name: "Bronze Glow",     hex: "#9A6832", type: "eyeshadow", intensity: 0.65},
  { name: "Plum Haze",       hex: "#6B3A5E", type: "eyeshadow", intensity: 0.65},
  { name: "Forest Green",    hex: "#2D5A3E", type: "eyeshadow", intensity: 0.7 },
  { name: "Terracotta",      hex: "#B45A40", type: "eyeshadow", intensity: 0.65},
];

export const HAIR_COLOR_PRESETS: TryOnPreset[] = [
  { name: "Jet Black",       hex: "#0A0A0F", type: "hair_color", intensity: 0.85 },
  { name: "Dark Brown",      hex: "#2C1810", type: "hair_color", intensity: 0.80 },
  { name: "Warm Brunette",   hex: "#5E3A1F", type: "hair_color", intensity: 0.75 },
  { name: "Golden Blonde",   hex: "#C4A035", type: "hair_color", intensity: 0.70 },
  { name: "Ash Blonde",      hex: "#B8AE98", type: "hair_color", intensity: 0.70 },
  { name: "Copper Auburn",   hex: "#8B3A14", type: "hair_color", intensity: 0.80 },
  { name: "Burgundy Red",    hex: "#6D1A2A", type: "hair_color", intensity: 0.80 },
  { name: "Rose Blonde",     hex: "#D4907A", type: "hair_color", intensity: 0.65 },
  { name: "Icy Platinum",    hex: "#E8E4DC", type: "hair_color", intensity: 0.70 },
  { name: "Dark Espresso",   hex: "#1C0A05", type: "hair_color", intensity: 0.85 },
];

export const FOUNDATION_SHADES: TryOnPreset[] = [
  { name: "Porcelain N10",   hex: "#F5E8DC", type: "foundation", intensity: 0.4 },
  { name: "Ivory N20",       hex: "#F0D9C5", type: "foundation", intensity: 0.4 },
  { name: "Light Beige N30", hex: "#E8C8A8", type: "foundation", intensity: 0.4 },
  { name: "Natural Tan N40", hex: "#D9B090", type: "foundation", intensity: 0.4 },
  { name: "Golden N50",      hex: "#C89070", type: "foundation", intensity: 0.4 },
  { name: "Medium Brown N60",hex: "#A87050", type: "foundation", intensity: 0.4 },
  { name: "Rich N70",        hex: "#885038", type: "foundation", intensity: 0.4 },
  { name: "Deep N80",        hex: "#603020", type: "foundation", intensity: 0.4 },
];

// ── Wardrobe AI ────────────────────────────────────────────────────────────────

export type ClothingCategory =
  | "tops" | "bottoms" | "dresses" | "outerwear"
  | "shoes" | "bags" | "accessories";

export interface WardrobeItemClassification {
  category:        ClothingCategory;
  subcategory:     string;
  confidence:      number;
  dominant_colors: string[];
  occasion_tags:   string[];
  season_tags:     string[];
  style_tags:      string[];
}

export interface WardrobeItemLocal {
  id:           string;
  name:         string;
  category?:    ClothingCategory;
  image_url?:   string;
  color_tags?:  string[];
  occasion_tags?:string[];
  season_tags?: string[];
  style_tags?:  string[];
  times_worn?:  number;
  cost?:        number;
  brand?:       string;
}

export interface AIOutfit {
  outfit_id:    string;
  items:        Array<{
    wardrobe_item_id: string;
    category:         string;
    image_url?:       string | null;
    name:             string;
    color_tags?:      string[];
  }>;
  occasion:     string;
  season:       string;
  color_harmony:string;
  ai_score:     number;
  explanation:  string;
  style_tags:   string[];
}

export interface CapsuleAnalysis {
  total_items:       number;
  total_value:       number;
  category_counts:   Record<string, number>;
  missing_essentials:Array<{ category: string; item: string; priority: number; reason?: string }>;
  redundancies:      Array<{ category: string; count: number; suggestion: string }>;
  cost_per_wear:     Array<{ item_id: string; name: string; times_worn: number; cost: number; cpw: number }>;
  capsule_score:     number;
  shopping_list:     Array<{ category: string; item: string; priority: number }>;
}

// Category display metadata
export const CATEGORY_META: Record<ClothingCategory, { label: string; emoji: string; color: string }> = {
  tops:        { label: "Tops",        emoji: "👕", color: "text-blue-400"   },
  bottoms:     { label: "Bottoms",     emoji: "👖", color: "text-indigo-400" },
  dresses:     { label: "Dresses",     emoji: "👗", color: "text-rose-400"   },
  outerwear:   { label: "Outerwear",   emoji: "🧥", color: "text-amber-400"  },
  shoes:       { label: "Shoes",       emoji: "👠", color: "text-purple-400" },
  bags:        { label: "Bags",        emoji: "👜", color: "text-brand-gold" },
  accessories: { label: "Accessories", emoji: "💍", color: "text-emerald-400"},
};

// ── Celebrity Matching ──────────────────────────────────────────────────────────

export interface CelebrityMatch {
  name:              string;
  similarity_score:  number;
  similarity_pct:    number;
  style_archetypes:  string[];
  known_aesthetics:  string[];
  makeup_signature:  string;
  fashion_signature: string;
  fragrance_family:  string | null;
  style_tip:         string;
  inspiration_tags:  string[];
}

export interface CelebrityMatchResult {
  matches:         CelebrityMatch[];
  query_aesthetic: string;
  style_era:       string;
  primary_style:   string;
}
