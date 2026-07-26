"use client";
/**
 * AuraFit — AlternativeCard.
 * Renders one affordable alternative with:
 *   - Product image + name + brand tier badge
 *   - Overall similarity ring + savings pill
 *   - Best Value badge (if applicable)
 *   - Per-signal breakdown bars (ingredient, shade, fragrance, formula)
 *   - Match detail chips (matched ingredients, notes, etc.)
 *   - Price comparison with savings amount
 */
import Image from "next/image";
import { motion } from "framer-motion";
import { Award, ShoppingBag, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { AlternativeProduct, MatchType } from "@/types/alternatives";
import { MATCH_TYPE_META, SIMILARITY_LABEL, formatPrice } from "@/types/alternatives";
import { SimilarityBar, SimilarityRing } from "./SimilarityBar";

interface AlternativeCardProps {
  alt:       AlternativeProduct;
  sourcePrice: number;
  currency:  string;
  index?:    number;
  className?:string;
}

const TIER_STYLE: Record<string, string> = {
  luxury:    "text-brand-gold border-brand-gold/30 bg-brand-gold/5",
  mid:       "text-blue-400  border-blue-400/30  bg-blue-400/5",
  drugstore: "text-emerald-400 border-emerald-400/30 bg-emerald-400/5",
};

export function AlternativeCard({ alt, sourcePrice, currency, index = 0, className }: AlternativeCardProps) {
  const p        = alt.product;
  const sim      = SIMILARITY_LABEL(alt.overall_pct);
  const tierStyle = TIER_STYLE[p.brand_tier] ?? TIER_STYLE["mid"];

  // Collect available score breakdowns to display
  const signals: Array<{ label: string; score: number; icon: string }> = [];
  if (alt.ingredient_score != null && alt.ingredient_score > 0)
    signals.push({ label: "Ingredients", score: alt.ingredient_score, icon: "🧪" });
  if (alt.shade_score != null && alt.shade_score > 0)
    signals.push({ label: "Shade",       score: alt.shade_score,      icon: "🎨" });
  if (alt.fragrance_score != null && alt.fragrance_score > 0)
    signals.push({ label: "Fragrance",   score: alt.fragrance_score,  icon: "🌸" });
  if (alt.formula_score != null && alt.formula_score > 0)
    signals.push({ label: "Formula",     score: alt.formula_score,    icon: "⚗️" });
  if (alt.embedding_score != null && signals.length === 0)
    signals.push({ label: "Similarity",  score: alt.embedding_score,  icon: "🔮" });

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
      className={cn(
        "luxury-card overflow-hidden flex flex-col gap-0",
        alt.is_best_value && "ring-1 ring-brand-gold/30",
        className
      )}
    >
      {/* Best Value banner */}
      {alt.is_best_value && (
        <div className="bg-gold-gradient px-4 py-1.5 flex items-center gap-2">
          <Award className="h-3.5 w-3.5 text-brand-black" />
          <span className="text-2xs font-bold text-brand-black uppercase tracking-wider">
            Best Value Pick
          </span>
        </div>
      )}

      <div className="p-5 space-y-5">
        {/* Top row: image + info + score ring */}
        <div className="flex gap-4">
          {/* Product image */}
          <div className="relative h-20 w-20 flex-shrink-0 overflow-hidden rounded-2xl bg-white/[0.03]">
            {p.image_url ? (
              <Image src={p.image_url} alt={p.name} fill className="object-cover" sizes="80px" />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center">
                <ShoppingBag className="h-8 w-8 text-muted-foreground/20" />
              </div>
            )}
          </div>

          {/* Product info */}
          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex items-start gap-2 flex-wrap">
              <span className={cn("text-2xs px-2 py-0.5 rounded-full border font-medium capitalize", tierStyle)}>
                {p.brand_tier}
              </span>
              {alt.match_types.map((mt) => {
                const meta = MATCH_TYPE_META[mt as MatchType];
                return meta ? (
                  <span key={mt} className={cn("text-2xs font-medium", meta.color)}>
                    {meta.icon} {meta.label}
                  </span>
                ) : null;
              })}
            </div>
            <p className="text-2xs text-muted-foreground/50">{p.brand_name}</p>
            <p className="text-sm font-medium text-foreground leading-snug line-clamp-2">{p.name}</p>
            {p.avg_rating != null && (
              <div className="flex items-center gap-1">
                <Star className="h-3 w-3 text-brand-gold fill-brand-gold" />
                <span className="text-2xs text-muted-foreground/60">
                  {p.avg_rating.toFixed(1)} ({p.review_count})
                </span>
              </div>
            )}
          </div>

          {/* Similarity ring */}
          <div className="flex-shrink-0">
            <SimilarityRing score={alt.overall_score} size={68} />
          </div>
        </div>

        {/* Similarity label */}
        <div className="flex items-center gap-2">
          <span className={cn("text-xs font-semibold", sim.color)}>{sim.label}</span>
          {alt.overall_pct >= 70 && (
            <Badge variant="gold" className="text-2xs">Dupe</Badge>
          )}
        </div>

        {/* Signal breakdowns */}
        {signals.length > 0 && (
          <div className="space-y-2.5">
            {signals.map((sig) => (
              <SimilarityBar
                key={sig.label}
                score={sig.score}
                label={`${sig.icon} ${sig.label}`}
                size="sm"
              />
            ))}
          </div>
        )}

        {/* Match detail chips */}
        {(alt.match_detail?.matched_ingredients?.length ?? 0) > 0 && (
          <div className="space-y-1.5">
            <p className="text-2xs text-muted-foreground/40 uppercase tracking-widest">
              Shared ingredients
            </p>
            <div className="flex flex-wrap gap-1.5">
              {alt.match_detail?.matched_ingredients?.slice(0, 5).map((ing: string) => (
                <span key={ing}
                  className="inline-flex items-center rounded-full bg-emerald-400/10 border border-emerald-400/20 px-2.5 py-0.5 text-2xs text-emerald-400 capitalize">
                  {ing}
                </span>
              ))}
            </div>
          </div>
        )}

        {(alt.match_detail?.matched_notes?.length ?? 0) > 0 && (
          <div className="space-y-1.5">
            <p className="text-2xs text-muted-foreground/40 uppercase tracking-widest">
              Shared notes
            </p>
            <div className="flex flex-wrap gap-1.5">
              {alt.match_detail?.matched_notes?.slice(0, 5).map((note: string) => (
                <span key={note}
                  className="inline-flex items-center rounded-full bg-purple-400/10 border border-purple-400/20 px-2.5 py-0.5 text-2xs text-purple-400 capitalize">
                  {note}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Shade comparison */}
        {alt.match_detail?.shade_hex_source && alt.match_detail?.shade_hex_alternative && (
          <div className="flex items-center gap-3">
            <p className="text-2xs text-muted-foreground/40">Shade comparison</p>
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-lg ring-1 ring-white/20"
                style={{ backgroundColor: alt.match_detail?.shade_hex_source }} />
              <span className="text-2xs text-muted-foreground/30">→</span>
              <div className="h-6 w-6 rounded-lg ring-1 ring-white/20"
                style={{ backgroundColor: alt.match_detail?.shade_hex_alternative }} />
              {alt.match_detail?.shade_delta_e != null && (
                <span className="text-2xs text-muted-foreground/40">
                  ΔE {alt.match_detail.shade_delta_e}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Price comparison */}
        <div className="pt-1 border-t border-white/[0.06]">
          <div className="flex items-end justify-between">
            <div className="space-y-0.5">
              <p className="text-2xs text-muted-foreground/40">Alternative price</p>
              <p className="text-lg font-bold text-foreground">
                {formatPrice(alt.alt_price, alt.currency)}
              </p>
              <p className="text-2xs text-muted-foreground/40 line-through">
                vs {formatPrice(alt.source_price, alt.currency)}
              </p>
            </div>
            <div className="text-right space-y-1">
              <div className="rounded-xl bg-emerald-400/10 border border-emerald-400/20 px-3 py-1.5">
                <p className="text-xs font-bold text-emerald-400">
                  Save {formatPrice(alt.price_savings, alt.currency)}
                </p>
                <p className="text-2xs text-emerald-400/60">{alt.savings_pct.toFixed(0)}% less</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
