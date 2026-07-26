"use client";
/**
 * AuraFit — Facial scan history detail page (Stage 4).
 * Renders a previously completed scan using the same result cards as the
 * live analysis page. The source selfie is not re-displayed (only the S3
 * key is persisted, never served back to the client for privacy), so this
 * view focuses entirely on the analysis results.
 */
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, CalendarDays, Sparkles, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GoldDivider } from "@/components/shared/GoldDivider";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { useScan } from "@/lib/hooks/useFacialScan";
import { SkinToneCard } from "@/components/features/analysis/SkinToneCard";
import { FaceShapeCard } from "@/components/features/analysis/FaceShapeCard";
import { SkinConcernsCard } from "@/components/features/analysis/SkinConcernsCard";
import { HairAgeSymmetryCard } from "@/components/features/analysis/HairAgeSymmetryCard";
import { RecommendationsCard } from "@/components/features/analysis/RecommendationsCard";

const anim = (i: number) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: i * 0.06, duration: 0.4, ease: [0.23, 1, 0.32, 1] as const },
});

export default function ScanDetailPage() {
  const params = useParams<{ scanId: string }>();
  const { data, isLoading, isError, error } = useScan(params.scanId);

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <motion.div {...anim(0)} className="space-y-4">
        <Button variant="ghost" size="sm" asChild className="-ml-2">
          <Link href="/dashboard/analysis">
            <ArrowLeft className="h-4 w-4" /> Back to Analysis
          </Link>
        </Button>

        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-2xs uppercase tracking-widest text-brand-gold/70">
              <Sparkles className="h-3.5 w-3.5" /> Scan History
            </div>
            <h1 className="font-display text-display-md font-light tracking-tightest">
              Scan Details
            </h1>
            {data?.scan && (
              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <CalendarDays className="h-3.5 w-3.5" />
                  {new Date(data.scan.created_at).toLocaleDateString(undefined, {
                    month: "long", day: "numeric", year: "numeric",
                  })}
                </span>
                {data.scan.is_active && (
                  <Badge variant="gold">
                    <ShieldCheck className="h-3 w-3" /> Active beauty profile
                  </Badge>
                )}
                {data.scan.model_version && (
                  <span className="text-2xs text-muted-foreground/40">
                    Pipeline v{data.scan.model_version}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </motion.div>

      <GoldDivider />

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center gap-4 py-24">
          <LoadingSpinner size="lg" />
          <p className="text-sm text-muted-foreground">Loading scan results…</p>
        </div>
      )}

      {/* Error */}
      {isError && (
        <motion.div {...anim(1)} className="luxury-card p-10 text-center space-y-3">
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : "This scan could not be found."}
          </p>
          <Button variant="ghost-gold" asChild>
            <Link href="/dashboard/analysis">
              <ArrowLeft className="h-4 w-4" /> Back to Analysis
            </Link>
          </Button>
        </motion.div>
      )}

      {/* Result is unavailable (older scan stored before this schema, or error) */}
      {data && !data.result && !isLoading && (
        <motion.div {...anim(1)} className="luxury-card p-10 text-center space-y-3">
          <p className="text-sm text-muted-foreground">
            This scan doesn't have detailed results available — it may have
            failed during processing or predate the current analysis pipeline.
          </p>
          <Button variant="ghost-gold" asChild>
            <Link href="/dashboard/analysis">
              <Sparkles className="h-4 w-4" /> Run a New Scan
            </Link>
          </Button>
        </motion.div>
      )}

      {/* Results */}
      {data?.result && (
        <div className="space-y-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <motion.div {...anim(1)}><SkinToneCard data={data.result.skin_tone} /></motion.div>
            <motion.div {...anim(2)}><FaceShapeCard data={data.result.face_shape} /></motion.div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <motion.div {...anim(3)}>
              <SkinConcernsCard
                acne={data.result.acne_analysis}
                darkCircles={data.result.dark_circles}
                texture={data.result.skin_texture}
                concerns={data.result.skin_concerns}
              />
            </motion.div>
            <motion.div {...anim(4)}>
              <HairAgeSymmetryCard
                age={data.result.age_estimation}
                hair={data.result.hair_analysis}
                symmetry={data.result.symmetry}
              />
            </motion.div>
          </div>

          <motion.div {...anim(5)}>
            <RecommendationsCard
              makeup={data.result.makeup_recommendations}
              skincare={data.result.skincare_recommendations}
              hairstyles={data.result.hairstyle_recommendations}
            />
          </motion.div>
        </div>
      )}
    </div>
  );
}
