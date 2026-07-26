// AuraFit — Smart Alternative Engine Types (Stage 7)

export interface ProductSummary {
  id:           string;
  name:         string;
  brand_name:   string;
  brand_tier:   "luxury" | "mid" | "drugstore";
  category:     string;
  price:        number;
  currency:     string;
  image_url:    string | null;
  avg_rating:   number | null;
  review_count: number;
  in_stock:     boolean;
  attributes:   Record<string, unknown> | null;
  ingredients:  string | null;
}

export type MatchType =
  | "ingredient" | "formula" | "shade"
  | "fragrance"  | "style"   | "embedding";

export interface MatchDetail {
  // Ingredient matches
  matched_ingredients?:    string[];
  active_match_count?:     number;
  total_active_ingredients?:number;
  formula_matches?:        Record<string, string>;
  // Shade
  shade_hex_source?:       string;
  shade_hex_alternative?:  string;
  shade_delta_e?:          number;
  shade_strength?:         string;
  shade_description?:      string;
  // Fragrance
  matched_notes?:          string[];
  fragrance_summary?:      string;
  shared_family?:          boolean;
  // Style
  style_matches?:          string[];
}

export interface AlternativeProduct {
  alt_id:         string;
  product:        ProductSummary;

  // Similarity scores [0,1]
  overall_score:    number;
  overall_pct:      number;       // 0–100
  embedding_score:  number | null;
  ingredient_score: number | null;
  formula_score:    number | null;
  shade_score:      number | null;
  fragrance_score:  number | null;
  style_score:      number | null;

  // Match context
  match_types:  MatchType[];
  match_detail: MatchDetail;

  // Price
  source_price:  number;
  alt_price:     number;
  price_savings: number;
  savings_pct:   number;
  currency:      string;

  // Quality
  is_best_value: boolean;
  rank:          number;
}

export interface AlternativeGroupResponse {
  source:         ProductSummary;
  alternatives:   AlternativeProduct[];
  total:          number;
  from_cache:     boolean;
  engine_version: string;
}

// ── Display helpers ────────────────────────────────────────────────────────────

export const MATCH_TYPE_META: Record<MatchType, { label: string; color: string; icon: string }> = {
  ingredient: { label: "Ingredient Match",  color: "text-emerald-400", icon: "🧪" },
  formula:    { label: "Formula Match",     color: "text-blue-400",    icon: "⚗️" },
  shade:      { label: "Shade Dupe",        color: "text-rose-400",    icon: "🎨" },
  fragrance:  { label: "Fragrance Dupe",    color: "text-purple-400",  icon: "🌸" },
  style:      { label: "Style Match",       color: "text-amber-400",   icon: "✨" },
  embedding:  { label: "Similar Product",   color: "text-blue-400",    icon: "🔮" },
};

export const SIMILARITY_LABEL = (pct: number): { label: string; color: string } => {
  if (pct >= 90) return { label: "Virtually identical",   color: "text-emerald-400" };
  if (pct >= 80) return { label: "Near-perfect dupe",     color: "text-emerald-400" };
  if (pct >= 70) return { label: "Excellent match",       color: "text-brand-gold"  };
  if (pct >= 60) return { label: "Very good match",       color: "text-amber-400"   };
  if (pct >= 50) return { label: "Good alternative",      color: "text-amber-400"   };
  return               { label: "Similar category",       color: "text-muted-foreground" };
};

// ── Price thresholds (INR) ────────────────────────────────────────────────────

export const LUXURY_THRESHOLD_INR = 10000;
export const PREMIUM_THRESHOLD_INR = 5000;

export const isLuxuryPrice = (price: number, currency: string): boolean => {
  // Simple INR conversion (production: use exchange rate API)
  const inr = currency === "INR" ? price :
               currency === "USD" ? price * 83 :
               currency === "EUR" ? price * 90 :
               currency === "GBP" ? price * 106 : price;
  return inr >= LUXURY_THRESHOLD_INR;
};

export const formatPrice = (price: number, currency: string): string => {
  const symbols: Record<string, string> = {
    INR: "₹", USD: "$", EUR: "€", GBP: "£",
  };
  const sym = symbols[currency] ?? currency;
  return `${sym}${price.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
};
