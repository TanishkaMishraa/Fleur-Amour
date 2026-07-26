"use client";
/**
 * AuraFit — Face shape result card (Stage 4).
 * Shows the classified shape, confidence, and the three key facial
 * proportion ratios used by the classifier (jaw/face-length/cheekbone).
 */
import { Scan } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScoreRing } from "./ScoreRing";
import type { FaceShapeResult } from "@/types";

const SHAPE_LABELS: Record<string, string> = {
  oval: "Oval", round: "Round", square: "Square", heart: "Heart",
  oblong: "Oblong", diamond: "Diamond", triangle: "Triangle", unknown: "Unclassified",
};

export function FaceShapeCard({ data }: { data: FaceShapeResult }) {
  const ratios = [
    { label: "Face length", value: data.ratios.face_length, max: 2 },
    { label: "Jaw width",   value: data.ratios.jaw_width,   max: 1 },
    { label: "Cheekbone",   value: data.ratios.cheekbone,   max: 1 },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Scan className="h-4 w-4 text-brand-gold" /> Face Shape
        </CardTitle>
        <CardDescription>Calculated from 468-point facial mesh geometry</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center gap-5">
          <ScoreRing value={data.confidence} label="Confidence" />
          <div className="space-y-1.5">
            <p className="font-display text-2xl font-light">{SHAPE_LABELS[data.shape] ?? data.shape}</p>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">{data.description}</p>
          </div>
        </div>

        <div className="space-y-3 pt-2 border-t border-white/[0.06]">
          {ratios.map((r) => (
            <div key={r.label} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">{r.label}</span>
                <span className="font-mono text-foreground/70">{r.value.toFixed(2)}</span>
              </div>
              <Progress value={Math.min(100, (r.value / r.max) * 100)} gold />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
