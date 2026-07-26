"use client";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Sparkles, Star } from "lucide-react";
import { Button } from "@/components/ui/button";

const HERO_BADGES = ["AI Skin Analysis", "Virtual Try-On", "Style DNA", "Fragrance Match"];

export function LandingHero() {
  return (
    <section className="relative flex min-h-screen items-center justify-center overflow-hidden pt-24 pb-16">
      <div className="container relative z-10 flex flex-col items-center text-center">

        {/* Pill badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
          className="mb-8"
        >
          <span className="inline-flex items-center gap-2 rounded-full border border-brand-gold/25 bg-brand-gold/8 px-4 py-1.5 text-xs font-medium tracking-widest uppercase text-brand-gold">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-gold animate-gold-pulse" />
            Introducing AuraFit AI · 2025
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: [0.23, 1, 0.32, 1] }}
          className="max-w-4xl font-display text-display-lg md:text-display-xl font-light leading-[1.05] tracking-tightest text-balance text-foreground"
        >
          Your beauty,{" "}
          <span className="italic text-gold-gradient">precisely</span>
          {" "}curated by AI
        </motion.h1>

        {/* Sub */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25 }}
          className="mt-7 max-w-xl text-base md:text-lg leading-relaxed text-muted-foreground text-pretty"
        >
          AuraFit analyses your skin tone, facial features, and style preferences to
          deliver hyper-personalised beauty, skincare, fragrance, and wardrobe recommendations.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.38 }}
          className="mt-10 flex flex-col items-center gap-4 sm:flex-row"
        >
          <Button variant="gold" size="lg" asChild className="min-w-44 shadow-gold-glow">
            <Link href="/auth/register">
              Start Your Journey <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button variant="ghost-gold" size="lg" asChild>
            <Link href="/#how-it-works">See How It Works</Link>
          </Button>
        </motion.div>

        {/* Social proof */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.55 }}
          className="mt-12 flex items-center gap-6 text-sm text-muted-foreground/60"
        >
          <div className="flex items-center gap-1.5">
            {[...Array(5)].map((_, i) => (
              <Star key={i} className="h-3.5 w-3.5 fill-brand-gold text-brand-gold" />
            ))}
            <span className="ml-1">4.9 · 2,400+ users</span>
          </div>
          <span className="hidden sm:block h-4 w-px bg-white/10" />
          <span className="hidden sm:block">No credit card required</span>
        </motion.div>

        {/* Feature tags */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.65 }}
          className="mt-14 flex flex-wrap justify-center gap-2"
        >
          {HERO_BADGES.map((tag, i) => (
            <motion.span
              key={tag}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.7 + i * 0.08 }}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] px-3.5 py-1.5 text-xs text-foreground/60"
            >
              <Sparkles className="h-3 w-3 text-brand-gold/60" />
              {tag}
            </motion.span>
          ))}
        </motion.div>

        {/* Hero visual — abstract orb */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, delay: 0.3, ease: [0.23, 1, 0.32, 1] }}
          className="mt-20 relative w-full max-w-2xl mx-auto"
        >
          <div className="relative aspect-video rounded-3xl overflow-hidden border border-white/[0.08] bg-gradient-to-br from-brand-graphite to-brand-black shadow-luxury-xl">
            {/* Simulated app UI preview */}
            <div className="absolute inset-0 bg-dark-mesh" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center space-y-3">
                <div className="mx-auto h-20 w-20 rounded-2xl bg-gold-gradient flex items-center justify-center shadow-gold-glow animate-float">
                  <Sparkles className="h-9 w-9 text-brand-black" />
                </div>
                <p className="font-display text-2xl italic text-foreground/40">Your style awaits</p>
              </div>
            </div>
            {/* Corner accents */}
            <div className="absolute top-4 left-4 h-12 w-12 border-l-2 border-t-2 border-brand-gold/20 rounded-tl-xl" />
            <div className="absolute bottom-4 right-4 h-12 w-12 border-r-2 border-b-2 border-brand-gold/20 rounded-br-xl" />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
