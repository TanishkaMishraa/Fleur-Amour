/**
 * AuraFit — Color Intelligence API client (Stage 5).
 * Thin wrappers over apiClient. All types from @/types/color.
 */
import { apiClient } from "./client";
import type { ApiResponse } from "@/types";
import type {
  ColorProfileRecord,
  FullColorAnalysisResponse,
} from "@/types/color";

interface ComputeRequest {
  scan_id?: string | null;
  use_extended_seasons?: boolean;
}

export const colorApi = {
  /**
   * Run the Color Intelligence Engine against the user's facial scan.
   * Returns the full season classification + all recommendation sets.
   * Synchronous — no polling needed.
   */
  compute: (payload: ComputeRequest = {}) =>
    apiClient.post<ApiResponse<FullColorAnalysisResponse>>("/color/compute", {
      scan_id: payload.scan_id ?? null,
      use_extended_seasons: payload.use_extended_seasons ?? true,
    }),

  /** Get the active (most recent) color profile. */
  getProfile: () =>
    apiClient.get<ApiResponse<ColorProfileRecord | null>>("/color/profile"),

  /** Full history of color profiles (newest first). */
  getHistory: () =>
    apiClient.get<ApiResponse<ColorProfileRecord[]>>("/color/history"),

  /** Delete a specific color profile by ID. */
  deleteProfile: (profileId: string) =>
    apiClient.delete<void>(`/color/profiles/${profileId}`),

  /** Static educational guide for all 16 seasons. */
  getSeasonGuide: () =>
    apiClient.get<{ seasons: Array<{
      key: string;
      family: string;
      description: string;
      characteristics: string[];
      celebrities: string[];
      contrast: string;
      chroma: string;
      value: string;
    }> }>("/color/season-guide"),
};
