"use client";
/**
 * AuraFit — Virtual Try-On Canvas (Stage 9).
 *
 * Client-side AR pipeline using the MediaPipe FaceMesh WASM model
 * running directly in the browser — zero server round-trips for
 * real-time rendering (<16ms per frame at 60fps).
 *
 * Architecture:
 *   1. Camera feed via HTMLVideoElement
 *   2. MediaPipe FaceMesh WASM detects 468 landmarks per frame
 *   3. Canvas2D renders makeup overlays at exact landmark positions
 *   4. Colour blending via globalCompositeOperation + rgba fill
 *
 * Fallback: If camera unavailable, accept a file upload and process
 * server-side via tryOnApi (returns base64 result image).
 *
 * Performance targets:
 *   Real-time (camera):   60fps, <5ms render per frame
 *   Static image:         Server-side ~250ms
 */
import {
  useCallback, useEffect, useRef, useState,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Camera, Upload, Loader2, Download, RefreshCw,
  Sliders, Eye, Layers, Palette,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { TryOnPreset, TryOnType } from "@/types/stage9";
import {
  LIPSTICK_PRESETS, EYESHADOW_PRESETS,
  HAIR_COLOR_PRESETS, FOUNDATION_SHADES,
} from "@/types/stage9";
import { tryOnApi } from "@/lib/api/stage9";

// ── Hex → RGBA helper ──────────────────────────────────────────────────────────

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ── Lip landmark indices (MediaPipe Face Mesh) ─────────────────────────────────
const UPPER_LIP = [61,185,40,39,37,0,267,269,270,409,291,308,415,310,311,312,13,82,81,80,191,78];
const LOWER_LIP = [61,146,91,181,84,17,314,405,321,375,291,308,324,318,402,317,14,87,178,88,95,78];
const LEFT_EYE_UPPER  = [246,161,160,159,158,157,173,133,155,154,153,145,144,163,7];
const RIGHT_EYE_UPPER = [466,388,387,386,385,384,398,362,382,381,380,374,373,390,249];

// ── Types ──────────────────────────────────────────────────────────────────────

interface Props {
  mode:      "camera" | "photo";   // "camera" = live webcam, "photo" = uploaded image
  onCapture?:(imageDataUrl: string) => void;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function VirtualTryOnCanvas({ mode, onCapture }: Props) {
  const videoRef    = useRef<HTMLVideoElement>(null);
  const canvasRef   = useRef<HTMLCanvasElement>(null);
  const fileRef     = useRef<HTMLInputElement>(null);
  const animRef     = useRef<number>(0);
  const faceRef     = useRef<any>(null);          // MediaPipe FaceMesh instance
  const landmarksRef= useRef<any>(null);          // Latest detected landmarks

  const [activeType,    setActiveType]    = useState<TryOnType>("lipstick");
  const [activePreset,  setActivePreset]  = useState<TryOnPreset>(LIPSTICK_PRESETS[0]);
  const [intensity,     setIntensity]     = useState(0.7);
  const [isLoading,     setIsLoading]     = useState(false);
  const [cameraOn,      setCameraOn]      = useState(false);
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [serverResult,  setServerResult]  = useState<string | null>(null);
  const [error,         setError]         = useState<string | null>(null);
  const [fps,           setFps]           = useState(0);

  const presetsByType: Record<TryOnType, TryOnPreset[]> = {
    lipstick:   LIPSTICK_PRESETS,
    eyeshadow:  EYESHADOW_PRESETS,
    hair_color: HAIR_COLOR_PRESETS,
    foundation: FOUNDATION_SHADES,
  };

  const TAB_META: Array<{ type: TryOnType; label: string; icon: React.ReactNode }> = [
    { type: "lipstick",   label: "Lip",    icon: <Palette className="h-3.5 w-3.5" /> },
    { type: "eyeshadow",  label: "Eye",    icon: <Eye className="h-3.5 w-3.5" /> },
    { type: "foundation", label: "Base",   icon: <Layers className="h-3.5 w-3.5" /> },
    { type: "hair_color", label: "Hair",   icon: <Sliders className="h-3.5 w-3.5" /> },
  ];

  // ── MediaPipe init ─────────────────────────────────────────────────────────

  const initFaceMesh = useCallback(async () => {
    try {
      // @ts-ignore — MediaPipe CDN script sets window.FaceMesh
      if (typeof window.FaceMesh === "undefined") {
        await new Promise<void>((resolve) => {
          const s = document.createElement("script");
          s.src = "https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js";
          s.onload = () => resolve();
          document.head.appendChild(s);
        });
      }
      // @ts-ignore
      const fm = new window.FaceMesh({
        locateFile: (file: string) =>
          `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
      });
      fm.setOptions({
        maxNumFaces:          1,
        refineLandmarks:      true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence:  0.5,
      });
      fm.onResults((results: any) => {
        landmarksRef.current = results.multiFaceLandmarks?.[0] ?? null;
        renderFrame(results.multiFaceLandmarks?.[0]);
      });
      faceRef.current = fm;
    } catch (err) {
      console.warn("MediaPipe load failed — falling back to server-side rendering", err);
    }
  }, []);

  // ── Camera stream ──────────────────────────────────────────────────────────

  const startCamera = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setCameraOn(true);
        if (!faceRef.current) await initFaceMesh();
        processVideoFrame();
      }
    } catch (err) {
      setError("Camera permission denied. Please allow camera access or upload a photo.");
    } finally {
      setIsLoading(false);
    }
  }, [initFaceMesh]);

  const stopCamera = useCallback(() => {
    const stream = videoRef.current?.srcObject as MediaStream | null;
    stream?.getTracks().forEach((t) => t.stop());
    cancelAnimationFrame(animRef.current);
    setCameraOn(false);
  }, []);

  // ── RAF video loop ─────────────────────────────────────────────────────────

  let lastFpsTime = 0;
  let frameCount  = 0;

  const processVideoFrame = useCallback(() => {
    const fm    = faceRef.current;
    const video = videoRef.current;
    if (!fm || !video || video.paused) return;

    const now = performance.now();
    frameCount++;
    if (now - lastFpsTime > 1000) {
      setFps(Math.round(frameCount));
      frameCount = 0;
      lastFpsTime = now;
    }

    fm.send({ image: video });
    animRef.current = requestAnimationFrame(processVideoFrame);
  }, []);

  // ── Canvas rendering ───────────────────────────────────────────────────────

  const renderFrame = useCallback((landmarks: any) => {
    const canvas = canvasRef.current;
    const video  = videoRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const src = uploadedImage
      ? (document.getElementById("uploaded-preview") as HTMLImageElement)
      : video;

    if (!src) return;

    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Draw base image (mirrored for camera, normal for upload)
    if (!uploadedImage) {
      ctx.save();
      ctx.scale(-1, 1);
      ctx.drawImage(src as HTMLVideoElement, -W, 0, W, H);
      ctx.restore();
    } else {
      ctx.drawImage(src as HTMLImageElement, 0, 0, W, H);
    }

    if (!landmarks) return;

    const lmPx = (idx: number): [number, number] => {
      const lm = landmarks[idx];
      return [lm.x * W, lm.y * H];
    };

    const alpha = activePreset.intensity ?? intensity;

    // Route to renderer
    if (activeType === "lipstick") {
      drawPolygon(ctx, UPPER_LIP.map(lmPx), hexToRgba(activePreset.hex, alpha));
      drawPolygon(ctx, LOWER_LIP.map(lmPx), hexToRgba(activePreset.hex, alpha));
    } else if (activeType === "eyeshadow") {
      drawPolygon(ctx, LEFT_EYE_UPPER.map(lmPx),  hexToRgba(activePreset.hex, alpha * 0.7));
      drawPolygon(ctx, RIGHT_EYE_UPPER.map(lmPx), hexToRgba(activePreset.hex, alpha * 0.7));
    } else if (activeType === "foundation") {
      // Foundation: large face oval with multiply blend
      const OVAL_IDX = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109];
      ctx.globalCompositeOperation = "multiply";
      drawPolygon(ctx, OVAL_IDX.map(lmPx), hexToRgba(activePreset.hex, alpha * 0.25));
      ctx.globalCompositeOperation = "source-over";
    }
  }, [activeType, activePreset, intensity, uploadedImage]);

  // ── Upload handler ────────────────────────────────────────────────────────

  const handleFileUpload = useCallback(async (file: File) => {
    setUploadedImage(URL.createObjectURL(file));
    setServerResult(null);

    if (activeType === "hair_color") {
      // Hair colour requires server-side (HSV segmentation)
      setIsLoading(true);
      try {
        const result = await tryOnApi.applyHairColor(file, activePreset.hex, intensity);
        if (result.success && result.result_b64) {
          setServerResult(`data:image/jpeg;base64,${result.result_b64}`);
        } else {
          setError(result.error ?? "Hair colour simulation failed");
        }
      } finally {
        setIsLoading(false);
      }
    } else {
      // For other types: load image into canvas and run MediaPipe
      if (!faceRef.current) await initFaceMesh();
      setTimeout(() => {
        const img = document.getElementById("uploaded-preview") as HTMLImageElement;
        if (img && faceRef.current) faceRef.current.send({ image: img });
      }, 500);
    }
  }, [activeType, activePreset, intensity, initFaceMesh]);

  // ── Capture ──────────────────────────────────────────────────────────────

  const capture = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
    onCapture?.(dataUrl);
    const link = document.createElement("a");
    link.download = `aurafit-tryon-${Date.now()}.jpg`;
    link.href = dataUrl;
    link.click();
  }, [onCapture]);

  // ── Effects ───────────────────────────────────────────────────────────────

  useEffect(() => {
    if (mode === "camera") startCamera();
    return () => { stopCamera(); cancelAnimationFrame(animRef.current); };
  }, [mode]);

  // Re-render when preset/intensity changes
  useEffect(() => {
    if (landmarksRef.current) renderFrame(landmarksRef.current);
  }, [activeType, activePreset, intensity, renderFrame]);

  // ── Tab change handler ────────────────────────────────────────────────────

  const handleTabChange = (type: TryOnType) => {
    setActiveType(type);
    const presets = presetsByType[type];
    setActivePreset(presets[0]);
    setServerResult(null);
    setError(null);
  };

  const displaySrc = serverResult ?? uploadedImage;

  return (
    <div className="space-y-6">
      {/* Try-on type tabs */}
      <div className="flex gap-1 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-1">
        {TAB_META.map(({ type, label, icon }) => (
          <button
            key={type}
            onClick={() => handleTabChange(type)}
            className={cn(
              "flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-medium transition-all",
              activeType === type
                ? "bg-brand-gold text-brand-black shadow-gold-glow"
                : "text-muted-foreground/60 hover:text-foreground"
            )}
          >
            {icon}{label}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Canvas / image display */}
        <div className="space-y-3">
          <div className="relative overflow-hidden rounded-3xl bg-black/40 aspect-[4/3] flex items-center justify-center">
            {/* Camera video (hidden, feeds canvas) */}
            <video
              ref={videoRef}
              className="hidden"
              playsInline
              muted
              autoPlay
            />

            {/* Result display */}
            {displaySrc ? (
              <img
                src={displaySrc}
                alt="Try-on result"
                className="w-full h-full object-contain"
              />
            ) : (
              <canvas
                ref={canvasRef}
                width={640}
                height={480}
                className="w-full h-full object-contain"
              />
            )}

            {/* Hidden img for uploaded preview → mediapipe processing */}
            {uploadedImage && (
              <img
                id="uploaded-preview"
                src={uploadedImage}
                alt=""
                className="hidden"
                onLoad={() => {
                  if (faceRef.current) {
                    const img = document.getElementById("uploaded-preview") as HTMLImageElement;
                    faceRef.current.send({ image: img });
                  }
                }}
              />
            )}

            {/* Loading overlay */}
            {isLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/60 rounded-3xl">
                <Loader2 className="h-8 w-8 text-brand-gold animate-spin" />
                <p className="text-sm text-white/70">Processing…</p>
              </div>
            )}

            {/* FPS counter */}
            {cameraOn && fps > 0 && (
              <div className="absolute top-3 right-3 rounded-lg bg-black/60 px-2 py-1 text-2xs text-white/50">
                {fps}fps
              </div>
            )}

            {/* Empty state */}
            {!displaySrc && !cameraOn && !isLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-center p-6">
                <div className="h-16 w-16 rounded-2xl bg-brand-gold/10 flex items-center justify-center">
                  <Camera className="h-8 w-8 text-brand-gold/60" />
                </div>
                <div className="space-y-1.5">
                  <p className="text-sm font-medium text-foreground">Virtual Try-On Studio</p>
                  <p className="text-xs text-muted-foreground/50">
                    Enable camera for real-time AR or upload a photo
                  </p>
                </div>
                <div className="flex gap-2 flex-wrap justify-center">
                  <Button variant="gold" size="sm" onClick={startCamera} className="gap-2">
                    <Camera className="h-4 w-4" /> Start Camera
                  </Button>
                  <Button variant="ghost-gold" size="sm"
                    onClick={() => fileRef.current?.click()} className="gap-2">
                    <Upload className="h-4 w-4" /> Upload Photo
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Controls bar */}
          {(cameraOn || displaySrc) && (
            <div className="flex items-center gap-3 flex-wrap">
              {!cameraOn && (
                <Button variant="ghost" size="sm" onClick={() => fileRef.current?.click()} className="gap-2">
                  <RefreshCw className="h-3.5 w-3.5" /> New Photo
                </Button>
              )}
              {cameraOn && (
                <Button variant="ghost" size="sm" onClick={stopCamera}>Stop Camera</Button>
              )}
              <Button variant="gold" size="sm" onClick={capture} className="gap-2">
                <Download className="h-4 w-4" /> Save Look
              </Button>

              <div className="flex items-center gap-2 ml-auto">
                <span className="text-2xs text-muted-foreground/40">Intensity</span>
                <input
                  type="range" min={0.3} max={1.0} step={0.05}
                  value={intensity}
                  onChange={(e) => setIntensity(Number(e.target.value))}
                  className="w-20 accent-brand-gold"
                />
                <span className="text-2xs text-brand-gold w-8">
                  {Math.round(intensity * 100)}%
                </span>
              </div>
            </div>
          )}

          {error && (
            <p className="text-xs text-destructive rounded-xl border border-destructive/20 bg-destructive/5 px-3 py-2">
              {error}
            </p>
          )}
        </div>

        {/* Colour picker panel */}
        <div className="space-y-4">
          <div>
            <p className="text-xs font-medium text-muted-foreground/60 mb-3 uppercase tracking-widest">
              {activeType.replace("_", " ")} shades
            </p>
            <div className="grid grid-cols-4 gap-2">
              {presetsByType[activeType].map((preset) => (
                <button
                  key={preset.hex}
                  onClick={() => {
                    setActivePreset(preset);
                    setServerResult(null);
                    // Re-trigger server-side for hair
                    if (activeType === "hair_color" && uploadedImage) {
                      const input = fileRef.current;
                      if (input?.files?.[0]) handleFileUpload(input.files[0]);
                    }
                  }}
                  title={preset.name}
                  className={cn(
                    "h-10 w-full rounded-xl ring-1 transition-all duration-200",
                    "hover:scale-110 active:scale-95",
                    activePreset.hex === preset.hex
                      ? "ring-white/80 scale-110 shadow-lg"
                      : "ring-white/10 hover:ring-white/30"
                  )}
                  style={{ backgroundColor: preset.hex }}
                />
              ))}
            </div>
          </div>

          {/* Active preset info */}
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-2">
            <div className="flex items-center gap-3">
              <div
                className="h-10 w-10 rounded-xl ring-1 ring-white/20 flex-shrink-0"
                style={{ backgroundColor: activePreset.hex }}
              />
              <div>
                <p className="text-sm font-medium">{activePreset.name}</p>
                <p className="text-2xs text-muted-foreground/40 font-mono">{activePreset.hex}</p>
              </div>
            </div>
            {activePreset.finish && (
              <Badge variant="default" className="text-2xs capitalize">{activePreset.finish}</Badge>
            )}
          </div>

          {/* Upload CTA if not in camera mode */}
          {!cameraOn && (
            <Button
              variant="ghost-gold"
              className="w-full gap-2"
              onClick={() => fileRef.current?.click()}
            >
              <Upload className="h-4 w-4" />
              {uploadedImage ? "Try different photo" : "Upload your photo"}
            </Button>
          )}
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFileUpload(file);
        }}
      />
    </div>
  );
}

// ── Canvas drawing helper ──────────────────────────────────────────────────────

function drawPolygon(
  ctx:   CanvasRenderingContext2D,
  points:[number, number][],
  color: string,
) {
  if (points.length < 3) return;
  ctx.beginPath();
  ctx.moveTo(points[0][0], points[0][1]);
  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(points[i][0], points[i][1]);
  }
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
}
