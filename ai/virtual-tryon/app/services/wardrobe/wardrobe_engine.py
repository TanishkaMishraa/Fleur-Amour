"""
AuraFit — Wardrobe AI Engine (Stage 9).

Three responsibilities:
  1. CLASSIFICATION — Categorise a clothing item image via ResNet-50/ViT
     → category (tops/bottoms/shoes/outerwear/accessories/bags/dresses)
     → subcategory (t-shirt/blouse/jeans/trousers/etc.)
     → dominant colours (top-3 via k-means on masked image)
     → occasion tags, season tags
     → style tags (minimalist/boho/classic/edgy/romantic)

  2. OUTFIT GENERATION — Given wardrobe items + user profile, generate
     outfit combinations using:
     - Rule-based colour harmony (season-aware, from Stage 5 ColorProfile)
     - Category balance constraints (top+bottom+shoes, or dress+shoes)
     - Occasion/season filter
     - Diversity scoring (prefer under-worn items)

  3. CAPSULE WARDROBE — Analyse full wardrobe, identify:
     - Category gaps (missing essentials for the archetype)
     - Cost-per-wear analysis
     - Redundancy (similar colours in same category)
     - Shopping list with priority rankings

Model chain:
  CLIP (openai/clip-vit-base-patch32) — zero-shot classification
  K-means on image pixels              — dominant colour extraction
  Rule engine                          — outfit composition
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Category taxonomy ─────────────────────────────────────────────────────────

CATEGORIES = {
    "tops":        ["t-shirt", "blouse", "shirt", "sweater", "knit", "crop top", "tank top", "polo"],
    "bottoms":     ["jeans", "trousers", "skirt", "shorts", "leggings", "culottes"],
    "dresses":     ["dress", "jumpsuit", "playsuit", "midi dress", "maxi dress"],
    "outerwear":   ["coat", "jacket", "blazer", "cardigan", "parka", "trench coat"],
    "shoes":       ["heels", "sneakers", "boots", "loafers", "sandals", "flats", "mules"],
    "bags":        ["handbag", "tote", "clutch", "backpack", "shoulder bag", "crossbody"],
    "accessories": ["jewellery", "belt", "scarf", "hat", "sunglasses", "watch"],
}

ALL_SUBCATEGORIES = [sub for subs in CATEGORIES.values() for sub in subs]

OCCASION_TAGS = ["work", "casual", "evening", "sport", "formal", "weekend", "travel"]
SEASON_TAGS   = ["spring", "summer", "autumn", "winter", "all-season"]
STYLE_TAGS    = ["minimalist", "classic", "boho", "edgy", "romantic", "preppy", "athletic", "glamorous"]

# Capsule wardrobe essentials by archetype
_CAPSULE_ESSENTIALS: dict[str, list[dict]] = {
    "The Classic": [
        {"category":"tops",      "item":"White button-down shirt",    "priority":1},
        {"category":"tops",      "item":"Navy blue knit sweater",      "priority":1},
        {"category":"bottoms",   "item":"Tailored black trousers",     "priority":1},
        {"category":"bottoms",   "item":"Straight-leg dark denim",     "priority":1},
        {"category":"dresses",   "item":"Little black dress",          "priority":2},
        {"category":"outerwear", "item":"Camel trench coat",            "priority":1},
        {"category":"outerwear", "item":"Structured blazer",           "priority":1},
        {"category":"shoes",     "item":"Black pumps",                  "priority":1},
        {"category":"shoes",     "item":"Tan loafers or ballet flats", "priority":2},
        {"category":"bags",      "item":"Structured leather tote",     "priority":1},
    ],
    "The Minimalist": [
        {"category":"tops",      "item":"White oversized tee",         "priority":1},
        {"category":"tops",      "item":"Black crewneck sweatshirt",   "priority":1},
        {"category":"bottoms",   "item":"High-waist wide-leg trousers","priority":1},
        {"category":"bottoms",   "item":"Black straight-leg jeans",    "priority":1},
        {"category":"dresses",   "item":"Slip dress in neutral",       "priority":2},
        {"category":"outerwear", "item":"Clean-cut longline coat",     "priority":1},
        {"category":"shoes",     "item":"White leather sneakers",      "priority":1},
        {"category":"shoes",     "item":"Simple leather loafers",      "priority":1},
        {"category":"bags",      "item":"Minimal leather crossbody",   "priority":1},
    ],
    "default": [
        {"category":"tops",      "item":"Quality white tee",           "priority":1},
        {"category":"tops",      "item":"Versatile knitwear",          "priority":1},
        {"category":"bottoms",   "item":"Classic blue jeans",          "priority":1},
        {"category":"bottoms",   "item":"Black trousers",              "priority":1},
        {"category":"dresses",   "item":"Day-to-evening dress",        "priority":2},
        {"category":"outerwear", "item":"All-weather coat",            "priority":1},
        {"category":"outerwear", "item":"Blazer",                      "priority":1},
        {"category":"shoes",     "item":"White sneakers",              "priority":1},
        {"category":"shoes",     "item":"Simple heels or boots",       "priority":2},
        {"category":"bags",      "item":"Quality everyday bag",        "priority":1},
    ],
}


@dataclass
class ClassificationResult:
    category:        str
    subcategory:     str
    confidence:      float
    dominant_colors: list[str]          # Top-3 hex codes
    occasion_tags:   list[str]
    season_tags:     list[str]
    style_tags:      list[str]
    is_luxury:       bool = False


@dataclass
class OutfitSuggestion:
    outfit_id:      str
    items:          list[dict]           # [{wardrobe_item_id, category, image_url, name}]
    occasion:       str
    season:         str
    color_harmony:  str                  # "monochrome" | "complementary" | "analogous"
    ai_score:       float
    explanation:    str
    style_tags:     list[str]


@dataclass
class CapsuleAnalysis:
    total_items:      int
    total_value:      float
    category_counts:  dict[str, int]
    missing_essentials: list[dict]       # [{category, item, priority}]
    redundancies:     list[dict]         # [{category, items, suggestion}]
    cost_per_wear:    list[dict]         # [{item_id, name, times_worn, cost, cpw}]
    capsule_score:    float              # 0–100: how capsule-ready is the wardrobe
    shopping_list:    list[dict]         # Prioritised items to buy


class WardrobeAIEngine:
    """
    AI-powered wardrobe intelligence.
    CLIP zero-shot for classification, rule-based outfit generation.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._clip_model    = None
        self._clip_processor= None

    # ── Classification ─────────────────────────────────────────────────────────

    def classify_item(self, image_bytes: bytes) -> ClassificationResult:
        """
        Classify a clothing item from its image.
        Uses CLIP zero-shot classification + k-means colour extraction.
        """
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_arr = np.array(img)

        # Attempt CLIP classification
        category, subcategory, confidence = self._classify_clip(img)

        # Dominant colours via k-means
        dominant_colors = self._extract_dominant_colors(img_arr)

        # Rule-based tags from category
        occasion_tags = self._infer_occasion_tags(subcategory, category)
        season_tags   = self._infer_season_tags(subcategory, dominant_colors)
        style_tags    = self._infer_style_tags(subcategory, dominant_colors)

        return ClassificationResult(
            category=category,
            subcategory=subcategory,
            confidence=confidence,
            dominant_colors=dominant_colors,
            occasion_tags=occasion_tags,
            season_tags=season_tags,
            style_tags=style_tags,
        )

    def _classify_clip(self, img: Image.Image) -> tuple[str, str, float]:
        """Zero-shot classification via CLIP."""
        model, processor = self._get_clip()
        if model is None:
            return self._fallback_classify()

        try:
            import torch
            # Build text prompts for all subcategories
            prompts = [f"a photo of a {sub}" for sub in ALL_SUBCATEGORIES]
            inputs  = processor(text=prompts, images=img, return_tensors="pt", padding=True)
            with torch.no_grad():
                outputs   = model(**inputs)
                logits    = outputs.logits_per_image
                probs     = logits.softmax(dim=1).squeeze().tolist()

            best_idx   = int(np.argmax(probs))
            best_sub   = ALL_SUBCATEGORIES[best_idx]
            best_prob  = probs[best_idx]

            # Find category for subcategory
            category = "accessories"
            for cat, subs in CATEGORIES.items():
                if best_sub in subs:
                    category = cat
                    break

            return category, best_sub, round(best_prob, 4)

        except Exception as exc:
            logger.warning("wardrobe.clip_error", error=str(exc))
            return self._fallback_classify()

    @staticmethod
    def _fallback_classify() -> tuple[str, str, float]:
        return "tops", "top", 0.0

    def _extract_dominant_colors(self, arr: np.ndarray, k: int = 3) -> list[str]:
        """K-means colour extraction → top-k hex codes."""
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            return ["#808080"]

        # Reshape to Nx3 and filter near-white/near-black background pixels
        pixels = arr.reshape(-1, 3).astype(np.float32)
        # Remove near-white background (heuristic: all channels > 240)
        mask   = ~(np.all(pixels > 240, axis=1) | np.all(pixels < 15, axis=1))
        pixels = pixels[mask]
        if len(pixels) < k:
            return ["#808080"]

        km = KMeans(n_clusters=k, n_init=3, max_iter=50, random_state=42)
        km.fit(pixels)
        centers = km.cluster_centers_.astype(int)
        return [f"#{int(r):02x}{int(g):02x}{int(b):02x}" for r, g, b in centers]

    def _infer_occasion_tags(self, subcategory: str, category: str) -> list[str]:
        occasion_map = {
            "dress":   ["evening", "casual", "formal"],
            "midi dress":["work", "casual", "evening"],
            "blazer":  ["work", "evening"],
            "coat":    ["work", "casual"],
            "jeans":   ["casual", "weekend"],
            "trousers":["work", "casual"],
            "heels":   ["evening", "formal", "work"],
            "sneakers":["casual", "sport", "weekend"],
        }
        for key, tags in occasion_map.items():
            if key in subcategory:
                return tags
        return ["casual"]

    def _infer_season_tags(self, subcategory: str, colors: list[str]) -> list[str]:
        heavy = ["coat", "parka", "sweater", "boot"]
        light = ["shorts", "sandal", "tank"]
        if any(h in subcategory for h in heavy):
            return ["autumn", "winter"]
        if any(l in subcategory for l in light):
            return ["spring", "summer"]
        return ["all-season"]

    def _infer_style_tags(self, subcategory: str, colors: list[str]) -> list[str]:
        tags = []
        neutral_colors = {"#000000", "#ffffff", "#808080", "#f5f5f0", "#c8b99a"}
        if all(c.lower() in neutral_colors or self._is_near_neutral(c) for c in colors[:2]):
            tags.append("minimalist")
        if subcategory in ("blazer", "trousers", "button-down"):
            tags.extend(["classic", "preppy"])
        if subcategory in ("dress",):
            tags.append("romantic")
        if not tags:
            tags.append("classic")
        return list(set(tags))

    @staticmethod
    def _is_near_neutral(hex_color: str) -> bool:
        h = hex_color.lstrip("#")
        try:
            r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            return max(r, g, b) - min(r, g, b) < 30
        except Exception:
            return False

    # ── Outfit generation ──────────────────────────────────────────────────────

    def generate_outfits(
        self,
        wardrobe_items: list[dict],
        occasion:       str | None = None,
        season:         str | None = None,
        color_season:   str | None = None,
        archetype:      str | None = None,
        limit:          int = 5,
    ) -> list[OutfitSuggestion]:
        """
        Generate outfit combinations from wardrobe items.
        Uses category balance + colour harmony + occasion/season filters.
        """
        import uuid

        # Filter items
        filtered = [item for item in wardrobe_items
                    if not occasion or occasion in (item.get("occasion_tags") or [])]
        if not filtered:
            filtered = wardrobe_items  # Fallback: use all

        # Categorise
        by_cat: dict[str, list[dict]] = {}
        for item in filtered:
            cat = item.get("category", "tops")
            by_cat.setdefault(cat, []).append(item)

        outfits = []
        attempts = 0
        max_attempts = limit * 6

        seen_combos: set = set()

        while len(outfits) < limit and attempts < max_attempts:
            attempts += 1
            combo = self._build_outfit_combo(by_cat, occasion, season)
            if not combo:
                continue

            combo_key = tuple(sorted(i["id"] for i in combo))
            if combo_key in seen_combos:
                continue
            seen_combos.add(combo_key)

            harmony = self._assess_color_harmony(combo)
            score   = self._score_outfit(combo, harmony, occasion, season, color_season)

            outfits.append(OutfitSuggestion(
                outfit_id=str(uuid.uuid4()),
                items=[{
                    "wardrobe_item_id": i.get("id", ""),
                    "category":         i.get("category", ""),
                    "image_url":        i.get("image_url"),
                    "name":             i.get("custom_name") or i.get("product_name", ""),
                    "color_tags":       i.get("color_tags", []),
                } for i in combo],
                occasion=occasion or "casual",
                season=season or "all-season",
                color_harmony=harmony,
                ai_score=score,
                explanation=self._explain_outfit(combo, harmony, occasion, archetype),
                style_tags=self._outfit_style_tags(combo),
            ))

        # Sort by score
        outfits.sort(key=lambda o: o.ai_score, reverse=True)
        return outfits[:limit]

    def _build_outfit_combo(
        self, by_cat: dict[str, list[dict]], occasion: str | None, season: str | None
    ) -> list[dict] | None:
        """
        Build one valid outfit: (top + bottom) or (dress), always + shoes.
        """
        import random
        outfit = []

        # Option A: dress outfit
        if "dresses" in by_cat and random.random() < 0.3:
            dress = random.choice(by_cat["dresses"])
            outfit.append(dress)
        elif "tops" in by_cat and "bottoms" in by_cat:
            outfit.append(random.choice(by_cat["tops"]))
            outfit.append(random.choice(by_cat["bottoms"]))
        elif "tops" in by_cat:
            outfit.append(random.choice(by_cat["tops"]))
        else:
            return None

        if "shoes" in by_cat:
            outfit.append(random.choice(by_cat["shoes"]))
        if "bags" in by_cat and random.random() < 0.5:
            outfit.append(random.choice(by_cat["bags"]))
        if "outerwear" in by_cat and random.random() < 0.4:
            outfit.append(random.choice(by_cat["outerwear"]))

        return outfit if len(outfit) >= 2 else None

    def _assess_color_harmony(self, combo: list[dict]) -> str:
        """Assess if outfit colours are harmonious."""
        all_colors = []
        for item in combo:
            all_colors.extend(item.get("color_tags", []) or [])

        if not all_colors:
            return "unknown"

        neutral_count = sum(1 for c in all_colors if self._is_near_neutral(c) if c.startswith("#"))
        if neutral_count >= len(all_colors) - 1:
            return "monochrome"

        # Simple heuristic: if there are similar hues → analogous
        return "analogous" if len(set(all_colors)) <= 2 else "complementary"

    def _score_outfit(
        self, combo: list[dict], harmony: str,
        occasion: str | None, season: str | None, color_season: str | None
    ) -> float:
        score = 0.5
        # Colour harmony bonus
        harmony_bonus = {"monochrome": 0.15, "analogous": 0.10, "complementary": 0.05, "unknown": 0.0}
        score += harmony_bonus.get(harmony, 0)
        # Category completeness
        cats = {i.get("category") for i in combo}
        if "shoes" in cats:
            score += 0.15
        if ("tops" in cats and "bottoms" in cats) or "dresses" in cats:
            score += 0.10
        # Diversity: prefer under-worn items
        times_worn_avg = np.mean([i.get("times_worn", 0) for i in combo]) if combo else 0
        if times_worn_avg < 3:
            score += 0.10
        return round(min(score, 1.0), 4)

    def _explain_outfit(
        self, combo: list[dict], harmony: str, occasion: str | None, archetype: str | None
    ) -> str:
        cats = [i.get("category", "") for i in combo]
        harmony_desc = {
            "monochrome":   "effortlessly monochromatic",
            "analogous":    "harmoniously tonal",
            "complementary":"interestingly contrasted",
        }
        occ_str  = f" for {occasion}" if occasion else ""
        arch_str = f" Suits {archetype} sensibility." if archetype else ""
        return (
            f"A {harmony_desc.get(harmony, 'well-balanced')} outfit{occ_str}, "
            f"combining {', '.join(cats[:3])}.{arch_str}"
        )

    def _outfit_style_tags(self, combo: list[dict]) -> list[str]:
        tags: set = set()
        for item in combo:
            tags.update(item.get("style_tags") or [])
        return list(tags)[:4]

    # ── Capsule wardrobe analysis ──────────────────────────────────────────────

    def analyse_capsule(
        self,
        wardrobe_items: list[dict],
        archetype:      str | None = None,
    ) -> CapsuleAnalysis:
        """
        Analyse the wardrobe for capsule-wardrobe completeness.
        Returns missing essentials, redundancies, and a shopping list.
        """
        # Category counts
        cat_counts: dict[str, int] = {}
        for item in wardrobe_items:
            cat = item.get("category", "other")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        # Missing essentials
        essentials = _CAPSULE_ESSENTIALS.get(archetype or "default", _CAPSULE_ESSENTIALS["default"])
        owned_cats = set(cat_counts.keys())
        missing: list[dict] = []
        for essential in essentials:
            cat   = essential["category"]
            count = cat_counts.get(cat, 0)
            if count == 0:
                missing.append({**essential, "reason": "category missing entirely"})
            elif count > 0 and essential["priority"] == 1 and count < 2:
                missing.append({**essential, "reason": "insufficient variety"})

        # Redundancies
        redundancies = self._find_redundancies(wardrobe_items, cat_counts)

        # Cost per wear
        cpw = self._cost_per_wear(wardrobe_items)

        # Capsule score (0–100)
        essential_count  = len(essentials)
        filled_essential = essential_count - len(missing)
        score = round((filled_essential / essential_count) * 100) if essential_count > 0 else 50

        # Shopping list: missing essentials sorted by priority
        shopping_list = sorted(missing, key=lambda m: m.get("priority", 2))[:10]

        total_value = sum(float(i.get("cost", 0) or 0) for i in wardrobe_items)

        return CapsuleAnalysis(
            total_items=len(wardrobe_items),
            total_value=round(total_value, 2),
            category_counts=cat_counts,
            missing_essentials=missing,
            redundancies=redundancies,
            cost_per_wear=cpw[:10],
            capsule_score=score,
            shopping_list=shopping_list,
        )

    def _find_redundancies(self, items: list[dict], cat_counts: dict) -> list[dict]:
        redundancies = []
        # Flag categories with more than 5 very similar colour items
        by_cat: dict[str, list[dict]] = {}
        for item in items:
            cat = item.get("category", "other")
            by_cat.setdefault(cat, []).append(item)

        for cat, cat_items in by_cat.items():
            if len(cat_items) <= 3:
                continue
            # Check for neutral overload
            neutral_items = [i for i in cat_items if all(
                self._is_near_neutral(c) for c in (i.get("color_tags") or ["#808080"])
            )]
            if len(neutral_items) > 4:
                redundancies.append({
                    "category":  cat,
                    "count":     len(neutral_items),
                    "suggestion": f"Consider donating {len(neutral_items) - 3} similar neutral {cat}",
                    "items":     [i.get("id") for i in neutral_items[:5]],
                })
        return redundancies

    def _cost_per_wear(self, items: list[dict]) -> list[dict]:
        cpw_list = []
        for item in items:
            cost     = float(item.get("cost", 0) or 0)
            worn     = max(int(item.get("times_worn", 1)), 1)
            cpw_list.append({
                "item_id":   item.get("id"),
                "name":      item.get("custom_name") or "Item",
                "times_worn":worn,
                "cost":      cost,
                "cpw":       round(cost / worn, 2),
            })
        return sorted(cpw_list, key=lambda x: x["cpw"], reverse=True)

    # ── CLIP loader ────────────────────────────────────────────────────────────

    def _get_clip(self):
        if self._clip_model is None:
            try:
                from transformers import CLIPProcessor, CLIPModel
                s = self._settings
                self._clip_processor = CLIPProcessor.from_pretrained(s.WARDROBE_CLIP_MODEL)
                self._clip_model     = CLIPModel.from_pretrained(s.WARDROBE_CLIP_MODEL)
                self._clip_model.eval()
                logger.info("wardrobe.clip_loaded")
            except Exception as exc:
                logger.warning("wardrobe.clip_load_failed", error=str(exc))
        return self._clip_model, self._clip_processor


# Module-level singleton
wardrobe_engine = WardrobeAIEngine()
