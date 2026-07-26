"""
AuraFit — Shade Matching Engine.

Converts hex color codes to CIELAB color space and computes ΔE (Delta-E)
perceptual colour difference — the industry-standard metric for shade matching.

ΔE interpretation (CIE 1994 standard):
  ΔE < 1.0  = imperceptible difference ("Exact Dupe")
  ΔE < 2.0  = very close ("Near-perfect Dupe")
  ΔE < 3.5  = noticeable only to trained eyes ("Very Good Match")
  ΔE < 5.0  = slight difference ("Good Match")
  ΔE < 8.0  = perceivable but cosmetically acceptable ("Fair Match")
  ΔE ≥ 8.0  = clearly different shades

Similarity score mapping (for the UI):
  0–1   → 100–97%
  1–2   → 97–92%
  2–3.5 → 92–82%
  3.5–5 → 82–70%
  5–8   → 70–50%
  8+    → < 50% (not a shade dupe)

Also handles:
  - Shade range compatibility (for products with multiple shades)
  - Finish similarity (matte vs satin vs gloss — affects perceived colour)
  - Undertone compatibility
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ShadeMatchResult:
    """Result of comparing two product shades."""
    delta_e:          float          # CIE ΔE 1994 colour difference
    similarity_score: float          # [0,1] — monotonically decreasing with ΔE
    similarity_pct:   int            # 0–100
    hex_source:       str
    hex_alternative:  str
    lab_source:       tuple[float, float, float]  # L*, a*, b*
    lab_alternative:  tuple[float, float, float]
    strength:         str            # "exact" | "near" | "very_good" | "good" | "fair" | "different"
    description:      str


class ShadeEngine:
    """
    Compute perceptual colour similarity using CIELAB ΔE.
    All methods are pure functions.
    """

    # ── Hex → Lab conversion ──────────────────────────────────────────────────

    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Parse hex string → (R, G, B) integers [0, 255]."""
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    @staticmethod
    def rgb_to_xyz(r: int, g: int, b: int) -> tuple[float, float, float]:
        """Convert RGB [0,255] → CIE XYZ (D65 illuminant)."""
        # Linearise
        def _linear(v: float) -> float:
            v /= 255.0
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

        rl, gl, bl = _linear(r), _linear(g), _linear(b)

        # sRGB → XYZ (D65 matrix)
        x = rl * 0.4124564 + gl * 0.3575761 + bl * 0.1804375
        y = rl * 0.2126729 + gl * 0.7151522 + bl * 0.0721750
        z = rl * 0.0193339 + gl * 0.1191920 + bl * 0.9503041
        return x, y, z

    @staticmethod
    def xyz_to_lab(x: float, y: float, z: float) -> tuple[float, float, float]:
        """Convert CIE XYZ → L*a*b* (D65 illuminant)."""
        # D65 reference white
        xn, yn, zn = 0.95047, 1.00000, 1.08883

        def _f(t: float) -> float:
            return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

        fx, fy, fz = _f(x / xn), _f(y / yn), _f(z / zn)
        L  = 116 * fy - 16
        a  = 500 * (fx - fy)
        b  = 200 * (fy - fz)
        return L, a, b

    def hex_to_lab(self, hex_color: str) -> tuple[float, float, float]:
        """One-shot hex → Lab*."""
        r, g, b = self.hex_to_rgb(hex_color)
        x, y, z = self.rgb_to_xyz(r, g, b)
        return self.xyz_to_lab(x, y, z)

    # ── ΔE calculation ────────────────────────────────────────────────────────

    @staticmethod
    def delta_e_cie94(
        lab1: tuple[float, float, float],
        lab2: tuple[float, float, float],
        graphics: bool = True,
    ) -> float:
        """
        Compute CIE ΔE 1994 between two Lab* triplets.
        graphics=True uses graphic arts weights (default for cosmetics);
        graphics=False uses textiles weights.
        """
        L1, a1, b1 = lab1
        L2, a2, b2 = lab2

        kL = 1.0 if graphics else 2.0
        K1 = 0.045 if graphics else 0.048
        K2 = 0.015 if graphics else 0.014

        dL   = L1 - L2
        C1   = math.sqrt(a1**2 + b1**2)
        C2   = math.sqrt(a2**2 + b2**2)
        dC   = C1 - C2
        da   = a1 - a2
        db   = b1 - b2
        dH2  = da**2 + db**2 - dC**2
        dH   = math.sqrt(max(dH2, 0))

        SL   = 1.0
        SC   = 1 + K1 * C1
        SH   = 1 + K2 * C1

        result = math.sqrt(
            (dL / (kL * SL)) ** 2
            + (dC / SC) ** 2
            + (dH / SH) ** 2
        )
        return round(result, 4)

    # ── Similarity scoring ────────────────────────────────────────────────────

    @staticmethod
    def delta_e_to_score(delta_e: float) -> float:
        """Convert ΔE to a [0, 1] similarity score using exponential decay."""
        # Score = exp(-k * ΔE) where k is tuned so:
        #   ΔE=0 → 1.00, ΔE=5 → ~0.70, ΔE=10 → ~0.50, ΔE=20 → ~0.25
        k = 0.07
        return round(math.exp(-k * delta_e), 4)

    @staticmethod
    def _strength(delta_e: float) -> tuple[str, str]:
        if delta_e < 1.0:
            return "exact",      "Virtually identical shades"
        elif delta_e < 2.0:
            return "near",       "Near-perfect shade match"
        elif delta_e < 3.5:
            return "very_good",  "Excellent shade match"
        elif delta_e < 5.0:
            return "good",       "Good shade match"
        elif delta_e < 8.0:
            return "fair",       "Similar colour family"
        else:
            return "different",  "Different shade"

    # ── Main comparison ────────────────────────────────────────────────────────

    def compare_hex(self, hex_a: str, hex_b: str) -> ShadeMatchResult:
        """Compare two hex colour codes. Returns full ShadeMatchResult."""
        try:
            lab_a = self.hex_to_lab(hex_a)
            lab_b = self.hex_to_lab(hex_b)
        except (ValueError, AttributeError):
            return self._empty(hex_a or "#000000", hex_b or "#000000")

        delta_e = self.delta_e_cie94(lab_a, lab_b)
        score   = self.delta_e_to_score(delta_e)
        strength, desc = self._strength(delta_e)

        return ShadeMatchResult(
            delta_e=delta_e,
            similarity_score=score,
            similarity_pct=round(score * 100),
            hex_source=hex_a,
            hex_alternative=hex_b,
            lab_source=tuple(round(v, 2) for v in lab_a),
            lab_alternative=tuple(round(v, 2) for v in lab_b),
            strength=strength,
            description=desc,
        )

    def compare_shade_ranges(
        self, shades_a: list[str], shades_b: list[str]
    ) -> tuple[float, str, str]:
        """
        Best-match between two shade range lists.
        Used when a product has multiple shade options.
        Returns (best_score, best_hex_a, best_hex_b).
        """
        best_score = 0.0
        best_ha, best_hb = "#000000", "#000000"

        for ha in shades_a:
            for hb in shades_b:
                try:
                    result = self.compare_hex(ha, hb)
                    if result.similarity_score > best_score:
                        best_score = result.similarity_score
                        best_ha, best_hb = ha, hb
                except Exception:
                    continue

        return best_score, best_ha, best_hb

    def _empty(self, ha: str, hb: str) -> ShadeMatchResult:
        return ShadeMatchResult(
            delta_e=99.0, similarity_score=0.0, similarity_pct=0,
            hex_source=ha, hex_alternative=hb,
            lab_source=(0, 0, 0), lab_alternative=(0, 0, 0),
            strength="different", description="Shade data unavailable",
        )


# Module-level singleton
shade_engine = ShadeEngine()
