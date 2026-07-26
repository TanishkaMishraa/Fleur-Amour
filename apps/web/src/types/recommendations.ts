// AuraFit — Recommendation System types (Stage 6)

export type RecDomain =
  | "makeup" | "skincare" | "haircare"
  | "fragrance" | "fashion" | "accessories" | "mixed";

export interface ProductListItem {
  id:           string;
  sku:          string;
  name:         string;
  brand_name:   string;
  brand_slug:   string;
  category:     string;
  price:        number;
  currency:     string;
  image_url:    string | null;
  avg_rating:   number | null;
  review_count: number;
  is_new_arrival: boolean;
  is_trending:  boolean;
  in_stock:     boolean;
}

export interface RecommendedProduct {
  product:       ProductListItem;
  score:         number;
  cf_score:      number | null;
  cb_score:      number | null;
  profile_score: number | null;
  position:      number;
  reason_code:   string;
  explanation:   string;
}

export interface RecommendationResponse {
  session_id:    string;
  domain:        string;
  items:         RecommendedProduct[];
  total:         number;
  model_version: string;
  cold_start:    boolean;
}

export interface ProductDetail {
  id:           string;
  sku:          string;
  name:         string;
  brand:        { id: string; name: string; slug: string; tier: string; logo_url: string | null };
  category:     { id: string; name: string; slug: string; icon: string | null; parent_id: string | null };
  description:  string | null;
  price:        number;
  currency:     string;
  image_urls:   string[] | null;
  attributes:   Record<string, unknown> | null;
  avg_rating:   number | null;
  review_count: number;
  is_new_arrival: boolean;
  is_trending:  boolean;
  in_stock:     boolean;
  style_tags:   string[] | null;
  season_tags:  string[] | null;
  concern_tags: string[] | null;
}

export interface PaginatedProducts {
  items:       ProductListItem[];
  total:       number;
  page:        number;
  per_page:    number;
  total_pages: number;
}

// Domain display metadata
export const DOMAIN_META: Record<RecDomain, {
  label:    string;
  emoji:    string;
  gradient: string;
  color:    string;
  description: string;
}> = {
  makeup:      { label: "Makeup",      emoji: "💄", gradient: "from-rose-500 to-pink-400",    color: "text-rose-400",    description: "Foundation, lip, eye & face" },
  skincare:    { label: "Skincare",    emoji: "✨", gradient: "from-emerald-500 to-teal-400", color: "text-emerald-400", description: "Serums, moisturisers, SPF" },
  haircare:    { label: "Haircare",    emoji: "💇", gradient: "from-amber-500 to-yellow-400", color: "text-amber-400",   description: "Shampoo, masks, styling" },
  fragrance:   { label: "Fragrance",   emoji: "🌸", gradient: "from-purple-500 to-violet-400",color: "text-purple-400",  description: "Perfumes & body mists" },
  fashion:     { label: "Fashion",     emoji: "👗", gradient: "from-blue-500 to-indigo-400",  color: "text-blue-400",    description: "Clothing & outfits" },
  accessories: { label: "Accessories", emoji: "💍", gradient: "from-brand-gold to-amber-400", color: "text-brand-gold",  description: "Jewellery, bags & more" },
  mixed:       { label: "All",         emoji: "🎯", gradient: "from-brand-gold to-rose-400",  color: "text-brand-gold",  description: "Personalised for you" },
};

export const REASON_COPY: Record<string, { label: string; color: string }> = {
  CF_MATCH:                  { label: "Loved by your beauty tribe",     color: "text-purple-400" },
  CB_SIMILAR:                { label: "Similar to your favourites",      color: "text-blue-400"   },
  SKIN_TONE_MATCH:           { label: "Matched to your skin tone",       color: "text-rose-400"   },
  CONCERN_INGREDIENT_MATCH:  { label: "Targets your skin concerns",      color: "text-emerald-400"},
  FRAGRANCE_FAMILY_MATCH:    { label: "Your fragrance family",           color: "text-purple-400" },
  STYLE_ARCHETYPE_MATCH:     { label: "Fits your personal style",        color: "text-blue-400"   },
  COLOR_SEASON_MATCH:        { label: "In your color palette",           color: "text-amber-400"  },
  NEW_ARRIVAL:               { label: "Just arrived",                    color: "text-brand-gold" },
  TRENDING:                  { label: "Trending now",                    color: "text-brand-gold" },
  PROFILE_MATCH:             { label: "For your profile",                color: "text-muted-foreground" },
};
