"use client";
/**
 * AuraFit — AI Skin & Facial Analysis page (Stage 4).
 * Upload flow → live progress → full results dashboard with mesh overlay,
 * skin tone/undertone, face shape, concerns, hair/age/symmetry, and
 * personalised recommendations.
 */
import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, RotateCcw, History } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GoldDivider } from "@/components/shared/GoldDivider";
import { useFacialScan, useScanHistory } from "@/lib/hooks/useFacialScan";
import { ScanUploader } from "@/components/features/analysis/ScanUploader";
import { FaceMeshOverlay } from "@/components/features/analysis/FaceMeshOverlay";
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

export default function AnalysisPage() {
  const { phase, progress, step, result, error, start, reset } = useFacialScan();
  const { data: history } = useScanHistory();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleFile = (file: File) => {
    setPreviewUrl(URL.createObjectURL(file));
    start(file);
  };

  const handleReset = () => {
    reset();
    setPreviewUrl(null);
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <motion.div {...anim(0)} className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-2xs uppercase tracking-widest text-brand-gold/70">
            <Sparkles className="h-3.5 w-3.5" /> AI Facial Analysis
          </div>
          <h1 className="font-display text-display-md font-light tracking-tightest">
            Your Beauty Profile
          </h1>
          <p className="text-sm text-muted-foreground max-w-lg">
            Powered by MediaPipe face mesh, DeepFace, and computer vision — analysed
            entirely from a single photo, in seconds.
          </p>
        </div>

        {result && phase === "complete" && (
          <Button variant="ghost-gold" onClick={handleReset}>
            <RotateCcw className="h-4 w-4" /> New Scan
          </Button>
        )}
      </motion.div>

      <GoldDivider />

      {/* Upload / progress / error states */}
      {phase !== "complete" && (
        <motion.div {...anim(1)}>
          <ScanUploader
            phase={phase} progress={progress} step={step} error={error}
            onFile={handleFile} onRetry={handleReset}
          />
        </motion.div>
      )}

      {/* Results */}
      <AnimatePresence>
        {result && phase === "complete" && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="space-y-6"
          >
            {/* Photo + mesh + processing meta */}
            <div className="grid gap-6 lg:grid-cols-3">
              {previewUrl && (
                <motion.div {...anim(0)} className="lg:col-span-1">
                  <FaceMeshOverlay imageUrl={previewUrl} result={result} className="border border-white/[0.06]" />
                  <p className="mt-3 text-center text-2xs text-muted-foreground/40">
                    Analysed in {(result.processing_time_ms / 1000).toFixed(1)}s ·
                    Pipeline v{result.pipeline_version} ·
                    Quality score {Math.round(100 - result.quality.brisque_score)}/100
                  </p>
                </motion.div>
              )}

              <div className="lg:col-span-2 grid gap-6 sm:grid-cols-2">
                <motion.div {...anim(1)}><SkinToneCard data={result.skin_tone} /></motion.div>
                <motion.div {...anim(2)}><FaceShapeCard data={result.face_shape} /></motion.div>
              </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div {...anim(3)}>
                <SkinConcernsCard
                  acne={result.acne_analysis}
                  darkCircles={result.dark_circles}
                  texture={result.skin_texture}
                  concerns={result.skin_concerns}
                />
              </motion.div>
              <motion.div {...anim(4)}>
                <HairAgeSymmetryCard
                  age={result.age_estimation}
                  hair={result.hair_analysis}
                  symmetry={result.symmetry}
                />
              </motion.div>
            </div>

            <div className="grid gap-6 lg:grid-cols-1">
              <motion.div {...anim(5)}>
                <RecommendationsCard
                  makeup={result.makeup_recommendations}
                  skincare={result.skincare_recommendations}
                  hairstyles={result.hairstyle_recommendations}
                />
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Scan history */}
      {history && history.length > 0 && phase === "idle" && (
        <motion.div {...anim(2)} className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <History className="h-4 w-4" /> Previous Scans
          </div>
          <div className="flex gap-3 overflow-x-auto pb-2 hide-scrollbar">
            {history.map((scan) => (
              <Link
                key={scan.id}
                href={`/dashboard/analysis/${scan.id}`}
                className="flex-shrink-0 w-44 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-3 space-y-1.5 transition-all hover:border-brand-gold/30 hover:bg-white/[0.04]"
              >
                <p className="text-xs text-muted-foreground/50">
                  {new Date(scan.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                </p>
                <p className="text-sm font-medium capitalize">{scan.face_shape ?? "Unclassified"}</p>
                {scan.is_active && <span className="inline-block text-2xs text-brand-gold">Active profile</span>}
              </Link>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
