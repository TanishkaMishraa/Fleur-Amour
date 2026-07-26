/**
 * AuraFit — Smart Alternative Engine API client & React hooks (Stage 7).
 */
import axios from "axios";
import { useQuery } from "@tanstack/react-query";
import type { AlternativeGroupResponse } from "@/types/alternatives";

const altClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_REC_API_URL ?? "/rec-api/api/v1",
  timeout: 12000,
  headers: { "Content-Type": "application/json" },
});

// ── API client ──────────────────────────────────────────────────────────────

export const alternativeApi = {
  /** Get affordable alternatives for a product. */
  getAlternatives: (productId: string, params?: { limit?: number; min_similarity?: number }) =>
    altClient.get<AlternativeGroupResponse>(`/alternatives/${productId}`, { params }),

  /** Compare two hex shade codes. */
  compareShades: (hexA: string, hexB: string) =>
    altClient.post("/alternatives/compare/shade", { hex_a: hexA, hex_b: hexB }),

  /** Compare two INCI ingredient strings. */
  compareIngredients: (a: string, b: string) =>
    altClient.post("/alternatives/compare/ingredients", {
      ingredients_a: a, ingredients_b: b,
    }),

  /** Compare two fragrance attribute objects. */
  compareFragrance: (attrsA: Record<string, unknown>, attrsB: Record<string, unknown>) =>
    altClient.post("/alternatives/compare/fragrance", {
      attrs_a: attrsA, attrs_b: attrsB,
    }),
};

// ── React Query hooks ────────────────────────────────────────────────────────

/** Fetch alternatives for a product. Enabled only when price triggers the threshold. */
export function useAlternatives(
  productId: string | undefined,
  options?: { limit?: number; min_similarity?: number; enabled?: boolean }
) {
  return useQuery({
    queryKey: ["alternatives", productId, options?.limit, options?.min_similarity],
    enabled: !!productId && (options?.enabled !== false),
    queryFn: async () => {
      const { data } = await alternativeApi.getAlternatives(productId!, {
        limit:          options?.limit          ?? 5,
        min_similarity: options?.min_similarity ?? 0.40,
      });
      return data;
    },
    staleTime: 1000 * 60 * 30,   // 30 min — alternatives don't change often
    gcTime:    1000 * 60 * 60,
    retry: 1,
  });
}
