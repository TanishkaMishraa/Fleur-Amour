// ── Core domain types — aligned with Stage 1 + Stage 3 backend ───────────────

export type UserRole   = "user" | "stylist" | "admin";
export type SkinTone   = "fair" | "light" | "medium" | "olive" | "tan" | "deep";
export type SkinType   = "normal" | "dry" | "oily" | "combination" | "sensitive";
export type Undertone  = "cool" | "warm" | "neutral";
export type BodyShape  = "hourglass" | "pear" | "apple" | "rectangle" | "inverted_triangle";

export interface User {
  id:              string;
  email:           string;
  full_name:       string;
  role:            UserRole;
  is_active:       boolean;
  is_verified:     boolean;
  avatar_url:      string | null;
  mfa_enabled:     boolean;
  last_login_at:   string | null;
  last_login_ip:   string | null;
  created_at:      string;
}

export interface UserProfile {
  id:                  string;
  user_id:             string;
  skin_tone:           SkinTone | null;
  skin_type:           SkinType | null;
  undertone:           Undertone | null;
  hair_type:           string | null;
  hair_color:          string | null;
  eye_color:           string | null;
  body_shape:          BodyShape | null;
  height_cm:           number | null;
  weight_kg:           number | null;
  age_range:           string | null;
  style_archetypes:    string[] | null;
  fragrance_family:    string[] | null;
  skin_concerns:       string[] | null;
  avoided_ingredients: string[] | null;
  budget_range:        string | null;
  currency:            string;
  onboarding_complete: boolean;
  quiz_version:        number;
}

export interface UserPreferences {
  id:                    string;
  user_id:               string;
  // Notifications
  email_marketing:       boolean;
  email_recommendations: boolean;
  email_product_updates: boolean;
  email_security_alerts: boolean;
  push_recommendations:  boolean;
  push_tryon_complete:   boolean;
  push_scan_complete:    boolean;
  in_app_notifications:  boolean;
  // Display
  theme:                 string;
  language:              string;
  currency:              string;
  measurement_unit:      string;
  // Privacy
  profile_public:        boolean;
  allow_data_training:   boolean;
  allow_personalisation: boolean;
}

export interface UserSession {
  id:             string;
  device_name:    string | null;
  device_type:    string | null;  // mobile | desktop | tablet
  ip_address:     string | null;
  location:       string | null;
  last_active_at: string | null;
  created_at:     string;
  is_current:     boolean;
}

export interface UserSecurity {
  email:                  string;
  is_verified:            boolean;
  mfa_enabled:             boolean;
  password_changed_at:    string | null;
  last_login_at:          string | null;
  last_login_ip:          string | null;
  failed_login_attempts:  number;
  active_sessions_count:  number;
}

export interface OAuthAccount {
  id:             string;
  provider:       string;
  provider_email: string | null;
  created_at:     string;
}

// ── API envelope types ─────────────────────────────────────────────────────

export interface ApiError {
  code:    string;
  field?:  string;
  message: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data:    T | null;
  errors:  ApiError[] | null;
}

export interface PaginationMeta {
  page:        number;
  per_page:    number;
  total:       number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data:    T[];
  meta:    PaginationMeta;
  errors:  ApiError[] | null;
}

// ── Domain types (wardrobe, chat, etc.) ───────────────────────────────────

export interface WardrobeItem {
  id: string; wardrobe_id: string; product_id: string | null;
  custom_name: string | null; category: string | null;
  image_url: string | null; notes: string | null; cost: number | null;
  times_worn: number; color_tags: string[] | null;
  occasion_tags: string[] | null; season_tags: string[] | null;
  brand: string | null; created_at: string;
}

export interface Product {
  id: string; sku: string; name: string; brand: string;
  category: string; description: string; price: number;
  currency: string; image_urls: string[];
  attributes: Record<string, unknown>;
}

export interface ChatMessage {
  id: string; session_id: string;
  role: "user" | "assistant"; content: string; created_at: string;
}

export interface Upload {
  id: string; purpose: string;
  status: "pending" | "uploaded" | "processing" | "complete" | "failed";
  s3_key: string; celery_task_id: string | null;
  result_url: string | null; created_at: string;
}

// ── Facial Analysis types (Stage 4) ──────────────────────────────────────────

export type FaceShape =
  | "oval" | "round" | "square" | "heart" | "oblong" | "diamond" | "triangle" | "unknown";

export interface FaceShapeResult {
  shape: FaceShape;
  confidence: number;
  ratios: { face_length: number; jaw_width: number; cheekbone: number };
  description: string;
}

export interface SkinToneResult {
  tone: SkinTone;
  undertone: Undertone;
  ita_angle: number;
  lab_values: { L: number; a: number; b: number };
  hex_color: string;
  fitzpatrick: number;
  confidence: number;
}

export interface AgeEstimationResult {
  estimated_age: number;
  age_range: string;
  confidence: number;
  model: string;
}

export type HairType = "straight" | "wavy" | "curly" | "coily" | "unknown";

export interface HairAnalysisResult {
  hair_detected: boolean;
  hair_type: HairType;
  dominant_color: string;
  color_names: string[];
  texture_score: number | null;
  shine_score: number | null;
  volume_score: number | null;
}

export type SkinConcernType =
  | "acne" | "dark_circles" | "hyperpigmentation" | "fine_lines"
  | "enlarged_pores" | "redness" | "dryness" | "oiliness"
  | "uneven_texture" | "dark_spots";

export interface SkinConcernResult {
  concern: SkinConcernType;
  severity: number;
  region: string;
  pixel_count: number | null;
}

export interface AcneAnalysisResult {
  detected: boolean;
  count: number;
  severity: "none" | "mild" | "moderate" | "severe";
  severity_score: number;
  regions: string[];
  concerns: SkinConcernResult[];
}

export interface DarkCircleResult {
  detected: boolean;
  severity: number;
  lab_delta: number;
  category: "none" | "mild" | "moderate" | "severe";
  vascularity: boolean;
}

export interface SkinTextureResult {
  overall_score: number;
  roughness: number;
  pore_visibility: number;
  evenness: number;
  haralick_features: Record<string, number>;
  lbp_score: number | null;
}

export interface SymmetryResult {
  overall_score: number;
  eye_symmetry: number;
  mouth_symmetry: number;
  nostril_symmetry: number;
  jaw_symmetry: number;
  deviation_summary: string;
}

export interface QualityCheck {
  passed: boolean;
  brisque_score: number;
  face_visible: boolean;
  face_centered: boolean;
  good_lighting: boolean;
  no_occlusion: boolean;
  rejection_reason: string | null;
}

export interface MakeupRecommendations {
  foundation: { shade_category: string; undertone: string; finish: string; coverage: string };
  blush: { placement: string; tone: string };
  [key: string]: unknown;
}

export interface SkincareRecommendations {
  priority_concerns: string[];
  routine_focus: string[];
  [key: string]: unknown;
}

export interface FullAnalysisResult {
  pipeline_version: string;
  processing_time_ms: number;
  quality: QualityCheck;
  face_shape: FaceShapeResult;
  bounding_box: { x: number; y: number; w: number; h: number; confidence: number };
  mesh_points: number[][];
  symmetry: SymmetryResult;
  skin_tone: SkinToneResult;
  age_estimation: AgeEstimationResult;
  acne_analysis: AcneAnalysisResult;
  dark_circles: DarkCircleResult;
  skin_texture: SkinTextureResult;
  skin_concerns: SkinConcernResult[];
  hair_analysis: HairAnalysisResult;
  makeup_recommendations: MakeupRecommendations;
  skincare_recommendations: SkincareRecommendations;
  hairstyle_recommendations: string[];
}

export interface ScanTaskStatus {
  task_id: string;
  status: "PENDING" | "STARTED" | "PROGRESS" | "SUCCESS" | "FAILURE" | "UNKNOWN";
  progress: number | null;
  step: string | null;
  result: { success: boolean; scan_id?: string; result?: FullAnalysisResult; error_code?: string; error_message?: string } | null;
  error: string | null;
}

export interface FacialScanRecord {
  id: string;
  user_id: string;
  storage_path: string;
  face_shape: string | null;
  skin_analysis: Record<string, unknown> | null;
  facial_features: Record<string, unknown> | null;
  model_version: string | null;
  quality_score: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
