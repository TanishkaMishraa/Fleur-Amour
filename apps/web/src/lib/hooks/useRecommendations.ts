/**
 * AuraFit — useRecommendations hooks (Stage 6).
 */
import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/lib/stores/auth.store";
import { recommendationApi, catalogApi, type RecRequest, type SearchParams } from "@/lib/api/recommendations";
import type { RecDomain, RecommendationResponse } from "@/types/recommendations";

// ── Domain recommendations hook ───────────────────────────────────────────────

export function useRecommendations(
  domain: RecDomain,
  options?: { occasion?: string; season?: string; budget_max?: number; limit?: number }
) {
  const { user } = useAuthStore();
  const userId = user?.id ?? "";

  return useQuery({
    queryKey: ["recommendations", domain, userId, options],
    enabled: !!userId,
    queryFn: async () => {
      const { data } = await recommendationApi.getRecommendations({
        user_id: userId,
        domain,
        ...options,
        limit: options?.limit ?? 20,
      });
      return data;
    },
    staleTime: 1000 * 60 * 5,    // 5 min — recs are personalised, refresh often
    gcTime:    1000 * 60 * 15,
  });
}

// ── Feedback mutation ─────────────────────────────────────────────────────────

export function useRecFeedback() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      recId,
      clicked = false,
      saved = false,
      purchased = false,
    }: { recId: string; clicked?: boolean; saved?: boolean; purchased?: boolean }) =>
      recommendationApi.sendFeedback(recId, { clicked, saved, purchased }),
    onSuccess: () => {
      // Stale all recommendation queries after feedback (preferences may have shifted)
      queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });
}

// ── Interaction recording ─────────────────────────────────────────────────────

export function useRecordInteraction() {
  const { user } = useAuthStore();
  return useMutation({
    mutationFn: (payload: {
      product_id: string;
      interaction_type: string;
      rating?: number;
    }) =>
      recommendationApi.recordInteraction({
        user_id: user?.id ?? "",
        ...payload,
      }),
  });
}

// ── Product catalog hooks ─────────────────────────────────────────────────────

export function useProductSearch(params: SearchParams) {
  return useQuery({
    queryKey: ["products", "search", params],
    queryFn: () => catalogApi.searchProducts(params).then((r) => r.data),
    staleTime: 1000 * 60 * 2,
    placeholderData: (prev) => prev,
  });
}

export function useProduct(productId: string | undefined) {
  return useQuery({
    queryKey: ["product", productId],
    enabled: !!productId,
    queryFn: () => catalogApi.getProduct(productId!).then((r) => r.data),
    staleTime: 1000 * 60 * 10,
  });
}

export function useSimilarProducts(productId: string | undefined, limit = 8) {
  return useQuery({
    queryKey: ["product", productId, "similar"],
    enabled: !!productId,
    queryFn: () => catalogApi.getSimilarProducts(productId!, limit).then((r) => r.data),
    staleTime: 1000 * 60 * 10,
  });
}

export function useCategories(parentId?: string) {
  return useQuery({
    queryKey: ["categories", parentId],
    queryFn: () => catalogApi.listCategories(parentId).then((r) => r.data),
    staleTime: Infinity,
  });
}
