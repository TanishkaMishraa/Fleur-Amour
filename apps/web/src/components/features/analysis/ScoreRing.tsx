"use client";
/**
 * AuraFit — Circular score ring (Stage 4).
 * Reusable gold-gradient progress ring for 0-1 scores
 * (symmetry, texture, severity, confidence, etc).
 */
import { cn } from "@/lib/utils";

interface ScoreRingProps {
  value: number;          // 0-1
  size?: number;           // px
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
  invert?: boolean;        // true = lower value is "better" (e.g. severity)
  className?: string;
}

export function ScoreRing({
  value, size = 88, strokeWidth = 6, label, sublabel, invert = false, className,
}: ScoreRingProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const displayValue = invert ? 1 - clamped : clamped;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - displayValue);

  const color =
    displayValue >= 0.7 ? "#C9A84C" :
    displayValue >= 0.4 ? "#D4818A" :
    "#8A8A8F";

  return (
    <div className={cn("flex flex-col items-center gap-2", className)}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={strokeWidth}
          />
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke={color} strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 800ms cubic-bezier(0.23,1,0.32,1)" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-display text-xl font-light text-foreground">
            {Math.round(displayValue * 100)}
          </span>
        </div>
      </div>
      {label && (
        <div className="text-center">
          <p className="text-xs font-medium text-foreground/80">{label}</p>
          {sublabel && <p className="text-2xs text-muted-foreground/50">{sublabel}</p>}
        </div>
      )}
    </div>
  );
}
