"use client";
/**
 * AuraFit — Virtual Try-On Dashboard Page (Stage 9).
 * Real-time makeup AR (lipstick/foundation/eyeshadow) + hair colour simulation.
 */
import { useState } from "react";
import { motion } from "framer-motion";
import { Camera, Upload, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GoldDivider } from "@/components/shared/GoldDivider";
import { VirtualTryOnCanvas } from "@/components/features/try-on/VirtualTryOnCanvas";
import { cn } from "@/lib/utils";

const anim = (i = 0) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: i * 0.07, duration: 0.4, ease: [0.23, 1, 0.32, 1] as const },
});

export default function TryOnPage() {
  const [mode, setMode] = useState<"camera" | "photo">("photo");

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-16">
      {/* Header */}
      <motion.div {...anim(0)} className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-2xs uppercase tracking-widest text-brand-gold/70">
            <Wand2 className="h-3.5 w-3.5" /> Virtual Try-On
          </div>
          <h1 className="font-display text-display-md font-light tracking-tightest">
            Try Before You Buy
          </h1>
          <p className="text-sm text-muted-foreground max-w-lg">
            Real-time AR makeup simulation — lipstick, foundation, eyeshadow, and hair colour.
            Uses your camera for live preview or upload a photo.
          </p>
        </div>
        {/* Mode toggle */}
        <div className="flex rounded-2xl border border-white/[0.08] overflow-hidden">
          {([
            { value: "photo",  label: "Photo",  icon: Upload  },
            { value: "camera", label: "Camera", icon: Camera  },
          ] as const).map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              onClick={() => setMode(value)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-sm transition-all",
                mode === value
                  ? "bg-brand-gold text-brand-black font-semibold"
                  : "text-muted-foreground/60 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
        </div>
      </motion.div>

      <GoldDivider />

      {/* Try-on canvas */}
      <motion.div {...anim(1)}>
        <VirtualTryOnCanvas
          mode={mode}
          onCapture={(url) => console.log("Captured:", url.slice(0, 40))}
        />
      </motion.div>

      {/* Tips */}
      <motion.div {...anim(3)} className="grid gap-3 sm:grid-cols-3 text-center">
        {[
          { emoji: "💡", title: "Best results",    desc: "Good lighting, face the camera straight-on" },
          { emoji: "🎨", title: "Adjust intensity", desc: "Use the slider to control how strong the effect appears" },
          { emoji: "📸", title: "Save your look",  desc: "Click 'Save Look' to download your try-on photo" },
        ].map((tip) => (
          <div key={tip.title} className="luxury-card px-4 py-4 space-y-1.5">
            <span className="text-xl">{tip.emoji}</span>
            <p className="text-xs font-semibold text-foreground">{tip.title}</p>
            <p className="text-2xs text-muted-foreground/50">{tip.desc}</p>
          </div>
        ))}
      </motion.div>
    </div>
  );
}
