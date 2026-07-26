"use client";
/**
 * AuraFit — Celebrity Matching Dashboard (Stage 9).
 * Upload selfie → CLIP embedding → FAISS nearest-neighbour → celebrity style matches.
 */
import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Loader2, Star, Sparkles, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GoldDivider } from "@/components/shared/GoldDivider";
import { celebrityApi } from "@/lib/api/stage9";
import type { CelebrityMatch, CelebrityMatchResult } from "@/types/stage9";

const anim = (i = 0) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: i * 0.06, duration: 0.4, ease: [0.23, 1, 0.32, 1] as const },
});

function SimilarityRingSmall({ pct }: { pct: number }) {
  const r    = 22;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const color = pct >= 80 ? "#C9A84C" : pct >= 65 ? "#F59E0B" : "#6B7280";
  return (
    <svg width={52} height={52} className="-rotate-90">
      <circle cx={26} cy={26} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={4} />
      <motion.circle
        cx={26} cy={26} r={r} fill="none"
        stroke={color} strokeWidth={4} strokeLinecap="round"
        strokeDasharray={`${circ} ${circ}`}
        initial={{ strokeDashoffset: circ }}
        animate={{ strokeDashoffset: circ - dash }}
        transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] }}
      />
      <text x={26} y={26} textAnchor="middle" dominantBaseline="middle"
        className="rotate-90" style={{ fontSize: 10, fill: color, fontWeight: 700 }}
        transform={`rotate(90, 26, 26)`}>
        {pct}%
      </text>
    </svg>
  );
}

function CelebrityCard({ match, index }: { match: CelebrityMatch; index: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <motion.div {...anim(index * 0.07)}
      className={cn(
        "luxury-card overflow-hidden transition-all",
        index === 0 && "ring-1 ring-brand-gold/30"
      )}
    >
      {/* Top match banner */}
      {index === 0 && (
        <div className="bg-gold-gradient px-4 py-1.5 flex items-center gap-2">
          <Star className="h-3.5 w-3.5 text-brand-black fill-brand-black" />
          <span className="text-2xs font-bold text-brand-black uppercase tracking-wider">
            Closest Style Match
          </span>
        </div>
      )}

      <div className="p-5 space-y-4">
        {/* Header */}
        <div className="flex gap-4">
          <div className="flex-shrink-0">
            <SimilarityRingSmall pct={match.similarity_pct} />
          </div>
          <div className="flex-1 min-w-0 space-y-1.5">
            <h3 className="text-base font-semibold text-foreground">{match.name}</h3>
            <div className="flex flex-wrap gap-1.5">
              {match.style_archetypes.map((a) => (
                <Badge key={a} variant="gold" className="text-2xs">{a}</Badge>
              ))}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {match.known_aesthetics.slice(0, 3).map((a) => (
                <span key={a} className="text-2xs text-muted-foreground/40 capitalize">{a}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Signatures */}
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1">
            <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">Makeup</p>
            <p className="text-xs text-foreground/70 leading-snug">{match.makeup_signature}</p>
          </div>
          <div className="space-y-1">
            <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">Fashion</p>
            <p className="text-xs text-foreground/70 leading-snug">{match.fashion_signature}</p>
          </div>
        </div>

        {/* Style tip (expandable) */}
        <button
          onClick={() => setExpanded((e) => !e)}
          className="w-full text-left rounded-xl border border-brand-gold/20 bg-brand-gold/5 px-4 py-3 flex items-start gap-2.5"
        >
          <Sparkles className="h-3.5 w-3.5 text-brand-gold mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-xs font-semibold text-brand-gold mb-0.5">Style Tip</p>
            <p className={cn("text-xs text-foreground/70 leading-relaxed", !expanded && "line-clamp-2")}>
              {match.style_tip}
            </p>
          </div>
          <ChevronRight className={cn("h-4 w-4 text-brand-gold/60 transition-transform flex-shrink-0",
            expanded && "rotate-90")} />
        </button>

        {/* Fragrance */}
        {match.fragrance_family && (
          <p className="text-2xs text-muted-foreground/40">
            Fragrance family: <span className="text-foreground/60">{match.fragrance_family}</span>
          </p>
        )}

        {/* Inspiration tags */}
        <div className="flex flex-wrap gap-1.5">
          {match.inspiration_tags.map((t) => (
            <span key={t}
              className="text-2xs rounded-full border border-white/[0.06] bg-white/[0.02] px-2.5 py-1 text-muted-foreground/50 capitalize">
              {t}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

export default function CelebrityPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [preview,    setPreview]    = useState<string | null>(null);
  const [result,     setResult]     = useState<CelebrityMatchResult | null>(null);
  const [isLoading,  setIsLoading]  = useState(false);
  const [error,      setError]      = useState<string | null>(null);

  const handleUpload = useCallback(async (file: File) => {
    setPreview(URL.createObjectURL(file));
    setResult(null);
    setError(null);
    setIsLoading(true);
    try {
      const res = await celebrityApi.matchCelebrity(file);
      setResult(res);
    } catch (err: any) {
      setError(err.message ?? "Celebrity matching failed. Please try a clearer photo.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-16">
      {/* Header */}
      <motion.div {...anim(0)} className="space-y-2">
        <div className="flex items-center gap-2 text-2xs uppercase tracking-widest text-brand-gold/70">
          <Star className="h-3.5 w-3.5" /> Celebrity Style Match
        </div>
        <h1 className="font-display text-display-md font-light tracking-tightest">
          Your Celebrity Style Twin
        </h1>
        <p className="text-sm text-muted-foreground max-w-xl">
          Upload a selfie and discover which celebrity your style resonates with — plus their
          makeup signatures, fashion approach, and fragrance family.
        </p>
      </motion.div>

      <GoldDivider />

      <div className="grid gap-8 lg:grid-cols-[300px_1fr]">
        {/* Upload panel */}
        <motion.div {...anim(1)} className="space-y-4">
          <div
            onClick={() => fileRef.current?.click()}
            className={cn(
              "relative overflow-hidden cursor-pointer rounded-3xl border-2 border-dashed",
              "aspect-[3/4] flex items-center justify-center text-center",
              "border-white/[0.10] hover:border-brand-gold/40 hover:bg-brand-gold/5 transition-all"
            )}
          >
            {preview ? (
              <img src={preview} alt="Your selfie" className="w-full h-full object-cover" />
            ) : (
              <div className="p-6 space-y-4">
                <div className="h-12 w-12 mx-auto rounded-2xl bg-brand-gold/10 flex items-center justify-center">
                  <Upload className="h-6 w-6 text-brand-gold/60" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">Upload a selfie</p>
                  <p className="text-xs text-muted-foreground/50 mt-1">
                    Clear, well-lit face photo works best
                  </p>
                </div>
              </div>
            )}
            {isLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/60">
                <Loader2 className="h-8 w-8 text-brand-gold animate-spin" />
                <p className="text-xs text-white/70">Finding your matches…</p>
              </div>
            )}
          </div>

          <Button
            variant={preview ? "ghost-gold" : "gold"}
            className="w-full gap-2"
            onClick={() => fileRef.current?.click()}
            loading={isLoading}
          >
            <Upload className="h-4 w-4" />
            {preview ? "Try a different photo" : "Upload Photo"}
          </Button>

          {error && (
            <p className="text-xs text-destructive rounded-xl border border-destructive/20 bg-destructive/5 px-3 py-2">
              {error}
            </p>
          )}

          {result && (
            <div className="luxury-card p-4 space-y-2.5">
              <p className="text-2xs uppercase tracking-widest text-muted-foreground/40">Your aesthetic</p>
              <p className="text-sm font-semibold text-foreground capitalize">{result.query_aesthetic}</p>
              <p className="text-2xs text-muted-foreground/50">
                Era: {result.style_era} · Primary: {result.primary_style}
              </p>
            </div>
          )}

          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); }}
          />
        </motion.div>

        {/* Results */}
        <div>
          <AnimatePresence mode="wait">
            {!result && !isLoading && (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="luxury-card p-12 text-center space-y-4 h-full flex flex-col items-center justify-center">
                <div className="h-20 w-20 rounded-3xl bg-brand-gold/10 flex items-center justify-center animate-float">
                  <Star className="h-9 w-9 text-brand-gold/60" />
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-foreground">Upload a selfie to begin</p>
                  <p className="text-xs text-muted-foreground/50 max-w-xs">
                    Our AI compares your style essence against hundreds of celebrity profiles using CLIP embeddings.
                  </p>
                </div>
              </motion.div>
            )}

            {result && (
              <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="space-y-4">
                <p className="text-sm text-muted-foreground/60">
                  Top {result.matches.length} style matches — ranked by aesthetic similarity
                </p>
                {result.matches.map((match, i) => (
                  <CelebrityCard key={match.name} match={match} index={i} />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
