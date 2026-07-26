"""
AuraFit — Style DNA Quiz Engine (Stage 8).

A 35-question quiz across 5 dimensions:
  1. Personality & aesthetic identity (7 questions)
  2. Fashion preference analysis (8 questions)
  3. Lifestyle & occasion analysis (7 questions)
  4. Budget & shopping behaviour (6 questions)
  5. Beauty & fragrance preference (7 questions)

Each answer maps to scores across 8 style dimensions:
  style_axis:      classic(0) ↔ avant-garde(1)
  energy_axis:     understated(0) ↔ bold(1)
  structure_axis:  relaxed(0) ↔ tailored(1)
  romance_axis:    minimalist(0) ↔ romantic(1)
  practicality:    impractical(0) ↔ practical(1)
  experimentalism: conservative(0) ↔ experimental(1)
  occasion_work:   0–1 work proportion
  occasion_casual: 0–1 casual proportion
  occasion_evening:0–1 evening proportion

12 style archetypes derived from dimension clusters:
  The Classic, The Minimalist, The Romantic, The Bohemian,
  The Edgy, The Athletic, The Glamorous, The Preppy,
  The Creative, The Sophisticated, The Casual, The Eclectic
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Question definitions ──────────────────────────────────────────────────────

@dataclass
class QuizOption:
    id:     str
    label:  str
    image:  str | None = None
    scores: dict[str, float] = field(default_factory=dict)


@dataclass
class QuizQuestion:
    id:           str
    section:      str
    index:        int
    type:         str     # single | multi | scale | image_grid | text
    question:     str
    subtitle:     str | None = None
    options:      list[QuizOption] = field(default_factory=list)
    scale_min:    int = 0
    scale_max:    int = 10
    scale_labels: tuple[str, str] = ("", "")
    max_select:   int = 1         # For multi-select questions


# ── Full quiz definition ─────────────────────────────────────────────────────

QUIZ_VERSION = "2.0"

QUIZ_QUESTIONS: list[QuizQuestion] = [

    # ═══════════════════════════════════════════════════════════
    # SECTION 1: PERSONALITY & AESTHETIC IDENTITY (7 questions)
    # ═══════════════════════════════════════════════════════════

    QuizQuestion(
        id="p1_visual_identity",
        section="personality",
        index=0,
        type="image_grid",
        question="Which aesthetic speaks to your soul?",
        subtitle="Pick the one that instantly feels like you",
        options=[
            QuizOption("clean_minimal",  "Clean & Minimal",   scores={"style_axis":0.1, "energy_axis":0.2, "structure_axis":0.7, "romance_axis":0.1}),
            QuizOption("dark_edgy",      "Dark & Edgy",       scores={"style_axis":0.8, "energy_axis":0.8, "structure_axis":0.4, "experimentalism":0.8}),
            QuizOption("soft_romantic",  "Soft & Romantic",   scores={"style_axis":0.3, "energy_axis":0.3, "romance_axis":0.9, "structure_axis":0.3}),
            QuizOption("bold_colorful",  "Bold & Colorful",   scores={"style_axis":0.7, "energy_axis":0.9, "experimentalism":0.8, "romance_axis":0.4}),
            QuizOption("classic_polish", "Classic & Polished",scores={"style_axis":0.1, "energy_axis":0.4, "structure_axis":0.9, "practicality":0.7}),
            QuizOption("boho_free",      "Boho & Free-Spirit",scores={"style_axis":0.5, "energy_axis":0.5, "romance_axis":0.6, "experimentalism":0.5}),
        ],
    ),

    QuizQuestion(
        id="p2_fashion_icon",
        section="personality",
        index=1,
        type="single",
        question="Which style icon resonates most with you?",
        subtitle="Not necessarily who you look like — who you aspire to dress like",
        options=[
            QuizOption("audrey",   "Audrey Hepburn — timeless, refined",   scores={"style_axis":0.0, "structure_axis":0.9, "energy_axis":0.3}),
            QuizOption("rihanna",  "Rihanna — fearless, trendsetting",      scores={"style_axis":0.9, "energy_axis":1.0, "experimentalism":0.9}),
            QuizOption("diana",    "Princess Diana — elegant, graceful",    scores={"style_axis":0.2, "structure_axis":0.8, "energy_axis":0.3}),
            QuizOption("zendaya",  "Zendaya — versatile, fashion-forward",  scores={"style_axis":0.7, "energy_axis":0.7, "experimentalism":0.7}),
            QuizOption("sienna",   "Sienna Miller — boho, effortless",      scores={"style_axis":0.4, "energy_axis":0.5, "romance_axis":0.7}),
            QuizOption("amal",     "Amal Clooney — sophisticated, powerful",scores={"style_axis":0.1, "structure_axis":0.9, "energy_axis":0.6}),
        ],
    ),

    QuizQuestion(
        id="p3_mood_board",
        section="personality",
        index=2,
        type="multi",
        question="If your wardrobe had a mood board, which words would be on it?",
        subtitle="Select up to 4",
        max_select=4,
        options=[
            QuizOption("effortless",   "Effortless",   scores={"practicality":0.6, "structure_axis":0.2}),
            QuizOption("powerful",     "Powerful",     scores={"energy_axis":0.8, "structure_axis":0.7}),
            QuizOption("romantic",     "Romantic",     scores={"romance_axis":0.9}),
            QuizOption("mysterious",   "Mysterious",   scores={"style_axis":0.7, "energy_axis":0.5}),
            QuizOption("playful",      "Playful",      scores={"energy_axis":0.7, "experimentalism":0.6}),
            QuizOption("timeless",     "Timeless",     scores={"style_axis":0.1, "structure_axis":0.6}),
            QuizOption("artistic",     "Artistic",     scores={"experimentalism":0.8, "style_axis":0.6}),
            QuizOption("elegant",      "Elegant",      scores={"structure_axis":0.8, "romance_axis":0.5}),
            QuizOption("casual_cool",  "Casual Cool",  scores={"practicality":0.7, "style_axis":0.3}),
            QuizOption("luxurious",    "Luxurious",    scores={"energy_axis":0.6, "structure_axis":0.7}),
        ],
    ),

    QuizQuestion(
        id="p4_confidence_expression",
        section="personality",
        index=3,
        type="scale",
        question="When you get dressed, you want to stand out or blend in?",
        subtitle="Drag to your preference",
        scale_min=0,
        scale_max=10,
        scale_labels=("Blend in gracefully", "Stand out boldly"),
    ),

    QuizQuestion(
        id="p5_change_frequency",
        section="personality",
        index=4,
        type="single",
        question="How often do you like to update your style?",
        options=[
            QuizOption("seasonal",   "Seasonally — I follow the trends",          scores={"experimentalism":0.7, "style_axis":0.6}),
            QuizOption("rarely",     "Rarely — my style is established",           scores={"style_axis":0.1, "experimentalism":0.2}),
            QuizOption("often",      "Frequently — style is my self-expression",   scores={"experimentalism":0.9, "style_axis":0.7}),
            QuizOption("occasion",   "Only for new occasions or life events",       scores={"practicality":0.7, "experimentalism":0.4}),
        ],
    ),

    QuizQuestion(
        id="p6_compliment_preference",
        section="personality",
        index=5,
        type="single",
        question="What compliment would make your day?",
        options=[
            QuizOption("chic",       '"You always look so chic"',        scores={"structure_axis":0.8, "style_axis":0.2}),
            QuizOption("unique",     '"Your style is so unique"',         scores={"experimentalism":0.9, "style_axis":0.8}),
            QuizOption("put_together",'"You always look so put-together"',scores={"practicality":0.8, "structure_axis":0.7}),
            QuizOption("glowing",    '"You\'re literally glowing"',        scores={"romance_axis":0.7, "energy_axis":0.6}),
            QuizOption("effortless_q",'"How do you make it look so easy"',scores={"practicality":0.7, "structure_axis":0.3}),
        ],
    ),

    QuizQuestion(
        id="p7_getting_ready_time",
        section="personality",
        index=6,
        type="single",
        question="How long do you typically spend getting ready?",
        options=[
            QuizOption("under_10",  "Under 10 minutes",     scores={"practicality":0.9, "structure_axis":0.2}),
            QuizOption("15_30",     "15–30 minutes",         scores={"practicality":0.6, "structure_axis":0.5}),
            QuizOption("30_60",     "30–60 minutes",         scores={"practicality":0.3, "structure_axis":0.7}),
            QuizOption("over_60",   "Over an hour",          scores={"practicality":0.1, "energy_axis":0.7, "romance_axis":0.6}),
        ],
    ),

    # ═══════════════════════════════════════════════════════════
    # SECTION 2: FASHION PREFERENCE (8 questions)
    # ═══════════════════════════════════════════════════════════

    QuizQuestion(
        id="f1_silhouette",
        section="fashion",
        index=7,
        type="multi",
        question="Which silhouettes do you gravitate toward?",
        subtitle="Select all that apply",
        max_select=5,
        options=[
            QuizOption("fitted",       "Fitted & structured",         scores={"structure_axis":0.9}),
            QuizOption("flowy",        "Flowy & relaxed",              scores={"romance_axis":0.7, "structure_axis":0.1}),
            QuizOption("oversized",    "Oversized & relaxed",          scores={"practicality":0.6, "structure_axis":0.1}),
            QuizOption("bodycon",      "Body-hugging & confident",     scores={"energy_axis":0.9}),
            QuizOption("tailored",     "Tailored classics",            scores={"structure_axis":0.9, "style_axis":0.1}),
            QuizOption("asymmetric",   "Asymmetric & unexpected",      scores={"experimentalism":0.8, "style_axis":0.7}),
            QuizOption("layered",      "Layered & textural",           scores={"experimentalism":0.6, "romance_axis":0.5}),
        ],
    ),

    QuizQuestion(
        id="f2_color_comfort",
        section="fashion",
        index=8,
        type="single",
        question="What's your relationship with colour in clothing?",
        options=[
            QuizOption("neutrals_only",  "Mostly neutrals — black, white, grey, camel",  scores={"structure_axis":0.6, "style_axis":0.1}),
            QuizOption("earth_tones",    "Earth tones — rust, olive, terracotta",          scores={"romance_axis":0.6, "style_axis":0.3}),
            QuizOption("pastels",        "Soft pastels and dusty tones",                   scores={"romance_axis":0.8, "energy_axis":0.3}),
            QuizOption("rich_jewel",     "Rich jewel tones — emerald, sapphire, burgundy", scores={"energy_axis":0.7, "structure_axis":0.6}),
            QuizOption("bright_bold",    "Bright, saturated, and bold colours",            scores={"energy_axis":0.9, "experimentalism":0.8}),
            QuizOption("pattern_print",  "Patterns and prints over solid colours",         scores={"experimentalism":0.8, "energy_axis":0.6}),
        ],
    ),

    QuizQuestion(
        id="f3_fabric_texture",
        section="fashion",
        index=9,
        type="multi",
        question="Which fabrics and textures feel most like you?",
        subtitle="Select up to 3",
        max_select=3,
        options=[
            QuizOption("silk_satin",   "Silk & satin — smooth, luxurious",    scores={"romance_axis":0.7, "energy_axis":0.6}),
            QuizOption("cotton_linen", "Cotton & linen — clean and easy",      scores={"practicality":0.8, "structure_axis":0.3}),
            QuizOption("denim",        "Denim — classic, effortless",          scores={"practicality":0.7, "style_axis":0.2}),
            QuizOption("leather",      "Leather & faux leather — edgy",        scores={"style_axis":0.8, "energy_axis":0.8}),
            QuizOption("knitwear",     "Knitwear & cashmere — cosy, refined",  scores={"romance_axis":0.5, "practicality":0.6}),
            QuizOption("velvet",       "Velvet & brocade — opulent",           scores={"romance_axis":0.9, "energy_axis":0.6}),
            QuizOption("technical",    "Technical / performance fabrics",       scores={"practicality":0.9, "structure_axis":0.5}),
        ],
    ),

    QuizQuestion(
        id="f4_outfit_formula",
        section="fashion",
        index=10,
        type="single",
        question="What's your go-to outfit formula on a regular day?",
        options=[
            QuizOption("jeans_tee",        "Jeans + a great tee or top",            scores={"practicality":0.8, "structure_axis":0.3}),
            QuizOption("trousers_blazer",  "Tailored trousers + blazer",            scores={"structure_axis":0.9, "practicality":0.7}),
            QuizOption("dress_always",     "A dress — always",                      scores={"romance_axis":0.8, "energy_axis":0.5}),
            QuizOption("monochrome",       "A monochrome look, head-to-toe",        scores={"structure_axis":0.7, "style_axis":0.3}),
            QuizOption("mix_match",        "Mixing unexpected pieces",              scores={"experimentalism":0.9, "style_axis":0.7}),
            QuizOption("athletic_casual",  "Athletic or sporty pieces, elevated",   scores={"practicality":0.7, "energy_axis":0.7}),
        ],
    ),

    QuizQuestion(
        id="f5_accessories",
        section="fashion",
        index=11,
        type="single",
        question="How do you feel about accessories?",
        options=[
            QuizOption("minimal_acc",   "Less is more — one statement piece",     scores={"structure_axis":0.7, "style_axis":0.1}),
            QuizOption("stacked",       "I love to layer and stack jewellery",    scores={"energy_axis":0.7, "experimentalism":0.6}),
            QuizOption("bag_focused",   "A beautiful bag changes everything",      scores={"structure_axis":0.6, "romance_axis":0.5}),
            QuizOption("scarf_hat",     "Scarves, hats, belts — the details",    scores={"experimentalism":0.6, "romance_axis":0.6}),
            QuizOption("no_acc",        "I barely accessorize",                   scores={"practicality":0.8}),
        ],
    ),

    QuizQuestion(
        id="f6_inspiration_source",
        section="fashion",
        index=12,
        type="multi",
        question="Where do you get your style inspiration?",
        subtitle="Select all that apply",
        max_select=5,
        options=[
            QuizOption("instagram",    "Instagram & social media",        scores={"experimentalism":0.6}),
            QuizOption("street_style", "Street style / real people",       scores={"practicality":0.5, "experimentalism":0.5}),
            QuizOption("runways",      "Runway & fashion week",            scores={"experimentalism":0.9, "style_axis":0.7}),
            QuizOption("films",        "Films & period fashion",           scores={"romance_axis":0.6, "style_axis":0.4}),
            QuizOption("magazines",    "Fashion magazines",                scores={"experimentalism":0.5, "structure_axis":0.5}),
            QuizOption("nature",       "Art, nature, and travel",          scores={"romance_axis":0.7, "experimentalism":0.6}),
            QuizOption("own_instinct", "Purely my own instinct",           scores={"experimentalism":0.7, "energy_axis":0.6}),
        ],
    ),

    QuizQuestion(
        id="f7_body_comfort",
        section="fashion",
        index=13,
        type="single",
        question="What matters most when you get dressed?",
        options=[
            QuizOption("comfort_first", "Physical comfort above all",           scores={"practicality":0.9, "structure_axis":0.1}),
            QuizOption("confidence",    "Feeling confident and powerful",        scores={"energy_axis":0.8, "structure_axis":0.6}),
            QuizOption("compliments",   "Getting compliments",                   scores={"energy_axis":0.7, "experimentalism":0.5}),
            QuizOption("authentic",     "Expressing who I really am",            scores={"experimentalism":0.7, "energy_axis":0.5}),
            QuizOption("appropriate",   "Looking appropriate for the occasion",  scores={"practicality":0.7, "structure_axis":0.7}),
        ],
    ),

    QuizQuestion(
        id="f8_wardrobe_size",
        section="fashion",
        index=14,
        type="single",
        question="How would you describe your current wardrobe?",
        options=[
            QuizOption("capsule",     "Small and curated — everything works together",  scores={"structure_axis":0.8, "practicality":0.8}),
            QuizOption("full",        "Full of options — I like variety",               scores={"experimentalism":0.6, "energy_axis":0.5}),
            QuizOption("chaotic",     "A bit chaotic — hard to put together",           scores={"experimentalism":0.5}),
            QuizOption("growing",     "I'm building it — I have a vision",              scores={"structure_axis":0.5, "experimentalism":0.5}),
        ],
    ),

    # ═══════════════════════════════════════════════════════════
    # SECTION 3: LIFESTYLE & OCCASIONS (7 questions)
    # ═══════════════════════════════════════════════════════════

    QuizQuestion(
        id="l1_primary_occupation",
        section="lifestyle",
        index=15,
        type="single",
        question="Which best describes your day-to-day life?",
        options=[
            QuizOption("corporate",   "Corporate / office environment",       scores={"structure_axis":0.8, "occasion_work":0.7}),
            QuizOption("creative_pro","Creative professional (design/media)",  scores={"experimentalism":0.7, "occasion_work":0.5}),
            QuizOption("student",     "Student",                               scores={"practicality":0.7, "occasion_casual":0.6}),
            QuizOption("home_parent", "Home / parenting focused",              scores={"practicality":0.8, "occasion_casual":0.7}),
            QuizOption("entrepreneur","Entrepreneur / freelancer",             scores={"experimentalism":0.6, "occasion_work":0.4}),
            QuizOption("social",      "Active social / events lifestyle",      scores={"energy_axis":0.7, "occasion_evening":0.5}),
            QuizOption("athletic",    "Athletic / outdoor lifestyle",          scores={"practicality":0.8, "occasion_casual":0.6}),
        ],
    ),

    QuizQuestion(
        id="l2_social_calendar",
        section="lifestyle",
        index=16,
        type="scale",
        question="How active is your social calendar?",
        scale_min=0,
        scale_max=10,
        scale_labels=("Mostly quiet/homebody", "Out every weekend"),
    ),

    QuizQuestion(
        id="l3_occasion_split",
        section="lifestyle",
        index=17,
        type="single",
        question="If you had to split 10 outfit days, how would it look?",
        options=[
            QuizOption("7w_2c_1e",  "7 work + 2 casual + 1 evening",     scores={"occasion_work":0.7, "occasion_casual":0.2, "occasion_evening":0.1}),
            QuizOption("3w_5c_2e",  "3 work + 5 casual + 2 evening",     scores={"occasion_work":0.3, "occasion_casual":0.5, "occasion_evening":0.2}),
            QuizOption("2w_6c_2e",  "2 work + 6 casual + 2 evening",     scores={"occasion_work":0.2, "occasion_casual":0.6, "occasion_evening":0.2}),
            QuizOption("1w_4c_5e",  "1 work + 4 casual + 5 evening",     scores={"occasion_work":0.1, "occasion_casual":0.4, "occasion_evening":0.5}),
            QuizOption("0w_8c_2e",  "Mostly casual with some evenings",   scores={"occasion_work":0.0, "occasion_casual":0.8, "occasion_evening":0.2}),
        ],
    ),

    QuizQuestion(
        id="l4_travel_style",
        section="lifestyle",
        index=18,
        type="single",
        question="How would you describe your travel style?",
        options=[
            QuizOption("light_pack",   "One carry-on, maximum versatility",    scores={"practicality":0.9, "structure_axis":0.6}),
            QuizOption("destination",  "I dress for each destination",          scores={"experimentalism":0.7, "romance_axis":0.6}),
            QuizOption("luxury_hotel", "Black-tie ready for any hotel bar",     scores={"energy_axis":0.7, "romance_axis":0.7}),
            QuizOption("adventure",    "Function over fashion — I'm outdoors",  scores={"practicality":0.8}),
            QuizOption("influencer",   "Every location is a photoshoot",        scores={"energy_axis":0.8, "experimentalism":0.7}),
        ],
    ),

    QuizQuestion(
        id="l5_fitness_lifestyle",
        section="lifestyle",
        index=19,
        type="single",
        question="What's your relationship with fitness and activewear?",
        options=[
            QuizOption("gym_daily",   "Gym is part of my daily routine",          scores={"practicality":0.7, "lifestyle_athletic":1.0}),
            QuizOption("yoga_pilates","Yoga / pilates — movement is self-care",   scores={"romance_axis":0.5, "practicality":0.6}),
            QuizOption("outdoor",     "Hiking, running, outdoor sports",          scores={"practicality":0.8, "lifestyle_athletic":1.0}),
            QuizOption("occasional",  "I work out occasionally",                  scores={"practicality":0.4}),
            QuizOption("rarely",      "Rarely — wellness for me is different",    scores={"practicality":0.2}),
        ],
    ),

    QuizQuestion(
        id="l6_lifestyle_values",
        section="lifestyle",
        index=20,
        type="multi",
        question="Which values define your lifestyle choices?",
        subtitle="Select up to 3",
        max_select=3,
        options=[
            QuizOption("sustainable",  "Sustainability & ethics",      scores={"practicality":0.5, "lifestyle_sustainable":1.0}),
            QuizOption("luxury_value", "Quality over quantity",         scores={"structure_axis":0.7}),
            QuizOption("trend",        "Staying ahead of trends",       scores={"experimentalism":0.8}),
            QuizOption("comfort_life", "Comfort and ease",              scores={"practicality":0.8}),
            QuizOption("self_express", "Self-expression",               scores={"energy_axis":0.7, "experimentalism":0.7}),
            QuizOption("professional", "Professional image",            scores={"structure_axis":0.8, "occasion_work":0.6}),
            QuizOption("minimalism",   "Minimalism and intentionality", scores={"structure_axis":0.6, "practicality":0.7}),
        ],
    ),

    QuizQuestion(
        id="l7_seasons_preference",
        section="lifestyle",
        index=21,
        type="single",
        question="Which season inspires your best outfits?",
        options=[
            QuizOption("spring", "Spring — fresh layers and florals",           scores={"romance_axis":0.7, "energy_axis":0.5}),
            QuizOption("summer", "Summer — light, bright and effortless",       scores={"practicality":0.6, "energy_axis":0.6}),
            QuizOption("autumn", "Autumn — layering and rich textures",         scores={"romance_axis":0.8, "structure_axis":0.6}),
            QuizOption("winter", "Winter — cosy maximalism or sleek minimal",   scores={"energy_axis":0.6, "structure_axis":0.7}),
        ],
    ),

    # ═══════════════════════════════════════════════════════════
    # SECTION 4: BUDGET & SHOPPING (6 questions)
    # ═══════════════════════════════════════════════════════════

    QuizQuestion(
        id="b1_monthly_budget",
        section="budget",
        index=22,
        type="single",
        question="What's your typical monthly beauty & fashion spend?",
        options=[
            QuizOption("under_2k",   "Under ₹2,000",        scores={"budget_tier":"budget",  "practicality":0.8}),
            QuizOption("2k_5k",      "₹2,000–₹5,000",       scores={"budget_tier":"low_mid", "practicality":0.6}),
            QuizOption("5k_15k",     "₹5,000–₹15,000",      scores={"budget_tier":"mid",     "practicality":0.4}),
            QuizOption("15k_30k",    "₹15,000–₹30,000",     scores={"budget_tier":"mid_high","practicality":0.2}),
            QuizOption("over_30k",   "Over ₹30,000",         scores={"budget_tier":"luxury",  "practicality":0.1}),
        ],
    ),

    QuizQuestion(
        id="b2_splurge_vs_save",
        section="budget",
        index=23,
        type="multi",
        question="Where would you happily splurge vs. save?",
        subtitle="Select where you SPLURGE (up to 3)",
        max_select=3,
        options=[
            QuizOption("bags",       "Bags & handbags",   scores={"energy_axis":0.6}),
            QuizOption("skincare",   "Skincare",           scores={"practicality":0.5}),
            QuizOption("shoes",      "Shoes",              scores={"structure_axis":0.6}),
            QuizOption("fragrance",  "Fragrance",          scores={"romance_axis":0.6}),
            QuizOption("basics",     "Core wardrobe basics",scores={"structure_axis":0.7}),
            QuizOption("statement",  "Statement pieces",   scores={"energy_axis":0.7}),
            QuizOption("jewellery",  "Jewellery",          scores={"romance_axis":0.5}),
        ],
    ),

    QuizQuestion(
        id="b3_brand_loyalty",
        section="budget",
        index=24,
        type="single",
        question="How do you feel about brands?",
        options=[
            QuizOption("brand_loyal",   "I'm loyal to a few trusted brands",        scores={"structure_axis":0.6, "practicality":0.6}),
            QuizOption("logo_lover",    "I love visible logos — they signal quality",scores={"energy_axis":0.7}),
            QuizOption("indie_seeker",  "I actively seek out indie and niche brands",scores={"experimentalism":0.8}),
            QuizOption("no_loyalty",    "Brand doesn't matter — quality does",       scores={"practicality":0.7}),
            QuizOption("mix_always",    "I mix luxury with high-street freely",      scores={"experimentalism":0.6, "practicality":0.5}),
        ],
    ),

    QuizQuestion(
        id="b4_shopping_trigger",
        section="budget",
        index=25,
        type="single",
        question="What triggers a shopping trip for you?",
        options=[
            QuizOption("need_based",   "A specific gap or need",               scores={"practicality":0.9}),
            QuizOption("mood_based",   "When I'm in the mood",                  scores={"energy_axis":0.6, "experimentalism":0.5}),
            QuizOption("sale_triggered","Sales, offers, and deals",             scores={"practicality":0.7}),
            QuizOption("trend_pull",   "A trend I can't resist",                scores={"experimentalism":0.7}),
            QuizOption("ritual",       "It's a ritual — I shop regularly",     scores={"romance_axis":0.5, "energy_axis":0.5}),
        ],
    ),

    QuizQuestion(
        id="b5_investment_mindset",
        section="budget",
        index=26,
        type="scale",
        question="How do you view fashion investment?",
        scale_min=0,
        scale_max=10,
        scale_labels=("Never spend on it", "It's an investment in self"),
    ),

    QuizQuestion(
        id="b6_sustainable_mindset",
        section="budget",
        index=27,
        type="single",
        question="How much does sustainability influence your choices?",
        options=[
            QuizOption("always",   "It's my top priority",                         scores={"lifestyle_sustainable":1.0, "practicality":0.5}),
            QuizOption("usually",  "I try to choose sustainably when I can",        scores={"lifestyle_sustainable":0.7}),
            QuizOption("sometimes","I consider it but price/quality comes first",   scores={"lifestyle_sustainable":0.4}),
            QuizOption("rarely",   "Rarely — I prioritize other factors",           scores={"lifestyle_sustainable":0.1}),
        ],
    ),

    # ═══════════════════════════════════════════════════════════
    # SECTION 5: BEAUTY & FRAGRANCE (7 questions)
    # ═══════════════════════════════════════════════════════════

    QuizQuestion(
        id="bq1_makeup_style",
        section="beauty",
        index=28,
        type="single",
        question="How would you describe your everyday makeup?",
        options=[
            QuizOption("no_makeup",   "No makeup — bare is beautiful",            scores={"practicality":0.8, "energy_axis":0.2}),
            QuizOption("skin_focus",  "Skincare-focused — skin texture, no cover", scores={"practicality":0.7, "romance_axis":0.4}),
            QuizOption("natural",     "Natural and enhancing — barely-there",      scores={"romance_axis":0.7, "structure_axis":0.4}),
            QuizOption("glam_lite",   "Polished — full face, natural finish",      scores={"structure_axis":0.7, "energy_axis":0.5}),
            QuizOption("bold_glam",   "Bold — statement lips or eyes",             scores={"energy_axis":0.9, "experimentalism":0.7}),
            QuizOption("creative_mu", "Artistic — colour and creative looks",      scores={"experimentalism":0.9, "style_axis":0.7}),
        ],
    ),

    QuizQuestion(
        id="bq2_skincare_priority",
        section="beauty",
        index=29,
        type="multi",
        question="What are your top skincare goals?",
        subtitle="Select up to 3",
        max_select=3,
        options=[
            QuizOption("glow",      "Luminous, glowy skin",      scores={"romance_axis":0.5}),
            QuizOption("clear",     "Clear, acne-free skin",      scores={"practicality":0.6}),
            QuizOption("anti_age",  "Anti-aging & firmness",      scores={"practicality":0.5}),
            QuizOption("even_tone", "Even skin tone",             scores={"structure_axis":0.5}),
            QuizOption("hydration", "Deep hydration",             scores={"romance_axis":0.4}),
            QuizOption("minimal_sk","Minimal routine",            scores={"practicality":0.8}),
        ],
    ),

    QuizQuestion(
        id="bq3_fragrance_personality",
        section="beauty",
        index=30,
        type="single",
        question="Your signature fragrance should smell like…",
        options=[
            QuizOption("just_showered", "Just showered — clean and fresh",          scores={"practicality":0.7, "structure_axis":0.5}),
            QuizOption("rose_garden",   "A blooming rose garden",                   scores={"romance_axis":0.9}),
            QuizOption("dark_incense",  "Smoky oud and dark incense",               scores={"energy_axis":0.8, "style_axis":0.7}),
            QuizOption("sunny_citrus",  "Sunny citrus and light woods",             scores={"energy_axis":0.6, "practicality":0.6}),
            QuizOption("warm_vanilla",  "Warm vanilla and creamy musk",             scores={"romance_axis":0.8, "energy_axis":0.4}),
            QuizOption("green_woods",   "Mossy green and fresh woods",              scores={"experimentalism":0.5, "practicality":0.5}),
        ],
    ),

    QuizQuestion(
        id="bq4_hair_attitude",
        section="beauty",
        index=31,
        type="single",
        question="What's your relationship with your hair?",
        options=[
            QuizOption("low_maint",  "Low-maintenance — I keep it simple",          scores={"practicality":0.9}),
            QuizOption("signature",  "It's my signature — I'm known for my hair",   scores={"energy_axis":0.8, "romance_axis":0.5}),
            QuizOption("experiment", "I love experimenting — colour, cuts, styles", scores={"experimentalism":0.9}),
            QuizOption("occasion",   "I style it for occasions, simple day-to-day", scores={"practicality":0.6, "energy_axis":0.5}),
            QuizOption("natural",    "I embrace my natural texture completely",      scores={"romance_axis":0.7, "practicality":0.6}),
        ],
    ),

    QuizQuestion(
        id="bq5_beauty_ritual",
        section="beauty",
        index=32,
        type="single",
        question="How do you view your beauty routine?",
        options=[
            QuizOption("self_care",   "Sacred self-care ritual",              scores={"romance_axis":0.9, "energy_axis":0.4}),
            QuizOption("discipline",  "Part of daily discipline",             scores={"structure_axis":0.8, "practicality":0.6}),
            QuizOption("creative",    "Creative expression and play",         scores={"experimentalism":0.8, "energy_axis":0.7}),
            QuizOption("necessary",   "Necessary but I keep it quick",        scores={"practicality":0.9}),
            QuizOption("evolving",    "I'm still discovering what works",     scores={"experimentalism":0.5}),
        ],
    ),

    QuizQuestion(
        id="bq6_fragrance_intensity",
        section="beauty",
        index=33,
        type="single",
        question="How do you like your fragrance to perform?",
        options=[
            QuizOption("intimate",       "Just for me — intimate sillage",          scores={"romance_axis":0.6, "practicality":0.5}),
            QuizOption("compliment",     "So people notice as I pass",              scores={"energy_axis":0.7}),
            QuizOption("trail",          "I want to leave a trail",                 scores={"energy_axis":0.9, "experimentalism":0.5}),
            QuizOption("all_day",        "All-day presence without overpowering",   scores={"practicality":0.7, "structure_axis":0.5}),
            QuizOption("context_dep",    "It depends on the occasion",              scores={"practicality":0.6, "structure_axis":0.6}),
        ],
    ),

    QuizQuestion(
        id="bq7_beauty_icon",
        section="beauty",
        index=34,
        type="single",
        question="Which beauty icon inspires your aesthetic?",
        options=[
            QuizOption("audrey_hb",    "Audrey Hepburn — classic cat eye",          scores={"style_axis":0.1, "structure_axis":0.8}),
            QuizOption("beyonce",      "Beyoncé — powerful, glam",                  scores={"energy_axis":0.9, "romance_axis":0.6}),
            QuizOption("adwoa",        "Adwoa Aboah — androgynous, cool",           scores={"style_axis":0.7, "experimentalism":0.8}),
            QuizOption("deepika",      "Deepika Padukone — timeless beauty",        scores={"style_axis":0.2, "romance_axis":0.7}),
            QuizOption("bjork",        "Björk — artistic, avant-garde",             scores={"experimentalism":0.9, "style_axis":0.9}),
            QuizOption("hailey",       "Hailey Bieber — clean girl aesthetic",      scores={"practicality":0.7, "structure_axis":0.4}),
        ],
    ),
]

# ── Dimension computation ─────────────────────────────────────────────────────

DIMENSION_KEYS = [
    "style_axis", "energy_axis", "structure_axis", "romance_axis",
    "practicality", "experimentalism",
    "occasion_work", "occasion_casual", "occasion_evening",
]

LIFESTYLE_TAGS = {
    "lifestyle_athletic":   "active",
    "lifestyle_sustainable":"sustainable",
}


def compute_dimensions(responses: list[dict]) -> dict:
    """
    Aggregate quiz responses into normalised dimension scores.
    responses: list of {question_id, answer_value, answer_options, answer_scores}
    Returns dict of dimension → float [0, 1]
    """
    totals: dict[str, float] = {k: 0.0 for k in DIMENSION_KEYS}
    counts: dict[str, int]   = {k: 0   for k in DIMENSION_KEYS}
    budget_tier = "mid"
    lifestyle_tags: list[str] = []

    for resp in responses:
        scores = resp.get("answer_scores") or {}
        if not scores:
            continue

        # Handle budget tier (special string value)
        if "budget_tier" in scores:
            budget_tier = scores["budget_tier"]

        # Handle lifestyle tags
        for tag_key, tag_value in LIFESTYLE_TAGS.items():
            if scores.get(tag_key, 0) >= 0.8:
                if tag_value not in lifestyle_tags:
                    lifestyle_tags.append(tag_value)

        for dim in DIMENSION_KEYS:
            if dim in scores:
                totals[dim] += scores[dim]
                counts[dim] += 1

    # Scale normalisations
    scale_questions = {"p4_confidence_expression", "l2_social_calendar", "b5_investment_mindset"}
    for resp in responses:
        if resp.get("question_id") in scale_questions and resp.get("answer_value"):
            try:
                val = float(resp["answer_value"]) / 10.0  # Scale is 0-10
                qid = resp["question_id"]
                if qid == "p4_confidence_expression":
                    totals["energy_axis"] += val
                    counts["energy_axis"] += 1
                elif qid == "l2_social_calendar":
                    totals["occasion_evening"] += val * 0.4
                    counts["occasion_evening"] += 1
                elif qid == "b5_investment_mindset":
                    pass  # Used in budget context not dimensions
            except (ValueError, TypeError):
                pass

    # Normalise to [0, 1]
    dimensions = {}
    for dim in DIMENSION_KEYS:
        if counts[dim] > 0:
            raw = totals[dim] / counts[dim]
            dimensions[dim] = round(min(max(raw, 0.0), 1.0), 4)
        else:
            dimensions[dim] = 0.5  # Neutral default

    # Normalise occasion proportions to sum to 1
    occ_sum = dimensions["occasion_work"] + dimensions["occasion_casual"] + dimensions["occasion_evening"]
    if occ_sum > 0:
        dimensions["occasion_work"]    = round(dimensions["occasion_work"]    / occ_sum, 3)
        dimensions["occasion_casual"]  = round(dimensions["occasion_casual"]  / occ_sum, 3)
        dimensions["occasion_evening"] = round(dimensions["occasion_evening"] / occ_sum, 3)

    return {
        "dimensions":    dimensions,
        "budget_tier":   budget_tier,
        "lifestyle_tags":lifestyle_tags,
    }


# ── Archetype classification ──────────────────────────────────────────────────

ARCHETYPES = {
    "The Classic":       {"style_axis": (0.0, 0.3), "structure_axis": (0.6, 1.0), "energy_axis": (0.2, 0.6)},
    "The Minimalist":    {"style_axis": (0.0, 0.3), "structure_axis": (0.5, 1.0), "energy_axis": (0.0, 0.4)},
    "The Romantic":      {"romance_axis": (0.7, 1.0), "energy_axis": (0.2, 0.7)},
    "The Bohemian":      {"experimentalism": (0.5, 1.0), "romance_axis": (0.5, 1.0), "structure_axis": (0.0, 0.5)},
    "The Edgy":          {"style_axis": (0.6, 1.0), "energy_axis": (0.7, 1.0), "structure_axis": (0.2, 0.6)},
    "The Athletic":      {"practicality": (0.7, 1.0), "structure_axis": (0.4, 0.8)},
    "The Glamorous":     {"energy_axis": (0.7, 1.0), "romance_axis": (0.5, 1.0), "structure_axis": (0.5, 1.0)},
    "The Preppy":        {"structure_axis": (0.7, 1.0), "style_axis": (0.0, 0.3), "practicality": (0.5, 1.0)},
    "The Creative":      {"experimentalism": (0.7, 1.0), "style_axis": (0.5, 1.0)},
    "The Sophisticated": {"structure_axis": (0.7, 1.0), "energy_axis": (0.4, 0.8), "style_axis": (0.0, 0.4)},
    "The Casual":        {"practicality": (0.7, 1.0), "energy_axis": (0.0, 0.5), "structure_axis": (0.0, 0.4)},
    "The Eclectic":      {"experimentalism": (0.6, 1.0), "style_axis": (0.4, 0.8), "romance_axis": (0.4, 0.7)},
}


def classify_archetypes(dimensions: dict) -> tuple[str, str]:
    """
    Return (primary_archetype, secondary_archetype) from dimension scores.
    Uses a range-matching approach: count how many axis ranges each archetype satisfies.
    """
    scores = {}
    for archetype, axis_ranges in ARCHETYPES.items():
        matches = 0
        total   = len(axis_ranges)
        for axis, (lo, hi) in axis_ranges.items():
            val = dimensions.get(axis, 0.5)
            if lo <= val <= hi:
                matches += 1
        scores[archetype] = matches / total

    ranked = sorted(scores, key=lambda k: scores[k], reverse=True)
    primary   = ranked[0] if ranked       else "The Classic"
    secondary = ranked[1] if len(ranked) > 1 else "The Minimalist"
    return primary, secondary
