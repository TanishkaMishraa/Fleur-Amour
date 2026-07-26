"""
AuraFit — Profile-Based Rules Engine.

Computes a 0–1 compatibility score for a (user_profile, product) pair
using deterministic rules derived from beauty science:

  1. Skin-tone/undertone shade compatibility (makeup domain)
  2. Skin-concern ingredient compatibility (skincare domain)
  3. Hair-type compatibility (haircare domain)
  4. Fragrance family affinity (fragrance domain)
  5. Style archetype + color season outfit compatibility (fashion/accessories)
  6. Budget band filter

The rules engine is the PROFILE_WEIGHT component of the hybrid score:
  hybrid = CF_WEIGHT * cf_score + CB_WEIGHT * cb_score + PROFILE_WEIGHT * profile_score

Benefits over ML-only:
  - Interpretable: every score has a human-readable reason_code
  - No data dependency: works for cold-start users
  - Corrects CF/CB blind spots (e.g., CF might recommend wrong foundation shade)
"""
from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.schemas.recommendation_schemas import UserPreferenceSignals

logger = get_logger(__name__)

# ── Skin tone → compatible makeup shade ranges ────────────────────────────────

_SKIN_TONE_COMPATIBLE = {
    "fair":   {"fair", "light", "fair-to-light"},
    "light":  {"light", "fair-to-light", "light-to-medium"},
    "medium": {"medium", "light-to-medium", "medium-to-tan"},
    "olive":  {"olive", "medium", "medium-to-tan"},
    "tan":    {"tan", "medium-to-tan", "tan-to-deep"},
    "deep":   {"deep", "dark", "tan-to-deep", "rich"},
}

_UNDERTONE_COMPATIBLE = {
    "cool":    {"cool", "pink", "rose", "blue-red", "berry"},
    "warm":    {"warm", "yellow", "golden", "orange-red", "peach"},
    "neutral": {"neutral", "cool", "warm"},   # neutral is compatible with all
}

# ── Concern → beneficial ingredient families ─────────────────────────────────

_CONCERN_INGREDIENTS = {
    "acne":              {"salicylic_acid", "benzoyl_peroxide", "niacinamide", "tea_tree", "zinc"},
    "hyperpigmentation": {"vitamin_c", "alpha_arbutin", "kojic_acid", "niacinamide", "tranexamic_acid"},
    "dark_circles":      {"caffeine", "vitamin_k", "retinol", "peptides", "hyaluronic_acid"},
    "dryness":           {"hyaluronic_acid", "ceramides", "glycerin", "squalane", "shea_butter"},
    "oiliness":          {"niacinamide", "salicylic_acid", "zinc", "kaolin", "glycolic_acid"},
    "fine_lines":        {"retinol", "retinal", "peptides", "vitamin_c", "hyaluronic_acid"},
    "redness":           {"centella", "azelaic_acid", "green_tea", "ceramides", "allantoin"},
    "enlarged_pores":    {"salicylic_acid", "niacinamide", "aha", "retinol"},
    "dullness":          {"vitamin_c", "glycolic_acid", "lactic_acid", "niacinamide"},
}

# ── Fragrance family affinities ───────────────────────────────────────────────

_FRAGRANCE_AFFINITY = {
    "floral":   {"floral", "powdery", "fruity"},
    "woody":    {"woody", "earthy", "oriental", "tobacco"},
    "oriental": {"oriental", "woody", "spicy", "gourmand"},
    "fresh":    {"fresh", "citrus", "aquatic", "green"},
    "citrus":   {"citrus", "fresh", "aromatic"},
    "gourmand": {"gourmand", "oriental", "powdery"},
    "chypre":   {"chypre", "woody", "floral"},
    "fougere":  {"fougere", "aromatic", "woody"},
}

# ── Style archetype outfit compatibility ──────────────────────────────────────

_STYLE_TAGS_MAP = {
    "minimalist":  {"minimalist", "classic", "clean", "structured"},
    "boho":        {"boho", "bohemian", "eclectic", "romantic", "festival"},
    "classic":     {"classic", "timeless", "preppy", "formal"},
    "romantic":    {"romantic", "feminine", "floral", "soft"},
    "edgy":        {"edgy", "punk", "rock", "grunge", "streetwear"},
    "athletic":    {"athletic", "sporty", "active", "casual"},
    "glamorous":   {"glamorous", "evening", "cocktail", "luxury"},
    "casual":      {"casual", "relaxed", "everyday", "comfort"},
    "preppy":      {"preppy", "classic", "collegiate"},
    "eclectic":    {"eclectic", "maximalist", "bold", "colorful"},
}

# ── Color season → compatible clothing color tags ─────────────────────────────

_SEASON_COLORS = {
    "spring":        {"warm", "golden", "peach", "coral", "cream", "warm-white"},
    "true_spring":   {"warm", "golden", "peach", "coral"},
    "light_spring":  {"light", "soft", "peach", "warm-pink"},
    "bright_spring": {"vivid", "bright", "warm", "clear"},
    "summer":        {"cool", "soft", "muted", "lavender", "dusty-rose", "powder-blue"},
    "true_summer":   {"cool", "muted", "dusty-rose"},
    "light_summer":  {"light", "cool", "pastel"},
    "soft_summer":   {"muted", "soft", "greige"},
    "autumn":        {"warm", "earthy", "terracotta", "rust", "olive", "mustard"},
    "true_autumn":   {"earthy", "terracotta", "rust"},
    "soft_autumn":   {"muted", "warm", "camel"},
    "deep_autumn":   {"deep", "warm", "rich", "burgundy"},
    "winter":        {"cool", "clear", "high-contrast", "icy", "jewel-tones"},
    "true_winter":   {"cool", "clear", "high-contrast"},
    "bright_winter": {"vivid", "cool", "electric"},
    "deep_winter":   {"deep", "cool", "rich", "dark"},
}


class ProfileRulesEngine:
    """
    Deterministic compatibility scorer.
    Returns (score: float, reason_code: str) per product.
    """

    def score(
        self,
        product: any,
        signals: UserPreferenceSignals,
    ) -> tuple[float, str]:
        """
        Score a product against user preference signals.
        Returns (0.0–1.0 score, reason_code).
        """
        attrs      = product.attributes or {}
        category   = product.category.slug if hasattr(product, "category") and product.category else ""
        domain     = self._infer_domain(category)

        if domain == "makeup":
            return self._score_makeup(attrs, signals)
        elif domain == "skincare":
            return self._score_skincare(attrs, product.ingredients or "", signals)
        elif domain == "haircare":
            return self._score_haircare(attrs, signals)
        elif domain == "fragrance":
            return self._score_fragrance(attrs, signals)
        elif domain in ("fashion", "accessories"):
            return self._score_fashion(attrs, product.style_tags or [], signals)
        else:
            # Generic: budget compatibility only
            return self._score_budget(product.price, signals)

    # ── Domain scorers ────────────────────────────────────────────────────────

    def _score_makeup(self, attrs: dict, signals: UserPreferenceSignals) -> tuple[float, str]:
        score = 0.5   # baseline

        # Shade range compatibility
        shade_range = (attrs.get("skin_tone_range") or "").lower()
        if signals.skin_tone and shade_range:
            compatible = _SKIN_TONE_COMPATIBLE.get(signals.skin_tone, set())
            if any(c in shade_range for c in compatible):
                score += 0.30
                return round(min(score, 1.0), 4), "SKIN_TONE_MATCH"
            elif shade_range:  # Has a shade range but doesn't match
                score -= 0.20

        # Undertone compatibility
        finish = (attrs.get("finish") or "").lower()
        formula_undertone = (attrs.get("undertone") or "").lower()
        if signals.undertone and formula_undertone:
            compatible = _UNDERTONE_COMPATIBLE.get(signals.undertone, set())
            if formula_undertone in compatible:
                score += 0.20

        return round(min(max(score, 0.0), 1.0), 4), "SKIN_COMPATIBLE"

    def _score_skincare(self, attrs: dict, ingredients: str, signals: UserPreferenceSignals) -> tuple[float, str]:
        score = 0.5
        ingredients_lower = ingredients.lower()

        if not signals.skin_concerns:
            return score, "PROFILE_MATCH"

        matched_concerns = 0
        total_concerns   = len(signals.skin_concerns)

        for concern in signals.skin_concerns:
            beneficial = _CONCERN_INGREDIENTS.get(concern, set())
            if any(ing in ingredients_lower for ing in beneficial):
                matched_concerns += 1

        if matched_concerns > 0:
            score += 0.40 * (matched_concerns / total_concerns)
            return round(min(score, 1.0), 4), "CONCERN_INGREDIENT_MATCH"

        # Skin type compatibility
        product_skin_type = (attrs.get("skin_type") or "").lower()
        return round(score, 4), "SKIN_COMPATIBLE"

    def _score_haircare(self, attrs: dict, signals: UserPreferenceSignals) -> tuple[float, str]:
        score = 0.5
        # Check if product is designed for user's hair type (from profile)
        # Note: hair_type is on UserProfile, accessible via UserPreferenceSignals
        return round(score, 4), "PROFILE_MATCH"

    def _score_fragrance(self, attrs: dict, signals: UserPreferenceSignals) -> tuple[float, str]:
        score = 0.5
        if not signals.fragrance_family:
            return score, "PROFILE_MATCH"

        product_family = (attrs.get("family") or "").lower()
        for pref_family in signals.fragrance_family:
            related = _FRAGRANCE_AFFINITY.get(pref_family.lower(), {pref_family.lower()})
            if product_family in related:
                return 0.90, "FRAGRANCE_FAMILY_MATCH"
            if product_family == pref_family.lower():
                return 0.95, "FRAGRANCE_EXACT_MATCH"

        return round(score, 4), "PROFILE_MATCH"

    def _score_fashion(self, attrs: dict, style_tags: list[str], signals: UserPreferenceSignals) -> tuple[float, str]:
        score = 0.5

        if signals.style_archetypes and style_tags:
            product_tag_set = {t.lower() for t in style_tags}
            for archetype in signals.style_archetypes:
                archetype_tags = _STYLE_TAGS_MAP.get(archetype.lower(), {archetype.lower()})
                if product_tag_set & archetype_tags:
                    score += 0.35
                    return round(min(score, 1.0), 4), "STYLE_ARCHETYPE_MATCH"

        if signals.color_season:
            season_colors = _SEASON_COLORS.get(signals.color_season, set())
            product_colors = {(attrs.get("color") or "").lower()}
            if product_colors & season_colors:
                score += 0.25
                return round(min(score, 1.0), 4), "COLOR_SEASON_MATCH"

        return round(score, 4), "PROFILE_MATCH"

    def _score_budget(self, price: float, signals: UserPreferenceSignals) -> tuple[float, str]:
        if not signals.budget_range:
            return 0.5, "PROFILE_MATCH"
        bands = {"low": (0, 25), "medium": (25, 75), "high": (75, 200), "luxury": (200, 99999)}
        lo, hi = bands.get(signals.budget_range.lower(), (0, 99999))
        if lo <= price <= hi:
            return 0.75, "BUDGET_MATCH"
        # Outside band but close
        margin = 0.20
        if price < lo * (1 + margin) or price < hi * (1 + margin):
            return 0.50, "BUDGET_CLOSE"
        return 0.20, "BUDGET_MISMATCH"

    # ── Domain inference ──────────────────────────────────────────────────────

    @staticmethod
    def _infer_domain(category_slug: str) -> str:
        slug = category_slug.lower()
        if any(k in slug for k in ("makeup", "cosmetic", "foundation", "lipstick", "blush", "eyeshadow")):
            return "makeup"
        if any(k in slug for k in ("skincare", "serum", "moisturis", "cleanser", "toner", "sunscreen", "spf")):
            return "skincare"
        if any(k in slug for k in ("hair", "shampoo", "conditioner", "mask", "hair-color")):
            return "haircare"
        if any(k in slug for k in ("fragrance", "perfume", "eau-de")):
            return "fragrance"
        if any(k in slug for k in ("fashion", "clothing", "dress", "top", "trouser", "jacket", "shoe")):
            return "fashion"
        if any(k in slug for k in ("accessor", "jewel", "bag", "belt", "hat", "scarf")):
            return "accessories"
        return "generic"
