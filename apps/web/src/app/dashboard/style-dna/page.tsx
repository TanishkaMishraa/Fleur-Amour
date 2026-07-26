"use client";
/**
 * AuraFit — Style DNA Dashboard Page (Stage 8).
 *
 * THE flagship feature. Assembles every piece of Stage 0–7 into one
 * personalised report.
 *
 * Flow:
 *   A) No report + no quiz → landing state → start quiz
 *   B) Quiz in progress    → quiz UI (inline, full-screen feel)
 *   C) Quiz done           → generate report CTA
 *   D) Report generating   → polling skeleton
 *   E) Report ready        → full report with all 8 sections + PDF download
 *
 * Data sources assembled into the report:
 *   - UserProfile (skin tone, body shape, budget, style archetypes)
 *   - FacialScan  (undertone, face shape, acne, symmetry, hair)
 *   - ColorProfile (season, palette, makeup recs)
 *   - QuizSession  (personality axes, archetypes, lifestyle)
 *   - InteractionHistory (top categories and brands)
 */
import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, Download, RefreshCw, ChevronRight,
  FileText, Dna, Star, ArrowRight, Lock,
} from "lucide-react";
import { Button }       from "@/components/ui/button";
import { Badge }        from "@/components/ui/badge";
import { Progress }     from "@/components/ui/progress";
import { Skeleton }     from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { GoldDivider }  from "@/components/shared/GoldDivider";
import { StyleDNAQuizUI } from "@/components/features/quiz/StyleDNAQuiz";
import {
  SkinProfileCard,
  ColorProfileCard,
  FashionProfileCard,
  FragranceProfileCard,
  HairstyleProfileCard,
  OccasionGuideCard,
  PersonalityCard,
} from "@/components/features/style-dna/ReportSections";
import {
  useCurrentReport,
  useGenerateReport,
  useQuiz,
} from "@/lib/api/style-dna";
import type { StyleDNAReport } from "@/types/style-dna";
import { ARCHETYPE_META, SECTION_META } from "@/types/style-dna";
import { cn } from "@/lib/utils";

// ── Animation presets ─────────────────────────────────────────────────────────

const fadeUp = (i = 0) => ({
  initial:    { opacity: 0, y: 16 },
  animate:    { opacity: 1, y: 0  },
  transition: { delay: i * 0.07, duration: 0.45, ease: [0.23, 1, 0.32, 1] as const },
});

// ── Sub-components ─────────────────────────────────────────────────────────────

function ArchetypeBadge({ archetype, size = "md" }: { archetype: string; size?: "sm" | "md" | "lg" }) {
  const meta = ARCHETYPE_META[archetype];
  if (!meta) return <Badge>{archetype}</Badge>;
  const sizes = { sm: "text-2xs px-3 py-1", md: "text-xs px-4 py-1.5", lg: "text-sm px-5 py-2" };
  return (
    <div className={cn(
      "inline-flex items-center gap-2 rounded-full font-semibold",
      `bg-gradient-to-r ${meta.gradient}`,
      "text-white shadow-sm",
      sizes[size],
    )}>
      <span>{meta.emoji}</span>
      <span>{archetype}</span>
    </div>
  );
}

function SectionSkeleton() {
  return (
    <div className="luxury-card p-6 space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-6 w-6 rounded-full" />
        <Skeleton className="h-4 w-36" />
      </div>
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-5/6" />
      <Skeleton className="h-3 w-4/6" />
      <div className="grid grid-cols-3 gap-3 pt-2">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-8 rounded-xl" />)}
      </div>
    </div>
  );
}

function LandingHero({ onStart }: { onStart: () => void }) {
  return (
    <motion.div {...fadeUp(0)} className="text-center space-y-10 py-12">
      {/* Animated DNA icon */}
      <div className="relative mx-auto">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="mx-auto h-28 w-28 rounded-full bg-gradient-to-br from-brand-gold via-rose-400 to-purple-500 p-0.5"
        >
          <div className="h-full w-full rounded-full bg-obsidian flex items-center justify-center">
            <Dna className="h-12 w-12 text-brand-gold" />
          </div>
        </motion.div>
        <motion.div
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          className="absolute inset-0 rounded-full bg-brand-gold/10 blur-xl"
        />
      </div>

      <div className="space-y-3 max-w-xl mx-auto">
        <h1 className="font-display text-display-lg font-light tracking-tightest">
          Your Style DNA
        </h1>
        <p className="text-lg text-muted-foreground leading-relaxed">
          A complete profile of your beauty identity — skin, colour, fragrance,
          fashion and personality — assembled from your analyses and a 5-minute quiz.
        </p>
      </div>

      {/* What goes in */}
      <div className="grid gap-3 sm:grid-cols-3 max-w-2xl mx-auto text-left">
        {[
          { emoji: "🤳", label: "Facial Analysis",     desc: "Skin tone, undertone, face shape, acne profile" },
          { emoji: "🎨", label: "Color Season",         desc: "12-season palette, makeup, and jewellery guide" },
          { emoji: "🧭", label: "Personality Quiz",     desc: "35 questions across 5 lifestyle dimensions" },
        ].map((item) => (
          <div key={item.label} className="luxury-card p-4 space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-lg">{item.emoji}</span>
              <p className="text-sm font-semibold text-foreground">{item.label}</p>
            </div>
            <p className="text-2xs text-muted-foreground/60">{item.desc}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col items-center gap-4">
        <Button variant="gold" size="lg" onClick={onStart} className="gap-3 min-w-[220px]">
          <Sparkles className="h-5 w-5" />
          Discover Your Style DNA
        </Button>
        <p className="text-2xs text-muted-foreground/40">5 minutes · 35 questions · Free forever</p>
      </div>
    </motion.div>
  );
}

function QuizCompletionCelebration({
  archetype, onGenerate, isGenerating,
}: {
  archetype: string;
  onGenerate: () => void;
  isGenerating: boolean;
}) {
  const meta = ARCHETYPE_META[archetype] ?? ARCHETYPE_META["The Classic"];
  return (
    <motion.div {...fadeUp(0)} className="text-center space-y-8 py-12 max-w-xl mx-auto">
      <div className={cn(
        "mx-auto h-24 w-24 rounded-3xl flex items-center justify-center text-5xl shadow-luxury-lg",
        `bg-gradient-to-br ${meta.gradient}`
      )}>
        {meta.emoji}
      </div>
      <div className="space-y-3">
        <p className="text-2xs uppercase tracking-widest text-brand-gold/60">
          Your primary archetype
        </p>
        <ArchetypeBadge archetype={archetype} size="lg" />
        <p className={cn("text-sm italic", meta.color)}>{meta.tagline}</p>
      </div>
      <GoldDivider />
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Quiz complete. Now generate your full Style DNA Report — it combines your
          quiz results with your skin analysis and colour season.
        </p>
        <Button
          variant="gold"
          size="lg"
          onClick={onGenerate}
          loading={isGenerating}
          className="gap-2"
        >
          <Sparkles className="h-5 w-5" />
          Generate My Style DNA Report
        </Button>
      </div>
    </motion.div>
  );
}

function GeneratingState() {
  const [step, setStep] = useState(0);
  const steps = [
    "Reading your skin analysis…",
    "Mapping your colour season…",
    "Analysing your style dimensions…",
    "Building your beauty profile…",
    "Composing your fashion profile…",
    "Crafting fragrance recommendations…",
    "Writing your Style DNA narrative…",
    "Finalising your report…",
  ];

  useEffect(() => {
    const t = setInterval(() => setStep((s) => Math.min(s + 1, steps.length - 1)), 1800);
    return () => clearInterval(t);
  }, []);

  return (
    <motion.div {...fadeUp(0)} className="text-center space-y-8 py-16">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        className="mx-auto h-16 w-16 rounded-full border-2 border-brand-gold/20 border-t-brand-gold"
      />
      <div className="space-y-2">
        <h2 className="font-display text-display-sm font-light">Generating your report…</h2>
        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="text-sm text-muted-foreground/60"
          >
            {steps[step]}
          </motion.p>
        </AnimatePresence>
      </div>
      <Progress value={(step / (steps.length - 1)) * 100} gold className="max-w-sm mx-auto h-1" />
    </motion.div>
  );
}

function ReportHeader({ report, onRegenerate, isRegenerating }: {
  report: StyleDNAReport;
  onRegenerate: () => void;
  isRegenerating: boolean;
}) {
  const archetype = (report.fashion_profile?.primary_archetype as string) ??
                    (report.personality?.primary_archetype as string) ?? "The Classic";
  const meta = ARCHETYPE_META[archetype] ?? ARCHETYPE_META["The Classic"];

  return (
    <motion.div {...fadeUp(0)} className="space-y-6">
      {/* Hero gradient header */}
      <div className={cn(
        "relative overflow-hidden rounded-3xl p-8 bg-gradient-to-br noise",
        meta.gradient,
      )}>
        <div className="absolute inset-0 bg-black/20" />
        <div className="relative z-10 space-y-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="space-y-2">
              <p className="text-2xs uppercase tracking-widest text-white/60">Your Style DNA</p>
              <h1 className="font-display text-3xl sm:text-4xl text-white font-light leading-tight">
                {report.headline ?? "Your Unique Beauty Story"}
              </h1>
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <ArchetypeBadge archetype={archetype} size="md" />
                {report.fashion_profile?.secondary_archetype && (
                  <span className="text-xs text-white/60">
                    + {report.fashion_profile.secondary_archetype as string}
                  </span>
                )}
              </div>
            </div>
            <div className="text-5xl">{meta.emoji}</div>
          </div>
          {report.narrative && (
            <p className="text-sm text-white/80 leading-relaxed max-w-xl">
              {report.narrative}
            </p>
          )}
        </div>
      </div>

      {/* Action bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 text-xs text-muted-foreground/50">
          <Star className="h-3.5 w-3.5 text-brand-gold" />
          Generated from your full AuraFit profile
          {!report.is_current && (
            <Badge variant="default" className="text-2xs">Outdated — regenerate for latest</Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {report.pdf_url && (
            <a href={report.pdf_url} target="_blank" rel="noopener noreferrer">
              <Button variant="ghost-gold" size="sm" className="gap-2">
                <Download className="h-4 w-4" />
                Download PDF
                {report.pdf_size_kb && (
                  <span className="text-2xs text-muted-foreground/40">
                    ({Math.round(report.pdf_size_kb / 1024 * 10) / 10}MB)
                  </span>
                )}
              </Button>
            </a>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={onRegenerate}
            loading={isRegenerating}
            className="gap-2"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Regenerate
          </Button>
        </div>
      </div>
    </motion.div>
  );
}

function ReportSections({ report }: { report: StyleDNAReport }) {
  const availableSections = SECTION_META.filter(
    (s) => report[s.key as keyof StyleDNAReport] != null
  );

  return (
    <Tabs defaultValue={availableSections[0]?.key ?? "skin_profile"} className="space-y-6">
      {/* Tab bar */}
      <TabsList className="flex-wrap h-auto gap-1 p-1.5 w-full">
        {availableSections.map((sec) => (
          <TabsTrigger key={sec.key} value={sec.key} className="gap-1.5 flex-shrink-0">
            <span>{sec.emoji}</span>
            <span className="hidden sm:inline text-xs">{sec.label}</span>
          </TabsTrigger>
        ))}
      </TabsList>

      {/* Section content */}
      {report.skin_profile && (
        <TabsContent value="skin_profile">
          <motion.div {...fadeUp(0)}>
            <SkinProfileCard data={report.skin_profile} />
          </motion.div>
        </TabsContent>
      )}

      {report.color_profile_section && (
        <TabsContent value="color_profile_section">
          <motion.div {...fadeUp(0)}>
            <ColorProfileCard data={report.color_profile_section} />
          </motion.div>
        </TabsContent>
      )}

      {report.fashion_profile && (
        <TabsContent value="fashion_profile">
          <motion.div {...fadeUp(0)}>
            <FashionProfileCard data={report.fashion_profile} />
          </motion.div>
        </TabsContent>
      )}

      {report.fragrance_profile_section && (
        <TabsContent value="fragrance_profile_section">
          <motion.div {...fadeUp(0)}>
            <FragranceProfileCard data={report.fragrance_profile_section} />
          </motion.div>
        </TabsContent>
      )}

      {report.hairstyle_profile && (
        <TabsContent value="hairstyle_profile">
          <motion.div {...fadeUp(0)}>
            <HairstyleProfileCard data={report.hairstyle_profile} />
          </motion.div>
        </TabsContent>
      )}

      {report.personality && (
        <TabsContent value="personality">
          <motion.div {...fadeUp(0)}>
            <PersonalityCard data={report.personality} />
          </motion.div>
        </TabsContent>
      )}

      {report.occasion_guide && (
        <TabsContent value="occasion_guide">
          <motion.div {...fadeUp(0)}>
            <OccasionGuideCard data={report.occasion_guide} />
          </motion.div>
        </TabsContent>
      )}

      {report.recommendations && (
        <TabsContent value="recommendations">
          <RecommendationsSection data={report.recommendations} />
        </TabsContent>
      )}
    </Tabs>
  );
}

function RecommendationsSection({ data }: { data: Record<string, unknown[]> }) {
  const domains = Object.entries(data).filter(([, items]) => Array.isArray(items) && items.length > 0);
  if (!domains.length) {
    return (
      <div className="luxury-card p-8 text-center text-sm text-muted-foreground/50">
        Recommendations will appear after syncing with the product catalog.
      </div>
    );
  }
  return (
    <div className="space-y-6">
      {domains.map(([domain, items]) => (
        <div key={domain} className="luxury-card p-6 space-y-4">
          <p className="text-sm font-semibold capitalize text-foreground">{domain}</p>
          <ul className="space-y-2">
            {(items as any[]).slice(0, 6).map((item: any, i: number) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-foreground/70">
                <ChevronRight className="h-3.5 w-3.5 text-brand-gold/60 mt-0.5 flex-shrink-0" />
                <span>{typeof item === "string" ? item : item.name ?? JSON.stringify(item)}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

type PagePhase =
  | "loading"
  | "landing"          // No quiz, no report
  | "quiz"             // Taking quiz
  | "quiz-done"        // Quiz complete, not yet generated
  | "generating"       // Report generating
  | "report";          // Report ready

export default function StyleDNAPage() {
  const { data: report, isLoading: reportLoading, refetch } = useCurrentReport();
  const { mutateAsync: generateReport, isPending: isGenerating } = useGenerateReport();
  const quiz = useQuiz();

  // Poll for report readiness while generating
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (report?.status === "generating" || report?.status === "queued") {
      pollingRef.current = setInterval(() => refetch(), 3000);
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [report?.status, refetch]);

  // Derive page phase
  let phase: PagePhase = "loading";
  if (!reportLoading) {
    if (quiz.phase === "in-progress") {
      phase = "quiz";
    } else if (quiz.phase === "complete" && !report) {
      phase = "quiz-done";
    } else if (quiz.phase === "complete" && report && (report.status === "queued" || report.status === "generating")) {
      phase = "generating";
    } else if (report?.status === "queued" || report?.status === "generating") {
      phase = "generating";
    } else if (report?.status === "ready") {
      phase = "report";
    } else if (quiz.result) {
      phase = "quiz-done";
    } else {
      phase = "landing";
    }
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-20">
      {/* Page header — shown always except during quiz */}
      {phase !== "quiz" && phase !== "loading" && (
        <motion.div {...fadeUp(0)} className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-2xs uppercase tracking-widest text-brand-gold/70">
              <Dna className="h-3.5 w-3.5" />
              Style DNA System
            </div>
            <h1 className="font-display text-display-md font-light tracking-tightest">
              {phase === "report" ? "Your Style DNA Report" : "Discover Your Style DNA"}
            </h1>
          </div>
        </motion.div>
      )}

      {phase !== "quiz" && phase !== "landing" && phase !== "loading" && (
        <GoldDivider />
      )}

      {/* Phase content */}
      <AnimatePresence mode="wait">

        {/* Loading */}
        {phase === "loading" && (
          <motion.div key="loading" {...fadeUp(0)} className="space-y-6">
            <SectionSkeleton />
            <div className="grid gap-4 sm:grid-cols-2">
              <SectionSkeleton /><SectionSkeleton />
            </div>
          </motion.div>
        )}

        {/* Landing */}
        {phase === "landing" && (
          <motion.div key="landing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <LandingHero onStart={() => quiz.startQuiz()} />
          </motion.div>
        )}

        {/* Quiz */}
        {phase === "quiz" && (
          <motion.div key="quiz" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {quiz.session_id && (
              <StyleDNAQuizUI
                sessionId={quiz.session_id}
                currentStep={quiz.current_step}
                totalSteps={quiz.total_steps}
                onRespond={quiz.respond}
                onComplete={quiz.completeQuiz}
                isCompleting={quiz.phase === "completing"}
              />
            )}
          </motion.div>
        )}

        {/* Quiz done — generate CTA */}
        {phase === "quiz-done" && quiz.result && (
          <motion.div key="quiz-done" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <QuizCompletionCelebration
              archetype={quiz.result.primary_archetype}
              onGenerate={async () => { await generateReport(); }}
              isGenerating={isGenerating}
            />
          </motion.div>
        )}

        {/* Generating */}
        {phase === "generating" && (
          <motion.div key="generating" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <GeneratingState />
          </motion.div>
        )}

        {/* Report ready */}
        {phase === "report" && report && (
          <motion.div key="report" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
            <ReportHeader
              report={report}
              onRegenerate={async () => { await generateReport(); }}
              isRegenerating={isGenerating}
            />
            <ReportSections report={report} />
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  );
}
