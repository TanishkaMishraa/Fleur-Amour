/**
 * AuraFit — Stage 9 API clients.
 * Calls the virtual-tryon service (port 8020, proxied via /vtryon-api).
 */
import axios from "axios";
import type {
  TryOnResult, WardrobeItemClassification,
  AIOutfit, CapsuleAnalysis, CelebrityMatchResult,
} from "@/types/stage9";

const vtClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_VTRYON_API_URL ?? "/vtryon-api/api/v1",
  timeout: 30000,    // 30s — image processing can be slow
});

// ── Virtual Try-On ─────────────────────────────────────────────────────────────

export const tryOnApi = {
  /** Apply lipstick / foundation / eyeshadow to a selfie */
  applyMakeup: async (
    imageFile:  File,
    hexColor:   string,
    tryOnType:  "lipstick" | "foundation" | "eyeshadow",
    intensity:  number = 1.0,
  ): Promise<TryOnResult> => {
    const fd = new FormData();
    fd.append("file",        imageFile);
    fd.append("hex_color",   hexColor);
    fd.append("try_on_type", tryOnType);
    fd.append("intensity",   String(intensity));
    const { data } = await vtClient.post<TryOnResult>("/tryon/makeup", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  /** Apply hair colour simulation */
  applyHairColor: async (
    imageFile: File,
    hexColor:  string,
    intensity: number = 1.0,
  ): Promise<TryOnResult> => {
    const fd = new FormData();
    fd.append("file",      imageFile);
    fd.append("hex_color", hexColor);
    fd.append("intensity", String(intensity));
    const { data } = await vtClient.post<TryOnResult>("/tryon/hair", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
};

// ── Wardrobe AI ─────────────────────────────────────────────────────────────────

export const wardrobeAIApi = {
  /** Classify a clothing item image */
  classifyItem: async (imageFile: File): Promise<WardrobeItemClassification> => {
    const fd = new FormData();
    fd.append("file", imageFile);
    const { data } = await vtClient.post<WardrobeItemClassification>(
      "/wardrobe/classify", fd, { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  },

  /** Generate AI outfit combinations */
  generateOutfits: async (payload: {
    wardrobe_items: unknown[];
    occasion?:      string;
    season?:        string;
    color_season?:  string;
    archetype?:     string;
    limit?:         number;
  }): Promise<AIOutfit[]> => {
    const { data } = await vtClient.post<AIOutfit[]>("/wardrobe/outfits", payload);
    return data;
  },

  /** Analyse wardrobe for capsule completeness */
  analyseCapsule: async (payload: {
    wardrobe_items: unknown[];
    archetype?:     string;
  }): Promise<CapsuleAnalysis> => {
    const { data } = await vtClient.post<CapsuleAnalysis>("/wardrobe/capsule", payload);
    return data;
  },
};

// ── Celebrity Matching ─────────────────────────────────────────────────────────

export const celebrityApi = {
  /** Find celebrity style matches for a selfie */
  matchCelebrity: async (imageFile: File): Promise<CelebrityMatchResult> => {
    const fd = new FormData();
    fd.append("file", imageFile);
    const { data } = await vtClient.post<CelebrityMatchResult>(
      "/celebrity/match", fd, { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  },
};
