/**
 * AuraFit — useColorProfile hook (Stage 5).
 * Manages color intelligence data: compute, fetch, and history.
 */
import { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { colorApi } from "@/lib/api/color";
import type { ColorProfileRecord, FullColorAnalysisResponse } from "@/types/color";

// ── useColorProfile ───────────────────────────────────────────────────────────

/**
 * Primary hook: fetches the active color profile and exposes
 * compute + delete mutations.
 */
export function useColorProfile() {
  const queryClient = useQueryClient();
  const [liveResult, setLiveResult] = useState<FullColorAnalysisResponse | null>(null);

  // ── Active profile query ──────────────────────────────────────────────
  const {
    data: profile,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["color-profile"],
    queryFn: async () => {
      const { data } = await colorApi.getProfile();
      return data.data ?? null;
    },
    staleTime: 1000 * 60 * 10,  // 10 minutes — color profiles change rarely
  });

  // ── Compute mutation ──────────────────────────────────────────────────
  const computeMutation = useMutation({
    mutationFn: async (options?: { scanId?: string }) => {
      const { data } = await colorApi.compute({
        scan_id: options?.scanId,
        use_extended_seasons: true,
      });
      if (!data.success || !data.data) {
        throw new Error(data.errors?.[0]?.message ?? "Color analysis failed");
      }
      return data.data;
    },
    onSuccess: (result) => {
      setLiveResult(result);
      queryClient.invalidateQueries({ queryKey: ["color-profile"] });
      queryClient.invalidateQueries({ queryKey: ["color-history"] });
    },
  });

  // ── Delete mutation ───────────────────────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: (profileId: string) => colorApi.deleteProfile(profileId),
    onSuccess: () => {
      setLiveResult(null);
      queryClient.invalidateQueries({ queryKey: ["color-profile"] });
      queryClient.invalidateQueries({ queryKey: ["color-history"] });
    },
  });

  const compute = useCallback((scanId?: string) => {
    return computeMutation.mutateAsync({ scanId });
  }, [computeMutation]);

  return {
    profile,
    liveResult,
    isLoading,
    isError,
    isComputing: computeMutation.isPending,
    computeError: computeMutation.error?.message ?? null,
    compute,
    deleteProfile: deleteMutation.mutateAsync,
    refetch,
  };
}

// ── useColorHistory ───────────────────────────────────────────────────────────

export function useColorHistory() {
  return useQuery({
    queryKey: ["color-history"],
    queryFn: async () => {
      const { data } = await colorApi.getHistory();
      return data.data ?? [];
    },
    staleTime: 1000 * 60 * 5,
  });
}

// ── useSeasonGuide ────────────────────────────────────────────────────────────

export function useSeasonGuide() {
  return useQuery({
    queryKey: ["season-guide"],
    queryFn: () => colorApi.getSeasonGuide().then((r) => r.data.seasons),
    staleTime: Infinity,  // Static data — never stale
  });
}
