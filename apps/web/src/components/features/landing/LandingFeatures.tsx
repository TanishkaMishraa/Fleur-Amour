"use client";
import { motion } from "framer-motion";
import { Camera, Shirt, Sparkles, Wind, MessageCircle, Shield } from "lucide-react";

const FEATURES = [
  { icon: Camera, title: "AI Skin Analysis", desc: "DeepFace + MediaPipe facial scan identifies your skin tone, type, concerns, and face shape in seconds.", color: "from-amber-500/20 to-orange-500/10" },
  { icon: Sparkles, title: "Style DNA", desc: "Collaborative filtering + CLIP embeddings learn your unique aesthetic and surface the perfect products.", color: "from-brand-gold/20 to-amber-500/10" },
  { icon: Shirt, title: "Virtual Try-On", desc: "OpenCV + TPS warping overlays makeup, accessories, and clothing onto your selfie with photorealistic blending.", color: "from-violet-500/20 to-purple-500/10" },
  { icon: Wind, title: "Fragrance Match", desc: "Semantic note embeddings map your scent preferences to your next signature fragrance.", color: "from-sky-500/20 to-blue-500/10" },
  { icon: MessageCircle, title: "Aura AI Chat", desc: "A streaming RAG-powered personal stylist that knows your wardrobe, skin profile, and style history.", color: "from-emerald-500/20 to-teal-500/10" },
  { icon: Shield, title: "Privacy First", desc: "Your facial data is processed and deleted. We never sell your data. GDPR compliant.", color: "from-rose-500/20 to-pink-500/10" },
];

export function LandingFeatures() {
  return (
    <section id="features" className="py-28 relative">
      <div className="container">
        <div className="mb-16 text-center space-y-4">
          <motion.p
            initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
            className="text-xs tracking-widest uppercase text-brand-gold/80 font-medium"
          >
            The Platform
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.6 }}
            className="font-display text-display-md font-light tracking-tightest text-foreground"
          >
            Everything about <span className="italic text-gold-gradient">your</span> beauty
          </motion.h2>
          <motion.p
            initial={{ opacity: 0 }} whileInView={{ opacity: 1 }}
            viewport={{ once: true }} transition={{ delay: 0.2 }}
            className="max-w-lg mx-auto text-muted-foreground leading-relaxed"
          >
            Six AI systems working in concert to understand, recommend, and refine your personal style.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((feat, i) => {
            const Icon = feat.icon;
            return (
              <motion.div
                key={feat.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.08, ease: [0.23, 1, 0.32, 1] }}
                className="luxury-card group p-6 space-y-4"
              >
                <div className={`inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${feat.color}`}>
                  <Icon className="h-5 w-5 text-foreground/80" />
                </div>
                <div className="space-y-2">
                  <h3 className="font-sans text-base font-semibold tracking-tight text-foreground">{feat.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">{feat.desc}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
