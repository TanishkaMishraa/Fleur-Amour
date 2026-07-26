/**
 * AuraFit — Recommendation API client (Stage 6).
 * Calls the recommendation-service (proxied via Next.js rewrites at /rec-api).
 */
import axios from "axios";
import type {
  PaginatedProducts, ProductDetail, RecommendationResponse, RecDomain,
} from "@/types/recommendations";

// Separate axios instance pointing to recommendation service
const recClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_REC_API_URL ?? "/rec-api/api/v1",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

const catalogClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_REC_API_URL ?? "/rec-api/api/v1",
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

// ── Recommendation calls ───────────────────────────────────────────────────

export interface RecRequest {
  user_id:    string;
  domain?:    RecDomain;
  occasion?:  string;
  season?:    string;
  budget_max?:number;
  budget_min?:number;
  limit?:     number;
}

export const recommendationApi = {
  /** Get hybrid recommendations for any/specified domain. */
  getRecommendations: (req: RecRequest) =>
    recClient.post<RecommendationResponse>("/recommendations", req),

  /** Domain-specific shorthand (convenience wrappers). */
  getMakeup:      (req: RecRequest) => recClient.post<RecommendationResponse>("/recommendations", { ...req, domain: "makeup" }),
  getSkincare:    (req: RecRequest) => recClient.post<RecommendationResponse>("/recommendations", { ...req, domain: "skincare" }),
  getHaircare:    (req: RecRequest) => recClient.post<RecommendationResponse>("/recommendations", { ...req, domain: "haircare" }),
  getFragrance:   (req: RecRequest) => recClient.post<RecommendationResponse>("/recommendations", { ...req, domain: "fragrance" }),
  getFashion:     (req: RecRequest) => recClient.post<RecommendationResponse>("/recommendations", { ...req, domain: "fashion" }),
  getAccessories: (req: RecRequest) => recClient.post<RecommendationResponse>("/recommendations", { ...req, domain: "accessories" }),

  /** Record feedback on a recommendation. */
  sendFeedback: (rec_id: string, signals: { clicked?: boolean; saved?: boolean; purchased?: boolean }) =>
    recClient.post("/recommendations/feedback", { recommendation_id: rec_id, ...signals }),

  /** Record a user-product interaction. */
  recordInteraction: (payload: {
    user_id: string;
    product_id: string;
    interaction_type: string;
    rating?: number;
  }) => recClient.post("/interactions", payload),
};

// ── Catalog calls ──────────────────────────────────────────────────────────

export interface SearchParams {
  q?:            string;
  domain?:       RecDomain;
  category_slug?:string;
  brand_slug?:   string;
  price_min?:    number;
  price_max?:    number;
  skin_tone?:    string;
  undertone?:    string;
  in_stock_only?:boolean;
  sort?:         string;
  page?:         number;
  per_page?:     number;
}

export const catalogApi = {
  searchProducts: (params: SearchParams) =>
    catalogClient.get<PaginatedProducts>("/products", { params }),

  getProduct: (productId: string) =>
    catalogClient.get<ProductDetail>(`/products/${productId}`),

  getSimilarProducts: (productId: string, limit?: number) =>
    catalogClient.get<{ items: any[]; total: number }>(`/products/${productId}/similar`, {
      params: { limit },
    }),

  getReviews: (productId: string, limit?: number) =>
    catalogClient.get(`/products/${productId}/reviews`, { params: { limit } }),

  listCategories: (parentId?: string) =>
    catalogClient.get("/categories", { params: parentId ? { parent_id: parentId } : {} }),

  listBrands: (tier?: string) =>
    catalogClient.get("/brands", { params: tier ? { tier } : {} }),
};
