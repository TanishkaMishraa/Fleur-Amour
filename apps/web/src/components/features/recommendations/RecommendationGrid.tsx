"use client";
/**
 * AuraFit — DomainSection & RecommendationGrid components (Stage 6).
 * DomainSection: a horizontal scrollable card strip per recommendation domain.
 * RecommendationGrid: a responsive grid of product cards.
 */
import { motion } from "framer-motion";
import { ArrowRight, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductCard } from "./ProductCard";
import type { RecDomain, RecommendedProduct } from "@/types/recommendations";
import { DOMAIN_META } from "@/types/recommendations";
import { useRecommendations } from "@/lib/hooks/useRecommendations";

// ── RecommendationGrid ────────────────────────────────────────────────────────

interface RecommendationGridProps {
  items:     RecommendedProduct[];
  loading?:  boolean;
  columns?:  2 | 3 | 4;
  className?: string;
}

export function RecommendationGrid({
  items, loading, columns = 4, className,
}: RecommendationGridProps) {
  const gridClass = {
    2: "grid-cols-2",
    3: "grid-cols-2 sm:grid-cols-3",
    4: "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4",
  }[columns];

  if (loading) {
    return (
      <div className={cn("grid gap-4", gridClass, className)}>
        {Array.from({ length: columns * 2 }).map((_, i) => (
          <div key={i} className="space-y-3">
            <Skeleton className="aspect-square rounded-2xl" />
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
            <Skeleton className="h-4 w-1/3" />
          </div>
        ))}
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="flex flex-col items-center py-16 text-center space-y-2">
        <p className="text-muted-foreground/50 text-sm">No products found.</p>
      </div>
    );
  }

  return (
    <div className={cn("grid gap-4", gridClass, className)}>
      {items.map((item, i) => (
        <motion.div
          key={item.product.id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05, duration: 0.35, ease: [0.23, 1, 0.32, 1] }}
        >
          <ProductCard
            product={item.product}
            reasonCode={item.reason_code}
            explanation={item.explanation}
            score={item.score}
          />
        </motion.div>
      ))}
    </div>
  );
}

// ── DomainSection ─────────────────────────────────────────────────────────────

interface DomainSectionProps {
  domain:     RecDomain;
  userId:     string;
  onViewAll?: (domain: RecDomain) => void;
  limit?:     number;
}

export function DomainSection({ domain, userId, onViewAll, limit = 8 }: DomainSectionProps) {
  const meta = DOMAIN_META[domain];
  const { data, isLoading, isError, refetch, isRefetching } = useRecommendations(domain, { limit });

  return (
    <section className="space-y-5">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn(
            "h-9 w-9 flex items-center justify-center rounded-xl text-lg",
            "bg-gradient-to-br shadow-sm",
            meta.gradient
          )}>
            {meta.emoji}
          </div>
          <div>
            <h2 className="font-sans text-base font-semibold text-foreground">{meta.label}</h2>
            <p className="text-xs text-muted-foreground/50">{meta.description}</p>
          </div>
          {data?.cold_start && (
            <span className="text-2xs text-muted-foreground/40 ml-2">
              (Personalising — interact more for better results)
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetch()}
            loading={isRefetching}
            className="h-8 w-8 p-0"
          >
            {!isRefetching && <RefreshCw className="h-3.5 w-3.5" />}
          </Button>
          {onViewAll && (
            <Button
              variant="ghost-gold"
              size="sm"
              onClick={() => onViewAll(domain)}
              className="gap-1 text-xs"
            >
              See all <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Horizontal scroll strip */}
      {isError ? (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive/70 text-center">
          Failed to load {meta.label.toLowerCase()} recommendations.
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-3 hide-scrollbar -mx-1 px-1">
          {isLoading
            ? Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex-shrink-0 w-44 space-y-2">
                  <Skeleton className="aspect-square rounded-2xl w-44" />
                  <Skeleton className="h-2.5 w-3/4" />
                  <Skeleton className="h-2.5 w-1/2" />
                </div>
              ))
            : data?.items.map((item) => (
                <div key={item.product.id} className="flex-shrink-0 w-44">
                  <ProductCard
                    product={item.product}
                    reasonCode={item.reason_code}
                    explanation={item.explanation}
                  />
                </div>
              ))}
        </div>
      )}
    </section>
  );
}
