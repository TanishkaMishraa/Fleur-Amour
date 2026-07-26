"use client";
/**
 * AuraFit — Face mesh overlay (Stage 4).
 * Renders the 468-point MediaPipe mesh as an SVG overlay on top of the
 * user's photo, plus the bounding box and key landmark markers.
 * Mesh points are normalised [0,1] — scaled to the rendered image size.
 */
import { useEffect, useRef, useState } from "react";
import type { FullAnalysisResult } from "@/types";

interface FaceMeshOverlayProps {
  imageUrl: string;
  result: FullAnalysisResult;
  showMesh?: boolean;
  showBoundingBox?: boolean;
  className?: string;
}

export function FaceMeshOverlay({
  imageUrl, result, showMesh = true, showBoundingBox = false, className,
}: FaceMeshOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDims({ w: width, h: height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const { mesh_points, bounding_box } = result;

  return (
    <div ref={containerRef} className={`relative overflow-hidden rounded-2xl ${className ?? ""}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={imageUrl} alt="Facial analysis" className="block w-full h-auto" />

      {dims.w > 0 && (
        <svg
          className="absolute inset-0 pointer-events-none"
          width={dims.w} height={dims.h}
          viewBox={`0 0 ${dims.w} ${dims.h}`}
        >
          {showMesh && mesh_points?.map((p, i) => (
            <circle
              key={i}
              cx={p[0] * dims.w}
              cy={p[1] * dims.h}
              r={0.9}
              fill="#C9A84C"
              opacity={0.55}
            />
          ))}

          {showBoundingBox && bounding_box && (
            <rect
              x={bounding_box.x * (dims.w / (bounding_box.w / bounding_box.confidence || 1))}
              y={bounding_box.y}
              width={bounding_box.w}
              height={bounding_box.h}
              fill="none"
              stroke="#E8C96C"
              strokeWidth={1.5}
              strokeDasharray="6 4"
              rx={12}
            />
          )}
        </svg>
      )}

      {/* Gold corner accents for luxury framing */}
      <div className="pointer-events-none absolute inset-3 border border-brand-gold/20 rounded-xl" />
    </div>
  );
}
