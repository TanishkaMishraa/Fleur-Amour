/**
 * AuraFit API client — Axios instance with interceptors.
 * Auto-attaches access token, auto-refreshes on 401, maps to ApiResponse envelope.
 */
import axios, { AxiosError, type AxiosInstance, type AxiosResponse } from "axios";
import Cookies from "js-cookie";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:80/api/v1";

function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: BASE_URL,
    timeout: 30_000,
    withCredentials: true, // send refresh_token cookie
    headers: { "Content-Type": "application/json" },
  });

  // ── Request: attach access token ─────────────────────────────────────────
  client.interceptors.request.use((config) => {
    const token = getAccessToken();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });

  // ── Response: unwrap envelope, handle 401 refresh ────────────────────────
  let isRefreshing = false;
  let refreshQueue: Array<(token: string) => void> = [];

  client.interceptors.response.use(
    (res: AxiosResponse) => res,
    async (error: AxiosError) => {
      const original = error.config as typeof error.config & { _retry?: boolean };
      if (error.response?.status === 401 && !original?._retry) {
        if (isRefreshing) {
          return new Promise((resolve) => {
            refreshQueue.push((token: string) => {
              if (original) {
                original.headers = original.headers ?? {};
                original.headers.Authorization = `Bearer ${token}`;
              }
              resolve(client(original!));
            });
          });
        }
        original!._retry = true;
        isRefreshing = true;
        try {
          const { data } = await client.post("/auth/refresh");
          const newToken: string = data?.data?.access_token;
          setAccessToken(newToken);
          refreshQueue.forEach((cb) => cb(newToken));
          refreshQueue = [];
          original!.headers!.Authorization = `Bearer ${newToken}`;
          return client(original!);
        } catch {
          clearAccessToken();
          if (typeof window !== "undefined") window.location.href = "/auth/login";
          return Promise.reject(error);
        } finally {
          isRefreshing = false;
        }
      }
      return Promise.reject(error);
    }
  );

  return client;
}

export const apiClient = createApiClient();

// ── Token storage (memory + cookie fallback) ──────────────────────────────
let _accessToken: string | null = null;

export function getAccessToken(): string | null {
  return _accessToken ?? Cookies.get("af_at") ?? null;
}
export function setAccessToken(token: string): void {
  _accessToken = token;
  Cookies.set("af_at", token, { sameSite: "strict", secure: process.env.NODE_ENV === "production" });
}
export function clearAccessToken(): void {
  _accessToken = null;
  Cookies.remove("af_at");
}
