/**
 * AuraFit — useFacialScan hook (Stage 4).
 * Orchestrates: file upload → task dispatch → polling → result.
 * Polling interval backs off slightly to avoid hammering the API for
 * longer-running analyses (DeepFace age model can take 1-3s).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { analysisApi, uploadAndStartScan } from "@/lib/api/analysis";
import type { FacialScanRecord, FullAnalysisResult, ScanTaskStatus } from "@/types";

type ScanPhase = "idle" | "uploading" | "queued" | "analyzing" | "complete" | "error";

interface UseFacialScanResult {
  phase: ScanPhase;
  progress: number;
  step: string | null;
  result: FullAnalysisResult | null;
  error: string | null;
  taskId: string | null;
  start: (file: File) => Promise<void>;
  reset: () => void;
}

const POLL_INTERVAL_MS = 1500;
const MAX_POLL_ATTEMPTS = 80; // ~2 minutes ceiling

export function useFacialScan(): UseFacialScanResult {
  const [phase, setPhase]     = useState<ScanPhase>("idle");
  const [progress, setProgress] = useState(0);
  const [step, setStep]       = useState<string | null>(null);
  const [result, setResult]   = useState<FullAnalysisResult | null>(null);
  const [error, setError]     = useState<string | null>(null);
  const [taskId, setTaskId]   = useState<string | null>(null);

  const pollCount = useRef(0);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queryClient = useQueryClient();

  const clearTimer = () => {
    if (pollTimer.current) {
      clearTimeout(pollTimer.current);
      pollTimer.current = null;
    }
  };

  const poll = useCallback(async (id: string) => {
    try {
      const { data } = await analysisApi.getTaskStatus(id);
      const status: ScanTaskStatus | null = data.data;
      if (!status) throw new Error("No task status returned");

      setProgress(status.progress ?? progressForStatus(status.status));
      setStep(status.step ?? stepLabelForStatus(status.status));

      if (status.status === "SUCCESS") {
        const payload = status.result;
        if (payload?.success && payload.result) {
          setResult(payload.result);
          setPhase("complete");
          setProgress(100);
          // Invalidate cached scan list/profile so dashboard reflects new scan
          queryClient.invalidateQueries({ queryKey: ["facial-scans"] });
          queryClient.invalidateQueries({ queryKey: ["latest-scan"] });
          return;
        }
        // SUCCESS at the Celery level but pipeline returned a logical failure
        setError(payload?.error_message ?? "Analysis did not complete successfully.");
        setPhase("error");
        return;
      }

      if (status.status === "FAILURE") {
        setError(status.error ?? "Analysis failed. Please try again with a clearer photo.");
        setPhase("error");
        return;
      }

      // Still pending/started/progress — keep polling
      pollCount.current += 1;
      if (pollCount.current > MAX_POLL_ATTEMPTS) {
        setError("Analysis is taking longer than expected. Please try again.");
        setPhase("error");
        return;
      }
      pollTimer.current = setTimeout(() => poll(id), POLL_INTERVAL_MS);
    } catch {
      pollCount.current += 1;
      if (pollCount.current > MAX_POLL_ATTEMPTS) {
        setError("Lost connection while checking analysis status.");
        setPhase("error");
        return;
      }
      pollTimer.current = setTimeout(() => poll(id), POLL_INTERVAL_MS * 2);
    }
  }, [queryClient]);

  const start = useCallback(async (file: File) => {
    clearTimer();
    pollCount.current = 0;
    setError(null);
    setResult(null);
    setProgress(5);
    setPhase("uploading");
    setStep("Uploading your photo");

    try {
      const id = await uploadAndStartScan(file);
      setTaskId(id);
      setPhase("queued");
      setProgress(15);
      setStep("Queued for analysis");
      pollTimer.current = setTimeout(() => poll(id), 800);
    } catch (err: any) {
      setError(err?.message ?? "Upload failed. Please try again.");
      setPhase("error");
    }
  }, [poll]);

  const reset = useCallback(() => {
    clearTimer();
    pollCount.current = 0;
    setPhase("idle");
    setProgress(0);
    setStep(null);
    setResult(null);
    setError(null);
    setTaskId(null);
  }, []);

  useEffect(() => () => clearTimer(), []);

  return { phase, progress, step, result, error, taskId, start, reset };
}

function progressForStatus(status: string): number {
  switch (status) {
    case "PENDING": return 15;
    case "STARTED": return 30;
    case "PROGRESS": return 60;
    default: return 0;
  }
}

function stepLabelForStatus(status: string): string {
  switch (status) {
    case "PENDING": return "Queued for analysis";
    case "STARTED": return "Detecting your face";
    case "PROGRESS": return "Analyzing skin, tone & features";
    default: return "Processing";
  }
}

/** React Query hook: fetch the latest active scan for the dashboard. */
export function useLatestScan() {
  return useQuery({
    queryKey: ["latest-scan"],
    queryFn: async () => {
      const { data } = await analysisApi.getLatestScan();
      return data.data;
    },
    staleTime: 1000 * 60,
  });
}

/** React Query hook: scan history list. */
export function useScanHistory() {
  return useQuery({
    queryKey: ["facial-scans"],
    queryFn: async () => {
      const { data } = await analysisApi.listScans();
      return data.data ?? [];
    },
    staleTime: 1000 * 60,
  });
}

/**
 * React Query hook: fetch a single scan by ID for the history detail page.
 * Reconstructs a FullAnalysisResult-shaped object from the stored
 * skin_analysis / facial_features JSON so the same result cards used on
 * the live analysis page can render historical scans.
 */
export function useScan(scanId: string | undefined) {
  return useQuery({
    queryKey: ["facial-scan", scanId],
    enabled: !!scanId,
    queryFn: async () => {
      const { data } = await analysisApi.getScanById(scanId!);
      const scan = data.data;
      if (!scan) throw new Error("Scan not found");
      return { scan, result: scanToAnalysisResult(scan) };
    },
    staleTime: 1000 * 60 * 5,
  });
}

/**
 * Reconstruct a FullAnalysisResult-shaped object from a persisted
 * FacialScanRecord. The stored skin_analysis JSON mirrors the AI service's
 * AnalysisResult contract (see ai/facial-analysis/app/schemas), so this is
 * mostly a direct remap with safe fallbacks for older/partial scans.
 */
export function scanToAnalysisResult(scan: FacialScanRecord): FullAnalysisResult | null {
  const sa = scan.skin_analysis as Record<string, any> | null;
  const ff = scan.facial_features as Record<string, any> | null;
  if (!sa || sa.error) return null;

  return {
    pipeline_version: scan.model_version ?? "unknown",
    processing_time_ms: 0,
    quality: {
      passed: true,
      brisque_score: scan.quality_score ?? 0,
      face_visible: true,
      face_centered: true,
      good_lighting: true,
      no_occlusion: true,
      rejection_reason: null,
    },
    face_shape: {
      shape: (scan.face_shape as any) ?? "unknown",
      confidence: 1,
      ratios: ff?.face_shape_ratios ?? {},
      description: ff?.face_shape_description ?? "",
    },
    bounding_box: ff?.bounding_box ?? { x: 0, y: 0, w: 0, h: 0, confidence: 1 },
    mesh_points: [],
    symmetry: sa.symmetry,
    skin_tone: sa.skin_tone,
    age_estimation: sa.age_estimation,
    acne_analysis: sa.acne_analysis,
    dark_circles: sa.dark_circles,
    skin_texture: sa.skin_texture,
    skin_concerns: sa.skin_concerns ?? [],
    hair_analysis: sa.hair_analysis,
    makeup_recommendations: sa.makeup_recommendations ?? {},
    skincare_recommendations: sa.skincare_recommendations ?? {},
    hairstyle_recommendations: sa.hairstyle_recommendations ?? [],
  };
}
