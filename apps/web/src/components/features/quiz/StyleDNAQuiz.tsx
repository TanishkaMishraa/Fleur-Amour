"use client";
/**
 * AuraFit — Style DNA Quiz UI (Stage 8).
 * 35-question adaptive quiz with 5 sections.
 * Supports single, multi, scale, and image_grid question types.
 */
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, ChevronRight, ArrowLeft, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { GoldDivider } from "@/components/shared/GoldDivider";
import { useQuizDefinition } from "@/lib/api/style-dna";
import type { QuizQuestion } from "@/types/style-dna";

const SECTION_LABELS: Record<string, { label: string; emoji: string }> = {
  personality: { label: "Personality",   emoji: "🧭" },
  fashion:     { label: "Fashion",        emoji: "👗" },
  lifestyle:   { label: "Lifestyle",      emoji: "🌿" },
  budget:      { label: "Budget",         emoji: "💎" },
  beauty:      { label: "Beauty",         emoji: "✨" },
};

interface QuizUIProps {
  sessionId:    string;
  currentStep:  number;
  totalSteps:   number;
  onRespond:    (qId: string, idx: number, val?: string | null, opts?: string[] | null) => Promise<void>;
  onComplete:   () => Promise<void>;
  isCompleting: boolean;
}

export function StyleDNAQuizUI({
  sessionId, currentStep, totalSteps, onRespond, onComplete, isCompleting,
}: QuizUIProps) {
  const { data: quizDef, isLoading } = useQuizDefinition();
  const [currentAnswer, setCurrentAnswer] = useState<string | null>(null);
  const [multiAnswers,  setMultiAnswers]  = useState<string[]>([]);
  const [scaleValue,    setScaleValue]    = useState<number>(5);
  const [isSubmitting,  setIsSubmitting]  = useState(false);

  // Flatten questions in order
  const allQuestions: QuizQuestion[] = quizDef
    ? (quizDef.section_order || []).flatMap((s) => quizDef.sections[s] || [])
    : [];
  const currentQuestion = allQuestions[currentStep] ?? null;
  const isLastQuestion  = currentStep >= totalSteps - 1;
  const pct             = Math.round((currentStep / totalSteps) * 100);

  // Reset state when question changes
  useEffect(() => {
    setCurrentAnswer(null);
    setMultiAnswers([]);
    setScaleValue(5);
  }, [currentStep]);

  const canProceed = (() => {
    if (!currentQuestion) return false;
    if (currentQuestion.type === "multi") return multiAnswers.length >= 1;
    if (currentQuestion.type === "scale") return true;
    return currentAnswer !== null;
  })();

  const handleNext = async () => {
    if (!currentQuestion || !canProceed || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const val  = currentQuestion.type === "scale" ? String(scaleValue) : currentAnswer;
      const opts = currentQuestion.type === "multi" ? multiAnswers : null;
      await onRespond(currentQuestion.id, currentQuestion.index, val, opts);
      if (isLastQuestion) {
        await onComplete();
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleMulti = (optId: string, max: number) => {
    setMultiAnswers((prev) =>
      prev.includes(optId)
        ? prev.filter((id) => id !== optId)
        : prev.length >= max ? prev : [...prev, optId]
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 rounded-full border-2 border-brand-gold/20 border-t-brand-gold animate-spin" />
      </div>
    );
  }

  if (!currentQuestion) return null;

  const sectionMeta = SECTION_LABELS[currentQuestion.section] ?? { label: currentQuestion.section, emoji: "✦" };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Progress */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-2xs text-muted-foreground/50">
          <span>{sectionMeta.emoji} {sectionMeta.label}</span>
          <span>{currentStep + 1} / {totalSteps}</span>
        </div>
        <Progress value={pct} gold className="h-1" />
      </div>

      {/* Question */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentQuestion.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
          className="space-y-6"
        >
          {/* Question text */}
          <div className="space-y-1.5">
            <h2 className="font-display text-display-sm font-light tracking-tightest">
              {currentQuestion.question}
            </h2>
            {currentQuestion.subtitle && (
              <p className="text-sm text-muted-foreground/60">{currentQuestion.subtitle}</p>
            )}
            {currentQuestion.type === "multi" && currentQuestion.max_select && (
              <p className="text-xs text-brand-gold/60">
                {multiAnswers.length} / {currentQuestion.max_select} selected
              </p>
            )}
          </div>

          {/* Single / image_grid options */}
          {(currentQuestion.type === "single" || currentQuestion.type === "image_grid") && (
            <div className={cn(
              "grid gap-3",
              currentQuestion.type === "image_grid" ? "grid-cols-2 sm:grid-cols-3" : "grid-cols-1"
            )}>
              {currentQuestion.options.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setCurrentAnswer(opt.id)}
                  className={cn(
                    "text-left rounded-2xl border p-4 transition-all duration-200 ease-luxury",
                    currentAnswer === opt.id
                      ? "border-brand-gold/50 bg-brand-gold/10 text-foreground"
                      : "border-white/[0.06] bg-white/[0.02] text-foreground/70 hover:border-white/[0.15] hover:bg-white/[0.04]"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "h-4 w-4 rounded-full border-2 flex-shrink-0 transition-all",
                      currentAnswer === opt.id
                        ? "border-brand-gold bg-brand-gold"
                        : "border-white/20"
                    )}>
                      {currentAnswer === opt.id && (
                        <Check className="h-3 w-3 text-brand-black m-auto" />
                      )}
                    </div>
                    <span className="text-sm leading-snug">{opt.label}</span>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Multi-select options */}
          {currentQuestion.type === "multi" && (
            <div className="grid gap-2.5 sm:grid-cols-2">
              {currentQuestion.options.map((opt) => {
                const selected = multiAnswers.includes(opt.id);
                const maxed = multiAnswers.length >= (currentQuestion.max_select ?? 99) && !selected;
                return (
                  <button
                    key={opt.id}
                    onClick={() => !maxed && toggleMulti(opt.id, currentQuestion.max_select ?? 10)}
                    disabled={maxed}
                    className={cn(
                      "text-left rounded-2xl border p-3.5 transition-all duration-200",
                      selected
                        ? "border-brand-gold/50 bg-brand-gold/10"
                        : maxed
                          ? "border-white/[0.04] bg-transparent opacity-40 cursor-not-allowed"
                          : "border-white/[0.06] bg-white/[0.02] hover:border-white/[0.15]"
                    )}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className={cn(
                        "h-4 w-4 rounded flex-shrink-0 border-2 flex items-center justify-center",
                        selected ? "border-brand-gold bg-brand-gold" : "border-white/20"
                      )}>
                        {selected && <Check className="h-2.5 w-2.5 text-brand-black" />}
                      </div>
                      <span className="text-sm text-foreground/80">{opt.label}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* Scale */}
          {currentQuestion.type === "scale" && (
            <div className="space-y-6 py-4">
              <div className="space-y-3">
                <input
                  type="range"
                  min={currentQuestion.scale_min ?? 0}
                  max={currentQuestion.scale_max ?? 10}
                  value={scaleValue}
                  onChange={(e) => setScaleValue(Number(e.target.value))}
                  className="w-full accent-brand-gold h-1.5 rounded cursor-pointer"
                />
                <div className="flex justify-between text-xs text-muted-foreground/50">
                  <span>{currentQuestion.scale_labels?.[0] ?? "Low"}</span>
                  <span className="text-brand-gold font-semibold text-sm">{scaleValue}</span>
                  <span>{currentQuestion.scale_labels?.[1] ?? "High"}</span>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div className="flex items-center justify-end pt-4">
        <Button
          variant="gold"
          onClick={handleNext}
          disabled={!canProceed || isSubmitting || isCompleting}
          loading={isSubmitting || isCompleting}
          className="min-w-[140px]"
        >
          {isLastQuestion ? (
            <>Generate My DNA <Sparkles className="h-4 w-4" /></>
          ) : (
            <>Next <ChevronRight className="h-4 w-4" /></>
          )}
        </Button>
      </div>
    </div>
  );
}
