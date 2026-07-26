"use client";
/**
 * AuraFit — ColorSwatch component.
 * Renders a row of colour swatches from a palette.
 * Hovering reveals the colour name. Clicking copies the hex.
 */
import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ColorEntry } from "@/types/color";

interface ColorSwatchProps {
  colors: ColorEntry[];
  size?: "sm" | "md" | "lg";
  showNames?: boolean;
  maxVisible?: number;
  className?: string;
}

const sizeClasses = {
  sm: "h-8 w-8 rounded-lg",
  md: "h-11 w-11 rounded-xl",
  lg: "h-14 w-14 rounded-2xl",
};

function SingleSwatch({ color, size = "md", showName }: {
  color: ColorEntry; size?: "sm" | "md" | "lg"; showName?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const [hovered, setHovered] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(color.hex).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  return (
    <div className="group flex flex-col items-center gap-1.5">
      <button
        onClick={copy}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        title={`${color.name} — ${color.hex}`}
        className={cn(
          "relative flex-shrink-0 cursor-pointer transition-all duration-200",
          "ring-1 ring-white/10 hover:ring-2 hover:ring-white/30",
          "hover:scale-110 active:scale-95",
          sizeClasses[size]
        )}
        style={{ backgroundColor: color.hex }}
      >
        {/* Copy / check icon */}
        <span className={cn(
          "absolute inset-0 flex items-center justify-center rounded-xl",
          "opacity-0 group-hover:opacity-100 transition-opacity",
          "bg-black/25"
        )}>
          {copied
            ? <Check className="h-3.5 w-3.5 text-white" />
            : <Copy className="h-3 w-3 text-white" />}
        </span>
      </button>
      {showName && (
        <p className="text-2xs text-muted-foreground/60 text-center max-w-[52px] leading-tight">
          {color.name}
        </p>
      )}
    </div>
  );
}

export function ColorSwatchRow({
  colors, size = "md", showNames, maxVisible = 12, className
}: ColorSwatchProps) {
  const visible = colors.slice(0, maxVisible);
  const hidden  = colors.length - visible.length;

  return (
    <div className={cn("flex flex-wrap gap-2 items-start", className)}>
      {visible.map((c, i) => (
        <SingleSwatch key={`${c.hex}-${i}`} color={c} size={size} showName={showNames} />
      ))}
      {hidden > 0 && (
        <div className={cn(
          "flex-shrink-0 flex items-center justify-center rounded-xl",
          "bg-white/[0.04] border border-white/[0.08] text-2xs text-muted-foreground/50",
          sizeClasses[size]
        )}>
          +{hidden}
        </div>
      )}
    </div>
  );
}

/** Hero swatch — large, prominent display for the signature colour */
export function HeroSwatch({ color }: { color: ColorEntry }) {
  const [copied, setCopied] = useState(false);

  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(color.hex);
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
      }}
      className="group relative flex flex-col items-center gap-3"
    >
      <div
        className="h-24 w-24 rounded-3xl shadow-luxury-lg ring-2 ring-white/10 group-hover:ring-white/30 transition-all duration-300 group-hover:scale-105"
        style={{ backgroundColor: color.hex }}
      />
      <div className="text-center">
        <p className="text-sm font-medium text-foreground">{color.name}</p>
        <p className="text-2xs text-muted-foreground/50 font-mono mt-0.5">
          {copied ? "✓ Copied" : color.hex}
        </p>
      </div>
    </button>
  );
}
