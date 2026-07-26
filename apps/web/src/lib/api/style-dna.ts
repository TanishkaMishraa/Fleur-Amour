/**
 * AuraFit — Style DNA API client & hooks (Stage 8).
 */
import { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { ApiResponse } from "@/types";
import type {
  QuizCompletionResult, QuizDefinition, QuizSessionState, StyleDNAReport,
} from "@/types/style-dna";

// ── API client ────────────────────────────────────────────────────────────────

export const styleDnaApi = {
  getQuizDefinition: () =>
    apiClient.get<QuizDefinition>("/style-dna/quiz"),

  startQuiz: () =>
    apiClient.post<ApiResponse<QuizSessionState>>("/style-dna/quiz/start"),

  respond: (sessionId: string, payload: {
    question_id: string;
    question_index: number;
    answer_value?: string | null;
    answer_options?: string[] | null;
  }) =>
    apiClient.post<ApiResponse<{ current_step: number; total_steps: number; is_complete: boolean }>>(
      `/style-dna/quiz/${sessionId}/respond`, payload
    ),

  completeQuiz: (sessionId: string) =>
    apiClient.post<ApiResponse<QuizCompletionResult>>(
      `/style-dna/quiz/${sessionId}/complete`
    ),

  generateReport: () =>
    apiClient.post<ApiResponse<{ report_id: string; status: string }>>("/style-dna/generate"),

  getCurrentReport: () =>
    apiClient.get<ApiResponse<StyleDNAReport | null>>("/style-dna/report"),

  getReport: (reportId: string) =>
    apiClient.get<ApiResponse<StyleDNAReport>>(`/style-dna/report/${reportId}`),

  getReportHistory: () =>
    apiClient.get<ApiResponse<StyleDNAReport[]>>("/style-dna/report/history"),

  getReportSection: (reportId: string, section: string) =>
    apiClient.get<ApiResponse<unknown>>(`/style-dna/report/${reportId}/section/${section}`),
};

// ── React Query hooks ─────────────────────────────────────────────────────────

export function useQuizDefinition() {
  return useQuery({
    queryKey: ["quiz-definition"],
    queryFn:  () => styleDnaApi.getQuizDefinition().then((r) => r.data),
    staleTime: Infinity,
  });
}

export function useCurrentReport() {
  return useQuery({
    queryKey: ["style-dna-report"],
    queryFn:  async () => {
      const { data } = await styleDnaApi.getCurrentReport();
      return data.data ?? null;
    },
    staleTime: 1000 * 60 * 10,
  });
}

export function useReportHistory() {
  return useQuery({
    queryKey: ["style-dna-history"],
    queryFn:  async () => {
      const { data } = await styleDnaApi.getReportHistory();
      return data.data ?? [];
    },
    staleTime: 1000 * 60 * 5,
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await styleDnaApi.generateReport();
      if (!data.success) throw new Error(data.errors?.[0]?.message ?? "Generation failed");
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["style-dna-report"] });
      queryClient.invalidateQueries({ queryKey: ["style-dna-history"] });
    },
  });
}

// ── Quiz session hook ─────────────────────────────────────────────────────────

interface QuizState {
  phase:      "idle" | "loading-def" | "in-progress" | "completing" | "complete" | "error";
  session_id: string | null;
  current_step: number;
  total_steps:  number;
  result:     QuizCompletionResult | null;
  error:      string | null;
}

export function useQuiz() {
  const [state, setState] = useState<QuizState>({
    phase: "idle", session_id: null, current_step: 0,
    total_steps: 35, result: null, error: null,
  });
  const queryClient = useQueryClient();

  const startQuiz = useCallback(async () => {
    setState((s) => ({ ...s, phase: "loading-def" }));
    try {
      const { data } = await styleDnaApi.startQuiz();
      if (!data.success || !data.data) throw new Error("Failed to start quiz");
      setState((s) => ({
        ...s, phase: "in-progress",
        session_id:   data.data!.session_id,
        current_step: data.data!.current_step,
        total_steps:  data.data!.total_steps,
      }));
    } catch (err: any) {
      setState((s) => ({ ...s, phase: "error", error: err.message }));
    }
  }, []);

  const respond = useCallback(async (
    questionId: string,
    questionIndex: number,
    answerValue?: string | null,
    answerOptions?: string[] | null,
  ) => {
    if (!state.session_id) return;
    try {
      const { data } = await styleDnaApi.respond(state.session_id, {
        question_id: questionId,
        question_index: questionIndex,
        answer_value: answerValue,
        answer_options: answerOptions,
      });
      if (data.success && data.data) {
        setState((s) => ({
          ...s,
          current_step: data.data!.current_step,
        }));
      }
    } catch {}
  }, [state.session_id]);

  const completeQuiz = useCallback(async () => {
    if (!state.session_id) return;
    setState((s) => ({ ...s, phase: "completing" }));
    try {
      const { data } = await styleDnaApi.completeQuiz(state.session_id);
      if (!data.success || !data.data) throw new Error("Failed to complete quiz");
      setState((s) => ({ ...s, phase: "complete", result: data.data! }));
      queryClient.invalidateQueries({ queryKey: ["style-dna-report"] });
    } catch (err: any) {
      setState((s) => ({ ...s, phase: "error", error: err.message }));
    }
  }, [state.session_id, queryClient]);

  return { ...state, startQuiz, respond, completeQuiz };
}
