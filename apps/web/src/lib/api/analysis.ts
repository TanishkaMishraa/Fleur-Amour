/**
 * AuraFit — Facial Analysis API client (Stage 4).
 * Covers the direct-to-S3 upload flow (presign → PUT → confirm) and the
 * async facial-scan task lifecycle (dispatch → poll → result).
 */
import { apiClient } from "./client";
import type {
  ApiResponse, FacialScanRecord, ScanTaskStatus,
} from "@/types";

interface PresignResponse {
  upload_url: string;
  s3_key: string;
  upload_id: string;
  expires_in: number;
}

interface ConfirmUploadResponse {
  upload_id: string;
  task_id: string;
  status: string;
  message: string;
}

export const analysisApi = {
  /** Step 1: request a presigned S3 PUT URL for a facial scan selfie. */
  presign: (file: File) =>
    apiClient.post<ApiResponse<PresignResponse>>("/uploads/presign", {
      file_type: file.type,
      size_bytes: file.size,
      purpose: "facial_scan",
    }),

  /** Step 2: PUT the raw file bytes directly to S3 (bypasses backend). */
  uploadToS3: (uploadUrl: string, file: File) =>
    fetch(uploadUrl, {
      method: "PUT",
      headers: { "Content-Type": file.type },
      body: file,
    }),

  /** Step 3: confirm upload — dispatches the facial-scan Celery task. */
  confirmUpload: (uploadId: string, s3Key: string) =>
    apiClient.post<ApiResponse<ConfirmUploadResponse>>(`/uploads/${uploadId}/confirm`, {
      upload_id: uploadId,
      s3_key: s3Key,
      purpose: "facial_scan",
    }),

  /** Step 4: kick off the analysis pipeline once upload is confirmed. */
  startFacialScan: (s3Key: string, uploadId: string) =>
    apiClient.post<ApiResponse<ScanTaskStatus>>("/analysis/facial-scan", {
      s3_key: s3Key,
      upload_id: uploadId,
    }),

  /** Poll task status — call every 1.5–2s until status is SUCCESS/FAILURE. */
  getTaskStatus: (taskId: string) =>
    apiClient.get<ApiResponse<ScanTaskStatus>>(`/analysis/tasks/${taskId}`),

  /** List all scans for the current user (most recent first). */
  listScans: () =>
    apiClient.get<ApiResponse<FacialScanRecord[]>>("/analysis/scans"),

  /** Get the most recent active scan (used on dashboard overview). */
  getLatestScan: () =>
    apiClient.get<ApiResponse<FacialScanRecord | null>>("/analysis/scans/latest"),

  /** Get a single scan by ID (history detail page). */
  getScanById: (scanId: string) =>
    apiClient.get<ApiResponse<FacialScanRecord>>(`/analysis/scans/${scanId}`),
};

/**
 * Convenience helper: runs the full presign → upload → confirm → start flow
 * for a single image file. Returns the Celery task_id to poll.
 */
export async function uploadAndStartScan(file: File): Promise<string> {
  const presignRes = await analysisApi.presign(file);
  const presign = presignRes.data.data;
  if (!presign) throw new Error("Failed to get upload URL");

  const putRes = await analysisApi.uploadToS3(presign.upload_url, file);
  if (!putRes.ok) throw new Error("Failed to upload image to storage");

  const confirmRes = await analysisApi.confirmUpload(presign.upload_id, presign.s3_key);
  const confirm = confirmRes.data.data;
  if (!confirm) throw new Error("Failed to confirm upload");

  return confirm.task_id;
}
