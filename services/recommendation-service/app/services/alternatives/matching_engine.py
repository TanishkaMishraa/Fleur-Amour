"""
AuraFit — Product Matching Engine.
Orchestrates all sub-engines to produce a comprehensive alternative match.

For each (source, candidate) pair:
  1. Embedding similarity (SBERT cosine) — universal signal, all domains
  2. Domain-specific signals:
       makeup:    shade (ΔE) + formula attributes
       skincare:  ingredient (weighted INCI Jaccard) + formula attributes
       haircare:  ingredient + formula attributes
       fragrance: note pyramid + olfactive family
       fashion:   style tag overlap + colour
       accessories: material + style tags
  3. Composite score with domain-appropriate weights
  4. Determines best_value: cheapest with overall_score ≥ BEST_VALUE_THRESHOLD

Pre-computation strategy:
  - Run nightly for all products above LUXURY_PRICE_THRESHOLD (₹10,000)
  - Also run on-demand when a user views a luxury product
  - Results cached in product_alternatives table + Redis (1h TTL)

Price threshold: ₹10,000 (configurable via LUXURY_PRICE_THRESHOLD_INR in settings)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.alternatives import AlternativeMatchType
from app.services.alternatives.ingredient_engine import ingredient_engine
from app.services.alternatives.fragrance_engine import fragrance_engine
from app.services.alternatives.shade_engine import shade_engine

logger = get_logger(__name__)

ENGINE_VERSION = "1.0.0"
BEST_VALUE_THRESHOLD = 0.65   # overall_score ≥ this + cheapest = Best Value badge


@dataclass
class AlternativeMatch:
    """
    Full match result for one (source, alternative) pair.
    This is serialised into the product_alternatives DB row and the API response.
    """
    source_id:        uuid.UUID
    alt_id:           uuid.UUID
    overall_score:    float
    embedding_score:  float | None = None
    ingredient_score: float | None = None
    formula_score:    float | None = None
    shade_score:      float | None = None
    fragrance_score:  float | None = None
    style_score:      float | None = None
    match_types:      list[str]   = field(default_factory=list)
    match_detail:     dict        = field(default_factory=dict)
    source_price:     float       = 0.0
    alt_price:        float       = 0.0
    price_savings:    float       = 0.0
    savings_pct:      float       = 0.0
    currency:         str         = "INR"
    is_best_value:    bool        = False
    rank:             int         = 1


# ── Domain weight tables ──────────────────────────────────────────────────────
# (embedding_w, domain_specific_w, formula_w)
# Must sum to 1.0 within each domain.

_DOMAIN_WEIGHTS: dict[str, dict[str, float]] = {
    "makeup": {
        "embedding":  0.30,
        "shade":      0.40,
        "formula":    0.30,
    },
    "skincare": {
        "embedding":  0.25,
        "ingredient": 0.50,
        "formula":    0.25,
    },
    "haircare": {
        "embedding":  0.25,
        "ingredient": 0.45,
        "formula":    0.30,
    },
    "fragrance": {
        "embedding":  0.20,
        "fragrance":  0.65,
        "formula":    0.15,     # longevity + sillage
    },
    "fashion": {
        "embedding":  0.45,
        "style":      0.35,
        "formula":    0.20,     # material + occasion
    },
    "accessories": {
        "embedding":  0.45,
        "style":      0.35,
        "formula":    0.20,
    },
}


class ProductMatchingEngine:
    """
    Compute AlternativeMatch for a (source_product, candidate_product) pair.
    Call .match() inline or .batch_match() for the nightly Celery task.
    """

    def __init__(self) -> None:
        self._s = get_settings()

    # ── Single pair matching ──────────────────────────────────────────────────

    def match(
        self,
        source: Any,        # Product ORM object
        candidate: Any,     # Product ORM object
        source_embedding: list[float] | None = None,
        candidate_embedding: list[float] | None = None,
        domain: str | None = None,
    ) -> AlternativeMatch:
        """
        Compute full similarity between source and candidate products.
        Returns an AlternativeMatch with all sub-scores and composite score.
        """
        if source.price <= candidate.price:
            # Only find cheaper alternatives
            return self._zero_match(source.id, candidate.id)

        inferred_domain = domain or self._infer_domain(source)
        weights         = _DOMAIN_WEIGHTS.get(inferred_domain, _DOMAIN_WEIGHTS["fashion"])

        match_types  = []
        match_detail = {}
        scores: dict[str, float] = {}

        # ── 1. Embedding similarity (universal) ──────────────────────────────
        if source_embedding and candidate_embedding:
            scores["embedding"] = self._cosine(source_embedding, candidate_embedding)
        else:
            scores["embedding"] = 0.5   # neutral if embeddings missing

        # ── 2. Domain-specific signals ────────────────────────────────────────
        src_attrs = source.attributes or {}
        cand_attrs = candidate.attributes or {}

        if inferred_domain in ("makeup",):
            shade_result = self._compute_shade(src_attrs, cand_attrs)
            scores["shade"] = shade_result[0]
            if shade_result[1]:
                match_detail.update(shade_result[1])
            if scores["shade"] >= 0.70:
                match_types.append(AlternativeMatchType.SHADE.value)

            formula_score, formula_matches = ingredient_engine.compare_formula_attributes(
                src_attrs, cand_attrs, inferred_domain
            )
            scores["formula"] = formula_score
            if formula_matches:
                match_detail["formula_matches"] = formula_matches
            if formula_score >= 0.60:
                match_types.append(AlternativeMatchType.FORMULA.value)

        elif inferred_domain in ("skincare", "haircare"):
            ing_result = ingredient_engine.compare_raw(
                source.ingredients or "", candidate.ingredients or ""
            )
            scores["ingredient"] = ing_result.weighted_score
            match_detail["matched_ingredients"] = ing_result.key_matches
            match_detail["active_match_count"]  = ing_result.active_match_count
            if ing_result.weighted_score >= 0.40:
                match_types.append(AlternativeMatchType.INGREDIENT.value)

            formula_score, formula_matches = ingredient_engine.compare_formula_attributes(
                src_attrs, cand_attrs, inferred_domain
            )
            scores["formula"] = formula_score
            if formula_matches:
                match_detail["formula_matches"] = formula_matches
            if formula_score >= 0.60:
                match_types.append(AlternativeMatchType.FORMULA.value)

        elif inferred_domain == "fragrance":
            frag_result = fragrance_engine.compare_attrs(src_attrs, cand_attrs)
            scores["fragrance"] = frag_result.overall_score
            match_detail["matched_notes"]   = frag_result.all_overlap[:8]
            match_detail["fragrance_summary"] = frag_result.summary
            match_detail["shared_family"]   = frag_result.shared_family
            if frag_result.overall_score >= 0.50:
                match_types.append(AlternativeMatchType.FRAGRANCE.value)

            # Formula (longevity/sillage as "character" score)
            scores["formula"] = frag_result.character_score

        elif inferred_domain in ("fashion", "accessories"):
            style_result = self._compute_style(source, candidate)
            scores["style"] = style_result[0]
            if style_result[1]:
                match_detail["style_matches"] = style_result[1]
            if style_result[0] >= 0.50:
                match_types.append(AlternativeMatchType.STYLE.value)

            formula_score, formula_matches = ingredient_engine.compare_formula_attributes(
                src_attrs, cand_attrs, inferred_domain
            )
            scores["formula"] = formula_score

        # ── 3. Composite score ─────────────────────────────────────────────────
        overall = 0.0
        total_w = 0.0
        for signal, weight in weights.items():
            if signal in scores:
                overall += scores[signal] * weight
                total_w  += weight
        if total_w > 0:
            overall /= total_w

        # Embedding always fires — add its contribution even if not in weights
        if "embedding" not in weights and "embedding" in scores:
            overall = 0.80 * overall + 0.20 * scores["embedding"]

        # Require minimum embedding similarity to avoid garbage matches
        if scores.get("embedding", 0.5) < 0.25:
            overall *= 0.6

        # ── 4. Price calculations ─────────────────────────────────────────────
        savings     = float(source.price) - float(candidate.price)
        savings_pct = savings / float(source.price) * 100 if source.price > 0 else 0.0

        if not match_types:
            match_types.append(AlternativeMatchType.EMBEDDING.value)

        return AlternativeMatch(
            source_id=source.id,
            alt_id=candidate.id,
            overall_score=round(overall, 5),
            embedding_score=round(scores.get("embedding", 0.0), 5),
            ingredient_score=round(scores.get("ingredient", 0.0), 5) if "ingredient" in scores else None,
            formula_score=round(scores.get("formula", 0.0), 5) if "formula" in scores else None,
            shade_score=round(scores.get("shade", 0.0), 5) if "shade" in scores else None,
            fragrance_score=round(scores.get("fragrance", 0.0), 5) if "fragrance" in scores else None,
            style_score=round(scores.get("style", 0.0), 5) if "style" in scores else None,
            match_types=match_types,
            match_detail=match_detail,
            source_price=float(source.price),
            alt_price=float(candidate.price),
            price_savings=round(savings, 2),
            savings_pct=round(savings_pct, 1),
            currency=source.currency or "INR",
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        va, vb = np.array(a), np.array(b)
        denom  = np.linalg.norm(va) * np.linalg.norm(vb)
        if denom == 0:
            return 0.0
        return float(np.clip(np.dot(va, vb) / denom, 0.0, 1.0))

    @staticmethod
    def _compute_shade(attrs_a: dict, attrs_b: dict) -> tuple[float, dict]:
        hex_a = attrs_a.get("shade_hex") or attrs_a.get("hex") or ""
        hex_b = attrs_b.get("shade_hex") or attrs_b.get("hex") or ""

        if not hex_a or not hex_b:
            # No hex data — fall back to shade name string similarity
            name_a = (attrs_a.get("shade") or "").lower()
            name_b = (attrs_b.get("shade") or "").lower()
            if name_a and name_b and name_a == name_b:
                return 0.90, {"shade_name_match": name_a}
            return 0.3, {}

        result = shade_engine.compare_hex(hex_a, hex_b)
        detail = {
            "shade_hex_source":      hex_a,
            "shade_hex_alternative": hex_b,
            "shade_delta_e":         result.delta_e,
            "shade_strength":        result.strength,
            "shade_description":     result.description,
        }
        return result.similarity_score, detail

    @staticmethod
    def _compute_style(source: Any, candidate: Any) -> tuple[float, list[str]]:
        src_tags  = set(source.style_tags or [])
        cand_tags = set(candidate.style_tags or [])
        if not src_tags or not cand_tags:
            return 0.5, []
        inter = src_tags & cand_tags
        union = src_tags | cand_tags
        score = len(inter) / len(union)
        return round(score, 4), sorted(inter)

    @staticmethod
    def _infer_domain(product: Any) -> str:
        slug = ""
        if hasattr(product, "category") and product.category:
            slug = (product.category.slug or "").lower()
        elif hasattr(product, "category_id"):
            slug = ""

        if any(k in slug for k in ("makeup", "lipstick", "foundation", "blush", "eye")):
            return "makeup"
        if any(k in slug for k in ("skincare", "serum", "moistur", "cleanser", "toner", "spf")):
            return "skincare"
        if any(k in slug for k in ("hair",)):
            return "haircare"
        if any(k in slug for k in ("fragrance", "perfume", "eau-de")):
            return "fragrance"
        if any(k in slug for k in ("accessor", "jewel", "bag")):
            return "accessories"
        return "fashion"

    @staticmethod
    def _zero_match(source_id: uuid.UUID, alt_id: uuid.UUID) -> AlternativeMatch:
        return AlternativeMatch(
            source_id=source_id, alt_id=alt_id, overall_score=0.0
        )

    # ── Batch marking ──────────────────────────────────────────────────────────

    @staticmethod
    def mark_best_value(matches: list[AlternativeMatch]) -> list[AlternativeMatch]:
        """
        Among a list of matches for the same source product:
        Mark the cheapest one with overall_score ≥ BEST_VALUE_THRESHOLD as best_value.
        """
        eligible = [m for m in matches if m.overall_score >= BEST_VALUE_THRESHOLD]
        if eligible:
            cheapest = min(eligible, key=lambda m: m.alt_price)
            cheapest.is_best_value = True
        for i, m in enumerate(
            sorted(matches, key=lambda m: m.overall_score, reverse=True), 1
        ):
            m.rank = i
        return matches


# Module-level singleton
matching_engine = ProductMatchingEngine()
