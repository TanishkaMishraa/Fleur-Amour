"""
AuraFit — Ingredient Comparison Engine.

Handles skincare and haircare formula matching via:
  1. INCI (International Nomenclature of Cosmetic Ingredients) parsing
  2. Active ingredient extraction (clinically significant actives only)
  3. Jaccard similarity on full ingredient set
  4. Weighted active-ingredient overlap (actives weighted 3× vs regular)
  5. Formula attribute matching (finish, texture, SPF, coverage, pH)

Jaccard similarity:
  J(A, B) = |A ∩ B| / |A ∪ B|

Weighted similarity:
  W(A, B) = (3 × |actives(A) ∩ actives(B)| + |base(A) ∩ base(B)|)
           / (3 × |actives(A) ∪ actives(B)| + |base(A) ∪ base(B)|)

A score ≥ 0.60 = strong ingredient match ("Ingredient Dupe")
A score ≥ 0.40 = moderate match ("Similar Formula")
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── Clinically significant active ingredients ─────────────────────────────────
# These are weighted 3× in similarity calculations because they drive efficacy.

ACTIVE_INGREDIENTS: frozenset[str] = frozenset({
    # Exfoliants
    "salicylic acid", "glycolic acid", "lactic acid", "mandelic acid",
    "azelaic acid", "phytic acid", "gluconolactone", "lactobionic acid",
    "citric acid", "tartaric acid",
    # Vitamins
    "ascorbic acid", "vitamin c", "niacinamide", "retinol", "retinal",
    "retinaldehyde", "vitamin e", "tocopherol", "vitamin b5", "panthenol",
    "vitamin b3", "vitamin a", "vitamin d",
    # Peptides
    "matrixyl", "argireline", "leuphasyl", "palmitoyl oligopeptide",
    "palmitoyl tripeptide", "copper peptide", "syn-ake",
    # Brighteners
    "alpha arbutin", "kojic acid", "tranexamic acid", "licorice extract",
    "bearberry extract", "resveratrol", "ferulic acid",
    # Hydration
    "hyaluronic acid", "sodium hyaluronate", "glycerin", "squalane",
    "betaine", "sorbitol",
    # Barriers
    "ceramide", "ceramide np", "ceramide ap", "ceramide eop",
    "cholesterol", "fatty acid",
    # Anti-acne
    "benzoyl peroxide", "sulfur", "zinc", "tea tree oil", "salicylate",
    # SPF actives
    "zinc oxide", "titanium dioxide", "avobenzone", "octinoxate",
    "octisalate", "octocrylene", "homosalate", "mexoryl",
    # Hair actives
    "minoxidil", "biotin", "caffeine", "keratin", "collagen",
    "hydrolyzed keratin", "hydrolyzed collagen", "silk amino acid",
    # Soothing
    "centella asiatica", "madecassoside", "asiaticoside", "allantoin",
    "bisabolol", "aloe vera", "green tea extract", "chamomile extract",
})

# Common normalisation aliases
_ALIASES: dict[str, str] = {
    "ascorbic acid":         "vitamin c",
    "tocopherol":            "vitamin e",
    "tocopheryl acetate":    "vitamin e",
    "panthenol":             "vitamin b5",
    "sodium ascorbyl phosphate": "vitamin c",
    "magnesium ascorbyl phosphate": "vitamin c",
    "retinyl palmitate":     "retinol",
    "sodium hyaluronate":    "hyaluronic acid",
    "aloe barbadensis leaf extract": "aloe vera",
    "camellia sinensis leaf extract": "green tea extract",
    "centella asiatica extract": "centella asiatica",
}


@dataclass
class IngredientProfile:
    """Parsed ingredient list split into actives and base ingredients."""
    raw_text:    str
    all_inci:    frozenset[str]          # All normalised INCI names
    actives:     frozenset[str]          # Clinically active subset
    base:        frozenset[str]          # Everything else
    count:       int                     = 0


@dataclass
class IngredientMatchResult:
    """Result of comparing two products' ingredient lists."""
    jaccard_score:       float            # Simple Jaccard on all ingredients
    weighted_score:      float            # Active-weighted similarity
    active_overlap:      frozenset[str]   # Shared active ingredients
    base_overlap:        frozenset[str]   # Shared base ingredients
    active_match_count:  int
    total_actives_union: int
    key_matches:         list[str]        # Top 5 matched actives for display
    strength:            str              # "dupe" | "similar" | "different"


class IngredientEngine:
    """
    Parse, normalise, and compare cosmetic ingredient lists.
    All methods are pure functions — no I/O, no state.
    """

    # ── Parsing ───────────────────────────────────────────────────────────────

    def parse(self, raw_text: str) -> IngredientProfile:
        """Parse a raw INCI ingredient string into a structured profile."""
        if not raw_text or not raw_text.strip():
            return IngredientProfile(
                raw_text="", all_inci=frozenset(), actives=frozenset(),
                base=frozenset(), count=0
            )

        # Split on commas, semicolons, or newlines
        parts = re.split(r"[,;\n]+", raw_text)
        normalised = frozenset(
            self._normalise(p) for p in parts
            if self._normalise(p)
        )

        actives = frozenset(i for i in normalised if self._is_active(i))
        base    = normalised - actives

        return IngredientProfile(
            raw_text=raw_text,
            all_inci=normalised,
            actives=actives,
            base=base,
            count=len(normalised),
        )

    # ── Comparison ────────────────────────────────────────────────────────────

    def compare(self, a: IngredientProfile, b: IngredientProfile) -> IngredientMatchResult:
        """
        Compare two ingredient profiles.
        Returns IngredientMatchResult with all similarity scores.
        """
        if not a.all_inci or not b.all_inci:
            return self._empty_result()

        # Jaccard: full ingredient set
        intersection = a.all_inci & b.all_inci
        union        = a.all_inci | b.all_inci
        jaccard      = len(intersection) / len(union) if union else 0.0

        # Active overlap
        active_inter = a.actives & b.actives
        active_union = a.actives | b.actives

        # Base overlap
        base_inter = a.base & b.base
        base_union = a.base | b.base

        # Weighted score: actives count 3×
        w_num = 3 * len(active_inter) + len(base_inter)
        w_den = 3 * len(active_union) + len(base_union)
        weighted = w_num / w_den if w_den > 0 else 0.0

        # Key matches: prioritise actives, limit to 6 for display
        key = sorted(active_inter, key=lambda x: x in ACTIVE_INGREDIENTS, reverse=True)[:6]

        # Strength label
        if weighted >= 0.60:
            strength = "dupe"
        elif weighted >= 0.40:
            strength = "similar"
        else:
            strength = "different"

        return IngredientMatchResult(
            jaccard_score=round(jaccard, 4),
            weighted_score=round(weighted, 4),
            active_overlap=active_inter,
            base_overlap=base_inter,
            active_match_count=len(active_inter),
            total_actives_union=len(active_union),
            key_matches=key,
            strength=strength,
        )

    def compare_raw(self, text_a: str, text_b: str) -> IngredientMatchResult:
        """Convenience: parse both and compare."""
        return self.compare(self.parse(text_a), self.parse(text_b))

    # ── Formula attribute comparison ───────────────────────────────────────────

    def compare_formula_attributes(
        self, attrs_a: dict, attrs_b: dict, domain: str
    ) -> tuple[float, dict[str, Any]]:
        """
        Compare domain-specific formula attributes (not ingredients).
        Returns (score [0,1], matched_attributes dict).

        Makeup: finish, coverage, formula (liquid/powder/cream), SPF, skin_tone_range
        Skincare: texture, spf, skin_type, ph_range
        Haircare: hold_level, application, finish
        """
        if not attrs_a or not attrs_b:
            return 0.0, {}

        keys = self._formula_keys(domain)
        matched = {}
        total_weight = 0.0
        score_sum    = 0.0

        for key, weight in keys:
            va = (str(attrs_a.get(key) or "")).lower().strip()
            vb = (str(attrs_b.get(key) or "")).lower().strip()
            if not va or not vb:
                continue
            total_weight += weight
            if va == vb:
                score_sum  += weight
                matched[key] = va
            elif self._partial_match(va, vb, key):
                score_sum  += weight * 0.6
                matched[key] = f"~{va}"

        score = score_sum / total_weight if total_weight > 0 else 0.0
        return round(score, 4), matched

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _normalise(raw: str) -> str:
        """Lowercase, strip parentheses and extra whitespace, apply aliases."""
        cleaned = re.sub(r"\([^)]*\)", "", raw).strip().lower()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return _ALIASES.get(cleaned, cleaned)

    @staticmethod
    def _is_active(ingredient: str) -> bool:
        """Return True if this ingredient is in the clinically active set."""
        return ingredient in ACTIVE_INGREDIENTS or any(
            a in ingredient for a in ACTIVE_INGREDIENTS
        )

    @staticmethod
    def _formula_keys(domain: str) -> list[tuple[str, float]]:
        """Return (attribute_key, weight) tuples for each domain."""
        _KEYS: dict[str, list[tuple[str, float]]] = {
            "makeup":   [("finish", 0.35), ("coverage", 0.30), ("formula", 0.20), ("spf", 0.15)],
            "skincare": [("texture", 0.30), ("spf", 0.30), ("skin_type", 0.25), ("finish", 0.15)],
            "haircare": [("hold_level", 0.40), ("application", 0.30), ("finish", 0.30)],
            "fashion":  [("material", 0.40), ("occasion", 0.30), ("season", 0.30)],
        }
        return _KEYS.get(domain, [("finish", 0.5), ("texture", 0.5)])

    @staticmethod
    def _partial_match(a: str, b: str, key: str) -> bool:
        """Allow partial matches for range-type attributes."""
        ranges = {
            "coverage": {"light": 0, "light-to-medium": 1, "medium": 1, "medium-to-full": 2, "full": 2},
            "hold_level": {"light": 0, "medium": 1, "strong": 2, "extra-strong": 3},
        }
        r = ranges.get(key, {})
        if r:
            va, vb = r.get(a, -1), r.get(b, -1)
            return va != -1 and vb != -1 and abs(va - vb) <= 1
        return False

    @staticmethod
    def _empty_result() -> IngredientMatchResult:
        return IngredientMatchResult(
            jaccard_score=0.0, weighted_score=0.0,
            active_overlap=frozenset(), base_overlap=frozenset(),
            active_match_count=0, total_actives_union=0,
            key_matches=[], strength="different",
        )


# Module-level singleton
ingredient_engine = IngredientEngine()
