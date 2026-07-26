"""
AuraFit — Style DNA NLP Report Generator (Stage 8).

Assembles all available user data:
  - UserProfile      (physical attrs, skin concerns, style archetypes, budget)
  - FacialScan       (face shape, skin tone/undertone, acne, hair analysis)
  - ColorProfile     (color season, palette, makeup recs)
  - FragranceProfile (note families, intensity, previous fragrances)
  - QuizSession      (personality dimensions, archetypes, lifestyle)
  - WardrobeItems    (category distribution, utilisation, brands)

Then generates one coherent StyleDNAReport with:
  - Personal headline ("Effortlessly Romantic, Beautifully Distinct")
  - Narrative intro paragraph
  - 7 detailed profile sections (beauty, skin, color, fashion, fragrance,
    hairstyle, recommendations)
  - Occasion guide
  - Personalised product recommendation pointers

All prose is template-driven + GPT-4o/Claude augmented for the narrative.
Production: the LLM call is optional — the template engine alone produces
a complete, high-quality report without any API dependency.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

ENGINE_VERSION = "1.0"

# ── Headline templates ────────────────────────────────────────────────────────
# Keyed by (primary_archetype, color_season_family)

_HEADLINES: dict[tuple[str, str], list[str]] = {
    ("The Romantic",   "spring"): ["Blooming Beautifully", "Soft, Radiant & Irresistibly You"],
    ("The Romantic",   "summer"): ["Quietly Magnetic", "The Romantic Minimalist"],
    ("The Classic",    "winter"): ["Timeless. Powerful. Undeniably You.", "Refined Elegance Perfected"],
    ("The Classic",    "autumn"): ["Warmly Sophisticated", "The Art of Quiet Luxury"],
    ("The Edgy",       "winter"): ["Fearlessly Original", "Dark Elegance, Sharp Edge"],
    ("The Edgy",       "autumn"): ["Untamed & Unmistakeable"],
    ("The Glamorous",  "winter"): ["Brilliantly Iconic", "Drama by Design"],
    ("The Glamorous",  "spring"): ["Radiant Energy, Golden Hour Beauty"],
    ("The Minimalist", "summer"): ["Effortless. Precise. Perfect.", "The Less-is-More Masterclass"],
    ("The Minimalist", "winter"): ["Stark Elegance Redefined"],
    ("The Bohemian",   "autumn"): ["Free Spirit, Earthy Soul", "Wander-Worn and Beautiful"],
    ("The Bohemian",   "spring"): ["Sun-Kissed & Wildly Free"],
    ("The Creative",   "spring"): ["Beautifully Unpredictable"],
    ("The Creative",   "winter"): ["Art Wears You Best"],
    ("The Sophisticated","winter"):["Polished Perfection", "Command the Room, Quietly"],
    ("The Preppy",     "summer"): ["Classically Cool, Confidently You"],
    ("The Athletic",   "spring"): ["Active Beauty, Effortless Power"],
    ("The Casual",     "autumn"): ["Relaxed Glamour — It's Always the Right Outfit"],
}

_DEFAULT_HEADLINES = [
    "Your Unique Beauty Story",
    "Distinctly, Perfectly You",
    "Style Intelligence, Beautifully Decoded",
]

# ── Body-shape styling guides ─────────────────────────────────────────────────

_BODY_SHAPE_GUIDE: dict[str, dict[str, Any]] = {
    "hourglass": {
        "summary":   "Balanced proportions — your silhouette is naturally harmonious.",
        "flatter":   ["Wrap dresses", "High-waisted silhouettes", "Belted styles", "Bodycon cuts"],
        "avoid":     ["Boxy oversized layers that hide your waist", "Drop-waist styles"],
        "tips":      "Emphasise your waist with belts and wrap cuts. You can carry almost any silhouette beautifully.",
    },
    "pear": {
        "summary":   "Fuller hips and thighs with a narrower upper body — draw the eye upward.",
        "flatter":   ["A-line skirts", "Wide-leg trousers", "Statement tops and necklines", "Boat necks and off-shoulders"],
        "avoid":     ["Skinny jeans with plain tops", "Cropped tops that end at the hip"],
        "tips":      "Balance with structured shoulders and standout necklines. Wide-leg trousers are your best friend.",
    },
    "apple": {
        "summary":   "Fuller midsection — create definition and draw attention to your best features.",
        "flatter":   ["Empire waists", "V-necks", "Wrap styles", "Flowy fabrics that skim the middle"],
        "avoid":     ["Tight waistbands", "Horizontal stripes across the midsection"],
        "tips":      "V-necklines elongate and open up your silhouette. Empire cuts are universally flattering.",
    },
    "rectangle": {
        "summary":   "Proportionally straight — create the illusion of curves with your styling.",
        "flatter":   ["Peplum tops", "Ruffles and volume", "Wrap styles", "Belted looks at the waist"],
        "avoid":     ["Straight-cut shift dresses with no definition"],
        "tips":      "Create shape with cinched waists, layering, and structured shoulders.",
    },
    "inverted_triangle": {
        "summary":   "Broader shoulders, narrower hips — balance by adding volume below the waist.",
        "flatter":   ["A-line and flared skirts", "Wide-leg trousers", "Soft necklines", "Flowy bottoms"],
        "avoid":     ["Boat necks and off-shoulder tops that widen the shoulders further"],
        "tips":      "Minimise the shoulder zone with simple tops; add drama and volume at the hem.",
    },
}

# ── Face-shape hairstyle guides ───────────────────────────────────────────────

_FACE_SHAPE_HAIR: dict[str, dict[str, Any]] = {
    "oval": {
        "summary":   "Lucky you — an oval face is universally flattering for virtually any hairstyle.",
        "recommend": ["Long layers", "Bob of any length", "Curtain bangs", "Blunt cuts"],
        "avoid":     ["Styles that cover your forehead entirely"],
        "tip":       "Almost any haircut works. Experiment with curtain bangs or a sleek blunt bob to complement your balanced proportions.",
    },
    "round": {
        "summary":   "Soft and symmetrical — add length and angles to elongate the face.",
        "recommend": ["Long layers with height at the crown", "Side parts", "Sleek straight hair", "Lob (long bob)"],
        "avoid":     ["Short blunt bobs at jaw level", "Heavy fringe that shortens the face"],
        "tip":       "Side parts and styles that add volume at the crown create a beautifully elongated appearance.",
    },
    "square": {
        "summary":   "Strong jawline and defined angles — soften with curves and movement.",
        "recommend": ["Soft waves and curls", "Side-swept bangs", "Long layers", "Textured lob"],
        "avoid":     ["Blunt bobs that end at the jaw", "Slicked-back styles that emphasise the jaw"],
        "tip":       "Soft waves and side-swept styles beautifully soften a strong square jaw.",
    },
    "heart": {
        "summary":   "Wider forehead, narrower chin — add volume at the chin and jaw.",
        "recommend": ["Chin-length bobs", "Curls and waves at jaw level", "Middle parts", "Full fringe"],
        "avoid":     ["Volume at the crown that widens the forehead"],
        "tip":       "Chin-grazing bobs and full fringes beautifully balance a wider forehead.",
    },
    "oblong": {
        "summary":   "Longer face — add width and fullness to create the appearance of a shorter face.",
        "recommend": ["Curtain bangs", "Layers with volume at the sides", "Waves", "Bob with volume"],
        "avoid":     ["Very long straight hair with no volume", "Extreme centre parts with no fringe"],
        "tip":       "Curtain bangs and side volume are your best tools for creating beautiful balance.",
    },
    "diamond": {
        "summary":   "Narrow forehead and jaw with wide cheekbones — balance with width at forehead and chin.",
        "recommend": ["Full fringe", "Chin-length styles", "Styles with volume at crown and chin", "Soft waves"],
        "avoid":     ["Styles that add volume only at the cheekbones"],
        "tip":       "A full fringe adds width at the forehead. Chin-length cuts balance your beautiful cheekbones.",
    },
}

# ── Fragrance occasion guide ──────────────────────────────────────────────────

_FRAGRANCE_OCCASIONS: dict[str, dict[str, str]] = {
    "floral":   {"work": "soft florals (rose, peony)", "evening": "intense floral orientals (jasmine, tuberose)", "casual": "fresh florals (freesia, lily of the valley)"},
    "woody":    {"work": "clean woods (cedar, sandalwood)", "evening": "dark woods + oud (vetiver, patchouli)", "casual": "light woods + citrus"},
    "oriental": {"work": "light oriental (soft amber)", "evening": "full oriental (oud, spice, musk)", "casual": "gourmand orientals (vanilla, tonka)"},
    "fresh":    {"work": "clean aquatics and green", "evening": "warm fresh (white musk)", "casual": "citrus + light woods"},
    "citrus":   {"work": "bright citrus + herbs", "evening": "citrus + warm base notes", "casual": "sparkling citrus"},
    "chypre":   {"work": "modern chypre (bergamot, oakmoss)", "evening": "classic chypre (labdanum, rose)", "casual": "light floral chypre"},
    "gourmand": {"work": "light gourmand (subtle caramel)", "evening": "indulgent gourmand (chocolate, caramel)", "casual": "vanilla + fruit"},
    "fougere":  {"work": "aromatic fougere (lavender, herbs)", "evening": "dark fougere (musks, coumarin)", "casual": "fresh fougere"},
}


@dataclass
class StyleDNAInput:
    """All source data assembled before report generation."""
    user_id:        uuid.UUID
    full_name:      str
    age_range:      str | None
    # Physical
    skin_tone:      str | None
    skin_type:      str | None
    undertone:      str | None
    skin_concerns:  list[str]
    face_shape:     str | None
    body_shape:     str | None
    hair_type:      str | None
    hair_color:     str | None
    eye_color:      str | None
    height_cm:      float | None
    # AI-derived
    skin_analysis:  dict
    facial_features:dict
    acne_data:      dict
    hair_analysis:  dict
    symmetry_score: float | None
    # Color
    color_season:   str | None
    color_season_family: str | None
    palette_best:   list[dict]
    palette_neutrals:list[dict]
    palette_accents:list[dict]
    makeup_recs:    dict
    # Fragrance
    fragrance_family:list[str]
    preferred_notes:list[str]
    avoided_notes:  list[str]
    intensity_pref: str | None
    longevity_pref: str | None
    # Quiz / Style
    primary_archetype:   str | None
    secondary_archetype: str | None
    style_dimensions:    dict
    budget_tier:         str | None
    lifestyle_tags:      list[str]
    occasion_mix:        dict
    # Wardrobe
    top_categories:      list[str]
    wardrobe_count:      int
    # Misc
    currency:       str = "INR"
    extra: dict     = field(default_factory=dict)


@dataclass
class StyleDNAReportContent:
    """The generated report sections — all pure Python dicts / strings."""
    headline:              str
    narrative:             str
    beauty_profile:        dict
    skin_profile:          dict
    color_profile_section: dict
    fashion_profile:       dict
    fragrance_profile_section: dict
    hairstyle_profile:     dict
    recommendations:       dict
    personality:           dict
    occasion_guide:        dict
    data_hash:             str


class StyleDNANLPEngine:
    """
    Generates a complete StyleDNAReportContent from StyleDNAInput.
    All sections use structured data + prose templates.
    Optional: LLM call enhances the narrative intro + headline.
    """

    def generate(self, inp: StyleDNAInput) -> StyleDNAReportContent:
        """Entry point — generates the full report. Called from Celery task."""
        logger.info("style_dna.generate_start", user_id=str(inp.user_id))

        headline  = self._generate_headline(inp)
        narrative = self._generate_narrative(inp)

        return StyleDNAReportContent(
            headline=headline,
            narrative=narrative,
            beauty_profile=self._beauty_profile(inp),
            skin_profile=self._skin_profile(inp),
            color_profile_section=self._color_profile_section(inp),
            fashion_profile=self._fashion_profile(inp),
            fragrance_profile_section=self._fragrance_profile_section(inp),
            hairstyle_profile=self._hairstyle_profile(inp),
            recommendations=self._recommendations(inp),
            personality=self._personality_section(inp),
            occasion_guide=self._occasion_guide(inp),
            data_hash=self._compute_hash(inp),
        )

    # ── Section generators ────────────────────────────────────────────────────

    def _generate_headline(self, inp: StyleDNAInput) -> str:
        season_family = (inp.color_season_family or "spring").split("_")[-1]
        archetype     = inp.primary_archetype or "The Classic"
        key = (archetype, season_family)
        candidates = _HEADLINES.get(key)
        if not candidates:
            # Try just archetype
            for (a, _), texts in _HEADLINES.items():
                if a == archetype:
                    candidates = texts
                    break
        if not candidates:
            candidates = _DEFAULT_HEADLINES
        return candidates[hash(str(inp.user_id)) % len(candidates)]

    def _generate_narrative(self, inp: StyleDNAInput) -> str:
        name      = inp.full_name.split()[0] if inp.full_name else "You"
        archetype = inp.primary_archetype or "sophisticated"
        season    = (inp.color_season or "spring").replace("_", " ").title()
        tone_desc = {
            "fair":   "luminous fair",    "light":  "delicate light",
            "medium": "warm medium",      "olive":  "radiant olive",
            "tan":    "golden tan",       "deep":   "rich deep",
        }.get(inp.skin_tone or "", "beautiful")
        under_desc = {
            "cool": "cool-toned",  "warm": "warm-toned",  "neutral": "balanced",
        }.get(inp.undertone or "", "balanced")

        return (
            f"{name}, your AuraFit Style DNA reveals a beautifully layered identity. "
            f"You are a {archetype.lower().replace('the ', '')} at heart — "
            f"with a {tone_desc}, {under_desc} complexion that blooms in your "
            f"{season} color season. Your style is guided by {self._axis_prose(inp)}, "
            f"and your beauty choices reflect someone who views self-presentation as "
            f"{'a creative expression' if (inp.style_dimensions.get('experimentalism', 0) > 0.6) else 'an intentional practice'}. "
            f"This is your personalised guide to dressing, grooming, and scenting "
            f"in a way that feels authentically, undeniably you."
        )

    @staticmethod
    def _axis_prose(inp: StyleDNAInput) -> str:
        dims  = inp.style_dimensions or {}
        style = dims.get("style_axis", 0.5)
        energy= dims.get("energy_axis", 0.5)
        struct= dims.get("structure_axis", 0.5)
        parts = []
        if struct > 0.6:
            parts.append("a love of clean structure and tailored lines")
        elif struct < 0.4:
            parts.append("an embrace of relaxed, effortless shapes")
        if energy > 0.7:
            parts.append("a boldness that commands attention")
        elif energy < 0.3:
            parts.append("an understated elegance that whispers rather than shouts")
        if style > 0.7:
            parts.append("an avant-garde sensibility that sets trends")
        elif style < 0.3:
            parts.append("a commitment to timeless classics")
        return " and ".join(parts) if parts else "a strong personal sense of self"

    def _beauty_profile(self, inp: StyleDNAInput) -> dict:
        return {
            "headline":     f"The {(inp.primary_archetype or 'Classic').replace('The ', '')} Beauty",
            "summary":      f"Your beauty identity is anchored in {self._beauty_summary(inp)}.",
            "strengths":    self._beauty_strengths(inp),
            "signature_look": self._signature_look(inp),
            "power_features": self._power_features(inp),
        }

    def _skin_profile(self, inp: StyleDNAInput) -> dict:
        concerns     = inp.skin_concerns or []
        skin_tone    = inp.skin_tone or "medium"
        skin_type    = inp.skin_type or "combination"
        undertone    = inp.undertone or "neutral"

        # Routine steps
        morning_steps = ["Gentle cleanser", "Vitamin C serum (brightening)"]
        evening_steps = ["Oil cleanser + water-based cleanser", "Targeted treatment serum"]

        if "acne" in concerns or "oiliness" in concerns:
            morning_steps.append("Niacinamide serum (pore-minimising)")
            evening_steps.append("Salicylic acid treatment (BHA exfoliant)")
        if "hyperpigmentation" in concerns:
            morning_steps.append("Alpha Arbutin or Kojic Acid serum")
        if "fine_lines" in concerns or "anti_aging" in concerns:
            evening_steps.append("Retinol (start 2× per week)")
        if "dryness" in concerns or skin_type in ("dry",):
            morning_steps.append("Hyaluronic Acid serum + occlusive moisturiser")
            evening_steps.append("Rich ceramide cream or facial oil")
        if "redness" in concerns or skin_type == "sensitive":
            morning_steps.append("Centella Asiatica or Azelaic Acid serum")

        morning_steps += ["Moisturiser", f"SPF 50+ (non-negotiable for {skin_tone} skin)"]
        evening_steps += ["Moisturiser", "Optional: Facial oil or sleeping mask"]

        return {
            "tone":          skin_tone,
            "type":          skin_type,
            "undertone":     undertone,
            "fitzpatrick":   inp.skin_analysis.get("fitzpatrick"),
            "concerns":      concerns,
            "avoided_ingredients": inp.extra.get("avoided_ingredients", []),
            "key_actives":   self._recommended_actives(concerns, skin_type),
            "routine": {
                "morning": morning_steps,
                "evening": evening_steps,
                "weekly":  ["Exfoliant mask (1–2×/week)", "Sheet mask for hydration"],
            },
            "skin_score":    inp.skin_analysis.get("texture_score"),
            "acne_severity": inp.acne_data.get("severity", "none"),
            "dark_circles":  inp.skin_analysis.get("dark_circles_detected", False),
        }

    def _color_profile_section(self, inp: StyleDNAInput) -> dict:
        season = (inp.color_season or "spring").replace("_", " ").title()
        family = inp.color_season_family or "spring"
        return {
            "season":        season,
            "season_family": family,
            "description":   self._season_description(family),
            "palette": {
                "best":     inp.palette_best[:8],
                "neutrals": inp.palette_neutrals[:6],
                "accents":  inp.palette_accents[:4],
            },
            "dos": self._color_dos(family),
            "donts": self._color_donts(family),
            "makeup_guide":  inp.makeup_recs,
            "metal_tones":   self._season_metals(family),
            "wardrobe_neutrals": self._season_neutrals(family),
        }

    def _fashion_profile(self, inp: StyleDNAInput) -> dict:
        body_guide = _BODY_SHAPE_GUIDE.get(inp.body_shape or "rectangle", {})
        dims       = inp.style_dimensions or {}

        return {
            "primary_archetype":   inp.primary_archetype,
            "secondary_archetype": inp.secondary_archetype,
            "archetype_description": self._archetype_description(inp.primary_archetype),
            "body_shape":          inp.body_shape,
            "body_guide":          body_guide,
            "capsule_wardrobe":    self._capsule_wardrobe(inp),
            "signature_pieces":    self._signature_pieces(inp),
            "style_axes": {
                "classic_vs_avantgarde": round(dims.get("style_axis", 0.5), 2),
                "understated_vs_bold":   round(dims.get("energy_axis", 0.5), 2),
                "relaxed_vs_tailored":   round(dims.get("structure_axis", 0.5), 2),
                "minimalist_vs_romantic":round(dims.get("romance_axis", 0.5), 2),
            },
            "occasion_split": inp.occasion_mix,
            "budget_tier":    inp.budget_tier,
            "lifestyle_tags": inp.lifestyle_tags,
        }

    def _fragrance_profile_section(self, inp: StyleDNAInput) -> dict:
        primary_family = (inp.fragrance_family or ["fresh"])[0].lower() if inp.fragrance_family else "fresh"
        occ_guide = _FRAGRANCE_OCCASIONS.get(primary_family, _FRAGRANCE_OCCASIONS["fresh"])

        return {
            "families":          inp.fragrance_family,
            "preferred_notes":   inp.preferred_notes,
            "avoided_notes":     inp.avoided_notes,
            "intensity":         inp.intensity_pref,
            "longevity":         inp.longevity_pref,
            "personality":       self._fragrance_personality(inp),
            "occasion_guide":    occ_guide,
            "layering_tip":      self._fragrance_layering_tip(primary_family),
            "wardrobe_size":     "Start with 3 fragrances: daily, work, evening",
        }

    def _hairstyle_profile(self, inp: StyleDNAInput) -> dict:
        face_guide  = _FACE_SHAPE_HAIR.get(inp.face_shape or "oval", _FACE_SHAPE_HAIR["oval"])
        hair_type   = inp.hair_type or "straight"
        hair_color  = inp.hair_color or "brown"
        skin_tone   = inp.skin_tone or "medium"
        undertone   = inp.undertone or "neutral"

        return {
            "face_shape":          inp.face_shape,
            "hair_type":           hair_type,
            "current_color":       hair_color,
            "recommended_styles":  face_guide.get("recommend", []),
            "avoid_styles":        face_guide.get("avoid", []),
            "face_shape_summary":  face_guide.get("summary", ""),
            "styling_tip":         face_guide.get("tip", ""),
            "color_recommendations": self._hair_color_recs(skin_tone, undertone, inp.color_season_family),
            "care_routine":        self._hair_care_routine(hair_type),
            "symmetry_score":      inp.symmetry_score,
        }

    def _recommendations(self, inp: StyleDNAInput) -> dict:
        return {
            "skincare":    self._skincare_picks(inp),
            "makeup":      self._makeup_picks(inp),
            "fragrance":   self._fragrance_picks(inp),
            "fashion":     self._fashion_picks(inp),
            "haircare":    self._haircare_picks(inp),
            "accessories": self._accessory_picks(inp),
        }

    def _personality_section(self, inp: StyleDNAInput) -> dict:
        dims = inp.style_dimensions or {}
        return {
            "primary_archetype":     inp.primary_archetype,
            "secondary_archetype":   inp.secondary_archetype,
            "archetype_blend":       f"{inp.primary_archetype} with {inp.secondary_archetype} tendencies",
            "dimensions":            dims,
            "lifestyle_summary":     self._lifestyle_summary(inp),
            "shopping_persona":      self._shopping_persona(inp),
            "beauty_philosophy":     self._beauty_philosophy(inp),
        }

    def _occasion_guide(self, inp: StyleDNAInput) -> dict:
        archetype = inp.primary_archetype or "The Classic"
        season    = inp.color_season_family or "spring"
        return {
            "work": {
                "outfit_formula":   self._work_formula(archetype, inp),
                "colour_palette":   self._occasion_palette("work", season),
                "beauty_look":      self._work_beauty(inp),
                "fragrance":        _FRAGRANCE_OCCASIONS.get((inp.fragrance_family or ["fresh"])[0], {}).get("work", "clean, professional fragrance"),
            },
            "casual": {
                "outfit_formula":   self._casual_formula(archetype, inp),
                "colour_palette":   self._occasion_palette("casual", season),
                "beauty_look":      "5-minute no-makeup makeup look",
                "fragrance":        _FRAGRANCE_OCCASIONS.get((inp.fragrance_family or ["fresh"])[0], {}).get("casual", "light, fresh fragrance"),
            },
            "evening": {
                "outfit_formula":   self._evening_formula(archetype, inp),
                "colour_palette":   self._occasion_palette("evening", season),
                "beauty_look":      self._evening_beauty(inp),
                "fragrance":        _FRAGRANCE_OCCASIONS.get((inp.fragrance_family or ["fresh"])[0], {}).get("evening", "rich, distinctive fragrance"),
            },
            "special": {
                "outfit_formula":   "Your season's hero colours in your most flattering silhouette",
                "beauty_look":      "Full glam — your most confident, complete look",
                "fragrance":        "Your most distinctive, memorable scent",
            },
        }

    # ── Private prose helpers ──────────────────────────────────────────────────

    def _beauty_summary(self, inp: StyleDNAInput) -> str:
        dims    = inp.style_dimensions or {}
        energy  = dims.get("energy_axis", 0.5)
        romance = dims.get("romance_axis", 0.5)
        if energy > 0.7:
            return "bold, expressive choices that turn heads"
        if romance > 0.7:
            return "soft, romantic details that feel inherently feminine"
        if dims.get("structure_axis", 0.5) > 0.7:
            return "precision and polish — always intentional, never accidental"
        return "an instinctive sense of what works beautifully on you"

    def _beauty_strengths(self, inp: StyleDNAInput) -> list[str]:
        strengths = []
        if inp.symmetry_score and inp.symmetry_score > 0.85:
            strengths.append("Beautifully symmetrical facial features")
        face = inp.face_shape
        if face:
            strengths.append(f"{face.title()} face shape — one of the most versatile for hairstyling")
        if inp.skin_tone:
            strengths.append(f"Your {inp.skin_tone} {inp.undertone or 'neutral'}-toned complexion glows in {inp.color_season or 'your'} palette")
        return strengths or ["Your unique features are your greatest beauty asset"]

    def _signature_look(self, inp: StyleDNAInput) -> str:
        archetype = inp.primary_archetype or "The Classic"
        makeup_recs = inp.makeup_recs or {}
        lips = (makeup_recs.get("lipstick", [{}]) or [{}])[0].get("shade", "your signature lip colour") if isinstance(makeup_recs.get("lipstick"), list) else "a perfect lip"
        looks = {
            "The Classic":      f"A polished cat-eye, fresh skin, and {lips}",
            "The Romantic":     "Flushed cheeks, glossy lips, and luminous skin",
            "The Edgy":         "Graphic liner, bold brows, and a statement lip",
            "The Minimalist":   "Skin-first, brow-focused, clean flush — barely there but perfect",
            "The Glamorous":    "Full glam: sculpted face, lashes, and a bold colour moment",
            "The Bohemian":     "Bronzed skin, sun-kissed freckles, and earthy tones",
            "The Creative":     "Unexpected colour — a vivid lid, artistic liner, or sculptural brow",
            "The Sophisticated":"Monochromatic tones, immaculate skin, understated perfection",
            "The Athletic":     "Skincare-forward, SPF flush, mascara, and a natural finish",
            "The Preppy":       "Classic red or berry lip, clean skin, and groomed brows",
        }
        return looks.get(archetype, "Your most confident, authentic look")

    def _power_features(self, inp: StyleDNAInput) -> list[str]:
        features = []
        ff = inp.facial_features or {}
        if ff.get("eyes"):
            features.append(f"{str(ff.get('eyes', '')).title()} eyes — enhance with liner and mascara")
        if ff.get("cheekbones") in ("high", "defined"):
            features.append("High cheekbones — emphasise with highlighter and blush placement")
        if inp.face_shape == "heart":
            features.append("Heart-shaped face — your lips are naturally stunning")
        return features or ["Your skin is your strongest canvas — invest in it first"]

    def _recommended_actives(self, concerns: list[str], skin_type: str) -> list[str]:
        actives = []
        if "acne" in concerns: actives += ["Salicylic Acid 2%", "Niacinamide 10%", "Tea Tree (spot treatment)"]
        if "hyperpigmentation" in concerns: actives += ["Vitamin C 15–20%", "Alpha Arbutin 2%", "Tranexamic Acid"]
        if "fine_lines" in concerns: actives += ["Retinol 0.025% (start)", "Peptide complex", "Vitamin C"]
        if "dryness" in concerns or skin_type == "dry": actives += ["Hyaluronic Acid", "Ceramides", "Squalane"]
        if "redness" in concerns: actives += ["Centella Asiatica", "Azelaic Acid 10%", "Green Tea Extract"]
        if not actives: actives = ["Niacinamide (universal)", "Hyaluronic Acid", "SPF 50+"]
        return list(dict.fromkeys(actives))  # deduplicate preserving order

    def _season_description(self, family: str) -> str:
        descs = {
            "spring": "Warm, luminous, and clear — you radiate golden warmth.",
            "summer": "Cool, soft, and delicate — you shine in dusty, muted tones.",
            "autumn": "Deep, warm, and earthy — rich tones bring you alive.",
            "winter": "Cool, clear, and high-contrast — you command attention in vivid hues.",
        }
        return descs.get(family, "You have a beautifully distinctive colour palette.")

    def _color_dos(self, family: str) -> list[str]:
        dos = {
            "spring":  ["Warm whites and creams", "Golden yellows and peaches", "Coral reds", "Warm greens"],
            "summer":  ["Soft greys and lavenders", "Dusty rose and mauve", "Cool blues", "Soft whites"],
            "autumn":  ["Rust, terracotta, and mustard", "Olive and warm greens", "Deep burgundy", "Camel and tan"],
            "winter":  ["True black and white", "Cool jewel tones", "Icy pastels", "Electric vivids"],
        }
        return dos.get(family, ["Your personal palette shades"])

    def _color_donts(self, family: str) -> list[str]:
        donts = {
            "spring":  ["Cold grey", "Icy blues", "True black (go for soft navy or brown)"],
            "summer":  ["Orange and hot coral", "Very warm yellows", "True black (go for charcoal)"],
            "autumn":  ["Icy pastels", "Cool pinks", "True black (go for deep aubergine or chocolate)"],
            "winter":  ["Warm, muted earth tones", "Orange and golden yellow", "Warm browns"],
        }
        return donts.get(family, ["Shades from opposing season families"])

    def _season_metals(self, family: str) -> list[str]:
        metals = {
            "spring":  ["Yellow gold", "Rose gold", "Warm bronze"],
            "summer":  ["Silver", "White gold", "Platinum", "Rose gold"],
            "autumn":  ["Yellow gold", "Bronze", "Copper", "Antique gold"],
            "winter":  ["Silver", "Platinum", "White gold", "Polished steel"],
        }
        return metals.get(family, ["Gold or silver depending on undertone"])

    def _season_neutrals(self, family: str) -> list[str]:
        neutrals = {
            "spring":  ["Ivory", "Warm white", "Camel", "Warm sand"],
            "summer":  ["Soft grey", "Greige", "Cool taupe", "Dusty blush"],
            "autumn":  ["Camel", "Dark brown", "Warm taupe", "Olive"],
            "winter":  ["True black", "Pure white", "Cool charcoal", "Navy"],
        }
        return neutrals.get(family, ["Neutral tones from your season"])

    def _archetype_description(self, archetype: str | None) -> str:
        descs = {
            "The Classic":      "You believe true style transcends trends. Your wardrobe is a curated collection of timeless pieces that work harder the older they get.",
            "The Minimalist":   "Less is your greatest luxury. You dress with intention and precision — every piece is considered and purposeful.",
            "The Romantic":     "Beauty moves you. You're drawn to softness, femininity, and the kind of dressing that feels like a love letter to yourself.",
            "The Bohemian":     "Free-spirited and instinctive, you dress as if the world is your runway and every setting is your backdrop.",
            "The Edgy":         "You use fashion as armor and art simultaneously. Rules are optional. Originality is non-negotiable.",
            "The Athletic":     "Functionality is your foundation, but you've mastered the art of elevating activewear into a lifestyle aesthetic.",
            "The Glamorous":    "Life is a stage and you dress accordingly. You believe in the transformative power of a fully realized look.",
            "The Preppy":       "Polished, put-together, and proudly classic. You understand that being well-dressed is a form of respect — for yourself and others.",
            "The Creative":     "Your wardrobe is your sketchbook. Colour, texture, proportion — you experiment fearlessly and the results are always interesting.",
            "The Sophisticated":"There's an innate authority to the way you dress. Understated but unmistakably intentional.",
            "The Casual":       "You've mastered the art of effortless — making the least effort look like the most thought.",
            "The Eclectic":     "You defy categorisation and that's exactly as it should be. Your style tells a story only you could write.",
        }
        return descs.get(archetype or "", "Your style is entirely your own — and that's your greatest strength.")

    def _capsule_wardrobe(self, inp: StyleDNAInput) -> list[dict]:
        archetype = inp.primary_archetype or "The Classic"
        capsules = {
            "The Classic":    [{"item":"Tailored wool blazer","note":"In your season's navy or camel"},{"item":"White button-down","note":"Crisp, well-fitted"},{"item":"Straight-leg dark denim","note":"The ultimate foundation"},{"item":"Camel trench coat","note":"Your signature outerwear"},{"item":"Simple A-line midi skirt","note":"Versatile and timeless"},{"item":"Black pump","note":"The power shoe"}],
            "The Minimalist": [{"item":"Oversized cashmere jumper","note":"In ivory or grey"},{"item":"High-waist wide-leg trousers","note":"In black or sand"},{"item":"Structured white shirt","note":"Clean lines, perfect fit"},{"item":"Simple slip dress","note":"In your season's neutral"},{"item":"Sleek coat","note":"Architectural cut"},{"item":"Clean leather loafer","note":"Italian-inspired simplicity"}],
            "The Romantic":   [{"item":"Floral midi dress","note":"In your season's palette"},{"item":"Silk blouse","note":"Feminine and luxurious"},{"item":"Wrap dress","note":"Universally flattering"},{"item":"Lace or embroidered detail piece","note":"The texture maker"},{"item":"Kitten heels","note":"Elegantly romantic"},{"item":"Structured mini bag","note":"In a soft, season-appropriate hue"}],
            "The Edgy":       [{"item":"Perfect black leather jacket","note":"This is non-negotiable"},{"item":"Black straight-leg trousers","note":"The foundation"},{"item":"Graphic or band tee","note":"Your personality piece"},{"item":"Combat or ankle boot","note":"The statement shoe"},{"item":"Oversized blazer","note":"For contrast and structure"},{"item":"One unexpected bag","note":"Architectural or unusual shape"}],
        }
        default = [
            {"item":"5 quality basics in your neutrals","note":"Build from the foundation"},
            {"item":"3 statement pieces in your best colours","note":"The conversation starters"},
            {"item":"2 occasion pieces","note":"For when you need to show up fully"},
        ]
        return capsules.get(archetype, default)

    def _signature_pieces(self, inp: StyleDNAInput) -> list[str]:
        archetype = inp.primary_archetype or "The Classic"
        pieces = {
            "The Classic":    ["A perfectly-cut blazer", "Quality leather loafers", "Gold jewellery"],
            "The Minimalist": ["An architectural bag", "Monochrome outfits", "Clean white sneakers"],
            "The Romantic":   ["A silk slip dress", "Delicate layered necklaces", "Ballet flats"],
            "The Edgy":       ["Leather jacket", "Statement boots", "Graphic elements"],
            "The Glamorous":  ["A bold evening piece", "Statement jewellery", "A luxury bag"],
        }
        return pieces.get(archetype, ["Your season's hero colour", "A quality signature bag", "Classic tailored separates"])

    def _fragrance_personality(self, inp: StyleDNAInput) -> str:
        families = inp.fragrance_family or ["fresh"]
        primary  = families[0].lower() if families else "fresh"
        personalites = {
            "floral":   "You are a romantic who finds beauty in bloom. Florals don't wear you — you wear them.",
            "woody":    "Grounded and confident, you're drawn to depth and longevity over fleeting impressions.",
            "oriental": "Sensual and memorable, your fragrance leaves a room changed after you've been in it.",
            "fresh":    "Clean, confident, and effortlessly present — you smell like yourself, at your very best.",
            "citrus":   "Bright, optimistic, and energising — your scent signals possibility.",
            "chypre":   "Sophisticated and quietly complex — a fragrance for someone who knows exactly who they are.",
            "gourmand": "Warm, inviting, and irresistibly comforting — you make everyone feel at ease.",
        }
        return personalites.get(primary, "Your fragrance identity is uniquely your own.")

    def _fragrance_layering_tip(self, family: str) -> str:
        tips = {
            "floral":   "Layer a rose or jasmine EDP over a musks body lotion for all-day radiance.",
            "woody":    "Apply to pulse points — wrists, neck, behind ears. Woody scents deepen on skin over time.",
            "oriental": "Less is more with oriental fragrances. One spray on the neck is enough to fill a room.",
            "fresh":    "Reapply mid-day for freshness. Layer with an unscented hair mist for lingering presence.",
            "citrus":   "Citrus fades fastest — layer over a vanilla or musk base for longevity.",
        }
        return tips.get(family, "Apply to pulse points immediately after moisturising for maximum longevity.")

    def _hair_color_recs(self, skin_tone: str, undertone: str, season_family: str | None) -> list[str]:
        if undertone == "warm":
            return ["Rich golden brown", "Warm auburn", "Honey balayage", "Caramel highlights"]
        if undertone == "cool":
            return ["Ash brown", "Cool espresso", "Platinum highlights", "Blue-black"]
        # neutral
        return ["Chocolate brown", "Soft balayage", "Natural-looking highlights in your season's tones"]

    def _hair_care_routine(self, hair_type: str) -> dict:
        routines = {
            "straight":    {"wash": "2–3×/week", "treatments": ["Lightweight smoothing serum", "Weekly protein mask"], "styling": "Blow-dry with a round brush for movement"},
            "wavy":        {"wash": "2–3×/week", "treatments": ["Curl-enhancing cream", "Weekly hydration mask"], "styling": "Diffuse on low heat; scrunch out the crunch"},
            "curly":       {"wash": "1–2×/week", "treatments": ["Deep conditioning mask weekly", "Leave-in conditioner daily"], "styling": "Rake in cream while soaking wet; diffuse or air-dry"},
            "coily":       {"wash": "1×/week", "treatments": ["Co-wash between washes", "Sealed moisture with oil or butter"], "styling": "LOC (Liquid, Oil, Cream) method for maximum moisture"},
        }
        return routines.get(hair_type, routines["straight"])

    def _skincare_picks(self, inp: StyleDNAInput) -> list[dict]:
        concerns = inp.skin_concerns or []
        picks = []
        if "acne" in concerns:
            picks.append({"category": "Treatment", "pick": "BHA exfoliant (Salicylic Acid 2%)", "why": "Clears pores, reduces breakouts"})
        if "hyperpigmentation" in concerns:
            picks.append({"category": "Brightening", "pick": "Vitamin C serum 15%+", "why": "Fades dark spots, brightens complexion"})
        picks.append({"category": "Hydration", "pick": "Hyaluronic Acid serum", "why": "Universal — works on every skin type"})
        picks.append({"category": "Protection", "pick": f"SPF 50+ suited to {inp.skin_type or 'combination'} skin", "why": "Your most anti-aging purchase"})
        return picks[:5]

    def _makeup_picks(self, inp: StyleDNAInput) -> list[dict]:
        skin_tone = inp.skin_tone or "medium"
        undertone  = inp.undertone or "neutral"
        return [
            {"category": "Foundation", "pick": f"Skin-matching {undertone}-toned formula for {skin_tone} skin", "finish": "Satin or luminous"},
            {"category": "Blush",      "pick": inp.makeup_recs.get("blush_shades", [{"name":"Peach or rose"}])[0].get("name", "Your season's blush") if isinstance(inp.makeup_recs.get("blush_shades"), list) else "Season-matched blush"},
            {"category": "Lip",        "pick": "A lip liner + matching lip balm for your everyday look"},
            {"category": "Eye",        "pick": f"{'Brown or charcoal liner' if inp.undertone == 'warm' else 'Black or grey liner'} + mascara"},
        ]

    def _fragrance_picks(self, inp: StyleDNAInput) -> list[dict]:
        family = (inp.fragrance_family or ["fresh"])[0].lower()
        picks_map = {
            "floral":   [{"pick": "A rose-forward EDP", "note": "Sophisticated and timeless"}, {"pick": "A jasmine + musk blend", "note": "Sensual for evenings"}],
            "woody":    [{"pick": "Sandalwood + cedar EDP", "note": "Grounding and warm"}, {"pick": "Oud + rose", "note": "Luxury statement scent"}],
            "oriental": [{"pick": "Amber + vanilla EDP", "note": "Enveloping and long-lasting"}, {"pick": "Oriental + spice blend", "note": "Evening drama"}],
            "fresh":    [{"pick": "Citrus + white musk EDP", "note": "Clean, everyday confidence"}, {"pick": "Aquatic + cedar", "note": "Professional presence"}],
            "citrus":   [{"pick": "Bergamot + green notes", "note": "Energising and bright"}, {"pick": "Lemon + vetiver", "note": "Unexpected depth"}],
        }
        return picks_map.get(family, [{"pick": "A fragrance from your preferred family", "note": "Choose what feels like you"}])

    def _fashion_picks(self, inp: StyleDNAInput) -> list[dict]:
        return [
            {"item": "Hero piece", "description": f"One statement item in {inp.color_season_family or 'your season'}'s best colour"},
            {"item": "Foundation piece", "description": "A perfectly-fitting pair of trousers or jeans in your best neutral"},
            {"item": "Layer", "description": f"A quality {inp.primary_archetype or 'signature'}-style blazer or coat"},
        ]

    def _haircare_picks(self, inp: StyleDNAInput) -> list[dict]:
        hair_type = inp.hair_type or "straight"
        picks = {
            "straight": [{"pick": "Lightweight smoothing serum", "why": "Frizz control without weight"}, {"pick": "Protein-rich mask", "why": "Strengthens and adds shine"}],
            "wavy":     [{"pick": "Curl-enhancing cream", "why": "Defines wave pattern"}, {"pick": "Hydrating mask", "why": "Prevents frizz"}],
            "curly":    [{"pick": "Rich leave-in conditioner", "why": "Daily moisture lock"}, {"pick": "Deep conditioning mask", "why": "Weekly repair treatment"}],
            "coily":    [{"pick": "Shea butter sealant", "why": "Locks in moisture for coily patterns"}, {"pick": "Lightweight co-wash", "why": "Cleanses without stripping"}],
        }
        return picks.get(hair_type, picks["straight"])

    def _accessory_picks(self, inp: StyleDNAInput) -> list[dict]:
        metals = self._season_metals(inp.color_season_family or "spring")[:2]
        return [
            {"pick": f"Jewellery in {metals[0] if metals else 'gold'}", "why": "Your season's most flattering metal tone"},
            {"pick": "A quality leather bag in a neutral from your season", "why": "The investment that lasts"},
        ]

    def _lifestyle_summary(self, inp: StyleDNAInput) -> str:
        tags = inp.lifestyle_tags or []
        parts = []
        if "active" in tags:
            parts.append("physically active")
        if "sustainable" in tags:
            parts.append("sustainability-conscious")
        occ = inp.occasion_mix or {}
        dominant = max(occ, key=lambda k: occ.get(k, 0), default="casual") if occ else "casual"
        parts.append(f"{dominant}-lifestyle-focused")
        return f"Your lifestyle is {', '.join(parts)} — and your style choices reflect exactly that."

    def _shopping_persona(self, inp: StyleDNAInput) -> str:
        tier = inp.budget_tier or "mid"
        personas = {
            "budget":   "Value-first shopper — you find the best quality at the best price.",
            "low_mid":  "Smart shopper — selective about where you spend.",
            "mid":      "Quality-conscious — you invest in pieces that earn their place.",
            "mid_high": "Selective investor — you choose fewer, better pieces.",
            "luxury":   "Luxury curator — your wardrobe is an investment portfolio.",
        }
        return personas.get(tier, "You have a clear sense of where to invest and where to save.")

    def _beauty_philosophy(self, inp: StyleDNAInput) -> str:
        dims = inp.style_dimensions or {}
        if dims.get("experimentalism", 0.5) > 0.7:
            return "Beauty is your creative outlet — a space for daily self-expression."
        if dims.get("practicality", 0.5) > 0.7:
            return "Beauty serves your life — efficient, effective, and purposeful."
        return "Beauty is part of your identity — a daily ritual that grounds you."

    def _work_formula(self, archetype: str, inp: StyleDNAInput) -> str:
        formulas = {
            "The Classic":      "Tailored trousers + silk blouse + structured blazer",
            "The Minimalist":   "Clean wide-leg trousers + fitted knit or crisp white shirt",
            "The Sophisticated":"Monochromatic look with one quality accessory",
            "The Creative":     "Interesting separates with a colour or texture pop",
            "The Romantic":     "A refined midi dress or feminine blouse + tailored trousers",
        }
        return formulas.get(archetype, "Polished separates in your best neutral, elevated with one hero piece")

    def _casual_formula(self, archetype: str, inp: StyleDNAInput) -> str:
        return "Well-fitting jeans or straight-leg trousers + a quality knit or t-shirt + your signature footwear"

    def _evening_formula(self, archetype: str, inp: StyleDNAInput) -> str:
        formulas = {
            "The Glamorous":  "Your season's showstopper dress, full glam, statement jewellery",
            "The Classic":    "Elegant midi or cocktail dress in a deep hue from your palette",
            "The Edgy":       "Black tailored separates + the leather jacket + bold lip",
            "The Romantic":   "Silk slip or flowy midi in your season's softest evening shade",
            "The Minimalist": "Clean, sculptural silhouette in black or your season's deep neutral",
        }
        return formulas.get(archetype, "Your most confident look in your season's evening palette")

    def _occasion_palette(self, occasion: str, season_family: str) -> list[str]:
        palettes = {
            "work":    {"spring":["Ivory","Warm navy","Camel"], "summer":["Greige","Dusty blue","Soft grey"], "autumn":["Camel","Chocolate","Forest green"], "winter":["Black","Navy","White"]},
            "casual":  {"spring":["Peach","Warm white","Coral"], "summer":["Lavender","Soft pink","Light blue"], "autumn":["Rust","Mustard","Olive"], "winter":["Cobalt","Crimson","Icy grey"]},
            "evening": {"spring":["Gold","Deep coral","Warm terracotta"], "summer":["Deep mauve","Berry","Midnight blue"], "autumn":["Burgundy","Deep rust","Gold"], "winter":["Black","Electric blue","Pure white"]},
        }
        return palettes.get(occasion, {}).get(season_family, ["Your season's palette shades"])

    def _work_beauty(self, inp: StyleDNAInput) -> str:
        return f"Flawless base, groomed brows, neutral lip in your {inp.undertone or 'warm'} undertone, mascara"

    def _evening_beauty(self, inp: StyleDNAInput) -> str:
        archetype = inp.primary_archetype or "The Classic"
        if archetype in ("The Edgy", "The Creative"):
            return "Graphic liner or bold eyeshadow, defined brow, and a clean skin moment"
        if archetype in ("The Glamorous",):
            return "Full face — sculpted cheeks, dramatic lash, and a statement lip in your season's bold"
        return "Enhanced skin, statement lip in your season's best shade, or a beautiful eye moment"

    @staticmethod
    def _compute_hash(inp: StyleDNAInput) -> str:
        key_data = {
            "skin_tone": inp.skin_tone,
            "undertone": inp.undertone,
            "skin_concerns": sorted(inp.skin_concerns or []),
            "color_season": inp.color_season,
            "primary_archetype": inp.primary_archetype,
            "fragrance_family": sorted(inp.fragrance_family or []),
        }
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:16]
