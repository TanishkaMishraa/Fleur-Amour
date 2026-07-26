"""
AuraFit — Beauty & style recommendation generator.
Converts raw analysis results into actionable, personalised recommendations.
All logic is rule-based (deterministic, auditable, fast).
Recommendations map directly to product categories in the catalog service.
"""
from __future__ import annotations

from app.schemas.analysis_schemas import (
    AnalysisResult, AcneAnalysisResult, DarkCircleResult,
    FaceShape, HairAnalysisResult, SkinConcern,
    SkinTextureResult, SkinToneResult, Undertone,
)


class RecommendationGenerator:
    """Generate makeup, skincare, and hairstyle recommendations from analysis."""

    def generate(self, result: AnalysisResult) -> tuple[dict, dict, list[str]]:
        """
        Returns:
            makeup_recommendations: dict
            skincare_recommendations: dict
            hairstyle_recommendations: list[str]
        """
        makeup   = self._makeup(result)
        skincare = self._skincare(result)
        hairstyles = self._hairstyles(result)
        return makeup, skincare, hairstyles

    # ── Makeup ────────────────────────────────────────────────────────────────

    def _makeup(self, r: AnalysisResult) -> dict:
        tone      = r.skin_tone
        undertone = tone.undertone
        shape     = r.face_shape.shape

        # Foundation
        foundation = {
            "shade_category":  tone.tone.value,
            "undertone":       undertone.value,
            "finish":          self._foundation_finish(r),
            "coverage":        self._foundation_coverage(r),
        }

        # Blush placement
        blush = {
            "placement":  self._blush_placement(shape),
            "tone":       "peach" if undertone == Undertone.WARM else
                          "berry" if undertone == Undertone.COOL else "rose",
        }

        # Contour / highlight
        contour = {
            "technique": self._contour_technique(shape),
            "highlight_placement": self._highlight_placement(shape),
        }

        # Eye makeup
        eye = {
            "liner_style": self._eye_liner(shape),
            "shadow_palette": self._shadow_palette(undertone),
        }

        # Lip colours
        lip = {
            "recommended_tones": self._lip_tones(undertone, tone.tone.value),
            "finish": "satin",
        }

        return {
            "foundation": foundation,
            "blush":      blush,
            "contour":    contour,
            "eye_makeup": eye,
            "lip_color":  lip,
        }

    # ── Skincare ──────────────────────────────────────────────────────────────

    def _skincare(self, r: AnalysisResult) -> dict:
        concerns: list[str] = [c.concern.value for c in r.skin_concerns if c.severity > 0.2]
        texture   = r.skin_texture
        dark_c    = r.dark_circles
        acne      = r.acne_analysis

        # Active ingredients
        actives = []
        if SkinConcern.ACNE.value in concerns:
            actives += ["salicylic_acid", "niacinamide", "benzoyl_peroxide"]
        if SkinConcern.HYPERPIGMENTATION.value in concerns:
            actives += ["vitamin_c", "alpha_arbutin", "kojic_acid"]
        if dark_c.detected:
            actives += ["caffeine", "vitamin_k", "retinol"]
        if texture.roughness > 0.5:
            actives += ["aha_glycolic", "pha_gluconolactone"]
        if SkinConcern.FINE_LINES.value in concerns:
            actives += ["retinol", "peptides", "hyaluronic_acid"]

        # Routine order
        routine = self._build_routine(concerns, acne.severity, texture)

        # SPF emphasis
        spf_note = (
            "Daily SPF 50+ is especially important for your skin tone "
            "to prevent further hyperpigmentation."
            if SkinConcern.HYPERPIGMENTATION.value in concerns
            else "Daily SPF 30+ recommended."
        )

        return {
            "primary_concerns":      concerns[:3],
            "recommended_actives":   list(dict.fromkeys(actives))[:6],  # dedupe, keep order
            "morning_routine":       routine["morning"],
            "evening_routine":       routine["evening"],
            "spf_guidance":          spf_note,
            "avoid_ingredients":     self._avoid_list(concerns),
            "concern_severity_map":  {c.concern.value: round(c.severity, 2)
                                      for c in r.skin_concerns},
        }

    # ── Hairstyles ────────────────────────────────────────────────────────────

    def _hairstyles(self, r: AnalysisResult) -> list[str]:
        shape = r.face_shape.shape
        hair  = r.hair_analysis

        _SHAPE_STYLES: dict[FaceShape, list[str]] = {
            FaceShape.OVAL:     ["Any length and style", "Curtain bangs", "Beachy waves",
                                 "Sleek blowout", "Textured bob"],
            FaceShape.ROUND:    ["Long layers", "Side-swept bangs", "High ponytail",
                                 "Angled bob (longer in front)", "Voluminous crown styles"],
            FaceShape.SQUARE:   ["Soft waves", "Side-swept styles", "Wispy bangs",
                                 "Long curtain bangs", "Textured layers"],
            FaceShape.HEART:    ["Chin-length bob", "Side-parted long hair",
                                 "Low bun with face-framing pieces", "Layered waves"],
            FaceShape.OBLONG:   ["Blunt bob", "Curtain bangs", "Voluminous wavy hair",
                                 "Shoulder-length layers"],
            FaceShape.DIAMOND:  ["Chin-length bob", "Full fringe", "Styles with volume at chin",
                                 "Wispy side bangs"],
            FaceShape.TRIANGLE: ["Voluminous top layers", "Side-parted waves",
                                 "Pompadour or lifted crown"],
        }

        base = _SHAPE_STYLES.get(shape, ["Consult with your stylist for personalised advice"])

        # Personalise by current hair type
        if hair.hair_type.value in ("curly", "coily"):
            base = [s for s in base if "sleek" not in s.lower()] + ["Defined curl sets", "Wash-and-go"]

        return base[:5]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _foundation_finish(self, r: AnalysisResult) -> str:
        oiliness = next((c.severity for c in r.skin_concerns
                         if c.concern == SkinConcern.OILINESS), 0.0)
        if oiliness > 0.5:
            return "matte"
        if r.skin_texture.roughness > 0.5:
            return "satin"
        return "luminous"

    def _foundation_coverage(self, r: AnalysisResult) -> str:
        if r.acne_analysis.detected and r.acne_analysis.severity in ("moderate", "severe"):
            return "full"
        if any(c.severity > 0.4 for c in r.skin_concerns):
            return "medium_to_full"
        return "light_to_medium"

    def _blush_placement(self, shape: FaceShape) -> str:
        return {
            FaceShape.ROUND:    "Apply high on cheekbones, blend toward temples to elongate",
            FaceShape.SQUARE:   "Circular placement on apple of cheeks to soften jaw",
            FaceShape.HEART:    "Apply below cheekbone apex, blend outward",
            FaceShape.OBLONG:   "Horizontal sweep across cheeks to add width",
        }.get(shape, "Sweep along cheekbones from apple toward temples")

    def _contour_technique(self, shape: FaceShape) -> str:
        return {
            FaceShape.ROUND:   "Contour temples and jaw sides; highlight centre-T",
            FaceShape.SQUARE:  "Soften corners with contour; highlight cheekbone peaks",
            FaceShape.HEART:   "Contour forehead sides; highlight mid-forehead and chin",
            FaceShape.OBLONG:  "Contour hairline and chin; add blush width to cheeks",
        }.get(shape, "Standard contour: temples, cheekbones, jawline definition")

    def _highlight_placement(self, shape: FaceShape) -> str:
        return {
            FaceShape.ROUND:   "Inner corners of eyes, cupid's bow, high bridge of nose",
            FaceShape.HEART:   "Centre forehead, under-eye, cupid's bow",
        }.get(shape, "Brow bone, inner eye corner, top of cheekbone, cupid's bow")

    def _eye_liner(self, shape: FaceShape) -> str:
        return {
            FaceShape.ROUND:   "Winged liner extending outward to elongate eyes",
            FaceShape.SQUARE:  "Soft smudged liner on upper lash line",
            FaceShape.HEART:   "Thin liner, thicker at outer corners",
        }.get(shape, "Classic thin liner on upper lid, optional wing")

    def _shadow_palette(self, undertone: Undertone) -> list[str]:
        if undertone == Undertone.WARM:
            return ["terracotta", "copper", "warm_bronze", "peach", "rust"]
        if undertone == Undertone.COOL:
            return ["mauve", "plum", "grey_taupe", "rose", "navy"]
        return ["taupe", "bronze", "chocolate", "rose_gold", "champagne"]

    def _lip_tones(self, undertone: Undertone, skin_tone: str) -> list[str]:
        bases = {
            Undertone.WARM:    ["coral", "warm_red", "terracotta", "peach", "nude_with_warmth"],
            Undertone.COOL:    ["berry", "plum", "cool_red", "dusty_rose", "nude_with_pink"],
            Undertone.NEUTRAL: ["rose", "brick_red", "mauve", "natural_nude"],
        }
        return bases.get(undertone, ["rose", "natural_nude"])

    def _build_routine(
        self, concerns: list[str], acne_severity: str, texture: SkinTextureResult
    ) -> dict:
        morning = ["Gentle cleanser", "Vitamin C serum", "Moisturiser", "SPF 50+"]
        evening = ["Oil cleanser (double cleanse)", "Exfoliating cleanser (2×/week)", "Treatment serum", "Moisturiser"]

        if "acne" in concerns:
            morning.insert(1, "Salicylic acid toner")
            evening[2] = "Niacinamide + salicylic acid serum"
        if "dark_circles" in concerns:
            morning.insert(1, "Eye cream (caffeine)")
        if "hyperpigmentation" in concerns:
            evening.insert(3, "Alpha arbutin serum")
        if texture.roughness > 0.5:
            evening.insert(2, "AHA/BHA exfoliant (3×/week, not with retinol nights)")

        return {"morning": morning, "evening": evening}

    def _avoid_list(self, concerns: list[str]) -> list[str]:
        avoid = []
        if "acne" in concerns:
            avoid += ["coconut_oil", "isopropyl_myristate", "lanolin (heavy)"]
        if "redness" in concerns:
            avoid += ["alcohol_denat", "fragrance", "menthol"]
        return avoid
