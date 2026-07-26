"use client";
import { motion } from "framer-motion";
import { ScanFace, Sliders, Sparkles, ShoppingBag } from "lucide-react";

const STEPS = [
  { n: "01", icon: ScanFace,    title: "Facial Scan",          desc: "Upload a selfie. Our AI pipeline maps 468 facial landmarks, analyses your skin tone, and detects concerns." },
  { n: "02", icon: Sliders,     title: "Style Quiz",           desc: "Answer 12 questions about your lifestyle, budget, and aesthetic preferences to build your Style DNA." },
  { n: "03", icon: Sparkles,    title: "AI Curation",          desc: "Our hybrid recommendation engine generates personalised picks across beauty, fashion, and fragrance." },
  { n: "04", icon: ShoppingBag, title: "Discover & Try",       desc: "Virtual try-on every recommendation. Ask Aura AI for deeper explanations. Save what you love." },
];

export function LandingHowItWorks() {
  return (
    <section id="how-it-works" className="py-28 border-t border-white/[0.05]">
      <div className="container">
        <div className="mb-16 text-center space-y-4">
          <motion.p
            initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
            className="text-xs tracking-widest uppercase text-brand-gold/80 font-medium"
          >
            How It Works
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="font-display text-display-md font-light tracking-tightest"
          >
            From scan to <span className="italic text-gold-gradient">style</span> in minutes
          </motion.h2>
        </div>

        <div className="relative">
          {/* Connecting line */}
          <div className="absolute left-8 top-10 bottom-10 w-px bg-gradient-to-b from-brand-gold/30 via-brand-gold/10 to-transparent hidden lg:block" />

          <div className="space-y-6 lg:space-y-0 lg:grid lg:grid-cols-4 lg:gap-6">
            {STEPS.map((step, i) => {
              const Icon = step.icon;
              return (
                <motion.div
                  key={step.n}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.12, duration: 0.55 }}
                  className="relative flex gap-5 lg:flex-col lg:gap-4"
                >
                  <div className="relative flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-brand-gold/20 bg-brand-gold/8 lg:h-14 lg:w-14">
                    <Icon className="h-6 w-6 text-brand-gold lg:h-5 lg:w-5" />
                    <span className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-brand-gold text-2xs font-bold text-brand-black">{i + 1}</span>
                  </div>
                  <div className="space-y-2 lg:pt-0 pt-2">
                    <p className="text-2xs font-medium tracking-widest text-brand-gold/60 uppercase">{step.n}</p>
                    <h3 className="font-sans text-base font-semibold text-foreground">{step.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{step.desc}</p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
