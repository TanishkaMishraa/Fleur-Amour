"use client";
/**
 * AuraFit — ProductCard component.
 * Used in recommendation grids, search results, and carousels.
 * Displays image, brand, name, price, rating, badges, and reason tag.
 */
import { useState } from "react";
import Image from "next/image";
import { Heart, ShoppingBag, Star, Zap } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { ProductListItem } from "@/types/recommendations";
import { REASON_COPY } from "@/types/recommendations";
import { useRecordInteraction } from "@/lib/hooks/useRecommendations";

interface ProductCardProps {
  product:      ProductListItem;
  reasonCode?:  string;
  explanation?: string;
  score?:       number;
  className?:   string;
  onClick?:     () => void;
}

export function ProductCard({
  product, reasonCode, explanation, score, className, onClick,
}: ProductCardProps) {
  const [saved, setSaved] = useState(false);
  const { mutate: recordInteraction } = useRecordInteraction();
  const reasonMeta = reasonCode ? REASON_COPY[reasonCode] : null;

  const handleSave = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSaved((s) => !s);
    recordInteraction({
      product_id: product.id,
      interaction_type: saved ? "unsave" : "save",
    });
  };

  const handleClick = () => {
    recordInteraction({ product_id: product.id, interaction_type: "view" });
    onClick?.();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
      onClick={handleClick}
      className={cn(
        "luxury-card group relative flex flex-col overflow-hidden cursor-pointer",
        className
      )}
    >
      {/* Image */}
      <div className="relative aspect-square overflow-hidden bg-white/[0.03]">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <ShoppingBag className="h-10 w-10 text-muted-foreground/20" />
          </div>
        )}

        {/* Overlay badges */}
        <div className="absolute top-2.5 left-2.5 flex flex-col gap-1.5">
          {product.is_new_arrival && (
            <Badge variant="gold" className="text-2xs shadow-sm">New</Badge>
          )}
          {product.is_trending && (
            <Badge variant="default" className="text-2xs shadow-sm gap-1">
              <Zap className="h-2.5 w-2.5" />Trending
            </Badge>
          )}
        </div>

        {/* Save button */}
        <button
          onClick={handleSave}
          className={cn(
            "absolute top-2.5 right-2.5 h-8 w-8 flex items-center justify-center rounded-full",
            "bg-black/40 backdrop-blur-sm transition-all duration-200",
            saved ? "text-rose-400" : "text-white/60 hover:text-white"
          )}
        >
          <Heart className={cn("h-3.5 w-3.5", saved && "fill-current")} />
        </button>
      </div>

      {/* Content */}
      <div className="flex flex-col flex-1 p-4 space-y-2">
        <div>
          <p className="text-2xs text-muted-foreground/50 uppercase tracking-wide">
            {product.brand_name}
          </p>
          <p className="text-sm font-medium text-foreground line-clamp-2 mt-0.5 leading-snug">
            {product.name}
          </p>
        </div>

        {/* Rating */}
        {product.avg_rating !== null && (
          <div className="flex items-center gap-1.5">
            <Star className="h-3 w-3 text-brand-gold fill-brand-gold" />
            <span className="text-2xs text-muted-foreground/70">
              {product.avg_rating.toFixed(1)}
              <span className="text-muted-foreground/40 ml-0.5">
                ({product.review_count})
              </span>
            </span>
          </div>
        )}

        {/* Price */}
        <div className="mt-auto pt-1 flex items-end justify-between">
          <p className="text-sm font-semibold text-foreground">
            {new Intl.NumberFormat("en-US", {
              style: "currency", currency: product.currency ?? "USD",
            }).format(product.price)}
          </p>
          {!product.in_stock && (
            <span className="text-2xs text-red-400/70">Out of stock</span>
          )}
        </div>

        {/* Reason tag */}
        {reasonMeta && (
          <div className={cn("text-2xs font-medium", reasonMeta.color)}>
            ✦ {reasonMeta.label}
          </div>
        )}
      </div>
    </motion.div>
  );
}
