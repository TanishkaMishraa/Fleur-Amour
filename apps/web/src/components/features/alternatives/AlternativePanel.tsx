"use client";
/**
 * AuraFit — AlternativePanel.
 *
 * Usage: Rendered automatically below a ProductCard when the product price
 * exceeds LUXURY_THRESHOLD_INR (₹10,000).
 *
 * Can be used standalone on the product detail page, or inline within
 * recommendation grids.
 *
 * Two modes:
 *   - collapsed: shows a "Find cheaper alternatives" trigger button
 *   - expanded:  shows AlternativeCard grid + source product summary
 */
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Sparkles, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AlternativeCard } from "./AlternativeCard";
import { useAlternatives } from "@/lib/api/alternatives";
import type { ProductListItem } from "@/types/recommendations";
import { formatPrice, isLuxuryPrice } from "@/types/alternatives";

interface AlternativePanelProps {
  product:         ProductListItem;
  defaultExpanded?:boolean;
  className?:      string;
}

export function AlternativePanel({ product, defaultExpanded = false, className }: AlternativePanelProps) {
  const [open, setOpen] = useState(defaultExpanded);
  const luxury = isLuxuryPrice(product.price, product.currency);

  // Only fetch when open
  const { data, isLoading, isError, refetch } = useAlternatives(product.id, {
    enabled: open,
    limit:   5,
  });

  // Don't render panel at all for non-luxury products
  if (!luxury) return null;

  return (
    <div className={cn("mt-3", className)}>
      {/* Trigger */}
      <button
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "w-full flex items-center gap-2.5 rounded-xl px-4 py-2.5 text-left",
          "border transition-all duration-250 ease-luxury",
          open
            ? "border-brand-gold/30 bg-brand-gold/5 text-brand-gold"
            : "border-white/[0.08] bg-white/[0.02] text-muted-foreground/60 hover:border-white/[0.15] hover:text-foreground/70"
        )}
      >
        <TrendingDown className="h-3.5 w-3.5 flex-shrink-0" />
        <span className="flex-1 text-xs font-medium">
          {open ? "Smart Alternatives" : "Find cheaper alternatives"}
        </span>
        <span className="text-2xs opacity-60 hidden sm:inline">
          Price: {formatPrice(product.price, product.currency)}
        </span>
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform duration-250", open && "rotate-180")} />
      </button>

      {/* Expanded panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35, ease: [0.23, 1, 0.32, 1] }}
            className="overflow-hidden"
          >
            <div className="pt-4 space-y-4">
              {/* Header */}
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-brand-gold" />
                <p className="text-sm font-semibold text-foreground">
                  Affordable Alternatives
                </p>
                <span className="text-xs text-muted-foreground/40">
                  — same formula, better price
                </span>
              </div>

              {/* Loading */}
              {isLoading && (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="luxury-card p-5 space-y-4">
                      <div className="flex gap-4">
                        <Skeleton className="h-20 w-20 rounded-2xl flex-shrink-0" />
                        <div className="flex-1 space-y-2">
                          <Skeleton className="h-3 w-1/3" />
                          <Skeleton className="h-3.5 w-2/3" />
                          <Skeleton className="h-2.5 w-1/4 mt-3" />
                        </div>
                        <Skeleton className="h-16 w-16 rounded-full flex-shrink-0" />
                      </div>
                      <Skeleton className="h-2 w-full" />
                      <Skeleton className="h-2 w-4/5" />
                    </div>
                  ))}
                </div>
              )}

              {/* Error */}
              {isError && (
                <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive/70 text-center space-y-2">
                  <p>Couldn't load alternatives.</p>
                  <Button variant="ghost-gold" size="sm" onClick={() => refetch()}>
                    Try again
                  </Button>
                </div>
              )}

              {/* Empty */}
              {data && data.alternatives.length === 0 && !isLoading && (
                <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 text-center space-y-2">
                  <p className="text-sm text-muted-foreground/50">
                    No alternatives found in your price range yet.
                  </p>
                  <p className="text-xs text-muted-foreground/30">
                    Our engine checks the catalog daily — check back soon.
                  </p>
                </div>
              )}

              {/* Results */}
              {data && data.alternatives.length > 0 && (
                <div className="space-y-4">
                  {data.alternatives.map((alt, i) => (
                    <AlternativeCard
                      key={alt.alt_id}
                      alt={alt}
                      sourcePrice={data.source.price}
                      currency={data.source.currency}
                      index={i}
                    />
                  ))}
                  <p className="text-center text-2xs text-muted-foreground/30 pt-2">
                    Similarity scores computed via ingredient matching, shade ΔE, and AI embeddings.
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Compact inline trigger (for use inside recommendation grids).
 * Renders as a small pill below the product card price.
 */
export function AlternativeTriggerBadge({
  product,
  onClick,
}: {
  product: ProductListItem;
  onClick: () => void;
}) {
  if (!isLuxuryPrice(product.price, product.currency)) return null;

  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className="mt-2 w-full flex items-center justify-center gap-1.5 rounded-xl border border-brand-gold/25 bg-brand-gold/5 px-3 py-1.5 text-2xs font-medium text-brand-gold/80 hover:bg-brand-gold/10 transition-colors"
    >
      <TrendingDown className="h-3 w-3" />
      Find cheaper dupes
    </button>
  );
}
