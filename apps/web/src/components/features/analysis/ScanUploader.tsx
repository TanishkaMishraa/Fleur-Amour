"use client";
/**
 * AuraFit — Scan uploader (Stage 4).
 * Drag-drop / click upload + live camera capture, with a luxury
 * progress overlay showing pipeline stage labels while polling.
 */
import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Camera, Upload, X, RotateCcw, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { cn } from "@/lib/utils";

interface ScanUploaderProps {
  phase: "idle" | "uploading" | "queued" | "analyzing" | "complete" | "error";
  progress: number;
  step: string | null;
  error: string | null;
  onFile: (file: File) => void;
  onRetry: () => void;
}

const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 10 * 1024 * 1024;

export function ScanUploader({ phase, progress, step, error, onFile, onRetry }: ScanUploaderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview]   = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const isBusy = phase === "uploading" || phase === "queued" || phase === "analyzing";

  const handleFile = useCallback((file: File | undefined) => {
    if (!file) return;
    if (!ACCEPTED.includes(file.type)) return;
    if (file.size > MAX_BYTES) return;
    setPreview(URL.createObjectURL(file));
    onFile(file);
  }, [onFile]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  if (isBusy && preview) {
    return (
      <div className="relative overflow-hidden rounded-3xl luxury-card">
        <div className="relative aspect-[4/5] sm:aspect-[3/4] max-h-[560px] mx-auto">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="Uploading" className="h-full w-full object-cover opacity-50" />
          <div className="absolute inset-0 bg-gradient-to-b from-brand-black/20 via-brand-black/40 to-brand-black/80" />

          {/* Scanning line animation */}
          <motion.div
            className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-brand-gold to-transparent shadow-gold-glow"
            animate={{ top: ["10%", "90%", "10%"] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
          />

          <div className="absolute inset-x-0 bottom-0 p-6 sm:p-8 space-y-4">
            <div className="flex items-center gap-3">
              <LoadingSpinner size="sm" />
              <p className="font-display text-lg font-light text-foreground">{step ?? "Processing"}</p>
            </div>
            <Progress value={progress} gold />
            <p className="text-xs text-muted-foreground/60">
              This usually takes 10–20 seconds. Hang tight while Aura analyses your photo.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="luxury-card p-10 text-center space-y-5">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 border border-destructive/20">
          <AlertTriangle className="h-6 w-6 text-destructive" />
        </div>
        <div className="space-y-1.5 max-w-sm mx-auto">
          <h3 className="font-display text-xl font-light">We couldn't complete your scan</h3>
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
        <Button variant="gold" onClick={onRetry}>
          <RotateCcw className="h-4 w-4" /> Try Again
        </Button>
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={cn(
        "relative rounded-3xl border-2 border-dashed transition-all duration-300",
        "flex flex-col items-center justify-center gap-6 p-10 sm:p-16 text-center",
        dragOver
          ? "border-brand-gold/50 bg-brand-gold/[0.03] scale-[1.01]"
          : "border-white/[0.08] bg-white/[0.01] hover:border-white/[0.15]"
      )}
    >
      <div className="relative">
        <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-gold-gradient shadow-gold-glow animate-float">
          <Camera className="h-8 w-8 text-brand-black" />
        </div>
      </div>

      <div className="space-y-2 max-w-sm">
        <h3 className="font-display text-2xl font-light">Reveal your beauty profile</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Upload a clear, front-facing photo in good lighting. Aura will analyse your
          skin tone, undertone, face shape, and more — completely privately.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
        <Button variant="gold" onClick={() => fileInputRef.current?.click()}>
          <Upload className="h-4 w-4" /> Upload Photo
        </Button>
        <Button variant="ghost-gold" onClick={() => cameraInputRef.current?.click()}>
          <Camera className="h-4 w-4" /> Take Photo
        </Button>
      </div>

      <p className="text-2xs text-muted-foreground/40">JPG, PNG or WebP · Max 10MB</p>

      <input
        ref={fileInputRef} type="file" accept={ACCEPTED.join(",")} className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <input
        ref={cameraInputRef} type="file" accept="image/*" capture="user" className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
    </div>
  );
}
