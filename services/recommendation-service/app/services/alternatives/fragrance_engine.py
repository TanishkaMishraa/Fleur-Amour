"""
AuraFit — Fragrance Note Matching Engine.

Matches fragrances across three dimensions:
  1. Note overlap: top/mid/base note Jaccard similarity
  2. Olfactive family affinity: weighted graph of related fragrance families
  3. Character matching: longevity, sillage, season, occasion

Note pyramid weighting (industry-standard):
  Base notes:  50% of overall character (most important — last longest)
  Mid notes:   30% (heart of the fragrance)
  Top notes:   20% (first impression, fades in 30 min)

Olfactive family similarity graph:
  Fragrances in related families get partial credit even if notes don't overlap.
  (e.g., Floral Oriental and Oriental have 0.7 similarity)

Score ≥ 0.70 = strong fragrance dupe
Score ≥ 0.50 = similar fragrance (same family)
Score < 0.50 = different character
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ── Olfactive family affinity matrix ─────────────────────────────────────────
# Values represent how similar two families smell to each other [0, 1].

_FAMILY_AFFINITY: dict[tuple[str, str], float] = {
    # Floral cluster
    ("floral", "floral"):              1.00,
    ("floral", "powdery"):             0.65,
    ("floral", "floral oriental"):     0.70,
    ("floral", "fruity"):              0.55,
    ("floral", "green"):               0.45,
    ("floral", "chypre"):              0.50,
    # Woody cluster
    ("woody", "woody"):                1.00,
    ("woody", "earthy"):               0.75,
    ("woody", "oriental"):             0.65,
    ("woody", "chypre"):               0.60,
    ("woody", "tobacco"):              0.55,
    ("woody", "fougere"):              0.60,
    # Oriental cluster
    ("oriental", "oriental"):          1.00,
    ("oriental", "floral oriental"):   0.80,
    ("oriental", "spicy"):             0.70,
    ("oriental", "gourmand"):          0.65,
    ("oriental", "woody"):             0.55,
    # Fresh cluster
    ("fresh", "fresh"):                1.00,
    ("fresh", "citrus"):               0.85,
    ("fresh", "aquatic"):              0.75,
    ("fresh", "aromatic"):             0.60,
    ("fresh", "green"):                0.65,
    ("fresh", "fougere"):              0.55,
    # Citrus cluster
    ("citrus", "citrus"):              1.00,
    ("citrus", "fresh"):               0.85,
    ("citrus", "aromatic"):            0.60,
    ("citrus", "fruity"):              0.65,
    # Gourmand cluster
    ("gourmand", "gourmand"):          1.00,
    ("gourmand", "oriental"):          0.60,
    ("gourmand", "powdery"):           0.55,
    # Chypre cluster
    ("chypre", "chypre"):              1.00,
    ("chypre", "floral"):              0.55,
    ("chypre", "woody"):               0.60,
    ("chypre", "mossy"):               0.80,
    # Fougere cluster
    ("fougere", "fougere"):            1.00,
    ("fougere", "aromatic"):           0.75,
    ("fougere", "woody"):              0.60,
    ("fougere", "fresh"):              0.50,
    # Aquatic
    ("aquatic", "aquatic"):            1.00,
    ("aquatic", "fresh"):              0.80,
    ("aquatic", "green"):              0.55,
}


def _family_affinity(fa: str, fb: str) -> float:
    """Return affinity score for two olfactive families."""
    fa, fb = fa.lower().strip(), fb.lower().strip()
    return (
        _FAMILY_AFFINITY.get((fa, fb))
        or _FAMILY_AFFINITY.get((fb, fa))
        or (1.0 if fa == fb else 0.0)
    )


# ── Note sets for common fragrance notes (for semantic grouping) ─────────────

_NOTE_SYNONYMS: dict[str, frozenset[str]] = {
    "rose":       frozenset({"rose", "turkish rose", "bulgarian rose", "rose absolute", "damask rose"}),
    "oud":        frozenset({"oud", "agarwood", "oud wood", "cambodian oud"}),
    "sandalwood": frozenset({"sandalwood", "australian sandalwood", "mysore sandalwood"}),
    "jasmine":    frozenset({"jasmine", "jasmine absolute", "sambac jasmine"}),
    "vanilla":    frozenset({"vanilla", "vanilla absolute", "tahitian vanilla", "vanilla bean"}),
    "musk":       frozenset({"musk", "white musk", "clean musk", "ambrette", "ambergris"}),
    "bergamot":   frozenset({"bergamot", "bergamot oil", "italian bergamot"}),
    "cedar":      frozenset({"cedar", "cedarwood", "atlas cedar", "virginia cedar", "cedar leaf"}),
    "patchouli":  frozenset({"patchouli", "dark patchouli", "patchouli heart"}),
    "amber":      frozenset({"amber", "ambergris", "amber resin", "labdanum"}),
    "vetiver":    frozenset({"vetiver", "haitian vetiver", "vetiver root"}),
    "iris":       frozenset({"iris", "orris root", "iris pallida", "iris butter"}),
    "neroli":     frozenset({"neroli", "orange blossom", "fleur d'oranger"}),
    "ylang ylang":frozenset({"ylang ylang", "cananga"}),
}

def _canonical_note(note: str) -> str:
    """Return the canonical name for a note, collapsing synonyms."""
    note_lower = note.lower().strip()
    for canonical, synonyms in _NOTE_SYNONYMS.items():
        if note_lower in synonyms:
            return canonical
    return note_lower


@dataclass
class FragranceProfile:
    """Parsed fragrance note pyramid."""
    top_notes:    frozenset[str]
    mid_notes:    frozenset[str]
    base_notes:   frozenset[str]
    all_notes:    frozenset[str]
    family:       str                    # Primary olfactive family
    longevity:    str | None             # light | moderate | long-lasting | very long-lasting
    sillage:      str | None             # intimate | moderate | strong | enormous
    season:       list[str] | None


@dataclass
class FragranceMatchResult:
    """Result of comparing two fragrance profiles."""
    overall_score:   float
    note_score:      float              # Weighted pyramid note overlap
    family_score:    float              # Olfactive family affinity
    character_score: float              # Longevity + sillage + season
    top_overlap:     list[str]
    mid_overlap:     list[str]
    base_overlap:    list[str]
    all_overlap:     list[str]
    shared_family:   bool
    strength:        str               # "dupe" | "similar" | "different"
    summary:         str               # Human-readable one-liner


class FragranceEngine:
    """
    Parse fragrance attributes and compute multi-dimensional match scores.
    """

    # ── Parsing ───────────────────────────────────────────────────────────────

    def parse(self, attrs: dict[str, Any]) -> FragranceProfile:
        """Parse a product's attributes dict into a FragranceProfile."""
        def _parse_notes(val) -> frozenset[str]:
            if not val:
                return frozenset()
            if isinstance(val, str):
                return frozenset(_canonical_note(n) for n in val.split(",") if n.strip())
            if isinstance(val, list):
                return frozenset(_canonical_note(n) for n in val if n)
            return frozenset()

        top  = _parse_notes(attrs.get("top_notes") or attrs.get("top"))
        mid  = _parse_notes(attrs.get("mid_notes") or attrs.get("middle") or attrs.get("heart"))
        base = _parse_notes(attrs.get("base_notes") or attrs.get("base"))

        return FragranceProfile(
            top_notes=top,
            mid_notes=mid,
            base_notes=base,
            all_notes=top | mid | base,
            family=(attrs.get("family") or "").lower().strip(),
            longevity=(attrs.get("longevity") or "").lower().strip() or None,
            sillage=(attrs.get("sillage") or "").lower().strip() or None,
            season=attrs.get("season") or None,
        )

    # ── Comparison ────────────────────────────────────────────────────────────

    def compare(self, a: FragranceProfile, b: FragranceProfile) -> FragranceMatchResult:
        """
        Multi-dimensional fragrance similarity.

        note_score = 0.20 × top_jaccard + 0.30 × mid_jaccard + 0.50 × base_jaccard
        family_score = affinity(a.family, b.family)
        character_score = avg(longevity_match, sillage_match, season_overlap)
        overall = 0.55 × note_score + 0.30 × family_score + 0.15 × character_score
        """
        # Note Jaccard per layer
        top_j  = self._jaccard(a.top_notes,  b.top_notes)
        mid_j  = self._jaccard(a.mid_notes,  b.mid_notes)
        base_j = self._jaccard(a.base_notes, b.base_notes)

        # Handle missing note layers gracefully
        layer_scores  = []
        layer_weights = []
        if a.top_notes or b.top_notes:
            layer_scores.append(top_j)
            layer_weights.append(0.20)
        if a.mid_notes or b.mid_notes:
            layer_scores.append(mid_j)
            layer_weights.append(0.30)
        if a.base_notes or b.base_notes:
            layer_scores.append(base_j)
            layer_weights.append(0.50)

        total_w   = sum(layer_weights) or 1.0
        note_score = sum(s * w for s, w in zip(layer_scores, layer_weights)) / total_w

        # Family score
        family_score = _family_affinity(a.family, b.family) if a.family and b.family else 0.5

        # Character score
        character_score = self._character_score(a, b)

        # Overall
        overall = 0.55 * note_score + 0.30 * family_score + 0.15 * character_score

        # Build overlap lists for display
        top_ovl  = sorted(a.top_notes  & b.top_notes)
        mid_ovl  = sorted(a.mid_notes  & b.mid_notes)
        base_ovl = sorted(a.base_notes & b.base_notes)
        all_ovl  = sorted(a.all_notes  & b.all_notes)

        strength = (
            "dupe"      if overall >= 0.70 else
            "similar"   if overall >= 0.50 else
            "different"
        )

        summary = self._build_summary(strength, all_ovl, a.family, b.family, family_score)

        return FragranceMatchResult(
            overall_score=round(overall, 4),
            note_score=round(note_score, 4),
            family_score=round(family_score, 4),
            character_score=round(character_score, 4),
            top_overlap=top_ovl,
            mid_overlap=mid_ovl,
            base_overlap=base_ovl,
            all_overlap=all_ovl,
            shared_family=(a.family == b.family and bool(a.family)),
            strength=strength,
            summary=summary,
        )

    def compare_attrs(self, attrs_a: dict, attrs_b: dict) -> FragranceMatchResult:
        """Convenience: parse both and compare."""
        return self.compare(self.parse(attrs_a), self.parse(attrs_b))

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _jaccard(a: frozenset, b: frozenset) -> float:
        if not a and not b:
            return 0.0
        intersection = a & b
        union        = a | b
        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def _character_score(a: FragranceProfile, b: FragranceProfile) -> float:
        scores = []
        # Longevity match
        _LONGEVITY_ORDER = ["light", "moderate", "long-lasting", "very long-lasting"]
        if a.longevity and b.longevity:
            la = _LONGEVITY_ORDER.index(a.longevity) if a.longevity in _LONGEVITY_ORDER else 1
            lb = _LONGEVITY_ORDER.index(b.longevity) if b.longevity in _LONGEVITY_ORDER else 1
            scores.append(1.0 - abs(la - lb) / (len(_LONGEVITY_ORDER) - 1))
        # Sillage match
        _SILLAGE_ORDER = ["intimate", "moderate", "strong", "enormous"]
        if a.sillage and b.sillage:
            sa = _SILLAGE_ORDER.index(a.sillage) if a.sillage in _SILLAGE_ORDER else 1
            sb = _SILLAGE_ORDER.index(b.sillage) if b.sillage in _SILLAGE_ORDER else 1
            scores.append(1.0 - abs(sa - sb) / (len(_SILLAGE_ORDER) - 1))
        # Season overlap
        if a.season and b.season:
            sa_set, sb_set = set(a.season), set(b.season)
            scores.append(len(sa_set & sb_set) / len(sa_set | sb_set) if sa_set | sb_set else 0)
        return round(sum(scores) / len(scores), 4) if scores else 0.5

    @staticmethod
    def _build_summary(
        strength: str, shared_notes: list[str], fam_a: str, fam_b: str, family_score: float
    ) -> str:
        if strength == "dupe":
            note_str = ", ".join(shared_notes[:3]) if shared_notes else "similar notes"
            return f"Fragrance dupe — shares {note_str}"
        elif strength == "similar":
            if fam_a == fam_b and fam_a:
                return f"Same {fam_a} family with overlapping character"
            return f"Similar character — {fam_a} meets {fam_b}"
        else:
            return "Different fragrance profile"


# Module-level singleton
fragrance_engine = FragranceEngine()
