"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-brand-black text-center px-6">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-80 w-80 rounded-full bg-brand-gold/[0.06] blur-[80px]" />
      </div>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="relative z-10 space-y-6 max-w-md"
      >
        <div className="mx-auto h-16 w-16 rounded-2xl bg-gold-gradient flex items-center justify-center shadow-gold-glow">
          <Sparkles className="h-7 w-7 text-brand-black" />
        </div>
        <div>
          <p className="font-display text-8xl font-light text-gold-gradient">404</p>
          <h1 className="mt-3 font-display text-display-sm font-light text-foreground">Page not found</h1>
          <p className="mt-3 text-muted-foreground">This page has left your wardrobe.</p>
        </div>
        <Button variant="gold" asChild>
          <Link href="/"><ArrowLeft className="h-4 w-4" /> Back Home</Link>
        </Button>
      </motion.div>
    </div>
  );
}
