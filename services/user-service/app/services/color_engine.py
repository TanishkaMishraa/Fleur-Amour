"""
AuraFit — Color Intelligence Engine (Stage 5).

Implements the full 12-season Seasonal Color Analysis system derived from
the Munsell-based color theory tradition (Carole Jackson, Bernice Kentner,
extended by Sci/ART 12-tone system).

Classification inputs (all from the facial scan pipeline):
  - skin_tone   : fair | light | medium | olive | tan | deep
  - undertone   : cool | warm | neutral
  - ita_angle   : ITA° value (Individual Typology Angle from CIELAB)
  - fitzpatrick : 1–6 phototype
  - hair_color_hex: dominant hair hex
  - eye_color   : string description

Algorithm:
  1. Value score (light vs deep) from ITA° and Fitzpatrick
  2. Chroma score (muted vs clear) from colour saturation of skin hex
  3. Undertone routing (cool vs warm vs neutral)
  4. 12-season classification via decision matrix
  5. Personal palette generation per season
  6. All recommendation sets generated deterministically (no ML needed —
     rule tables are clinically validated color theory)
"""
from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass
from typing import Any

ENGINE_VERSION = "1.0.0"


# ══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ColorEntry:
    hex: str
    name: str
    category: str      # neutral | accent | base | statement
    season_fit: str = "best"


@dataclass
class SeasonResult:
    season: str
    confidence: float
    description: str
    key_characteristics: list[str]
    celebrity_examples: list[str]
    season_family: str
    contrast_level: str
    chroma_level: str
    value_level: str


@dataclass
class FullColorProfile:
    season: SeasonResult
    palette_best: list[ColorEntry]
    palette_neutrals: list[ColorEntry]
    palette_accents: list[ColorEntry]
    palette_avoid: list[ColorEntry]
    hero_color: ColorEntry
    makeup: dict
    lipstick: list[dict]
    hair_color: list[dict]
    outfits: dict
    jewelry: dict


# ══════════════════════════════════════════════════════════════════════════════
# SEASON PALETTES  (hex, name, category)
# ══════════════════════════════════════════════════════════════════════════════

_SEASON_PALETTES: dict[str, dict[str, list[tuple[str, str, str]]]] = {

    # ── SPRING family (warm + clear/light) ────────────────────────────────
    "true_spring": {
        "best":     [("#F4A460", "Sandy Brown", "base"), ("#FFA500", "Warm Orange", "accent"),
                     ("#FFD700", "Golden Yellow", "accent"), ("#90EE90", "Light Green", "base"),
                     ("#87CEEB", "Sky Blue", "base"), ("#FF7F50", "Coral", "statement"),
                     ("#FFDAB9", "Peach Puff", "neutral"), ("#DEB887", "Burlywood", "neutral"),
                     ("#F0E68C", "Khaki", "base"), ("#98FB98", "Pale Green", "neutral")],
        "avoid":    [("#808080", "Grey", "base"), ("#000000", "Black", "base"),
                     ("#800080", "Purple", "base"), ("#4B0082", "Indigo", "base")],
        "neutrals": [("#FFDAB9", "Peach Puff", "neutral"), ("#DEB887", "Burlywood", "neutral"),
                     ("#D2B48C", "Tan", "neutral"), ("#F5DEB3", "Wheat", "neutral")],
        "accents":  [("#FF4500", "Orange Red", "accent"), ("#FFD700", "Gold", "accent"),
                     ("#32CD32", "Lime Green", "accent")],
    },
    "light_spring": {
        "best":     [("#FFB6C1", "Light Pink", "base"), ("#FFDAB9", "Peach", "base"),
                     ("#FFFACD", "Lemon Chiffon", "base"), ("#E0FFFF", "Light Cyan", "base"),
                     ("#F0FFF0", "Honeydew", "base"), ("#FFF0F5", "Lavender Blush", "neutral"),
                     ("#FAFAD2", "Light Goldenrod", "neutral"), ("#FFE4E1", "Misty Rose", "base"),
                     ("#AFEEEE", "Pale Turquoise", "accent"), ("#98FB98", "Pale Green", "accent")],
        "avoid":    [("#000000", "Black", "base"), ("#8B0000", "Dark Red", "base"),
                     ("#191970", "Midnight Blue", "base"), ("#2F4F4F", "Dark Slate", "base")],
        "neutrals": [("#FFF5EE", "Seashell", "neutral"), ("#FAEBD7", "Antique White", "neutral"),
                     ("#FFF8DC", "Cornsilk", "neutral"), ("#FFFAF0", "Floral White", "neutral")],
        "accents":  [("#FFB6C1", "Light Pink", "accent"), ("#AFEEEE", "Pale Turquoise", "accent"),
                     ("#98FB98", "Pale Green", "accent")],
    },
    "bright_spring": {
        "best":     [("#FF0000", "True Red", "statement"), ("#FF4500", "Orange Red", "accent"),
                     ("#00FF7F", "Spring Green", "accent"), ("#00BFFF", "Deep Sky Blue", "accent"),
                     ("#FF69B4", "Hot Pink", "statement"), ("#FFD700", "Gold", "accent"),
                     ("#FFFFFF", "Crisp White", "neutral"), ("#FFA500", "Orange", "accent"),
                     ("#32CD32", "Lime Green", "accent"), ("#1E90FF", "Dodger Blue", "base")],
        "avoid":    [("#808080", "Grey", "base"), ("#A0A0A0", "Medium Grey", "base"),
                     ("#C0C0A0", "Muted Khaki", "base")],
        "neutrals": [("#FFFFFF", "White", "neutral"), ("#F5F5F5", "White Smoke", "neutral"),
                     ("#FFFAF0", "Floral White", "neutral")],
        "accents":  [("#FF0000", "True Red", "accent"), ("#00FF7F", "Spring Green", "accent"),
                     ("#FF69B4", "Hot Pink", "accent")],
    },

    # ── SUMMER family (cool + muted/light) ───────────────────────────────
    "true_summer": {
        "best":     [("#DDA0DD", "Plum", "base"), ("#9370DB", "Medium Purple", "accent"),
                     ("#6495ED", "Cornflower Blue", "base"), ("#20B2AA", "Light Sea Green", "base"),
                     ("#BC8F8F", "Rosy Brown", "neutral"), ("#C8A2C8", "Lilac", "base"),
                     ("#B0C4DE", "Light Steel Blue", "neutral"), ("#DB7093", "Pale Violet Red", "accent"),
                     ("#8FBC8F", "Dark Sea Green", "base"), ("#708090", "Slate Grey", "neutral")],
        "avoid":    [("#FF4500", "Orange Red", "base"), ("#FFD700", "Gold", "base"),
                     ("#8B4513", "Saddle Brown", "base"), ("#FF6347", "Tomato", "base")],
        "neutrals": [("#D3D3D3", "Light Grey", "neutral"), ("#C0C0C0", "Silver", "neutral"),
                     ("#A9A9A9", "Dark Grey", "neutral"), ("#DCDCDC", "Gainsboro", "neutral")],
        "accents":  [("#9370DB", "Medium Purple", "accent"), ("#DB7093", "Pale Violet Red", "accent"),
                     ("#20B2AA", "Teal", "accent")],
    },
    "light_summer": {
        "best":     [("#E6E6FA", "Lavender", "base"), ("#FFB6C1", "Light Pink", "base"),
                     ("#B0E0E6", "Powder Blue", "base"), ("#D8BFD8", "Thistle", "base"),
                     ("#F0F8FF", "Alice Blue", "neutral"), ("#FFF0F5", "Lavender Blush", "neutral"),
                     ("#E0FFFF", "Light Cyan", "base"), ("#FFC0CB", "Pink", "accent"),
                     ("#C8C8C8", "Silver Mist", "neutral"), ("#B8D8D8", "Powder Teal", "base")],
        "avoid":    [("#FF4500", "Orange", "base"), ("#8B0000", "Dark Red", "base"),
                     ("#000080", "Navy", "base"), ("#8B4513", "Brown", "base")],
        "neutrals": [("#F5F5F5", "White Smoke", "neutral"), ("#E8E8E8", "Pale Grey", "neutral"),
                     ("#D3D3D3", "Light Grey", "neutral")],
        "accents":  [("#FFB6C1", "Soft Pink", "accent"), ("#B0E0E6", "Powder Blue", "accent"),
                     ("#D8BFD8", "Mauve", "accent")],
    },
    "soft_summer": {
        "best":     [("#9F8B77", "Warm Greige", "neutral"), ("#BFA89E", "Dusty Rose Beige", "neutral"),
                     ("#8B9E8B", "Sage Green", "base"), ("#7B9BAB", "Muted Blue", "base"),
                     ("#A89BB4", "Soft Lavender", "base"), ("#B0956E", "Warm Taupe", "neutral"),
                     ("#829CAF", "Steel Blue Muted", "base"), ("#C4A882", "Warm Sand", "neutral"),
                     ("#8FAF8F", "Soft Moss", "base"), ("#9B8EA3", "Mauve Grey", "accent")],
        "avoid":    [("#FF0000", "True Red", "base"), ("#000000", "Black", "base"),
                     ("#FFFFFF", "Stark White", "base"), ("#FFD700", "Bright Gold", "base")],
        "neutrals": [("#C8BDB8", "Rosy Taupe", "neutral"), ("#B8B0A8", "Warm Linen", "neutral"),
                     ("#A0958C", "Greige", "neutral"), ("#D3C8C0", "Blush Linen", "neutral")],
        "accents":  [("#A89BB4", "Dusty Lavender", "accent"), ("#7B9BAB", "Muted Teal", "accent"),
                     ("#BF8F8F", "Dusty Rose", "accent")],
    },

    # ── AUTUMN family (warm + muted/deep) ────────────────────────────────
    "true_autumn": {
        "best":     [("#8B4513", "Saddle Brown", "base"), ("#A0522D", "Sienna", "base"),
                     ("#D2691E", "Chocolate", "base"), ("#CD853F", "Peru", "accent"),
                     ("#B8860B", "Dark Goldenrod", "accent"), ("#6B8E23", "Olive Drab", "base"),
                     ("#8FBC8F", "Dark Sea Green", "base"), ("#BC8F8F", "Rosy Brown", "neutral"),
                     ("#F4A460", "Sandy Brown", "neutral"), ("#DAA520", "Goldenrod", "accent")],
        "avoid":    [("#FF69B4", "Hot Pink", "base"), ("#00BFFF", "Sky Blue", "base"),
                     ("#9400D3", "Violet", "base"), ("#FFFFFF", "Stark White", "base")],
        "neutrals": [("#DEB887", "Burlywood", "neutral"), ("#D2B48C", "Tan", "neutral"),
                     ("#C4A882", "Warm Beige", "neutral"), ("#BCAAA4", "Warm Greige", "neutral")],
        "accents":  [("#FF6347", "Tomato", "accent"), ("#DAA520", "Goldenrod", "accent"),
                     ("#6B8E23", "Olive", "accent")],
    },
    "soft_autumn": {
        "best":     [("#C4A882", "Warm Sand", "neutral"), ("#BFA89E", "Dusty Blush", "neutral"),
                     ("#A09060", "Warm Khaki", "base"), ("#8B9060", "Olive Sage", "base"),
                     ("#B09070", "Caramel", "neutral"), ("#90A090", "Soft Sage", "base"),
                     ("#C0907A", "Terra Cotta Muted", "accent"), ("#A08070", "Warm Greige", "neutral"),
                     ("#789090", "Muted Teal", "base"), ("#A07850", "Warm Camel", "neutral")],
        "avoid":    [("#FF0000", "True Red", "base"), ("#0000FF", "Royal Blue", "base"),
                     ("#FF69B4", "Hot Pink", "base"), ("#000000", "Black", "base")],
        "neutrals": [("#C4B8A8", "Warm Linen", "neutral"), ("#B8A898", "Dusty Beige", "neutral"),
                     ("#A89880", "Warm Taupe", "neutral"), ("#D0C0A8", "Creamy Beige", "neutral")],
        "accents":  [("#C08060", "Rust Muted", "accent"), ("#8A9060", "Olive", "accent"),
                     ("#A07878", "Dusty Rose Warm", "accent")],
    },
    "deep_autumn": {
        "best":     [("#4A2C0A", "Deep Brown", "base"), ("#8B0000", "Dark Red", "statement"),
                     ("#006400", "Dark Green", "base"), ("#4B4B00", "Dark Olive", "base"),
                     ("#8B4513", "Rust", "accent"), ("#5C3317", "Dark Chocolate", "base"),
                     ("#800000", "Maroon", "statement"), ("#2E4B1E", "Forest Green", "base"),
                     ("#A0522D", "Deep Sienna", "accent"), ("#6B3A2A", "Brick", "accent")],
        "avoid":    [("#FFB6C1", "Light Pink", "base"), ("#E6E6FA", "Lavender", "base"),
                     ("#00BFFF", "Sky Blue", "base"), ("#FFFF00", "Yellow", "base")],
        "neutrals": [("#3C2A1E", "Dark Espresso", "neutral"), ("#5C4033", "Warm Dark", "neutral"),
                     ("#7A5C46", "Deep Camel", "neutral"), ("#6B4C3B", "Mocha", "neutral")],
        "accents":  [("#C04000", "Burnt Orange", "accent"), ("#8B0000", "Deep Red", "accent"),
                     ("#4A7C59", "Deep Teal Green", "accent")],
    },

    # ── WINTER family (cool + clear/deep) ────────────────────────────────
    "true_winter": {
        "best":     [("#000000", "Black", "base"), ("#FFFFFF", "Pure White", "neutral"),
                     ("#C0C0C0", "Silver", "neutral"), ("#000080", "Navy", "base"),
                     ("#8B0000", "Burgundy", "statement"), ("#800080", "Purple", "accent"),
                     ("#006400", "Forest Green", "base"), ("#DC143C", "Crimson", "statement"),
                     ("#4169E1", "Royal Blue", "accent"), ("#008B8B", "Dark Cyan", "base")],
        "avoid":    [("#FFA500", "Orange", "base"), ("#F4A460", "Sandy Brown", "base"),
                     ("#DEB887", "Burlywood", "base"), ("#F5DEB3", "Wheat", "base")],
        "neutrals": [("#FFFFFF", "Pure White", "neutral"), ("#000000", "Black", "neutral"),
                     ("#808080", "True Grey", "neutral"), ("#C0C0C0", "Silver", "neutral")],
        "accents":  [("#DC143C", "Crimson", "accent"), ("#800080", "Purple", "accent"),
                     ("#4169E1", "Royal Blue", "accent")],
    },
    "deep_winter": {
        "best":     [("#1C1C1C", "Off Black", "base"), ("#191970", "Midnight Blue", "base"),
                     ("#722F37", "Deep Wine", "statement"), ("#2C3E50", "Dark Slate", "base"),
                     ("#1A3A4A", "Deep Teal", "base"), ("#4A1A4A", "Deep Plum", "accent"),
                     ("#8B0000", "Dark Red", "statement"), ("#2E2E2E", "Charcoal", "neutral"),
                     ("#006633", "Deep Forest", "base"), ("#3A3A5A", "Deep Navy", "base")],
        "avoid":    [("#FFDAB9", "Peach", "base"), ("#FFD700", "Gold", "base"),
                     ("#FFA07A", "Light Salmon", "base"), ("#F0E68C", "Khaki", "base")],
        "neutrals": [("#2E2E2E", "Charcoal", "neutral"), ("#1C1C1C", "Near Black", "neutral"),
                     ("#4A4A4A", "Dark Grey", "neutral"), ("#3C3C3C", "Dark Charcoal", "neutral")],
        "accents":  [("#722F37", "Wine", "accent"), ("#4A1A4A", "Deep Purple", "accent"),
                     ("#1A3A4A", "Dark Teal", "accent")],
    },
    "bright_winter": {
        "best":     [("#000000", "Black", "base"), ("#FFFFFF", "Pure White", "neutral"),
                     ("#FF0000", "True Red", "statement"), ("#0000FF", "True Blue", "accent"),
                     ("#FF00FF", "Magenta", "statement"), ("#00FFFF", "Cyan", "accent"),
                     ("#7B68EE", "Medium Slate Blue", "accent"), ("#FF1493", "Deep Pink", "statement"),
                     ("#00FF00", "Lime", "accent"), ("#FFD700", "True Gold", "accent")],
        "avoid":    [("#F5DEB3", "Wheat", "base"), ("#DEB887", "Burlywood", "base"),
                     ("#C8A87A", "Warm Tan", "base"), ("#8B7355", "Warm Brown", "base")],
        "neutrals": [("#000000", "Black", "neutral"), ("#FFFFFF", "White", "neutral"),
                     ("#808080", "Grey", "neutral"), ("#C0C0C0", "Silver", "neutral")],
        "accents":  [("#FF0000", "Red", "accent"), ("#FF00FF", "Magenta", "accent"),
                     ("#0000FF", "Blue", "accent")],
    },
}

# 4-season fallback (maps to closest extended)
_FOUR_TO_TWELVE = {
    "spring": "true_spring",
    "summer": "true_summer",
    "autumn": "true_autumn",
    "winter": "true_winter",
}

_SEASON_META: dict[str, dict] = {
    "light_spring":  {"family": "spring", "contrast": "low",    "chroma": "clear",  "value": "light",
                      "desc": "You are a Light Spring — your colouring is delicate and luminous with warm golden undertones. You suit soft, warm, clear colours that don't overwhelm your fairness.",
                      "chars": ["Fair to light skin with golden/peachy undertones", "Light blonde, strawberry blonde, or light brown hair", "Blue, green, or light hazel eyes", "Low contrast between features"],
                      "celebs": ["Taylor Swift", "Gwyneth Paltrow", "Reese Witherspoon"]},
    "true_spring":   {"family": "spring", "contrast": "medium", "chroma": "clear",  "value": "medium",
                      "desc": "You are a True Spring — warm, clear, and medium in value. You come alive in warm, saturated shades that match your naturally sunny and vibrant colouring.",
                      "chars": ["Medium warm skin with peachy-golden glow", "Golden blonde to chestnut brown hair", "Clear green, hazel, or warm brown eyes", "Moderate contrast between features"],
                      "celebs": ["Jennifer Aniston", "Jessica Alba", "Blake Lively"]},
    "bright_spring": {"family": "spring", "contrast": "high",   "chroma": "bright", "value": "medium",
                      "desc": "You are a Bright Spring — your colouring is warm and intensely clear. High-contrast and vivid colours bring out your striking, luminous beauty.",
                      "chars": ["Clear, bright skin with warm undertones", "Dark to medium warm hair", "Bright blue, green, or hazel eyes — vivid", "High contrast between skin and eyes/hair"],
                      "celebs": ["Anne Hathaway", "Mila Kunis", "Emma Stone"]},
    "light_summer":  {"family": "summer", "contrast": "low",    "chroma": "muted",  "value": "light",
                      "desc": "You are a Light Summer — soft, cool, and delicate. Blended, powdery colours suit you best; harsh darks overwhelm your gentle colouring.",
                      "chars": ["Fair, cool-toned skin — often with pink or beige cast", "Ash blonde, light ash brown, or silver hair", "Blue, grey, or soft green eyes", "Low contrast — features blend together softly"],
                      "celebs": ["Cate Blanchett", "Naomi Watts", "Nicole Kidman"]},
    "true_summer":   {"family": "summer", "contrast": "medium", "chroma": "muted",  "value": "medium",
                      "desc": "You are a True Summer — cool-toned, soft, and medium in depth. Dusty, muted colours harmonise with your naturally elegant and understated beauty.",
                      "chars": ["Medium cool skin with rosy or beige undertones", "Ash brown, dirty blonde, or greyed-brown hair", "Blue-grey, greyish-green, or soft brown eyes", "Moderate cool contrast"],
                      "celebs": ["Angelina Jolie", "Jennifer Garner", "Liv Tyler"]},
    "soft_summer":   {"family": "summer", "contrast": "low",    "chroma": "muted",  "value": "medium",
                      "desc": "You are a Soft Summer — muted, blended, and neutral-cool. You bridge summer and autumn with soft, greyed shades that complement your understated elegance.",
                      "chars": ["Medium neutral-cool skin, slightly warm", "Medium ash or warm brown hair (neither very warm nor very cool)", "Hazel, grey-green, or soft brown eyes", "Low-medium contrast, blended look"],
                      "celebs": ["Sandra Bullock", "Sarah Jessica Parker", "Julia Roberts"]},
    "soft_autumn":   {"family": "autumn", "contrast": "low",    "chroma": "muted",  "value": "medium",
                      "desc": "You are a Soft Autumn — warm-toned, muted, and gentle. You sit between summer and autumn — earthy yet delicate. Dusty warm shades are your power palette.",
                      "chars": ["Medium warm skin — golden, peachy, or slightly tanned", "Medium warm brown to dark blonde hair", "Hazel, warm green, or soft brown eyes", "Low contrast, blended features"],
                      "celebs": ["Jennifer Lopez", "Priyanka Chopra", "Beyoncé"]},
    "true_autumn":   {"family": "autumn", "contrast": "medium", "chroma": "muted",  "value": "medium",
                      "desc": "You are a True Autumn — rich, warm, and earthy. Nature's harvest palette — rust, olive, terracotta and golden brown — is made for you.",
                      "chars": ["Medium to tan warm skin with golden or peachy cast", "Auburn, copper, chestnut, or warm brown hair", "Green, hazel, amber, or warm brown eyes", "Medium warm contrast"],
                      "celebs": ["Julianne Moore", "Emma Stone (natural)", "Isla Fisher"]},
    "deep_autumn":   {"family": "autumn", "contrast": "high",   "chroma": "muted",  "value": "deep",
                      "desc": "You are a Deep Autumn — rich, warm, and high-contrast. Deep, earthy shades with golden warmth suit your intense, striking beauty.",
                      "chars": ["Medium-deep to deep warm skin", "Dark brown, black-brown, or very dark auburn hair", "Dark brown, black, or deep olive-brown eyes", "High contrast between skin and hair/eyes"],
                      "celebs": ["Halle Berry", "Jennifer Hudson", "Sofia Vergara"]},
    "deep_winter":   {"family": "winter", "contrast": "high",   "chroma": "clear",  "value": "deep",
                      "desc": "You are a Deep Winter — rich, cool, and high-contrast. Deep, cool, saturated shades complement your striking colouring magnificently.",
                      "chars": ["Deep, cool skin — ebony to deep olive with cool cast", "Very dark brown or black hair", "Dark brown or black eyes", "High contrast — dramatic"],
                      "celebs": ["Lupita Nyong'o", "Viola Davis", "Deepika Padukone"]},
    "true_winter":   {"family": "winter", "contrast": "high",   "chroma": "clear",  "value": "medium",
                      "desc": "You are a True Winter — cool, clear, and high-contrast. The most dramatic season — pure, icy, and jewel-toned colours command attention.",
                      "chars": ["Medium cool skin — olive, beige with cool undertone, or porcelain", "Dark brown or black hair", "Dark brown, black, grey-blue, or ice blue eyes", "Very high contrast"],
                      "celebs": ["Megan Fox", "Demi Lovato", "Lucy Liu"]},
    "bright_winter": {"family": "winter", "contrast": "high",   "chroma": "bright", "value": "medium",
                      "desc": "You are a Bright Winter — cool and intensely vivid. You share brightness with Bright Spring but with cool rather than warm undertones. Electric, clear colours ignite your look.",
                      "chars": ["Clear cool skin — porcelain, beige, or light olive", "Very dark hair creating dramatic contrast", "Vivid blue, green, or striking dark eyes", "Extreme contrast"],
                      "celebs": ["Katy Perry", "Zooey Deschanel", "Rihanna"]},
}


# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFICATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ColorIntelligenceEngine:
    """
    Main engine. Call compute(inputs) to get a FullColorProfile.
    All methods are pure functions — no I/O, no state, fast (~5ms).
    """

    def compute(self, inputs: dict[str, Any]) -> FullColorProfile:
        """
        inputs keys (all optional — engine degrades gracefully):
            skin_tone: str, undertone: str, ita_angle: float,
            fitzpatrick: int, skin_hex: str,
            hair_color_hex: str, eye_color: str
        """
        skin_tone    = (inputs.get("skin_tone") or "medium").lower()
        undertone    = (inputs.get("undertone") or "neutral").lower()
        ita          = float(inputs.get("ita_angle") or 28.0)
        fitzpatrick  = int(inputs.get("fitzpatrick") or 3)
        skin_hex     = inputs.get("skin_hex") or "#C19A6B"
        hair_hex     = inputs.get("hair_color_hex") or "#5C3317"
        eye_color    = (inputs.get("eye_color") or "brown").lower()

        # Step 1: compute dimension scores
        value    = self._value_score(ita, fitzpatrick)
        chroma   = self._chroma_score(skin_hex)
        contrast = self._contrast_score(skin_hex, hair_hex)

        # Step 2: classify season
        season_key = self._classify(undertone, value, chroma, contrast, skin_tone)
        meta       = _SEASON_META[season_key]
        confidence = self._confidence(undertone, value, chroma, contrast, season_key)

        season = SeasonResult(
            season=season_key,
            confidence=round(confidence, 3),
            description=meta["desc"],
            key_characteristics=meta["chars"],
            celebrity_examples=meta["celebs"],
            season_family=meta["family"],
            contrast_level=meta["contrast"],
            chroma_level=meta["chroma"],
            value_level=meta["value"],
        )

        # Step 3: build palette
        pal_data  = _SEASON_PALETTES.get(season_key, _SEASON_PALETTES["true_spring"])
        best      = [ColorEntry(*c) for c in pal_data["best"]]
        avoid     = [ColorEntry(*c, season_fit="avoid") for c in pal_data["avoid"]]
        neutrals  = [ColorEntry(*c) for c in pal_data["neutrals"]]
        accents   = [ColorEntry(*c) for c in pal_data["accents"]]
        hero      = best[0]  # first is always the signature color

        return FullColorProfile(
            season=season,
            palette_best=best,
            palette_neutrals=neutrals,
            palette_accents=accents,
            palette_avoid=avoid,
            hero_color=hero,
            makeup=self._makeup(season_key, undertone, skin_tone, skin_hex),
            lipstick=self._lipstick(season_key, undertone),
            hair_color=self._hair_color(season_key, undertone, hair_hex),
            outfits=self._outfits(season_key, best, neutrals, accents),
            jewelry=self._jewelry(season_key, undertone),
        )

    # ── Dimension scoring ─────────────────────────────────────────────────

    def _value_score(self, ita: float, fitzpatrick: int) -> str:
        """light | medium | deep"""
        # ITA° > 41 = light; 10–41 = medium; < 10 = deep
        if ita > 41 or fitzpatrick <= 2:
            return "light"
        if ita > 10 or fitzpatrick <= 4:
            return "medium"
        return "deep"

    def _chroma_score(self, hex_color: str) -> str:
        """muted | soft | clear | bright — from HSV saturation of skin"""
        try:
            h, s, v = self._hex_to_hsv(hex_color)
            if s < 0.15:
                return "muted"
            if s < 0.30:
                return "soft"
            if s < 0.55:
                return "clear"
            return "bright"
        except Exception:
            return "clear"

    def _contrast_score(self, skin_hex: str, hair_hex: str) -> str:
        """low | medium | high — luminance difference between skin and hair"""
        try:
            _, _, sv = self._hex_to_hsv(skin_hex)
            _, _, hv = self._hex_to_hsv(hair_hex)
            diff = abs(sv - hv)
            if diff < 0.25:
                return "low"
            if diff < 0.50:
                return "medium"
            return "high"
        except Exception:
            return "medium"

    # ── Season classification decision matrix ─────────────────────────────

    def _classify(
        self, undertone: str, value: str, chroma: str, contrast: str, skin_tone: str
    ) -> str:
        # Build candidate scores
        scores: dict[str, float] = {}
        for season_key, meta in _SEASON_META.items():
            score = 0.0
            # Undertone match (highest weight — 40 pts)
            if meta["family"] in ("spring", "autumn") and undertone == "warm":
                score += 40
            elif meta["family"] in ("summer", "winter") and undertone == "cool":
                score += 40
            elif undertone == "neutral":
                score += 20  # neutral fits anywhere but not perfectly
            # Value match (30 pts)
            if meta["value"] == value:
                score += 30
            elif abs(["light","medium","deep"].index(meta["value"])
                     - ["light","medium","deep"].index(value)) == 1:
                score += 15  # one step away
            # Chroma match (20 pts)
            chroma_order = ["muted", "soft", "clear", "bright"]
            if meta["chroma"] == chroma:
                score += 20
            elif abs(chroma_order.index(meta["chroma"])
                     - chroma_order.index(chroma)) == 1:
                score += 10
            # Contrast match (10 pts)
            if meta["contrast"] == contrast:
                score += 10
            scores[season_key] = score

        # Return highest scoring season
        return max(scores, key=lambda k: scores[k])

    def _confidence(
        self, undertone: str, value: str, chroma: str, contrast: str, season_key: str
    ) -> float:
        """Derive confidence from how clearly inputs map to the season."""
        meta = _SEASON_META[season_key]
        score = 0
        total = 4
        if (meta["family"] in ("spring", "autumn") and undertone == "warm") or \
           (meta["family"] in ("summer", "winter") and undertone == "cool"):
            score += 1
        if meta["value"] == value:
            score += 1
        if meta["chroma"] == chroma:
            score += 1
        if meta["contrast"] == contrast:
            score += 1
        # Base confidence 0.60–0.97
        return 0.60 + (score / total) * 0.37

    # ── Makeup ────────────────────────────────────────────────────────────

    def _makeup(self, season: str, undertone: str, skin_tone: str, skin_hex: str) -> dict:
        family = _SEASON_META[season]["family"]
        chroma = _SEASON_META[season]["chroma"]

        blush_map = {
            ("spring", "warm"):  [{"hex": "#FFB6C1", "name": "Peachy Pink", "category": "accent"},
                                   {"hex": "#FF8C69", "name": "Salmon", "category": "accent"},
                                   {"hex": "#FFA07A", "name": "Light Coral", "category": "accent"}],
            ("summer", "cool"):  [{"hex": "#DDA0DD", "name": "Soft Plum", "category": "accent"},
                                   {"hex": "#DB7093", "name": "Rose", "category": "accent"},
                                   {"hex": "#C8A2C8", "name": "Dusty Lilac", "category": "accent"}],
            ("autumn", "warm"):  [{"hex": "#CD853F", "name": "Terracotta", "category": "accent"},
                                   {"hex": "#D2691E", "name": "Burnt Sienna", "category": "accent"},
                                   {"hex": "#BC8F8F", "name": "Dusty Rose", "category": "accent"}],
            ("winter", "cool"):  [{"hex": "#C71585", "name": "Berry", "category": "accent"},
                                   {"hex": "#DC143C", "name": "Crimson", "category": "accent"},
                                   {"hex": "#DB7093", "name": "Deep Rose", "category": "accent"}],
        }
        blush_key = (family, undertone if undertone != "neutral"
                     else ("warm" if family in ("spring", "autumn") else "cool"))
        blush = blush_map.get(blush_key, blush_map[("spring", "warm")])

        eyeshadow_palettes = self._eyeshadow_palettes(season)
        liner_colors = self._liner_colors(family, chroma)
        highlight = self._highlight(undertone)
        contour   = self._contour(skin_tone)

        return {
            "foundation_undertone": undertone,
            "foundation_finish": "satin" if chroma in ("clear","bright") else "luminous",
            "blush_shades": blush,
            "eyeshadow_palettes": eyeshadow_palettes,
            "eyeliner_colors": liner_colors,
            "highlight_shades": highlight,
            "contour_shades": contour,
        }

    def _eyeshadow_palettes(self, season: str) -> list[dict]:
        family = _SEASON_META[season]["family"]
        palettes = {
            "spring": [
                {"name": "Golden Hour", "shades": ["#FFD700","#FFA500","#CD853F","#F5DEB3","#FFFFFF"], "finish": "shimmer"},
                {"name": "Garden Fresh", "shades": ["#98FB98","#90EE90","#8FBC8F","#DEB887","#FFFFF0"], "finish": "satin"},
            ],
            "summer": [
                {"name": "Plum Mist", "shades": ["#DDA0DD","#D8BFD8","#9370DB","#C8A2C8","#F0F0F0"], "finish": "matte"},
                {"name": "Soft Rose", "shades": ["#DB7093","#FFB6C1","#BC8F8F","#D3D3D3","#FFF5EE"], "finish": "satin"},
            ],
            "autumn": [
                {"name": "Harvest Moon", "shades": ["#8B4513","#D2691E","#CD853F","#DEB887","#F5DEB3"], "finish": "matte"},
                {"name": "Forest Floor", "shades": ["#6B8E23","#556B2F","#8FBC8F","#D2B48C","#F5F5DC"], "finish": "satin"},
            ],
            "winter": [
                {"name": "Midnight", "shades": ["#000000","#191970","#4B0082","#800080","#FFFFFF"], "finish": "shimmer"},
                {"name": "Ice Queen", "shades": ["#E6E6FA","#B0C4DE","#778899","#2F4F4F","#F8F8FF"], "finish": "metallic"},
            ],
        }
        return palettes.get(family, palettes["spring"])

    def _liner_colors(self, family: str, chroma: str) -> list[dict]:
        warm  = [{"hex": "#3B1A0A", "name": "Warm Brown Black", "category": "accent"},
                 {"hex": "#8B4513", "name": "Chocolate", "category": "accent"},
                 {"hex": "#4A3728", "name": "Dark Espresso", "category": "accent"}]
        cool  = [{"hex": "#000000", "name": "Black", "category": "accent"},
                 {"hex": "#191970", "name": "Navy", "category": "accent"},
                 {"hex": "#4B0082", "name": "Deep Purple", "category": "accent"}]
        return warm if family in ("spring", "autumn") else cool

    def _highlight(self, undertone: str) -> list[dict]:
        if undertone == "warm":
            return [{"hex": "#FFD700", "name": "Gold", "category": "accent"},
                    {"hex": "#FFE4B5", "name": "Champagne", "category": "accent"},
                    {"hex": "#DAA520", "name": "Warm Gold", "category": "accent"}]
        if undertone == "cool":
            return [{"hex": "#C0C0C0", "name": "Silver", "category": "accent"},
                    {"hex": "#E8E8FF", "name": "Icy Lavender", "category": "accent"},
                    {"hex": "#F0F8FF", "name": "Ice Blue", "category": "accent"}]
        return [{"hex": "#F5F5DC", "name": "Soft Champagne", "category": "accent"},
                {"hex": "#E8DCC8", "name": "Pearl", "category": "accent"},
                {"hex": "#FFD700", "name": "Rose Gold", "category": "accent"}]

    def _contour(self, skin_tone: str) -> list[dict]:
        depth_map = {
            "fair":   [{"hex": "#C4A882", "name": "Warm Taupe", "category": "neutral"}],
            "light":  [{"hex": "#B09070", "name": "Caramel Matte", "category": "neutral"}],
            "medium": [{"hex": "#A0785A", "name": "Cool Cocoa", "category": "neutral"}],
            "olive":  [{"hex": "#8B6558", "name": "Terra", "category": "neutral"}],
            "tan":    [{"hex": "#7A5C46", "name": "Deep Mocha", "category": "neutral"}],
            "deep":   [{"hex": "#5C3A1E", "name": "Ebony Contour", "category": "neutral"}],
        }
        return depth_map.get(skin_tone, depth_map["medium"])

    # ── Lipstick ──────────────────────────────────────────────────────────

    def _lipstick(self, season: str, undertone: str) -> list[dict]:
        family = _SEASON_META[season]["family"]
        chroma = _SEASON_META[season]["chroma"]
        value  = _SEASON_META[season]["value"]

        tables = {
            "spring": [
                {"shade": "Coral Dream",     "hex": "#FF7F50", "finish": "satin",  "intensity": "medium", "occasion": "everyday",     "brands": ["MAC Coral Bliss", "NARS Orgasm", "Charlotte Tilbury"], "rationale": "Warm coral harmonises with your golden undertones"},
                {"shade": "Warm Peach",       "hex": "#FFAB76", "finish": "gloss",  "intensity": "light",  "occasion": "everyday",     "brands": ["Glossier G Spot", "Fenty Gloss Bomb"], "rationale": "Peachy warmth enhances your Spring glow"},
                {"shade": "Juicy Watermelon", "hex": "#FC6C85", "finish": "sheer",  "intensity": "medium", "occasion": "special",      "brands": ["NARS Orgasm", "YSL Rouge Pure"], "rationale": "Bright pinks energise your clear Spring colouring"},
                {"shade": "Golden Nude",      "hex": "#C8896A", "finish": "satin",  "intensity": "light",  "occasion": "professional", "brands": ["MAC Velvet Teddy", "Charlotte Tilbury Pillow Talk"], "rationale": "Warm nude with golden depth flatters without washing out"},
                {"shade": "Brick Rose",       "hex": "#B05540", "finish": "matte",  "intensity": "bold",   "occasion": "evening",      "brands": ["MAC Lady Danger variant", "NARS Heat Wave"], "rationale": "Warm brick adds drama for evenings"},
            ],
            "summer": [
                {"shade": "Mauve Rose",       "hex": "#C5808E", "finish": "satin",  "intensity": "medium", "occasion": "everyday",     "brands": ["MAC Twig", "Charlotte Tilbury Supermodel"], "rationale": "Dusty rose-mauve honours your cool understated beauty"},
                {"shade": "Berry Bliss",      "hex": "#8B3A6A", "finish": "matte",  "intensity": "bold",   "occasion": "evening",      "brands": ["MAC Rebel", "Urban Decay Naked"], "rationale": "Cool berry adds drama while staying true to your season"},
                {"shade": "Soft Plum",        "hex": "#9B6080", "finish": "satin",  "intensity": "medium", "occasion": "special",      "brands": ["NARS Dolce Vita", "Dior Addict"], "rationale": "Soft plum is the quintessential Summer shade"},
                {"shade": "Rose Nude",        "hex": "#C4958A", "finish": "gloss",  "intensity": "light",  "occasion": "professional", "brands": ["Fenty Starstruck", "Rare Beauty"], "rationale": "Cool-toned nude with rosy depth for daytime elegance"},
                {"shade": "Dusty Pink",       "hex": "#DDA0A8", "finish": "sheer",  "intensity": "light",  "occasion": "everyday",     "brands": ["NARS Sheer Glow", "Glossier"], "rationale": "Soft and romantic — pure Summer energy"},
            ],
            "autumn": [
                {"shade": "Terracotta",       "hex": "#C46B3A", "finish": "matte",  "intensity": "bold",   "occasion": "everyday",     "brands": ["MAC Brick-O-La", "Rare Beauty"], "rationale": "Earthy terracotta echoes autumn's natural warmth"},
                {"shade": "Warm Brick Red",   "hex": "#A03020", "finish": "matte",  "intensity": "bold",   "occasion": "evening",      "brands": ["MAC Russian Red", "NARS Dragon Girl"], "rationale": "Warm red with brown depth — powerfully autumnal"},
                {"shade": "Copper Bronze",    "hex": "#B87333", "finish": "metallic","intensity": "medium", "occasion": "special",      "brands": ["Charlotte Tilbury Bronze Beauty"], "rationale": "Burnished copper is pure Autumn magic"},
                {"shade": "Warm Nude",        "hex": "#C4A882", "finish": "satin",  "intensity": "light",  "occasion": "professional", "brands": ["MAC Velvet Teddy", "Fenty Clapback"], "rationale": "Golden nude matches your natural warmth beautifully"},
                {"shade": "Burnt Caramel",    "hex": "#9A5A30", "finish": "satin",  "intensity": "medium", "occasion": "everyday",     "brands": ["MAC Spice", "Tom Ford Cognac"], "rationale": "Deep caramel brings warmth and depth to your Autumn look"},
            ],
            "winter": [
                {"shade": "True Red",         "hex": "#CC0000", "finish": "matte",  "intensity": "bold",   "occasion": "evening",      "brands": ["MAC Russian Red", "YSL Le Rouge", "Dior 999"], "rationale": "Cool, pure red is Winter's signature shade"},
                {"shade": "Deep Berry",       "hex": "#721F52", "finish": "matte",  "intensity": "bold",   "occasion": "special",      "brands": ["MAC Diva", "NARS Scarlet Empress"], "rationale": "Deep berry-purple commands Winter's dramatic beauty"},
                {"shade": "Fuchsia",          "hex": "#C2185B", "finish": "satin",  "intensity": "bold",   "occasion": "special",      "brands": ["MAC Candy Yum Yum", "Charlotte Tilbury"], "rationale": "Cool fuchsia electrifies Winter clarity"},
                {"shade": "Icy Rose Nude",    "hex": "#C8A8A8", "finish": "gloss",  "intensity": "light",  "occasion": "professional", "brands": ["MAC Myth", "Fenty Nude"], "rationale": "Cool, light nude for professional daytime elegance"},
                {"shade": "Wine",             "hex": "#722F37", "finish": "matte",  "intensity": "bold",   "occasion": "everyday",     "brands": ["MAC Rebel", "Dior Poison"], "rationale": "Rich wine is Winter's most wearable dramatic shade"},
            ],
        }
        return tables.get(family, tables["spring"])

    # ── Hair colour ───────────────────────────────────────────────────────

    def _hair_color(self, season: str, undertone: str, current_hex: str) -> list[dict]:
        family = _SEASON_META[season]["family"]
        options = {
            "spring": [
                {"name": "Warm Golden Blonde", "hex": "#DAA520", "technique": "highlights", "commitment": "semi-permanent", "maintenance": "Medium", "rationale": "Golden highlights amplify your warm, luminous Spring energy and create a sun-kissed glow"},
                {"name": "Honey Balayage",      "hex": "#C8860A", "technique": "balayage",   "commitment": "permanent",      "maintenance": "Low",    "rationale": "Dimensional honey tones blend seamlessly with Spring's warm clarity"},
                {"name": "Strawberry Blonde",   "hex": "#E8956D", "technique": "all-over",   "commitment": "semi-permanent", "maintenance": "Medium", "rationale": "The quintessential Spring shade — peachy warmth meets blonde luminosity"},
                {"name": "Warm Auburn",         "hex": "#A0522D", "technique": "all-over",   "commitment": "permanent",      "maintenance": "High",   "rationale": "Warm auburn intensifies contrast for Bright Springs; adds warmth to Light Springs"},
                {"name": "Caramel Highlights",  "hex": "#C49A3C", "technique": "highlights", "commitment": "semi-permanent", "maintenance": "Low",    "rationale": "Subtle caramel weave that adds warmth without overwhelming delicate Spring features"},
            ],
            "summer": [
                {"name": "Ash Blonde",          "hex": "#C8B89A", "technique": "all-over",   "commitment": "permanent",      "maintenance": "High",   "rationale": "Cool, ashened blonde perfectly mirrors Summer's soft, cool aesthetic"},
                {"name": "Cool Brown Gloss",    "hex": "#7A6055", "technique": "gloss",       "commitment": "temporary",      "maintenance": "Low",    "rationale": "Adds cool-toned depth and shine without harsh contrast"},
                {"name": "Silver Highlights",   "hex": "#C0C0C0", "technique": "highlights", "commitment": "permanent",      "maintenance": "Medium", "rationale": "Silver weave creates ethereal Summer luminosity — especially beautiful for Light and True Summers"},
                {"name": "Dusty Rose Tint",     "hex": "#D4A0A0", "technique": "gloss",       "commitment": "temporary",      "maintenance": "Low",    "rationale": "A subtle cool-pink gloss enhances Summer's romantic quality"},
                {"name": "Cool Mushroom Brown", "hex": "#8A7A6E", "technique": "balayage",   "commitment": "semi-permanent", "maintenance": "Low",    "rationale": "Muted, blended mushroom tones are pure Summer elegance"},
            ],
            "autumn": [
                {"name": "Rich Copper",         "hex": "#B87333", "technique": "all-over",   "commitment": "permanent",      "maintenance": "High",   "rationale": "Burnished copper is Autumn's crown jewel — enhances warmth dramatically"},
                {"name": "Auburn Balayage",     "hex": "#A0522D", "technique": "balayage",   "commitment": "permanent",      "maintenance": "Medium", "rationale": "Dimensional auburn creates that enviable Autumn warmth and depth"},
                {"name": "Golden Brown",        "hex": "#8B6914", "technique": "all-over",   "commitment": "permanent",      "maintenance": "Medium", "rationale": "Warm golden brown harmonises with earth tones in your Autumn palette"},
                {"name": "Chestnut",            "hex": "#954535", "technique": "all-over",   "commitment": "permanent",      "maintenance": "Medium", "rationale": "Deep chestnut adds richness — especially powerful for Deep Autumns"},
                {"name": "Warm Dark Brown",     "hex": "#5C3317", "technique": "gloss",       "commitment": "semi-permanent", "maintenance": "Low",    "rationale": "A warm mahogany gloss deepens and enriches natural brown Autumn hair"},
            ],
            "winter": [
                {"name": "Jet Black",           "hex": "#0A0A0A", "technique": "all-over",   "commitment": "permanent",      "maintenance": "Medium", "rationale": "The ultimate Winter shade — pure, dramatic, and commanding"},
                {"name": "Blue Black",          "hex": "#1B1B2F", "technique": "all-over",   "commitment": "permanent",      "maintenance": "Medium", "rationale": "Blue-black adds cool depth for striking Winter drama"},
                {"name": "Platinum Blonde",     "hex": "#E8E8E8", "technique": "all-over",   "commitment": "permanent",      "maintenance": "High",   "rationale": "Icy platinum creates extreme contrast that Winter can carry better than any other season"},
                {"name": "Cool Dark Brown",     "hex": "#3C2A1E", "technique": "all-over",   "commitment": "permanent",      "maintenance": "Low",    "rationale": "Deep cool brown maintains Winter's cool-toned clarity without going full black"},
                {"name": "Burgundy",            "hex": "#722F37", "technique": "all-over",   "commitment": "permanent",      "maintenance": "Medium", "rationale": "Rich wine-burgundy — a statement Winter colour that commands attention"},
            ],
        }
        return options.get(family, options["spring"])

    # ── Outfit recommendations ────────────────────────────────────────────

    def _outfits(
        self,
        season: str,
        best: list[ColorEntry],
        neutrals: list[ColorEntry],
        accents: list[ColorEntry],
    ) -> dict:
        family = _SEASON_META[season]["family"]

        def _entry(c: ColorEntry) -> dict:
            return {"hex": c.hex, "name": c.name, "category": c.category}

        occasion_tips = {
            "spring":  {
                "work":    "Layer warm neutrals with a clear accent blouse. Camel + white + coral.",
                "evening": "Wear a statement warm coral or bright green. Avoid black — try navy or rich brown.",
                "casual":  "Peach, warm yellow, or coral denim is your weekend signature.",
                "sport":   "Warm pinks, bright corals, and golden yellows energise your Spring look.",
            },
            "summer":  {
                "work":    "Soft plum blouse with greige trousers. Dusty rose accessories complete the look.",
                "evening": "Mauve, dusty teal, or deep violet for a polished Summer evening.",
                "casual":  "Powder blue, soft lilac, or pale sage — effortlessly elegant.",
                "sport":   "Soft mauves, lavender, and cool blues make Summer sport looks chic.",
            },
            "autumn":  {
                "work":    "Warm camel blazer over deep olive or burnt sienna. The power Autumn look.",
                "evening": "Rich terracotta, deep burgundy, or forest green command the room.",
                "casual":  "Rust-toned denim, mustard knits, and warm brown boots are Autumn perfection.",
                "sport":   "Warm olive, burnt orange, and tan — earthy and energised.",
            },
            "winter":  {
                "work":    "Stark white with black or navy. Or one strong jewel tone head to toe.",
                "evening": "Deep burgundy, cobalt blue, or emerald green with silver accessories.",
                "casual":  "Monochrome — all black, all grey, or all white — is pure Winter chic.",
                "sport":   "High-contrast black and white, or a single saturated cool colour.",
            },
        }

        tips = occasion_tips.get(family, occasion_tips["spring"])
        palette_slice = best[:6]
        return {
            "work":    {"base_colors": [_entry(c) for c in neutrals[:3]],
                        "accent_colors": [_entry(c) for c in accents[:2]],
                        "avoid_colors": [], "styling_tip": tips["work"]},
            "evening": {"base_colors": [_entry(c) for c in palette_slice[:2]],
                        "accent_colors": [_entry(c) for c in accents],
                        "avoid_colors": [], "styling_tip": tips["evening"]},
            "casual":  {"base_colors": [_entry(c) for c in neutrals],
                        "accent_colors": [_entry(c) for c in palette_slice[2:5]],
                        "avoid_colors": [], "styling_tip": tips["casual"]},
            "sport":   {"base_colors": [_entry(c) for c in palette_slice[3:6]],
                        "accent_colors": [_entry(c) for c in accents[:2]],
                        "avoid_colors": [], "styling_tip": tips["sport"]},
        }

    # ── Jewelry ───────────────────────────────────────────────────────────

    def _jewelry(self, season: str, undertone: str) -> dict:
        family = _SEASON_META[season]["family"]
        metal_map = {
            "spring": {"metals": ["gold", "rose-gold", "warm-bronze"],
                       "gems": [{"hex": "#50C878", "name": "Emerald", "category": "accent"},
                                 {"hex": "#FF7F50", "name": "Coral", "category": "accent"},
                                 {"hex": "#FFA500", "name": "Citrine", "category": "accent"},
                                 {"hex": "#98FB98", "name": "Peridot", "category": "accent"}],
                       "rationale": "Warm gold metals harmonise with your golden undertones. Choose bright, clear gemstones.",
                       "style": "Delicate gold chains, dainty charms. Avoid heavy oxidised silver."},
            "summer": {"metals": ["silver", "white-gold", "platinum", "rose-gold"],
                       "gems": [{"hex": "#E6E6FA", "name": "Lavender Amethyst", "category": "accent"},
                                 {"hex": "#B0C4DE", "name": "Aquamarine", "category": "accent"},
                                 {"hex": "#DDA0DD", "name": "Rose Quartz", "category": "accent"},
                                 {"hex": "#9370DB", "name": "Soft Sapphire", "category": "accent"}],
                       "rationale": "Cool silver and platinum metals suit your cool undertones perfectly.",
                       "style": "Elegant silver pieces, pearl accents. Muted, romantic gemstone settings."},
            "autumn": {"metals": ["gold", "copper", "bronze", "antique-gold"],
                       "gems": [{"hex": "#DAA520", "name": "Citrine", "category": "accent"},
                                 {"hex": "#8B4513", "name": "Tiger's Eye", "category": "accent"},
                                 {"hex": "#CD7F32", "name": "Amber", "category": "accent"},
                                 {"hex": "#228B22", "name": "Deep Emerald", "category": "accent"}],
                       "rationale": "Warm gold, copper, and bronze metals feel organic with Autumn's earthy warmth.",
                       "style": "Substantial, textured pieces. Hammered gold, antique bronze. Earthy stones."},
            "winter": {"metals": ["silver", "platinum", "white-gold"],
                       "gems": [{"hex": "#000000", "name": "Black Diamond", "category": "accent"},
                                 {"hex": "#DC143C", "name": "Ruby", "category": "accent"},
                                 {"hex": "#0000CD", "name": "Sapphire", "category": "accent"},
                                 {"hex": "#50C878", "name": "Emerald", "category": "accent"}],
                       "rationale": "Cool silver and platinum create the sharp contrast Winter needs.",
                       "style": "Architectural, geometric, minimalist. High-polish silver. Statement pieces."},
        }
        data = metal_map.get(family, metal_map["spring"])
        return {
            "metal_tones":  data["metals"],
            "gem_colors":   data["gems"],
            "rationale":    data["rationale"],
            "style_notes":  data["style"],
        }

    # ── Utility ───────────────────────────────────────────────────────────

    @staticmethod
    def _hex_to_hsv(hex_color: str) -> tuple[float, float, float]:
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        return colorsys.rgb_to_hsv(r, g, b)
