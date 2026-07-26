"use client";
/**
 * AuraFit — Wardrobe AI page (Stage 9).
 * Upload clothes → auto-categorize → AI outfit generation → capsule analysis.
 */
import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, Plus, Shirt, Sparkles, BarChart3,
  Loader2, X, ChevronRight, ShoppingBag, Star,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { GoldDivider } from "@/components/shared/GoldDivider";
import { wardrobeAIApi } from "@/lib/api/stage9";
import type {
  WardrobeItemLocal, WardrobeItemClassification,
  AIOutfit, CapsuleAnalysis, ClothingCategory,
} from "@/types/stage9";
import { CATEGORY_META } from "@/types/stage9";

const anim = (i = 0) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: i * 0.06, duration: 0.4, ease: [0.23, 1, 0.32, 1] as const },
});

export default function WardrobePage() {
  const fileRef = useRef<HTMLInputElement>(null);

  const [items,       setItems]       = useState<WardrobeItemLocal[]>([]);
  const [outfits,     setOutfits]     = useState<AIOutfit[]>([]);
  const [capsule,     setCapsule]     = useState<CapsuleAnalysis | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating,setIsGenerating]= useState(false);
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<string[]>([]);
  const [occasion,    setOccasion]    = useState("casual");
  const [season,      setSeason]      = useState("all-season");
  const [error,       setError]       = useState<string | null>(null);

  // ── Upload + classify ────────────────────────────────────────────────────────

  const handleFileDrop = useCallback(async (files: FileList) => {
    setIsUploading(true);
    setError(null);
    const newItems: WardrobeItemLocal[] = [];
    for (const file of Array.from(files)) {
      const id      = `local-${Date.now()}-${Math.random()}`;
      const preview = URL.createObjectURL(file);
      setUploadQueue((q) => [...q, id]);
      try {
        const cls: WardrobeItemClassification = await wardrobeAIApi.classifyItem(file);
        newItems.push({
          id,
          name:         cls.subcategory || "Item",
          category:     cls.category as ClothingCategory,
          image_url:    preview,
          color_tags:   cls.dominant_colors,
          occasion_tags:cls.occasion_tags,
          season_tags:  cls.season_tags,
          style_tags:   cls.style_tags,
          times_worn:   0,
        });
      } catch {
        newItems.push({ id, name: "Item", image_url: preview });
      } finally {
        setUploadQueue((q) => q.filter((x) => x !== id));
      }
    }
    setItems((prev) => [...prev, ...newItems]);
    setIsUploading(false);
  }, []);

  const removeItem = (id: string) =>
    setItems((prev) => prev.filter((i) => i.id !== id));

  // ── Outfit generation ────────────────────────────────────────────────────────

  const generateOutfits = async () => {
    if (items.length < 2) return setError("Add at least 2 wardrobe items to generate outfits.");
    setIsGenerating(true);
    setError(null);
    try {
      const suggestions = await wardrobeAIApi.generateOutfits({
        wardrobe_items: items.map((i) => ({
          id:            i.id,
          category:      i.category,
          image_url:     i.image_url,
          custom_name:   i.name,
          color_tags:    i.color_tags,
          occasion_tags: i.occasion_tags,
          season_tags:   i.season_tags,
          style_tags:    i.style_tags,
          times_worn:    i.times_worn ?? 0,
        })),
        occasion,
        season,
        limit: 5,
      });
      setOutfits(suggestions);
    } catch (err: any) {
      setError(err.message ?? "Outfit generation failed.");
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Capsule analysis ──────────────────────────────────────────────────────────

  const analyseCapsule = async () => {
    if (items.length === 0) return setError("Add wardrobe items first.");
    setIsAnalysing(true);
    setError(null);
    try {
      const result = await wardrobeAIApi.analyseCapsule({
        wardrobe_items: items.map((i) => ({
          id: i.id, category: i.category, custom_name: i.name,
          color_tags: i.color_tags, times_worn: i.times_worn, cost: i.cost,
        })),
      });
      setCapsule(result);
    } catch (err: any) {
      setError(err.message ?? "Analysis failed.");
    } finally {
      setIsAnalysing(false);
    }
  };

  // ── Category counts ───────────────────────────────────────────────────────────

  const catCounts = items.reduce<Record<string, number>>((acc, i) => {
    const c = i.category ?? "other";
    acc[c] = (acc[c] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-16">
      {/* Header */}
      <motion.div {...anim(0)} className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-2xs uppercase tracking-widest text-brand-gold/70">
            <Shirt className="h-3.5 w-3.5" /> Wardrobe AI
          </div>
          <h1 className="font-display text-display-md font-light tracking-tightest">
            Your Digital Wardrobe
          </h1>
          <p className="text-sm text-muted-foreground">
            Upload your clothes, get AI-categorized wardrobe, outfit suggestions, and capsule analysis.
          </p>
        </div>
        <Badge className="text-sm px-4 py-1.5">{items.length} items</Badge>
      </motion.div>

      <GoldDivider />

      {/* Upload dropzone */}
      <motion.div {...anim(1)}>
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); handleFileDrop(e.dataTransfer.files); }}
          onClick={() => fileRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded-3xl p-10 text-center cursor-pointer transition-all",
            "border-white/[0.10] hover:border-brand-gold/40 hover:bg-brand-gold/5",
            isUploading && "opacity-60 pointer-events-none"
          )}
        >
          {isUploading ? (
            <div className="space-y-3">
              <Loader2 className="h-8 w-8 text-brand-gold animate-spin mx-auto" />
              <p className="text-sm text-muted-foreground">
                Classifying {uploadQueue.length} item(s)…
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="h-12 w-12 mx-auto rounded-2xl bg-brand-gold/10 flex items-center justify-center">
                <Plus className="h-6 w-6 text-brand-gold" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">Drop clothing photos here</p>
                <p className="text-xs text-muted-foreground/50 mt-1">
                  or click to upload · JPEG, PNG · AI auto-classifies each item
                </p>
              </div>
            </div>
          )}
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleFileDrop(e.target.files)}
        />
      </motion.div>

      {error && (
        <p className="text-sm text-destructive rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3">
          {error}
        </p>
      )}

      {/* Wardrobe grid + AI panels */}
      {items.length > 0 && (
        <motion.div {...anim(2)}>
          <Tabs defaultValue="wardrobe" className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <TabsList>
                <TabsTrigger value="wardrobe" className="gap-2">
                  <Shirt className="h-3.5 w-3.5" /> Wardrobe
                </TabsTrigger>
                <TabsTrigger value="outfits" className="gap-2">
                  <Sparkles className="h-3.5 w-3.5" /> Outfits
                </TabsTrigger>
                <TabsTrigger value="capsule" className="gap-2">
                  <BarChart3 className="h-3.5 w-3.5" /> Capsule
                </TabsTrigger>
              </TabsList>

              <div className="flex gap-2">
                <Button variant="ghost-gold" size="sm" onClick={generateOutfits}
                  loading={isGenerating} className="gap-2">
                  <Sparkles className="h-4 w-4" /> Generate Outfits
                </Button>
                <Button variant="ghost" size="sm" onClick={analyseCapsule}
                  loading={isAnalysing} className="gap-2">
                  <BarChart3 className="h-4 w-4" /> Capsule Analysis
                </Button>
              </div>
            </div>

            {/* Wardrobe grid */}
            <TabsContent value="wardrobe">
              {/* Category summary */}
              {Object.keys(catCounts).length > 0 && (
                <div className="flex flex-wrap gap-2 mb-5">
                  {Object.entries(catCounts).map(([cat, count]) => {
                    const meta = CATEGORY_META[cat as ClothingCategory];
                    return (
                      <div key={cat} className="flex items-center gap-1.5 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-1.5">
                        <span>{meta?.emoji ?? "👔"}</span>
                        <span className={cn("text-xs font-medium", meta?.color ?? "text-muted-foreground")}>
                          {meta?.label ?? cat}
                        </span>
                        <Badge className="text-2xs">{count}</Badge>
                      </div>
                    );
                  })}
                </div>
              )}

              <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                <AnimatePresence>
                  {items.map((item, i) => (
                    <motion.div
                      key={item.id}
                      {...anim(i * 0.03)}
                      className="group relative luxury-card overflow-hidden"
                    >
                      {/* Image */}
                      <div className="relative aspect-square overflow-hidden bg-white/[0.03]">
                        {item.image_url && (
                          <img src={item.image_url} alt={item.name}
                            className="w-full h-full object-cover" />
                        )}
                        {/* Remove button */}
                        <button
                          onClick={() => removeItem(item.id)}
                          className="absolute top-2 right-2 h-6 w-6 rounded-full bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <X className="h-3 w-3 text-white" />
                        </button>
                      </div>
                      {/* Info */}
                      <div className="p-3 space-y-1.5">
                        <div className="flex items-center gap-1.5">
                          {item.category && (
                            <span className="text-base">
                              {CATEGORY_META[item.category]?.emoji ?? "👔"}
                            </span>
                          )}
                          <p className="text-xs font-medium text-foreground line-clamp-1 capitalize">
                            {item.name}
                          </p>
                        </div>
                        {item.color_tags && item.color_tags.length > 0 && (
                          <div className="flex gap-1">
                            {item.color_tags.slice(0, 3).map((hex) => (
                              <div
                                key={hex}
                                className="h-3 w-3 rounded-full ring-1 ring-white/20"
                                style={{ backgroundColor: hex }}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </TabsContent>

            {/* Outfit suggestions */}
            <TabsContent value="outfits">
              {outfits.length === 0 ? (
                <div className="luxury-card p-12 text-center space-y-4">
                  <div className="h-16 w-16 mx-auto rounded-2xl bg-brand-gold/10 flex items-center justify-center">
                    <Sparkles className="h-8 w-8 text-brand-gold/60" />
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm text-foreground font-medium">No outfits generated yet</p>
                    <p className="text-xs text-muted-foreground/50">
                      Click "Generate Outfits" to get AI outfit combinations
                    </p>
                  </div>
                  <div className="flex gap-3 justify-center flex-wrap">
                    <select value={occasion} onChange={(e) => setOccasion(e.target.value)}
                      className="input-luxury text-sm">
                      {["casual","work","evening","weekend","sport"].map((o) => (
                        <option key={o} value={o} className="capitalize">{o}</option>
                      ))}
                    </select>
                    <select value={season} onChange={(e) => setSeason(e.target.value)}
                      className="input-luxury text-sm">
                      {["all-season","spring","summer","autumn","winter"].map((s) => (
                        <option key={s} value={s} className="capitalize">{s}</option>
                      ))}
                    </select>
                  </div>
                  <Button variant="gold" onClick={generateOutfits} loading={isGenerating} className="gap-2">
                    <Sparkles className="h-4 w-4" /> Generate Outfits
                  </Button>
                </div>
              ) : (
                <div className="space-y-5">
                  {outfits.map((outfit, i) => (
                    <motion.div key={outfit.outfit_id} {...anim(i * 0.08)}
                      className="luxury-card p-5 space-y-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <Badge variant="default" className="text-2xs capitalize">{outfit.occasion}</Badge>
                            <Badge variant="default" className="text-2xs capitalize">{outfit.color_harmony}</Badge>
                            <span className="text-2xs text-brand-gold flex items-center gap-0.5">
                              <Star className="h-3 w-3 fill-brand-gold" />
                              {Math.round(outfit.ai_score * 100)}%
                            </span>
                          </div>
                          <p className="text-sm text-muted-foreground/60">{outfit.explanation}</p>
                        </div>
                      </div>
                      {/* Outfit items strip */}
                      <div className="flex gap-3 overflow-x-auto pb-1 hide-scrollbar">
                        {outfit.items.map((item) => {
                          const localItem = items.find((i) => i.id === item.wardrobe_item_id);
                          const meta = CATEGORY_META[item.category as ClothingCategory];
                          return (
                            <div key={item.wardrobe_item_id} className="flex-shrink-0 text-center space-y-1.5">
                              <div className="h-20 w-16 rounded-xl overflow-hidden bg-white/[0.03] ring-1 ring-white/[0.06]">
                                {localItem?.image_url && (
                                  <img src={localItem.image_url} alt={item.name}
                                    className="w-full h-full object-cover" />
                                )}
                                {!localItem?.image_url && (
                                  <div className="w-full h-full flex items-center justify-center">
                                    <span className="text-2xl">{meta?.emoji ?? "👔"}</span>
                                  </div>
                                )}
                              </div>
                              <p className="text-2xs text-muted-foreground/50 w-16 line-clamp-1">
                                {item.name || meta?.label}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Capsule analysis */}
            <TabsContent value="capsule">
              {!capsule ? (
                <div className="luxury-card p-12 text-center space-y-4">
                  <div className="h-16 w-16 mx-auto rounded-2xl bg-brand-gold/10 flex items-center justify-center">
                    <BarChart3 className="h-8 w-8 text-brand-gold/60" />
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm text-foreground font-medium">Capsule Analysis</p>
                    <p className="text-xs text-muted-foreground/50 max-w-sm mx-auto">
                      Analyses your wardrobe completeness, missing essentials,
                      cost-per-wear, and builds a prioritised shopping list.
                    </p>
                  </div>
                  <Button variant="gold" onClick={analyseCapsule} loading={isAnalysing} className="gap-2">
                    <BarChart3 className="h-4 w-4" /> Analyse My Capsule
                  </Button>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Score */}
                  <div className="luxury-card p-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-2xs uppercase tracking-widest text-muted-foreground/40 mb-1">
                          Capsule Score
                        </p>
                        <p className="text-3xl font-display font-light">
                          {capsule.capsule_score}
                          <span className="text-lg text-muted-foreground/40">/100</span>
                        </p>
                      </div>
                      <div className="text-right text-xs text-muted-foreground/50 space-y-1">
                        <p>{capsule.total_items} total items</p>
                        <p>₹{capsule.total_value.toLocaleString()} estimated value</p>
                      </div>
                    </div>
                    <Progress value={capsule.capsule_score} gold className="h-2" />
                    <p className="text-xs text-muted-foreground/60">
                      {capsule.capsule_score >= 80 ? "Excellent capsule wardrobe! Very complete." :
                       capsule.capsule_score >= 60 ? "Good foundation. A few key pieces will complete it." :
                       "Building up — focus on the priority essentials first."}
                    </p>
                  </div>

                  <div className="grid gap-6 sm:grid-cols-2">
                    {/* Missing essentials */}
                    {capsule.missing_essentials.length > 0 && (
                      <div className="luxury-card p-5 space-y-4">
                        <p className="text-sm font-semibold text-foreground">Missing Essentials</p>
                        <div className="space-y-2">
                          {capsule.missing_essentials.slice(0, 6).map((m, i) => (
                            <div key={i} className="flex items-start gap-2.5">
                              <span className={cn("mt-0.5 text-xs", m.priority === 1 ? "text-rose-400" : "text-amber-400")}>
                                {m.priority === 1 ? "★" : "☆"}
                              </span>
                              <div>
                                <p className="text-sm text-foreground/80">{m.item}</p>
                                <p className="text-2xs text-muted-foreground/40 capitalize">{m.category}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Shopping list */}
                    {capsule.shopping_list.length > 0 && (
                      <div className="luxury-card p-5 space-y-4">
                        <p className="text-sm font-semibold text-foreground">Shopping Priority List</p>
                        <div className="space-y-2">
                          {capsule.shopping_list.slice(0, 6).map((s, i) => (
                            <div key={i} className="flex items-center gap-2.5">
                              <span className="text-2xs text-muted-foreground/40 w-4">{i + 1}.</span>
                              <div className="flex-1">
                                <p className="text-sm text-foreground/80">{s.item}</p>
                                <p className="text-2xs text-muted-foreground/40 capitalize">{s.category}</p>
                              </div>
                              <ChevronRight className="h-3.5 w-3.5 text-brand-gold/40" />
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Cost per wear */}
                  {capsule.cost_per_wear.length > 0 && (
                    <div className="luxury-card p-5 space-y-4">
                      <p className="text-sm font-semibold text-foreground">
                        Cost Per Wear — Most Expensive Items
                      </p>
                      <div className="space-y-2">
                        {capsule.cost_per_wear.slice(0, 5).map((c, i) => (
                          <div key={i} className="flex items-center gap-3">
                            <div className="flex-1">
                              <p className="text-sm text-foreground/70 line-clamp-1">{c.name}</p>
                              <p className="text-2xs text-muted-foreground/40">
                                Worn {c.times_worn}×  · ₹{c.cost} total
                              </p>
                            </div>
                            <p className={cn("text-sm font-semibold",
                              c.cpw > 500 ? "text-rose-400" :
                              c.cpw > 100 ? "text-amber-400" : "text-emerald-400"
                            )}>
                              ₹{c.cpw}/wear
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </motion.div>
      )}
    </div>
  );
}
