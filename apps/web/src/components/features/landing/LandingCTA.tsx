"use client";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function LandingCTA() {
  return (
    <section className="py-28 border-t border-white/[0.05]">
      <div className="container">
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.23, 1, 0.32, 1] }}
          className="relative overflow-hidden rounded-3xl border border-brand-gold/15 bg-gradient-to-br from-brand-graphite to-brand-black p-12 md:p-16 text-center gold-border-animated"
        >
          <div className="absolute inset-0 bg-dark-mesh pointer-events-none" />
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 h-48 w-96 rounded-full bg-brand-gold/10 blur-3xl" />

          <div className="relative z-10 space-y-6 max-w-xl mx-auto">
            <p className="text-xs tracking-widest uppercase text-brand-gold/70 font-medium">Begin Your Journey</p>
            <h2 className="font-display text-display-md font-light tracking-tightest text-foreground">
              Discover beauty<br /><span className="italic text-gold-gradient">made for you</span>
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              Join thousands who've found their signature style through the power of AI. Free to start, no card required.
            </p>
            <Button variant="gold" size="lg" asChild className="shadow-gold-glow">
              <Link href="/auth/register">
                Create Free Account <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
