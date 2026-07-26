"use client";
/**
 * AuraFit — Smart Alternatives Dashboard Page (Stage 7).
 *
 * Two entry points:
 *   1. /dashboard/alternatives?product={id}
 *      → Shows alternatives for a specific product (deep-link from product cards)
 *   2. /dashboard/alternatives
 *      → Explorer mode: search luxury products and compare alternatives
 */
import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingDown, Search, ShoppingBag,
  Sparkles, Info, ArrowLeft,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { GoldDivider } from "@/components/shared/GoldDivider";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AlternativeCard } from "@/components/features/alternatives/AlternativeCard";
import { SimilarityRing } from "@/components/features/alternatives/SimilarityBar";
import { useAlternatives } from "@/lib/api/alternatives";
import { useProductSearch } from "@/lib/hooks/useRecommendations";
import { formatPrice, isLuxuryPrice, LUXURY_THRESHOLD_INR } from "@/types/alternatives";
import type { ProductListItem } from "@/types/recommendations";

export default function AlternativesPage() {
  const params    = useSearchParams();
  const productId = params.get("product") ?? undefined;
  const [searchQ, setSearchQ] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<ProductListItem | null>(null);

  // When a product ID is in URL, immediately show its alternatives
  const resolvedId = selectedProduct?.id ?? productId;

  const { data: searchResults, isLoading: searching } = useProductSearch({
    q:           searchQ,
    in_stock_only: true,
    per_page:    12,
  });

  const {
    data:      alternatives,
    isLoading: loadingAlts,
    isError:   altError,
  } = useAlternatives(resolvedId, { enabled: !!resolvedId, limit: 8 });

  const hasAlts = !loadingAlts && alternatives && alternatives.alternatives.length > 0;

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-16">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 text-2xs uppercase tracking-widest text-brand-gold/70 mb-3">
          <TrendingDown className="h-3.5 w-3.5" />
          Smart Alternative Engine
        </div>
        <h1 className="font-display text-display-md font-light tracking-tightest">
          Find Affordable Dupes
        </h1>
        <p className="text-sm text-muted-foreground mt-2 max-w-xl">
          For any product above ₹{LUXURY_THRESHOLD_INR.toLocaleString()}, our engine finds affordable
          alternatives matched by ingredients, formula, shade, and fragrance notes — not just price.
        </p>
      </motion.div>

      <GoldDivider />

      {/* How it works */}
      <motion.div
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid gap-3 sm:grid-cols-4"
      >
        {[
          { icon: "🧪", label: "Ingredient Match",  desc: "INCI Jaccard + active weighting" },
          { icon: "🎨", label: "Shade ΔE",          desc: "CIE 1994 colour science" },
          { icon: "🌸", label: "Fragrance Pyramid",  desc: "Top / mid / base note overlap" },
          { icon: "🔮", label: "AI Embedding",       desc: "SBERT semantic similarity" },
        ].map((item, i) => (
          <div key={i} className="luxury-card px-4 py-3 flex items-start gap-3">
            <span className="text-xl">{item.icon}</span>
            <div>
              <p className="text-xs font-semibold text-foreground">{item.label}</p>
              <p className="text-2xs text-muted-foreground/50 mt-0.5">{item.desc}</p>
            </div>
          </div>
        ))}
      </motion.div>

      {/* Product search / selector */}
      {!resolvedId && (
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="space-y-5"
        >
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40" />
            <input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="Search for a luxury product (e.g. La Mer moisturiser)…"
              className="input-luxury pl-10 pr-4 py-3 w-full"
            />
          </div>

          {searchQ.length >= 2 && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {searching
                ? Array(6).fill(0).map((_, i) => (
                    <div key={i} className="luxury-card p-4 flex gap-3">
                      <Skeleton className="h-14 w-14 rounded-xl flex-shrink-0" />
                      <div className="flex-1 space-y-2">
                        <Skeleton className="h-3 w-3/4" />
                        <Skeleton className="h-3 w-1/2" />
                      </div>
                    </div>
                  ))
                : searchResults?.items
                    .filter((p) => isLuxuryPrice(p.price, p.currency))
                    .map((product) => (
                      <button
                        key={product.id}
                        onClick={() => setSelectedProduct(product)}
                        className="luxury-card p-4 flex items-center gap-3 text-left hover:border-brand-gold/30 transition-colors"
                      >
                        <div className="relative h-14 w-14 flex-shrink-0 overflow-hidden rounded-xl bg-white/[0.03]">
                          {product.image_url ? (
                            <Image src={product.image_url} alt={product.name} fill className="object-cover" sizes="56px" />
                          ) : (
                            <ShoppingBag className="h-6 w-6 absolute inset-0 m-auto text-muted-foreground/20" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="text-2xs text-muted-foreground/50">{product.brand_name}</p>
                          <p className="text-sm font-medium line-clamp-1">{product.name}</p>
                          <p className="text-xs font-semibold text-brand-gold mt-0.5">
                            {formatPrice(product.price, product.currency)}
                          </p>
                        </div>
                      </button>
                    ))}
              {!searching && searchResults?.items.filter((p) => isLuxuryPrice(p.price, p.currency)).length === 0 && (
                <p className="col-span-3 text-sm text-muted-foreground/50 text-center py-6">
                  No luxury products found for "{searchQ}".
                  Only products above ₹{LUXURY_THRESHOLD_INR.toLocaleString()} have alternatives.
                </p>
              )}
            </div>
          )}
        </motion.div>
      )}

      {/* Selected product + alternatives view */}
      <AnimatePresence>
        {resolvedId && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="space-y-8"
          >
            {/* Back button */}
            {selectedProduct && (
              <Button variant="ghost" size="sm" onClick={() => setSelectedProduct(null)} className="-ml-2">
                <ArrowLeft className="h-4 w-4" /> Search again
              </Button>
            )}

            {/* Source product header */}
            {alternatives?.source && (
              <div className="luxury-card p-6 flex gap-5">
                <div className="relative h-24 w-24 flex-shrink-0 overflow-hidden rounded-2xl bg-white/[0.03]">
                  {alternatives.source.image_url ? (
                    <Image src={alternatives.source.image_url} alt={alternatives.source.name}
                      fill className="object-cover" sizes="96px" />
                  ) : (
                    <ShoppingBag className="h-10 w-10 absolute inset-0 m-auto text-muted-foreground/20" />
                  )}
                </div>
                <div className="flex-1 min-w-0 space-y-2">
                  <p className="text-2xs text-muted-foreground/50">{alternatives.source.brand_name}</p>
                  <h2 className="font-display text-display-sm font-light">{alternatives.source.name}</h2>
                  <div className="flex items-center gap-3">
                    <p className="text-xl font-bold text-foreground">
                      {formatPrice(alternatives.source.price, alternatives.source.currency)}
                    </p>
                    <Badge variant="gold">Luxury</Badge>
                  </div>
                </div>
                <div className="text-right text-xs text-muted-foreground/40 flex-shrink-0 space-y-1">
                  <p>{alternatives.total} alternatives found</p>
                  {!alternatives.from_cache && <p className="text-brand-gold/40">Live result</p>}
                </div>
              </div>
            )}

            {/* Loading */}
            {loadingAlts && (
              <div className="grid gap-4 lg:grid-cols-2">
                {[1,2,3,4].map((i) => (
                  <div key={i} className="luxury-card p-5 space-y-4">
                    <div className="flex gap-4">
                      <Skeleton className="h-20 w-20 rounded-2xl flex-shrink-0" />
                      <div className="flex-1 space-y-2">
                        <Skeleton className="h-3 w-1/3" />
                        <Skeleton className="h-4 w-2/3" />
                        <Skeleton className="h-3 w-1/4 mt-2" />
                      </div>
                      <Skeleton className="h-16 w-16 rounded-full" />
                    </div>
                    <Skeleton className="h-2" /><Skeleton className="h-2 w-4/5" />
                  </div>
                ))}
              </div>
            )}

            {/* Error */}
            {altError && !loadingAlts && (
              <div className="luxury-card p-8 text-center text-sm text-destructive/70">
                Could not load alternatives. Please try again.
              </div>
            )}

            {/* Empty */}
            {alternatives && alternatives.alternatives.length === 0 && !loadingAlts && (
              <div className="luxury-card p-12 text-center space-y-3">
                <Info className="h-8 w-8 text-muted-foreground/30 mx-auto" />
                <p className="text-sm text-muted-foreground/60">
                  No alternatives found yet. Our engine processes luxury products nightly.
                </p>
              </div>
            )}

            {/* Results grid */}
            {hasAlts && (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <Sparkles className="h-4 w-4 text-brand-gold" />
                  <p className="text-sm font-semibold">
                    {alternatives.alternatives.length} Affordable Alternatives
                  </p>
                  <span className="text-2xs text-muted-foreground/40">ranked by similarity</span>
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  {alternatives.alternatives.map((alt, i) => (
                    <AlternativeCard
                      key={alt.alt_id}
                      alt={alt}
                      sourcePrice={alternatives.source.price}
                      currency={alternatives.source.currency}
                      index={i}
                    />
                  ))}
                </div>
                <p className="text-center text-2xs text-muted-foreground/30 pt-4">
                  AuraFit Smart Alternative Engine v{alternatives.engine_version} ·
                  Scores computed via ingredient analysis, shade ΔE colour science, and SBERT AI embeddings.
                  Not sponsored — purely algorithmic.
                </p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
